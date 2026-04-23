# Contributing

## Local setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Quality checks

Run these before opening a pull request:

```bash
ruff check .
pytest
python -m build
python -m twine check --strict dist/*
```

## Release flow

1. Update `src/python_automation_tool/__init__.py` with the new version.
2. Add the release notes to `CHANGELOG.md`.
3. Run the quality checks locally.
4. Commit the release changes.
5. Push a matching Git tag such as `v0.1.0`.

The GitHub Actions release workflow will verify the tag/package version match before publishing.
