# backend/app/core/logging.py — Structured JSON logging configuration
# Cost classification: FREE + OPEN SOURCE

import logging
import sys
from typing import Any, Dict

from pythonjsonlogger import jsonlogger


def setup_logging() -> None:
    """Configure root logger to output JSON-structured logs to stdout."""
    logHandler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(level)s %(name)s %(message)s",
        rename_fields={"level": "levelname", "asctime": "timestamp"},
    )
    logHandler.setFormatter(formatter)

    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.INFO)
    rootLogger.handlers.clear()  # Remove any existing handlers
    rootLogger.addHandler(logHandler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name, using the JSON configuration."""
    return logging.getLogger(name)