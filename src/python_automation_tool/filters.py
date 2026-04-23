"""File filtering rules shared by organize and rename commands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class FileFilterCriteria:
    """Filter criteria for selecting files to process."""

    include_extensions: set[str] | None = None
    exclude_extensions: set[str] | None = None
    keyword: str | None = None
    min_size_bytes: int | None = None
    max_size_bytes: int | None = None

    def validate(self) -> None:
        """Validate criteria consistency and numeric constraints."""
        if self.min_size_bytes is not None and self.min_size_bytes < 0:
            raise ValueError("Minimum size must be greater than or equal to zero.")
        if self.max_size_bytes is not None and self.max_size_bytes < 0:
            raise ValueError("Maximum size must be greater than or equal to zero.")
        if (
            self.min_size_bytes is not None
            and self.max_size_bytes is not None
            and self.min_size_bytes > self.max_size_bytes
        ):
            raise ValueError("Minimum size cannot be greater than maximum size.")


def matches_filters(file_path: Path, criteria: FileFilterCriteria | None) -> bool:
    """Return True when a file path satisfies the provided criteria."""
    if criteria is None:
        return True

    extension = file_path.suffix.lower()
    include = criteria.include_extensions or set()
    exclude = criteria.exclude_extensions or set()

    if include and extension not in include:
        return False
    if exclude and extension in exclude:
        return False

    if criteria.keyword and criteria.keyword.lower() not in file_path.name.lower():
        return False

    if criteria.min_size_bytes is not None or criteria.max_size_bytes is not None:
        size = file_path.stat().st_size
        if criteria.min_size_bytes is not None and size < criteria.min_size_bytes:
            return False
        if criteria.max_size_bytes is not None and size > criteria.max_size_bytes:
            return False

    return True
