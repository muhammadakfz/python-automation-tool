"""File scanning and organization workflows."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from python_automation_tool.filters import FileFilterCriteria, matches_filters
from python_automation_tool.models import ActionRecord
from python_automation_tool.utils import find_unique_path

CATEGORY_EXTENSIONS: dict[str, set[str]] = {
    "images": {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".svg",
        ".webp",
        ".tif",
        ".tiff",
    },
    "documents": {
        ".pdf",
        ".doc",
        ".docx",
        ".txt",
        ".rtf",
        ".odt",
        ".md",
        ".ppt",
        ".pptx",
    },
    "spreadsheets": {".csv", ".xls", ".xlsx", ".ods"},
    "code": {
        ".py",
        ".js",
        ".ts",
        ".java",
        ".c",
        ".cpp",
        ".cs",
        ".go",
        ".rs",
        ".html",
        ".css",
        ".json",
        ".yaml",
        ".yml",
        ".sh",
        ".sql",
    },
    "archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
    "audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"},
    "video": {".mp4", ".mov", ".mkv", ".avi", ".wmv", ".webm"},
}
DEFAULT_CATEGORY = "others"


def scan_files(source_dir: Path, recursive: bool = False) -> list[Path]:
    """Return all files in a directory, optionally including nested folders."""
    pattern = "**/*" if recursive else "*"
    return [entry for entry in source_dir.glob(pattern) if entry.is_file()]


def categorize_file(file_path: Path) -> str:
    """Map a file extension to a destination category folder."""
    extension = file_path.suffix.lower()
    for category, extensions in CATEGORY_EXTENSIONS.items():
        if extension in extensions:
            return category
    return DEFAULT_CATEGORY


def _is_in_category_folder(file_path: Path, source_dir: Path) -> bool:
    """Check whether a file already sits under a category folder."""
    try:
        relative = file_path.relative_to(source_dir)
    except ValueError:
        return False

    if not relative.parts:
        return False

    first_part = relative.parts[0]
    all_categories = set(CATEGORY_EXTENSIONS).union({DEFAULT_CATEGORY})
    if first_part not in all_categories:
        return False

    parent = file_path.parent
    if parent == source_dir / first_part:
        return categorize_file(file_path) == first_part

    return False


def organize_files(
    source_dir: Path,
    recursive: bool = False,
    filters: FileFilterCriteria | None = None,
    dry_run: bool = False,
    logger: logging.Logger | None = None,
) -> list[ActionRecord]:
    """Organize files in a source directory by extension categories.

    Files are moved into category folders created inside the source directory.
    Duplicate names are handled with numeric suffixes.
    """
    if not source_dir.exists() or not source_dir.is_dir():
        raise ValueError(f"Invalid source directory: {source_dir}")

    if filters is not None:
        filters.validate()

    files = scan_files(source_dir, recursive=recursive)
    if not files:
        raise ValueError("Source directory contains no files to organize.")

    records: list[ActionRecord] = []

    for file_path in files:
        if _is_in_category_folder(file_path, source_dir):
            continue

        try:
            if not matches_filters(file_path, filters):
                continue
        except OSError as exc:
            records.append(
                ActionRecord.create(
                    original_path=str(file_path),
                    new_path=str(file_path),
                    action_type="organize",
                    status="failed",
                    error_message=str(exc),
                )
            )
            continue

        category = categorize_file(file_path)
        destination_dir = source_dir / category
        destination_path = destination_dir / file_path.name
        final_destination = find_unique_path(destination_path)

        if file_path.resolve() == final_destination.resolve():
            records.append(
                ActionRecord.create(
                    original_path=str(file_path),
                    new_path=str(final_destination),
                    action_type="organize",
                    status="skipped",
                    error_message="File is already in the target category.",
                )
            )
            continue

        if dry_run:
            records.append(
                ActionRecord.create(
                    original_path=str(file_path),
                    new_path=str(final_destination),
                    action_type="organize",
                    status="dry-run",
                )
            )
            continue

        try:
            destination_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file_path), str(final_destination))
            records.append(
                ActionRecord.create(
                    original_path=str(file_path),
                    new_path=str(final_destination),
                    action_type="organize",
                    status="success",
                )
            )
        except PermissionError as exc:
            records.append(
                ActionRecord.create(
                    original_path=str(file_path),
                    new_path=str(final_destination),
                    action_type="organize",
                    status="failed",
                    error_message=f"Permission denied: {exc}",
                )
            )
        except OSError as exc:
            records.append(
                ActionRecord.create(
                    original_path=str(file_path),
                    new_path=str(final_destination),
                    action_type="organize",
                    status="failed",
                    error_message=str(exc),
                )
            )

    if logger is not None:
        logger.info("Organize completed with %d action records.", len(records))

    return records
