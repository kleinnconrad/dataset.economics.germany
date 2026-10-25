"""
Writes the entries of the series catalog and the company registry to their datasets.

``config/series.toml`` and ``config/companies.toml`` are the slowly changing dimensions of the
dataset: every entry is written when it appears and again, with the next revision, when one of
its fields changes, so that the definition of a series or company at time t can be
reconstructed from the data alone. The collectors send no requests.
"""
import logging
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from catalog import CONFIG_PATH as CATALOG_PATH
from catalog import Series, load_catalog
from collectors.base import Collector, CollectorResult, RunContext
from companies import CONFIG_PATH as COMPANIES_PATH
from companies import Company, load_registry
from schema import CompanyRecord, RecordBase, SeriesCatalogRecord
from state import CollectorEntry, content_hash

logger = logging.getLogger(__name__)

SOURCE_ID = "registry"
LICENSE = "Configuration of this project; no license granted"
REPOSITORY_URL = "https://github.com/kleinnconrad/dataset.economics.germany/blob/main/"


def series_fields(series: Series) -> dict[str, Any]:
    """Returns the dataset fields of a catalog series.

    Args:
        series: The catalog series.

    Returns:
        dict: The fields of a ``SeriesCatalogRecord`` without the common fields.
    """
    return {
        "series_id": series.series_id, "concept": series.concept, "name": series.name, "topic": series.topic,
        "geo": series.geo, "frequency": series.frequency, "unit": series.unit, "provider": series.provider,
        "provider_flow": series.flow, "provider_key": series.key, "added": series.added, "removed": series.removed,
        "removed_reason": series.removed_reason,
    }


def company_fields(company: Company) -> dict[str, Any]:
    """Returns the dataset fields of a registry company.

    Args:
        company: The registry entry.

    Returns:
        dict: The fields of a ``CompanyRecord`` without the common fields.
    """
    return {
        "company_id": company.id, "name": company.name, "aliases": list(company.aliases), "sector": company.sector,
        "country": company.country, "listed": company.listed, "isin": company.isin, "wikidata_qid": company.wikidata,
        "added": company.added, "removed": company.removed, "removed_reason": company.removed_reason,
    }


def emit_changes(ctx: RunContext, dataset: str, items: Sequence[tuple[str, dict[str, Any]]],
                 model: Callable[..., RecordBase], source_url: str) -> dict[str, int]:
    """Emits a record for every item that is new or changed since the previous run.

    Args:
        ctx: The run context.
        dataset: Name of the dataset.
        items: Key and record fields of every item.
        model: Record model of the dataset.
        source_url: URL of the configuration file.

    Returns:
        dict[str, int]: Counts of all, new and changed items.
    """
    seen = ctx.seen(dataset)
    counters = {"items": len(items), "new": 0, "changed": 0}
    records = []
    for key, fields in items:
        item_hash = content_hash(fields)
        status = seen.classify(key, item_hash)
        if status == "unchanged":
            continue
        counters[status] += 1
        revision = seen.mark(key, item_hash, ctx.today)
        records.append(model(**ctx.envelope(dataset, f"{dataset}:{key}", revision=revision, source_id=SOURCE_ID,
                                            source_url=source_url, license=LICENSE, backfilled=False), **fields))
    ctx.emit(dataset, records)
    logger.info("%s: %d new, %d changed of %d entries.", dataset, counters["new"], counters["changed"], len(items))
    return counters


class SeriesCatalogCollector(Collector):
    """Writes new and changed entries of the series catalog."""
    name = "series_catalog"
    datasets = ("series_catalog",)

    def __init__(self, catalog_path: Path = CATALOG_PATH) -> None:
        """Initializes the collector.

        Args:
            catalog_path: The series catalog.
        """
        self._catalog_path = catalog_path

    def collect(self, ctx: RunContext, entry: CollectorEntry) -> CollectorResult:
        """Emits a record for every catalog series that is new or changed.

        Args:
            ctx: The run context.
            entry: Run history of this collector.

        Returns:
            CollectorResult: Counters.
        """
        items = [(series.series_id, series_fields(series)) for series in load_catalog(self._catalog_path)]
        return CollectorResult(counters=emit_changes(ctx, "series_catalog", items, SeriesCatalogRecord,
                                                     REPOSITORY_URL + "config/series.toml"))


class CompaniesCollector(Collector):
    """Writes new and changed entries of the company registry."""
    name = "companies"
    datasets = ("companies",)

    def __init__(self, registry_path: Path = COMPANIES_PATH) -> None:
        """Initializes the collector.

        Args:
            registry_path: The company registry.
        """
        self._registry_path = registry_path

    def collect(self, ctx: RunContext, entry: CollectorEntry) -> CollectorResult:
        """Emits a record for every registry company that is new or changed.

        Args:
            ctx: The run context.
            entry: Run history of this collector.

        Returns:
            CollectorResult: Counters.
        """
        items = [(company.id, company_fields(company)) for company in load_registry(self._registry_path)]
        return CollectorResult(counters=emit_changes(ctx, "companies", items, CompanyRecord,
                                                     REPOSITORY_URL + "config/companies.toml"))
