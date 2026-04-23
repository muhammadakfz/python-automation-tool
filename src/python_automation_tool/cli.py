"""Command line interface for python-automation-tool."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from python_automation_tool.batch_renamer import build_rename_plan, execute_rename_plan
from python_automation_tool.csv_processor import process_csv_file
from python_automation_tool.file_operations import organize_files
from python_automation_tool.filters import FileFilterCriteria
from python_automation_tool.history import load_last_operation, save_last_operation, undo_last_operation
from python_automation_tool.logging_config import configure_logging
from python_automation_tool.models import ActionRecord, RenamePlanItem
from python_automation_tool.reporting import generate_action_report, summarize_statuses
from python_automation_tool.utils import parse_column_mappings, parse_extensions


def _path(value: str) -> Path:
    """Argparse path converter that expands home paths."""
    return Path(value).expanduser()


def _add_filter_arguments(parser: argparse.ArgumentParser) -> None:
    """Attach shared file filter arguments to a subcommand parser."""
    parser.add_argument(
        "--include-ext",
        nargs="+",
        help="Only include file extensions (for example: --include-ext .jpg .png csv).",
    )
    parser.add_argument(
        "--exclude-ext",
        nargs="+",
        help="Exclude file extensions from processing.",
    )
    parser.add_argument(
        "--keyword",
        type=str,
        help="Only include files whose names contain this keyword.",
    )
    parser.add_argument(
        "--min-size",
        type=int,
        help="Minimum file size in bytes.",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        help="Maximum file size in bytes.",
    )


def _add_batch_output_arguments(parser: argparse.ArgumentParser) -> None:
    """Attach shared dry-run/report/history arguments to a parser."""
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without changing files.",
    )
    parser.add_argument(
        "--report-path",
        type=_path,
        help="Optional path to write CSV report for this command.",
    )
    parser.add_argument(
        "--history-file",
        type=_path,
        help="Optional path for operation history JSON used by undo.",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="python-automation-tool",
        description=(
            "Automate repetitive file and CSV workflows: organize files, "
            "rename batches, process CSVs, and undo the latest batch operation."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose console logging.",
    )
    parser.add_argument(
        "--log-file",
        type=_path,
        help="Optional log file path for detailed execution logs.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    organize_parser = subparsers.add_parser(
        "organize",
        help="Organize files by extension categories.",
    )
    organize_parser.add_argument(
        "--source",
        type=_path,
        required=True,
        help="Source directory to scan and organize.",
    )
    organize_parser.add_argument(
        "--recursive",
        action="store_true",
        help="Scan files recursively in nested folders.",
    )
    _add_filter_arguments(organize_parser)
    _add_batch_output_arguments(organize_parser)

    rename_parser = subparsers.add_parser(
        "rename",
        help="Preview and rename files with numbered format.",
    )
    rename_parser.add_argument(
        "--source",
        type=_path,
        required=True,
        help="Source directory containing files to rename.",
    )
    rename_parser.add_argument(
        "--prefix",
        type=str,
        required=True,
        help="Prefix for renamed files (for example: invoice).",
    )
    rename_parser.add_argument(
        "--start-number",
        type=int,
        default=1,
        help="Starting number for sequence (default: 1).",
    )
    rename_parser.add_argument(
        "--recursive",
        action="store_true",
        help="Rename files recursively in nested folders.",
    )
    rename_parser.add_argument(
        "--lower-ext",
        action="store_true",
        help="Normalize renamed file extensions to lowercase.",
    )
    rename_parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the rename plan. Without this flag, only preview is shown.",
    )
    _add_filter_arguments(rename_parser)
    _add_batch_output_arguments(rename_parser)

    csv_parser = subparsers.add_parser(
        "process-csv",
        help="Clean and transform CSV files.",
    )
    csv_parser.add_argument(
        "--input",
        type=_path,
        required=True,
        help="Input CSV path.",
    )
    csv_parser.add_argument(
        "--output",
        type=_path,
        required=True,
        help="Output CSV path for cleaned result.",
    )
    csv_parser.add_argument(
        "--remove-duplicates",
        action="store_true",
        help="Remove duplicate rows.",
    )
    csv_parser.add_argument(
        "--trim-whitespace",
        action="store_true",
        help="Trim surrounding whitespace in all fields.",
    )
    csv_parser.add_argument(
        "--rename-column",
        action="append",
        help="Rename a column using OLD:NEW. Repeat for multiple columns.",
    )
    csv_parser.add_argument(
        "--filter-column",
        type=str,
        help="Column name for value-based filtering.",
    )
    csv_parser.add_argument(
        "--filter-value",
        type=str,
        help="Column value used by --filter-column.",
    )
    csv_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview row transformations without writing output.",
    )
    csv_parser.add_argument(
        "--report-path",
        type=_path,
        help="Optional path to write CSV report for this command.",
    )

    undo_parser = subparsers.add_parser(
        "undo",
        help="Undo the latest organize/rename batch operation.",
    )
    undo_parser.add_argument(
        "--history-file",
        type=_path,
        help="Optional path for operation history JSON used by undo.",
    )
    undo_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview undo actions without changing files.",
    )
    undo_parser.add_argument(
        "--report-path",
        type=_path,
        help="Optional path to write CSV report for this command.",
    )

    report_parser = subparsers.add_parser(
        "report",
        help="Export the latest operation history as a CSV report.",
    )
    report_parser.add_argument(
        "--output",
        type=_path,
        required=True,
        help="Output path for exported report CSV.",
    )
    report_parser.add_argument(
        "--history-file",
        type=_path,
        help="Optional path for operation history JSON.",
    )

    return parser


def _build_filter_criteria(args: argparse.Namespace) -> FileFilterCriteria:
    """Create and validate filter criteria from parsed command args."""
    criteria = FileFilterCriteria(
        include_extensions=parse_extensions(getattr(args, "include_ext", None)) or None,
        exclude_extensions=parse_extensions(getattr(args, "exclude_ext", None)) or None,
        keyword=getattr(args, "keyword", None),
        min_size_bytes=getattr(args, "min_size", None),
        max_size_bytes=getattr(args, "max_size", None),
    )
    criteria.validate()
    return criteria


def _safe_relative(path: Path, root: Path) -> str:
    """Return a relative path when possible, otherwise full path string."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _print_rename_preview(
    plan: Sequence[RenamePlanItem],
    source_dir: Path,
    limit: int = 30,
) -> None:
    """Render a concise preview table for rename operations."""
    print(f"Previewing {len(plan)} rename action(s):")
    print("index | source -> destination")
    print("------|-----------------------")

    for index, item in enumerate(plan[:limit], start=1):
        source_display = _safe_relative(item.source, source_dir)
        destination_display = _safe_relative(item.destination, source_dir)
        print(f"{index:>5} | {source_display} -> {destination_display}")

    remaining = len(plan) - limit
    if remaining > 0:
        print(f"... {remaining} additional action(s) not shown")


