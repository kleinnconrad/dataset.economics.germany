"""Tests of the feeds collector with a fake web and a fake annotator."""
import threading
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from typing import Any, Optional
from xml.sax.saxutils import escape

import httpx
import pytest

from annotation import AnnotationInput, CallBudgetExceededError, clean_annotation
from collectors.base import CollectorSkipped, RunContext
from collectors.feeds import Candidate, FeedsCollector, interleave, looks_economic, parse_feed, parse_news_sitemap
from conftest import COMPANIES_FIXTURE, RUN_STARTED, SOURCES_FIXTURE, read_dataset
from schema import ItemAnnotation
from settings import Settings
from sources import SourceHealthStore, load_config
from state import CollectorEntry
from test_annotation import label

SOURCES = SOURCES_FIXTURE
RECENT = RUN_STARTED - timedelta(hours=5)


def rss(items: list[tuple[str, str, Optional[datetime], str]]) -> str:
    """Builds an RSS feed from (title, link, published, description) tuples."""
    entries = "".join(
        f"<item><title>{escape(title)}</title><link>{escape(link)}</link>"
        + (f"<pubDate>{format_datetime(published)}</pubDate>" if published else "")
        + f"<description>{escape(description)}</description></item>"
        for title, link, published, description in items
    )
    return f'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>{entries}</channel></rss>'


def news_sitemap(items: list[tuple[str, str, datetime, str]]) -> str:
    """Builds a Google News sitemap from (title, link, published, keywords) tuples."""
    urls = "".join(
        f"<url><loc>{escape(link)}</loc><news:news><news:publication><news:name>N</news:name>"
        f"<news:language>de</news:language></news:publication>"
        f"<news:publication_date>{published.isoformat()}</news:publication_date>"
        f"<news:title>{escape(title)}</news:title><news:keywords>{escape(keywords)}</news:keywords></news:news></url>"
        for title, link, published, keywords in items
    )
    return ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">' + urls + "</urlset>")


class FakeAnnotator:
    """Annotator double that labels every item and records the inputs."""
    model = "fake-model"
    extraction_hash = "0123456789abcdef"

    def __init__(self, stop_after: Optional[int] = None) -> None:
        self.inputs: list[AnnotationInput] = []
        self.usage = type("Usage", (), {"calls": 0})()
        self._stop_after = stop_after

    def annotate(self, items: list[AnnotationInput]) -> list[Optional[ItemAnnotation]]:
        if self._stop_after is not None and len(self.inputs) >= self._stop_after:
            raise CallBudgetExceededError("MAX_GEMINI_CALLS_PER_RUN (1) reached")
        self.inputs.extend(items)
        return [clean_annotation(ItemAnnotation.model_validate(label(n)), item.kind, item.published)
                for n, item in enumerate(items, start=1)]


def collector(annotator: Any, config_path: Any = SOURCES) -> FeedsCollector:
    return FeedsCollector(annotator, config_path=config_path, companies_path=COMPANIES_FIXTURE)


def setup_sources(fake_web: Any) -> None:
    fake_web.add("https://news.example/wirtschaft/index.rss", rss([
        ("Volkswagen streicht Stellen bei Zulieferern", "https://news.example/politik/haushalt-1.html?utm_source=rss",
         RECENT, "Der Autobauer baut Stellen ab."),
        ("Alter Artikel", "https://news.example/wirtschaft/alt.html", RUN_STARTED - timedelta(days=10), "alt"),
    ]), content_type="application/rss+xml")
    fake_web.add("https://news.example/sitemap-news.xml", news_sitemap([
        ("Volkswagen streicht Stellen bei Zulieferern", "https://news.example/politik/haushalt-1.html", RECENT, "VW"),
        ("Bundesliga: Spieltag", "https://news.example/sport/bundesliga.html", RECENT, "Fußball"),
        ("Ministerin stellt Industriestrategie vor", "https://news.example/panorama/strategie.html", RECENT, "Industrie"),
    ]), content_type="application/xml")
    fake_web.add_fixture("https://news.example/politik/haushalt-1.html", "pages/news_article.html")
    fake_web.add("https://news.example/panorama/strategie.html", "<html><body><article><p>"
                 + "Die Ministerin stellte am Montag eine Strategie für die Industrie vor. " * 3
                 + "</p></article></body></html>")
    fake_web.add("https://trade.example/feed/", rss([
        ("Neue Modelle auf der Messe", "https://trade.example/news/messe", RECENT, ""),
    ]), content_type="application/rss+xml")
    fake_web.add("https://press.example/presse.rss", rss([
        ("Volkswagen Konzern legt Quartalszahlen vor", "https://press.example/presse/q3", RECENT, "Umsatz stabil"),
    ]), content_type="application/rss+xml")


