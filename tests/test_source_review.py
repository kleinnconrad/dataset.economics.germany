"""Tests of the monthly source review with a fake web and a fake search model."""
import json
from datetime import date, datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import source_review
from catalog import load_catalog
from companies import CompanyIndex, active_companies
from conftest import CATALOG_FIXTURE, COMPANIES_FIXTURE, FakeWeb
from settings import Settings
from source_review import (
    Change,
    NewEntry,
    SearchError,
    SearchModel,
    apply_changes,
    build_report,
    check_feed,
    count_company_mentions,
    count_items,
    feed_links,
    find_gaps,
    parse_json_array,
    period_end,
    run_review,
    stale_series,
    toml_value,
)
from sources import SourceHealth, SourceHealthStore, load_config
from state import SeenStore
from storage import dumps_records, partition_file

NOW = datetime(2026, 11, 1, 6, 0, tzinfo=timezone.utc)
RECENT = NOW - timedelta(days=1)

CONFIG = """\
# Test sources of the source review.

# feeds: 10 h
[[outlet]]
id = "news_example"
name = "News Example"
homepage = "https://news.example/"
outlet_type = "national_daily"
owner_group = "Example Group"
paywall_model = "mixed"
feeds = ["https://news.example/wirtschaft/index.rss", "https://news.example/old.rss", "https://news.example/gone.rss"]
news_sitemap = "https://news.example/sitemap-news.xml"
fetch_pages = true
added = 2026-01-05

[[outlet]]
id = "daily_example"
name = "Daily Example"
homepage = "https://daily.example/"
outlet_type = "regional_daily"
owner_group = "Example Verlag"
home_state = "DE-SN"
paywall_model = "free"
feeds = ["https://daily.example/rss"]
fetch_pages = true
added = 2026-01-05

[[outlet]]
id = "quiet_example"
name = "Quiet Example"
homepage = "https://quiet.example/"
outlet_type = "regional_daily"
owner_group = "Quiet Verlag"
home_state = "DE-TH"
paywall_model = "free"
feeds = ["https://quiet.example/rss"]
added = 2026-01-05

[[outlet]]
id = "kept_example"
name = "Kept Example"
homepage = "https://kept.example/"
outlet_type = "trade_press"
owner_group = "Kept Media"
sector = "Automotive"
paywall_model = "free"
feeds = ["https://kept.example/rss"]
added = 2026-01-05
keep = true

[[press_source]]
id = "vw_press"
name = "Volkswagen Group"
homepage = "https://vw.example/"
actor_type = "company"
company_id = "volkswagen"
jurisdiction = "DE"
feeds = ["https://vw.example/presse.rss"]
fetch_pages = false
added = 2026-01-05

[[press_source]]
id = "blocked_example"
name = "Blocked Ministry"
homepage = "https://blocked.example/"
actor_type = "federal_ministry"
jurisdiction = "DE"
feeds = ["https://blocked.example/rss"]
fetch_pages = true
added = 2026-01-05

# Candidates that were checked and not admitted.
[[excluded]]
id = "excluded_example"
name = "Excluded Example"
homepage = "https://excluded.example/"
status = "blocked"
reason = "blocks automated requests"
checked = 2026-01-05
"""


def rss(items: list[tuple[str, str, datetime]]) -> str:
    """Builds an RSS feed from (title, link, published) tuples."""
    entries = "".join(f"<item><title>{title}</title><link>{link}</link><pubDate>{format_datetime(published)}"
                      f"</pubDate></item>" for title, link, published in items)
    return f'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>{entries}</channel></rss>'


def economic_feed(host: str, count: int = 6, published: datetime = RECENT) -> str:
    return rss([(f"Inflation steigt im Monat {n}", f"https://{host}/wirtschaft/artikel-{n}.html", published)
                for n in range(count)])


def news_sitemap(host: str) -> str:
    return ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"><url>'
            f"<loc>https://{host}/wirtschaft/a.html</loc><news:news><news:publication><news:name>N</news:name>"
            f"<news:language>de</news:language></news:publication><news:publication_date>{RECENT.isoformat()}"
            "</news:publication_date><news:title>Konjunktur schwächelt</news:title></news:news></url></urlset>")


