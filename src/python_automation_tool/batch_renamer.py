"""Batch file rename workflows with preview-first behavior."""

from __future__ import annotations

from collections import defaultdict
import logging
from pathlib import Path
from uuid import uuid4

from python_automation_tool.file_operations import scan_files
from python_automation_tool.filters import FileFilterCriteria, matches_filters
from python_automation_tool.models import ActionRecord, RenamePlanItem


def _allocate_unique_name(desired_name: str, used_names: set[str]) -> str:
    """Allocate a unique filename inside one directory."""
    if desired_name not in used_names:
        used_names.add(desired_name)
        return desired_name

    base = Path(desired_name)
    stem = base.stem
    suffix = base.suffix
    counter = 1
    while True:
        candidate = f"{stem}_{counter:03d}{suffix}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        counter += 1


def build_rename_plan(
    source_dir: Path,
    prefix: str,
    start_number: int = 1,
    recursive: bool = False,
    lowercase_extension: bool = False,
    filters: FileFilterCriteria | None = None,
) -> list[RenamePlanItem]:
    """Build a deterministic rename plan without modifying files."""
    if not source_dir.exists() or not source_dir.is_dir():
        raise ValueError(f"Invalid source directory: {source_dir}")
    if not prefix.strip():
        raise ValueError("Prefix cannot be empty.")
    if start_number < 0:
        raise ValueError("Start number must be greater than or equal to zero.")

    if filters is not None:
        filters.validate()

    all_files = scan_files(source_dir, recursive=recursive)
    if not all_files:
        raise ValueError("Source directory contains no files to rename.")

    selected_files: list[Path] = []
    for file_path in sorted(all_files, key=lambda item: (str(item.parent).lower(), item.name.lower())):
        try:
            if matches_filters(file_path, filters):
                selected_files.append(file_path)
        except OSError:
            continue

    used_names_by_directory: dict[Path, set[str]] = defaultdict(set)
    selected_names_by_directory: dict[Path, set[str]] = defaultdict(set)

    for file_path in selected_files:
        selected_names_by_directory[file_path.parent].add(file_path.name)

    for directory, selected_names in selected_names_by_directory.items():
        try:
            existing_names = {
                entry.name for entry in directory.iterdir() if entry.is_file()
            }
        except OSError:
            existing_names = set()
        used_names_by_directory[directory] = existing_names - selected_names

    plan: list[RenamePlanItem] = []
    number = start_number

    for file_path in selected_files:
        extension = file_path.suffix.lower() if lowercase_extension else file_path.suffix
        desired_name = f"{prefix}_{number:03d}{extension}"
        final_name = _allocate_unique_name(
            desired_name,
            used_names_by_directory[file_path.parent],
        )
        destination = file_path.with_name(final_name)
        plan.append(RenamePlanItem(source=file_path, destination=destination))
        number += 1

    return plan


def _rollback_staged(
    staged_items: list[tuple[RenamePlanItem, Path]],
    logger: logging.Logger | None = None,
) -> None:
    """Rollback staged temporary names back to original names."""
    for item, temporary_path in reversed(staged_items):
        if not temporary_path.exists():
            continue
        try:
            temporary_path.rename(item.source)
        except OSError as exc:
            if logger is not None:
                logger.error(
                    "Rollback failed for %s -> %s: %s",
                    temporary_path,
                    item.source,
                    exc,
                )


def _rollback_after_commit_failure(
    committed_items: list[RenamePlanItem],
    current_item: RenamePlanItem,
    current_temp_path: Path,
    pending_items: list[tuple[RenamePlanItem, Path]],
    logger: logging.Logger | None = None,
) -> None:
    """Rollback all rename stages when commit phase fails."""
    if current_temp_path.exists():
        try:
            current_temp_path.rename(current_item.source)
        except OSError as exc:
            if logger is not None:
                logger.error(
                    "Rollback failed for %s -> %s: %s",
                    current_temp_path,
                    current_item.source,
                    exc,
                )

    _rollback_staged(pending_items, logger=logger)

    for item in reversed(committed_items):
        if not item.destination.exists():
            continue
        try:
            item.destination.rename(item.source)
        except OSError as exc:
            if logger is not None:
                logger.error(
                    "Rollback failed for %s -> %s: %s",
                    item.destination,
                    item.source,
                    exc,
                )


def execute_rename_plan(
    plan: list[RenamePlanItem],
    dry_run: bool = False,
    logger: logging.Logger | None = None,
) -> list[ActionRecord]:
    """Execute a rename plan with collision-safe two-phase renaming."""
    records: list[ActionRecord] = []

    if not plan:
        return records

    if dry_run:
        for item in plan:
            status = "skipped" if item.source == item.destination else "dry-run"
            message = "" if status == "dry-run" else "Destination equals source path."
            records.append(
                ActionRecord.create(
                    original_path=str(item.source),
                    new_path=str(item.destination),
                    action_type="rename",
                    status=status,
                    error_message=message,
                )
            )
        return records

    staged_items: list[tuple[RenamePlanItem, Path]] = []

    for item in plan:
        if not item.source.exists():
            records.append(
                ActionRecord.create(
                    original_path=str(item.source),
                    new_path=str(item.destination),
                    action_type="rename",
                    status="failed",
                    error_message="Source file does not exist.",
                )
            )
            continue

        if item.source.resolve() == item.destination.resolve():
            records.append(
                ActionRecord.create(
                    original_path=str(item.source),
                    new_path=str(item.destination),
                    action_type="rename",
                    status="skipped",
                    error_message="Destination equals source path.",
                )
            )
            continue

        temporary_path = item.source.with_name(
            f".python_automation_tmp_{uuid4().hex}{item.source.suffix}"
        )

        try:
            item.source.rename(temporary_path)
            staged_items.append((item, temporary_path))
        except OSError as exc:
            records.append(
                ActionRecord.create(
                    original_path=str(item.source),
                    new_path=str(item.destination),
                    action_type="rename",
                    status="failed",
                    error_message=str(exc),
                )
            )
            _rollback_staged(staged_items, logger=logger)
            return records

    committed_items: list[RenamePlanItem] = []

    for index, (item, temporary_path) in enumerate(staged_items):
        try:
            if item.destination.exists():
                raise FileExistsError(
                    f"Destination already exists: {item.destination}"
                )
            temporary_path.rename(item.destination)
            committed_items.append(item)
            records.append(
                ActionRecord.create(
                    original_path=str(item.source),
                    new_path=str(item.destination),
                    action_type="rename",
                    status="success",
                )
            )
        except OSError as exc:
            records.append(
                ActionRecord.create(
                    original_path=str(item.source),
                    new_path=str(item.destination),
                    action_type="rename",
                    status="failed",
                    error_message=str(exc),
                )
            )
            pending_items = staged_items[index + 1 :]
            _rollback_after_commit_failure(
                committed_items=committed_items,
                current_item=item,
                current_temp_path=temporary_path,
                pending_items=pending_items,
                logger=logger,
            )
            return records

    if logger is not None:
        logger.info("Rename completed with %d action records.", len(records))

    return records
