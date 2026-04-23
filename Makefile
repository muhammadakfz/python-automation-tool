PYTHON ?= python

.PHONY: install-dev lint test build check release-check

install-dev:
	$(PYTHON) -m pip install -e ".[dev]"

lint:
	ruff check .

test:
	pytest

build:
	$(PYTHON) -m build

check: lint test build
	$(PYTHON) -m twine check --strict dist/*

release-check: check
