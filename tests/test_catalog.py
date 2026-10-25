"""Tests of the series catalog."""
from pathlib import Path

import pytest

from catalog import CatalogError, active_series, load_catalog
from conftest import CATALOG_FIXTURE

ENTRY = """
[[series]]
concept = "gdp_real_qoq"
name = "GDP"
topic = "output_and_demand"
frequency = "Q"
unit = "percent"
provider = "eurostat"
flow = "namq_10_gdp"
key = "Q.CLV_PCH_PRE.SCA.B1GQ.{geo}"
geos = ["DE", "EA"]
added = 2026-10-25
"""


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "series.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_entries_are_expanded_per_geo_with_provider_codes() -> None:
    catalog = {series.series_id: series for series in load_catalog(CATALOG_FIXTURE)}
    assert catalog["hicp_inflation_yoy.DE"].key == "M.RCH_A.TOTAL.DE"
    # The euro area is EA in the series id and EA21 in the Eurostat key of this entry
    assert catalog["hicp_inflation_yoy.EA"].key == "M.RCH_A.TOTAL.EA21"
    assert catalog["eur_usd.EA"].key == "D.USD.EUR.SP00.A"
    assert catalog["old_series.DE"].active is False


def test_ecb_keys_write_the_euro_area_as_u2(tmp_path) -> None:
    text = ENTRY.replace('"eurostat"', '"ecb"').replace('"namq_10_gdp"', '"BSI"').replace(
        "Q.CLV_PCH_PRE.SCA.B1GQ.{geo}", "M.{geo}.Y.V.M30.X.I.U2.2300.Z01.A")
    catalog = {series.series_id: series.key for series in load_catalog(write(tmp_path, text))}
    assert catalog == {"gdp_real_qoq.DE": "M.DE.Y.V.M30.X.I.U2.2300.Z01.A",
                       "gdp_real_qoq.EA": "M.U2.Y.V.M30.X.I.U2.2300.Z01.A"}


def test_active_series_filters_by_provider() -> None:
    assert [series.series_id for series in active_series("smard", CATALOG_FIXTURE)] == ["day_ahead_power_price.DE"]
    assert "old_series.DE" not in [series.series_id for series in active_series(path=CATALOG_FIXTURE)]


@pytest.mark.parametrize("change, message", [
    (("topic = \"output_and_demand\"", "topic = \"weather\""), "unknown topic"),
    (("frequency = \"Q\"", "frequency = \"H\""), "unknown frequency"),
    (("provider = \"eurostat\"", "provider = \"imf\""), "unknown provider"),
    (("geos = [\"DE\", \"EA\"]", "geo = \"DE\""), "needs geos"),
    (("geos = [\"DE\", \"EA\"]", "geos = [\"Germany\"]"), "invalid geo codes"),
    (("added = 2026-10-25", "added = \"yesterday\""), "added must be a date"),
    (("added = 2026-10-25", "added = 2026-10-25\nremoved = 2026-10-26"), "removed and removed_reason"),
    (("added = 2026-10-25", "added = 2026-10-25\ncolour = \"red\""), "unknown keys"),
    (("geos = [\"DE\", \"EA\"]", "geos = [\"DE\", \"EA\"]\ngeo_codes = { FR = \"FR\" }"), "geo_codes for geos"),
])
def test_invalid_entries_are_rejected(tmp_path, change: tuple[str, str], message: str) -> None:
    with pytest.raises(CatalogError, match=message):
        load_catalog(write(tmp_path, ENTRY.replace(*change)))


def test_duplicate_series_ids_and_keys_are_rejected(tmp_path) -> None:
    with pytest.raises(CatalogError, match="duplicate series id"):
        load_catalog(write(tmp_path, ENTRY + ENTRY))


def test_repository_catalog_is_valid() -> None:
    catalog = load_catalog()
    assert len(catalog) > 200
    assert all(series.added for series in catalog)
