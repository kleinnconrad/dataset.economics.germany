"""
Writes the dataset overview into the README.

The overview replaces the text between the markers DATASET_OVERVIEW_START and
DATASET_OVERVIEW_END: record counts per dataset, the outcome of the latest
run, the statistical series per topic with their latest period, the company
registry, the status and output of every news and press-release source, the
annotation coverage, the main topics of the last 30 days, and the fields of
every dataset with their descriptions from ``schema.py`` and their fill
rates. Long tables are placed in collapsible sections.

Usage:
    uv run python src/generate_dataset_overview.py [--data-dir data] [--readme README.md]
"""
import argparse
import json
import logging
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from catalog import CONFIG_PATH as CATALOG_PATH
from catalog import CatalogError, load_catalog
from companies import CONFIG_PATH as COMPANIES_PATH
from companies import RegistryError, load_registry
from schema import DATASET_MODELS
from sources import CONFIG_PATH, SourceHealthStore, load_config
from state import RUN_LOG_FILE
from storage import iter_dataset_files, load_records

logger = logging.getLogger(__name__)

START_MARKER = "<!-- DATASET_OVERVIEW_START -->"
END_MARKER = "<!-- DATASET_OVERVIEW_END -->"
RECENT_WINDOW_DAYS = 30
TOP_TOPICS = 10
ITEM_DATASETS = ("news_items", "press_releases")


@dataclass
class DatasetData:
    """The stored records of one dataset.

    Attributes:
        files (int): Number of partition files.
        records (list[dict]): All records in chronological order of the files.
    """
    files: int
    records: list[dict[str, Any]]


def load_datasets(data_dir: Path) -> dict[str, DatasetData]:
    """Reads all records of all datasets.

    Args:
        data_dir: Root folder of the datasets.

    Returns:
        dict[str, DatasetData]: Records per dataset, in the order of ``DATASET_MODELS``.
    """
    datasets = {}
    for dataset in DATASET_MODELS:
        files = list(iter_dataset_files(data_dir, dataset))
        records: list[dict[str, Any]] = []
        for path in files:
            records.extend(load_records(path))
        datasets[dataset] = DatasetData(files=len(files), records=records)
    return datasets


def _description(dataset: str) -> str:
    """Returns the first line of the docstring of a dataset's record model."""
    doc = DATASET_MODELS[dataset].__doc__ or ""
    return doc.strip().splitlines()[0] if doc.strip() else ""


def _cell(text: Optional[str]) -> str:
    """Escapes text for a Markdown table cell."""
    return (text or "").replace("|", "\\|").replace("\n", " ")


def _share(part: int, total: int) -> str:
    """Formats a share with its count, e.g. ``95.0% (190)``."""
    return f"{part / total:.1%} ({part:,})" if total else "0.0% (0)"


def dataset_lines(datasets: dict[str, DatasetData]) -> list[str]:
    """Builds the table of the datasets.

    Args:
        datasets: Records per dataset.

    Returns:
        list[str]: Markdown lines.
    """
    lines = ["| Dataset | Records | Items | Files | Observed | Content |", "|---|---|---|---|---|---|"]
    for dataset, data in datasets.items():
        observed = sorted(str(r.get("observed_at"))[:10] for r in data.records if r.get("observed_at"))
        items = len({record.get("record_id") for record in data.records})
        span = f"{observed[0]} to {observed[-1]}" if observed else "none"
        lines.append(f"| `{dataset}` | {len(data.records):,} | {items:,} | {data.files} | {span} | "
                     f"{_cell(_description(dataset))} |")
    return lines


def _is_filled(value: Any) -> bool:
    """Tells whether a field has a value: not null and not an empty text, list or object."""
    return value is not None and value != "" and value != [] and value != {}


def _distinct(values: list[Any]) -> int:
    """Counts the distinct values of a field: list elements and object keys are counted individually."""
    distinct: set[str] = set()
    for value in values:
        if isinstance(value, list):
            distinct.update(json.dumps(item, sort_keys=True, ensure_ascii=False) for item in value)
        elif isinstance(value, dict):
            distinct.update(str(key) for key in value)
        elif value is not None:
            distinct.add(json.dumps(value, ensure_ascii=False))
    return len(distinct)


