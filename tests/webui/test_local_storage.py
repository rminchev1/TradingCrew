"""
Unit tests for the local storage persistence layer (SQLite database)
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch


class TestLocalStorageInit:
    """Tests for database initialization"""

    def test_init_db_creates_tables(self, tmp_storage):
        """Test that init_db creates the required tables"""
        from webui.utils import local_storage

        conn = local_storage._get_connection()
        cursor = conn.cursor()

        # Check that kv_store table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='kv_store'
        """)
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result["name"] == "kv_store"

    def test_init_db_is_idempotent(self, tmp_storage):
        """Test that init_db can be called multiple times safely"""
        from webui.utils import local_storage

        # Call init_db multiple times - should not raise
        local_storage.init_db()
        local_storage.init_db()
        local_storage.init_db()

        # Verify table still exists and works
        local_storage.set_value("test_key", "test_value")
        assert local_storage.get_value("test_key") == "test_value"


class TestKeyValueStore:
    """Tests for basic key-value operations"""

    def test_set_and_get_string(self, tmp_storage):
        """Test setting and getting a string value"""
        from webui.utils import local_storage

        local_storage.set_value("test_string", "hello world")
        result = local_storage.get_value("test_string")

        assert result == "hello world"

    def test_set_and_get_integer(self, tmp_storage):
        """Test setting and getting an integer value"""
        from webui.utils import local_storage

        local_storage.set_value("test_int", 42)
        result = local_storage.get_value("test_int")

        assert result == 42

    def test_set_and_get_float(self, tmp_storage):
        """Test setting and getting a float value"""
        from webui.utils import local_storage

        local_storage.set_value("test_float", 3.14159)
        result = local_storage.get_value("test_float")

        assert result == 3.14159

    def test_set_and_get_boolean(self, tmp_storage):
        """Test setting and getting boolean values"""
        from webui.utils import local_storage

        local_storage.set_value("test_true", True)
        local_storage.set_value("test_false", False)

        assert local_storage.get_value("test_true") is True
        assert local_storage.get_value("test_false") is False

    def test_set_and_get_list(self, tmp_storage):
        """Test setting and getting a list value"""
        from webui.utils import local_storage

        test_list = ["AAPL", "NVDA", "TSLA"]
        local_storage.set_value("test_list", test_list)
        result = local_storage.get_value("test_list")

        assert result == test_list

    def test_set_and_get_dict(self, tmp_storage):
        """Test setting and getting a dictionary value"""
        from webui.utils import local_storage

        test_dict = {"key1": "value1", "key2": 123, "nested": {"a": 1}}
        local_storage.set_value("test_dict", test_dict)
        result = local_storage.get_value("test_dict")

        assert result == test_dict

    def test_set_and_get_none(self, tmp_storage):
        """Test setting and getting None value"""
        from webui.utils import local_storage

        local_storage.set_value("test_none", None)
        result = local_storage.get_value("test_none")

        assert result is None

    def test_get_nonexistent_key_returns_default(self, tmp_storage):
        """Test that getting a nonexistent key returns the default value"""
        from webui.utils import local_storage

        result = local_storage.get_value("nonexistent_key")
        assert result is None

        result = local_storage.get_value("nonexistent_key", default="default_value")
        assert result == "default_value"

        result = local_storage.get_value("nonexistent_key", default=[])
        assert result == []

    def test_update_existing_value(self, tmp_storage):
        """Test updating an existing value"""
        from webui.utils import local_storage

        local_storage.set_value("update_test", "initial")
        assert local_storage.get_value("update_test") == "initial"

        local_storage.set_value("update_test", "updated")
        assert local_storage.get_value("update_test") == "updated"

    def test_delete_value(self, tmp_storage):
        """Test deleting a value"""
        from webui.utils import local_storage

        local_storage.set_value("delete_test", "to_be_deleted")
        assert local_storage.get_value("delete_test") == "to_be_deleted"

        local_storage.delete_value("delete_test")
        assert local_storage.get_value("delete_test") is None

    def test_delete_nonexistent_key(self, tmp_storage):
        """Test deleting a nonexistent key doesn't raise"""
        from webui.utils import local_storage

        # Should not raise
        local_storage.delete_value("nonexistent_key")

    def test_get_all_keys(self, tmp_storage):
        """Test getting all keys"""
        from webui.utils import local_storage

        local_storage.set_value("key1", "value1")
        local_storage.set_value("key2", "value2")
        local_storage.set_value("key3", "value3")

        keys = local_storage.get_all_keys()

        assert "key1" in keys
        assert "key2" in keys
        assert "key3" in keys

    def test_special_characters_in_key(self, tmp_storage):
        """Test keys with special characters"""
        from webui.utils import local_storage

        local_storage.set_value("key-with-dashes", "value1")
        local_storage.set_value("key_with_underscores", "value2")
        local_storage.set_value("key.with.dots", "value3")

        assert local_storage.get_value("key-with-dashes") == "value1"
        assert local_storage.get_value("key_with_underscores") == "value2"
        assert local_storage.get_value("key.with.dots") == "value3"

    def test_unicode_values(self, tmp_storage):
        """Test storing unicode values"""
        from webui.utils import local_storage

        local_storage.set_value("unicode_test", "Hello 世界 🌍 émojis")
        result = local_storage.get_value("unicode_test")

        assert result == "Hello 世界 🌍 émojis"


