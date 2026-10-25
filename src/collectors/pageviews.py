"""
Collects the daily views of the German Wikipedia articles of the registered companies.

The article of a company is resolved at run time from its Wikidata id (sitelink ``dewiki``),
so that a renamed article keeps its series. For each company the collector fetches the days
since the last stored day from the Wikimedia Pageviews API (CC0), with the agent type ``user``
(views by people, without known crawlers and automated traffic). A new company gets the
history from July 2015, the first month of the API.

Pageviews measure public attention to a company, e.g. after profit warnings, scandals or job
cuts. The collector runs once a week; the API keeps the daily views and each run fetches all
days since the last stored day, so no day is lost. At the run deadline it stops; the remaining
articles follow in the next run.
"""
import logging
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote

from collectors.base import Collector, CollectorResult, RunContext, batches, series_start
from companies import CONFIG_PATH, active_companies
from schema import PageviewRecord
from state import CollectorEntry, is_backfilled
from web import FetchError, NotFoundError

logger = logging.getLogger(__name__)

DATASET = "wikipedia_pageviews"
SOURCE_ID = "wikimedia_pageviews"
LICENSE = "CC0-1.0"
PROJECT = "de.wikipedia"
PAGEVIEWS_URL = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/de.wikipedia.org/"
                 "all-access/user/{title}/daily/{start}/{end}")
WIKIDATA_API_URL = "https://www.wikidata.org/w/api.php"
# The first day with pageview data in the Wikimedia API
HISTORY_START = date(2015, 7, 1)
# Ids per Wikidata API request
API_BATCH_SIZE = 50
# Records are written in batches, so that an interrupted run keeps its progress
EMIT_BATCH_SIZE = 50


def german_titles_for_qids(ctx: RunContext, qids: Sequence[str]) -> dict[str, str]:
    """Returns the German Wikipedia titles of Wikidata items.

    Args:
        ctx: The run context.
        qids: Wikidata ids.

    Returns:
        dict[str, str]: Title by Wikidata id, for items with a German article.
    """
    titles: dict[str, str] = {}
    for batch in batches(sorted(set(qids)), API_BATCH_SIZE):
        data = ctx.web.get(WIKIDATA_API_URL, respect_robots=False, params={
            "action": "wbgetentities", "ids": "|".join(batch), "props": "sitelinks", "sitefilter": "dewiki",
            "format": "json",
        }).json()
        for qid, item in (data.get("entities") or {}).items():
            title = ((item.get("sitelinks") or {}).get("dewiki") or {}).get("title")
            if title:
                titles[qid] = title
    return titles


def article_url(title: str, start: date, end: date) -> str:
    """Builds the Pageviews API URL of an article and a day range.

    Args:
        title: Article title.
        start: First day.
        end: Last day.

    Returns:
        str: The URL.
    """
    encoded = quote(title.replace(" ", "_"), safe="")
    return PAGEVIEWS_URL.format(title=encoded, start=f"{start:%Y%m%d}", end=f"{end:%Y%m%d}")


def fetch_daily_views(ctx: RunContext, title: str, start: date, end: date) -> dict[date, int]:
    """Fetches the daily views of an article.

    Args:
        ctx: The run context.
        title: Article title.
        start: First day.
        end: Last day.

    Returns:
        dict[date, int]: Views by day; days without data are missing.
    """
    try:
        data = ctx.web.get(article_url(title, start, end), respect_robots=False).json()
    except NotFoundError:
        return {}
    views: dict[date, int] = {}
    for item in data.get("items", []):
        timestamp = str(item.get("timestamp", ""))
        try:
            day = datetime.strptime(timestamp[:8], "%Y%m%d").date()
        except ValueError:
            continue
        if isinstance(item.get("views"), int):
            views[day] = item["views"]
    return views


class PageviewsCollector(Collector):
    """Writes the new daily views of the German Wikipedia articles of the registered companies."""
    name = "wikipedia_pageviews"
    datasets = (DATASET,)
    min_days_between_runs = 6

    def __init__(self, registry_path: Path = CONFIG_PATH) -> None:
        """Initializes the collector.

        Args:
            registry_path: The company registry.
        """
        self._registry_path = registry_path

    def collect(self, ctx: RunContext, entry: CollectorEntry) -> CollectorResult:
        """Fetches the days since the last stored day for every article and emits one record per article.

        Args:
            ctx: The run context.
            entry: Run history of this collector.

        Returns:
            CollectorResult: Counters; the progress per article is kept in the seen store.
        """
        companies = [company for company in active_companies(self._registry_path) if company.wikidata]
        titles = german_titles_for_qids(ctx, [company.wikidata for company in companies if company.wikidata])
        seen = ctx.seen(DATASET)
        end = ctx.today - timedelta(days=1)
        records: list[PageviewRecord] = []
        counters: dict[str, Any] = {"articles": 0, "records": 0, "days": 0, "failed": 0, "without_article": 0}
        complete = True
        for position, company in enumerate(companies):
            title = titles.get(company.wikidata or "")
            if title is None:
                logger.warning("No German Wikipedia article for %s (%s).", company.id, company.wikidata)
                counters["without_article"] += 1
                continue
            counters["articles"] += 1
            if ctx.past_deadline():
                counters["deferred"] = len(companies) - position
                complete = False
                break
            start = series_start(seen.get(company.id), HISTORY_START)
            if start > end:
                continue
            try:
                views = fetch_daily_views(ctx, title, start, end)
            except FetchError as e:
                logger.warning("Pageviews of %s failed: %s", title, e)
                counters["failed"] += 1
                continue
            if not views:
                continue
            first, last = min(views), max(views)
            # Each record covers new days, so it is a new item with revision 0
            seen.mark(company.id, title, ctx.today, data={"last_day": last.isoformat()})
            records.append(PageviewRecord(
                **ctx.envelope(
                    DATASET, f"pageviews:{company.id}:{first.isoformat()}:{last.isoformat()}",
                    revision=0, source_id=SOURCE_ID, source_url=article_url(title, first, last),
                    license=LICENSE, backfilled=is_backfilled(first, entry.first_run),
                ),
                company_id=company.id,
                wikipedia_project=PROJECT,
                wikipedia_title=title,
                wikidata_qid=company.wikidata or "",
                daily_views=dict(sorted(views.items())),
            ))
            counters["days"] += len(views)
            if len(records) >= EMIT_BATCH_SIZE:
                ctx.emit(DATASET, records)
                counters["records"] += len(records)
                records = []
        ctx.emit(DATASET, records)
        counters["records"] += len(records)
        logger.info("Pageviews: %d records with %d days for %d articles.", counters["records"], counters["days"],
                    counters["articles"])
        failed = counters["failed"]
        error = f"{failed} of {counters['articles']} articles failed" if failed and failed == counters["articles"] else None
        return CollectorResult(counters=counters, complete=complete, error=error)