def serve_sources(fake_web: FakeWeb) -> None:
    """Serves the feeds of the configured test sources."""
    fake_web.add("https://news.example/robots.txt",
                 "# Die Nutzung für Text- und Data-Mining (§ 44b UrhG) ist vorbehalten.\nUser-agent: *\nAllow: /\n",
                 content_type="text/plain")
    fake_web.add("https://news.example/wirtschaft/index.rss", economic_feed("news.example"),
                 content_type="application/rss+xml")
    fake_web.add("https://news.example/old.rss", economic_feed("news.example", 2, NOW - timedelta(days=400)),
                 content_type="application/rss+xml")
    fake_web.add("https://news.example/sitemap-news.xml", news_sitemap("news.example"), content_type="application/xml")
    fake_web.add("https://daily.example/robots.txt", "User-agent: *\nCrawl-delay: 30\n", content_type="text/plain")
    fake_web.add("https://daily.example/rss", "", status=301, headers={"location": "https://daily.example/feed.xml"})
    fake_web.add("https://daily.example/feed.xml", economic_feed("daily.example"), content_type="application/rss+xml")
    fake_web.add("https://kept.example/rss", economic_feed("kept.example"), content_type="application/rss+xml")
    fake_web.add("https://vw.example/presse.rss", economic_feed("vw.example", 2), content_type="application/rss+xml")


def serve_candidates(fake_web: FakeWeb) -> None:
    """Serves the websites of the candidates that the fake search returns."""
    fake_web.add("https://ministry.example/", "<html><body>Ministerium</body></html>")
    fake_web.add("https://ministry.example/presse.rss", economic_feed("ministry.example", 3),
                 content_type="application/rss+xml")
    fake_web.add("https://office.example/", "Forbidden", status=403)
    fake_web.add("https://institut.example/", '<html><head><link rel="alternate" type="application/rss+xml" '
                 'href="/presse/feed.xml"></head><body></body></html>')
    fake_web.add("https://institut.example/presse/feed.xml", economic_feed("institut.example", 4),
                 content_type="application/rss+xml")
    fake_web.add("https://newsroom.example/", "<html><body>Newsroom</body></html>")
    fake_web.add("https://newsroom.example/presse.rss", economic_feed("newsroom.example", 2),
                 content_type="application/rss+xml")
    fake_web.add("https://fachblatt.example/", "<html><body>Fachblatt</body></html>")
    fake_web.add("https://fachblatt.example/robots.txt", "# Kein Text und Data Mining\nUser-agent: *\nAllow: /\n",
                 content_type="text/plain")
    fake_web.add("https://fachblatt.example/feed/", economic_feed("fachblatt.example", 6),
                 content_type="application/rss+xml")
    fake_web.add("https://reserved.example/.well-known/tdmrep.json", [{"location": "/", "tdm-reservation": 1}])


class FakeSearch:
    """Search double that answers each category with a prepared JSON text."""

    def __init__(self, answers: dict[str, Any]) -> None:
        self.answers = answers
        self.prompts: list[str] = []
        self.calls = 0

    def ask(self, prompt: str) -> str:
        self.prompts.append(prompt)
        self.calls += 1
        for marker, answer in self.answers.items():
            if marker in prompt:
                return answer if isinstance(answer, str) else json.dumps(answer)
        return "[]"


