"""Tests of the company registry and the resolution of company names."""
from pathlib import Path

import pytest

from companies import CompanyIndex, RegistryError, active_companies, load_registry, normalize_name
from conftest import COMPANIES_FIXTURE

ENTRY = """
[[company]]
id = "acme"
name = "Acme"
sector = "Chemicals"
country = "DE"
listed = true
isin = "DE0001234567"
wikidata = "Q1"
added = 2026-10-25
"""


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "companies.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_normalize_name_folds_umlauts_and_drops_legal_forms() -> None:
    assert normalize_name("Münchener Rück AG") == "muenchener rueck"
    assert normalize_name("Porsche SE", strip_legal_forms=False) == "porsche se"
    assert normalize_name("E.ON SE") == "e on"
    assert normalize_name("Merck & Co.") == "merck co"


@pytest.mark.parametrize("name, expected", [
    ("Volkswagen AG", "volkswagen"), ("VW", "volkswagen"), ("Porsche", "porsche_ag"), ("Porsche AG", "porsche_ag"),
    ("Porsche SE", "porsche_se"), ("Lidl", "schwarz_gruppe"), ("Schwarz-Gruppe", "schwarz_gruppe"),
    ("Old Company", None), ("Unknown GmbH", None), ("AG", None),
])
def test_index_resolves_names_with_and_without_legal_forms(name: str, expected) -> None:
    assert CompanyIndex(load_registry(COMPANIES_FIXTURE)).resolve(name) == expected


def test_removed_companies_are_not_active() -> None:
    assert "old_company" not in [company.id for company in active_companies(COMPANIES_FIXTURE)]


@pytest.mark.parametrize("change, message", [
    (('sector = "Chemicals"', 'sector = "Rockets"'), "unknown sector"),
    (('country = "DE"', 'country = "Germany"'), "country"),
    (('isin = "DE0001234567"', 'isin = "123"'), "not an ISIN"),
    (('listed = true', 'listed = false'), "unlisted company has no isin"),
    (('wikidata = "Q1"', 'wikidata = "1"'), "not a Wikidata id"),
    (('id = "acme"', 'id = "Acme"'), "snake_case"),
    (('added = 2026-10-25', 'added = 2026-10-25\nremoved = 2026-10-26'), "removed and removed_reason"),
])
def test_invalid_entries_are_rejected(tmp_path, change: tuple[str, str], message: str) -> None:
    with pytest.raises(RegistryError, match=message):
        load_registry(write(tmp_path, ENTRY.replace(*change)))


def test_names_must_belong_to_one_company(tmp_path) -> None:
    other = ENTRY.replace('id = "acme"', 'id = "acme_two"').replace('"DE0001234567"', '"DE0007654321"').replace(
        '"Q1"', '"Q2"')
    with pytest.raises(RegistryError, match="several companies"):
        load_registry(write(tmp_path, ENTRY + other))


def test_repository_registry_is_valid() -> None:
    companies = load_registry()
    assert len(companies) >= 100
    assert all(company.wikidata for company in companies)
    index = CompanyIndex(companies)
    assert index.resolve("Deutsche Post") == "dhl_group"
    assert index.resolve("Merck & Co.") is None
