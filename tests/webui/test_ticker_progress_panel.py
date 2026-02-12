"""
Unit tests for the ticker progress panel component
"""

import pytest
import time
from datetime import datetime
from unittest.mock import patch, MagicMock
from dash import html
import dash_bootstrap_components as dbc

from webui.components.ticker_progress_panel import (
    render_agent_badge,
    render_ticker_progress_row,
    render_all_ticker_progress,
    calculate_progress,
    get_overall_status,
    AGENT_ABBREVIATIONS,
    ANALYST_AGENTS,
)


class TestRenderAgentBadgeIcons:
    """Tests for render_agent_badge() icon rendering."""

    def test_completed_badge_has_check_icon(self):
        """Completed badge should contain a fa-check icon."""
        badge = render_agent_badge("MA", "completed")
        inner_badge = badge.children  # dbc.Badge
        badge_content = inner_badge.children  # html.Span with [I, text]
        icon_element = badge_content.children[0]
        assert isinstance(icon_element, html.I)
        assert "fa-check" in icon_element.className

    def test_in_progress_badge_has_spinner_icon(self):
        """In-progress badge should contain an animated spinner icon."""
        badge = render_agent_badge("NA", "in_progress")
        inner_badge = badge.children
        badge_content = inner_badge.children
        icon_element = badge_content.children[0]
        assert isinstance(icon_element, html.I)
        assert "fa-spinner" in icon_element.className
        assert "fa-spin" in icon_element.className

    def test_pending_badge_has_circle_icon(self):
        """Pending badge should contain a circle icon."""
        badge = render_agent_badge("TR", "pending")
        inner_badge = badge.children
        badge_content = inner_badge.children
        icon_element = badge_content.children[0]
        assert isinstance(icon_element, html.I)
        assert "fa-circle" in icon_element.className

    def test_badge_shows_abbreviation_text(self):
        """Badge should display the agent abbreviation text."""
        badge = render_agent_badge("FA", "completed")
        inner_badge = badge.children
        badge_content = inner_badge.children
        abbrev_text = badge_content.children[1]
        assert abbrev_text == "FA"

    def test_badge_tooltip_contains_agent_name(self):
        """Badge wrapper should have a tooltip title with agent name."""
        badge = render_agent_badge("MA", "completed")
        assert "Market Analyst" in badge.title
        assert "completed" in badge.title

    def test_badge_color_matches_status(self):
        """Badge color should correspond to the status."""
        completed = render_agent_badge("MA", "completed")
        in_progress = render_agent_badge("MA", "in_progress")
        pending = render_agent_badge("MA", "pending")

        assert completed.children.color == "success"
        assert in_progress.children.color == "warning"
        assert pending.children.color == "secondary"

    def test_all_abbreviations_render_all_statuses(self):
        """Every abbreviation/status combination should render without error."""
        for abbrev in AGENT_ABBREVIATIONS:
            for status in ["completed", "in_progress", "pending"]:
                badge = render_agent_badge(abbrev, status)
                assert badge is not None
                # Verify icon element exists
                inner = badge.children.children
                assert isinstance(inner.children[0], html.I)


class TestTickerRowStatusIcons:
    """Tests for Font Awesome icons in render_ticker_progress_row()."""

    def _make_statuses(self, status="pending"):
        return {name: status for name in AGENT_ABBREVIATIONS.values()}

    def test_analyzing_ticker_shows_fa_spinner(self):
        """Analyzing tickers should show a Font Awesome spinner icon."""
        statuses = self._make_statuses("in_progress")
        row = render_ticker_progress_row("AAPL", statuses, is_analyzing=True)
        header_row = row.children[0]
        symbol_col = header_row.children[0]
        icon = symbol_col.children[1]
        assert isinstance(icon, html.I)
        assert "fa-spinner" in icon.className
        assert "fa-spin" in icon.className

    def test_completed_analyzing_ticker_shows_fa_check(self):
        """Completed analyzing tickers should show a Font Awesome check icon."""
        statuses = self._make_statuses("completed")
        row = render_ticker_progress_row("AAPL", statuses, is_analyzing=True)
        header_row = row.children[0]
        symbol_col = header_row.children[0]
        icon = symbol_col.children[1]
        assert isinstance(icon, html.I)
        assert "fa-circle-check" in icon.className

    def test_not_analyzing_has_no_icon(self):
        """Non-analyzing tickers should have no icon."""
        statuses = self._make_statuses("pending")
        row = render_ticker_progress_row("AAPL", statuses, is_analyzing=False)
        header_row = row.children[0]
        symbol_col = header_row.children[0]
        assert symbol_col.children[1] is None

    def test_icons_use_font_awesome_not_bootstrap(self):
        """Status icons should use fa-* classes, not bi-* classes."""
        for status_value in ["completed", "in_progress", "pending"]:
            statuses = self._make_statuses(status_value)
            row = render_ticker_progress_row("X", statuses, is_analyzing=True)
            header_row = row.children[0]
            symbol_col = header_row.children[0]
            icon = symbol_col.children[1]
            assert isinstance(icon, html.I)
            assert "fa-" in icon.className
            assert "bi-" not in icon.className