ANSWERS = {
    "economic, financial and labour market policy": [
        {"name": "Bundesministerium für Beispiele", "homepage": "https://ministry.example/",
         "feeds": ["https://ministry.example/presse.rss"], "actor_type": "federal_ministry"},
        {"name": "Amt für Sperren", "homepage": "https://office.example/", "feeds": [], "actor_type": "public_agency"},
        {"name": "Ausgeschlossen", "homepage": "https://excluded.example/", "feeds": [], "actor_type": "public_agency"},
    ],
    "business associations, economic research institutes": "```json\n" + json.dumps([
        {"name": "Institut für Beispielforschung", "homepage": "https://institut.example/", "feeds": [],
         "actor_type": "research_institute"},
        {"name": "Sportverein", "homepage": "https://sport.example/", "feeds": [], "actor_type": "club"},
    ]) + "\n```",
    "corporate newsrooms": [
        {"name": "Porsche", "homepage": "https://newsroom.example/", "feeds": ["https://newsroom.example/presse.rss"],
         "company_id": "porsche_ag"},
        {"name": "BMW", "homepage": "https://bmw.example/", "feeds": [], "company_id": "bmw"},
    ],
    "trade publications": [
        {"name": "Fachblatt Chemie", "homepage": "https://fachblatt.example/", "feeds": ["https://fachblatt.example/feed/"],
         "sector": "Chemicals", "owner_group": "Fachverlag", "paywall_model": "mixed"},
        {"name": "Vorbehalt-Kurier", "homepage": "https://reserved.example/", "feeds": [], "sector": "Chemicals",
         "owner_group": "Vorbehalt Verlag", "paywall_model": "hard"},
    ],
}


def write_annotations(data_dir: Path, day: date, records: list[dict[str, Any]]) -> None:
    path = partition_file(data_dir, "text_annotations", day)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_records(records), encoding="utf-8")


@pytest.fixture
def review_setup(tmp_path: Path, fake_web: FakeWeb) -> tuple[Settings, Path]:
    """Writes the test configuration, the state, recent records of three sources and annotations."""
    config_path = tmp_path / "sources.toml"
    config_path.write_text(CONFIG, encoding="utf-8")
    settings = Settings(output_dir=tmp_path / "data")
    health = SourceHealthStore(settings.state_dir / "sources.json", {
        "blocked_example": SourceHealth(status="blocked", last_attempt=NOW.date() - timedelta(days=10),
                                        last_error="blocked (HTTP 403): https://blocked.example/rss"),
    })
    health.save()
    for dataset, source_id in (("news_items", "news_example"), ("news_items", "daily_example"),
                               ("press_releases", "vw_press")):
        path = partition_file(settings.output_dir, dataset, (NOW - timedelta(days=10)).date())
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        path.write_text(dumps_records([*existing, {"record_id": f"x:{source_id}", "source_id": source_id}]),
                        encoding="utf-8")
    write_annotations(settings.output_dir, (NOW - timedelta(days=5)).date(), [
        {"record_id": f"a{n}", "mentioned_companies": ["porsche_ag"], "other_companies": ["Unbekannt AG"]}
        for n in range(3)
    ] + [{"record_id": "a9", "mentioned_companies": [], "other_companies": ["Lidl"]}])
    serve_sources(fake_web)
    serve_candidates(fake_web)
    return settings, config_path


def review(settings: Settings, config_path: Path, fake_web: FakeWeb, search: Any) -> tuple[str, Any]:
    return run_review(settings, config_path, fake_web.client(), search, NOW, companies_path=COMPANIES_FIXTURE,
                      catalog_path=CATALOG_FIXTURE)


def changes_by(result: Any) -> dict[tuple[str, str], Change]:
    return {(change.action, change.source_id): change for change in result.changes
            if change.action not in ("remove_feed",)}


