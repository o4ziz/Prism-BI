"""Structured logging bootstrap."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from prism_bi.infrastructure.config import LoggingSettings


class StructuredFormatter(logging.Formatter):
    """Key=value style formatter suitable for file and console sinks."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extras: list[str] = []
        for key in ("correlation_id", "job_id", "project_id"):
            value = getattr(record, key, None)
            if value is not None:
                extras.append(f"{key}={value}")
        if extras:
            return f"{base} | {' '.join(extras)}"
        return base


def setup_logging(
    settings: LoggingSettings,
    *,
    log_dir: Path,
    console: bool = True,
) -> logging.Logger:
    """Configure root Prism logger with rotating file (+ optional console)."""
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("prism_bi")
    logger.handlers.clear()
    logger.setLevel(settings.level.upper())
    logger.propagate = False

    formatter = StructuredFormatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_dir / "prism-bi.log",
        maxBytes=settings.max_bytes,
        backupCount=settings.backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if console:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return logger