class TestCalculateProgressFunc:
    """Tests for calculate_progress()."""

    def test_empty_returns_zero(self):
        assert calculate_progress({}) == 0

    def test_none_returns_zero(self):
        assert calculate_progress(None) == 0

    def test_all_completed_returns_100(self):
        assert calculate_progress({"A": "completed", "B": "completed"}) == 100

    def test_all_pending_returns_0(self):
        assert calculate_progress({"A": "pending", "B": "pending"}) == 0

    def test_mixed_returns_correct_percentage(self):
        statuses = {"A": "completed", "B": "in_progress", "C": "pending", "D": "completed"}
        assert calculate_progress(statuses) == 50


class TestGetOverallStatusFunc:
    """Tests for get_overall_status()."""

    def test_empty_returns_pending(self):
        status, _, _ = get_overall_status({})
        assert status == "pending"

    def test_all_completed(self):
        status, _, color = get_overall_status({"A": "completed", "B": "completed"})
        assert status == "completed"
        assert color == "success"

    def test_any_in_progress(self):
        status, _, color = get_overall_status({"A": "completed", "B": "in_progress"})
        assert status == "in_progress"
        assert color == "warning"

    def test_all_pending(self):
        status, _, color = get_overall_status({"A": "pending", "B": "pending"})
        assert status == "pending"
        assert color == "secondary"


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


class TestErrorState:
    """Tests for the error status in progress panel components."""

    def test_error_badge_has_xmark_icon(self):
        """Error badge should contain a fa-xmark icon."""
        badge = render_agent_badge("MA", "error")
        inner_badge = badge.children  # dbc.Badge
        badge_content = inner_badge.children  # html.Span with [I, text]
        icon_element = badge_content.children[0]
        assert isinstance(icon_element, html.I)
        assert "fa-xmark" in icon_element.className

    def test_error_badge_color_is_danger(self):
        """Error badge should use the 'danger' color."""
        badge = render_agent_badge("MA", "error")
        assert badge.children.color == "danger"

    def test_error_badge_tooltip_shows_error(self):
        """Error badge tooltip should mention error status."""
        badge = render_agent_badge("MA", "error")
        assert "error" in badge.title

    def test_get_overall_status_returns_error_when_any_error(self):
        """Overall status should be 'error' when any agent has error status."""
        statuses = {"A": "completed", "B": "error", "C": "pending"}
        status, text, color = get_overall_status(statuses)
        assert status == "error"
        assert text == "Failed"
        assert color == "danger"

    def test_get_overall_status_error_takes_priority_over_in_progress(self):
        """Error status should take priority over in_progress."""
        statuses = {"A": "in_progress", "B": "error"}
        status, text, color = get_overall_status(statuses)
        assert status == "error"
        assert color == "danger"

    def test_calculate_progress_counts_only_completed(self):
        """calculate_progress should only count 'completed', not 'error'."""
        statuses = {"A": "completed", "B": "error", "C": "error", "D": "completed"}
        assert calculate_progress(statuses) == 50

    def test_render_ticker_row_with_error_status(self):
        """Ticker row with error agents should show 'Failed' status."""
        statuses = {name: "error" for name in AGENT_ABBREVIATIONS.values()}
        row = render_ticker_progress_row("FAIL", statuses, is_analyzing=True)
        result_str = str(row)
        assert "Failed" in result_str

    def test_render_ticker_row_error_icon(self):
        """Error ticker should show circle-xmark icon."""
        statuses = {name: "error" for name in AGENT_ABBREVIATIONS.values()}
        row = render_ticker_progress_row("FAIL", statuses, is_analyzing=True)
        header_row = row.children[0]
        symbol_col = header_row.children[0]
        icon = symbol_col.children[1]
        assert isinstance(icon, html.I)
        assert "fa-circle-xmark" in icon.className

    def test_render_all_shows_failed_count(self):
        """Summary header should show Failed count when errors exist."""
        symbol_states = {
            "FAIL": {
                "agent_statuses": {name: "error" for name in AGENT_ABBREVIATIONS.values()},
            },
            "OK": {
                "agent_statuses": {name: "completed" for name in AGENT_ABBREVIATIONS.values()},
            }
        }
        result = render_all_ticker_progress(symbol_states, analyzing_symbols=set())
        result_str = str(result)
        assert "Failed" in result_str

    def test_render_all_no_failed_badge_when_no_errors(self):
        """Summary header should NOT show Failed count when no errors exist."""
        symbol_states = {
            "OK": {
                "agent_statuses": {name: "completed" for name in AGENT_ABBREVIATIONS.values()},
            }
        }
        result = render_all_ticker_progress(symbol_states, analyzing_symbols=set())
        result_str = str(result)
        assert "Failed" not in result_str


class TestUpdateAgentStatusAcceptsError:
    """Tests that AppState.update_agent_status accepts 'error' status."""

    def test_update_agent_status_accepts_error(self):
        """update_agent_status should accept 'error' as a valid status."""
        from webui.utils.state import AppState

        state = AppState()
        state.init_symbol_state("TEST")
        state.update_agent_status("Market Analyst", "error", symbol="TEST")

        symbol_state = state.get_state("TEST")
        assert symbol_state["agent_statuses"]["Market Analyst"] == "error"

    def test_update_agent_status_still_rejects_invalid(self):
        """update_agent_status should still reject truly invalid statuses."""
        from webui.utils.state import AppState

        state = AppState()
        state.init_symbol_state("TEST")
        state.update_agent_status("Market Analyst", "bogus_status", symbol="TEST")

        symbol_state = state.get_state("TEST")
        # Should have been defaulted to "pending"
        assert symbol_state["agent_statuses"]["Market Analyst"] == "pending"
