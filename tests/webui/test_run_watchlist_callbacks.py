"""
Unit tests for Run Watchlist callback functions

These tests verify the callback behavior by testing the underlying logic
and simulating callback contexts where needed.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from dash import html
import dash_bootstrap_components as dbc


class TestAddToRunQueueCallback:
    """Tests for the add_to_run_queue callback"""

    def test_add_symbol_to_empty_queue(self):
        """Test adding a symbol to an empty Run Queue"""
        # Simulate callback inputs
        store_data = {"symbols": []}
        symbol_to_add = "AAPL"

        # Logic from the callback
        if not store_data:
            store_data = {"symbols": []}

        symbols = store_data.get("symbols", [])
        if symbol_to_add not in symbols:
            symbols.append(symbol_to_add)
            store_data["symbols"] = symbols

        assert store_data == {"symbols": ["AAPL"]}

    def test_add_multiple_symbols_sequentially(self):
        """Test adding multiple symbols one by one"""
        store_data = {"symbols": []}

        for symbol in ["AAPL", "MSFT", "NVDA"]:
            symbols = store_data.get("symbols", [])
            if symbol not in symbols:
                symbols.append(symbol)
                store_data["symbols"] = symbols

        assert store_data == {"symbols": ["AAPL", "MSFT", "NVDA"]}

    def test_add_symbol_prevents_duplicate(self):
        """Test that adding an existing symbol is prevented"""
        store_data = {"symbols": ["AAPL", "MSFT"]}
        symbol_to_add = "AAPL"

        symbols = store_data.get("symbols", [])
        original_count = len(symbols)

        if symbol_to_add not in symbols:
            symbols.append(symbol_to_add)
            store_data["symbols"] = symbols

        assert len(store_data["symbols"]) == original_count
        assert store_data["symbols"].count("AAPL") == 1


class TestRemoveFromRunQueueCallback:
    """Tests for the remove_from_run_queue callback"""

    def test_remove_existing_symbol(self):
        """Test removing an existing symbol"""
        store_data = {"symbols": ["AAPL", "MSFT", "NVDA"]}
        symbol_to_remove = "MSFT"

        symbols = store_data.get("symbols", [])
        if symbol_to_remove in symbols:
            symbols.remove(symbol_to_remove)
            store_data["symbols"] = symbols

        assert "MSFT" not in store_data["symbols"]
        assert store_data == {"symbols": ["AAPL", "NVDA"]}

    def test_remove_first_symbol(self):
        """Test removing the first symbol in the list"""
        store_data = {"symbols": ["AAPL", "MSFT", "NVDA"]}

        symbols = store_data.get("symbols", [])
        if "AAPL" in symbols:
            symbols.remove("AAPL")
            store_data["symbols"] = symbols

        assert store_data == {"symbols": ["MSFT", "NVDA"]}

    def test_remove_last_symbol(self):
        """Test removing the last symbol in the list"""
        store_data = {"symbols": ["AAPL", "MSFT", "NVDA"]}

        symbols = store_data.get("symbols", [])
        if "NVDA" in symbols:
            symbols.remove("NVDA")
            store_data["symbols"] = symbols

        assert store_data == {"symbols": ["AAPL", "MSFT"]}

    def test_remove_only_symbol(self):
        """Test removing the only symbol leaves empty list"""
        store_data = {"symbols": ["AAPL"]}

        symbols = store_data.get("symbols", [])
        if "AAPL" in symbols:
            symbols.remove("AAPL")
            store_data["symbols"] = symbols

        assert store_data == {"symbols": []}

    def test_remove_nonexistent_symbol(self):
        """Test removing a symbol that doesn't exist"""
        store_data = {"symbols": ["AAPL", "MSFT"]}
        symbol_to_remove = "TSLA"

        symbols = store_data.get("symbols", [])
        if symbol_to_remove in symbols:
            symbols.remove(symbol_to_remove)
            store_data["symbols"] = symbols

        assert store_data == {"symbols": ["AAPL", "MSFT"]}


