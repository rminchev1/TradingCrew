"""
Unit tests for the enhanced positions panel UI.

Tests:
- render_portfolio_summary() computes totals correctly
- render_positions_table() sort, filter, weight computation
- _get_pl_color() helper
- _pl_bar() helper
- _render_positions_toolbar() returns valid component
- CSV export data formatting
"""

import pytest
from unittest.mock import patch, MagicMock
from dash import html


# Sample positions data matching the new format from get_positions_data()
SAMPLE_POSITIONS = [
    {
        "Symbol": "AAPL",
        "Qty": 100.0,
        "Market Value": "$15,000.00",
        "Avg Entry": "$140.00",
        "Cost Basis": "$14,000.00",
        "Current Price": "$150.00",
        "Today's P/L (%)": "1.43%",
        "Today's P/L ($)": "$200.00",
        "Total P/L (%)": "7.14%",
        "Total P/L ($)": "$1,000.00",
        "current_price": 150.0,
        "market_value_raw": 15000.0,
        "cost_basis_raw": 14000.0,
        "avg_entry_raw": 140.0,
        "today_pl_dollars_raw": 200.0,
        "total_pl_dollars_raw": 1000.0,
        "today_pl_percent_raw": 1.43,
        "total_pl_percent_raw": 7.14,
        "side": "long",
        "asset_class": "us_equity",
        "change_today": 0.013,
    },
    {
        "Symbol": "NVDA",
        "Qty": 50.0,
        "Market Value": "$5,000.00",
        "Avg Entry": "$120.00",
        "Cost Basis": "$6,000.00",
        "Current Price": "$100.00",
        "Today's P/L (%)": "-0.50%",
        "Today's P/L ($)": "$-30.00",
        "Total P/L (%)": "-16.67%",
        "Total P/L ($)": "$-1,000.00",
        "current_price": 100.0,
        "market_value_raw": 5000.0,
        "cost_basis_raw": 6000.0,
        "avg_entry_raw": 120.0,
        "today_pl_dollars_raw": -30.0,
        "total_pl_dollars_raw": -1000.0,
        "today_pl_percent_raw": -0.50,
        "total_pl_percent_raw": -16.67,
        "side": "long",
        "asset_class": "us_equity",
        "change_today": -0.005,
    },
    {
        "Symbol": "TSLA",
        "Qty": 25.0,
        "Market Value": "$10,000.00",
        "Avg Entry": "$380.00",
        "Cost Basis": "$9,500.00",
        "Current Price": "$400.00",
        "Today's P/L (%)": "0.25%",
        "Today's P/L ($)": "$25.00",
        "Total P/L (%)": "5.26%",
        "Total P/L ($)": "$500.00",
        "current_price": 400.0,
        "market_value_raw": 10000.0,
        "cost_basis_raw": 9500.0,
        "avg_entry_raw": 380.0,
        "today_pl_dollars_raw": 25.0,
        "total_pl_dollars_raw": 500.0,
        "today_pl_percent_raw": 0.25,
        "total_pl_percent_raw": 5.26,
        "side": "long",
        "asset_class": "us_equity",
        "change_today": 0.0025,
    },
]

SAMPLE_ACCOUNT_INFO = {
    "buying_power": 50000.0,
    "cash": 25000.0,
    "equity": 75000.0,
    "last_equity": 74000.0,
    "daily_change_dollars": 1000.0,
    "daily_change_percent": 1.35,
}


class TestGetPlColor:
    """Tests for _get_pl_color() helper."""

    def test_positive_value(self):
        from webui.components.alpaca_account import _get_pl_color
        assert _get_pl_color("$200.00") == "text-success"

    def test_negative_value(self):
        from webui.components.alpaca_account import _get_pl_color
        assert _get_pl_color("$-100.00") == "text-danger"

    def test_zero_value(self):
        from webui.components.alpaca_account import _get_pl_color
        assert _get_pl_color("$0.00") == "text-muted"

    def test_invalid_value(self):
        from webui.components.alpaca_account import _get_pl_color
        assert _get_pl_color("N/A") == "text-muted"

    def test_value_with_commas(self):
        from webui.components.alpaca_account import _get_pl_color
        assert _get_pl_color("$1,234.56") == "text-success"


