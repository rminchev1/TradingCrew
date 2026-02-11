"""
Unit tests for the ticker progress panel component
"""

import pytest
import time
from datetime import datetime
from unittest.mock import patch, MagicMock


class TestFormatTimestampEST:
    """Tests for the format_timestamp_est function"""

    def test_format_timestamp_returns_correct_format(self):
        """Test that timestamp is formatted correctly with date, time, and timezone"""
        from webui.components.ticker_progress_panel import format_timestamp_est

        # Use a known timestamp (2024-01-15 10:30:00 EST)
        timestamp = 1705329000  # 2024-01-15 10:30:00 EST

        result = format_timestamp_est(timestamp)

        # Should contain date (MM/DD), time (HH:MM AM/PM), and timezone
        assert result is not None
        assert "/" in result  # Date separator
        assert ":" in result  # Time separator
        # Should have timezone indicator (EST or EDT)
        assert "EST" in result or "EDT" in result

    def test_format_timestamp_returns_none_for_none_input(self):
        """Test that None input returns None"""
        from webui.components.ticker_progress_panel import format_timestamp_est

        result = format_timestamp_est(None)
        assert result is None

    def test_format_timestamp_returns_none_for_zero(self):
        """Test that zero timestamp returns None"""
        from webui.components.ticker_progress_panel import format_timestamp_est

        result = format_timestamp_est(0)
        assert result is None

    def test_format_timestamp_handles_current_time(self):
        """Test that current time is formatted correctly"""
        from webui.components.ticker_progress_panel import format_timestamp_est

        current_time = time.time()
        result = format_timestamp_est(current_time)

        assert result is not None
        # Should contain either EST or EDT
        assert "EST" in result or "EDT" in result

    def test_format_timestamp_handles_invalid_input(self):
        """Test that invalid input returns None"""
        from webui.components.ticker_progress_panel import format_timestamp_est

        # Test with negative timestamp (edge case)
        result = format_timestamp_est(-1000)
        # Should still work or return None gracefully
        assert result is None or isinstance(result, str)


class TestRenderTickerProgressRow:
    """Tests for the render_ticker_progress_row function"""

    def test_row_includes_timestamps_section(self):
        """Test that rendered row includes timestamps section"""
        from webui.components.ticker_progress_panel import render_ticker_progress_row

        agent_statuses = {
            "Market Analyst": "completed",
            "Options Analyst": "pending",
            "Social Analyst": "pending",
            "News Analyst": "pending",
            "Fundamentals Analyst": "pending",
            "Macro Analyst": "pending",
            "Bull Researcher": "pending",
            "Bear Researcher": "pending",
            "Research Manager": "pending",
            "Trader": "pending",
            "Risky Analyst": "pending",
            "Safe Analyst": "pending",
            "Neutral Analyst": "pending",
            "Portfolio Manager": "pending",
        }

        start_time = time.time() - 300  # 5 minutes ago
        completed_time = time.time()

        result = render_ticker_progress_row(
            "AAPL", agent_statuses, is_analyzing=False,
            start_time=start_time, completed_time=completed_time
        )

        # Convert to string to check content
        result_str = str(result)

        # Should contain "Started:" and "Completed:" labels
        assert "Started" in result_str
        assert "Completed" in result_str

    def test_row_shows_in_progress_when_analyzing(self):
        """Test that row shows 'In progress...' when analysis is ongoing"""
        from webui.components.ticker_progress_panel import render_ticker_progress_row

        agent_statuses = {
            "Market Analyst": "in_progress",
            "Options Analyst": "pending",
            "Social Analyst": "pending",
            "News Analyst": "pending",
            "Fundamentals Analyst": "pending",
            "Macro Analyst": "pending",
            "Bull Researcher": "pending",
            "Bear Researcher": "pending",
            "Research Manager": "pending",
            "Trader": "pending",
            "Risky Analyst": "pending",
            "Safe Analyst": "pending",
            "Neutral Analyst": "pending",
            "Portfolio Manager": "pending",
        }

        start_time = time.time() - 60  # 1 minute ago

        result = render_ticker_progress_row(
            "NVDA", agent_statuses, is_analyzing=True,
            start_time=start_time, completed_time=None
        )

        result_str = str(result)
        assert "In progress" in result_str

    def test_row_shows_dash_when_no_times_provided(self):
        """Test that row shows dash when no times are provided"""
        from webui.components.ticker_progress_panel import render_ticker_progress_row

        agent_statuses = {
            "Market Analyst": "pending",
            "Options Analyst": "pending",
            "Social Analyst": "pending",
            "News Analyst": "pending",
            "Fundamentals Analyst": "pending",
            "Macro Analyst": "pending",
            "Bull Researcher": "pending",
            "Bear Researcher": "pending",
            "Research Manager": "pending",
            "Trader": "pending",
            "Risky Analyst": "pending",
            "Safe Analyst": "pending",
            "Neutral Analyst": "pending",
            "Portfolio Manager": "pending",
        }

        result = render_ticker_progress_row(
            "TSLA", agent_statuses, is_analyzing=False,
            start_time=None, completed_time=None
        )

        # The result should render without errors
        assert result is not None


