"""Tests of the Wikipedia pageviews of the registered companies with a fake web."""
from datetime import timedelta

from collectors.pageviews import WIKIDATA_API_URL, PageviewsCollector, article_url
from conftest import COMPANIES_FIXTURE, RUN_STARTED, read_dataset
from state import CollectorEntry


def wikidata_answer() -> dict:
    return {"entities": {
        "Q156578": {"sitelinks": {"dewiki": {"title": "Volkswagen AG"}}},
        "Q40993": {"sitelinks": {"dewiki": {"title": "Porsche"}}},
        "Q2104551": {"sitelinks": {}},
        "Q712034": {"sitelinks": {"dewiki": {"title": "Schwarz-Gruppe"}}},
    }}


def views(days: list[str]) -> dict:
    return {"items": [{"timestamp": day.replace("-", "") + "00", "views": 100 + index}
                      for index, day in enumerate(days)]}


def test_article_url_encodes_titles() -> None:
    url = article_url("Volkswagen AG", RUN_STARTED.date(), RUN_STARTED.date())
    assert "/de.wikipedia.org/all-access/user/Volkswagen_AG/daily/20261027/20261027" in url


def test_collector_fetches_new_days_per_article(make_ctx, fake_web, tmp_path) -> None:
    fake_web.add(WIKIDATA_API_URL, wikidata_answer())
    base = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/de.wikipedia.org/all-access/user"
    fake_web.add(f"{base}/Volkswagen_AG/daily/20150701/20261026", views(["2026-10-25", "2026-10-26"]))
    fake_web.add(f"{base}/Porsche/daily/20150701/20261026", views(["2026-10-26"]))
    ctx = make_ctx()
    entry = CollectorEntry(first_run=ctx.today)
    result = PageviewsCollector(COMPANIES_FIXTURE).collect(ctx, entry)
    assert result.counters["records"] == 2 and result.counters["without_article"] == 1
    records = {record["company_id"]: record for record in read_dataset(tmp_path / "data", "wikipedia_pageviews")}
    assert records["volkswagen"]["daily_views"] == {"2026-10-25": 100, "2026-10-26": 101}
    assert records["volkswagen"]["wikipedia_project"] == "de.wikipedia"

    # A week later only the days after the last stored day are requested
    fake_web.requested.clear()
    fake_web.add(f"{base}/Volkswagen_AG/daily/20261027/20261102", views(["2026-10-27"]))
    later = make_ctx(started=RUN_STARTED + timedelta(days=7))
    PageviewsCollector(COMPANIES_FIXTURE).collect(later, entry)
    assert any("Volkswagen_AG/daily/20261027/20261102" in url for url in fake_web.requested)
