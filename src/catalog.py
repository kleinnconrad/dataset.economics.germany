"""
The catalog of statistical series (``config/series.toml``).

Every ``[[series]]`` entry describes one concept, e.g. the annual HICP
inflation rate, at one provider: the dataset or dataflow (``flow``), the
series key (``key``) and the countries or areas it is collected for. A key
with the placeholder ``{geo}`` is expanded for every code in ``geos``; an
entry without placeholder has exactly one ``geo``. Each expansion is a series
with the stable id ``<concept>.<geo>``, the join key ``series_id`` of the
datasets ``economic_series`` and ``series_catalog``. Geo codes follow
Eurostat; where a provider writes a code differently in its keys, the key
gets the provider's code: the ECB writes the euro area as U2, and Eurostat
datasets without the changing-composition code EA use the current fixed
composition (``geo_codes = { EA = "EA21" }`` in the entry).

Every entry has the date on which it was ``added``. An entry that is no
longer collected keeps its place with the date on which it was ``removed``
and a ``removed_reason``, so that the coverage period of every series stays
known; series ids are never reused for a different meaning.
"""
import re
import tomllib
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional, get_args

from schema import Frequency, Provider, SeriesTopic

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "series.toml"

CONCEPT_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
# Eurostat country codes, EA (euro area, changing composition), EU27_2020, and WLD for world prices
GEO_PATTERN = re.compile(r"^(?:[A-Z]{2}|EA|EU27_2020|WLD)$")
GEO_PLACEHOLDER = "{geo}"
# Codes that differ in the keys of a provider: the ECB writes the euro area (changing composition) as U2
PROVIDER_GEO_CODES: dict[str, dict[str, str]] = {"ecb": {"EA": "U2"}}
KNOWN_KEYS = frozenset({
    "concept", "name", "topic", "frequency", "unit", "provider", "flow", "key", "geo", "geos", "geo_codes", "added",
    "removed", "removed_reason", "notes",
})


class CatalogError(ValueError):
    """The catalog file contains invalid or duplicate entries."""


@dataclass(frozen=True)
class Series:
    """One statistical series of the catalog.

    Attributes:
        concept (str): What the series measures, independent of the country.
        geo (str): Country or area code.
        name (str): Name of the series.
        topic (str): Topic group (see ``schema.SeriesTopic``).
        frequency (str): D, W, M, Q, S or A.
        unit (str): Unit of the values.
        provider (str): Provider (see ``schema.Provider``).
        flow (str): Dataset or dataflow of the provider.
        key (str): Series key at the provider, with the geo filled in.
        added (date): Day on which the entry was added; start of collection.
        removed (Optional[date]): Day on which the entry was removed; it is no longer collected.
        removed_reason (Optional[str]): Why the entry was removed.
    """
    concept: str
    geo: str
    name: str
    topic: str
    frequency: str
    unit: str
    provider: str
    flow: str
    key: str
    added: date
    removed: Optional[date] = None
    removed_reason: Optional[str] = None

    @property
    def series_id(self) -> str:
        """The stable id ``<concept>.<geo>``."""
        return f"{self.concept}.{self.geo}"

    @property
    def active(self) -> bool:
        """True if the series is collected, i.e. it was not removed."""
        return self.removed is None


def _required_str(raw: dict[str, Any], key: str) -> str:
    """Reads a required non-empty string."""
    value = raw.get(key)
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


