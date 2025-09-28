import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional, Callable
import contextvars
import asyncio

_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Request ID context variable
_request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)

def set_request_id(request_id: Optional[str]):
    """Set request_id for current context. Returns a token for reset."""
    return _request_id_var.set(request_id)

def reset_request_id(token):
    """Reset request_id context using token from set_request_id."""
    try:
        _request_id_var.reset(token)
    except Exception:
        pass

def get_request_id() -> Optional[str]:
    return _request_id_var.get()

class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        rid = _request_id_var.get()
        # Only set if not already provided via extras
        if not hasattr(record, "request_id"):
            record.request_id = rid
        return True

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=datetime.now().astimezone().tzinfo).astimezone().isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Attach extra attributes (excluding built-ins)
        for k, v in record.__dict__.items():
            if k.startswith("_"):
                continue
            if k in {"name","msg","args","levelname","levelno","pathname","filename","module","exc_info","exc_text","stack_info","lineno","funcName","created","msecs","relativeCreated","thread","threadName","processName","message"}:
                continue
            try:
                json.dumps(v)
                payload[k] = v
            except Exception:
                payload[k] = str(v)
        return json.dumps(payload, ensure_ascii=False)

def get_logger(name: str = "app", level: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        handler.addFilter(RequestIdFilter())
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, (level or _LOG_LEVEL), logging.INFO))
    logger.propagate = False
    return logger

# Helpers to wrap background tasks to carry request_id context
def wrap_async_bg(fn: Callable, request_id: Optional[str]):
    if asyncio.iscoroutinefunction(fn):
        async def _wrapped(*args, **kwargs):
            token = set_request_id(request_id)
            try:
                return await fn(*args, **kwargs)
            finally:
                reset_request_id(token)
        return _wrapped
    else:
        def _wrapped(*args, **kwargs):
            token = set_request_id(request_id)
            try:
                return fn(*args, **kwargs)
            finally:
                reset_request_id(token)
        return _wrapped
