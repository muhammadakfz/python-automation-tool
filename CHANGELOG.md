# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [0.1.0] - 2026-04-23

### Added
- Modular CLI for organizing files, batch renaming, CSV processing, reporting, and undo history
- Ruff lint configuration, pytest coverage, and end-to-end CLI integration tests
- GitHub Actions CI for lint, tests, and packaging validation
- Tag-driven release workflow with PyPI trusted publishing support

### Fixed
- CSV duplicate-header validation after normalization
- Invalid one-sided CSV filter argument handling
- Recursive organize behavior for user folders named like category folders