def test_review_proposes_removals_fixes_additions_and_exclusions(review_setup, fake_web) -> None:
    settings, config_path = review_setup
    search = FakeSearch(ANSWERS)

    text, result = review(settings, config_path, fake_web, search)

    found = changes_by(result)
    assert "no economic items" in found[("remove_source", "quiet_example")].reason
    assert found[("remove_source", "blocked_example")].reason.startswith("blocked since")
    assert ("remove_source", "kept_example") not in found
    removed_feeds = {change.old: change.reason for change in result.changes if change.action == "remove_feed"}
    assert removed_feeds["https://news.example/old.rss"].startswith("newest item from")
    assert "404" in removed_feeds["https://news.example/gone.rss"]
    assert "natural language" in found[("set_fetch_pages", "news_example")].reason
    assert found[("replace_feed", "daily_example")].new == "https://daily.example/feed.xml"
    assert "crawl delay 30 s" in found[("set_fetch_pages", "daily_example")].reason
    assert not any("blocked.example" in url or "quiet.example" in url for url in fake_web.requested)
    assert not any("excluded.example" in url for url in fake_web.requested)

    # Companies without a press source, the most frequently named first ("Lidl" resolves to the Schwarz Gruppe)
    assert result.gaps.companies == ("porsche_ag", "schwarz_gruppe", "porsche_se")
    assert "Automotive" not in result.gaps.sectors and "Chemicals" in result.gaps.sectors
    assert result.searches == ["federal", "associations", "companies", "trade_press"]
    assert result.unregistered_companies == [("Unbekannt AG", 3)]

    added = {change.source_id: change.entry for change in result.changes if change.action == "add_source"}
    assert set(added) == {"ministry", "institut", "porsche_ag_press", "fachblatt"}
    assert added["institut"].fields["feeds"] == ["https://institut.example/presse/feed.xml"]
    assert added["institut"].fields["actor_type"] == "research_institute"
    assert added["porsche_ag_press"].fields["company_id"] == "porsche_ag"
    assert added["fachblatt"].fields["fetch_pages"] is False and added["fachblatt"].fields["sector"] == "Chemicals"
    assert added["ministry"].fields["fetch_pages"] is True
    excluded = {change.entry.fields["homepage"]: change.entry.fields for change in result.changes
                if change.action == "exclude"}
    assert excluded["https://office.example/"]["status"] == "blocked"
    assert excluded["https://reserved.example/"]["status"] == "tdm_reserved"
    assert excluded["https://office.example/"]["actor_type"] == "public_agency"
    assert excluded["https://reserved.example/"]["sector"] == "Chemicals"
    # Candidates outside the searched gaps are rejected without an exclusion
    assert any(rejection.homepage == "https://bmw.example/" and rejection.status is None
               for rejection in result.rejections)

    config = source_review.validate_config_text(text)
    by_id = {source.id: source for source in config.sources}
    assert by_id["quiet_example"].removed == NOW.date() and not by_id["quiet_example"].active
    assert by_id["news_example"].feeds == ("https://news.example/wirtschaft/index.rss",)
    assert by_id["news_example"].fetch_pages is False and by_id["news_example"].news_sitemap is not None
    assert by_id["daily_example"].feeds == ("https://daily.example/feed.xml",)
    assert by_id["porsche_ag_press"].company_id == "porsche_ag" and by_id["porsche_ag_press"].added == NOW.date()
    assert by_id["fachblatt"].outlet_type == "trade_press"
    assert [entry.id for entry in config.excluded] == ["excluded_example", "office", "reserved"]
    assert "# source review 2026-11-01: feed https://news.example/old.rss removed" in text

    report = build_report(result, load_config(config_path), NOW, search=True)
    for heading in ("### Removals", "### Feeds and page fetching", "### Additions", "### Exclusions", "### Gaps",
                    "### Companies not in the registry", "### Series that need attention"):
        assert heading in report
    assert "| Quiet Example (`quiet_example`) | no economic items in the last 90 days |" in report
    assert "| Unbekannt AG | 3 |" in report
    assert "`eur_usd.EA` (ecb EXR): no values stored" in report


def test_excluded_candidates_are_checked_again_by_every_review(review_setup, fake_web) -> None:
    settings, config_path = review_setup
    config_path.write_text(CONFIG + (
        "\n[[excluded]]\nid = \"later_institut\"\nname = \"Späteres Institut\"\nhomepage = \"https://later.example/\"\n"
        "kind = \"press_source\"\nactor_type = \"research_institute\"\njurisdiction = \"DE\"\n"
        "feeds = [\"https://later.example/rss\"]\nstatus = \"no_feed\"\nreason = \"no feed\"\nchecked = 2026-10-01\n"),
        encoding="utf-8")
    fake_web.add("https://later.example/", "<html></html>")
    fake_web.add("https://later.example/rss", economic_feed("later.example", 2), content_type="application/rss+xml")

    text, result = review(settings, config_path, fake_web, None)

    assert result.rechecked == 1
    found = changes_by(result)
    assert ("add_source", "later_institut") in found and ("drop_exclusion", "later_institut") in found
    config = source_review.validate_config_text(text)
    assert "later_institut" in {source.id for source in config.press_sources}
    assert "later_institut" not in {entry.id for entry in config.excluded}