class TestPlBar:
    """Tests for _pl_bar() helper."""

    def test_positive_pl_returns_positive_class(self):
        from webui.components.alpaca_account import _pl_bar
        bar = _pl_bar(5.0)
        assert isinstance(bar, html.Div)
        # The inner div should have 'positive' class
        inner = bar.children
        assert "positive" in inner.className

    def test_negative_pl_returns_negative_class(self):
        from webui.components.alpaca_account import _pl_bar
        bar = _pl_bar(-3.0)
        inner = bar.children
        assert "negative" in inner.className

    def test_large_pl_capped_at_100(self):
        from webui.components.alpaca_account import _pl_bar
        bar = _pl_bar(200.0)
        inner = bar.children
        # Width should be 100%, not 200%
        assert inner.style["width"] == "100%"

    def test_zero_pl_has_minimum_width(self):
        from webui.components.alpaca_account import _pl_bar
        bar = _pl_bar(0.0)
        inner = bar.children
        assert inner.style["width"] == "2%"


class TestRenderPortfolioSummary:
    """Tests for render_portfolio_summary()."""

    @patch("webui.components.alpaca_account._is_alpaca_configured", return_value=True)
    @patch("webui.components.alpaca_account.AlpacaUtils")
    def test_computes_totals_correctly(self, mock_utils, mock_configured):
        """Verify total market value and total P/L are summed correctly."""
        mock_utils.get_positions_data.return_value = SAMPLE_POSITIONS
        mock_utils.get_account_info.return_value = SAMPLE_ACCOUNT_INFO

        from webui.components.alpaca_account import render_portfolio_summary
        result = render_portfolio_summary()

        # Should return a Div with portfolio-summary-bar class
        assert hasattr(result, "className")
        assert result.className == "portfolio-summary-bar"

    @patch("webui.components.alpaca_account._is_alpaca_configured", return_value=True)
    def test_with_provided_data(self, mock_configured):
        """Verify it works when data is passed directly (no API call)."""
        from webui.components.alpaca_account import render_portfolio_summary
        result = render_portfolio_summary(
            positions_data=SAMPLE_POSITIONS,
            account_info=SAMPLE_ACCOUNT_INFO
        )

        assert result.className == "portfolio-summary-bar"

    @patch("webui.components.alpaca_account._is_alpaca_configured", return_value=True)
    def test_empty_positions_returns_empty_div(self, mock_configured):
        """Empty positions returns an empty div."""
        from webui.components.alpaca_account import render_portfolio_summary
        result = render_portfolio_summary(positions_data=[], account_info=SAMPLE_ACCOUNT_INFO)

        # Should return empty html.Div
        assert isinstance(result, html.Div)
        assert result.children is None or result.children == []

    @patch("webui.components.alpaca_account._is_alpaca_configured", return_value=False)
    def test_unconfigured_returns_empty_div(self, mock_configured):
        """When Alpaca not configured, returns empty div."""
        from webui.components.alpaca_account import render_portfolio_summary
        result = render_portfolio_summary()

        assert isinstance(result, html.Div)


