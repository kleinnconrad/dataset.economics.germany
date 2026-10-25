"""Tests of the README overview generator."""
from datetime import datetime, timezone

import pytest

from conftest import CATALOG_FIXTURE, COMPANIES_FIXTURE, SOURCES_FIXTURE
from generate_dataset_overview import END_MARKER, START_MARKER, build_overview, update_readme
from state import append_run_log
from storage import dumps_records, partition_file

NOW = datetime(2026, 10, 27, 3, 0, tzinfo=timezone.utc)


def write(data_dir, dataset: str, records: list[dict]) -> None:
    path = partition_file(data_dir, dataset, NOW.date())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_records(records), encoding="utf-8")


def overview_of(data_dir, config_path=SOURCES_FIXTURE) -> str:
    return build_overview(data_dir, config_path, now=NOW, catalog_path=CATALOG_FIXTURE,
                          registry_path=COMPANIES_FIXTURE)


def test_build_overview_counts_records_series_companies_and_annotations(tmp_path) -> None:
    data_dir = tmp_path / "data"
    write(data_dir, "economic_series", [
        {"record_id": "series:eur_usd.EA", "revision": 0, "series_id": "eur_usd.EA", "observed_at": "2026-10-27T01:00:00Z",
         "first_period": "1999-01-04", "last_period": "2026-10-23", "observations": 7121},
        {"record_id": "series:eur_usd.EA", "revision": 1, "series_id": "eur_usd.EA", "observed_at": "2026-10-27T01:00:00Z",
         "first_period": "1999-01-04", "last_period": "2026-10-26", "observations": 7122},
    ])
    write(data_dir, "news_items", [{"record_id": "news:a", "observed_at": "2026-10-27T01:00:00Z",
                                    "source_id": "news_example", "published_at": "2026-10-26T22:00:00Z",
                                    "content_basis": "lead_text", "keywords": ["DAX", "Börse"]},
                                   {"record_id": "news:b", "observed_at": "2026-10-27T01:00:00Z",
                                    "source_id": "news_example", "content_basis": "title_only", "keywords": []}])
    write(data_dir, "text_annotations", [{"record_id": "annotation:news:a:x", "item_id": "news:a",
                                          "observed_at": "2026-10-27T01:00:00Z", "is_economic": True,
                                          "topic": "Energy", "mentioned_companies": ["volkswagen"]}])
    append_run_log(data_dir / "state", {"started": "2026-10-27T01:07:00+00:00", "mode": "normal",
                                        "collectors": {"ecb": {"status": "ok", "records": {"economic_series": 2}}}})

    overview = overview_of(data_dir)

    assert "| `economic_series` | 2 | 1 | 1 | 2026-10-27 to 2026-10-27 |" in overview
    assert "- **Active series:** 7 (eurostat 2, worldbank_cmo 2, ecb 1, bundesbank 1, smard 1); with stored values: 1" \
        in overview
    assert "| `eur_usd.EA` | exchange rates | D | US dollar per euro | 1999-01-04 | 2026-10-26 | 7,122 | 1 |" in overview
    assert "- **Registered companies:** 4 (3 listed, 4 with headquarters in Germany)" in overview
    assert "| Volkswagen | 1 |" in overview
    assert "**Annotated items:** 1 of 2 (50.0%)" in overview
    assert "| Energy | 1 | 100.0% |" in overview
    assert "- **News outlets:** 2 configured (2 active)" in overview
    assert "`ecb`: ok (economic_series 2)" in overview
    assert "| News Example | national daily | active | 2 | 2 | 50.0% (1) | 50.0% (1) | 2026-10-26 |" in overview
    assert "| `keywords` | Keywords from the article page or the news sitemap. | 50.0% (1) | 2 |" in overview
    assert "<summary><code>companies</code>" not in overview


def test_update_readme_replaces_only_the_marked_section(tmp_path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(f"# Title\n{START_MARKER}\nold\n{END_MARKER}\nrest\n", encoding="utf-8")

    assert update_readme(readme, "new") is True
    assert readme.read_text(encoding="utf-8") == f"# Title\n{START_MARKER}\nnew\n{END_MARKER}\nrest\n"
    assert update_readme(readme, "new") is False


def test_update_readme_requires_markers(tmp_path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Title\n", encoding="utf-8")
    with pytest.raises(ValueError):
        update_readme(readme, "x")


def test_removed_sources_are_counted_as_removed(tmp_path) -> None:
    config = SOURCES_FIXTURE.read_text(encoding="utf-8").replace('id = "trade_example"',
                                                                 'id = "trade_example"\nremoved = 2026-10-26')
    config_path = tmp_path / "sources.toml"
    config_path.write_text(config, encoding="utf-8")

    overview = overview_of(tmp_path / "data", config_path)

    assert "- **News outlets:** 2 configured (1 active, 1 removed)" in overview
    assert "| Trade Example | trade press | removed | 0 |" in overview


def test_overview_without_data(tmp_path) -> None:
    overview = overview_of(tmp_path / "data")
    assert "- No run yet." in overview
    assert "| `news_items` | 0 | 0 | 0 | none |" in overview
    assert "with stored values: 0" in overview