def test_parse_feed_and_sitemap() -> None:
    outlet = load_config(SOURCES).outlets[0]
    feed = parse_feed(rss([("Titel", "https://news.example/a.html", RECENT, "<p>Teaser</p>")]).encode(),
                      outlet, "https://news.example/wirtschaft/index.rss")
    assert feed[0].title == "Titel" and feed[0].teaser == "Teaser" and feed[0].from_economics_feed
    assert feed[0].published_at == RECENT

    sitemap, children = parse_news_sitemap(news_sitemap([("T", "https://news.example/x.html", RECENT, "DAX, Börse")]).encode(),
                                           outlet, "https://news.example/sitemap-news.xml")
    assert children == [] and sitemap[0].keywords == ["DAX", "Börse"] and sitemap[0].channel == "news_sitemap"


def test_sitemap_with_entity_declarations_is_rejected() -> None:
    outlet = load_config(SOURCES).outlets[0]
    bomb = ('<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">]>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>&lol;</loc></url></urlset>')
    with pytest.raises(ValueError):
        parse_news_sitemap(bomb.encode(), outlet, "https://news.example/sitemap-news.xml")


def test_central_european_zone_abbreviations_are_not_read_as_utc() -> None:
    outlet = load_config(SOURCES).outlets[0]
    feed = ('<rss version="2.0"><channel><item><title>T</title><link>https://news.example/wirtschaft/a</link>'
            "<pubDate>Mon, 26 Oct 2026 10:00:00 CET</pubDate></item></channel></rss>")

    candidate = parse_feed(feed.encode(), outlet, "https://news.example/wirtschaft/index.rss")[0]

    assert candidate.published_at == datetime(2026, 10, 26, 9, 0, tzinfo=timezone.utc)


def test_looks_economic_filters_general_outlet_items_only() -> None:
    config = load_config(SOURCES)
    outlet, trade, press = config.outlets[0], config.outlets[1], config.press_sources[0]

    def candidate(source: Any, url: str, title: str) -> Candidate:
        return Candidate(source=source, url=url, key=url, title=title, teaser="", published_at=None, channel="rss")

    assert looks_economic(candidate(outlet, "https://news.example/wirtschaft/x.html", "Irgendwas"))
    assert looks_economic(candidate(outlet, "https://news.example/panorama/x.html", "Inflation steigt auf 3 Prozent"))
    assert not looks_economic(candidate(outlet, "https://news.example/sport/x.html", "Bayern gewinnt gegen Dortmund"))
    assert looks_economic(candidate(trade, "https://trade.example/news/x", "Neue Modelle"))
    assert looks_economic(candidate(press, "https://press.example/presse/x", "Sommerfest"))


def test_interleave_takes_turns() -> None:
    assert list(interleave([["a1", "a2", "a3"], ["b1"], ["c1", "c2"]])) == ["a1", "b1", "c1", "a2", "c2", "a3"]


