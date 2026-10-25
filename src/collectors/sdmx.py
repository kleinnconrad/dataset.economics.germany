"""
Collects statistical series from the SDMX 2.1 REST interfaces of Eurostat, the ECB and the Bundesbank.

Sources:
- Eurostat dissemination API (``ec.europa.eu/eurostat/api/dissemination/sdmx/2.1``): national
  accounts, HICP, short-term business statistics, labour market, business and consumer surveys
  (European Commission, DG ECFIN), government finance, house and energy prices. Eurostat
  authorises the reuse of its data provided the source is acknowledged.
- ECB Data Portal (``data-api.ecb.europa.eu``): key interest rates, euro short-term rate,
  Euribor, yield curves, long-term interest rates, MFI interest rates, monetary aggregates,
  exchange rates and the Composite Indicator of Systemic Stress. ECB statistics may be reused
  free of charge provided the source is acknowledged.
- Deutsche Bundesbank time series database (``api.statistiken.bundesbank.de``): yields of
  Federal securities, new orders, the truck toll mileage index, the weekly activity index,
  national consumer prices, negotiated wages and labour market data of the Federal Employment
  Agency. The Bundesbank permits the reuse of its time series with attribution of the source;
  series that the Bundesbank redistributes keep the attribution of their original compiler,
  which is stored in ``original_source``.

All three interfaces are documented APIs without a key; they are called with
``respect_robots=False`` and at most one request per second per host.

Fetch strategy: one request per catalog series, with the exact SDMX series key of the catalog
and the response format SDMX-CSV, which all three providers offer. The CSV has one row per
observation; ``TIME_PERIOD`` and ``OBS_VALUE`` are the period and the value. A key that matches
no series returns HTTP 404 (the series was discontinued or the key is wrong); a key that
matches several series is rejected.

Records: vintages of each series in ``economic_series`` (see ``collectors/series.py``).

History: all periods that the provider publishes, on the first run.

Schedule: every run, because statistics are released on many days of the month and
``observed_at`` should be close to the release. At the run deadline the collector stops; the
remaining series follow in the next run.
"""
import csv
import io
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar, Optional

from catalog import CONFIG_PATH, Series, active_series
from collectors.base import Collector, CollectorResult, RunContext
from collectors.series import DATASET, IncompleteSeriesError, SeriesData, SeriesWriter, normalize_period, parse_value
from state import CollectorEntry
from web import BlockedError, FetchError, NotFoundError, RateLimitError

logger = logging.getLogger(__name__)

# Columns that carry a series title or the original compiler, by provider
TITLE_COLUMNS = ("TITLE", "BBK_TITLE")
SOURCE_COLUMNS = ("BBK_COMM_SRC",)
# Eurostat states the last update of a dataset in this column, e.g. 06/02/26 23:00:00
LAST_UPDATE_COLUMN = "LAST UPDATE"
# Columns before TIME_PERIOD that do not identify a series
NON_KEY_COLUMNS = frozenset({LAST_UPDATE_COLUMN})
REQUEST_TIMEOUT_S = 60.0


@dataclass(frozen=True)
class SdmxProvider:
    """An SDMX 2.1 REST interface.

    Attributes:
        name (str): Provider name in the catalog and collector name.
        source_id (str): Source id stored in the records.
        license (str): License or terms stored in the records.
        url_template (str): URL of a series with the placeholders ``{flow}`` and ``{key}``.
        params (tuple): Query parameters that select SDMX-CSV.
        headers (tuple): Request headers that select SDMX-CSV.
    """
    name: str
    source_id: str
    license: str
    url_template: str
    params: tuple[tuple[str, str], ...] = ()
    headers: tuple[tuple[str, str], ...] = ()

    def url(self, series: Series) -> str:
        """Returns the request URL of a series without the format parameters."""
        return self.url_template.format(flow=series.flow, key=series.key)


