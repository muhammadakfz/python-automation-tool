from __future__ import annotations

import csv

import pytest

from python_automation_tool.csv_processor import process_csv_file


def _read_rows(path):
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_process_csv_file_applies_all_transformations(tmp_path):
    input_path = tmp_path / "raw.csv"
    output_path = tmp_path / "clean.csv"

    input_path.write_text(
        "Name,Role\n Alice , Dev \nBob,Dev\nAlice,Dev\n",
        encoding="utf-8",
    )

    summary = process_csv_file(
        input_path=input_path,
        output_path=output_path,
        remove_duplicates=True,
        trim_whitespace=True,
        rename_columns={"Name": "full_name"},
        filter_column="Role",
        filter_value="Dev",
        dry_run=False,
    )

    assert summary.input_rows == 3
    assert summary.output_rows == 2
    assert summary.columns == ["full_name", "Role"]

    rows = _read_rows(output_path)
    assert rows[0]["full_name"] == "Alice"
    assert rows[1]["full_name"] == "Bob"


def test_process_csv_file_dry_run_does_not_write_output(tmp_path):
    input_path = tmp_path / "raw.csv"
    output_path = tmp_path / "clean.csv"

    input_path.write_text("Name\nAlice\n", encoding="utf-8")

    summary = process_csv_file(
        input_path=input_path,
        output_path=output_path,
        dry_run=True,
    )

    assert summary.input_rows == 1
    assert summary.output_rows == 1
    assert not output_path.exists()


def test_process_csv_file_rejects_missing_header(tmp_path):
    input_path = tmp_path / "invalid.csv"
    output_path = tmp_path / "clean.csv"

    input_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError):
        process_csv_file(input_path=input_path, output_path=output_path)


def test_process_csv_file_rejects_duplicate_headers_after_normalization(tmp_path):
    input_path = tmp_path / "invalid.csv"
    output_path = tmp_path / "clean.csv"

    input_path.write_text("Name, Name \nAlice,Bob\n", encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate column names"):
        process_csv_file(input_path=input_path, output_path=output_path)


def test_process_csv_file_requires_filter_column_when_filter_value_is_set(tmp_path):
    input_path = tmp_path / "raw.csv"
    output_path = tmp_path / "clean.csv"

    input_path.write_text("Name\nAlice\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Filtering requires both filter column and filter value"):
        process_csv_file(
            input_path=input_path,
            output_path=output_path,
            filter_value="Alice",
        )
