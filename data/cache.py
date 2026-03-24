"""Simple TTL cache decorator for data fetching."""

import time
from functools import wraps

_cache = {}
_cache_ttls = {}  # Track TTL per key for correct expiry
_MAX_CACHE_SIZE = 500  # Prevent unbounded growth


def ttl_cache(ttl_seconds=60):
    """Decorator that caches function results with a TTL.

    Args:
        ttl_seconds: Time-to-live in seconds (default 60).
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build a hashable key from function name + args
            key_parts = [func.__name__] + [str(a) for a in args]
            key_parts += [f"{k}={v}" for k, v in sorted(kwargs.items())]
            key = "|".join(key_parts)

            now = time.time()
            if key in _cache:
                result, timestamp = _cache[key]
                if now - timestamp < ttl_seconds:
                    return result

            # Evict expired entries if cache is getting large
            if len(_cache) >= _MAX_CACHE_SIZE:
                clear_expired()

            result = func(*args, **kwargs)
            _cache[key] = (result, now)
            _cache_ttls[key] = ttl_seconds
            return result
        return wrapper
    return decorator


def clear_cache():
    """Clear all cached data."""
    _cache.clear()
    _cache_ttls.clear()


def clear_expired():
    """Remove only expired entries using their actual TTL."""
    now = time.time()
    expired = [
        k for k, (_, ts) in _cache.items()
        if now - ts > _cache_ttls.get(k, 300)
    ]
    for k in expired:
        del _cache[k]
        _cache_ttls.pop(k, None)