EUROSTAT = SdmxProvider(
    name="eurostat", source_id="eurostat", license="Eurostat (reuse authorised with acknowledgement of the source)",
    url_template="https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/{flow}/{key}",
    params=(("format", "SDMX-CSV"),),
)
ECB = SdmxProvider(
    name="ecb", source_id="ecb_data_portal", license="ECB (reuse free of charge with acknowledgement of the source)",
    url_template="https://data-api.ecb.europa.eu/service/data/{flow}/{key}",
    params=(("format", "csvdata"),),
)
BUNDESBANK = SdmxProvider(
    name="bundesbank", source_id="bundesbank", license="Deutsche Bundesbank (reuse with attribution of the source)",
    url_template="https://api.statistiken.bundesbank.de/rest/data/{flow}/{key}",
    headers=(("Accept", "application/vnd.sdmx.data+csv;version=1.0.0"),),
)


def parse_timestamp(value: str) -> Optional[datetime]:
    """Parses the last-update column of Eurostat (``dd/mm/yy HH:MM:SS``, CET) or an ISO timestamp.

    Args:
        value: The text.

    Returns:
        Optional[datetime]: The time in UTC; Eurostat times without zone are taken as UTC. None if invalid.
    """
    text = value.strip()
    for parse in (lambda: datetime.strptime(text, "%d/%m/%y %H:%M:%S"), lambda: datetime.fromisoformat(text)):
        try:
            parsed = parse()
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return None


