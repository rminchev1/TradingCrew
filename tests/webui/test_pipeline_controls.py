"""
Unit tests for pipeline pause/resume/stop controls.
"""

import pytest
import threading
import time
from unittest.mock import patch, MagicMock


class TestPipelineControlState:
    """Tests for pause/stop/resume state management on AppState."""

    def test_initial_state_not_paused_not_stopped(self, app_state):
        """Pipeline starts in running state."""
        assert not app_state.pipeline_paused
        assert not app_state.pipeline_stopped
        assert app_state._pause_event.is_set()
        assert not app_state._stop_event.is_set()

    def test_pause_sets_flags(self, app_state):
        """Pausing sets correct flags."""
        app_state.pause_pipeline()
        assert app_state.pipeline_paused
        assert not app_state._pause_event.is_set()

    def test_resume_clears_flags(self, app_state):
        """Resuming clears pause flags."""
        app_state.pause_pipeline()
        app_state.resume_pipeline()
        assert not app_state.pipeline_paused
        assert app_state._pause_event.is_set()

    def test_stop_sets_all_flags(self, app_state):
        """Stopping sets stop flag and clears pause."""
        app_state.analysis_running = True
        app_state.stop_pipeline()
        assert app_state.pipeline_stopped
        assert not app_state.pipeline_paused
        assert app_state._stop_event.is_set()
        assert not app_state.analysis_running

    def test_stop_while_paused_unblocks(self, app_state):
        """Stopping while paused unblocks paused threads."""
        app_state.pause_pipeline()
        assert not app_state._pause_event.is_set()
        app_state.stop_pipeline()
        # Pause event must be set so blocked threads wake up
        assert app_state._pause_event.is_set()
        assert app_state._stop_event.is_set()

    def test_reset_pipeline_controls(self, app_state):
        """Reset clears all pipeline control state."""
        app_state.stop_pipeline()
        app_state.reset_pipeline_controls()
        assert not app_state.pipeline_paused
        assert not app_state.pipeline_stopped
        assert app_state._pause_event.is_set()
        assert not app_state._stop_event.is_set()
        assert len(app_state.paused_symbols) == 0

    def test_stop_sets_legacy_flags(self, app_state):
        """Stopping sets legacy stop_loop and stop_market_hour flags."""
        app_state.loop_enabled = True
        app_state.market_hour_enabled = True
        app_state.stop_pipeline()
        assert app_state.stop_loop is True
        assert app_state.stop_market_hour is True
        assert not app_state.loop_enabled
        assert not app_state.market_hour_enabled

    def test_reset_called_from_full_reset(self, app_state):
        """Full reset() also resets pipeline controls."""
        app_state.stop_pipeline()
        assert app_state._stop_event.is_set()
        app_state.reset()
        assert not app_state._stop_event.is_set()
        assert not app_state.pipeline_stopped


class TestCheckPipelineInterrupt:
    """Tests for the check_pipeline_interrupt method."""

    def test_returns_continue_when_running(self, app_state):
        """Normal running state returns 'continue'."""
        result = app_state.check_pipeline_interrupt(symbol="AAPL")
        assert result == "continue"

    def test_returns_stopped_when_stopped(self, app_state):
        """Stopped state returns 'stopped'."""
        app_state._stop_event.set()
        result = app_state.check_pipeline_interrupt(symbol="AAPL")
        assert result == "stopped"

    def test_blocks_when_paused_then_resumes(self, app_state):
        """Pause blocks the thread, resume unblocks it."""
        result_holder = {}

        def worker():
            result_holder["status"] = app_state.check_pipeline_interrupt(symbol="AAPL")

        app_state.pause_pipeline()
        t = threading.Thread(target=worker)
        t.start()

        time.sleep(0.3)  # Let thread block
        assert t.is_alive()  # Thread should be blocked
        assert "AAPL" in app_state.paused_symbols

        app_state.resume_pipeline()
        t.join(timeout=3)
        assert not t.is_alive()
        assert result_holder["status"] == "continue"

    def test_stop_unblocks_paused_thread(self, app_state):
        """Stop unblocks a paused thread with 'stopped' status."""
        result_holder = {}

        def worker():
            result_holder["status"] = app_state.check_pipeline_interrupt(symbol="NVDA")

        app_state.pause_pipeline()
        t = threading.Thread(target=worker)
        t.start()

        time.sleep(0.3)
        app_state.stop_pipeline()
        t.join(timeout=3)
        assert result_holder["status"] == "stopped"

    def test_tracks_paused_symbols(self, app_state):
        """Paused symbols are tracked and cleared on resume."""
        def worker(symbol):
            app_state.check_pipeline_interrupt(symbol=symbol)

        app_state.pause_pipeline()
        threads = [
            threading.Thread(target=worker, args=(s,))
            for s in ["AAPL", "NVDA"]
        ]
        for t in threads:
            t.start()

        time.sleep(0.3)
        assert "AAPL" in app_state.paused_symbols
        assert "NVDA" in app_state.paused_symbols

        app_state.resume_pipeline()
        for t in threads:
            t.join(timeout=3)

        # After resume, symbols should be removed from paused set
        assert "AAPL" not in app_state.paused_symbols
        assert "NVDA" not in app_state.paused_symbols


class TestParallelTickerPauseStop:
    """Tests for pause/stop with multiple parallel tickers."""

    def test_multiple_threads_pause_simultaneously(self, app_state):
        """Multiple ticker threads all pause at their breakpoints."""
        results = {}

        def worker(symbol):
            results[symbol] = app_state.check_pipeline_interrupt(symbol=symbol)

        app_state.pause_pipeline()
        threads = [
            threading.Thread(target=worker, args=(s,))
            for s in ["AAPL", "NVDA", "TSLA"]
        ]
        for t in threads:
            t.start()

        time.sleep(0.3)
        # All should be paused
        assert len(app_state.paused_symbols) == 3

        app_state.resume_pipeline()
        for t in threads:
            t.join(timeout=3)

        assert all(r == "continue" for r in results.values())

    def test_stop_releases_all_paused_threads(self, app_state):
        """Stop releases all paused threads."""
        results = {}

        def worker(symbol):
            results[symbol] = app_state.check_pipeline_interrupt(symbol=symbol)

        app_state.pause_pipeline()
        threads = [
            threading.Thread(target=worker, args=(s,))
            for s in ["AAPL", "NVDA"]
        ]
        for t in threads:
            t.start()

        time.sleep(0.3)
        app_state.stop_pipeline()
        for t in threads:
            t.join(timeout=3)

        assert all(r == "stopped" for r in results.values())

    def test_pause_resume_multiple_cycles(self, app_state):
        """Multiple pause/resume cycles work correctly."""
        results = []

        def worker():
            for _ in range(3):
                status = app_state.check_pipeline_interrupt(symbol="AAPL")
                results.append(status)
                if status == "stopped":
                    break

        t = threading.Thread(target=worker)
        t.start()

        # Let worker run through first check (not paused)
        time.sleep(0.1)

        # Pause, then resume
        app_state.pause_pipeline()
        time.sleep(0.3)
        app_state.resume_pipeline()
        time.sleep(0.1)

        t.join(timeout=5)
        assert all(r == "continue" for r in results)


# Pytest fixtures
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


@pytest.fixture
def app_state(tmp_storage):
    """Create a fresh AppState instance for testing"""
    from webui.utils.state import AppState

    state = AppState()
    yield state

    # Reset state and ensure no threads are blocked
    state._pause_event.set()
    state._stop_event.set()
    state.reset()
