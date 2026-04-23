"""CSV action reporting helpers."""

from __future__ import annotations

from collections import Counter
import csv
from pathlib import Path
from typing import Sequence

from python_automation_tool.models import ActionRecord

REPORT_COLUMNS = [
    "timestamp",
    "original_path",
    "new_path",
    "action_type",
    "status",
    "error_message",
]


def generate_action_report(records: Sequence[ActionRecord], output_path: Path) -> Path:
    """Write action records to a CSV report and return the report path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPORT_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_dict())
    return output_path


def summarize_statuses(records: Sequence[ActionRecord]) -> dict[str, int]:
    """Count records by status and include total action count."""
    counts = Counter(record.status for record in records)
    result = {key: value for key, value in counts.items()}
    result["total"] = len(records)
    return result
