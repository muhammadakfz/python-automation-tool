from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"


def _run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(SRC_DIR)
        if not existing_pythonpath
        else f"{SRC_DIR}{os.pathsep}{existing_pythonpath}"
    )
    return subprocess.run(
        [sys.executable, "-m", "python_automation_tool", *args],
        cwd=cwd or PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_cli_rename_report_and_undo_round_trip(tmp_path):
    source = tmp_path / "workspace"
    source.mkdir()
    history_path = tmp_path / "history.json"
    rename_report = tmp_path / "rename_report.csv"
    exported_report = tmp_path / "exported_report.csv"
    undo_report = tmp_path / "undo_report.csv"

    (source / "alpha.txt").write_text("A", encoding="utf-8")
    (source / "beta.txt").write_text("B", encoding="utf-8")

    rename_result = _run_cli(
        "rename",
        "--source",
        str(source),
        "--prefix",
        "doc",
        "--apply",
        "--history-file",
        str(history_path),
        "--report-path",
        str(rename_report),
    )

    assert rename_result.returncode == 0, rename_result.stderr
    assert "Action summary:" in rename_result.stdout
    assert (source / "doc_001.txt").exists()
    assert (source / "doc_002.txt").exists()
    assert history_path.exists()
    rename_rows = _read_csv_rows(rename_report)
    assert len(rename_rows) == 2
    assert {row["status"] for row in rename_rows} == {"success"}

    report_result = _run_cli(
        "report",
        "--output",
        str(exported_report),
        "--history-file",
        str(history_path),
    )

    assert report_result.returncode == 0, report_result.stderr
    assert exported_report.exists()
    exported_rows = _read_csv_rows(exported_report)
    assert len(exported_rows) == 2

    undo_result = _run_cli(
        "undo",
        "--history-file",
        str(history_path),
        "--report-path",
        str(undo_report),
    )

    assert undo_result.returncode == 0, undo_result.stderr
    assert (source / "alpha.txt").exists()
    assert (source / "beta.txt").exists()
    assert not history_path.exists()
    undo_rows = _read_csv_rows(undo_report)
    assert len(undo_rows) == 2
    assert {row["status"] for row in undo_rows} == {"success"}


def test_cli_process_csv_generates_output_and_report(tmp_path):
    input_path = tmp_path / "raw.csv"
    output_path = tmp_path / "clean.csv"
    report_path = tmp_path / "csv_report.csv"

    input_path.write_text(
        "Name,Role\n Alice , Dev \nBob,Dev\nAlice,Dev\n",
        encoding="utf-8",
    )

    result = _run_cli(
        "process-csv",
        "--input",
        str(input_path),
        "--output",
        str(output_path),
        "--trim-whitespace",
        "--remove-duplicates",
        "--rename-column",
        "Name:full_name",
        "--filter-column",
        "Role",
        "--filter-value",
        "Dev",
        "--report-path",
        str(report_path),
    )

    assert result.returncode == 0, result.stderr
    assert "Rows processed: 3 -> 2" in result.stdout
    assert output_path.exists()
    assert report_path.exists()
    rows = _read_csv_rows(output_path)
    assert [row["full_name"] for row in rows] == ["Alice", "Bob"]
    report_rows = _read_csv_rows(report_path)
    assert len(report_rows) == 1
    assert report_rows[0]["status"] == "success"


def test_cli_organize_dry_run_with_filters_reports_preview(tmp_path):
    source = tmp_path / "workspace"
    source.mkdir()
    report_path = tmp_path / "organize_report.csv"

    (source / "invoice.pdf").write_text("important", encoding="utf-8")
    (source / "notes.txt").write_text("ignore", encoding="utf-8")

    result = _run_cli(
        "organize",
        "--source",
        str(source),
        "--include-ext",
        ".pdf",
        "--keyword",
        "invoice",
        "--dry-run",
        "--report-path",
        str(report_path),
    )

    assert result.returncode == 0, result.stderr
    assert "dry-run" in result.stdout
    assert (source / "invoice.pdf").exists()
    assert not (source / "documents" / "invoice.pdf").exists()
    report_rows = _read_csv_rows(report_path)
    assert len(report_rows) == 1
    assert report_rows[0]["status"] == "dry-run"
