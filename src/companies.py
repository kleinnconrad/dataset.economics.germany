"""
The registry of companies (``config/companies.toml``) and the resolution of company names.

The registry lists large companies that the German economic press reports on: the members
of the DAX, further large German companies (listed and unlisted) and foreign companies with
a strong presence in German economic news. Every entry has a stable ``id``, the join key
``company_id`` of the datasets ``companies``, ``wikipedia_pageviews``, ``press_releases`` and
``text_annotations``, and the names under which the annotation resolves it (``name`` and
``aliases``).

Every entry has the date on which it was ``added``. An entry that is no longer tracked keeps
its place with the date on which it was ``removed`` and a ``removed_reason``; ids are never
reused. Index memberships are not stored, because they change; the ISIN identifies the main
share line of a listed company.
"""
import re
import tomllib
import unicodedata
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional, get_args

from schema import Sector

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "companies.toml"

ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
WIKIDATA_PATTERN = re.compile(r"^Q[1-9][0-9]*$")
ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
COUNTRY_PATTERN = re.compile(r"^[A-Z]{2}$")
KNOWN_KEYS = frozenset({"id", "name", "aliases", "sector", "country", "listed", "isin", "wikidata", "added",
                        "removed", "removed_reason"})
# Legal forms and generic words that are dropped before names are compared
# ("co" is kept, so that "Merck & Co." does not resolve to Merck KGaA)
LEGAL_FORMS = frozenset({
    "ag", "se", "kgaa", "gmbh", "kg", "mbh", "ohg", "eg", "group", "gruppe", "konzern", "holding", "holdings",
    "plc", "inc", "incorporated", "corp", "corporation", "ltd", "limited", "nv", "sa", "spa", "llc", "the", "und",
    "and",
})
MAX_NAME_CHARS = 80
MAX_OTHER_COMPANIES = 10


class RegistryError(ValueError):
    """The registry file contains invalid or duplicate entries."""


@dataclass(frozen=True)
class Company:
    """A company of the registry.

    Attributes:
        id (str): Stable id, lower-case snake_case; never reused.
        name (str): Name of the company or corporate group.
        sector (str): Main sector (see ``schema.Sector``).
        country (str): Country of the headquarters (ISO 3166-1 alpha-2).
        listed (bool): Whether the shares are listed on a stock exchange.
        added (date): Day on which the entry was added.
        aliases (tuple[str, ...]): Further names, e.g. brands or former names.
        isin (Optional[str]): ISIN of the main share line.
        wikidata (Optional[str]): Wikidata id; the German Wikipedia article is resolved from it.
        removed (Optional[date]): Day on which the entry was removed.
        removed_reason (Optional[str]): Why the entry was removed.
    """
    id: str
    name: str
    sector: str
    country: str
    listed: bool
    added: date
    aliases: tuple[str, ...] = ()
    isin: Optional[str] = None
    wikidata: Optional[str] = None
    removed: Optional[date] = None
    removed_reason: Optional[str] = None

    @property
    def active(self) -> bool:
        """True if the company is tracked, i.e. it was not removed."""
        return self.removed is None


def normalize_name(name: str, strip_legal_forms: bool = True) -> str:
    """Returns a comparison key for a company name.

    The key is lower case, without accents, with umlauts written as ae, oe, ue and ss, with
    punctuation replaced by spaces, and, by default, without legal forms such as AG, SE or GmbH.

    Args:
        name: The name.
        strip_legal_forms: Whether legal forms and generic words (LEGAL_FORMS) are removed.

    Returns:
        str: For example ``muenchener rueck`` for "Münchener Rück AG".
    """
    text = name.casefold()
    for umlaut, replacement in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(umlaut, replacement)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    words = re.sub(r"[^a-z0-9]+", " ", text.replace("&", " ")).split()
    return " ".join(word for word in words if not (strip_legal_forms and word in LEGAL_FORMS))


def clean_company_name(name: str) -> str:
    """Collapses whitespace and shortens a company name returned by the model.

    Args:
        name: The name.

    Returns:
        str: The cleaned name, at most MAX_NAME_CHARS characters.
    """
    return " ".join(name.split())[:MAX_NAME_CHARS]


def _str_list(raw: dict[str, Any], key: str) -> tuple[str, ...]:
    """Reads an optional list of non-empty strings."""
    values = raw.get(key, [])
    if not isinstance(values, list) or not all(isinstance(value, str) and value.strip() for value in values):
        raise ValueError(f"{key} must be a list of non-empty strings")
    return tuple(value.strip() for value in values)


def _optional_str(raw: dict[str, Any], key: str) -> Optional[str]:
    """Reads an optional non-empty string."""
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def _optional_date(raw: dict[str, Any], key: str) -> Optional[date]:
    """Reads an optional TOML date."""
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, date) or isinstance(value, datetime):
        raise ValueError(f"{key} must be a date (YYYY-MM-DD)")
    return value


