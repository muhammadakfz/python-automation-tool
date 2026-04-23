from __future__ import annotations

import pytest

from python_automation_tool.filters import FileFilterCriteria, matches_filters


def test_matches_filters_with_extension_keyword_and_size(tmp_path):
    file_path = tmp_path / "Report.csv"
    file_path.write_text("1234567890", encoding="utf-8")

    criteria = FileFilterCriteria(
        include_extensions={".csv"},
        keyword="report",
        min_size_bytes=5,
        max_size_bytes=20,
    )

    assert matches_filters(file_path, criteria)


def test_matches_filters_respects_exclusion(tmp_path):
    file_path = tmp_path / "data.csv"
    file_path.write_text("abc", encoding="utf-8")

    criteria = FileFilterCriteria(exclude_extensions={".csv"})

    assert not matches_filters(file_path, criteria)


def test_filter_validation_rejects_invalid_range():
    criteria = FileFilterCriteria(min_size_bytes=100, max_size_bytes=10)
    with pytest.raises(ValueError):
        criteria.validate()
