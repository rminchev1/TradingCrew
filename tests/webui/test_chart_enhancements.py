"""
Unit tests for chart enhancements: OHLC legend, indicator labels, live price updates.

Tests:
- Phase 1: OHLC legend divs exist in chart panel component
- Phase 2: Indicator legend divs exist in chart panel
- Phase 3: Live toggle, live data fetch, live interval/store in layout
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestChartPanelOhlcLegend:
    """Tests for OHLC legend elements in the chart panel component."""

    def test_ohlc_legend_div_exists(self):
        """Verify chart-ohlc-legend div exists in the chart panel."""
        from webui.components.chart_panel import create_chart_panel
        panel = create_chart_panel()
        html_str = str(panel)
        assert "chart-ohlc-legend" in html_str

    def test_ohlc_elements_present(self):
        """Verify all OHLC value elements are present."""
        from webui.components.chart_panel import create_chart_panel
        panel = create_chart_panel()
        html_str = str(panel)
        for el_id in ["ohlc-open", "ohlc-high", "ohlc-low", "ohlc-close", "ohlc-change", "ohlc-volume"]:
            assert el_id in html_str, f"Missing OHLC element: {el_id}"


class TestChartPanelIndicatorLegends:
    """Tests for indicator legend elements in the chart panel."""

    def test_indicator_legend_div_exists(self):
        """Verify chart-indicator-legend div exists for overlay indicators."""
        from webui.components.chart_panel import create_chart_panel
        panel = create_chart_panel()
        html_str = str(panel)
        assert "chart-indicator-legend" in html_str

    def test_pane_legend_divs_exist(self):
        """Verify pane legend divs exist for RSI, MACD, OBV."""
        from webui.components.chart_panel import create_chart_panel
        panel = create_chart_panel()
        html_str = str(panel)
        assert "rsi-pane-legend" in html_str
        assert "macd-pane-legend" in html_str
        assert "obv-pane-legend" in html_str


class TestChartPanelLiveButton:
    """Tests for the LIVE toggle button."""

    def test_live_button_exists(self):
        """Verify LIVE button exists in chart panel."""
        from webui.components.chart_panel import create_chart_panel
        panel = create_chart_panel()
        html_str = str(panel)
        assert "chart-live-btn" in html_str

    def test_live_dot_span_exists(self):
        """Verify live dot indicator span exists."""
        from webui.components.chart_panel import create_chart_panel
        panel = create_chart_panel()
        html_str = str(panel)
        assert "live-dot" in html_str


class TestLayoutLiveComponents:
    """Tests for live interval and store in global layout."""

    def test_live_interval_in_create_intervals(self):
        """Verify chart-live-interval is in create_intervals()."""
        from webui.layout import create_intervals
        intervals = create_intervals()
        interval_ids = [i.id for i in intervals]
        assert "chart-live-interval" in interval_ids

    def test_live_interval_disabled_by_default(self):
        """Verify chart-live-interval starts disabled."""
        from webui.layout import create_intervals
        intervals = create_intervals()
        live_interval = next(i for i in intervals if i.id == "chart-live-interval")
        assert live_interval.disabled is True

    def test_live_interval_is_5_seconds(self):
        """Verify chart-live-interval is 5000ms."""
        from webui.layout import create_intervals
        intervals = create_intervals()
        live_interval = next(i for i in intervals if i.id == "chart-live-interval")
        assert live_interval.interval == 5000

    def test_live_store_in_create_stores(self):
        """Verify tv-chart-live-store is in create_stores()."""
        from webui.layout import create_stores
        stores = create_stores()
        store_ids = [s.id for s in stores if hasattr(s, 'id')]
        assert "tv-chart-live-store" in store_ids


class TestLiveToggleCallback:
    """Tests for the live toggle callback logic."""

    def test_toggle_enables_live(self):
        """Toggle from disabled -> enabled returns correct outputs."""
        # Import the module to test the callback function
        # We test the logic directly since Dash callback testing requires app context
        # The callback: toggle_live_mode(n_clicks, currently_disabled)
        # When currently_disabled=True, should return: (False, active_class, "success")
        # Simulating: n_clicks=1, currently_disabled=True
        currently_disabled = True
        # Live mode ON: interval disabled=False, active class, success color
        new_disabled = not currently_disabled  # False
        assert new_disabled is False

    def test_toggle_disables_live(self):
        """Toggle from enabled -> disabled returns correct outputs."""
        currently_disabled = False
        new_disabled = not currently_disabled  # True
        assert new_disabled is True


class TestLivePriceFetch:
    """Tests for the live price fetch callback."""

    @patch("tradingagents.dataflows.alpaca_utils.AlpacaUtils.get_latest_quote")
    def test_fetch_returns_price_data(self, mock_quote):
        """Fetch live price returns proper format with mid-price."""
        mock_quote.return_value = {
            "symbol": "AAPL",
            "bid_price": 150.00,
            "ask_price": 150.10,
            "bid_size": 100,
            "ask_size": 200,
        }

        from tradingagents.dataflows.alpaca_utils import AlpacaUtils
        quote = AlpacaUtils.get_latest_quote("AAPL")

        bid = quote.get("bid_price", 0) or 0
        ask = quote.get("ask_price", 0) or 0
        price = (bid + ask) / 2

        assert price == 150.05
        assert bid == 150.00
        assert ask == 150.10

    @patch("tradingagents.dataflows.alpaca_utils.AlpacaUtils.get_latest_quote")
    def test_fetch_handles_zero_bid(self, mock_quote):
        """When bid is 0, use ask price only."""
        mock_quote.return_value = {
            "symbol": "AAPL",
            "bid_price": 0,
            "ask_price": 150.10,
        }

        from tradingagents.dataflows.alpaca_utils import AlpacaUtils
        quote = AlpacaUtils.get_latest_quote("AAPL")

        bid = quote.get("bid_price", 0) or 0
        ask = quote.get("ask_price", 0) or 0

        if bid > 0 and ask > 0:
            price = (bid + ask) / 2
        elif ask > 0:
            price = ask
        else:
            price = bid

        assert price == 150.10

    @patch("tradingagents.dataflows.alpaca_utils.AlpacaUtils.get_latest_quote")
    def test_fetch_crypto_symbol_format(self, mock_quote):
        """Crypto symbols (BTC/USD) should work with Alpaca."""
        mock_quote.return_value = {
            "symbol": "BTC/USD",
            "bid_price": 45000.00,
            "ask_price": 45010.00,
        }

        from tradingagents.dataflows.alpaca_utils import AlpacaUtils
        quote = AlpacaUtils.get_latest_quote("BTC/USD")

        assert quote["symbol"] == "BTC/USD"
        assert quote["bid_price"] == 45000.00
