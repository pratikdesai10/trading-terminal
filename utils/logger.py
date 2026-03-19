"""Structured logging with UUID request tracing."""

import logging
import uuid
import time
from functools import wraps

_request_id = "--------"


class RequestIdFormatter(logging.Formatter):
    """Formatter that injects request_id into log messages."""

    def format(self, record):
        record.request_id = _request_id
        return super().format(record)


# Configure our app logger (not root — avoids conflicts with third-party loggers)
logger = logging.getLogger("terminal")
logger.setLevel(logging.DEBUG)
logger.propagate = False  # Don't propagate to root logger

# Console handler with our custom formatter
_handler = logging.StreamHandler()
_handler.setLevel(logging.DEBUG)
_handler.setFormatter(RequestIdFormatter(
    fmt="%(asctime)s | %(levelname)-5s | %(request_id)s | %(module)s.%(funcName)s | %(message)s",
    datefmt="%H:%M:%S",
))
logger.addHandler(_handler)


def new_request_id():
    """Generate a new short request ID and set it globally."""
    global _request_id
    _request_id = uuid.uuid4().hex[:8]
    return _request_id


def log_data_fetch(func):
    """Decorator that logs data fetch calls with timing and error details."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_name = f"{func.__module__}.{func.__name__}"
        args_str = ", ".join([str(a) for a in args[:3]])
        logger.info(f"FETCH START | {func_name}({args_str})")
        start = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            if result is None:
                logger.warning(f"FETCH EMPTY | {func_name}({args_str}) | {elapsed:.2f}s | returned None")
            elif hasattr(result, 'empty') and result.empty:
                logger.warning(f"FETCH EMPTY | {func_name}({args_str}) | {elapsed:.2f}s | empty DataFrame")
            else:
                size = len(result) if hasattr(result, '__len__') else "ok"
                logger.info(f"FETCH OK    | {func_name}({args_str}) | {elapsed:.2f}s | size={size}")
            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"FETCH FAIL  | {func_name}({args_str}) | {elapsed:.2f}s | {type(e).__name__}: {e}")
            raise
    return wrapper