def _print_action_summary(records: Sequence[ActionRecord]) -> None:
    """Print command result summary by status."""
    summary = summarize_statuses(records)
    print("Action summary:")
    print(f"  total   : {summary.get('total', 0)}")
    for status in ("success", "dry-run", "skipped", "failed"):
        if status in summary:
            print(f"  {status:<7}: {summary[status]}")


def _write_report_if_requested(
    records: Sequence[ActionRecord],
    report_path: Path | None,
    logger: logging.Logger,
) -> None:
    """Write CSV report when path is provided."""
    if report_path is None:
        return
    written_path = generate_action_report(records, report_path)
    logger.info("Report written to %s", written_path)


def _persist_history_if_needed(
    operation_type: str,
    args: argparse.Namespace,
    records: Sequence[ActionRecord],
    logger: logging.Logger,
) -> None:
    """Save last operation history for undo when command changed files."""
    if getattr(args, "dry_run", False):
        return

    if not any(record.status == "success" for record in records):
        return

    history_path = save_last_operation(
        operation_type=operation_type,
        command=" ".join(sys.argv),
        records=list(records),
        dry_run=False,
        history_path=getattr(args, "history_file", None),
    )
    logger.info("Operation history saved to %s", history_path)


def _exit_code_from_records(records: Sequence[ActionRecord]) -> int:
    """Return non-zero when there are failed records."""
    return 1 if any(record.status == "failed" for record in records) else 0


