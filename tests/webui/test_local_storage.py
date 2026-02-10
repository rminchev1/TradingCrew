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


class TestAnalystReports:
    """Tests for analyst reports storage functions"""

    def test_save_and_get_single_report(self, tmp_storage):
        """Test saving and retrieving a single analyst report"""
        from webui.utils import local_storage

        local_storage.save_analyst_report(
            symbol="NVDA",
            report_type="market_report",
            report_content="This is a market analysis report for NVDA",
            session_id="test-session-1"
        )

        report = local_storage.get_analyst_report("NVDA", "market_report", "test-session-1")

        assert report is not None
        assert report["content"] == "This is a market analysis report for NVDA"
        assert report["updated_at"] is not None

    def test_save_report_with_prompt(self, tmp_storage):
        """Test saving a report with its prompt content"""
        from webui.utils import local_storage

        local_storage.save_analyst_report(
            symbol="AAPL",
            report_type="news_report",
            report_content="News analysis for Apple",
            prompt_content="You are a news analyst. Analyze the following...",
            session_id="test-session-2"
        )

        report = local_storage.get_analyst_report("AAPL", "news_report", "test-session-2")

        assert report is not None
        assert report["content"] == "News analysis for Apple"
        assert report["prompt"] == "You are a news analyst. Analyze the following..."

    def test_save_empty_report_does_nothing(self, tmp_storage):
        """Test that saving an empty report does not create a record"""
        from webui.utils import local_storage

        local_storage.save_analyst_report(
            symbol="TSLA",
            report_type="market_report",
            report_content="",
            session_id="test-session-3"
        )

        report = local_storage.get_analyst_report("TSLA", "market_report", "test-session-3")
        assert report is None

        # Also test with whitespace only
        local_storage.save_analyst_report(
            symbol="TSLA",
            report_type="market_report",
            report_content="   ",
            session_id="test-session-3"
        )

        report = local_storage.get_analyst_report("TSLA", "market_report", "test-session-3")
        assert report is None

    def test_update_existing_report(self, tmp_storage):
        """Test that updating an existing report overwrites the content"""
        from webui.utils import local_storage

        local_storage.save_analyst_report(
            symbol="MSFT",
            report_type="fundamentals_report",
            report_content="Initial fundamentals report",
            session_id="test-session-4"
        )

        local_storage.save_analyst_report(
            symbol="MSFT",
            report_type="fundamentals_report",
            report_content="Updated fundamentals report with more data",
            session_id="test-session-4"
        )

        report = local_storage.get_analyst_report("MSFT", "fundamentals_report", "test-session-4")

        assert report["content"] == "Updated fundamentals report with more data"

    def test_get_all_reports_for_symbol(self, tmp_storage):
        """Test retrieving all reports for a symbol"""
        from webui.utils import local_storage

        session_id = "test-session-5"

        # Save multiple reports
        local_storage.save_analyst_report("GOOGL", "market_report", "Market analysis", session_id=session_id)
        local_storage.save_analyst_report("GOOGL", "news_report", "News analysis", session_id=session_id)
        local_storage.save_analyst_report("GOOGL", "fundamentals_report", "Fundamentals analysis", session_id=session_id)

        reports = local_storage.get_analyst_reports("GOOGL", session_id)

        assert len(reports) == 3
        assert "market_report" in reports
        assert "news_report" in reports
        assert "fundamentals_report" in reports
        assert reports["market_report"]["content"] == "Market analysis"

    def test_get_reports_without_session_returns_latest(self, tmp_storage):
        """Test that getting reports without session_id returns the most recent"""
        from webui.utils import local_storage

        # Save reports in different sessions
        local_storage.save_analyst_report("META", "market_report", "Old market report", session_id="old-session")
        local_storage.save_analyst_report("META", "market_report", "New market report", session_id="new-session")

        # Get without specifying session
        reports = local_storage.get_analyst_reports("META")

        assert len(reports) >= 1
        assert reports["market_report"]["content"] == "New market report"

    def test_get_nonexistent_report_returns_none(self, tmp_storage):
        """Test that getting a nonexistent report returns None"""
        from webui.utils import local_storage

        report = local_storage.get_analyst_report("NONEXISTENT", "market_report")
        assert report is None

    def test_crypto_symbol_format(self, tmp_storage):
        """Test storing reports for crypto symbols with slash"""
        from webui.utils import local_storage

        local_storage.save_analyst_report(
            symbol="BTC/USD",
            report_type="market_report",
            report_content="Bitcoin market analysis",
            session_id="crypto-session-1"
        )

        report = local_storage.get_analyst_report("BTC/USD", "market_report", "crypto-session-1")

        assert report is not None
        assert report["content"] == "Bitcoin market analysis"

    def test_all_report_types(self, tmp_storage):
        """Test saving all supported report types"""
        from webui.utils import local_storage

        report_types = [
            "market_report",
            "options_report",
            "sentiment_report",
            "news_report",
            "fundamentals_report",
            "macro_report",
            "bull_report",
            "bear_report",
            "research_manager_report",
            "trader_investment_plan",
            "risky_report",
            "safe_report",
            "neutral_report",
            "final_trade_decision",
        ]

        session_id = "all-types-session"

        for report_type in report_types:
            local_storage.save_analyst_report(
                symbol="TEST",
                report_type=report_type,
                report_content=f"Content for {report_type}",
                session_id=session_id
            )

        reports = local_storage.get_analyst_reports("TEST", session_id)

        assert len(reports) == len(report_types)
        for report_type in report_types:
            assert report_type in reports
            assert reports[report_type]["content"] == f"Content for {report_type}"


