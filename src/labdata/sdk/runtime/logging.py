"""Log estruturado em JSON, uma linha por evento, com o run_id. Legível no CloudWatch Logs Insights."""

from __future__ import annotations

import json
import logging
import sys
from typing import Any

_CONTEXT: dict[str, Any] = {}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            **_CONTEXT,
            **getattr(record, "extra_fields", {}),
        }
        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure(level: int = logging.INFO, **context: Any) -> None:
    _CONTEXT.clear()
    _CONTEXT.update(context)
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.handlers = [handler]


def info(logger: logging.Logger, message: str, **fields: Any) -> None:
    logger.info(message, extra={"extra_fields": fields})