def test_collect_writes_items_annotations_and_resolves_companies(fake_web, make_ctx) -> None:
    setup_sources(fake_web)
    ctx = make_ctx()
    annotator = FakeAnnotator()

    result = collector(annotator).collect(ctx, CollectorEntry(first_run=ctx.today))

    news = read_dataset(ctx.settings.output_dir, "news_items")
    press = read_dataset(ctx.settings.output_dir, "press_releases")
    annotations = read_dataset(ctx.settings.output_dir, "text_annotations")
    assert sorted(item["title"] for item in news) == ["Ministerin stellt Industriestrategie vor",
                                                      "Neue Modelle auf der Messe",
                                                      "Volkswagen streicht Stellen bei Zulieferern"]
    assert [item["title"] for item in press] == ["Volkswagen Konzern legt Quartalszahlen vor"]
    assert press[0]["company_id"] == "volkswagen" and press[0]["jurisdiction"] == "DE"
    assert len(annotations) == 4
    vw = next(item for item in news if item["title"].startswith("Volkswagen"))
    assert vw["channel"] == "rss" and vw["content_basis"] == "lead_text"
    assert vw["jsonld_type"] == "NewsArticle" and vw["is_paywalled"] is True
    assert vw["outlet_sector"] is None
    trade = next(item for item in news if item["outlet_id"] == "trade_example")
    assert trade["outlet_sector"] == "Automotive" and trade["content_basis"] == "title_only"
    annotation = next(a for a in annotations if a["item_id"] == vw["record_id"])
    assert annotation["mentioned_companies"] == ["volkswagen"]
    assert annotation["company_tone"] == {"volkswagen": "Negative"}
    assert annotation["company_roles"] == {"volkswagen": "Subject"}
    assert annotation["other_companies"] == ["Zulieferer GmbH"]
    assert annotation["indicators"] == {"Employment": "Falling"}
    assert annotation["commodities"] == {"Steel and iron ore": "Rising"}
    assert annotation["license"].startswith("Derived data of this project")
    assert result.counters["annotated"] == 4 and result.error is None
    strategy = next(item for item in news if item["title"].startswith("Ministerin"))
    assert strategy["channel"] == "news_sitemap" and strategy["keywords"] == ["Industrie"]
    press_input = next(item for item in annotator.inputs if item.kind == "press release")
    assert press_input.source == "Volkswagen Group (company)"


def test_second_run_skips_known_items(fake_web, make_ctx) -> None:
    setup_sources(fake_web)
    ctx = make_ctx()
    collector(FakeAnnotator()).collect(ctx, CollectorEntry(first_run=ctx.today))
    annotator = FakeAnnotator()

    result = collector(annotator).collect(make_ctx(), CollectorEntry(first_run=ctx.today))

    assert annotator.inputs == []
    assert result.counters["items_selected"] == 0


def test_blocked_source_is_marked_and_skipped(fake_web, make_ctx) -> None:
    setup_sources(fake_web)
    fake_web.add("https://press.example/presse.rss", "Forbidden", status=403)
    ctx = make_ctx()

    collector(FakeAnnotator()).collect(ctx, CollectorEntry(first_run=ctx.today))

    health = SourceHealthStore.load(ctx.settings.state_dir)
    assert health.get("vw_press").status == "blocked"
    assert not health.is_due("vw_press", ctx.today + timedelta(days=30))
    assert read_dataset(ctx.settings.output_dir, "press_releases") == []


def test_tdm_reservation_excludes_the_source(fake_web, make_ctx) -> None:
    setup_sources(fake_web)
    fake_web.add("https://news.example/.well-known/tdmrep.json", [{"location": "/", "tdm-reservation": 1}])
    ctx = make_ctx()

    collector(FakeAnnotator()).collect(ctx, CollectorEntry(first_run=ctx.today))

    health = SourceHealthStore.load(ctx.settings.state_dir)
    assert health.get("news_example").status == "tdm_reserved"
    news = read_dataset(ctx.settings.output_dir, "news_items")
    assert all(item["outlet_id"] != "news_example" for item in news)


def test_budget_stop_writes_items_without_annotations(fake_web, make_ctx) -> None:
    setup_sources(fake_web)
    ctx = make_ctx()

    result = collector(FakeAnnotator(stop_after=0)).collect(ctx, CollectorEntry(first_run=ctx.today))

    assert len(read_dataset(ctx.settings.output_dir, "news_items")) == 3
    assert read_dataset(ctx.settings.output_dir, "text_annotations") == []
    assert result.counters["not_annotated"] == 4
    assert result.error is None


def test_cap_annotates_press_releases_first_and_stores_the_rest_without_labels(fake_web, make_ctx) -> None:
    setup_sources(fake_web)
    ctx = make_ctx(max_annotations_per_run=2)
    annotator = FakeAnnotator()

    result = collector(annotator).collect(ctx, CollectorEntry(first_run=ctx.today))

    assert [item.kind for item in annotator.inputs].count("press release") == 1
    assert len(annotator.inputs) == 2
    assert len(read_dataset(ctx.settings.output_dir, "news_items")) == 3
    assert len(read_dataset(ctx.settings.output_dir, "text_annotations")) == 2
    assert result.counters["items_selected"] == 2 and result.counters["beyond_cap"] == 2


