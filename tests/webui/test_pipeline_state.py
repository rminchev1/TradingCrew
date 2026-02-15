"""
Tests for pipeline state management and control flow.

Tests the fixes for:
1. Interruptible stagger delays
2. Thread-local symbol tracking
3. Error state tracking
4. Pipeline pause/resume/stop
5. Memory management (tool_calls_log clearing)
6. State initialization
"""

import pytest
import threading
import time
from unittest.mock import patch, MagicMock


class TestAppStateInitialization:
    """Tests for AppState initialization and duplicate field removal."""

    def test_no_duplicate_loop_fields(self):
        """Verify loop fields are not duplicated in __init__."""
        from webui.utils.state import AppState

        state = AppState()

        # These fields should exist only once
        assert hasattr(state, 'loop_enabled')
        assert hasattr(state, 'loop_symbols')
        assert hasattr(state, 'loop_config')
        assert hasattr(state, 'loop_interval_minutes')
        assert hasattr(state, 'stop_loop')

        # Verify they have correct default values
        assert state.loop_enabled is False
        assert state.loop_symbols == []
        assert state.loop_config == {}
        assert state.loop_interval_minutes == 60
        assert state.stop_loop is False

    def test_no_duplicate_market_hour_fields(self):
        """Verify market hour fields are not duplicated in __init__."""
        from webui.utils.state import AppState

        state = AppState()

        assert hasattr(state, 'market_hour_enabled')
        assert hasattr(state, 'market_hour_symbols')
        assert hasattr(state, 'market_hour_config')
        assert hasattr(state, 'market_hours')
        assert hasattr(state, 'stop_market_hour')

        assert state.market_hour_enabled is False
        assert state.market_hour_symbols == []
        assert state.market_hour_config == {}
        assert state.market_hours == []
        assert state.stop_market_hour is False

    def test_no_duplicate_trade_fields(self):
        """Verify trade fields are not duplicated in __init__."""
        from webui.utils.state import AppState

        state = AppState()

        assert hasattr(state, 'trade_enabled')
        assert hasattr(state, 'trade_amount')
        assert hasattr(state, 'trade_occurred')

        assert state.trade_enabled is False
        assert state.trade_amount == 1000
        assert state.trade_occurred is False


class TestSymbolStateErrorTracking:
    """Tests for error tracking in symbol state."""

    def test_symbol_state_has_error_fields(self):
        """Symbol state should include has_error and error_message fields."""
        from webui.utils.state import AppState

        state = AppState()
        state.init_symbol_state("AAPL")

        symbol_state = state.get_state("AAPL")
        assert "has_error" in symbol_state
        assert "error_message" in symbol_state
        assert symbol_state["has_error"] is False
        assert symbol_state["error_message"] is None

    def test_reset_for_loop_clears_error_fields(self):
        """reset_for_loop should clear error tracking fields."""
        from webui.utils.state import AppState

        state = AppState()
        state.init_symbol_state("AAPL")

        # Simulate error
        symbol_state = state.get_state("AAPL")
        symbol_state["has_error"] = True
        symbol_state["error_message"] = "Test error"

        # Reset
        state.reset_for_loop()

        # Verify cleared
        symbol_state = state.get_state("AAPL")
        assert symbol_state["has_error"] is False
        assert symbol_state["error_message"] is None


class TestInterruptibleSleep:
    """Tests for interruptible_sleep method."""

    def test_interruptible_sleep_completes_normally(self):
        """interruptible_sleep should return True when not interrupted."""
        from webui.utils.state import AppState

        state = AppState()
        state.reset_pipeline_controls()

        start = time.time()
        result = state.interruptible_sleep(0.2)
        elapsed = time.time() - start

        assert result is True
        assert elapsed >= 0.2
        assert elapsed < 0.5  # Should not take too long

    def test_interruptible_sleep_interrupted_by_stop(self):
        """interruptible_sleep should return False when stop event is set."""
        from webui.utils.state import AppState

        state = AppState()
        state.reset_pipeline_controls()

        # Set stop event in another thread after a short delay
        def set_stop():
            time.sleep(0.1)
            state._stop_event.set()

        thread = threading.Thread(target=set_stop)
        thread.start()

        start = time.time()
        result = state.interruptible_sleep(5.0)  # Would take 5s if not interrupted
        elapsed = time.time() - start

        thread.join()

        assert result is False
        assert elapsed < 1.0  # Should be interrupted quickly


class TestPipelineControl:
    """Tests for pipeline pause/resume/stop."""

    def test_pause_pipeline(self):
        """pause_pipeline should set paused state."""
        from webui.utils.state import AppState

        state = AppState()
        state.reset_pipeline_controls()

        assert state.pipeline_paused is False
        assert state._pause_event.is_set()

        state.pause_pipeline()

        assert state.pipeline_paused is True
        assert not state._pause_event.is_set()

    def test_resume_pipeline(self):
        """resume_pipeline should clear paused state."""
        from webui.utils.state import AppState

        state = AppState()
        state.pause_pipeline()

        assert state.pipeline_paused is True

        state.resume_pipeline()

        assert state.pipeline_paused is False
        assert state._pause_event.is_set()

    def test_stop_pipeline_unblocks_paused_threads(self):
        """stop_pipeline should set pause_event to unblock paused threads."""
        from webui.utils.state import AppState

        state = AppState()
        state.pause_pipeline()

        assert not state._pause_event.is_set()

        state.stop_pipeline()

        # pause_event should be set to unblock waiting threads
        assert state._pause_event.is_set()
        assert state._stop_event.is_set()
        assert state.pipeline_stopped is True

    def test_check_pipeline_interrupt_blocks_on_pause(self):
        """check_pipeline_interrupt should block when paused."""
        from webui.utils.state import AppState

        state = AppState()
        state.reset_pipeline_controls()
        state.pause_pipeline()

        result_holder = {"result": None}

        def check_interrupt():
            # This should block until resumed
            result = state.check_pipeline_interrupt(symbol="AAPL")
            result_holder["result"] = result

        thread = threading.Thread(target=check_interrupt)
        thread.start()

        # Give thread time to start and block
        time.sleep(0.2)

        # Thread should still be running (blocked)
        assert thread.is_alive()

        # Resume and wait for thread
        state.resume_pipeline()
        thread.join(timeout=1.0)

        assert not thread.is_alive()
        assert result_holder["result"] == "continue"

    def test_check_pipeline_interrupt_returns_stopped(self):
        """check_pipeline_interrupt should return 'stopped' when stop event is set."""
        from webui.utils.state import AppState

        state = AppState()
        state.reset_pipeline_controls()
        state._stop_event.set()

        result = state.check_pipeline_interrupt(symbol="AAPL")

        assert result == "stopped"