def test_review_without_search_changes_only_existing_sources(review_setup, fake_web) -> None:
    settings, config_path = review_setup

    text, result = review(settings, config_path, fake_web, None)

    assert result.searches == [] and result.candidates == 0
    assert not any(change.action in ("add_source", "exclude") for change in result.changes)
    assert "search for new sources was turned off" in build_report(result, load_config(config_path), NOW, False)


def test_unchanged_review_keeps_the_text(tmp_path) -> None:
    config_path = tmp_path / "sources.toml"
    config_path.write_text(CONFIG, encoding="utf-8")
    assert apply_changes(CONFIG, load_config(config_path), [], NOW.date()) == CONFIG


def test_apply_changes_keeps_other_entries_byte_identical(tmp_path) -> None:
    config_path = tmp_path / "sources.toml"
    config_path.write_text(CONFIG, encoding="utf-8")
    changes = [Change("remove_source", "quiet_example", 'no "items"')]

    text = apply_changes(CONFIG, load_config(config_path), changes, NOW.date())

    assert 'removed_reason = "no \\"items\\""' in text
    assert text.replace('removed = 2026-11-01\nremoved_reason = "no \\"items\\""\n', "") == CONFIG
    assert source_review.validate_config_text(text).outlets[2].removed_reason == 'no "items"'


def test_dropped_exclusion_is_removed_from_the_configuration(tmp_path) -> None:
    config_path = tmp_path / "sources.toml"
    config_path.write_text(CONFIG.replace('status = "blocked"', 'status = "no_feed"'), encoding="utf-8")
    config = load_config(config_path)
    entry = NewEntry("press_source", {"id": "excluded_ministry", "name": "Ministerium", "homepage": "https://x.example/",
                                      "actor_type": "federal_ministry", "jurisdiction": "DE",
                                      "feeds": ["https://x.example/rss"], "fetch_pages": True, "added": NOW.date()})
    changes = [Change("add_source", "excluded_ministry", "admitted", entry=entry),
               Change("drop_exclusion", "excluded_example", "admitted")]

    text = apply_changes(config_path.read_text(encoding="utf-8"), config, changes, NOW.date())

    parsed = source_review.validate_config_text(text)
    assert parsed.excluded == ()
    assert parsed.press_sources[-1].id == "excluded_ministry"


def test_find_gaps_counts_sources_that_leave_as_missing(tmp_path) -> None:
    config_path = tmp_path / "sources.toml"
    config_path.write_text(CONFIG, encoding="utf-8")
    config = load_config(config_path)
    companies = active_companies(COMPANIES_FIXTURE)

    assert "volkswagen" not in find_gaps(config, companies, {}).companies
    gaps = find_gaps(config, companies, {}, frozenset({"vw_press", "kept_example"}))
    assert "volkswagen" in gaps.companies and "Automotive" in gaps.sectors


def test_count_items_and_company_mentions_read_only_recent_partitions(tmp_path) -> None:
    for day, source_id in ((NOW.date() - timedelta(days=100), "old"), (NOW.date() - timedelta(days=5), "new")):
        path = partition_file(tmp_path, "news_items", day)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dumps_records([{"record_id": "r", "source_id": source_id}]), encoding="utf-8")
    write_annotations(tmp_path, NOW.date() - timedelta(days=100), [{"record_id": "x", "mentioned_companies": ["volkswagen"]}])
    write_annotations(tmp_path, NOW.date() - timedelta(days=5), [
        {"record_id": "y", "mentioned_companies": ["volkswagen", "volkswagen"], "other_companies": ["VW", "Neu GmbH"]}])

    since = NOW.date() - timedelta(days=90)
    assert count_items(tmp_path, since) == {"new": 1}
    registered, unregistered = count_company_mentions(tmp_path, since, CompanyIndex(active_companies(COMPANIES_FIXTURE)))
    assert registered == {"volkswagen": 2} and unregistered == {"Neu GmbH": 1}


