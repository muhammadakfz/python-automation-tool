"""Persist and restore last batch operation for undo support."""

from __future__ import annotations

import json
import logging
from pathlib import Path
import shutil

from python_automation_tool.models import ActionRecord, BatchOperation
from python_automation_tool.utils import ensure_directory, find_unique_path, utc_timestamp

DEFAULT_HISTORY_PATH = Path.home() / ".python_automation_tool" / "last_operation.json"
UNDOABLE_ACTIONS = {"organize", "rename"}


def resolve_history_path(history_path: Path | None = None) -> Path:
    """Resolve configured or default history path."""
    return history_path.expanduser() if history_path is not None else DEFAULT_HISTORY_PATH


def save_last_operation(
    operation_type: str,
    command: str,
    records: list[ActionRecord],
    dry_run: bool,
    history_path: Path | None = None,
) -> Path:
    """Save batch operation metadata and action records to JSON."""
    target_path = resolve_history_path(history_path)
    ensure_directory(target_path.parent)

    operation = BatchOperation(
        operation_type=operation_type,
        command=command,
        created_at=utc_timestamp(),
        dry_run=dry_run,
        records=records,
    )

    target_path.write_text(
        json.dumps(operation.to_dict(), indent=2),
        encoding="utf-8",
    )
    return target_path


def load_last_operation(history_path: Path | None = None) -> BatchOperation | None:
    """Load last batch operation if history file exists."""
    target_path = resolve_history_path(history_path)
    if not target_path.exists():
        return None

    payload = json.loads(target_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("History file format is invalid.")

    return BatchOperation.from_dict(payload)


def undo_last_operation(
    history_path: Path | None = None,
    dry_run: bool = False,
    logger: logging.Logger | None = None,
) -> list[ActionRecord]:
    """Undo the most recent successful file move/rename batch where possible."""
    target_path = resolve_history_path(history_path)
    operation = load_last_operation(target_path)

    if operation is None:
        raise FileNotFoundError(
            f"No history file found at {target_path}. Run organize/rename first."
        )

    if operation.dry_run:
        raise ValueError("The last operation was a dry run and cannot be undone.")

    undoable_records = [
        record
        for record in operation.records
        if record.status == "success"
        and record.action_type in UNDOABLE_ACTIONS
        and record.original_path
        and record.new_path
        and record.original_path != record.new_path
    ]

    if not undoable_records:
        raise ValueError("No undoable actions were found in the last operation.")

    results: list[ActionRecord] = []

    for record in reversed(undoable_records):
        current_path = Path(record.new_path)
        desired_original = Path(record.original_path)

        if not current_path.exists():
            results.append(
                ActionRecord.create(
                    original_path=str(current_path),
                    new_path=str(desired_original),
                    action_type="undo",
                    status="failed",
                    error_message="Current file path does not exist.",
                )
            )
            continue

        destination = desired_original
        warning_message = ""

        if destination.exists() and destination.resolve() != current_path.resolve():
            destination = find_unique_path(destination)
            warning_message = (
                "Original path already existed; restored file to a unique path instead."
            )

        if dry_run:
            results.append(
                ActionRecord.create(
                    original_path=str(current_path),
                    new_path=str(destination),
                    action_type="undo",
                    status="dry-run",
                    error_message=warning_message,
                )
            )
            continue

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(current_path), str(destination))
            results.append(
                ActionRecord.create(
                    original_path=str(current_path),
                    new_path=str(destination),
                    action_type="undo",
                    status="success",
                    error_message=warning_message,
                )
            )
        except OSError as exc:
            results.append(
                ActionRecord.create(
                    original_path=str(current_path),
                    new_path=str(destination),
                    action_type="undo",
                    status="failed",
                    error_message=str(exc),
                )
            )

    has_failures = any(result.status == "failed" for result in results)
    if not dry_run and not has_failures:
        target_path.unlink(missing_ok=True)

    if logger is not None:
        logger.info("Undo completed with %d action records.", len(results))

    return results