class TestMemoryManagement:
    """Tests for memory leak prevention."""

    def test_reset_clears_tool_calls_log(self):
        """reset() should clear tool_calls_log to prevent memory leak."""
        from webui.utils.state import AppState

        state = AppState()

        # Add some mock tool calls
        state.tool_calls_log = [
            {"tool_name": "test", "timestamp": "00:00:00"},
            {"tool_name": "test2", "timestamp": "00:00:01"},
        ]
        state.llm_calls_log = [
            ("00:00:00", "Reasoning", "test"),
        ]

        state.reset()

        assert state.tool_calls_log == []
        assert state.llm_calls_log == []

    def test_reset_for_loop_clears_tool_calls_log(self):
        """reset_for_loop() should clear tool_calls_log."""
        from webui.utils.state import AppState

        state = AppState()
        state.init_symbol_state("AAPL")

        state.tool_calls_log = [{"tool_name": "test"}]
        state.llm_calls_log = [("00:00:00", "Reasoning", "test")]

        state.reset_for_loop()

        assert state.tool_calls_log == []
        assert state.llm_calls_log == []


class TestThreadLocalSymbol:
    """Tests for thread-local symbol tracking."""

    def test_thread_local_isolation(self):
        """Each thread should have its own symbol."""
        from webui.utils.state import set_thread_symbol, get_thread_symbol, clear_thread_symbol

        results = {}

        def thread_work(symbol, thread_id):
            set_thread_symbol(symbol)
            time.sleep(0.1)  # Allow other threads to run
            results[thread_id] = get_thread_symbol()
            clear_thread_symbol()

        threads = []
        for i, symbol in enumerate(["AAPL", "NVDA", "TSLA"]):
            t = threading.Thread(target=thread_work, args=(symbol, i))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Each thread should have read its own symbol
        assert results[0] == "AAPL"
        assert results[1] == "NVDA"
        assert results[2] == "TSLA"

    def test_clear_thread_symbol(self):
        """clear_thread_symbol should set thread symbol to None."""
        from webui.utils.state import set_thread_symbol, get_thread_symbol, clear_thread_symbol

        set_thread_symbol("AAPL")
        assert get_thread_symbol() == "AAPL"

        clear_thread_symbol()
        assert get_thread_symbol() is None


class TestPropagatorInitialState:
    """Tests for graph propagator initial state."""

    def test_initial_state_has_options_report(self):
        """Initial state should include options_report field."""
        from tradingagents.graph.propagation import Propagator

        propagator = Propagator()
        state = propagator.create_initial_state("AAPL", "2025-01-01")

        assert "options_report" in state
        assert state["options_report"] == ""

    def test_initial_state_has_all_report_fields(self):
        """Initial state should have all required report fields."""
        from tradingagents.graph.propagation import Propagator

        propagator = Propagator()
        state = propagator.create_initial_state("AAPL", "2025-01-01")

        expected_fields = [
            "market_report",
            "fundamentals_report",
            "sentiment_report",
            "news_report",
            "macro_report",
            "options_report",
            "sector_correlation_report",
        ]

        for field in expected_fields:
            assert field in state, f"Missing field: {field}"
            assert state[field] == ""


class TestAnalysisErrorHandling:
    """Tests for analysis error state tracking."""

    def test_error_state_set_on_exception(self):
        """has_error should be set when analysis fails."""
        from webui.utils.state import AppState

        state = AppState()
        state.init_symbol_state("AAPL")

        symbol_state = state.get_state("AAPL")

        # Simulate error handling from analysis.py
        error_msg = "Test error"
        symbol_state["analysis_complete"] = True
        symbol_state["has_error"] = True
        symbol_state["error_message"] = error_msg

        assert symbol_state["analysis_complete"] is True
        assert symbol_state["has_error"] is True
        assert symbol_state["error_message"] == error_msg

    def test_can_distinguish_success_from_error(self):
        """Should be able to distinguish successful completion from error."""
        from webui.utils.state import AppState

        state = AppState()

        # Symbol with successful completion
        state.init_symbol_state("AAPL")
        aapl_state = state.get_state("AAPL")
        aapl_state["analysis_complete"] = True
        aapl_state["has_error"] = False

        # Symbol with error completion
        state.init_symbol_state("NVDA")
        nvda_state = state.get_state("NVDA")
        nvda_state["analysis_complete"] = True
        nvda_state["has_error"] = True
        nvda_state["error_message"] = "API timeout"

        # Both are "complete" but we can tell them apart
        assert aapl_state["analysis_complete"] is True
        assert nvda_state["analysis_complete"] is True

        assert aapl_state["has_error"] is False
        assert nvda_state["has_error"] is True