def parse_entry(raw: dict[str, Any]) -> list[Series]:
    """Validates one catalog entry and expands it to its series.

    Args:
        raw: The entry as read from TOML.

    Returns:
        list[Series]: One series per geo.

    Raises:
        ValueError: If a field is missing, unknown or invalid.
    """
    unknown = sorted(set(raw) - KNOWN_KEYS)
    if unknown:
        raise ValueError(f"unknown keys: {', '.join(unknown)}")
    concept = _required_str(raw, "concept")
    if not CONCEPT_PATTERN.match(concept):
        raise ValueError("concept must be lower-case snake_case")
    topic = _required_str(raw, "topic")
    if topic not in get_args(SeriesTopic):
        raise ValueError(f"unknown topic {topic!r}")
    frequency = _required_str(raw, "frequency")
    if frequency not in get_args(Frequency):
        raise ValueError(f"unknown frequency {frequency!r}")
    provider = _required_str(raw, "provider")
    if provider not in get_args(Provider):
        raise ValueError(f"unknown provider {provider!r}")
    key = _required_str(raw, "key")
    added = _optional_date(raw, "added")
    if added is None:
        raise ValueError("added is missing")
    removed = _optional_date(raw, "removed")
    removed_reason = raw.get("removed_reason")
    if (removed is None) != (removed_reason is None):
        raise ValueError("removed and removed_reason must be given together")
    if removed is not None and removed < added:
        raise ValueError("removed is earlier than added")
    if "geo" in raw and "geos" in raw:
        raise ValueError("give either geo or geos")
    if "geos" in raw:
        geos = raw["geos"]
        if not isinstance(geos, list) or not geos or not all(isinstance(geo, str) for geo in geos):
            raise ValueError("geos must be a non-empty list of strings")
        if GEO_PLACEHOLDER not in key:
            raise ValueError(f"an entry with geos needs {GEO_PLACEHOLDER} in its key")
    else:
        geos = [_required_str(raw, "geo")]
        if GEO_PLACEHOLDER in key:
            raise ValueError(f"an entry with {GEO_PLACEHOLDER} in its key needs geos")
    bad_geos = [geo for geo in geos if not GEO_PATTERN.match(geo)]
    if bad_geos:
        raise ValueError(f"invalid geo codes: {', '.join(bad_geos)}")
    geo_codes = raw.get("geo_codes", {})
    if not isinstance(geo_codes, dict) or not all(isinstance(code, str) and code for code in geo_codes.values()):
        raise ValueError("geo_codes must map geo codes to provider codes")
    unused = sorted(set(geo_codes) - set(geos))
    if unused:
        raise ValueError(f"geo_codes for geos that the entry does not list: {', '.join(unused)}")
    common = {
        "concept": concept, "name": _required_str(raw, "name"), "topic": topic, "frequency": frequency,
        "unit": _required_str(raw, "unit"), "provider": provider, "flow": _required_str(raw, "flow"),
        "added": added, "removed": removed, "removed_reason": removed_reason,
    }
    codes = {**PROVIDER_GEO_CODES.get(provider, {}), **geo_codes}
    return [Series(geo=geo, key=key.replace(GEO_PLACEHOLDER, codes.get(geo, geo)), **common) for geo in geos]


def load_catalog(path: Path = CONFIG_PATH) -> list[Series]:
    """Reads and validates the catalog.

    Args:
        path: The catalog file.

    Returns:
        list[Series]: All series in file order, including removed ones.

    Raises:
        CatalogError: If an entry is invalid or a series id or provider key is duplicated.
    """
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    entries = data.get("series", [])
    if not isinstance(entries, list):
        raise CatalogError(f"{path} must contain [[series]] entries")
    series: list[Series] = []
    problems: list[str] = []
    for position, raw in enumerate(entries, start=1):
        try:
            series.extend(parse_entry(raw))
        except ValueError as e:
            problems.append(f"entry {position} ({raw.get('concept', '?')}): {e}")
    for label, values in (("series id", [item.series_id for item in series]),
                          ("provider key", [f"{item.provider}:{item.flow}:{item.key}" for item in series])):
        duplicates = sorted(value for value, count in Counter(values).items() if count > 1)
        if duplicates:
            problems.append(f"duplicate {label}: {', '.join(duplicates)}")
    if problems:
        raise CatalogError(f"{path}: " + "; ".join(problems))
    return series


def active_series(provider: Optional[str] = None, path: Path = CONFIG_PATH) -> list[Series]:
    """Returns the series that are collected, optionally of one provider.

    Args:
        provider: Provider to select; None returns the series of all providers.
        path: The catalog file.

    Returns:
        list[Series]: The active series in file order.
    """
    return [item for item in load_catalog(path) if item.active and (provider is None or item.provider == provider)]