def field_lines(datasets: dict[str, DatasetData]) -> list[str]:
    """Builds one collapsible field table per dataset with records.

    Args:
        datasets: Records per dataset.

    Returns:
        list[str]: Markdown lines; empty if no dataset has records.
    """
    lines: list[str] = []
    for dataset, data in datasets.items():
        if not data.records:
            continue
        total = len(data.records)
        lines.extend([
            "<details>",
            f"<summary><code>{dataset}</code>: {len(DATASET_MODELS[dataset].model_fields)} fields</summary>",
            "",
            "| Field | Description | Filled | Distinct values |",
            "|---|---|---|---|",
        ])
        for name, field in DATASET_MODELS[dataset].model_fields.items():
            values = [record.get(name) for record in data.records]
            filled = sum(1 for value in values if _is_filled(value))
            lines.append(f"| `{name}` | {_cell(field.description)} | {_share(filled, total)} | {_distinct(values):,} |")
        lines.extend(["", "</details>", ""])
    return lines


def source_lines(state_dir: Path, config_path: Path, datasets: dict[str, DatasetData], now: datetime) -> list[str]:
    """Summarizes the status of the sources and builds a collapsible table per source.

    Args:
        state_dir: Folder of the state files.
        config_path: The source configuration.
        datasets: Records per dataset.
        now: Current UTC time.

    Returns:
        list[str]: Markdown lines.
    """
    if not config_path.exists():
        return ["- No sources configured."]
    config = load_config(config_path)
    health = SourceHealthStore.load(state_dir)
    items = [record for dataset in ITEM_DATASETS for record in datasets[dataset].records]
    annotated = {record.get("item_id") for record in datasets["text_annotations"].records}
    by_source: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_source.setdefault(str(item.get("source_id")), []).append(item)
    cutoff = (now - timedelta(days=RECENT_WINDOW_DAYS)).isoformat()
    lines = []
    tables: list[str] = []
    groups = (("News outlets", config.outlets, "outlet_type"),
              ("Press-release sources", config.press_sources, "actor_type"))
    for label, sources, type_attribute in groups:
        counts = Counter(health.status_of(source) for source in sources)
        text = ", ".join(f"{count} {status}" for status, count in sorted(counts.items())) or "none"
        lines.append(f"- **{label}:** {len(sources)} configured ({text})")
        tables.extend([
            "<details>",
            f"<summary>{label}: items per source</summary>",
            "",
            "| Source | Type | Status | Items | Last 30 days | Annotated | With lead text | Latest publication |",
            "|---|---|---|---|---|---|---|---|",
        ])
        for source in sorted(sources, key=lambda s: s.name.casefold()):
            source_items = by_source.get(source.id, [])
            recent = sum(1 for item in source_items if str(item.get("observed_at", "")) >= cutoff)
            with_labels = sum(1 for item in source_items if item.get("record_id") in annotated)
            with_lead = sum(1 for item in source_items if item.get("content_basis") == "lead_text")
            published = [str(item["published_at"])[:10] for item in source_items if item.get("published_at")]
            observed = [str(item["observed_at"])[:10] for item in source_items if item.get("observed_at")]
            latest = max(published or observed, default="none")
            tables.append(
                f"| {_cell(source.name)} | {getattr(source, type_attribute).replace('_', ' ')} | "
                f"{health.status_of(source)} | {len(source_items):,} | {recent:,} | "
                f"{_share(with_labels, len(source_items))} | {_share(with_lead, len(source_items))} | {latest} |"
            )
        tables.extend(["", "</details>", ""])
    return [*lines, "", *tables]


