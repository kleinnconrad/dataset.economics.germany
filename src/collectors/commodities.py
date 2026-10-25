"""
Collects monthly commodity prices and price indices from the World Bank Pink Sheet.

Source: World Bank Commodity Price Data (the "Pink Sheet"), the workbook
``CMO-Historical-Data-Monthly.xlsx`` with monthly prices in nominal US dollars from 1960
(sheet "Monthly Prices": about 70 energy, agricultural, fertilizer and metal prices) and
price indices (sheet "Monthly Indices": total, energy, non-energy, agriculture, food,
fertilizers, metals and minerals, base metals, precious metals; 2010 = 100). The World Bank
licenses the data under CC BY 4.0. The World Bank updates the workbook in the first days of
every month.

Fetch strategy: the address of the workbook changes once a year. The collector reads it from
the commodity markets page of the World Bank (a website request that respects robots.txt) and
keeps the last address in its cursor, so that a failure of the page does not stop the
collector. The workbook (about 0.6 MB) is requested with ``If-None-Match`` and
``If-Modified-Since``; an unchanged file is not downloaded again, unless a catalog series has
no stored values yet.

Parsing: the first column holds the period (``1960M01``); the header rows above the first
period hold the name of each column (on the indices sheet one level of the index hierarchy
per row) and, on the price sheet, the unit in parentheses. A catalog series selects a column
by its name (``key``) on its sheet (``flow``); footnote markers (``*``) and repeated spaces
are removed from the names. Cells with ``…`` or without a number have no value.

Records: vintages of each series in ``economic_series`` (see ``collectors/series.py``).

Schedule: weekly; the World Bank updates the workbook monthly.
"""
import io
import logging
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin

import openpyxl
from openpyxl.utils.exceptions import InvalidFileException

from catalog import CONFIG_PATH, Series, active_series
from collectors.base import Collector, CollectorResult, RunContext
from collectors.sdmx import collect_series
from collectors.series import DATASET, SeriesData, SeriesWriter, normalize_period, parse_value
from state import CollectorEntry
from web import BlockedError, FetchError

logger = logging.getLogger(__name__)

PROVIDER = "worldbank_cmo"
SOURCE_ID = "worldbank_pink_sheet"
LICENSE = "CC-BY-4.0 (World Bank Commodity Price Data)"
PAGE_URL = "https://www.worldbank.org/en/research/commodity-markets"
WORKBOOK_PATTERN = re.compile(r"""["']([^"']*CMO-Historical-Data-Monthly\.xlsx)["']""", re.IGNORECASE)
PERIOD_PATTERN = re.compile(r"^\d{4}M\d{2}$")
UPDATED_PATTERN = re.compile(r"Updated on\s+([A-Za-z]+ \d{1,2}, \d{4})")
DOWNLOAD_TIMEOUT_S = 120.0


class WorkbookError(Exception):
    """The workbook could not be found, downloaded or parsed."""


def clean_header(value: Any) -> str:
    """Removes footnote markers and repeated whitespace from a header cell.

    Args:
        value: The cell value.

    Returns:
        str: The cleaned text; empty for empty cells.
    """
    if not isinstance(value, str):
        return ""
    return " ".join(value.replace("*", " ").split())


@dataclass
class Sheet:
    """The columns of one sheet of the workbook.

    Attributes:
        columns (dict[str, dict[str, float]]): Values by period for every column name.
        units (dict[str, str]): Unit of every column, where the sheet states one.
    """
    columns: dict[str, dict[str, float]] = field(default_factory=dict)
    units: dict[str, str] = field(default_factory=dict)


def parse_sheet(rows: list[tuple[Any, ...]]) -> Sheet:
    """Reads the columns of a sheet of the Pink Sheet.

    Args:
        rows: The rows of the sheet as tuples of cell values.

    Returns:
        Sheet: The columns by name.

    Raises:
        WorkbookError: If the sheet has no row with a period in the first column.
    """
    first_data = next((index for index, row in enumerate(rows)
                       if row and isinstance(row[0], str) and PERIOD_PATTERN.match(row[0].strip())), None)
    if first_data is None:
        raise WorkbookError("no row with a period such as 1960M01")
    width = max(len(row) for row in rows)
    names: dict[int, str] = {}
    units: dict[int, str] = {}
    for column in range(1, width):
        parts = []
        for row in rows[:first_data]:
            text = clean_header(row[column]) if column < len(row) else ""
            if not text:
                continue
            if text.startswith("(") and text.endswith(")"):
                units[column] = text[1:-1]
            else:
                parts.append(text)
        if parts:
            names[column] = " ".join(parts)
    sheet = Sheet()
    for column, name in names.items():
        values: dict[str, float] = {}
        for row in rows[first_data:]:
            if not row or not isinstance(row[0], str):
                continue
            period = normalize_period(row[0], "M")
            value = parse_value(row[column]) if column < len(row) else None
            if period is not None and value is not None:
                values[period] = value
        sheet.columns[name] = values
        if column in units:
            sheet.units[name] = units[column]
    return sheet


