"""Tests of the vintage records of statistical series."""
from dataclasses import replace

import pytest

from catalog import load_catalog
from collectors.series import (
    IncompleteSeriesError,
    SeriesData,
    SeriesWriter,
    normalize_period,
    parse_value,
    period_delta,
)
from conftest import CATALOG_FIXTURE

SERIES = next(series for series in load_catalog(CATALOG_FIXTURE) if series.series_id == "hicp_inflation_yoy.DE")


@pytest.mark.parametrize("raw, frequency, expected", [
    ("2026-09", "M", "2026-09"),
    ("2026M09", "M", "2026-09"),
    ("2026M9", "M", "2026-09"),
    ("2026-Q3", "Q", "2026-Q3"),
    ("2026Q3", "Q", "2026-Q3"),
    ("2026-S1", "S", "2026-S1"),
    ("2026", "A", "2026"),
    ("2026-W05", "W", "2026-W05"),
    ("2026-10-23", "D", "2026-10-23"),
    ("2026-10", "Q", None),
    ("garbage", "M", None),
])
def test_normalize_period(raw: str, frequency: str, expected) -> None:
    assert normalize_period(raw, frequency) == expected


@pytest.mark.parametrize("raw, expected", [("2.25", 2.25), (3, 3.0), ("", None), ("NaN", None), (None, None),
                                           ("…", None), (True, None), (float("inf"), None)])
def test_parse_value(raw, expected) -> None:
    assert parse_value(raw) == expected


def test_period_delta_lists_added_changed_and_removed_periods() -> None:
    changed, removed = period_delta({"2026-07": 1.0, "2026-08": 2.0, "2026-09": 3.0},
                                    {"2026-08": 2.5, "2026-09": 3.0, "2026-10": 4.0})
    assert changed == {"2026-08": 2.5, "2026-10": 4.0}
    assert removed == ["2026-07"]


def test_first_observation_holds_all_values_and_later_revisions_only_changes(make_ctx) -> None:
    ctx = make_ctx()
    writer = SeriesWriter(ctx, "eurostat", "Eurostat")
    values = {f"2026-{month:02d}": float(month) for month in range(1, 10)}
    first = writer.build(SERIES, SeriesData(values=dict(values), url="https://x.example/1"))
    assert first is not None and first.revision == 0 and first.backfilled
    assert first.values == values and first.first_period == "2026-01" and first.last_period == "2026-09"
    assert first.observations == 9
    assert writer.build(SERIES, SeriesData(values=dict(values), url="https://x.example/1")) is None

    revised = {**values, "2026-09": 9.5, "2026-10": 10.0}
    second = writer.build(SERIES, SeriesData(values=revised, url="https://x.example/1"))
    assert second is not None and second.revision == 1 and not second.backfilled
    assert second.values == {"2026-09": 9.5, "2026-10": 10.0}
    assert second.removed_periods == [] and second.observations == 10


def test_response_that_drops_many_periods_is_not_written(make_ctx) -> None:
    ctx = make_ctx()
    writer = SeriesWriter(ctx, "eurostat", "Eurostat")
    values = {f"20{year:02d}": float(year) for year in range(10, 30)}
    annual = replace(SERIES, frequency="A")
    writer.build(annual, SeriesData(values=values, url="u"))
    with pytest.raises(IncompleteSeriesError):
        writer.build(annual, SeriesData(values={"2029": 29.0}, url="u"))
    # A single removed period is a normal revision
    trimmed = {period: value for period, value in values.items() if period != "2010"}
    record = writer.build(annual, SeriesData(values=trimmed, url="u"))
    assert record is not None and record.removed_periods == ["2010"] and record.values == {}


def test_new_series_without_values_is_not_written(make_ctx) -> None:
    writer = SeriesWriter(make_ctx(), "eurostat", "Eurostat")
    assert writer.build(SERIES, SeriesData(values={}, url="u")) is None