def parse_company(raw: dict[str, Any]) -> Company:
    """Validates one registry entry.

    Args:
        raw: The entry as read from TOML.

    Returns:
        Company: The parsed entry.

    Raises:
        ValueError: If a field is missing, unknown or invalid.
    """
    unknown = sorted(set(raw) - KNOWN_KEYS)
    if unknown:
        raise ValueError(f"unknown keys: {', '.join(unknown)}")
    company_id = _optional_str(raw, "id")
    if company_id is None or not ID_PATTERN.match(company_id):
        raise ValueError("id must be lower-case snake_case")
    name = _optional_str(raw, "name")
    if name is None:
        raise ValueError("name is missing")
    sector = raw.get("sector")
    if sector not in get_args(Sector):
        raise ValueError(f"unknown sector {sector!r}")
    country = _optional_str(raw, "country")
    if country is None or not COUNTRY_PATTERN.match(country):
        raise ValueError("country must be an ISO 3166-1 alpha-2 code")
    listed = raw.get("listed")
    if not isinstance(listed, bool):
        raise ValueError("listed must be true or false")
    isin = _optional_str(raw, "isin")
    if isin is not None and not ISIN_PATTERN.match(isin):
        raise ValueError(f"isin {isin!r} is not an ISIN")
    if isin is not None and not listed:
        raise ValueError("an unlisted company has no isin")
    wikidata = _optional_str(raw, "wikidata")
    if wikidata is not None and not WIKIDATA_PATTERN.match(wikidata):
        raise ValueError(f"wikidata {wikidata!r} is not a Wikidata id")
    added = _optional_date(raw, "added")
    if added is None:
        raise ValueError("added is missing")
    removed = _optional_date(raw, "removed")
    removed_reason = _optional_str(raw, "removed_reason")
    if (removed is None) != (removed_reason is None):
        raise ValueError("removed and removed_reason must be given together")
    return Company(id=company_id, name=name, sector=sector, country=country, listed=listed, added=added,
                   aliases=_str_list(raw, "aliases"), isin=isin, wikidata=wikidata, removed=removed,
                   removed_reason=removed_reason)


def _duplicate_problems(companies: Sequence[Company]) -> list[str]:
    """Returns a message for every id, identifier or name that occurs in more than one entry."""
    identifiers: dict[str, list[str]] = {
        "id": [company.id for company in companies],
        "isin": [company.isin for company in companies if company.isin],
        "wikidata": [company.wikidata for company in companies if company.wikidata],
    }
    problems = []
    for key, values in identifiers.items():
        duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
        if duplicates:
            problems.append(f"duplicate {key}: {', '.join(duplicates)}")
    owners: dict[str, set[str]] = {}
    for company in companies:
        for name in (company.name, *company.aliases):
            owners.setdefault(normalize_name(name, strip_legal_forms=False), set()).add(company.id)
    shared = sorted(f"{name!r} ({', '.join(sorted(ids))})" for name, ids in owners.items() if len(ids) > 1)
    if shared:
        problems.append(f"names that resolve to several companies: {', '.join(shared)}")
    empty = sorted(company.id for company in companies
                   if any(not normalize_name(name) for name in (company.name, *company.aliases)))
    if empty:
        problems.append(f"names without letters or digits after normalization: {', '.join(empty)}")
    return problems


def load_registry(path: Path = CONFIG_PATH) -> list[Company]:
    """Reads and validates the registry.

    Args:
        path: The registry file.

    Returns:
        list[Company]: All entries in file order, including removed ones.

    Raises:
        RegistryError: If an entry is invalid or an id, identifier or name is duplicated.
    """
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    entries = data.get("company", [])
    if not isinstance(entries, list):
        raise RegistryError(f"{path} must contain [[company]] entries")
    companies: list[Company] = []
    problems: list[str] = []
    for position, raw in enumerate(entries, start=1):
        try:
            companies.append(parse_company(raw))
        except ValueError as e:
            problems.append(f"entry {position} ({raw.get('id', '?')}): {e}")
    problems.extend(_duplicate_problems(companies))
    if problems:
        raise RegistryError(f"{path}: " + "; ".join(problems))
    return companies


def active_companies(path: Path = CONFIG_PATH) -> list[Company]:
    """Returns the companies that are tracked, i.e. not removed.

    Args:
        path: The registry file.

    Returns:
        list[Company]: The active entries in file order.
    """
    return [company for company in load_registry(path) if company.active]


class CompanyIndex:
    """Resolves company names returned by the model against the registry.

    A name is compared in two steps: first with its legal form (so that "Porsche SE" and "Porsche"
    stay apart), then without legal forms (so that "Volkswagen AG" finds "Volkswagen"). A key of
    the second step that belongs to several companies is not used.
    """

    def __init__(self, companies: Iterable[Company]) -> None:
        """Builds the index from the names and aliases of the active companies.

        Args:
            companies: The registry entries; removed entries are ignored.
        """
        self._full: dict[str, str] = {}
        stripped: dict[str, set[str]] = {}
        for company in companies:
            if not company.active:
                continue
            for name in (company.name, *company.aliases):
                self._full[normalize_name(name, strip_legal_forms=False)] = company.id
                stripped.setdefault(normalize_name(name), set()).add(company.id)
        self._stripped = {key: next(iter(ids)) for key, ids in stripped.items() if len(ids) == 1}

    def __len__(self) -> int:
        return len(set(self._full.values()))

    def resolve(self, name: str) -> Optional[str]:
        """Returns the registry id of a company name.

        Args:
            name: Name as returned by the model.

        Returns:
            Optional[str]: The id if the name, with or without its legal form, equals the name or an
            alias of exactly one registered company; None otherwise.
        """
        full = normalize_name(name, strip_legal_forms=False)
        if full in self._full:
            return self._full[full]
        key = normalize_name(name)
        return self._stripped.get(key) if key else None