def parse_workbook(content: bytes) -> tuple[dict[str, Sheet], Optional[datetime]]:
    """Reads all sheets with periods from the workbook.

    Args:
        content: The xlsx file.

    Returns:
        tuple: Sheets by name, and the update date stated in the workbook (UTC midnight).

    Raises:
        WorkbookError: If the file is not a readable workbook.
    """
    try:
        workbook = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except (InvalidFileException, zipfile.BadZipFile, KeyError, OSError) as e:
        raise WorkbookError(f"not a readable workbook: {e}") from e
    sheets: dict[str, Sheet] = {}
    updated: Optional[datetime] = None
    try:
        for worksheet in workbook.worksheets:
            rows = [tuple(row) for row in worksheet.iter_rows(values_only=True)]
            for row in rows[:10]:
                for cell in row[:1]:
                    match = UPDATED_PATTERN.search(cell) if isinstance(cell, str) else None
                    if match and updated is None:
                        try:
                            updated = datetime.strptime(match.group(1), "%B %d, %Y").replace(tzinfo=timezone.utc)
                        except ValueError:
                            pass
            try:
                sheets[worksheet.title] = parse_sheet(rows)
            except WorkbookError:
                continue
    finally:
        workbook.close()
    if not sheets:
        raise WorkbookError("the workbook has no sheet with monthly periods")
    return sheets, updated


def find_workbook_url(ctx: RunContext) -> str:
    """Reads the address of the monthly workbook from the commodity markets page.

    Args:
        ctx: The run context.

    Returns:
        str: The absolute URL of the workbook.

    Raises:
        FetchError: If the page cannot be fetched.
        WorkbookError: If the page links no workbook.
    """
    response = ctx.web.get(PAGE_URL)
    match = WORKBOOK_PATTERN.search(response.text)
    if match is None:
        raise WorkbookError(f"{PAGE_URL} links no CMO-Historical-Data-Monthly.xlsx")
    return urljoin(response.url, match.group(1))


class CommoditiesCollector(Collector):
    """Writes vintages of the World Bank commodity prices and indices of the catalog."""
    name = "commodities"
    datasets = (DATASET,)
    min_days_between_runs = 6

    def __init__(self, catalog_path: Path = CONFIG_PATH) -> None:
        """Initializes the collector.

        Args:
            catalog_path: The series catalog.
        """
        self._catalog_path = catalog_path

    def collect(self, ctx: RunContext, entry: CollectorEntry) -> CollectorResult:
        """Downloads the workbook if it changed and emits the new and revised series.

        Args:
            ctx: The run context.
            entry: Run history; the cursor holds the workbook URL, its ETag and Last-Modified header.

        Returns:
            CollectorResult: The updated cursor and counters.
        """
        catalog = active_series(PROVIDER, self._catalog_path)
        cursor = dict(entry.cursor)
        writer = SeriesWriter(ctx, SOURCE_ID, LICENSE)
        try:
            url = find_workbook_url(ctx)
        except BlockedError as e:
            return CollectorResult(cursor=cursor, error=f"blocked: {e}", complete=False)
        except (FetchError, WorkbookError) as e:
            url = cursor.get("url")
            logger.warning("Workbook address not read from the page (%s); using the stored address %s.", e, url)
            if not url:
                return CollectorResult(cursor=cursor, error=f"no workbook address: {e}")
        new_series = any(not writer.stored_values(series) for series in catalog)
        headers: dict[str, str] = {}
        if url == cursor.get("url") and not new_series:
            if cursor.get("etag"):
                headers["If-None-Match"] = str(cursor["etag"])
            if cursor.get("last_modified"):
                headers["If-Modified-Since"] = str(cursor["last_modified"])
        try:
            response = ctx.web.get(url, headers=headers or None, timeout_s=DOWNLOAD_TIMEOUT_S)
        except BlockedError as e:
            return CollectorResult(cursor=cursor, error=f"blocked: {e}", complete=False)
        except FetchError as e:
            return CollectorResult(cursor=cursor, error=f"workbook download failed: {e}")
        if response.status == 304:
            logger.info("Pink Sheet unchanged since %s.", cursor.get("last_modified") or cursor.get("etag"))
            return CollectorResult(cursor=cursor, counters={"series": len(catalog), "workbook": "unchanged"})
        try:
            sheets, updated = parse_workbook(response.content)
        except WorkbookError as e:
            return CollectorResult(cursor=cursor, error=f"workbook not readable: {e}")

        def fetch(series: Series) -> SeriesData:
            sheet = sheets.get(series.flow)
            if sheet is None:
                raise KeyError(f"sheet {series.flow!r} not in the workbook")
            if series.key not in sheet.columns:
                raise KeyError(f"column {series.key!r} not on sheet {series.flow!r}")
            return SeriesData(values=sheet.columns[series.key], url=url, title=series.key, source_updated=updated)

        result = collect_series(ctx, catalog, fetch, writer, "Pink Sheet")
        # The validators are kept only after every series was processed, so that an interrupted run
        # downloads the unchanged workbook again in the next run
        processed = result.complete and not result.counters.get("failed") and not result.counters.get("incomplete")
        cursor.update(url=url, etag=response.headers.get("etag") if processed else None,
                      last_modified=response.headers.get("last-modified") if processed else None)
        result.cursor = cursor
        result.counters["workbook"] = "downloaded"
        return result