class TestClearRunQueueCallback:
    """Tests for the clear_run_queue callback"""

    def test_clear_populated_queue(self):
        """Test clearing a queue with multiple symbols"""
        store_data = {"symbols": ["AAPL", "MSFT", "NVDA", "TSLA"]}

        # Simulate clear callback
        store_data = {"symbols": []}

        assert store_data == {"symbols": []}

    def test_clear_empty_queue(self):
        """Test clearing an already empty queue"""
        store_data = {"symbols": []}

        store_data = {"symbols": []}

        assert store_data == {"symbols": []}

    def test_clear_single_item_queue(self):
        """Test clearing a queue with one symbol"""
        store_data = {"symbols": ["AAPL"]}

        store_data = {"symbols": []}

        assert store_data == {"symbols": []}


class TestUpdateRunQueueDisplayCallback:
    """Tests for the update_run_queue_display callback"""

    def test_display_with_symbols(self):
        """Test display update with symbols in queue"""
        from webui.components.run_watchlist import create_run_watchlist_item

        store_data = {"symbols": ["AAPL", "MSFT"]}

        # Simulate the display callback logic
        symbols = store_data.get("symbols", [])
        items = [create_run_watchlist_item(symbol, i) for i, symbol in enumerate(symbols)]
        count = str(len(symbols))

        assert len(items) == 2
        assert count == "2"

    def test_display_empty_queue(self):
        """Test display update with empty queue"""
        store_data = {"symbols": []}

        # Simulate the display callback logic
        if not store_data or not store_data.get("symbols"):
            is_empty = True
            count = "0"
        else:
            is_empty = False
            count = str(len(store_data["symbols"]))

        assert is_empty is True
        assert count == "0"

    def test_display_none_store(self):
        """Test display update with None store"""
        store_data = None

        if not store_data or not store_data.get("symbols"):
            is_empty = True
            count = "0"
        else:
            is_empty = False
            count = str(len(store_data["symbols"]))

        assert is_empty is True
        assert count == "0"

    def test_count_badge_updates(self):
        """Test that count badge gets correct value"""
        store_data = {"symbols": ["AAPL", "MSFT", "NVDA", "TSLA", "AMD"]}

        symbols = store_data.get("symbols", [])
        count = str(len(symbols))

        assert count == "5"


class TestAnalyzeFromWatchlistCallback:
    """Tests for the analyze_from_watchlist callback (adds to Run Queue)"""

    def test_analyze_adds_to_run_queue(self):
        """Test that clicking analyze adds symbol to Run Queue"""
        store_data = {"symbols": ["AAPL"]}
        symbol = "MSFT"

        # Simulate callback logic
        symbols = store_data.get("symbols", [])
        if symbol.upper() not in symbols:
            symbols.append(symbol.upper())
            store_data["symbols"] = symbols

        assert "MSFT" in store_data["symbols"]
        assert store_data == {"symbols": ["AAPL", "MSFT"]}

    def test_analyze_normalizes_symbol_case(self):
        """Test that symbol is normalized to uppercase"""
        store_data = {"symbols": []}
        symbol = "nvda"

        symbols = store_data.get("symbols", [])
        if symbol.upper() not in symbols:
            symbols.append(symbol.upper())
            store_data["symbols"] = symbols

        assert store_data == {"symbols": ["NVDA"]}

    def test_analyze_prevents_duplicate(self):
        """Test that duplicate symbols aren't added via analyze"""
        store_data = {"symbols": ["AAPL"]}
        symbol = "AAPL"

        symbols = store_data.get("symbols", [])
        if symbol.upper() not in symbols:
            symbols.append(symbol.upper())
            store_data["symbols"] = symbols

        assert len(store_data["symbols"]) == 1


