"""
Tests for thread-local symbol tracking in parallel ticker analysis.

This tests the fix for the race condition where tool outputs were tagged
with the wrong ticker during parallel execution.
"""

import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


class TestThreadLocalSymbol:
    """Tests for thread-local symbol storage."""

    def test_thread_local_functions_exist(self):
        """Verify thread-local functions are exported from state module."""
        from webui.utils.state import get_thread_symbol, set_thread_symbol, clear_thread_symbol

        # All functions should exist
        assert callable(get_thread_symbol)
        assert callable(set_thread_symbol)
        assert callable(clear_thread_symbol)

    def test_set_and_get_thread_symbol(self):
        """Verify set and get work for thread-local symbol."""
        from webui.utils.state import get_thread_symbol, set_thread_symbol, clear_thread_symbol

        # Initially should be None
        clear_thread_symbol()
        assert get_thread_symbol() is None

        # Set a symbol
        set_thread_symbol("AAPL")
        assert get_thread_symbol() == "AAPL"

        # Clear it
        clear_thread_symbol()
        assert get_thread_symbol() is None

    def test_thread_isolation(self):
        """Verify each thread has its own symbol (thread isolation)."""
        from webui.utils.state import get_thread_symbol, set_thread_symbol, clear_thread_symbol

        results = {}
        errors = []

        def worker(symbol, worker_id):
            try:
                # Set this thread's symbol
                set_thread_symbol(symbol)

                # Small delay to allow race conditions to manifest
                time.sleep(0.01)

                # Verify we still have our own symbol
                current = get_thread_symbol()
                results[worker_id] = {
                    "expected": symbol,
                    "actual": current,
                    "match": current == symbol
                }

                # Clean up
                clear_thread_symbol()
            except Exception as e:
                errors.append((worker_id, str(e)))

        # Run multiple threads with different symbols
        threads = []
        test_data = [
            ("AAPL", 1),
            ("NVDA", 2),
            ("HOOD", 3),
            ("TSLA", 4),
            ("MSFT", 5),
        ]

        for symbol, worker_id in test_data:
            t = threading.Thread(target=worker, args=(symbol, worker_id))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify all workers got their expected symbol
        for worker_id, result in results.items():
            assert result["match"], f"Worker {worker_id}: expected {result['expected']}, got {result['actual']}"

    def test_thread_pool_executor_isolation(self):
        """Verify thread isolation works with ThreadPoolExecutor (as used in parallel ticker analysis)."""
        from webui.utils.state import get_thread_symbol, set_thread_symbol, clear_thread_symbol

        results = {}

        def analyze_ticker(symbol):
            """Simulate ticker analysis."""
            set_thread_symbol(symbol)

            # Simulate some work with multiple checks
            for _ in range(3):
                time.sleep(0.01)
                current = get_thread_symbol()
                if current != symbol:
                    return symbol, False, f"Symbol changed from {symbol} to {current}"

            clear_thread_symbol()
            return symbol, True, None

        symbols = ["AAPL", "NVDA", "HOOD", "TSLA", "MSFT", "AMD", "GOOG", "META"]

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(analyze_ticker, s): s for s in symbols}

            for future in as_completed(futures):
                symbol, success, error = future.result()
                results[symbol] = {"success": success, "error": error}

        # All should succeed
        for symbol, result in results.items():
            assert result["success"], f"{symbol} failed: {result['error']}"


class TestAppStateThreadSafety:
    """Tests for AppState thread-safe symbol methods."""

    def test_start_analyzing_symbol_sets_thread_local(self):
        """Verify start_analyzing_symbol sets thread-local symbol."""
        from webui.utils.state import app_state, get_thread_symbol, clear_thread_symbol

        # Clean state
        clear_thread_symbol()

        # Start analyzing
        app_state.start_analyzing_symbol("TEST")

        # Thread-local should be set
        assert get_thread_symbol() == "TEST"

        # Clean up
        app_state.stop_analyzing_symbol("TEST")
        assert get_thread_symbol() is None

    def test_stop_analyzing_symbol_clears_thread_local(self):
        """Verify stop_analyzing_symbol clears thread-local symbol."""
        from webui.utils.state import app_state, get_thread_symbol, set_thread_symbol

        # Set symbol
        set_thread_symbol("TEST")
        app_state.analyzing_symbols.add("TEST")

        # Stop analyzing
        app_state.stop_analyzing_symbol("TEST")

        # Thread-local should be cleared
        assert get_thread_symbol() is None

    def test_parallel_start_analyzing_isolated(self):
        """Verify parallel start_analyzing_symbol calls are isolated."""
        from webui.utils.state import app_state, get_thread_symbol, clear_thread_symbol

        results = {}

        def analyze(symbol):
            app_state.start_analyzing_symbol(symbol)
            time.sleep(0.02)
            current = get_thread_symbol()
            result = current == symbol
            app_state.stop_analyzing_symbol(symbol)
            return symbol, result, current

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(analyze, s): s for s in ["A", "B", "C"]}

            for future in as_completed(futures):
                symbol, matched, actual = future.result()
                results[symbol] = {"matched": matched, "actual": actual}

        for symbol, result in results.items():
            assert result["matched"], f"{symbol} had wrong thread-local: {result['actual']}"


class TestGetCurrentSymbolHelper:
    """Tests for the _get_current_symbol helper in agent_utils."""

    def test_get_current_symbol_prefers_thread_local(self):
        """Verify _get_current_symbol prefers thread-local over global."""
        from tradingagents.agents.utils.agent_utils import _get_current_symbol
        from webui.utils.state import app_state, set_thread_symbol, clear_thread_symbol

        # Set global to one thing
        app_state.analyzing_symbol = "GLOBAL"
        app_state.current_symbol = "UI"

        # Set thread-local to another
        set_thread_symbol("THREAD")

        # Should prefer thread-local
        assert _get_current_symbol() == "THREAD"

        # Clean up
        clear_thread_symbol()
        app_state.analyzing_symbol = None
        app_state.current_symbol = None

    def test_get_current_symbol_falls_back_to_global(self):
        """Verify _get_current_symbol falls back to global when no thread-local."""
        from tradingagents.agents.utils.agent_utils import _get_current_symbol
        from webui.utils.state import app_state, clear_thread_symbol

        # Clear thread-local
        clear_thread_symbol()

        # Set global
        app_state.analyzing_symbol = "GLOBAL"

        # Should fall back to global
        assert _get_current_symbol() == "GLOBAL"

        # Clean up
        app_state.analyzing_symbol = None
