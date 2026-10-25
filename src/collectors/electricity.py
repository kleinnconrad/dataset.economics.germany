"""
Collects daily electricity market data for Germany from SMARD.

Source: SMARD, the electricity market data platform of the Bundesnetzagentur
(``www.smard.de/app/chart_data``), which publishes data of the European transmission system
operators (ENTSO-E). The Bundesnetzagentur licenses the data under CC BY 4.0 with the
attribution "Bundesnetzagentur | SMARD.de". The platform has no robots.txt; its chart data
files are requested at one request per second.

Series: the day-ahead wholesale price of the bidding zone Germany/Luxembourg (daily average
in EUR/MWh), the grid load and the net generation per energy source (daily sums in MWh). A
catalog series selects a SMARD filter and region with ``key = "<filter>/<region>"``.

Fetch strategy: ``<filter>/<region>/index_day.json`` lists the start times of the files with
daily values, one file per year. A new series reads all files; a known series reads the two
newest files (the current and the previous year), so that revisions of recent days are
captured. Each file holds ``[timestamp, value]`` pairs, where the timestamp is midnight
Europe/Berlin in milliseconds; days without value (``null``) are not stored. Only days before
the day of the run are stored, because the current day is incomplete.

Records: vintages of each series in ``economic_series`` (see ``collectors/series.py``).

Schedule: every run; at the run deadline the collector stops and the remaining series follow
in the next run.
"""
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from catalog import CONFIG_PATH, Series, active_series
from collectors.base import Collector, CollectorResult, RunContext
from collectors.sdmx import collect_series
from collectors.series import DATASET, SeriesData, SeriesWriter, parse_value
from state import CollectorEntry

logger = logging.getLogger(__name__)

PROVIDER = "smard"
SOURCE_ID = "smard"
LICENSE = "CC-BY-4.0 (Bundesnetzagentur | SMARD.de)"
BASE_URL = "https://www.smard.de/app/chart_data"
RESOLUTION = "day"
# Files read for a series with stored values: the current and the previous year
RECENT_FILES = 2


def smard_day(timestamp_ms: Any) -> date:
    """Converts a SMARD timestamp (midnight Europe/Berlin in milliseconds) to the calendar day.

    Midnight in Berlin is 22:00 or 23:00 UTC of the previous day; adding twelve hours before
    taking the UTC date gives the Berlin day in summer and in winter.

    Args:
        timestamp_ms: The timestamp.

    Returns:
        date: The day.

    Raises:
        ValueError: If the timestamp is not a number.
    """
    if isinstance(timestamp_ms, bool) or not isinstance(timestamp_ms, (int, float)):
        raise ValueError(f"invalid timestamp {timestamp_ms!r}")
    moment = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc) + timedelta(hours=12)
    return moment.date()


def parse_values(data: Any, before: date) -> dict[str, float]:
    """Reads the daily values of a SMARD data file.

    Args:
        data: The parsed JSON file with a ``series`` list of ``[timestamp, value]`` pairs.
        before: First day that is not stored (the day of the run).

    Returns:
        dict[str, float]: Values by day (YYYY-MM-DD).

    Raises:
        ValueError: If the file has no series list.
    """
    pairs = data.get("series") if isinstance(data, dict) else None
    if not isinstance(pairs, list):
        raise ValueError("the file has no series list")
    values: dict[str, float] = {}
    for pair in pairs:
        if not isinstance(pair, list) or len(pair) != 2:
            continue
        value = parse_value(pair[1])
        if value is None:
            continue
        day = smard_day(pair[0])
        if day < before:
            values[day.isoformat()] = value
    return values


def fetch_series(ctx: RunContext, series: Series, stored: dict[str, float]) -> SeriesData:
    """Fetches the daily values of a series and merges them with the stored older values.

    Args:
        ctx: The run context.
        series: The catalog series.
        stored: Values stored at the previous observation.

    Returns:
        SeriesData: The complete series: stored values before the first fetched file, fetched values after.

    Raises:
        FetchError: If a request fails.
        ValueError: If the key or a response is invalid.
    """
    filter_id, _, region = series.key.partition("/")
    if not filter_id.isdigit() or not region:
        raise ValueError(f"SMARD key {series.key!r} must be <filter>/<region>")
    base = f"{BASE_URL}/{filter_id}/{region}"
    index = ctx.web.get(f"{base}/index_{RESOLUTION}.json", respect_robots=False).json()
    timestamps = sorted(stamp for stamp in (index.get("timestamps") or []) if isinstance(stamp, (int, float)))
    if not timestamps:
        raise ValueError("the index lists no files")
    selected = timestamps[-RECENT_FILES:] if stored else timestamps
    fetched: dict[str, float] = {}
    for stamp in selected:
        url = f"{base}/{filter_id}_{region}_{RESOLUTION}_{int(stamp)}.json"
        fetched.update(parse_values(ctx.web.get(url, respect_robots=False).json(), ctx.today))
    first_fetched = smard_day(selected[0]).isoformat()
    values = {period: value for period, value in stored.items() if period < first_fetched}
    values.update(fetched)
    return SeriesData(values=values, url=f"{base}/index_{RESOLUTION}.json")


class ElectricityCollector(Collector):
    """Writes vintages of the SMARD electricity series of the catalog."""
    name = "electricity"
    datasets = (DATASET,)

    def __init__(self, catalog_path: Path = CONFIG_PATH) -> None:
        """Initializes the collector.

        Args:
            catalog_path: The series catalog.
        """
        self._catalog_path = catalog_path

    def collect(self, ctx: RunContext, entry: CollectorEntry) -> CollectorResult:
        """Fetches every SMARD series of the catalog and emits the new and revised days.

        Args:
            ctx: The run context.
            entry: Run history of this collector.

        Returns:
            CollectorResult: Counters.
        """
        catalog = active_series(PROVIDER, self._catalog_path)
        writer = SeriesWriter(ctx, SOURCE_ID, LICENSE)
        return collect_series(ctx, catalog, lambda series: fetch_series(ctx, series, writer.stored_values(series)),
                              writer, "SMARD")
