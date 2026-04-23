"""General utility functions for path, parsing, and timestamp handling."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


def utc_timestamp() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def ensure_directory(path: Path) -> None:
    """Create the directory path if it does not already exist."""
    path.mkdir(parents=True, exist_ok=True)


def normalize_extension(extension: str) -> str:
    """Normalize user input extension into lowercase .ext format."""
    cleaned = extension.strip().lower()
    if not cleaned:
        return ""
    if not cleaned.startswith("."):
        cleaned = f".{cleaned}"
    return cleaned


def parse_extensions(values: Sequence[str] | None) -> set[str]:
    """Parse one or more extension args into a normalized extension set."""
    extensions: set[str] = set()
    if not values:
        return extensions

    for value in values:
        for part in value.split(","):
            normalized = normalize_extension(part)
            if normalized:
                extensions.add(normalized)
    return extensions


def parse_column_mappings(values: Sequence[str] | None) -> dict[str, str]:
    """Parse repeated OLD:NEW mappings used for CSV column rename."""
    mappings: dict[str, str] = {}
    if not values:
        return mappings

    for raw in values:
        if ":" not in raw:
            raise ValueError(
                f"Invalid rename mapping '{raw}'. Use the OLD:NEW format."
            )
        old, new = (part.strip() for part in raw.split(":", 1))
        if not old or not new:
            raise ValueError(
                f"Invalid rename mapping '{raw}'. OLD and NEW names are required."
            )
        mappings[old] = new
    return mappings


def find_unique_path(path: Path) -> Path:
    """Return a non-conflicting path by appending an incrementing numeric suffix."""
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    counter = 1
    while True:
        candidate = path.with_name(f"{stem}_{counter:03d}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1
