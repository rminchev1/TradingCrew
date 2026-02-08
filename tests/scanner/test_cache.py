"""
Unit tests for the cache module
"""

import pytest
import time
from tradingagents.scanner.cache import (
    cached,
    clear_cache,
    clear_expired,
    get_cache_stats,
    invalidate,
    _cache,
)


class TestCachedDecorator:
    """Tests for the @cached decorator"""

    def setup_method(self):
        """Clear cache before each test"""
        clear_cache()

    def test_cached_returns_same_value(self):
        """Test that cached function returns correct value"""
        call_count = 0

        @cached(ttl_seconds=60)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = expensive_function(5)
        result2 = expensive_function(5)

        assert result1 == 10
        assert result2 == 10
        assert call_count == 1  # Should only be called once

    def test_cached_different_args(self):
        """Test that different arguments result in different cache entries"""
        call_count = 0

        @cached(ttl_seconds=60)
        def add(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        result1 = add(1, 2)
        result2 = add(3, 4)
        result3 = add(1, 2)  # Should be cached

        assert result1 == 3
        assert result2 == 7
        assert result3 == 3
        assert call_count == 2  # First two calls, third is cached

    def test_cached_with_kwargs(self):
        """Test caching with keyword arguments"""
        call_count = 0

        @cached(ttl_seconds=60)
        def greet(name, greeting="Hello"):
            nonlocal call_count
            call_count += 1
            return f"{greeting}, {name}!"

        result1 = greet("Alice")
        result2 = greet("Alice")
        result3 = greet("Alice", greeting="Hi")

        assert result1 == "Hello, Alice!"
        assert result2 == "Hello, Alice!"
        assert result3 == "Hi, Alice!"
        assert call_count == 2

    def test_cached_expiration(self):
        """Test that cache expires after TTL"""
        call_count = 0

        @cached(ttl_seconds=1)  # 1 second TTL
        def get_value():
            nonlocal call_count
            call_count += 1
            return "value"

        result1 = get_value()
        assert call_count == 1

        # Wait for expiration
        time.sleep(1.1)

        result2 = get_value()
        assert call_count == 2  # Should be called again after expiration
        assert result1 == result2


class TestClearCache:
    """Tests for clear_cache function"""

    def setup_method(self):
        clear_cache()

    def test_clear_cache_empty(self):
        """Test clearing empty cache"""
        count = clear_cache()
        assert count == 0

    def test_clear_cache_with_entries(self):
        """Test clearing cache with entries"""
        @cached(ttl_seconds=60)
        def func(x):
            return x

        func(1)
        func(2)
        func(3)

        count = clear_cache()
        assert count == 3

        # Verify cache is empty
        stats = get_cache_stats()
        assert stats["total_entries"] == 0


class TestClearExpired:
    """Tests for clear_expired function"""

    def setup_method(self):
        clear_cache()

    def test_clear_expired_removes_old_entries(self):
        """Test that only expired entries are removed"""
        @cached(ttl_seconds=1)
        def short_ttl(x):
            return x

        @cached(ttl_seconds=60)
        def long_ttl(x):
            return x

        short_ttl(1)
        long_ttl(2)

        # Wait for short TTL to expire
        time.sleep(1.1)

        expired = clear_expired()
        assert expired == 1

        stats = get_cache_stats()
        assert stats["active_entries"] == 1

    def test_clear_expired_no_expired(self):
        """Test when no entries are expired"""
        @cached(ttl_seconds=60)
        def func(x):
            return x

        func(1)
        func(2)

        expired = clear_expired()
        assert expired == 0


class TestGetCacheStats:
    """Tests for get_cache_stats function"""

    def setup_method(self):
        clear_cache()

    def test_stats_empty_cache(self):
        """Test stats on empty cache"""
        stats = get_cache_stats()
        assert stats["total_entries"] == 0
        assert stats["expired_entries"] == 0
        assert stats["active_entries"] == 0

    def test_stats_with_entries(self):
        """Test stats with active entries"""
        @cached(ttl_seconds=60)
        def func(x):
            return x

        func(1)
        func(2)
        func(3)

        stats = get_cache_stats()
        assert stats["total_entries"] == 3
        assert stats["expired_entries"] == 0
        assert stats["active_entries"] == 3

    def test_stats_with_expired(self):
        """Test stats with expired entries"""
        @cached(ttl_seconds=1)
        def func(x):
            return x

        func(1)
        time.sleep(1.1)

        stats = get_cache_stats()
        assert stats["total_entries"] == 1
        assert stats["expired_entries"] == 1
        assert stats["active_entries"] == 0


class TestInvalidate:
    """Tests for invalidate function"""

    def setup_method(self):
        clear_cache()

    def test_invalidate_all(self):
        """Test invalidating all entries"""
        @cached(ttl_seconds=60)
        def func(x):
            return x

        func(1)
        func(2)

        count = invalidate()
        assert count == 2

    def test_invalidate_by_pattern(self):
        """Test invalidating entries matching pattern"""
        @cached(ttl_seconds=60)
        def get_stock(symbol):
            return symbol

        @cached(ttl_seconds=60)
        def get_news(symbol):
            return f"news for {symbol}"

        get_stock("AAPL")
        get_stock("MSFT")
        get_news("AAPL")

        # Invalidate only stock entries
        count = invalidate("get_stock")
        assert count == 2

        stats = get_cache_stats()
        assert stats["total_entries"] == 1  # Only news entry remains
