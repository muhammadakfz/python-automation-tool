from __future__ import annotations

from python_automation_tool.history import save_last_operation, undo_last_operation
from python_automation_tool.models import ActionRecord


def test_undo_last_operation_restores_previous_name(tmp_path):
    source_path = tmp_path / "original.txt"
    moved_path = tmp_path / "renamed.txt"

    source_path.write_text("content", encoding="utf-8")
    source_path.rename(moved_path)

    history_file = tmp_path / "history.json"
    record = ActionRecord.create(
        original_path=str(source_path),
        new_path=str(moved_path),
        action_type="rename",
        status="success",
    )

    save_last_operation(
        operation_type="rename",
        command="rename --apply",
        records=[record],
        dry_run=False,
        history_path=history_file,
    )

    results = undo_last_operation(history_path=history_file, dry_run=False)

    assert source_path.exists()
    assert not moved_path.exists()
    assert len(results) == 1
    assert results[0].status == "success"
    assert not history_file.exists()


def test_undo_last_operation_dry_run_keeps_current_state(tmp_path):
    source_path = tmp_path / "original.txt"
    moved_path = tmp_path / "renamed.txt"

    source_path.write_text("content", encoding="utf-8")
    source_path.rename(moved_path)

    history_file = tmp_path / "history.json"
    record = ActionRecord.create(
        original_path=str(source_path),
        new_path=str(moved_path),
        action_type="rename",
        status="success",
    )

    save_last_operation(
        operation_type="rename",
        command="rename --apply",
        records=[record],
        dry_run=False,
        history_path=history_file,
    )

    results = undo_last_operation(history_path=history_file, dry_run=True)

    assert moved_path.exists()
    assert not source_path.exists()
    assert len(results) == 1
    assert results[0].status == "dry-run"
    assert history_file.exists()