def series_lines(catalog_path: Path, datasets: dict[str, DatasetData]) -> list[str]:
    """Summarizes the statistical series: series per topic and provider, and the latest period of every series.

    Args:
        catalog_path: The series catalog.
        datasets: Records per dataset.

    Returns:
        list[str]: Markdown lines.
    """
    try:
        catalog = [series for series in load_catalog(catalog_path) if series.active]
    except (FileNotFoundError, CatalogError) as e:
        return [f"- Series catalog not readable: {_cell(str(e))[:200]}"]
    latest: dict[str, dict[str, Any]] = {}
    for record in datasets["economic_series"].records:
        latest[str(record.get("series_id"))] = record
    topics = Counter(series.topic for series in catalog)
    providers = Counter(series.provider for series in catalog)
    lines = [
        f"- **Active series:** {len(catalog):,} ({', '.join(f'{name} {count}' for name, count in providers.most_common())});"
        f" with stored values: {sum(1 for series in catalog if series.series_id in latest):,}",
        "",
        "<details>",
        "<summary>Series: latest period and number of revisions</summary>",
        "",
        "| Series | Topic | Frequency | Unit | First period | Latest period | Periods | Revisions |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for series in sorted(catalog, key=lambda item: (item.topic, item.series_id)):
        record = latest.get(series.series_id, {})
        lines.append(f"| `{series.series_id}` | {series.topic.replace('_', ' ')} | {series.frequency} | "
                     f"{_cell(series.unit)} | {record.get('first_period') or 'none'} | "
                     f"{record.get('last_period') or 'none'} | {record.get('observations', 0):,} | "
                     f"{record.get('revision', 0) if record else 0} |")
    lines.extend(["", "</details>", "", "| Topic | Series |", "|---|---|"])
    lines.extend(f"| {topic.replace('_', ' ')} | {count} |" for topic, count in sorted(topics.items()))
    return lines


def company_lines(registry_path: Path, datasets: dict[str, DatasetData], now: datetime) -> list[str]:
    """Summarizes the company registry and the companies named most often in the last 30 days.

    Args:
        registry_path: The company registry.
        datasets: Records per dataset.
        now: Current UTC time.

    Returns:
        list[str]: Markdown lines.
    """
    try:
        companies = [company for company in load_registry(registry_path) if company.active]
    except (FileNotFoundError, RegistryError) as e:
        return [f"- Company registry not readable: {_cell(str(e))[:200]}"]
    names = {company.id: company.name for company in companies}
    lines = [f"- **Registered companies:** {len(companies):,} ({sum(company.listed for company in companies)} listed, "
             f"{sum(company.country == 'DE' for company in companies)} with headquarters in Germany)"]
    cutoff = (now - timedelta(days=RECENT_WINDOW_DAYS)).isoformat()
    mentions: Counter[str] = Counter()
    for record in datasets["text_annotations"].records:
        if str(record.get("observed_at", "")) >= cutoff:
            mentions.update(record.get("mentioned_companies") or [])
    if mentions:
        lines.extend(["", f"**Companies named most often, last {RECENT_WINDOW_DAYS} days**", "",
                      "| Company | Annotated items |", "|---|---|"])
        lines.extend(f"| {_cell(names.get(company_id, company_id))} | {count:,} |"
                     for company_id, count in mentions.most_common(TOP_TOPICS))
    return lines


def annotation_lines(datasets: dict[str, DatasetData], now: datetime) -> list[str]:
    """Summarizes the annotation coverage and the main topics of recent economic items.

    Args:
        datasets: Records per dataset.
        now: Current UTC time.

    Returns:
        list[str]: Markdown lines.
    """
    items = [record for dataset in ITEM_DATASETS for record in datasets[dataset].records]
    annotations = datasets["text_annotations"].records
    if not items:
        return ["- No news articles or press releases yet."]
    annotated_ids = {record.get("item_id") for record in annotations}
    annotated = sum(1 for item in items if item.get("record_id") in annotated_ids)
    basis = Counter(item.get("content_basis") for item in items)
    lines = [
        f"- **Annotated items:** {annotated:,} of {len(items):,} ({annotated / len(items):.1%})",
        "- **Text seen by the model:** " + ", ".join(f"{name} {count:,}" for name, count in basis.most_common()),
    ]
    cutoff = (now - timedelta(days=RECENT_WINDOW_DAYS)).isoformat()
    recent = [record for record in annotations
              if record.get("is_economic") and str(record.get("observed_at", "")) >= cutoff]
    if recent:
        topics = Counter(record.get("topic") for record in recent).most_common(TOP_TOPICS)
        lines.extend([
            "",
            f"**Main topics of economic items, last {RECENT_WINDOW_DAYS} days** ({len(recent):,} items)",
            "",
            "| Topic | Items | Share |",
            "|---|---|---|",
        ])
        lines.extend(f"| {topic} | {count:,} | {count / len(recent):.1%} |" for topic, count in topics)
    return lines


def last_run_lines(state_dir: Path) -> list[str]:
    """Summarizes the latest run from the run log.

    Args:
        state_dir: Folder of the state files.

    Returns:
        list[str]: Markdown lines.
    """
    path = state_dir / RUN_LOG_FILE
    if not path.exists():
        return ["- No run yet."]
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    entry = json.loads(lines[-1])
    rows = [f"- **Latest run:** {entry.get('started', '?')[:16].replace('T', ' ')} UTC ({entry.get('mode')})"]
    for name, outcome in entry.get("collectors", {}).items():
        records = ", ".join(f"{dataset} {count:,}" for dataset, count in outcome.get("records", {}).items())
        error = f"; {outcome['error']}" if outcome.get("error") else ""
        rows.append(f"  - `{name}`: {outcome.get('status')}{' (' + records + ')' if records else ''}{error}")
    return rows


def build_overview(data_dir: Path, config_path: Path = CONFIG_PATH, now: Optional[datetime] = None,
                   catalog_path: Path = CATALOG_PATH, registry_path: Path = COMPANIES_PATH) -> str:
    """Builds the Markdown of the overview.

    Args:
        data_dir: Root folder of the datasets.
        config_path: The source configuration.
        now: Current UTC time; defaults to now.
        catalog_path: The series catalog.
        registry_path: The company registry.

    Returns:
        str: The overview without the markers.
    """
    now = now or datetime.now(timezone.utc)
    datasets = load_datasets(data_dir)
    state_dir = data_dir / "state"
    fields = field_lines(datasets)
    parts = [
        f"**Last updated:** {now:%Y-%m-%d %H:%M} UTC",
        "",
        *dataset_lines(datasets),
        "",
        "**Runs**",
        "",
        *last_run_lines(state_dir),
        "",
        "**Statistical series**",
        "",
        *series_lines(catalog_path, datasets),
        "",
        "**Companies**",
        "",
        *company_lines(registry_path, datasets, now),
        "",
        "**Sources**",
        "",
        *source_lines(state_dir, config_path, datasets, now),
        "**Annotations**",
        "",
        *annotation_lines(datasets, now),
    ]
    if fields:
        parts.extend(["", "**Fields** (Filled: records with a value that is not null and not empty)", "", *fields])
    return "\n".join(parts).rstrip()


def update_readme(readme: Path, overview: str) -> bool:
    """Replaces the text between the markers of the README.

    Args:
        readme: The README file.
        overview: The new overview.

    Returns:
        bool: True if the README changed.

    Raises:
        ValueError: If the markers are missing.
    """
    text = readme.read_text(encoding="utf-8")
    start = text.find(START_MARKER)
    end = text.find(END_MARKER)
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"{readme} has no overview markers")
    updated = text[: start + len(START_MARKER)] + "\n" + overview + "\n" + text[end:]
    if updated == text:
        return False
    readme.write_text(updated, encoding="utf-8", newline="\n")
    return True


def main(argv: Optional[list[str]] = None) -> int:
    """Writes the overview into the README.

    Args:
        argv: Arguments without the program name; None reads ``sys.argv``.

    Returns:
        int: 0 on success, 1 if the README has no markers.
    """
    parser = argparse.ArgumentParser(description="Writes the dataset overview into the README.")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--readme", type=Path, default=Path("README.md"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    try:
        changed = update_readme(args.readme, build_overview(args.data_dir))
    except ValueError as e:
        logger.error("%s", e)
        return 1
    logger.info("README overview %s.", "updated" if changed else "unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
