"""
Writes vintages of statistical series to the dataset ``economic_series``.

All series collectors (Eurostat, ECB, Bundesbank, World Bank commodity
prices, SMARD) fetch the complete values of a catalog series, or its recent
part, and pass them to ``SeriesWriter``. The writer compares them with the
values stored at the previous observation and emits a record only if
something changed:

- revision 0 holds all periods of the series (the first observation);
- a later revision holds the periods that were added or whose value changed,
  and lists the periods whose value disappeared in ``removed_periods``.

Replaying the revisions of a series in the order of ``observed_at`` gives the
series as it was known at any time t (a real-time data set), which avoids
look-ahead bias in models trained on revised data.

The current values of every series are kept in the seen store, one shard per
series (``state/seen/economic_series/<series_id>.json``), so that a run
rewrites only the shards of the series that changed. A response that would
remove more than MAX_REMOVED_SHARE of the stored periods is treated as
incomplete and not written.
"""
import logging
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from catalog import Series
from collectors.base import RunContext
from schema import EconomicSeriesRecord
from state import content_hash

logger = logging.getLogger(__name__)

DATASET = "economic_series"
# A response that removes more than this share of the stored periods (and more than MIN_SUSPICIOUS_REMOVALS)
# is treated as incomplete
MAX_REMOVED_SHARE = 0.05
MIN_SUSPICIOUS_REMOVALS = 3
PERIOD_PATTERNS: dict[str, re.Pattern[str]] = {
    "D": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "W": re.compile(r"^\d{4}-W\d{2}$"),
    "M": re.compile(r"^\d{4}-\d{2}$"),
    "Q": re.compile(r"^\d{4}-Q[1-4]$"),
    "S": re.compile(r"^\d{4}-S[12]$"),
    "A": re.compile(r"^\d{4}$"),
}
# Period formats of the providers that differ from the stored format: 2026M09, 2026Q3, 2026S1, 2026W05
_COMPACT_PERIOD = re.compile(r"^(\d{4})([MQSW])(\d{1,2})$")


class IncompleteSeriesError(Exception):
    """A response would remove too many stored periods; it is not written."""


@dataclass
class SeriesData:
    """The values of a series as fetched from the provider.

    Attributes:
        values (dict[str, float]): Values by normalized period.
        url (str): URL of the request, stored as ``source_url``.
        title (Optional[str]): Title of the series at the provider.
        original_source (Optional[str]): Original compiler of redistributed data.
        source_updated (Optional[datetime]): Last update of the dataset at the provider (UTC).
    """
    values: dict[str, float]
    url: str
    title: Optional[str] = None
    original_source: Optional[str] = None
    source_updated: Optional[datetime] = None


def normalize_period(raw: str, frequency: str) -> Optional[str]:
    """Converts a period of a provider to the stored format of its frequency.

    Args:
        raw: The period, e.g. ``2026-09``, ``2026M09``, ``2026-Q3`` or ``2026-10-23``.
        frequency: Frequency of the series (D, W, M, Q, S, A).

    Returns:
        Optional[str]: The period as YYYY-MM-DD, YYYY-Www, YYYY-MM, YYYY-Qn, YYYY-Sn or YYYY; None if the
        period does not match the frequency.
    """
    text = raw.strip()
    compact = _COMPACT_PERIOD.match(text)
    if compact:
        year, letter, number = compact.groups()
        text = f"{year}-{letter}{int(number)}" if letter in "QS" else f"{year}-{'W' if letter == 'W' else ''}{int(number):02d}"
    pattern = PERIOD_PATTERNS.get(frequency)
    return text if pattern is not None and pattern.match(text) else None


def parse_value(raw: Any) -> Optional[float]:
    """Parses an observation value.

    Args:
        raw: A number or a text such as ``2.25``; empty texts, ``NaN`` and markers of missing values give None.

    Returns:
        Optional[float]: The finite value, or None.
    """
    if isinstance(raw, bool) or raw is None:
        return None
    if isinstance(raw, (int, float)):
        value = float(raw)
    else:
        text = str(raw).strip()
        if not text:
            return None
        try:
            value = float(text)
        except ValueError:
            return None
    return value if math.isfinite(value) else None


def period_delta(previous: Mapping[str, float], current: Mapping[str, float]) -> tuple[dict[str, float], list[str]]:
    """Compares the stored values of a series with the current ones.

    Args:
        previous: Stored values by period.
        current: Current values by period.

    Returns:
        tuple: The added or changed values by period, and the periods whose value disappeared.
    """
    changed = {period: value for period, value in current.items() if previous.get(period) != value}
    removed = sorted(period for period in previous if period not in current)
    return changed, removed


class SeriesWriter:
    """Compares fetched series with the stored ones and builds the vintage records."""

    def __init__(self, ctx: RunContext, source_id: str, license: str) -> None:
        """Initializes the writer.

        Args:
            ctx: The run context.
            source_id: Id of the source, stored in every record.
            license: License or terms of the source.
        """
        self._ctx = ctx
        self._source_id = source_id
        self._license = license

    def stored_values(self, series: Series) -> dict[str, float]:
        """Returns the values of a series stored at the previous observation.

        Args:
            series: The catalog series.

        Returns:
            dict[str, float]: Values by period; empty for a new series.
        """
        entry = self._ctx.seen(DATASET, shard=series.series_id).get(series.series_id)
        return dict(entry.data.get("values") or {}) if entry else {}

    def build(self, series: Series, data: SeriesData) -> Optional[EconomicSeriesRecord]:
        """Builds the record of a new or changed series and stores its current values.

        Args:
            series: The catalog series.
            data: The fetched values.

        Returns:
            Optional[EconomicSeriesRecord]: The record, or None if nothing changed or the
            series has no values yet.

        Raises:
            IncompleteSeriesError: If the response would remove too many stored periods.
        """
        seen = self._ctx.seen(DATASET, shard=series.series_id)
        values = dict(sorted(data.values.items()))
        item_hash = content_hash(values)
        status = seen.classify(series.series_id, item_hash)
        if status == "unchanged" or (status == "new" and not values):
            return None
        stored = self.stored_values(series)
        changed, removed = period_delta(stored, values)
        if len(removed) > max(MIN_SUSPICIOUS_REMOVALS, MAX_REMOVED_SHARE * len(stored)):
            raise IncompleteSeriesError(f"{series.series_id}: the response lacks {len(removed)} of {len(stored)} "
                                        f"stored periods")
        revision = seen.mark(series.series_id, item_hash, self._ctx.today, data={"values": values})
        periods = list(values)
        return EconomicSeriesRecord(
            **self._ctx.envelope(DATASET, f"series:{series.series_id}", revision=revision, source_id=self._source_id,
                                 source_url=data.url, license=self._license, backfilled=revision == 0),
            series_id=series.series_id,
            concept=series.concept,
            topic=series.topic,
            geo=series.geo,
            frequency=series.frequency,
            unit=series.unit,
            provider=series.provider,
            provider_flow=series.flow,
            provider_key=series.key,
            provider_title=data.title,
            original_source=data.original_source,
            values=changed,
            removed_periods=removed,
            first_period=periods[0] if periods else None,
            last_period=periods[-1] if periods else None,
            observations=len(periods),
            source_updated=data.source_updated,
        )

    def emit(self, record: Optional[EconomicSeriesRecord]) -> None:
        """Writes a record together with the seen shard of its series.

        Args:
            record: The record; None writes nothing.
        """
        if record is not None:
            self._ctx.emit(DATASET, [record])
