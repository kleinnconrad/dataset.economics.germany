"""Tests of the collectors that write the series catalog and the company registry."""
from collectors.registries import CompaniesCollector, SeriesCatalogCollector
from conftest import CATALOG_FIXTURE, COMPANIES_FIXTURE, read_dataset
from state import CollectorEntry


def test_catalog_entries_are_written_once_and_again_after_a_change(make_ctx, tmp_path) -> None:
    ctx = make_ctx()
    entry = CollectorEntry(first_run=ctx.today)
    result = SeriesCatalogCollector(CATALOG_FIXTURE).collect(ctx, entry)
    assert result.counters == {"items": 8, "new": 8, "changed": 0}
    records = read_dataset(tmp_path / "data", "series_catalog")
    by_id = {record["series_id"]: record for record in records}
    assert by_id["hicp_inflation_yoy.EA"]["provider_key"] == "M.RCH_A.TOTAL.EA21"
    assert by_id["old_series.DE"]["removed"] == "2026-10-26"
    assert all(record["license"].startswith("Configuration of this project") for record in records)

    assert SeriesCatalogCollector(CATALOG_FIXTURE).collect(make_ctx(), entry).counters["new"] == 0
    changed = tmp_path / "series.toml"
    changed.write_text(CATALOG_FIXTURE.read_text(encoding="utf-8").replace('unit = "euro per MWh"',
                                                                             'unit = "EUR per MWh"'), encoding="utf-8")
    result = SeriesCatalogCollector(changed).collect(make_ctx(), entry)
    assert result.counters["changed"] == 1
    revisions = [r for r in read_dataset(tmp_path / "data", "series_catalog") if r["revision"] == 1]
    assert [r["series_id"] for r in revisions] == ["day_ahead_power_price.DE"]


def test_companies_are_written_with_their_identifiers(make_ctx, tmp_path) -> None:
    ctx = make_ctx()
    CompaniesCollector(COMPANIES_FIXTURE).collect(ctx, CollectorEntry(first_run=ctx.today))
    records = {record["company_id"]: record for record in read_dataset(tmp_path / "data", "companies")}
    assert records["volkswagen"]["aliases"] == ["VW"]
    assert records["volkswagen"]["isin"] == "DE0007664039"
    assert records["schwarz_gruppe"]["listed"] is False
    assert records["old_company"]["removed_reason"] == "merged"
