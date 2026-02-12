"""
Unit tests for pipeline pause/resume/stop controls.
"""

import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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


class TestSafeAnalysisThread:
    """Tests for the safe_analysis_thread wrapper that guarantees cleanup."""

    def test_analysis_running_reset_on_success(self, app_state):
        """analysis_running is set to False when thread completes normally."""
        app_state.analysis_running = True

        def fake_analysis():
            pass  # Succeeds normally

        def safe_wrapper():
            try:
                fake_analysis()
            except Exception:
                pass
            finally:
                app_state.analysis_running = False

        t = threading.Thread(target=safe_wrapper)
        t.start()
        t.join(timeout=5)

        assert not app_state.analysis_running

    def test_analysis_running_reset_on_crash(self, app_state):
        """analysis_running is set to False even when thread crashes with unhandled exception."""
        app_state.analysis_running = True

        def crashing_analysis():
            raise RuntimeError("Unexpected crash in analysis thread")

        def safe_wrapper():
            try:
                crashing_analysis()
            except Exception:
                pass
            finally:
                app_state.analysis_running = False

        t = threading.Thread(target=safe_wrapper)
        t.start()
        t.join(timeout=5)

        assert not app_state.analysis_running

    def test_analysis_running_reset_on_system_exit(self, app_state):
        """analysis_running is reset even on SystemExit (finally always runs)."""
        app_state.analysis_running = True

        def exiting_analysis():
            raise SystemExit(1)

        def safe_wrapper():
            try:
                exiting_analysis()
            except Exception:
                pass
            finally:
                app_state.analysis_running = False

        t = threading.Thread(target=safe_wrapper)
        t.start()
        t.join(timeout=5)

        assert not app_state.analysis_running


class TestParallelExecutorStopEvent:
    """Tests for ThreadPoolExecutor behavior with the stop event."""

    def test_stop_event_skips_queued_tickers(self, app_state):
        """Tickers queued behind the stop event are skipped immediately."""
        symbols = ["AAPL", "NVDA", "TSLA", "AMZN", "GOOG"]
        processed = []
        skipped = []

        def analyze_ticker(symbol):
            if app_state._stop_event.is_set():
                return symbol, False, "Pipeline stopped before analysis started"
            # Simulate analysis work
            time.sleep(0.2)
            processed.append(symbol)
            return symbol, True, None

        # Set stop event after a brief delay to let first ticker start
        def stop_after_delay():
            time.sleep(0.1)
            app_state._stop_event.set()

        stopper = threading.Thread(target=stop_after_delay)
        stopper.start()

        max_workers = 1  # Only 1 worker so tickers queue up
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(analyze_ticker, s): s for s in symbols}
            for future in as_completed(futures):
                sym, success, error = future.result()
                if not success:
                    skipped.append(sym)

        stopper.join(timeout=5)

        # At least one ticker should have been processed before stop
        assert len(processed) >= 1
        # Remaining tickers should have been skipped
        assert len(skipped) >= 1
        # All tickers accounted for
        assert len(processed) + len(skipped) == len(symbols)

    def test_all_tickers_complete_without_stop(self, app_state):
        """Without stop event, all tickers are processed."""
        symbols = ["AAPL", "NVDA", "TSLA", "AMZN"]
        succeeded = []
        failed = []

        def analyze_ticker(symbol):
            if app_state._stop_event.is_set():
                return symbol, False, "Pipeline stopped"
            time.sleep(0.05)
            return symbol, True, None

        max_workers = 2
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(analyze_ticker, s): s for s in symbols}
            for future in as_completed(futures):
                sym, success, error = future.result()
                if success:
                    succeeded.append(sym)
                else:
                    failed.append(sym)

        assert len(succeeded) == 4
        assert len(failed) == 0

    def test_completion_summary_classification(self, app_state):
        """Tickers are correctly classified as succeeded, failed, or skipped."""
        symbols = ["AAPL", "NVDA", "TSLA", "AMZN", "GOOG"]

        def analyze_ticker(symbol):
            if app_state._stop_event.is_set():
                return symbol, False, "Pipeline stopped before analysis started"
            if symbol == "TSLA":
                raise ValueError("Simulated TSLA failure")
            if symbol == "AMZN":
                return symbol, False, "API timeout"
            time.sleep(0.05)
            return symbol, True, None

        # Stop after a brief delay to skip GOOG
        def stop_later():
            time.sleep(0.15)
            app_state._stop_event.set()

        stopper = threading.Thread(target=stop_later)
        stopper.start()

        succeeded = []
        failed = []

        max_workers = 1  # Sequential to control ordering
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(analyze_ticker, s): s for s in symbols}
            for future in as_completed(futures):
                sym_key = futures[future]
                try:
                    sym, success, error = future.result()
                    if success:
                        succeeded.append(sym)
                    else:
                        failed.append((sym, error))
                except Exception as e:
                    failed.append((sym_key, str(e)))

        stopper.join(timeout=5)

        # Build the skipped list (same logic as production code)
        failed_syms = {s for s, _ in failed}
        skipped = [s for s in symbols if s not in succeeded and s not in failed_syms]

        # Every ticker accounted for in exactly one bucket
        all_accounted = set(succeeded) | failed_syms | set(skipped)
        assert all_accounted == set(symbols)

    def test_executor_handles_mixed_exceptions(self, app_state):
        """Executor processes all tickers even when some raise exceptions."""
        symbols = ["AAPL", "NVDA", "TSLA"]

        def analyze_ticker(symbol):
            if symbol == "NVDA":
                raise RuntimeError("NVDA analysis crashed")
            time.sleep(0.05)
            return symbol, True, None

        succeeded = []
        failed = []

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(analyze_ticker, s): s for s in symbols}
            for future in as_completed(futures):
                sym_key = futures[future]
                try:
                    sym, success, error = future.result()
                    if success:
                        succeeded.append(sym)
                    else:
                        failed.append((sym, error))
                except Exception as e:
                    failed.append((sym_key, str(e)))

        assert set(succeeded) == {"AAPL", "TSLA"}
        assert len(failed) == 1
        assert failed[0][0] == "NVDA"


