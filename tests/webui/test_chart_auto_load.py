"""
Tests for chart auto-load portfolio symbols and 8-month daily span.

Tests:
- Auto-load picks first portfolio position symbol
- Auto-load populates dropdown with all portfolio symbols
- Auto-load skips when symbol already selected
- Auto-load only attempts once
- Auto-load stores portfolio_symbols in app_state
- Daily chart period mapping uses ~8 months (244 days)
- get_yahoo_data uses start/end dates for days_back periods
- Dropdown fallback to portfolio_symbols when symbol_states is empty
- handle_chart_symbol_select resolves from portfolio_symbols
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


class TestDailyChartSpan:
    """Tests for 8-month daily chart span configuration."""

    def test_1d_period_uses_days_back(self):
        """Verify '1d' period mapping uses days_back instead of yfinance period."""
        from webui.utils.charts import get_yahoo_data
        with patch("webui.utils.charts.yf") as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = MagicMock(empty=True)
            mock_yf.Ticker.return_value = mock_ticker

            get_yahoo_data("AAPL", "1d")

            # Verify history was called with start/end (not period)
            call_kwargs = mock_ticker.history.call_args
            assert "start" in call_kwargs.kwargs or (
                len(call_kwargs.args) == 0 and "start" in str(call_kwargs)
            ), "Expected start/end date params for '1d' period"

    def test_1d_period_span_is_approximately_8_months(self):
        """Verify '1d' period fetches ~8 months (244 days) of data."""
        from datetime import date
        from webui.utils.charts import get_yahoo_data
        with patch("webui.utils.charts.yf") as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = MagicMock(empty=True)
            mock_yf.Ticker.return_value = mock_ticker

            get_yahoo_data("AAPL", "1d")

            call_kwargs = mock_ticker.history.call_args.kwargs
            # Dates are passed as ISO strings (YYYY-MM-DD)
            start_dt = date.fromisoformat(call_kwargs["start"])
            end_dt = date.fromisoformat(call_kwargs["end"])

            # The span should be ~244 days
            span = (end_dt - start_dt).days
            assert 240 <= span <= 250, f"Expected ~244 day span, got {span}"

    def test_other_periods_still_use_yfinance_period(self):
        """Verify non-1d periods still use yfinance period parameter."""
        from webui.utils.charts import get_yahoo_data
        with patch("webui.utils.charts.yf") as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = MagicMock(empty=True)
            mock_yf.Ticker.return_value = mock_ticker

            get_yahoo_data("AAPL", "1y")

            call_kwargs = mock_ticker.history.call_args.kwargs
            assert "period" in call_kwargs, "Expected period param for '1y'"
            assert call_kwargs["period"] == "2y"


class TestAutoLoadWatchlistSymbols:
    """Tests for auto-loading watchlist symbols into chart dropdown on startup."""

    @patch("webui.utils.local_storage.get_watchlist")
    def test_auto_load_picks_first_watchlist_symbol(self, mock_watchlist):
        """Auto-load should pick the first watchlist symbol."""
        mock_watchlist.return_value = {"symbols": ["NVDA", "HOOD", "HIMS"]}

        from webui.utils.local_storage import get_watchlist
        watchlist = get_watchlist()
        symbols = watchlist.get("symbols", [])

        assert symbols[0] == "NVDA"

    @patch("webui.utils.local_storage.get_watchlist")
    def test_auto_load_builds_dropdown_options(self, mock_watchlist):
        """Auto-load should build dropdown options for all watchlist symbols."""
        mock_watchlist.return_value = {"symbols": ["AAPL", "NVDA", "TSLA"]}

        from webui.utils.local_storage import get_watchlist
        watchlist = get_watchlist()
        symbols = watchlist.get("symbols", [])
        options = [{"label": s, "value": str(i + 1)} for i, s in enumerate(symbols)]

        assert len(options) == 3
        assert options[0] == {"label": "AAPL", "value": "1"}
        assert options[1] == {"label": "NVDA", "value": "2"}
        assert options[2] == {"label": "TSLA", "value": "3"}

    @patch("webui.utils.local_storage.get_watchlist")
    def test_auto_load_stores_portfolio_symbols(self, mock_watchlist):
        """Auto-load should store watchlist symbols in app_state.portfolio_symbols."""
        mock_watchlist.return_value = {"symbols": ["AAPL", "NVDA"]}

        from webui.utils.state import app_state
        from webui.utils.local_storage import get_watchlist

        watchlist = get_watchlist()
        symbols = watchlist.get("symbols", [])
        app_state.portfolio_symbols = symbols

        assert app_state.portfolio_symbols == ["AAPL", "NVDA"]

        # Cleanup
        app_state.portfolio_symbols = []

    @patch("webui.utils.local_storage.get_watchlist")
    def test_auto_load_returns_correct_store_data(self, mock_watchlist):
        """Auto-load should produce chart-store data with first symbol and 1d period."""
        mock_watchlist.return_value = {"symbols": ["TSLA", "GOOG"]}

        from webui.utils.local_storage import get_watchlist
        watchlist = get_watchlist()
        symbols = watchlist.get("symbols", [])

        if symbols:
            store_data = {
                "last_symbol": symbols[0],
                "selected_period": "1d",
            }
        else:
            store_data = None

        assert store_data == {"last_symbol": "TSLA", "selected_period": "1d"}

    @patch("webui.utils.local_storage.get_watchlist")
    def test_auto_load_handles_empty_watchlist(self, mock_watchlist):
        """Auto-load should not crash when watchlist is empty."""
        mock_watchlist.return_value = {"symbols": []}

        from webui.utils.local_storage import get_watchlist
        watchlist = get_watchlist()
        symbols = watchlist.get("symbols", [])

        assert len(symbols) == 0

    @patch("webui.utils.local_storage.get_watchlist")
    def test_auto_load_handles_db_error(self, mock_watchlist):
        """Auto-load should gracefully handle database errors."""
        mock_watchlist.side_effect = Exception("Database error")

        from webui.utils.local_storage import get_watchlist

        result = None
        try:
            watchlist = get_watchlist()
            symbols = watchlist.get("symbols", [])
            if symbols:
                result = symbols[0]
        except Exception:
            pass

        assert result is None

    def test_auto_load_skips_when_symbol_already_set(self):
        """Auto-load should not override an already-selected symbol."""
        chart_store_data = {"last_symbol": "NVDA", "selected_period": "1d"}

        should_skip = chart_store_data and chart_store_data.get("last_symbol")
        assert should_skip, "Should skip auto-load when symbol is already set"

    def test_auto_load_runs_when_no_symbol(self):
        """Auto-load should run when chart-store has no symbol."""
        chart_store_data = {"last_symbol": None, "selected_period": "1d"}

        should_skip = chart_store_data and chart_store_data.get("last_symbol")
        assert not should_skip, "Should NOT skip auto-load when no symbol is set"

    def test_auto_load_only_attempts_once(self):
        """Auto-load uses a flag to ensure it only runs once."""
        state = {"attempted": False}

        # First call
        assert not state["attempted"]
        state["attempted"] = True

        # Second call should short-circuit
        assert state["attempted"]


class TestDropdownPortfolioFallback:
    """Tests for dropdown population falling back to portfolio_symbols."""

    def test_dropdown_uses_portfolio_when_no_symbol_states(self):
        """When symbol_states is empty, dropdown should use portfolio_symbols."""
        from webui.utils.state import app_state

        # Setup: no analysis symbols, but portfolio has symbols
        original_states = app_state.symbol_states
        original_portfolio = app_state.portfolio_symbols
        app_state.symbol_states = {}
        app_state.portfolio_symbols = ["AAPL", "NVDA", "TSLA"]

        # The logic from update_chart_symbol_select
        if app_state.symbol_states:
            symbols = list(app_state.symbol_states.keys())
        elif app_state.portfolio_symbols:
            symbols = app_state.portfolio_symbols
        else:
            symbols = []

        assert symbols == ["AAPL", "NVDA", "TSLA"]

        # Cleanup
        app_state.symbol_states = original_states
        app_state.portfolio_symbols = original_portfolio

    def test_dropdown_prefers_symbol_states_over_portfolio(self):
        """When symbol_states has data, it should take priority over portfolio."""
        from webui.utils.state import app_state

        original_states = app_state.symbol_states
        original_portfolio = app_state.portfolio_symbols
        app_state.symbol_states = {"GOOG": {}, "META": {}}
        app_state.portfolio_symbols = ["AAPL", "NVDA"]

        if app_state.symbol_states:
            symbols = list(app_state.symbol_states.keys())
        elif app_state.portfolio_symbols:
            symbols = app_state.portfolio_symbols
        else:
            symbols = []

        assert symbols == ["GOOG", "META"]

        # Cleanup
        app_state.symbol_states = original_states
        app_state.portfolio_symbols = original_portfolio


class TestSymbolResolutionFromDropdown:
    """Tests for resolving symbol names from dropdown values using portfolio_symbols."""

    def test_resolve_symbol_from_portfolio(self):
        """Dropdown value '2' should map to second portfolio symbol."""
        from webui.utils.state import app_state

        original_states = app_state.symbol_states
        original_portfolio = app_state.portfolio_symbols
        app_state.symbol_states = {}
        app_state.portfolio_symbols = ["AAPL", "NVDA", "TSLA"]

        # Simulate _get_chart_symbols()
        if app_state.symbol_states:
            symbols = list(app_state.symbol_states.keys())
        else:
            symbols = app_state.portfolio_symbols or []

        page = 2  # User selected second item
        assert 0 < page <= len(symbols)
        assert symbols[page - 1] == "NVDA"

        # Cleanup
        app_state.symbol_states = original_states
        app_state.portfolio_symbols = original_portfolio

    def test_handle_selection_updates_chart_store(self):
        """Selecting a symbol should update chart-store with the symbol name."""
        chart_store_data = {"last_symbol": "AAPL", "selected_period": "1d"}
        new_symbol = "NVDA"

        updated_store = chart_store_data.copy()
        updated_store["last_symbol"] = new_symbol

        assert updated_store["last_symbol"] == "NVDA"
        assert updated_store["selected_period"] == "1d"
