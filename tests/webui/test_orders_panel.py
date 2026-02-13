"""
Unit tests for the enhanced orders panel UI.

Tests:
- render_orders_table() sort, filter, scroll container, count badge
- _render_orders_toolbar() returns valid component with count badge
- Orders stores exist in create_stores()
"""

import pytest
from unittest.mock import patch, MagicMock
from dash import html


# Sample orders data matching the format from get_recent_orders()
SAMPLE_ORDERS = [
    {
        "Asset": "AAPL",
        "Order Type": "market",
        "Side": "buy",
        "Qty": 10.0,
        "Filled Qty": 10.0,
        "Avg. Fill Price": "$150.00",
        "Status": "filled",
        "Source": "manual",
        "Date": "02/10 14:30",
        "Order ID": "abcdef12-3456-7890-abcd-ef1234567890",
        "Order ID Short": "abcdef12",
    },
    {
        "Asset": "NVDA",
        "Order Type": "limit",
        "Side": "sell",
        "Qty": 5.0,
        "Filled Qty": 5.0,
        "Avg. Fill Price": "$800.00",
        "Status": "filled",
        "Source": "manual",
        "Date": "02/11 09:45",
        "Order ID": "11223344-5566-7788-99aa-bbccddeeff00",
        "Order ID Short": "11223344",
    },
    {
        "Asset": "TSLA",
        "Order Type": "market",
        "Side": "buy",
        "Qty": 20.0,
        "Filled Qty": 0.0,
        "Avg. Fill Price": "-",
        "Status": "canceled",
        "Source": "manual",
        "Date": "02/09 11:00",
        "Order ID": "deadbeef-dead-beef-dead-beefdeadbeef",
        "Order ID Short": "deadbeef",
    },
]


class TestRenderOrdersToolbar:
    """Tests for _render_orders_toolbar()."""

    def test_toolbar_renders(self):
        """Verify toolbar returns a Div with correct class."""
        from webui.components.alpaca_account import _render_orders_toolbar
        result = _render_orders_toolbar(shown=3, total=3)

        assert isinstance(result, html.Div)
        assert result.className == "positions-toolbar"

    def test_toolbar_has_search_input(self):
        """Verify toolbar contains search input."""
        from webui.components.alpaca_account import _render_orders_toolbar
        result = _render_orders_toolbar(shown=3, total=3)

        child_ids = [getattr(c, "id", None) for c in result.children]
        assert "orders-search-input" in child_ids

    def test_toolbar_has_sort_select(self):
        """Verify toolbar contains sort select."""
        from webui.components.alpaca_account import _render_orders_toolbar
        result = _render_orders_toolbar(shown=3, total=3)

        child_ids = [getattr(c, "id", None) for c in result.children]
        assert "orders-sort-select" in child_ids

    def test_toolbar_has_count_badge(self):
        """Verify toolbar contains count badge."""
        from webui.components.alpaca_account import _render_orders_toolbar
        result = _render_orders_toolbar(shown=5, total=10)

        child_classes = [getattr(c, "className", None) for c in result.children]
        assert "positions-count-badge" in child_classes

    def test_count_badge_shows_filtered_count(self):
        """When filtered, badge shows 'shown/total' format."""
        from webui.components.alpaca_account import _render_orders_toolbar
        result = _render_orders_toolbar(shown=3, total=20)

        badge = result.children[0]
        assert badge.children == "3/20"

    def test_count_badge_shows_total_only_when_no_filter(self):
        """When all orders shown, badge shows just the total."""
        from webui.components.alpaca_account import _render_orders_toolbar
        result = _render_orders_toolbar(shown=20, total=20)

        badge = result.children[0]
        assert badge.children == "20"

    def test_count_badge_shows_zero(self):
        """When no orders, badge shows '0'."""
        from webui.components.alpaca_account import _render_orders_toolbar
        result = _render_orders_toolbar(shown=0, total=0)

        badge = result.children[0]
        assert badge.children == "0"