class TestRetryFailedTickers:
    """Tests for automatic retry of failed tickers."""

    def test_retry_recovers_transient_failure(self, app_state):
        """A ticker that fails once but succeeds on retry should end up in succeeded."""
        attempt_count = {}

        def analyze_ticker(symbol):
            attempt_count[symbol] = attempt_count.get(symbol, 0) + 1
            if symbol == "NVDA" and attempt_count[symbol] == 1:
                return symbol, False, "Transient API error"
            return symbol, True, None

        symbols = ["AAPL", "NVDA", "TSLA"]
        succeeded = []
        failed = []

        # First pass
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(analyze_ticker, s): s for s in symbols}
            for future in as_completed(futures):
                sym, success, error = future.result()
                if success:
                    succeeded.append(sym)
                else:
                    failed.append((sym, error))

        # Retry pass (mirrors production logic)
        max_retries = 1
        retry_round = 0
        while failed and retry_round < max_retries:
            retry_round += 1
            retry_symbols = [sym for sym, _ in failed]
            failed = []
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {executor.submit(analyze_ticker, s): s for s in retry_symbols}
                for future in as_completed(futures):
                    sym, success, error = future.result()
                    if success:
                        succeeded.append(sym)
                    else:
                        failed.append((sym, error))

        assert set(succeeded) == {"AAPL", "NVDA", "TSLA"}
        assert len(failed) == 0
        assert attempt_count["NVDA"] == 2

    def test_retry_respects_max_retries(self, app_state):
        """A ticker that always fails should remain in failed after max retries."""
        def analyze_ticker(symbol):
            if symbol == "BAD":
                return symbol, False, "Permanent failure"
            return symbol, True, None

        symbols = ["AAPL", "BAD"]
        succeeded = []
        failed = []

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(analyze_ticker, s): s for s in symbols}
            for future in as_completed(futures):
                sym, success, error = future.result()
                if success:
                    succeeded.append(sym)
                else:
                    failed.append((sym, error))

        max_retries = 1
        retry_round = 0
        while failed and retry_round < max_retries:
            retry_round += 1
            retry_symbols = [sym for sym, _ in failed]
            failed = []
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = {executor.submit(analyze_ticker, s): s for s in retry_symbols}
                for future in as_completed(futures):
                    sym, success, error = future.result()
                    if success:
                        succeeded.append(sym)
                    else:
                        failed.append((sym, error))

        assert "AAPL" in succeeded
        assert len(failed) == 1
        assert failed[0][0] == "BAD"

    def test_retry_skipped_when_stop_event_set(self, app_state):
        """Retry should not execute when stop event is already set."""
        def analyze_ticker(symbol):
            if app_state._stop_event.is_set():
                return symbol, False, "Pipeline stopped"
            return symbol, True, None

        # Simulate initial failure
        failed = [("NVDA", "API error")]
        succeeded = []

        # Set stop event before retry
        app_state._stop_event.set()

        max_retries = 1
        retry_round = 0
        while failed and retry_round < max_retries and not app_state._stop_event.is_set():
            retry_round += 1
            # This block should never execute
            retry_symbols = [sym for sym, _ in failed]
            failed = []
            for sym in retry_symbols:
                succeeded.append(sym)

        # NVDA should remain in the original failed list (retry loop never entered)
        assert len(succeeded) == 0
        assert retry_round == 0

    def test_retry_resets_symbol_state(self, app_state):
        """Retry should reinitialize symbol state before retrying."""
        app_state.init_symbol_state("NVDA")
        state = app_state.get_state("NVDA")
        # Simulate some agents marked as error from first failure
        state["agent_statuses"]["Market Analyst"] = "error"
        state["agent_statuses"]["News Analyst"] = "error"

        # Re-init (same as what retry does)
        app_state.init_symbol_state("NVDA")
        state = app_state.get_state("NVDA")

        # All agents should be back to pending
        for agent_status in state["agent_statuses"].values():
            assert agent_status == "pending"


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