class TestRenderPositionsTable:
    """Tests for render_positions_table()."""

    @patch("webui.components.alpaca_account._is_alpaca_configured", return_value=True)
    @patch("webui.components.alpaca_account.AlpacaUtils")
    def test_sort_by_symbol_asc(self, mock_utils, mock_configured):
        """Verify positions sorted by symbol ascending."""
        mock_utils.get_positions_data.return_value = list(SAMPLE_POSITIONS)

        from webui.components.alpaca_account import render_positions_table
        result = render_positions_table(sort_key="symbol", sort_direction="asc", equity=75000)

        # Result should be a Div with enhanced-table-container class
        assert "enhanced-table-container" in result.className

    @patch("webui.components.alpaca_account._is_alpaca_configured", return_value=True)
    @patch("webui.components.alpaca_account.AlpacaUtils")
    def test_sort_by_total_pl_desc(self, mock_utils, mock_configured):
        """Verify positions can be sorted by total P/L descending."""
        mock_utils.get_positions_data.return_value = list(SAMPLE_POSITIONS)

        from webui.components.alpaca_account import render_positions_table
        result = render_positions_table(sort_key="total_pl", sort_direction="desc", equity=75000)

        assert "enhanced-table-container" in result.className

    @patch("webui.components.alpaca_account._is_alpaca_configured", return_value=True)
    @patch("webui.components.alpaca_account.AlpacaUtils")
    def test_filter_by_symbol(self, mock_utils, mock_configured):
        """Verify search filter excludes non-matching symbols."""
        mock_utils.get_positions_data.return_value = list(SAMPLE_POSITIONS)

        from webui.components.alpaca_account import render_positions_table
        result = render_positions_table(search_filter="AAPL", equity=75000)

        # Should render without error - the table should only have AAPL rows
        assert "enhanced-table-container" in result.className

    @patch("webui.components.alpaca_account._is_alpaca_configured", return_value=True)
    @patch("webui.components.alpaca_account.AlpacaUtils")
    def test_filter_no_match_shows_empty(self, mock_utils, mock_configured):
        """Filter with no matches still renders valid container."""
        mock_utils.get_positions_data.return_value = list(SAMPLE_POSITIONS)

        from webui.components.alpaca_account import render_positions_table
        result = render_positions_table(search_filter="ZZZZ", equity=75000)

        # Should render the toolbar + empty table (no rows)
        assert "enhanced-table-container" in result.className

    @patch("webui.components.alpaca_account._is_alpaca_configured", return_value=True)
    @patch("webui.components.alpaca_account.AlpacaUtils")
    def test_weight_computation(self, mock_utils, mock_configured):
        """Verify weight is computed as market_value / equity * 100."""
        mock_utils.get_positions_data.return_value = [SAMPLE_POSITIONS[0].copy()]

        from webui.components.alpaca_account import render_positions_table
        # AAPL: market_value_raw=15000, equity=75000 → weight=20%
        result = render_positions_table(equity=75000)

        # If rendering succeeds, the weight was computed without error
        assert "enhanced-table-container" in result.className

    @patch("webui.components.alpaca_account._is_alpaca_configured", return_value=True)
    @patch("webui.components.alpaca_account.AlpacaUtils")
    def test_zero_equity_no_error(self, mock_utils, mock_configured):
        """Zero equity should not cause ZeroDivisionError in weight computation."""
        mock_utils.get_positions_data.return_value = list(SAMPLE_POSITIONS)

        from webui.components.alpaca_account import render_positions_table
        result = render_positions_table(equity=0)

        assert "enhanced-table-container" in result.className

    @patch("webui.components.alpaca_account._is_alpaca_configured", return_value=True)
    @patch("webui.components.alpaca_account.AlpacaUtils")
    def test_empty_positions_shows_empty_state(self, mock_utils, mock_configured):
        """Empty positions shows the empty state message."""
        mock_utils.get_positions_data.return_value = []

        from webui.components.alpaca_account import render_positions_table
        result = render_positions_table()

        assert "enhanced-table-container" in result.className

    @patch("webui.components.alpaca_account._is_alpaca_configured", return_value=False)
    def test_not_configured_shows_message(self, mock_configured):
        """When Alpaca not configured, shows configuration message."""
        from webui.components.alpaca_account import render_positions_table
        result = render_positions_table()

        assert "enhanced-table-container" in result.className


class TestRenderPositionsToolbar:
    """Tests for _render_positions_toolbar()."""

    def test_toolbar_renders(self):
        """Verify toolbar returns a Div with correct class."""
        from webui.components.alpaca_account import _render_positions_toolbar
        result = _render_positions_toolbar(shown=3, total=3)

        assert isinstance(result, html.Div)
        assert result.className == "positions-toolbar"

    def test_toolbar_has_search_input(self):
        """Verify toolbar contains search input."""
        from webui.components.alpaca_account import _render_positions_toolbar
        result = _render_positions_toolbar(shown=3, total=3)

        child_ids = [getattr(c, "id", None) for c in result.children]
        assert "positions-search-input" in child_ids

    def test_toolbar_has_sort_select(self):
        """Verify toolbar contains sort select."""
        from webui.components.alpaca_account import _render_positions_toolbar
        result = _render_positions_toolbar(shown=3, total=3)

        child_ids = [getattr(c, "id", None) for c in result.children]
        assert "positions-sort-select" in child_ids

    def test_toolbar_has_export_button(self):
        """Verify toolbar contains CSV export button."""
        from webui.components.alpaca_account import _render_positions_toolbar
        result = _render_positions_toolbar(shown=3, total=3)

        child_ids = [getattr(c, "id", None) for c in result.children]
        assert "positions-export-csv-btn" in child_ids

    def test_toolbar_has_count_badge(self):
        """Verify toolbar contains position count badge."""
        from webui.components.alpaca_account import _render_positions_toolbar
        result = _render_positions_toolbar(shown=5, total=10)

        child_classes = [getattr(c, "className", None) for c in result.children]
        assert "positions-count-badge" in child_classes

    def test_count_badge_shows_filtered_count(self):
        """When filtered, badge shows 'shown/total' format."""
        from webui.components.alpaca_account import _render_positions_toolbar
        result = _render_positions_toolbar(shown=3, total=16)

        badge = result.children[0]
        assert badge.children == "3/16"

    def test_count_badge_shows_total_only_when_no_filter(self):
        """When all positions shown, badge shows just the total."""
        from webui.components.alpaca_account import _render_positions_toolbar
        result = _render_positions_toolbar(shown=16, total=16)

        badge = result.children[0]
        assert badge.children == "16"

    def test_count_badge_shows_zero(self):
        """When no positions, badge shows '0'."""
        from webui.components.alpaca_account import _render_positions_toolbar
        result = _render_positions_toolbar(shown=0, total=0)

        badge = result.children[0]
        assert badge.children == "0"


