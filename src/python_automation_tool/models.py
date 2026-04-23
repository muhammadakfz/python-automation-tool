"""Shared data models used across the automation tool."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from python_automation_tool.utils import utc_timestamp


@dataclass(slots=True)
class ActionRecord:
    """Represents one file or CSV action outcome."""

    timestamp: str
    original_path: str
    new_path: str
    action_type: str
    status: str
    error_message: str = ""

    @classmethod
    def create(
        cls,
        original_path: str,
        new_path: str,
        action_type: str,
        status: str,
        error_message: str = "",
    ) -> "ActionRecord":
        """Create an action record with a generated UTC timestamp."""
        return cls(
            timestamp=utc_timestamp(),
            original_path=original_path,
            new_path=new_path,
            action_type=action_type,
            status=status,
            error_message=error_message,
        )

    def to_dict(self) -> dict[str, str]:
        """Serialize the action for reports and history files."""
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, str]) -> "ActionRecord":
        """Deserialize an action record from dictionary data."""
        return cls(
            timestamp=payload.get("timestamp", utc_timestamp()),
            original_path=payload.get("original_path", ""),
            new_path=payload.get("new_path", ""),
            action_type=payload.get("action_type", "unknown"),
            status=payload.get("status", "unknown"),
            error_message=payload.get("error_message", ""),
        )


@dataclass(slots=True)
class BatchOperation:
    """Stores one command batch so the last batch can be undone."""

    operation_type: str
    command: str
    created_at: str
    dry_run: bool
    records: list[ActionRecord]

    def to_dict(self) -> dict[str, object]:
        """Serialize operation data into JSON-compatible structure."""
        return {
            "operation_type": self.operation_type,
            "command": self.command,
            "created_at": self.created_at,
            "dry_run": self.dry_run,
            "records": [record.to_dict() for record in self.records],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "BatchOperation":
        """Deserialize operation data from dictionary payload."""
        raw_records = payload.get("records", [])
        records = [
            ActionRecord.from_dict(item)
            for item in raw_records
            if isinstance(item, dict)
        ]
        return cls(
            operation_type=str(payload.get("operation_type", "unknown")),
            command=str(payload.get("command", "")),
            created_at=str(payload.get("created_at", utc_timestamp())),
            dry_run=bool(payload.get("dry_run", False)),
            records=records,
        )


@dataclass(slots=True)
class RenamePlanItem:
    """Captures one source-to-destination rename step."""

    source: Path
    destination: Path


@dataclass(slots=True)
class CsvProcessSummary:
    """Summarizes CSV input/output row counts and columns."""

    input_rows: int
    output_rows: int
    columns: list[str]
