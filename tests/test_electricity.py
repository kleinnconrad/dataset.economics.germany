"""Tests of the SMARD electricity collector with a fake web."""
from datetime import date, datetime, timedelta, timezone

from collectors.electricity import BASE_URL, ElectricityCollector, parse_values, smard_day
from conftest import CATALOG_FIXTURE, RUN_STARTED, read_dataset
from state import CollectorEntry

BASE = f"{BASE_URL}/4169/DE-LU"


def berlin_midnight_ms(day: date) -> int:
    """Midnight Europe/Berlin of a day in milliseconds (CEST until the last Sunday of October)."""
    offset = 2 if date(day.year, 3, 29) <= day < date(day.year, 10, 25) else 1
    moment = datetime(day.year, day.month, day.day, tzinfo=timezone.utc) - timedelta(hours=offset)
    return int(moment.timestamp() * 1000)


def test_smard_day_converts_berlin_midnight_in_summer_and_winter() -> None:
    assert smard_day(berlin_midnight_ms(date(2026, 7, 1))) == date(2026, 7, 1)
    assert smard_day(berlin_midnight_ms(date(2026, 1, 1))) == date(2026, 1, 1)


def test_parse_values_skips_missing_values_and_the_current_day() -> None:
    data = {"series": [[berlin_midnight_ms(date(2026, 10, 25)), 13.12], [berlin_midnight_ms(date(2026, 10, 26)), None],
                       [berlin_midnight_ms(date(2026, 10, 27)), 116.57]]}
    assert parse_values(data, before=date(2026, 10, 27)) == {"2026-10-25": 13.12}


def test_collector_reads_all_files_first_and_then_the_newest_two(make_ctx, fake_web, tmp_path) -> None:
    years = [date(2024, 1, 1), date(2025, 1, 1), date(2026, 1, 1)]
    stamps = [berlin_midnight_ms(day) for day in years]
    fake_web.add(f"{BASE}/index_day.json", {"timestamps": stamps})
    for day, stamp in zip(years, stamps):
        fake_web.add(f"{BASE}/4169_DE-LU_day_{stamp}.json",
                     {"meta_data": {"version": 1}, "series": [[stamp, float(day.year - 2000)]]})
    ctx = make_ctx()
    entry = CollectorEntry(first_run=ctx.today)
    result = ElectricityCollector(CATALOG_FIXTURE).collect(ctx, entry)
    assert result.error is None and result.counters["new"] == 1
    record = read_dataset(tmp_path / "data", "economic_series")[0]
    assert record["values"] == {"2024-01-01": 24.0, "2025-01-01": 25.0, "2026-01-01": 26.0}
    assert record["license"] == "CC-BY-4.0 (Bundesnetzagentur | SMARD.de)"

    # The second run reads only the two newest files and keeps the older stored days
    fake_web.requested.clear()
    fake_web.add(f"{BASE}/4169_DE-LU_day_{stamps[2]}.json",
                 {"series": [[stamps[2], 26.5], [berlin_midnight_ms(date(2026, 1, 2)), 30.0]]})
    later = make_ctx(started=RUN_STARTED + timedelta(days=3))
    revised = ElectricityCollector(CATALOG_FIXTURE).collect(later, entry)
    assert revised.counters["revised"] == 1
    assert not any(str(stamps[0]) in url for url in fake_web.requested)
    second = [r for r in read_dataset(tmp_path / "data", "economic_series") if r["revision"] == 1][0]
    assert second["values"] == {"2026-01-01": 26.5, "2026-01-02": 30.0}
    assert second["removed_periods"] == [] and second["observations"] == 4


def test_invalid_key_is_counted_as_failed(make_ctx, tmp_path) -> None:
    catalog = tmp_path / "series.toml"
    catalog.write_text(CATALOG_FIXTURE.read_text(encoding="utf-8").replace('key = "4169/DE-LU"', 'key = "price"'),
                       encoding="utf-8")
    ctx = make_ctx()
    result = ElectricityCollector(catalog).collect(ctx, CollectorEntry(first_run=ctx.today))
    assert result.counters["failed"] == 1 and result.error is not None
