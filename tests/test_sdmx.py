"""Tests of the SDMX collectors of Eurostat, the ECB and the Bundesbank with a fake web."""
import pytest

from collectors.sdmx import BundesbankCollector, EcbCollector, EurostatCollector, parse_sdmx_csv, parse_timestamp
from conftest import CATALOG_FIXTURE, read_dataset
from state import CollectorEntry

ECB_URL = "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A"
BBK_URL = "https://api.statistiken.bundesbank.de/rest/data/BBSIS/D.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A"
ESTAT_URL = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/prc_hicp_minr/M.RCH_A.TOTAL.{geo}"


def ecb_csv(rows: list[tuple[str, str]]) -> str:
    lines = ["KEY,FREQ,CURRENCY,TIME_PERIOD,OBS_VALUE,OBS_STATUS,TITLE"]
    lines += [f"EXR.D.USD.EUR.SP00.A,D,USD,{period},{value},A,US dollar/Euro ECB reference exchange rate"
              for period, value in rows]
    return "\n".join(lines) + "\n"


def bbk_csv(rows: list[tuple[str, str]]) -> str:
    lines = ["﻿DATAFLOW;BBK_STD_FREQ;TIME_PERIOD;OBS_VALUE;BBK_ID;BBK_TITLE;BBK_COMM_SRC"]
    lines += [f"BBK:BBSIS(1.0);D;{period};{value};BBSIS.D.I;Zinsstrukturkurve / 10,0 Jahr(e) RLZ;"
              f"Statistisches Bundesamt, Wiesbaden." for period, value in rows]
    return "\n".join(lines) + "\n"


def estat_csv(geo: str, rows: list[tuple[str, str]]) -> str:
    lines = ["DATAFLOW,LAST UPDATE,freq,unit,coicop18,geo,TIME_PERIOD,OBS_VALUE,OBS_FLAG,CONF_STATUS"]
    lines += [f"ESTAT:PRC_HICP_MINR(1.0),16/10/26 23:00:00,M,RCH_A,TOTAL,{geo},{period},{value},,"
              for period, value in rows]
    return "\n".join(lines) + "\n"


def test_parse_sdmx_csv_reads_comma_and_semicolon_files() -> None:
    values, meta = parse_sdmx_csv(ecb_csv([("2026-10-22", "1.12"), ("2026-10-23", "NaN")]), "D")
    assert values == {"2026-10-22": 1.12}
    assert meta["title"] == "US dollar/Euro ECB reference exchange rate"
    values, meta = parse_sdmx_csv(bbk_csv([("2026-10-23", "3.39")]), "D")
    assert values == {"2026-10-23": 3.39}
    assert meta["original_source"] == "Statistisches Bundesamt, Wiesbaden"
    values, meta = parse_sdmx_csv(estat_csv("DE", [("2026-09", "3.3")]), "M")
    assert values == {"2026-09": 3.3} and meta["last_update"] == "16/10/26 23:00:00"


def test_parse_sdmx_csv_rejects_several_series_and_other_formats() -> None:
    two = estat_csv("DE", [("2026-09", "3.3")]) + "ESTAT:PRC_HICP_MINR(1.0),16/10/26 23:00:00,M,RCH_A,TOTAL,FR,2026-09,3.4,,\n"
    with pytest.raises(ValueError, match="2 series"):
        parse_sdmx_csv(two, "M")
    with pytest.raises(ValueError, match="not an SDMX-CSV"):
        parse_sdmx_csv("<html>error</html>", "M")


def test_parse_timestamp_reads_the_eurostat_format() -> None:
    assert parse_timestamp("16/10/26 23:00:00").isoformat() == "2026-10-16T23:00:00+00:00"
    assert parse_timestamp("garbage") is None


def test_collectors_write_new_series_and_skip_unchanged_ones(make_ctx, fake_web, tmp_path) -> None:
    fake_web.add(ECB_URL, ecb_csv([("2026-10-22", "1.12"), ("2026-10-23", "1.11")]), content_type="text/csv")
    fake_web.add(BBK_URL, bbk_csv([("2026-10-23", "3.39")]), content_type="text/csv")
    fake_web.add(ESTAT_URL.format(geo="DE"), estat_csv("DE", [("2026-08", "3.1"), ("2026-09", "3.3")]),
                 content_type="text/csv")
    fake_web.add(ESTAT_URL.format(geo="EA21"), estat_csv("EA21", [("2026-09", "3.8")]), content_type="text/csv")
    ctx = make_ctx()
    entry = CollectorEntry(first_run=ctx.today)
    for collector in (EcbCollector(CATALOG_FIXTURE), BundesbankCollector(CATALOG_FIXTURE),
                      EurostatCollector(CATALOG_FIXTURE)):
        result = collector.collect(ctx, entry)
        assert result.error is None and result.complete
    records = {record["series_id"]: record for record in read_dataset(tmp_path / "data", "economic_series")}
    assert set(records) == {"eur_usd.EA", "bund_yield_10y.DE", "hicp_inflation_yoy.DE", "hicp_inflation_yoy.EA"}
    assert records["hicp_inflation_yoy.EA"]["provider_key"] == "M.RCH_A.TOTAL.EA21"
    assert records["hicp_inflation_yoy.DE"]["source_updated"] == "2026-10-16T23:00:00Z"
    assert records["bund_yield_10y.DE"]["original_source"] == "Statistisches Bundesamt, Wiesbaden"
    assert records["eur_usd.EA"]["license"].startswith("ECB")
    # The Bundesbank is asked for SDMX-CSV with the Accept header, the ECB with a query parameter
    assert any(url.startswith(ECB_URL + "?format=csvdata") for url in fake_web.requested)

    again = EcbCollector(CATALOG_FIXTURE).collect(make_ctx(), entry)
    assert again.counters["unchanged"] == 1 and again.counters["new"] == 0


def test_missing_series_is_counted_and_all_missing_is_an_error(make_ctx) -> None:
    ctx = make_ctx()
    result = EurostatCollector(CATALOG_FIXTURE).collect(ctx, CollectorEntry(first_run=ctx.today))
    assert result.counters["not_found"] == 2
    assert result.counters["not_found_series"] == ["hicp_inflation_yoy.DE", "hicp_inflation_yoy.EA"]
    assert result.error == "all 2 series failed or were not found"


def test_refusal_stops_the_collector_with_an_error(make_ctx, fake_web) -> None:
    fake_web.add(ESTAT_URL.format(geo="DE"), "forbidden", status=403)
    ctx = make_ctx()
    result = EurostatCollector(CATALOG_FIXTURE).collect(ctx, CollectorEntry(first_run=ctx.today))
    assert result.error is not None and result.error.startswith("blocked")
    assert not result.complete
