"""Logging setup for consistent CLI and optional file logging."""

from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(verbose: bool = False, log_file: Path | None = None) -> logging.Logger:
    """Configure and return the package logger.

    The logger is initialized once and reconfigured safely across repeated calls,
    which is useful for tests.
    """
    logger = logging.getLogger("python_automation_tool")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s")
    )
    logger.addHandler(console_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
            )
        )
        logger.addHandler(file_handler)

    return logger