@pytest.mark.parametrize("period, frequency, expected", [
    ("2026-09", "M", date(2026, 9, 30)), ("2026-12", "M", date(2026, 12, 31)), ("2026-Q4", "Q", date(2026, 12, 31)),
    ("2026-Q1", "Q", date(2026, 3, 31)), ("2026-S1", "S", date(2026, 6, 30)), ("2026", "A", date(2026, 12, 31)),
    ("2026-W01", "W", date(2026, 1, 4)), ("2026-10-23", "D", date(2026, 10, 23)), ("bad", "M", None),
])
def test_period_end(period: str, frequency: str, expected) -> None:
    assert period_end(period, frequency) == expected


def test_stale_series_lists_old_and_missing_series(tmp_path) -> None:
    catalog = [series for series in load_catalog(CATALOG_FIXTURE) if series.active]
    for series_id, values in (("eur_usd.EA", {"2026-10-30": 1.1}), ("bund_yield_10y.DE", {"2026-08-01": 3.0})):
        store = SeenStore.load(tmp_path, "economic_series", series_id)
        store.mark(series_id, "h", NOW.date(), data={"values": values})
        store.save()

    notes = stale_series(tmp_path, catalog, NOW.date())

    assert not any("eur_usd.EA" in note for note in notes)
    assert "`bund_yield_10y.DE` (bundesbank BBSIS): newest period 2026-08-01" in notes
    assert "`day_ahead_power_price.DE` (smard chart_data): no values stored" in notes


def test_check_feed_reports_redirects_and_errors(fake_web) -> None:
    serve_sources(fake_web)
    config = source_review.validate_config_text(CONFIG)
    web = fake_web.client()

    moved = check_feed(web, "https://daily.example/rss", config.outlets[1])
    missing = check_feed(web, "https://news.example/gone.rss", config.outlets[0])

    assert moved.outcome == "ok" and moved.moved_to == "https://daily.example/feed.xml" and len(moved.entries) == 6
    assert missing.outcome == "not_found"


def test_feed_links_and_json_answers() -> None:
    html = ('<html><head><link rel="alternate" type="application/rss+xml" href="/rss.xml">'
            '<link rel="stylesheet" href="/a.css"></head><body><a href="/presse/feed/">Feed</a>'
            '<a href="/feedback">Feedback</a></body></html>')
    assert feed_links(html, "https://site.example/start") == ["https://site.example/rss.xml",
                                                              "https://site.example/presse/feed/"]
    assert parse_json_array('Here: ```json\n[{"a": 1}]\n```') == [{"a": 1}]
    with pytest.raises(ValueError):
        parse_json_array("no list")
    assert toml_value(["a", 'b"c']) == '["a", "b\\"c"]'
    assert toml_value(NOW.date()) == "2026-11-01"


def test_search_model_stops_at_the_budget_and_wraps_errors() -> None:
    answers = iter([SimpleNamespace(text="[]", usage_metadata=None)] * 10)
    client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kwargs: next(answers)))
    model = SearchModel(Settings(gemini_api_key="key"), client=client, sleep=lambda seconds: None)

    for _ in range(source_review.MAX_SEARCH_CALLS):
        assert model.ask("prompt") == "[]"
    with pytest.raises(SearchError):
        model.ask("prompt")


def test_report_lists_notes(tmp_path) -> None:
    config_path = tmp_path / "sources.toml"
    config_path.write_text(CONFIG, encoding="utf-8")
    many = source_review.ReviewResult(notes=[f"note {n}" for n in range(source_review.MAX_REPORT_NOTES + 3)])

    report = build_report(many, load_config(config_path), NOW, True)

    assert "- note 0" in report
    assert "- 3 further notes are in the workflow log" in report
    assert "**Companies without a press source (searched, the most frequently named first):** none" in report


def test_main_writes_the_configuration_and_the_report(review_setup, fake_web, monkeypatch) -> None:
    settings, config_path = review_setup
    monkeypatch.setattr(source_review, "WebClient", fake_web.client)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    report = config_path.parent / "report.md"

    exit_code = source_review.main(["--report", str(report), "--config", str(config_path),
                                    "--output-dir", str(settings.output_dir), "--no-search"])

    assert exit_code == 0
    assert "## Source review" in report.read_text(encoding="utf-8")
    assert "removed = " in config_path.read_text(encoding="utf-8")
