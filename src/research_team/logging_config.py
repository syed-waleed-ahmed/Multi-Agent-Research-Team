"""Centralized logging configuration.

The package logs through the standard :mod:`logging` module under the
``research_team`` namespace so that host applications can attach their own
handlers, adjust levels, or route logs to a structured sink. When run as a CLI
we install a :class:`rich.logging.RichHandler` for readable, colorized output.
"""

from __future__ import annotations

import logging

LOGGER_NAME = "research_team"

_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a package logger, optionally namespaced by ``name``."""
    if name:
        return logging.getLogger(f"{LOGGER_NAME}.{name}")
    return logging.getLogger(LOGGER_NAME)


def normalize_level(level: str | int) -> int:
    """Coerce a level name or number to a :mod:`logging` level integer."""
    if isinstance(level, int):
        return level
    candidate = str(level).strip().upper()
    if candidate not in _VALID_LEVELS:
        return logging.INFO
    return getattr(logging, candidate)


def configure_logging(level: str | int = "INFO", *, quiet: bool = False) -> None:
    """Configure the package logger once for CLI usage.

    Parameters
    ----------
    level:
        Minimum level to emit (name or numeric).
    quiet:
        When true, suppress everything below ``ERROR`` regardless of ``level``.
    """
    logger = get_logger()
    effective = logging.ERROR if quiet else normalize_level(level)
    logger.setLevel(effective)

    # Idempotent: never stack duplicate handlers across repeated CLI/test calls.
    if logger.handlers:
        for existing in logger.handlers:
            existing.setLevel(effective)
        return

    handler: logging.Handler
    try:
        from rich.logging import RichHandler

        handler = RichHandler(
            rich_tracebacks=True,
            show_time=False,
            show_path=False,
            markup=True,
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
    except Exception:  # pragma: no cover - rich should be installed
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    handler.setLevel(effective)
    logger.addHandler(handler)
    # Prevent double emission if the root logger is also configured.
    logger.propagate = False
