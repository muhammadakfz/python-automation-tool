from __future__ import annotations

from pathlib import Path

from python_automation_tool.file_operations import categorize_file, organize_files


def test_categorize_file_maps_known_and_unknown_extensions():
    assert categorize_file(Path("photo.JPG")) == "images"
    assert categorize_file(Path("custom.weird")) == "others"


def test_organize_files_handles_duplicate_names(tmp_path):
    source = tmp_path / "workspace"
    source.mkdir()

    nested = source / "nested"
    nested.mkdir()

    (source / "photo.jpg").write_text("root", encoding="utf-8")
    (nested / "photo.jpg").write_text("nested", encoding="utf-8")

    records = organize_files(source, recursive=True, dry_run=False)

    images_dir = source / "images"
    renamed_files = sorted(path.name for path in images_dir.iterdir() if path.is_file())

    assert renamed_files == ["photo.jpg", "photo_001.jpg"]
    assert len(records) == 2
    assert all(record.status == "success" for record in records)


def test_organize_files_dry_run_does_not_move_files(tmp_path):
    source = tmp_path / "workspace"
    source.mkdir()

    original_file = source / "report.pdf"
    original_file.write_text("content", encoding="utf-8")

    records = organize_files(source, recursive=False, dry_run=True)

    assert original_file.exists()
    assert len(records) == 1
    assert records[0].status == "dry-run"


def test_organize_files_processes_user_folder_named_like_a_category(tmp_path):
    source = tmp_path / "workspace"
    source.mkdir()

    category_named_folder = source / "images"
    category_named_folder.mkdir()
    text_file = category_named_folder / "notes.txt"
    text_file.write_text("content", encoding="utf-8")

    records = organize_files(source, recursive=True, dry_run=True)

    assert len(records) == 1
    assert records[0].status == "dry-run"
    assert Path(records[0].original_path) == text_file
    assert Path(records[0].new_path) == source / "documents" / "notes.txt"