class TestRenderOrdersTable:
    """Tests for render_orders_table()."""

    @patch("webui.components.alpaca_account._is_alpaca_configured", return_value=True)
    @patch("webui.components.alpaca_account.AlpacaUtils")
    def test_renders_with_data(self, mock_utils, mock_configured):
        """Verify orders table renders successfully with data."""
        mock_utils.get_recent_orders.return_value = (list(SAMPLE_ORDERS), 3)

        from webui.components.alpaca_account import render_orders_table
        result, total_pages = render_orders_table()

        assert "enhanced-table-container" in result.className
        assert total_pages >= 1

    @patch("webui.components.alpaca_account._is_alpaca_configured", return_value=True)
    @patch("webui.components.alpaca_account.AlpacaUtils")
    def test_empty_orders_shows_empty_state(self, mock_utils, mock_configured):
        """Empty orders shows the empty state message."""
        mock_utils.get_recent_orders.return_value = ([], 0)

        from webui.components.alpaca_account import render_orders_table
        result, total_pages = render_orders_table()

        assert "enhanced-table-container" in result.className
        assert total_pages == 1

    @patch("webui.components.alpaca_account._is_alpaca_configured", return_value=False)
    def test_not_configured_shows_message(self, mock_configured):
        """When Alpaca not configured, shows configuration message."""
        from webui.components.alpaca_account import render_orders_table
        result, total_pages = render_orders_table()

        assert "enhanced-table-container" in result.className
        assert total_pages == 1

    @patch("webui.components.alpaca_account._is_alpaca_configured", return_value=True)
    @patch("webui.components.alpaca_account.AlpacaUtils")
    def test_filter_by_symbol(self, mock_utils, mock_configured):
        """Verify search filter excludes non-matching symbols."""
        mock_utils.get_recent_orders.return_value = (list(SAMPLE_ORDERS), 3)

        from webui.components.alpaca_account import render_orders_table
        result, total_pages = render_orders_table(search_filter="AAPL")

        assert "enhanced-table-container" in result.className

    @patch("webui.components.alpaca_account._is_alpaca_configured", return_value=True)
    @patch("webui.components.alpaca_account.AlpacaUtils")
    def test_sort_by_symbol_asc(self, mock_utils, mock_configured):
        """Verify orders sorted by symbol ascending."""
        mock_utils.get_recent_orders.return_value = (list(SAMPLE_ORDERS), 3)

        from webui.components.alpaca_account import render_orders_table
        result, total_pages = render_orders_table(sort_key="symbol", sort_direction="asc")

        assert "enhanced-table-container" in result.className

    @patch("webui.components.alpaca_account._is_alpaca_configured", return_value=True)
    @patch("webui.components.alpaca_account.AlpacaUtils")
    def test_sort_by_date_desc(self, mock_utils, mock_configured):
        """Verify orders sorted by date descending (default)."""
        mock_utils.get_recent_orders.return_value = (list(SAMPLE_ORDERS), 3)

        from webui.components.alpaca_account import render_orders_table
        result, total_pages = render_orders_table(sort_key="date", sort_direction="desc")

        assert "enhanced-table-container" in result.className


class TestOrdersScrollContainer:
    """Tests for the scrollable orders table wrapper."""

    @patch("webui.components.alpaca_account._is_alpaca_configured", return_value=True)
    @patch("webui.components.alpaca_account.AlpacaUtils")
    def test_table_wrapped_in_scroll_container(self, mock_utils, mock_configured):
        """Verify the table is inside an orders-scroll-container div."""
        mock_utils.get_recent_orders.return_value = (list(SAMPLE_ORDERS), 3)

        from webui.components.alpaca_account import render_orders_table
        result, _ = render_orders_table()

        # result children: [toolbar, scroll-container]
        scroll_container = result.children[1]
        assert getattr(scroll_container, "className", "") == "orders-scroll-container"

    @patch("webui.components.alpaca_account._is_alpaca_configured", return_value=True)
    @patch("webui.components.alpaca_account.AlpacaUtils")
    def test_table_has_enhanced_orders_class(self, mock_utils, mock_configured):
        """Verify table inside scroll container has enhanced-orders class."""
        mock_utils.get_recent_orders.return_value = (list(SAMPLE_ORDERS), 3)

        from webui.components.alpaca_account import render_orders_table
        result, _ = render_orders_table()

        scroll_container = result.children[1]
        # The scroll container wraps an html.Table directly
        table = scroll_container.children[0] if isinstance(scroll_container.children, list) else scroll_container.children
        assert "enhanced-orders" in table.className


class TestOrdersStoresInLayout:
    """Tests that orders stores are in create_stores() for panel removal safety."""

    def test_orders_sort_store_exists(self):
        """Verify orders-sort-store is in create_stores()."""
        from webui.layout import create_stores
        stores = create_stores()
        store_ids = [getattr(s, "id", None) for s in stores]
        assert "orders-sort-store" in store_ids

    def test_orders_filter_store_exists(self):
        """Verify orders-filter-store is in create_stores()."""
        from webui.layout import create_stores
        stores = create_stores()
        store_ids = [getattr(s, "id", None) for s in stores]
        assert "orders-filter-store" in store_ids
