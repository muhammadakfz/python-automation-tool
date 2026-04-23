"""CSV data processing utilities for repeatable cleanup workflows."""

from __future__ import annotations

import csv
from pathlib import Path

from python_automation_tool.models import CsvProcessSummary


def _read_csv(input_path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read CSV headers and rows with strict validation."""
    try:
        with input_path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ValueError("CSV file must include a header row.")

            raw_headers = reader.fieldnames
            headers = [header.strip() for header in raw_headers]

            if any(not header for header in headers):
                raise ValueError("CSV header contains an empty column name.")
            if len(set(headers)) != len(headers):
                raise ValueError("CSV header contains duplicate column names.")

            rows: list[dict[str, str]] = []
            for raw_row in reader:
                normalized_row: dict[str, str] = {}
                for index, header in enumerate(raw_headers):
                    normalized_key = headers[index]
                    normalized_row[normalized_key] = (raw_row.get(header) or "")
                rows.append(normalized_row)

            return headers, rows
    except csv.Error as exc:
        raise ValueError(f"Malformed CSV file: {exc}") from exc


def _trim_whitespace(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Trim surrounding whitespace from every value."""
    trimmed_rows: list[dict[str, str]] = []
    for row in rows:
        trimmed_rows.append({key: value.strip() for key, value in row.items()})
    return trimmed_rows


def _rename_columns(
    headers: list[str],
    rows: list[dict[str, str]],
    mappings: dict[str, str],
) -> tuple[list[str], list[dict[str, str]]]:
    """Rename columns while preserving row values."""
    missing = set(mappings).difference(headers)
    if missing:
        missing_str = ", ".join(sorted(missing))
        raise ValueError(f"Cannot rename missing columns: {missing_str}")

    renamed_headers = [mappings.get(column, column) for column in headers]
    if len(set(renamed_headers)) != len(renamed_headers):
        raise ValueError("Column rename would create duplicate header names.")

    renamed_rows: list[dict[str, str]] = []
    for row in rows:
        renamed_rows.append({mappings.get(key, key): value for key, value in row.items()})

    return renamed_headers, renamed_rows


def _filter_rows(
    headers: list[str],
    rows: list[dict[str, str]],
    filter_column: str,
    filter_value: str,
) -> list[dict[str, str]]:
    """Filter rows by exact column value match."""
    if filter_column not in headers:
        raise ValueError(f"Filter column '{filter_column}' does not exist.")
    return [row for row in rows if row.get(filter_column, "") == filter_value]


def _deduplicate_rows(
    headers: list[str],
    rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Remove duplicate rows while preserving original order."""
    seen: set[tuple[str, ...]] = set()
    unique_rows: list[dict[str, str]] = []

    for row in rows:
        signature = tuple(row.get(column, "") for column in headers)
        if signature in seen:
            continue
        seen.add(signature)
        unique_rows.append(row)

    return unique_rows


def _write_csv(output_path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    """Write transformed data to CSV output path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def process_csv_file(
    input_path: Path,
    output_path: Path,
    *,
    remove_duplicates: bool = False,
    trim_whitespace: bool = False,
    rename_columns: dict[str, str] | None = None,
    filter_column: str | None = None,
    filter_value: str | None = None,
    dry_run: bool = False,
) -> CsvProcessSummary:
    """Process a CSV file and return a summary of the transformation."""
    if not input_path.exists() or not input_path.is_file():
        raise ValueError(f"Invalid CSV input path: {input_path}")

    headers, rows = _read_csv(input_path)
    input_count = len(rows)

    if trim_whitespace:
        rows = _trim_whitespace(rows)

    mappings = rename_columns or {}
    if mappings:
        headers, rows = _rename_columns(headers, rows, mappings)

    if filter_value is not None and filter_column is None:
        raise ValueError("Filtering requires both filter column and filter value.")
    if filter_column is not None:
        if filter_value is None:
            raise ValueError("Filtering requires both filter column and filter value.")
        rows = _filter_rows(headers, rows, filter_column, filter_value)

    if remove_duplicates:
        rows = _deduplicate_rows(headers, rows)

    if not dry_run:
        _write_csv(output_path, headers, rows)

    return CsvProcessSummary(
        input_rows=input_count,
        output_rows=len(rows),
        columns=headers,
    )
