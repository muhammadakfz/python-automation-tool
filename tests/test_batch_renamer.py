from __future__ import annotations

from python_automation_tool.batch_renamer import build_rename_plan, execute_rename_plan


def test_build_rename_plan_generates_expected_numbering(tmp_path):
    source = tmp_path / "workspace"
    source.mkdir()

    (source / "b.TXT").write_text("1", encoding="utf-8")
    (source / "a.txt").write_text("2", encoding="utf-8")

    plan = build_rename_plan(
        source_dir=source,
        prefix="file",
        start_number=1,
        lowercase_extension=True,
    )

    destination_names = [item.destination.name for item in plan]
    assert destination_names == ["file_001.txt", "file_002.txt"]


def test_execute_rename_plan_dry_run_keeps_files(tmp_path):
    source = tmp_path / "workspace"
    source.mkdir()

    (source / "a.txt").write_text("A", encoding="utf-8")

    plan = build_rename_plan(source_dir=source, prefix="doc")
    records = execute_rename_plan(plan, dry_run=True)

    assert (source / "a.txt").exists()
    assert records[0].status == "dry-run"


def test_execute_rename_plan_applies_changes(tmp_path):
    source = tmp_path / "workspace"
    source.mkdir()

    (source / "a.txt").write_text("A", encoding="utf-8")
    (source / "b.txt").write_text("B", encoding="utf-8")

    plan = build_rename_plan(source_dir=source, prefix="doc", start_number=10)
    records = execute_rename_plan(plan, dry_run=False)

    assert (source / "doc_010.txt").exists()
    assert (source / "doc_011.txt").exists()
    assert not (source / "a.txt").exists()
    assert not (source / "b.txt").exists()
    assert all(record.status == "success" for record in records)