class TestReportSessions:
    """Tests for report session management"""

    def test_list_report_sessions(self, tmp_storage):
        """Test listing report sessions"""
        from webui.utils import local_storage

        # Create reports in multiple sessions
        local_storage.save_analyst_report("AAPL", "market_report", "Report 1", session_id="session-a")
        local_storage.save_analyst_report("AAPL", "news_report", "Report 2", session_id="session-a")
        local_storage.save_analyst_report("NVDA", "market_report", "Report 3", session_id="session-b")

        sessions = local_storage.list_report_sessions()

        assert len(sessions) >= 2

        # Find our sessions
        session_ids = [s["session_id"] for s in sessions]
        assert "session-a" in session_ids
        assert "session-b" in session_ids

    def test_list_report_sessions_for_symbol(self, tmp_storage):
        """Test listing sessions filtered by symbol"""
        from webui.utils import local_storage

        local_storage.save_analyst_report("AAPL", "market_report", "Report 1", session_id="session-x")
        local_storage.save_analyst_report("AAPL", "market_report", "Report 2", session_id="session-y")
        local_storage.save_analyst_report("NVDA", "market_report", "Report 3", session_id="session-z")

        sessions = local_storage.list_report_sessions(symbol="AAPL")

        session_ids = [s["session_id"] for s in sessions]
        assert "session-x" in session_ids
        assert "session-y" in session_ids
        assert "session-z" not in session_ids

    def test_list_sessions_includes_report_count(self, tmp_storage):
        """Test that session listing includes report count"""
        from webui.utils import local_storage

        session_id = "count-test-session"
        local_storage.save_analyst_report("TEST", "market_report", "Report 1", session_id=session_id)
        local_storage.save_analyst_report("TEST", "news_report", "Report 2", session_id=session_id)
        local_storage.save_analyst_report("TEST", "fundamentals_report", "Report 3", session_id=session_id)

        sessions = local_storage.list_report_sessions()

        # Find our session
        our_session = next((s for s in sessions if s["session_id"] == session_id), None)

        assert our_session is not None
        assert our_session["report_count"] == 3

    def test_list_sessions_respects_limit(self, tmp_storage):
        """Test that session listing respects the limit parameter"""
        from webui.utils import local_storage

        # Create many sessions
        for i in range(10):
            local_storage.save_analyst_report("TEST", "market_report", f"Report {i}", session_id=f"limit-session-{i}")

        sessions = local_storage.list_report_sessions(limit=5)

        assert len(sessions) <= 5

    def test_delete_report_session(self, tmp_storage):
        """Test deleting all reports for a session"""
        from webui.utils import local_storage

        session_id = "delete-test-session"
        local_storage.save_analyst_report("TEST", "market_report", "Report 1", session_id=session_id)
        local_storage.save_analyst_report("TEST", "news_report", "Report 2", session_id=session_id)

        # Verify reports exist
        reports = local_storage.get_analyst_reports("TEST", session_id)
        assert len(reports) == 2

        # Delete session
        result = local_storage.delete_report_session(session_id)
        assert result is True

        # Verify reports are deleted
        reports = local_storage.get_analyst_reports("TEST", session_id)
        assert len(reports) == 0

    def test_delete_nonexistent_session(self, tmp_storage):
        """Test deleting a session that doesn't exist"""
        from webui.utils import local_storage

        result = local_storage.delete_report_session("nonexistent-session")
        assert result is False


