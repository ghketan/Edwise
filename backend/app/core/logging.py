import contextvars
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Optional

request_id_ctx = contextvars.ContextVar[Optional[str]]("request_id", default=None)
user_id_ctx = contextvars.ContextVar[Optional[int]]("user_id", default=None)


class StructuredJsonFormatter(logging.Formatter):
    """
    Formatter that outputs JSON logs respecting D-014 & R-017:
    Only system info, timestamp, log level, request_id, and user_id.
    Student PII (names, admission numbers, marks, credentials) are excluded.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get(),
            "user_id": user_id_ctx.get(),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = [handler]
    
    # Silence overly verbose external loggers
    logging.getLogger("uvicorn.access").handlers = [handler]
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


logger = logging.getLogger("edwise")