def parse_sdmx_csv(text: str, frequency: str) -> tuple[dict[str, float], dict[str, Optional[str]]]:
    """Reads the observations of one series from an SDMX-CSV response.

    The delimiter is a comma (Eurostat, ECB) or a semicolon (Bundesbank); a byte order mark
    is ignored. The series identity is the combination of the columns before ``TIME_PERIOD``.

    Args:
        text: The CSV text.
        frequency: Frequency of the series, used to normalize the periods.

    Returns:
        tuple: Values by normalized period, and metadata (title, original_source, last_update).

    Raises:
        ValueError: If the CSV has no TIME_PERIOD or OBS_VALUE column or contains several series.
    """
    text = text.lstrip("﻿")
    first_line = text.split("\n", 1)[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    columns = reader.fieldnames or []
    if "TIME_PERIOD" not in columns or "OBS_VALUE" not in columns:
        raise ValueError(f"not an SDMX-CSV response (columns: {', '.join(columns[:8])})")
    key_columns = [name for name in columns[:columns.index("TIME_PERIOD")] if name not in NON_KEY_COLUMNS]
    values: dict[str, float] = {}
    identities: set[tuple[str, ...]] = set()
    meta: dict[str, Optional[str]] = {"title": None, "original_source": None, "last_update": None}
    for row in reader:
        identities.add(tuple(row.get(name) or "" for name in key_columns))
        period = normalize_period(row.get("TIME_PERIOD") or "", frequency)
        value = parse_value(row.get("OBS_VALUE"))
        if period is not None and value is not None:
            values[period] = value
        for name in TITLE_COLUMNS:
            if meta["title"] is None and (row.get(name) or "").strip():
                meta["title"] = " ".join(str(row[name]).split())
        for name in SOURCE_COLUMNS:
            if meta["original_source"] is None and (row.get(name) or "").strip():
                meta["original_source"] = " ".join(str(row[name]).split()).rstrip(".")
        if meta["last_update"] is None and (row.get(LAST_UPDATE_COLUMN) or "").strip():
            meta["last_update"] = str(row[LAST_UPDATE_COLUMN])
    if len(identities) > 1:
        raise ValueError(f"the key matches {len(identities)} series; the catalog key must select one series")
    return values, meta


def fetch_series(ctx: RunContext, provider: SdmxProvider, series: Series) -> SeriesData:
    """Fetches all observations of a series.

    Args:
        ctx: The run context.
        provider: The SDMX interface.
        series: The catalog series.

    Returns:
        SeriesData: The values and metadata.

    Raises:
        NotFoundError: If the key matches no series.
        FetchError: If the request fails.
        ValueError: If the response is not a valid SDMX-CSV of one series.
    """
    url = provider.url(series)
    response = ctx.web.get(url, params=dict(provider.params) or None, headers=dict(provider.headers) or None,
                           respect_robots=False, timeout_s=REQUEST_TIMEOUT_S)
    values, meta = parse_sdmx_csv(response.text, series.frequency)
    return SeriesData(values=values, url=url, title=meta["title"], original_source=meta["original_source"],
                      source_updated=parse_timestamp(meta["last_update"]) if meta["last_update"] else None)


class SdmxCollector(Collector):
    """Writes vintages of the catalog series of one SDMX provider (set by the subclasses)."""
    datasets = (DATASET,)
    provider: ClassVar[SdmxProvider]

    def __init__(self, catalog_path: Path = CONFIG_PATH) -> None:
        """Initializes the collector.

        Args:
            catalog_path: The series catalog.
        """
        self._catalog_path = catalog_path

    def collect(self, ctx: RunContext, entry: CollectorEntry) -> CollectorResult:
        """Fetches every catalog series of the provider and emits the new and changed vintages.

        Args:
            ctx: The run context.
            entry: Run history of this collector.

        Returns:
            CollectorResult: Counters; an error if all series failed or the provider refused the requests.
        """
        catalog = active_series(self.provider.name, self._catalog_path)
        return collect_series(ctx, catalog, lambda series: fetch_series(ctx, self.provider, series),
                              SeriesWriter(ctx, self.provider.source_id, self.provider.license), self.provider.name)


class EurostatCollector(SdmxCollector):
    """Writes vintages of the Eurostat series of the catalog."""
    name = "eurostat"
    provider = EUROSTAT


class EcbCollector(SdmxCollector):
    """Writes vintages of the ECB series of the catalog."""
    name = "ecb"
    provider = ECB


class BundesbankCollector(SdmxCollector):
    """Writes vintages of the Bundesbank series of the catalog."""
    name = "bundesbank"
    provider = BUNDESBANK


def collect_series(ctx: RunContext, catalog: Sequence[Series], fetch: Callable[[Series], SeriesData],
                   writer: SeriesWriter, label: str) -> CollectorResult:
    """Fetches the series one after another and emits their vintages.

    Shared by the series collectors: a quota stops the collector until the next run, a refusal
    stops it with an error, and a single failing series is counted and skipped.

    Args:
        ctx: The run context.
        catalog: The series to fetch.
        fetch: Function that returns the ``SeriesData`` of a series.
        writer: The vintage writer.
        label: Name of the provider for the log.

    Returns:
        CollectorResult: Counters, completeness and an error message if needed.
    """
    counters: dict[str, Any] = {"series": len(catalog), "new": 0, "revised": 0, "unchanged": 0, "not_found": 0,
                                "failed": 0, "incomplete": 0, "values": 0}
    complete = True
    error: Optional[str] = None
    not_found: list[str] = []
    for position, series in enumerate(catalog):
        if ctx.past_deadline():
            counters["deferred"] = len(catalog) - position
            complete = False
            break
        try:
            data = fetch(series)
            record = writer.build(series, data)
        except RateLimitError as e:
            logger.warning("%s rate limit at %s; the remaining series follow in the next run: %s", label,
                           series.series_id, e)
            counters["deferred"] = len(catalog) - position
            complete = False
            break
        except BlockedError as e:
            logger.error("%s refused the request; no further requests in this run: %s", label, e)
            error = f"blocked: {e}"
            complete = False
            break
        except NotFoundError as e:
            logger.warning("%s series %s not found (discontinued or wrong key): %s", label, series.series_id, e)
            counters["not_found"] += 1
            not_found.append(series.series_id)
            continue
        except IncompleteSeriesError as e:
            logger.warning("%s series not written: %s", label, e)
            counters["incomplete"] += 1
            continue
        except (FetchError, ValueError, KeyError) as e:
            logger.warning("%s series %s failed: %s", label, series.series_id, e)
            counters["failed"] += 1
            continue
        if record is None:
            counters["unchanged"] += 1
            continue
        counters["new" if record.revision == 0 else "revised"] += 1
        counters["values"] += len(record.values)
        writer.emit(record)
    if not_found:
        counters["not_found_series"] = not_found
    attempted = counters["series"] - counters.get("deferred", 0)
    unavailable = counters["failed"] + counters["not_found"]
    if error is None and attempted and unavailable == attempted:
        error = f"all {attempted} series failed or were not found"
    logger.info("%s: %d new and %d revised series (%d values), %d unchanged, %d not found, %d failed.", label,
                counters["new"], counters["revised"], counters["values"], counters["unchanged"], counters["not_found"],
                counters["failed"])
    return CollectorResult(counters=counters, complete=complete, error=error)