class TestRecentSymbols:
    """Tests for recent symbols tracking"""

    def test_get_recent_symbols(self, tmp_storage):
        """Test getting recently analyzed symbols"""
        from webui.utils import local_storage

        local_storage.save_analyst_report("AAPL", "market_report", "Report 1", session_id="session-1")
        local_storage.save_analyst_report("NVDA", "market_report", "Report 2", session_id="session-2")
        local_storage.save_analyst_report("TSLA", "market_report", "Report 3", session_id="session-3")

        recent = local_storage.get_recent_symbols()

        assert "AAPL" in recent
        assert "NVDA" in recent
        assert "TSLA" in recent

    def test_get_recent_symbols_respects_limit(self, tmp_storage):
        """Test that recent symbols respects limit"""
        from webui.utils import local_storage

        for i in range(10):
            local_storage.save_analyst_report(f"SYM{i}", "market_report", f"Report {i}", session_id=f"session-{i}")

        recent = local_storage.get_recent_symbols(limit=3)

        assert len(recent) == 3

    def test_get_recent_symbols_no_duplicates(self, tmp_storage):
        """Test that recent symbols doesn't include duplicates"""
        from webui.utils import local_storage

        # Same symbol, multiple reports
        local_storage.save_analyst_report("AAPL", "market_report", "Report 1", session_id="session-1")
        local_storage.save_analyst_report("AAPL", "news_report", "Report 2", session_id="session-1")
        local_storage.save_analyst_report("AAPL", "fundamentals_report", "Report 3", session_id="session-2")

        recent = local_storage.get_recent_symbols()

        # AAPL should only appear once
        aapl_count = sum(1 for s in recent if s == "AAPL")
        assert aapl_count == 1


class TestAnalystReportsPersistence:
    """Tests for analyst reports persistence across operations"""

    def test_reports_persist_across_connections(self, tmp_storage):
        """Test that reports persist across database connections"""
        from webui.utils import local_storage

        session_id = "persist-test"
        local_storage.save_analyst_report("PERSIST", "market_report", "Persistent content", session_id=session_id)

        # Force a new query
        report = local_storage.get_analyst_report("PERSIST", "market_report", session_id)

        assert report is not None
        assert report["content"] == "Persistent content"

    def test_unicode_in_reports(self, tmp_storage):
        """Test storing unicode content in reports"""
        from webui.utils import local_storage

        unicode_content = "Market analysis with émojis 📈📉 and 中文 characters"
        local_storage.save_analyst_report("UNICODE", "market_report", unicode_content, session_id="unicode-test")

        report = local_storage.get_analyst_report("UNICODE", "market_report", "unicode-test")

        assert report["content"] == unicode_content

    def test_large_report_content(self, tmp_storage):
        """Test storing large report content"""
        from webui.utils import local_storage

        # Create a large report (50KB)
        large_content = "A" * 50000
        local_storage.save_analyst_report("LARGE", "market_report", large_content, session_id="large-test")

        report = local_storage.get_analyst_report("LARGE", "market_report", "large-test")

        assert report["content"] == large_content
        assert len(report["content"]) == 50000


class TestAnalystReportsConcurrency:
    """Tests for thread safety of analyst reports"""

    def test_concurrent_report_writes(self, tmp_storage):
        """Test concurrent write operations for reports"""
        from webui.utils import local_storage
        import threading

        errors = []

        def write_report(symbol, session_id):
            try:
                for i in range(5):
                    local_storage.save_analyst_report(
                        symbol=symbol,
                        report_type="market_report",
                        report_content=f"Report iteration {i}",
                        session_id=session_id
                    )
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(5):
            t = threading.Thread(target=write_report, args=(f"SYM{i}", f"concurrent-session-{i}"))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should have no errors
        assert len(errors) == 0

        # Verify all writes succeeded
        for i in range(5):
            report = local_storage.get_analyst_report(f"SYM{i}", "market_report", f"concurrent-session-{i}")
            assert report is not None

    def test_concurrent_reads_and_writes(self, tmp_storage):
        """Test concurrent read and write operations for reports"""
        from webui.utils import local_storage
        import threading

        session_id = "rw-concurrent-session"
        local_storage.save_analyst_report("RW_TEST", "market_report", "Initial", session_id=session_id)
        errors = []

        def read_write(thread_id):
            try:
                for _ in range(10):
                    local_storage.save_analyst_report(
                        "RW_TEST",
                        "market_report",
                        f"Updated by thread {thread_id}",
                        session_id=session_id
                    )
                    local_storage.get_analyst_report("RW_TEST", "market_report", session_id)
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


