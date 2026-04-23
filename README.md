# python-automation-tool

A production-style Python CLI project for repetitive file and CSV workflows.

[![CI](https://github.com/genius/python-automation-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/muhammadakfz/python-automation-tool/actions/workflows/ci.yml)
[![Release](https://github.com/genius/python-automation-tool/actions/workflows/release.yml/badge.svg)](https://github.com/muhammadakfz/python-automation-tool/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

This repository is structured to present well as a portfolio project:
- clean `src/` layout and modular CLI architecture
- lint, unit tests, and end-to-end CLI integration tests
- build verification for both sdist and wheel
- tag-driven GitHub Actions release workflow for PyPI publishing

This tool is designed for local automation work such as:
- organizing mixed folders by file type
- batch renaming files with predictable numbering
- cleaning and transforming CSV files
- generating CSV action reports
- undoing the most recent organize/rename batch

## Key Features

- Python 3.11+ CLI with subcommands
- Professional modular architecture (src layout)
- Safe file operations with duplicate-name handling
- Dry-run support for every destructive workflow
- Undo support for the latest organize/rename batch
- CSV action reporting (timestamp, source, destination, status, errors)
- File filters:
  - include/exclude extensions
  - filename keyword filter
  - min/max file size filtering
- CSV processing utility:
  - trim whitespace
  - remove duplicate rows
  - rename columns
  - filter rows by column value
- Unit tests for core logic plus CLI integration tests

## Portfolio Highlights

- `CI/CD`: GitHub Actions validates lint, tests, and packaging on every push and pull request
- `Release discipline`: versioned releases are tied to Git tags and validated before publishing
- `Operational safety`: destructive workflows support dry runs, duplicate handling, reports, and undo
- `Test depth`: the suite covers both module-level logic and real CLI execution paths

## Project Docs

- [Changelog](CHANGELOG.md)
- [Contributing Guide](CONTRIBUTING.md)
- [MIT License](LICENSE)

## Project Structure

```text
python-automation-tool/
  src/
    python_automation_tool/
      __init__.py
      __main__.py
      cli.py
      models.py
      logging_config.py
      filters.py
      utils.py
      file_operations.py
      batch_renamer.py
      csv_processor.py
      reporting.py
      history.py
  tests/
    test_filters.py
    test_file_operations.py
    test_batch_renamer.py
    test_csv_processor.py
    test_history.py
  pyproject.toml
  requirements.txt
  README.md
```

## Architecture Summary

- CLI Layer (`cli.py`)
  - Parses command arguments
  - Dispatches subcommands
  - Handles command-level errors and summaries
  - Controls report/history integration

- Service Layer
  - `file_operations.py`: scanning, categorization, safe moves
  - `batch_renamer.py`: deterministic rename planning and apply
  - `csv_processor.py`: CSV cleaning/transform pipeline
  - `history.py`: persistent last-operation history + undo
  - `reporting.py`: CSV report generation

- Shared Components
  - `filters.py`: reusable file filter criteria
  - `models.py`: typed data structures (action records, summaries)
  - `utils.py`: extension parsing, unique path logic, timestamps
  - `logging_config.py`: console/file logging setup

## Setup

1. Create and activate a virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

2. Install project and test dependencies:

```bash
pip install -e .
pip install -r requirements.txt
```

For a single dev install that includes lint, test, and packaging tools:

```bash
pip install -e ".[dev]"
```

3. Verify CLI is available:

```bash
python-automation-tool --help
```

You can also run it as a module:

```bash
python -m python_automation_tool --help
```

## Commands

### 1) organize

Scan a folder and move files into category folders:
`images`, `documents`, `spreadsheets`, `code`, `archives`, `audio`, `video`, `others`.

```bash
python-automation-tool organize \
  --source ./data/inbox \
  --recursive \
  --include-ext .jpg .png .pdf .csv \
  --keyword invoice \
  --min-size 100 \
  --report-path ./reports/organize_report.csv
```

Dry run:

```bash
python-automation-tool organize --source ./data/inbox --dry-run
```

### 2) rename

Preview and batch rename with numbered format (`prefix_001.ext`).
By default it only previews. Use `--apply` to execute.

```bash
python-automation-tool rename \
  --source ./data/inbox \
  --prefix project_asset \
  --start-number 1 \
  --lower-ext \
  --recursive
```

Apply changes:

```bash
python-automation-tool rename \
  --source ./data/inbox \
  --prefix project_asset \
  --start-number 1 \
  --lower-ext \
  --apply \
  --report-path ./reports/rename_report.csv
```

Dry run with apply mode:

```bash
python-automation-tool rename \
  --source ./data/inbox \
  --prefix archive \
  --apply \
  --dry-run
```

### 3) process-csv

Transform CSV files and write cleaned output.

```bash
python-automation-tool process-csv \
  --input ./data/raw/customers.csv \
  --output ./data/clean/customers_clean.csv \
  --trim-whitespace \
  --remove-duplicates \
  --rename-column Name:customer_name \
  --rename-column Email:email_address \
  --filter-column Status \
  --filter-value Active \
  --report-path ./reports/csv_report.csv
```

Dry run:

```bash
python-automation-tool process-csv \
  --input ./data/raw/customers.csv \
  --output ./data/clean/customers_clean.csv \
  --trim-whitespace \
  --dry-run
```

### 4) undo

Undo the most recent successful `organize` or `rename` batch.

```bash
python-automation-tool undo --report-path ./reports/undo_report.csv
```

Dry run undo:

```bash
python-automation-tool undo --dry-run
```

### 5) report

Export the latest saved operation history to CSV.

```bash
python-automation-tool report --output ./reports/latest_history_report.csv
```

## Logging

Verbose console logs:

```bash
python-automation-tool --verbose organize --source ./data/inbox --dry-run
```

Write logs to file:

```bash
python-automation-tool --log-file ./logs/tool.log organize --source ./data/inbox
```

## Undo History File

By default, operation history is saved at:

- `~/.python_automation_tool/last_operation.json`

You can override it per command:

```bash
python-automation-tool organize --source ./data/inbox --history-file ./state/last_op.json
python-automation-tool undo --history-file ./state/last_op.json
```

## Error Handling Highlights

The CLI includes explicit handling for:
- invalid or missing paths
- empty source folders
- permission failures during move/rename
- malformed CSV files or invalid column mappings
- invalid filter ranges and argument combinations

## Run Tests

```bash
pytest
```

Run lint checks:

```bash
ruff check .
```

Build and validate release artifacts locally:

```bash
python -m build
python -m twine check --strict dist/*
```

Shortcut with Make:

```bash
make check
```

## Quality Gates

- GitHub Actions CI runs Ruff linting, pytest, and distribution build checks
- Integration tests exercise the CLI end-to-end through `python -m python_automation_tool`
- Packaging validation checks both sdist and wheel metadata before release

## Versioning And Releases

- Package version is defined once in `src/python_automation_tool/__init__.py`
- `pyproject.toml` reads that version dynamically during packaging
- Create a release by updating `__version__`, committing the change, and pushing a matching tag such as `v0.1.0`
- The release workflow verifies that the Git tag matches the package version before publishing

## GitHub Actions Workflows

- `.github/workflows/ci.yml`
  Runs lint, tests, and package build validation on pushes and pull requests
- `.github/workflows/release.yml`
  Runs on version tags, rebuilds and validates the package, publishes to PyPI via trusted publishing, and creates a GitHub Release

Before enabling PyPI publishing, configure a `pypi` environment in GitHub and connect it to your PyPI trusted publisher settings.

If your GitHub repository slug is different from `genius/python-automation-tool`, update the repository URLs in `pyproject.toml` and the badges above.

## Practical Portfolio Workflow

1. Preview an organize run:
```bash
python-automation-tool organize --source ./workspace --recursive --dry-run
```

2. Apply organize + save report:
```bash
python-automation-tool organize --source ./workspace --recursive --report-path ./reports/organize.csv
```

3. Preview rename:
```bash
python-automation-tool rename --source ./workspace/images --prefix event --start-number 100
```

4. Apply rename:
```bash
python-automation-tool rename --source ./workspace/images --prefix event --start-number 100 --apply --report-path ./reports/rename.csv
```

5. If needed, undo last batch:
```bash
python-automation-tool undo --report-path ./reports/undo.csv
```
