from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any


def correlation_context(**kwargs: object) -> dict[str, object]:
    return {key: value for key, value in kwargs.items() if value is not None}


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        context = getattr(record, "context", None)
        if isinstance(context, dict) and context:
            payload["context"] = context
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    root_logger = logging.getLogger()
    if any(isinstance(handler.formatter, StructuredFormatter) for handler in root_logger.handlers):
        root_logger.setLevel(level)
        return

    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    root_logger.handlers = [handler]
    root_logger.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