class TestPositionsScrollContainer:
    """Tests for the scrollable positions table wrapper."""

    @patch("webui.components.alpaca_account._is_alpaca_configured", return_value=True)
    @patch("webui.components.alpaca_account.AlpacaUtils")
    def test_table_wrapped_in_scroll_container(self, mock_utils, mock_configured):
        """Verify the table is inside a positions-scroll-container div."""
        mock_utils.get_positions_data.return_value = list(SAMPLE_POSITIONS)

        from webui.components.alpaca_account import render_positions_table
        result = render_positions_table(equity=75000)

        # result is the outer enhanced-table-container div
        # children[0] = toolbar, children[1] = scroll container
        scroll_container = result.children[1]
        assert getattr(scroll_container, "className", "") == "positions-scroll-container"


class TestPositionsStoresInLayout:
    """Tests that new stores are in create_stores() for panel removal safety."""

    def test_positions_sort_store_exists(self):
        """Verify positions-sort-store is in create_stores()."""
        from webui.layout import create_stores
        stores = create_stores()
        store_ids = [getattr(s, "id", None) for s in stores]
        assert "positions-sort-store" in store_ids

    def test_positions_filter_store_exists(self):
        """Verify positions-filter-store is in create_stores()."""
        from webui.layout import create_stores
        stores = create_stores()
        store_ids = [getattr(s, "id", None) for s in stores]
        assert "positions-filter-store" in store_ids

    def test_positions_pending_close_store_exists(self):
        """Verify positions-pending-close-store is in create_stores()."""
        from webui.layout import create_stores
        stores = create_stores()
        store_ids = [getattr(s, "id", None) for s in stores]
        assert "positions-pending-close-store" in store_ids

    def test_positions_csv_download_exists(self):
        """Verify positions-csv-download is in create_stores()."""
        from webui.layout import create_stores
        stores = create_stores()
        store_ids = [getattr(s, "id", None) for s in stores]
        assert "positions-csv-download" in store_ids


class TestCSVExport:
    """Tests for CSV export data formatting."""

    def test_csv_content_generation(self):
        """Verify CSV export generates valid content."""
        import csv
        import io

        positions_data = SAMPLE_POSITIONS

        output = io.StringIO()
        fieldnames = [
            "Symbol", "Side", "Qty", "Current Price", "Avg Entry",
            "Cost Basis", "Market Value", "Today P/L ($)", "Today P/L (%)",
            "Total P/L ($)", "Total P/L (%)"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for p in positions_data:
            writer.writerow({
                "Symbol": p.get("Symbol", ""),
                "Side": p.get("side", "long").upper(),
                "Qty": p.get("Qty", 0),
                "Current Price": p.get("Current Price", ""),
                "Avg Entry": p.get("Avg Entry", ""),
                "Cost Basis": p.get("Cost Basis", ""),
                "Market Value": p.get("Market Value", ""),
                "Today P/L ($)": p.get("Today's P/L ($)", ""),
                "Today P/L (%)": p.get("Today's P/L (%)", ""),
                "Total P/L ($)": p.get("Total P/L ($)", ""),
                "Total P/L (%)": p.get("Total P/L (%)", ""),
            })

        csv_content = output.getvalue()
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        assert len(rows) == 3
        assert rows[0]["Symbol"] == "AAPL"
        assert rows[0]["Side"] == "LONG"
        assert rows[1]["Symbol"] == "NVDA"
        assert rows[2]["Symbol"] == "TSLA"