def test_items_after_the_run_deadline_are_stored_without_labels(fake_web, tmp_path, monkeypatch) -> None:
    setup_sources(fake_web)
    now = [RUN_STARTED]
    serve = fake_web.handler

    def slow_page(request: httpx.Request) -> httpx.Response:
        # The first article page takes longer than the run deadline
        if request.url.path == "/politik/haushalt-1.html":
            now[0] += timedelta(minutes=30)
        return serve(request)

    monkeypatch.setattr(fake_web, "handler", slow_page)
    settings = replace(Settings(), output_dir=tmp_path / "data")
    ctx = RunContext(settings, fake_web.client(), RUN_STARTED, clock=lambda: now[0])
    annotator = FakeAnnotator()

    result = collector(annotator).collect(ctx, CollectorEntry(first_run=ctx.today))

    assert not result.complete
    assert result.counters["annotated"] + result.counters["not_annotated"] == 4
    assert len(read_dataset(ctx.settings.output_dir, "news_items")) == 3
    assert len(read_dataset(ctx.settings.output_dir, "press_releases")) == 1
    assert "https://news.example/panorama/strategie.html" not in fake_web.requested


class ParallelAnnotator(FakeAnnotator):
    """Annotator double whose first two calls wait for each other, so that they must run at the same time."""

    def __init__(self) -> None:
        super().__init__()
        self._barrier = threading.Barrier(2, timeout=5)
        self._lock = threading.Lock()
        self._calls = 0

    def annotate(self, items: list[AnnotationInput]) -> list[Optional[ItemAnnotation]]:
        with self._lock:
            self._calls += 1
            call = self._calls
        if call <= 2:
            self._barrier.wait()
        return super().annotate(items)


def test_batches_are_annotated_in_parallel_and_written_in_order(fake_web, make_ctx) -> None:
    titles = [f"Volkswagen meldet Ergebnis {n}" for n in range(25)]
    fake_web.add("https://press.example/presse.rss", rss([
        (title, f"https://press.example/presse/{n}", RECENT - timedelta(minutes=n), "Text")
        for n, title in enumerate(titles)
    ]), content_type="application/rss+xml")
    ctx = make_ctx(gemini_concurrency=3)

    result = collector(ParallelAnnotator()).collect(ctx, CollectorEntry(first_run=ctx.today))

    assert result.counters["annotated"] == 25
    assert [item["title"] for item in read_dataset(ctx.settings.output_dir, "press_releases")] == titles
    assert len(read_dataset(ctx.settings.output_dir, "text_annotations")) == 25


def test_removed_sources_are_not_read(fake_web, make_ctx, tmp_path) -> None:
    setup_sources(fake_web)
    config = SOURCES.read_text(encoding="utf-8").replace(
        'feeds = ["https://press.example/presse.rss"]', 'feeds = ["https://press.example/presse.rss"]\nremoved = 2026-10-26')
    config_path = tmp_path / "sources.toml"
    config_path.write_text(config, encoding="utf-8")
    ctx = make_ctx()

    collector(FakeAnnotator(), config_path).collect(ctx, CollectorEntry(first_run=ctx.today))

    assert "https://press.example/presse.rss" not in fake_web.requested
    assert read_dataset(ctx.settings.output_dir, "press_releases") == []


def test_dry_run_reads_sources_without_writing(fake_web, make_ctx) -> None:
    setup_sources(fake_web)
    ctx = make_ctx(dry_run=True)

    result = collector(None).collect(ctx, CollectorEntry(first_run=ctx.today))

    assert result.counters["items_selected"] == 4
    assert not (ctx.settings.output_dir / "news_items").exists()
    assert "https://news.example/politik/haushalt-1.html" not in fake_web.requested


def test_missing_annotator_skips_the_collector(make_ctx) -> None:
    with pytest.raises(CollectorSkipped):
        collector(None).collect(make_ctx(), CollectorEntry(first_run=RUN_STARTED.date()))