class TestSettings:
    """Tests for settings-specific functions"""

    def test_get_settings_returns_defaults(self, tmp_storage):
        """Test that get_settings returns defaults when no settings saved"""
        from webui.utils import local_storage

        settings = local_storage.get_settings()

        assert "analyst_checklist" in settings
        assert "research_depth" in settings
        assert "quick_llm" in settings
        assert "deep_llm" in settings
        assert settings["research_depth"] == "Shallow"

    def test_save_and_get_settings(self, tmp_storage):
        """Test saving and retrieving settings"""
        from webui.utils import local_storage

        custom_settings = {
            "analyst_checklist": ["market", "news"],
            "analyst_checklist_2": ["fundamentals"],
            "research_depth": "Deep",
            "allow_shorts": True,
            "loop_enabled": True,
            "loop_interval": 120,
            "market_hour_enabled": False,
            "market_hours_input": "10,14",
            "trade_after_analyze": True,
            "trade_dollar_amount": 5000,
            "quick_llm": "gpt-4o-mini",
            "deep_llm": "gpt-4o",
        }

        local_storage.save_settings(custom_settings)
        result = local_storage.get_settings()

        assert result["analyst_checklist"] == ["market", "news"]
        assert result["research_depth"] == "Deep"
        assert result["allow_shorts"] is True
        assert result["loop_interval"] == 120
        assert result["trade_dollar_amount"] == 5000
        assert result["quick_llm"] == "gpt-4o-mini"

    def test_get_settings_merges_with_defaults(self, tmp_storage):
        """Test that get_settings merges saved settings with defaults"""
        from webui.utils import local_storage

        # Save partial settings
        partial_settings = {"research_depth": "Medium"}
        local_storage.save_settings(partial_settings)

        result = local_storage.get_settings()

        # Should have the saved value
        assert result["research_depth"] == "Medium"
        # Should also have default values for other keys
        assert "analyst_checklist" in result
        assert "quick_llm" in result

    def test_get_single_setting(self, tmp_storage):
        """Test getting a single setting"""
        from webui.utils import local_storage

        local_storage.save_settings({"research_depth": "Deep"})

        result = local_storage.get_setting("research_depth")
        assert result == "Deep"

        # Test with default
        result = local_storage.get_setting("nonexistent", default="fallback")
        assert result == "fallback"

    def test_save_single_setting(self, tmp_storage):
        """Test saving a single setting"""
        from webui.utils import local_storage

        local_storage.save_setting("research_depth", "Medium")

        result = local_storage.get_setting("research_depth")
        assert result == "Medium"

        # Other settings should remain
        settings = local_storage.get_settings()
        assert "analyst_checklist" in settings


class TestWatchlist:
    """Tests for watchlist-specific functions"""

    def test_get_watchlist_returns_empty_default(self, tmp_storage):
        """Test that get_watchlist returns empty list by default"""
        from webui.utils import local_storage

        result = local_storage.get_watchlist()

        assert result == {"symbols": []}

    def test_save_and_get_watchlist(self, tmp_storage):
        """Test saving and retrieving watchlist"""
        from webui.utils import local_storage

        watchlist = {"symbols": ["AAPL", "NVDA", "TSLA", "MSFT"]}
        local_storage.save_watchlist(watchlist)

        result = local_storage.get_watchlist()

        assert result == watchlist
        assert "AAPL" in result["symbols"]
        assert len(result["symbols"]) == 4

    def test_update_watchlist(self, tmp_storage):
        """Test updating watchlist"""
        from webui.utils import local_storage

        local_storage.save_watchlist({"symbols": ["AAPL"]})
        local_storage.save_watchlist({"symbols": ["AAPL", "NVDA"]})

        result = local_storage.get_watchlist()

        assert result["symbols"] == ["AAPL", "NVDA"]

    def test_clear_watchlist(self, tmp_storage):
        """Test clearing watchlist"""
        from webui.utils import local_storage

        local_storage.save_watchlist({"symbols": ["AAPL", "NVDA"]})
        local_storage.save_watchlist({"symbols": []})

        result = local_storage.get_watchlist()

        assert result["symbols"] == []