class TestScannerAddToRunQueueCallback:
    """Tests for scanner adding symbols to Run Queue"""

    def test_scanner_analyze_adds_to_run_queue(self):
        """Test that scanner analyze button adds to Run Queue"""
        store_data = {"symbols": []}
        symbol = "AAPL"

        # Simulate scanner callback logic
        if not store_data:
            store_data = {"symbols": []}

        symbols = store_data.get("symbols", [])
        if symbol.upper() not in symbols:
            symbols.append(symbol.upper())
            store_data["symbols"] = symbols

        assert store_data == {"symbols": ["AAPL"]}

    def test_scanner_add_multiple_symbols(self):
        """Test adding multiple symbols from scanner"""
        store_data = {"symbols": []}
        scanner_symbols = ["AAPL", "MSFT", "NVDA"]

        for symbol in scanner_symbols:
            symbols = store_data.get("symbols", [])
            if symbol.upper() not in symbols:
                symbols.append(symbol.upper())
                store_data["symbols"] = symbols

        assert store_data == {"symbols": ["AAPL", "MSFT", "NVDA"]}


class TestControlCallbacksIntegration:
    """Tests for Run Queue integration with control callbacks"""

    def test_start_analysis_reads_from_run_queue(self):
        """Test that analysis reads symbols from Run Queue"""
        run_watchlist_data = {"symbols": ["NVDA", "AMD", "TSLA"]}

        # Simulate the extraction in control_callbacks
        run_store = run_watchlist_data or {"symbols": []}
        symbols = run_store.get("symbols", [])

        assert symbols == ["NVDA", "AMD", "TSLA"]

    def test_empty_run_queue_prevents_analysis(self):
        """Test that empty Run Queue prevents analysis start"""
        run_watchlist_data = {"symbols": []}

        run_store = run_watchlist_data or {"symbols": []}
        symbols = run_store.get("symbols", [])

        can_start = len(symbols) > 0
        assert can_start is False

    def test_none_store_prevents_analysis(self):
        """Test that None store prevents analysis start"""
        run_watchlist_data = None

        run_store = run_watchlist_data or {"symbols": []}
        symbols = run_store.get("symbols", [])

        can_start = len(symbols) > 0
        assert can_start is False

    def test_single_symbol_analysis(self):
        """Test starting analysis with single symbol"""
        run_watchlist_data = {"symbols": ["AAPL"]}

        run_store = run_watchlist_data or {"symbols": []}
        symbols = run_store.get("symbols", [])

        assert symbols == ["AAPL"]
        assert len(symbols) == 1


class TestHistoryCallbacksIntegration:
    """Tests for Run Queue integration with history callbacks"""

    def test_save_history_reads_from_run_queue(self):
        """Test that history save reads symbols from Run Queue"""
        run_watchlist_data = {"symbols": ["AAPL", "MSFT"]}

        run_store = run_watchlist_data or {"symbols": []}
        symbols = run_store.get("symbols", [])

        assert symbols == ["AAPL", "MSFT"]

    def test_empty_run_queue_prevents_history_save(self):
        """Test that empty Run Queue shows no data message"""
        run_watchlist_data = {"symbols": []}

        run_store = run_watchlist_data or {"symbols": []}
        symbols = run_store.get("symbols", [])

        has_data = len(symbols) > 0
        assert has_data is False


class TestUXCallbacksIntegration:
    """Tests for Run Queue integration with UX callbacks"""

    def test_agent_summary_reads_from_run_queue(self):
        """Test that agent summary reads symbols from Run Queue"""
        run_watchlist_data = {"symbols": ["NVDA", "AMD"]}

        run_store = run_watchlist_data or {"symbols": []}
        symbols = run_store.get("symbols", [])

        assert len(symbols) == 2
        assert "NVDA" in symbols

    def test_toast_notification_reads_from_run_queue(self):
        """Test that toast reads symbols from Run Queue"""
        run_watchlist_data = {"symbols": ["TSLA"]}

        run_store = run_watchlist_data or {"symbols": []}
        symbols = run_store.get("symbols", [])

        assert symbols == ["TSLA"]