def _handle_organize(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Execute the organize subcommand."""
    try:
        filters = _build_filter_criteria(args)
        records = organize_files(
            source_dir=args.source,
            recursive=args.recursive,
            filters=filters,
            dry_run=args.dry_run,
            logger=logger,
        )
    except Exception as exc:
        logger.error("Organize failed: %s", exc)
        return 1

    if not records:
        print("No files matched the selected criteria.")
        return 0

    _write_report_if_requested(records, args.report_path, logger)
    _persist_history_if_needed("organize", args, records, logger)
    _print_action_summary(records)
    return _exit_code_from_records(records)


def _handle_rename(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Execute preview/apply behavior for batch rename."""
    try:
        filters = _build_filter_criteria(args)
        plan = build_rename_plan(
            source_dir=args.source,
            prefix=args.prefix,
            start_number=args.start_number,
            recursive=args.recursive,
            lowercase_extension=args.lower_ext,
            filters=filters,
        )
    except Exception as exc:
        logger.error("Rename planning failed: %s", exc)
        return 1

    if not plan:
        print("No files matched the selected criteria.")
        return 0

    _print_rename_preview(plan, source_dir=args.source)

    if not args.apply:
        print("Preview only. Re-run with --apply to execute renaming.")
        return 0

    records = execute_rename_plan(plan, dry_run=args.dry_run, logger=logger)
    _write_report_if_requested(records, args.report_path, logger)
    _persist_history_if_needed("rename", args, records, logger)
    _print_action_summary(records)
    return _exit_code_from_records(records)


def _handle_process_csv(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Execute CSV cleanup and transformation command."""
    record: ActionRecord

    try:
        mappings = parse_column_mappings(args.rename_column)
        summary = process_csv_file(
            input_path=args.input,
            output_path=args.output,
            remove_duplicates=args.remove_duplicates,
            trim_whitespace=args.trim_whitespace,
            rename_columns=mappings,
            filter_column=args.filter_column,
            filter_value=args.filter_value,
            dry_run=args.dry_run,
        )
        status = "dry-run" if args.dry_run else "success"
        record = ActionRecord.create(
            original_path=str(args.input),
            new_path=str(args.output),
            action_type="process-csv",
            status=status,
            error_message="",
        )

        print(
            "Rows processed: "
            f"{summary.input_rows} -> {summary.output_rows} | "
            f"Columns: {', '.join(summary.columns)}"
        )
    except Exception as exc:
        logger.error("CSV processing failed: %s", exc)
        record = ActionRecord.create(
            original_path=str(args.input),
            new_path=str(args.output),
            action_type="process-csv",
            status="failed",
            error_message=str(exc),
        )

    records = [record]
    _write_report_if_requested(records, args.report_path, logger)
    _print_action_summary(records)
    return _exit_code_from_records(records)


def _handle_undo(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Execute undo of the latest stored batch operation."""
    try:
        records = undo_last_operation(
            history_path=args.history_file,
            dry_run=args.dry_run,
            logger=logger,
        )
    except Exception as exc:
        logger.error("Undo failed: %s", exc)
        return 1

    _write_report_if_requested(records, args.report_path, logger)
    _print_action_summary(records)
    return _exit_code_from_records(records)


def _handle_report(args: argparse.Namespace, logger: logging.Logger) -> int:
    """Export CSV report from latest saved operation history."""
    try:
        operation = load_last_operation(args.history_file)
        if operation is None:
            raise FileNotFoundError("No operation history available to export.")

        generate_action_report(operation.records, args.output)
        print(f"Report exported: {args.output}")
        return 0
    except Exception as exc:
        logger.error("Report export failed: %s", exc)
        return 1


def main(argv: Sequence[str] | None = None) -> int:
    """CLI program entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)
    logger = configure_logging(verbose=args.verbose, log_file=args.log_file)

    handlers = {
        "organize": _handle_organize,
        "rename": _handle_rename,
        "process-csv": _handle_process_csv,
        "undo": _handle_undo,
        "report": _handle_report,
    }

    handler = handlers[args.command]
    return handler(args, logger)


if __name__ == "__main__":
    raise SystemExit(main())