class TestRunQueue:
    """Tests for run queue-specific functions"""

    def test_get_run_queue_returns_empty_default(self, tmp_storage):
        """Test that get_run_queue returns empty list by default"""
        from webui.utils import local_storage

        result = local_storage.get_run_queue()

        assert result == {"symbols": []}

    def test_save_and_get_run_queue(self, tmp_storage):
        """Test saving and retrieving run queue"""
        from webui.utils import local_storage

        run_queue = {"symbols": ["GOOGL", "META", "AMZN"]}
        local_storage.save_run_queue(run_queue)

        result = local_storage.get_run_queue()

        assert result == run_queue
        assert "GOOGL" in result["symbols"]
        assert len(result["symbols"]) == 3

    def test_update_run_queue(self, tmp_storage):
        """Test updating run queue"""
        from webui.utils import local_storage

        local_storage.save_run_queue({"symbols": ["AAPL"]})
        local_storage.save_run_queue({"symbols": ["AAPL", "NVDA", "TSLA"]})

        result = local_storage.get_run_queue()

        assert result["symbols"] == ["AAPL", "NVDA", "TSLA"]

    def test_clear_run_queue(self, tmp_storage):
        """Test clearing run queue"""
        from webui.utils import local_storage

        local_storage.save_run_queue({"symbols": ["AAPL", "NVDA"]})
        local_storage.save_run_queue({"symbols": []})

        result = local_storage.get_run_queue()

        assert result["symbols"] == []


class TestPersistence:
    """Tests for data persistence"""

    def test_data_persists_across_connections(self, tmp_storage):
        """Test that data persists across database connections"""
        from webui.utils import local_storage

        # Save data
        local_storage.save_settings({"research_depth": "Deep"})
        local_storage.save_watchlist({"symbols": ["AAPL"]})
        local_storage.save_run_queue({"symbols": ["NVDA"]})

        # Force a new connection by getting data again
        # (simulates app restart)
        settings = local_storage.get_settings()
        watchlist = local_storage.get_watchlist()
        run_queue = local_storage.get_run_queue()

        # Verify data persisted
        assert settings["research_depth"] == "Deep"
        assert watchlist["symbols"] == ["AAPL"]
        assert run_queue["symbols"] == ["NVDA"]

    def test_data_survives_multiple_operations(self, tmp_storage):
        """Test that data survives multiple read/write operations"""
        from webui.utils import local_storage

        # Multiple write operations
        for i in range(5):
            local_storage.save_watchlist({"symbols": [f"SYM{i}"]})

        # Verify final state
        result = local_storage.get_watchlist()
        assert result["symbols"] == ["SYM4"]


class TestConcurrency:
    """Tests for thread safety"""

    def test_concurrent_writes(self, tmp_storage):
        """Test concurrent write operations"""
        from webui.utils import local_storage
        import threading

        results = []

        def write_value(key, value):
            local_storage.set_value(key, value)
            results.append((key, value))

        threads = []
        for i in range(10):
            t = threading.Thread(target=write_value, args=(f"key_{i}", f"value_{i}"))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Verify all writes succeeded
        assert len(results) == 10
        for i in range(10):
            assert local_storage.get_value(f"key_{i}") == f"value_{i}"

    def test_concurrent_reads_and_writes(self, tmp_storage):
        """Test concurrent read and write operations"""
        from webui.utils import local_storage
        import threading

        local_storage.set_value("shared_key", "initial")
        errors = []

        def read_write(thread_id):
            try:
                for _ in range(10):
                    local_storage.set_value("shared_key", f"value_{thread_id}")
                    local_storage.get_value("shared_key")
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(5):
            t = threading.Thread(target=read_write, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should have no errors
        assert len(errors) == 0


# Pytest fixture for temporary storage
@pytest.fixture
def tmp_storage(tmp_path, monkeypatch):
    """Create a temporary database for testing"""
    from webui.utils import local_storage

    # Override the database path
    test_db_path = tmp_path / "test_tradingcrew.db"
    monkeypatch.setattr(local_storage, "DB_PATH", test_db_path)
    monkeypatch.setattr(local_storage, "DB_DIR", tmp_path)

    # Initialize the database
    local_storage.init_db()

    yield tmp_path

    # Cleanup (optional, tmp_path is auto-cleaned)
    if test_db_path.exists():
        test_db_path.unlink()