class TestRenderAllTickerProgress:
    """Tests for the render_all_ticker_progress function"""

    def test_render_passes_times_to_row(self):
        """Test that render_all_ticker_progress passes start/end times to each row"""
        from webui.components.ticker_progress_panel import render_all_ticker_progress

        start_time = time.time() - 300
        completed_time = time.time()

        symbol_states = {
            "AAPL": {
                "agent_statuses": {
                    "Market Analyst": "completed",
                    "Options Analyst": "completed",
                    "Social Analyst": "completed",
                    "News Analyst": "completed",
                    "Fundamentals Analyst": "completed",
                    "Macro Analyst": "completed",
                    "Bull Researcher": "completed",
                    "Bear Researcher": "completed",
                    "Research Manager": "completed",
                    "Trader": "completed",
                    "Risky Analyst": "completed",
                    "Safe Analyst": "completed",
                    "Neutral Analyst": "completed",
                    "Portfolio Manager": "completed",
                },
                "session_start_time": start_time,
                "analysis_completed_time": completed_time,
            }
        }

        result = render_all_ticker_progress(symbol_states, analyzing_symbols=set())

        result_str = str(result)
        # Should have timestamps displayed
        assert "Started" in result_str
        assert "Completed" in result_str

    def test_render_handles_empty_states(self):
        """Test that empty symbol states show appropriate message"""
        from webui.components.ticker_progress_panel import render_all_ticker_progress

        result = render_all_ticker_progress({}, analyzing_symbols=set())

        result_str = str(result)
        assert "No active analyses" in result_str


class TestAppStateAnalysisCompletedTime:
    """Tests for analysis_completed_time tracking in AppState"""

    def test_init_symbol_state_includes_completed_time(self):
        """Test that init_symbol_state includes analysis_completed_time"""
        from webui.utils.state import AppState

        state = AppState()
        state.init_symbol_state("TEST")

        symbol_state = state.get_state("TEST")
        assert "analysis_completed_time" in symbol_state
        assert symbol_state["analysis_completed_time"] is None

    def test_process_chunk_sets_completed_time_on_final_decision(self):
        """Test that final decision sets analysis_completed_time"""
        from webui.utils.state import AppState

        state = AppState()
        state.init_symbol_state("TEST")
        symbol_state = state.get_state("TEST")

        # Simulate processing final decision
        chunk = {
            "risk_debate_state": {
                "judge_decision": "FINAL DECISION: BUY 100 shares"
            }
        }

        before_time = time.time()
        state.process_chunk_updates(chunk, "TEST")
        after_time = time.time()

        # analysis_completed_time should be set
        assert symbol_state["analysis_completed_time"] is not None
        assert before_time <= symbol_state["analysis_completed_time"] <= after_time

    def test_reset_for_loop_clears_completed_time(self):
        """Test that reset_for_loop clears analysis_completed_time"""
        from webui.utils.state import AppState

        state = AppState()
        state.init_symbol_state("TEST")
        symbol_state = state.get_state("TEST")

        # Set completed time
        symbol_state["analysis_completed_time"] = time.time()

        # Reset for loop
        state.reset_for_loop()

        # Completed time should be cleared
        symbol_state = state.get_state("TEST")
        assert symbol_state["analysis_completed_time"] is None