class TestAnalysisRuns:
    """Tests for analysis runs storage functions"""

    def test_save_and_list_analysis_run(self, tmp_storage):
        """Test saving and listing analysis runs"""
        from webui.utils import local_storage

        local_storage.save_analysis_run(
            run_id="test-run-1",
            symbols=["AAPL", "NVDA"],
            tool_calls_count=10,
            llm_calls_count=5,
            generated_reports_count=3
        )

        runs = local_storage.list_analysis_runs()

        assert len(runs) >= 1
        run = next((r for r in runs if r["run_id"] == "test-run-1"), None)
        assert run is not None
        assert run["symbols"] == ["AAPL", "NVDA"]
        assert run["tool_calls_count"] == 10
        assert run["llm_calls_count"] == 5
        assert run["generated_reports_count"] == 3

    def test_get_analysis_run_with_reports(self, tmp_storage):
        """Test getting an analysis run with its reports"""
        from webui.utils import local_storage

        run_id = "test-run-with-reports"

        # Save run
        local_storage.save_analysis_run(
            run_id=run_id,
            symbols=["TSLA"],
            tool_calls_count=5,
            llm_calls_count=3,
            generated_reports_count=2
        )

        # Save associated reports
        local_storage.save_analyst_report("TSLA", "market_report", "Market analysis", session_id=run_id)
        local_storage.save_analyst_report("TSLA", "news_report", "News analysis", session_id=run_id)

        # Get run with reports
        run = local_storage.get_analysis_run(run_id)

        assert run is not None
        assert run["run_id"] == run_id
        assert "TSLA" in run["symbol_states"]
        assert run["symbol_states"]["TSLA"]["reports"]["market_report"] == "Market analysis"
        assert run["symbol_states"]["TSLA"]["reports"]["news_report"] == "News analysis"

    def test_get_nonexistent_run(self, tmp_storage):
        """Test getting a run that doesn't exist"""
        from webui.utils import local_storage

        run = local_storage.get_analysis_run("nonexistent-run")
        assert run is None

    def test_delete_analysis_run(self, tmp_storage):
        """Test deleting an analysis run and its reports"""
        from webui.utils import local_storage

        run_id = "test-run-to-delete"

        # Save run and reports
        local_storage.save_analysis_run(run_id=run_id, symbols=["META"])
        local_storage.save_analyst_report("META", "market_report", "Content", session_id=run_id)

        # Verify exists
        run = local_storage.get_analysis_run(run_id)
        assert run is not None

        # Delete
        result = local_storage.delete_analysis_run(run_id)
        assert result is True

        # Verify deleted
        run = local_storage.get_analysis_run(run_id)
        assert run is None

        # Verify reports also deleted
        report = local_storage.get_analyst_report("META", "market_report", run_id)
        assert report is None

    def test_list_runs_sorted_by_date(self, tmp_storage):
        """Test that runs are sorted by date (newest first)"""
        from webui.utils import local_storage
        import time

        # Create runs with 1+ second delay to ensure different timestamps
        local_storage.save_analysis_run(run_id="run-1", symbols=["A"])
        time.sleep(1.1)
        local_storage.save_analysis_run(run_id="run-2", symbols=["B"])
        time.sleep(1.1)
        local_storage.save_analysis_run(run_id="run-3", symbols=["C"])

        runs = local_storage.list_analysis_runs()

        # Most recent should be first
        run_ids = [r["run_id"] for r in runs]
        assert run_ids.index("run-3") < run_ids.index("run-2")
        assert run_ids.index("run-2") < run_ids.index("run-1")

    def test_list_runs_respects_limit(self, tmp_storage):
        """Test that list_analysis_runs respects limit parameter"""
        from webui.utils import local_storage

        # Create many runs
        for i in range(10):
            local_storage.save_analysis_run(run_id=f"limit-test-run-{i}", symbols=[f"SYM{i}"])

        runs = local_storage.list_analysis_runs(limit=3)

        assert len(runs) == 3

    def test_update_existing_run(self, tmp_storage):
        """Test updating an existing analysis run"""
        from webui.utils import local_storage

        run_id = "update-test-run"

        # Initial save
        local_storage.save_analysis_run(run_id=run_id, symbols=["AAPL"], tool_calls_count=5)

        # Update
        local_storage.save_analysis_run(run_id=run_id, symbols=["AAPL", "NVDA"], tool_calls_count=15)

        run = local_storage.get_analysis_run(run_id)

        assert run["symbols"] == ["AAPL", "NVDA"]
        assert run["tool_calls_count"] == 15


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
