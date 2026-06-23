"""Logging configuration for the validation harness."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def configure_logging(
    *,
    level: int = logging.INFO,
    log_file: Path | None = None,
    verbose: bool = False,
) -> logging.Logger:
    """Configure root logger for CLI and report generation.

    Args:
        level: Default log level when ``verbose`` is False.
        log_file: Optional file path for a duplicate log stream.
        verbose: When True, use DEBUG level.

    Returns:
        Package logger named ``validation``.
    """
    effective = logging.DEBUG if verbose else level
    logger = logging.getLogger("validation")
    logger.setLevel(effective)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream = logging.StreamHandler(sys.stdout)
    stream.setLevel(effective)
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(effective)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
