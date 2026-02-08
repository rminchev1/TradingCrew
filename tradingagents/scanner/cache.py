"""
Cache Layer - TTL-based caching for expensive API calls
"""

import time
from functools import wraps
from typing import Any, Dict, Callable, Optional

# Global cache storage: {cache_key: (value, expiry_timestamp)}
_cache: Dict[str, tuple] = {}


def cached(ttl_seconds: int = 300):
    """
    TTL-based caching decorator.

    Args:
        ttl_seconds: Time-to-live in seconds (default 5 minutes)

    Usage:
        @cached(ttl_seconds=300)
        def expensive_function(arg1, arg2):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = _make_cache_key(func.__name__, args, kwargs)

            # Check if cached and not expired
            if cache_key in _cache:
                value, expiry = _cache[cache_key]
                if time.time() < expiry:
                    return value

            # Call function and cache result
            result = func(*args, **kwargs)
            _cache[cache_key] = (result, time.time() + ttl_seconds)

            return result

        return wrapper
    return decorator


def _make_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """Create a hashable cache key from function name and arguments."""
    # Convert args and kwargs to a string representation
    args_str = str(args)
    kwargs_str = str(sorted(kwargs.items()))
    return f"{func_name}:{args_str}:{kwargs_str}"


def clear_cache() -> int:
    """
    Clear all cached entries.

    Returns:
        Number of entries cleared
    """
    global _cache
    count = len(_cache)
    _cache = {}
    return count


def clear_expired() -> int:
    """
    Clear only expired cache entries.

    Returns:
        Number of expired entries removed
    """
    global _cache
    current_time = time.time()
    expired_keys = [key for key, (_, expiry) in _cache.items() if current_time >= expiry]

    for key in expired_keys:
        del _cache[key]

    return len(expired_keys)


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.

    Returns:
        Dict with cache stats (total entries, expired entries, etc.)
    """
    current_time = time.time()
    total = len(_cache)
    expired = sum(1 for _, (_, expiry) in _cache.items() if current_time >= expiry)

    return {
        "total_entries": total,
        "expired_entries": expired,
        "active_entries": total - expired,
    }


def invalidate(pattern: Optional[str] = None) -> int:
    """
    Invalidate cache entries matching a pattern.

    Args:
        pattern: String pattern to match in cache keys. If None, clears all.

    Returns:
        Number of entries invalidated
    """
    global _cache

    if pattern is None:
        return clear_cache()

    keys_to_remove = [key for key in _cache.keys() if pattern in key]
    for key in keys_to_remove:
        del _cache[key]

    return len(keys_to_remove)