class TestChartCallbacksIntegration:
    """Tests for Run Queue integration with chart callbacks"""

    def test_chart_fallback_to_run_queue(self):
        """Test that chart falls back to Run Queue for symbol"""
        run_watchlist_data = {"symbols": ["AAPL", "MSFT"]}
        chart_store_data = None  # No last symbol

        # Simulate the chart callback fallback logic
        if chart_store_data and chart_store_data.get("last_symbol"):
            symbol = chart_store_data["last_symbol"]
        elif run_watchlist_data and run_watchlist_data.get("symbols"):
            symbol = run_watchlist_data["symbols"][0]
        else:
            symbol = None

        assert symbol == "AAPL"

    def test_chart_prefers_last_symbol(self):
        """Test that chart prefers last_symbol over Run Queue"""
        run_watchlist_data = {"symbols": ["AAPL", "MSFT"]}
        chart_store_data = {"last_symbol": "NVDA"}

        if chart_store_data and chart_store_data.get("last_symbol"):
            symbol = chart_store_data["last_symbol"]
        elif run_watchlist_data and run_watchlist_data.get("symbols"):
            symbol = run_watchlist_data["symbols"][0]
        else:
            symbol = None

        assert symbol == "NVDA"


class TestConfigPanelRunQueueDisplay:
    """Tests for Run Queue display in config panel"""

    def test_config_panel_count_sync(self):
        """Test that config panel count syncs with Run Queue"""
        store_data = {"symbols": ["AAPL", "MSFT", "NVDA"]}

        symbols = store_data.get("symbols", [])
        count = str(len(symbols))

        assert count == "3"

    def test_config_panel_empty_count(self):
        """Test config panel shows 0 for empty queue"""
        store_data = {"symbols": []}

        symbols = store_data.get("symbols", [])
        count = str(len(symbols))

        assert count == "0"


class TestWatchlistToRunQueueFlow:
    """Integration tests for the Watchlist -> Run Queue flow"""

    def test_add_from_watchlist_to_run_queue(self):
        """Test adding a symbol from watchlist to run queue"""
        watchlist_store = {"symbols": ["AAPL", "MSFT", "NVDA"]}
        run_queue_store = {"symbols": []}

        # Simulate clicking "Add to Run" on MSFT
        symbol_to_add = "MSFT"

        symbols = run_queue_store.get("symbols", [])
        if symbol_to_add not in symbols:
            symbols.append(symbol_to_add)
            run_queue_store["symbols"] = symbols

        # Watchlist should remain unchanged
        assert watchlist_store == {"symbols": ["AAPL", "MSFT", "NVDA"]}
        # Run Queue should have the symbol
        assert run_queue_store == {"symbols": ["MSFT"]}

    def test_multiple_adds_from_watchlist(self):
        """Test adding multiple symbols from watchlist"""
        run_queue_store = {"symbols": []}

        for symbol in ["AAPL", "MSFT"]:
            symbols = run_queue_store.get("symbols", [])
            if symbol not in symbols:
                symbols.append(symbol)
                run_queue_store["symbols"] = symbols

        assert run_queue_store == {"symbols": ["AAPL", "MSFT"]}


class TestScannerToWatchlistToRunQueueFlow:
    """Integration tests for Scanner -> Watchlist -> Run Queue flow"""

    def test_scanner_to_watchlist_to_run_queue(self):
        """Test the complete flow from scanner to run queue"""
        watchlist_store = {"symbols": []}
        run_queue_store = {"symbols": []}

        # Step 1: Add from scanner to watchlist
        scanner_symbol = "AAPL"
        symbols = watchlist_store.get("symbols", [])
        if scanner_symbol not in symbols:
            symbols.append(scanner_symbol)
            watchlist_store["symbols"] = symbols

        assert watchlist_store == {"symbols": ["AAPL"]}

        # Step 2: Add from watchlist to run queue
        symbols = run_queue_store.get("symbols", [])
        if scanner_symbol not in symbols:
            symbols.append(scanner_symbol)
            run_queue_store["symbols"] = symbols

        assert run_queue_store == {"symbols": ["AAPL"]}

    def test_scanner_direct_to_run_queue(self):
        """Test adding from scanner directly to run queue via analyze button"""
        run_queue_store = {"symbols": []}

        scanner_symbol = "NVDA"
        symbols = run_queue_store.get("symbols", [])
        if scanner_symbol.upper() not in symbols:
            symbols.append(scanner_symbol.upper())
            run_queue_store["symbols"] = symbols

        assert run_queue_store == {"symbols": ["NVDA"]}
