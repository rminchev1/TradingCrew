"""
tests/dataflows/test_bracket_orders.py

Unit tests for bracket order functionality (stop-loss and take-profit orders).
"""

import pytest
from unittest.mock import patch, MagicMock


class TestExtractSlTpFromAnalysis:
    """Tests for extracting SL/TP levels from trader analysis text."""

    def test_extract_sl_tp_from_markdown_table(self):
        """Test extraction from standard markdown table format."""
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils

        analysis = """
        **TRADING DECISION TABLE:**
        | Aspect | Details |
        |--------|---------|
        | Entry Price | $150.00 |
        | Stop Loss | $142.50 |
        | Target 1 | $165.00 |
        | Target 2 | $180.00 |
        | Risk/Reward | 3:1 ratio |
        """

        result = AlpacaUtils.extract_sl_tp_from_analysis(analysis, entry_price=150.0, is_short=False)

        assert result["stop_loss"] == 142.50
        assert result["take_profit"] == 165.00

    def test_extract_sl_tp_without_dollar_sign(self):
        """Test extraction when prices don't have dollar signs."""
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils

        analysis = """
        | Stop Loss | 95.50 |
        | Target 1 | 110.00 |
        """

        result = AlpacaUtils.extract_sl_tp_from_analysis(analysis, entry_price=100.0, is_short=False)

        assert result["stop_loss"] == 95.50
        assert result["take_profit"] == 110.00

    def test_extract_sl_tp_with_commas(self):
        """Test extraction when prices have thousand separators."""
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils

        analysis = """
        | Stop Loss | $1,250.00 |
        | Target 1 | $1,500.00 |
        """

        result = AlpacaUtils.extract_sl_tp_from_analysis(analysis, entry_price=1300.0, is_short=False)

        assert result["stop_loss"] == 1250.00
        assert result["take_profit"] == 1500.00

    def test_validate_long_sl_above_entry_ignored(self):
        """Test that SL above entry is ignored for LONG positions."""
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils

        # SL at 160 is above entry of 150, which is invalid for LONG
        analysis = """
        | Stop Loss | $160.00 |
        | Target 1 | $170.00 |
        """

        result = AlpacaUtils.extract_sl_tp_from_analysis(analysis, entry_price=150.0, is_short=False)

        assert result["stop_loss"] is None  # Invalid, should be ignored
        assert result["take_profit"] == 170.00

    def test_validate_long_tp_below_entry_ignored(self):
        """Test that TP below entry is ignored for LONG positions."""
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils

        # TP at 140 is below entry of 150, which is invalid for LONG
        analysis = """
        | Stop Loss | $145.00 |
        | Target 1 | $140.00 |
        """

        result = AlpacaUtils.extract_sl_tp_from_analysis(analysis, entry_price=150.0, is_short=False)

        assert result["stop_loss"] == 145.00
        assert result["take_profit"] is None  # Invalid, should be ignored

    def test_validate_short_sl_below_entry_ignored(self):
        """Test that SL below entry is ignored for SHORT positions."""
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils

        # SL at 140 is below entry of 150, which is invalid for SHORT
        analysis = """
        | Stop Loss | $140.00 |
        | Target 1 | $130.00 |
        """

        result = AlpacaUtils.extract_sl_tp_from_analysis(analysis, entry_price=150.0, is_short=True)

        assert result["stop_loss"] is None  # Invalid for SHORT, should be ignored
        assert result["take_profit"] == 130.00

    def test_validate_short_tp_above_entry_ignored(self):
        """Test that TP above entry is ignored for SHORT positions."""
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils

        # TP at 160 is above entry of 150, which is invalid for SHORT
        analysis = """
        | Stop Loss | $155.00 |
        | Target 1 | $160.00 |
        """

        result = AlpacaUtils.extract_sl_tp_from_analysis(analysis, entry_price=150.0, is_short=True)

        assert result["stop_loss"] == 155.00
        assert result["take_profit"] is None  # Invalid for SHORT, should be ignored

    def test_extract_from_empty_text(self):
        """Test extraction from empty or None text."""
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils

        result_empty = AlpacaUtils.extract_sl_tp_from_analysis("", entry_price=100.0, is_short=False)
        result_none = AlpacaUtils.extract_sl_tp_from_analysis(None, entry_price=100.0, is_short=False)

        assert result_empty["stop_loss"] is None
        assert result_empty["take_profit"] is None
        assert result_none["stop_loss"] is None
        assert result_none["take_profit"] is None

    def test_extract_entry_price_from_ai(self):
        """Test extraction of AI's entry price."""
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils

        analysis = """
        | Entry Price | $155.50 |
        | Stop Loss | $148.00 |
        """

        result = AlpacaUtils.extract_sl_tp_from_analysis(analysis, entry_price=155.0, is_short=False)

        assert result["entry_price_from_ai"] == 155.50


class TestPlaceBracketOrder:
    """Tests for placing bracket orders."""

    @patch("tradingagents.dataflows.alpaca_utils.get_alpaca_trading_client")
    def test_place_bracket_order_with_sl_only(self, mock_get_client):
        """Test placing bracket order with stop-loss only."""
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils

        # Mock the trading client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_order = MagicMock()
        mock_order.id = "order123"
        mock_order.symbol = "AAPL"
        mock_order.side = "buy"
        mock_order.qty = 10
        mock_order.status = "accepted"
        mock_client.submit_order.return_value = mock_order

        result = AlpacaUtils.place_bracket_order(
            symbol="AAPL",
            side="buy",
            qty=10,
            stop_loss_price=145.00,
            take_profit_price=None
        )

        assert result["success"] is True
        assert result["order_id"] == "order123"
        assert result["order_class"] == "bracket"
        assert result["stop_loss_price"] == 145.00
        assert result["take_profit_price"] is None

    @patch("tradingagents.dataflows.alpaca_utils.get_alpaca_trading_client")
    def test_place_bracket_order_with_sl_and_tp(self, mock_get_client):
        """Test placing bracket order with both SL and TP."""
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_order = MagicMock()
        mock_order.id = "order456"
        mock_order.symbol = "NVDA"
        mock_order.side = "buy"
        mock_order.qty = 5
        mock_order.status = "accepted"
        mock_client.submit_order.return_value = mock_order

        result = AlpacaUtils.place_bracket_order(
            symbol="NVDA",
            side="buy",
            qty=5,
            stop_loss_price=850.00,
            take_profit_price=950.00
        )

        assert result["success"] is True
        assert result["stop_loss_price"] == 850.00
        assert result["take_profit_price"] == 950.00

    def test_bracket_order_fails_for_crypto(self):
        """Test that bracket orders are rejected for crypto symbols."""
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils

        result = AlpacaUtils.place_bracket_order(
            symbol="BTC/USD",
            side="buy",
            qty=1,
            stop_loss_price=95000.00
        )

        assert result["success"] is False
        assert "not supported for crypto" in result["error"]

    @patch("tradingagents.dataflows.alpaca_utils.get_alpaca_trading_client")
    def test_bracket_order_handles_api_error(self, mock_get_client):
        """Test that API errors are handled gracefully."""
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.submit_order.side_effect = Exception("Insufficient buying power")

        result = AlpacaUtils.place_bracket_order(
            symbol="AAPL",
            side="buy",
            qty=1000,
            stop_loss_price=145.00
        )

        assert result["success"] is False
        assert "Insufficient buying power" in result["error"]


class TestPlaceStopOrder:
    """Tests for placing standalone stop orders."""

    @patch("tradingagents.dataflows.alpaca_utils.get_alpaca_trading_client")
    def test_place_stop_order_stock(self, mock_get_client):
        """Test placing stop order for stocks."""
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_order = MagicMock()
        mock_order.id = "stop123"
        mock_order.symbol = "AAPL"
        mock_order.side = "sell"
        mock_order.qty = 10
        mock_order.status = "accepted"
        mock_client.submit_order.return_value = mock_order

        result = AlpacaUtils.place_stop_order(
            symbol="AAPL",
            side="sell",
            qty=10,
            stop_price=145.00
        )

        assert result["success"] is True
        assert result["stop_price"] == 145.00

    @patch("tradingagents.dataflows.alpaca_utils.get_alpaca_trading_client")
    def test_place_stop_order_crypto_uses_gtc(self, mock_get_client):
        """Test that crypto stop orders use GTC time-in-force."""
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils
        from alpaca.trading.enums import TimeInForce

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_order = MagicMock()
        mock_order.id = "stop_crypto"
        mock_order.symbol = "BTCUSD"
        mock_order.side = "sell"
        mock_order.qty = 1
        mock_order.status = "accepted"
        mock_client.submit_order.return_value = mock_order

        AlpacaUtils.place_stop_order(
            symbol="BTC/USD",
            side="sell",
            qty=1,
            stop_price=95000.00
        )

        # Verify the order request used GTC
        call_args = mock_client.submit_order.call_args
        order_request = call_args[0][0]
        assert order_request.time_in_force == TimeInForce.GTC


class TestPlaceLimitOrder:
    """Tests for placing standalone limit orders."""

    @patch("tradingagents.dataflows.alpaca_utils.get_alpaca_trading_client")
    def test_place_limit_order_stock(self, mock_get_client):
        """Test placing limit order for stocks."""
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_order = MagicMock()
        mock_order.id = "limit123"
        mock_order.symbol = "AAPL"
        mock_order.side = "sell"
        mock_order.qty = 10
        mock_order.status = "accepted"
        mock_client.submit_order.return_value = mock_order

        result = AlpacaUtils.place_limit_order(
            symbol="AAPL",
            side="sell",
            qty=10,
            limit_price=165.00
        )

        assert result["success"] is True
        assert result["limit_price"] == 165.00


class TestExecuteTradingActionWithSlTp:
    """Tests for execute_trading_action with SL/TP configuration."""

    @patch("tradingagents.dataflows.alpaca_utils.AlpacaUtils.get_latest_quote")
    @patch("tradingagents.dataflows.alpaca_utils.AlpacaUtils.place_bracket_order")
    def test_buy_with_sl_tp_uses_bracket_order(self, mock_bracket, mock_quote):
        """Test that BUY with SL/TP enabled uses bracket order for stocks."""
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils

        mock_quote.return_value = {"bid_price": 150.00, "ask_price": 150.50}
        mock_bracket.return_value = {
            "success": True,
            "order_id": "bracket123",
            "symbol": "AAPL",
            "side": "buy",
            "qty": 10,
            "order_class": "bracket",
            "stop_loss_price": 142.50,
            "take_profit_price": 165.00,
            "status": "accepted"
        }

        sl_tp_config = {
            "enable_stop_loss": True,
            "stop_loss_percentage": 5.0,
            "stop_loss_use_ai": False,
            "enable_take_profit": True,
            "take_profit_percentage": 10.0,
            "take_profit_use_ai": False,
        }

        result = AlpacaUtils.execute_trading_action(
            symbol="AAPL",
            current_position="NEUTRAL",
            signal="BUY",
            dollar_amount=1500,
            allow_shorts=False,
            sl_tp_config=sl_tp_config,
            analysis_text=""
        )

        assert result["success"] is True
        # Verify bracket order was called
        mock_bracket.assert_called_once()

    @patch("tradingagents.dataflows.alpaca_utils.AlpacaUtils.get_latest_quote")
    @patch("tradingagents.dataflows.alpaca_utils.AlpacaUtils.place_market_order")
    def test_buy_without_sl_tp_uses_market_order(self, mock_market, mock_quote):
        """Test that BUY without SL/TP uses standard market order."""
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils

        mock_quote.return_value = {"bid_price": 150.00, "ask_price": 150.50}
        mock_market.return_value = {
            "success": True,
            "order_id": "market123",
            "symbol": "AAPL",
            "side": "buy",
            "qty": 10,
            "status": "accepted"
        }

        result = AlpacaUtils.execute_trading_action(
            symbol="AAPL",
            current_position="NEUTRAL",
            signal="BUY",
            dollar_amount=1500,
            allow_shorts=False,
            sl_tp_config=None,
            analysis_text=""
        )

        assert result["success"] is True
        # Verify market order was called (not bracket)
        mock_market.assert_called_once()

    @patch("tradingagents.dataflows.alpaca_utils.AlpacaUtils.get_latest_quote")
    @patch("tradingagents.dataflows.alpaca_utils.AlpacaUtils.place_market_order")
    @patch("tradingagents.dataflows.alpaca_utils.AlpacaUtils.place_stop_order")
    @patch("tradingagents.dataflows.alpaca_utils.AlpacaUtils.place_limit_order")
    def test_crypto_buy_with_sl_tp_uses_separate_orders(
        self, mock_limit, mock_stop, mock_market, mock_quote
    ):
        """Test that crypto BUY with SL/TP uses separate orders (not bracket)."""
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils

        mock_quote.return_value = {"bid_price": 100000.00, "ask_price": 100100.00}
        mock_market.return_value = {
            "success": True,
            "order_id": "crypto_entry",
            "symbol": "BTCUSD",
            "side": "buy",
            "notional": 1500,
            "status": "accepted"
        }
        mock_stop.return_value = {"success": True, "order_id": "crypto_sl"}
        mock_limit.return_value = {"success": True, "order_id": "crypto_tp"}

        sl_tp_config = {
            "enable_stop_loss": True,
            "stop_loss_percentage": 5.0,
            "stop_loss_use_ai": False,
            "enable_take_profit": True,
            "take_profit_percentage": 10.0,
            "take_profit_use_ai": False,
        }

        result = AlpacaUtils.execute_trading_action(
            symbol="BTC/USD",
            current_position="NEUTRAL",
            signal="BUY",
            dollar_amount=1500,
            allow_shorts=False,
            sl_tp_config=sl_tp_config,
            analysis_text=""
        )

        assert result["success"] is True
        # Verify separate orders were placed
        mock_market.assert_called_once()
        mock_stop.assert_called_once()
        mock_limit.assert_called_once()

    @patch("tradingagents.dataflows.alpaca_utils.AlpacaUtils.get_latest_quote")
    @patch("tradingagents.dataflows.alpaca_utils.AlpacaUtils.place_bracket_order")
    def test_ai_sl_tp_extraction_used_when_enabled(self, mock_bracket, mock_quote):
        """Test that AI-extracted SL/TP levels are used when configured."""
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils

        mock_quote.return_value = {"bid_price": 150.00, "ask_price": 150.50}
        mock_bracket.return_value = {
            "success": True,
            "order_id": "ai_bracket",
            "symbol": "AAPL",
            "side": "buy",
            "qty": 10,
            "order_class": "bracket",
            "stop_loss_price": 142.50,
            "take_profit_price": 165.00,
            "status": "accepted"
        }

        sl_tp_config = {
            "enable_stop_loss": True,
            "stop_loss_percentage": 5.0,
            "stop_loss_use_ai": True,  # Use AI levels
            "enable_take_profit": True,
            "take_profit_percentage": 10.0,
            "take_profit_use_ai": True,  # Use AI levels
        }

        analysis_with_levels = """
        **TRADING DECISION TABLE:**
        | Aspect | Details |
        | Entry Price | $150.00 |
        | Stop Loss | $142.50 |
        | Target 1 | $165.00 |
        """

        result = AlpacaUtils.execute_trading_action(
            symbol="AAPL",
            current_position="NEUTRAL",
            signal="BUY",
            dollar_amount=1500,
            allow_shorts=False,
            sl_tp_config=sl_tp_config,
            analysis_text=analysis_with_levels
        )

        assert result["success"] is True
        # Verify bracket order was called with AI-extracted prices
        mock_bracket.assert_called_once()
        call_args = mock_bracket.call_args
        # Check the actual call - args could be positional or keyword
        # place_bracket_order(symbol, side, qty, stop_loss_price, take_profit_price)
        if call_args[1]:  # keyword args
            assert call_args[1].get("stop_loss_price") == 142.50 or call_args[0][3] == 142.50
        else:  # positional args
            assert call_args[0][3] == 142.50
            assert call_args[0][4] == 165.00


class TestSlTpSettings:
    """Tests for SL/TP settings in storage and state."""

    def test_default_settings_include_sl_tp(self):
        """Test that DEFAULT_SYSTEM_SETTINGS includes SL/TP settings."""
        from webui.utils.storage import DEFAULT_SYSTEM_SETTINGS

        assert "enable_stop_loss" in DEFAULT_SYSTEM_SETTINGS
        assert "stop_loss_percentage" in DEFAULT_SYSTEM_SETTINGS
        assert "stop_loss_use_ai" in DEFAULT_SYSTEM_SETTINGS
        assert "enable_take_profit" in DEFAULT_SYSTEM_SETTINGS
        assert "take_profit_percentage" in DEFAULT_SYSTEM_SETTINGS
        assert "take_profit_use_ai" in DEFAULT_SYSTEM_SETTINGS

        # Check defaults
        assert DEFAULT_SYSTEM_SETTINGS["enable_stop_loss"] is False
        assert DEFAULT_SYSTEM_SETTINGS["stop_loss_percentage"] == 5.0
        assert DEFAULT_SYSTEM_SETTINGS["stop_loss_use_ai"] is True
        assert DEFAULT_SYSTEM_SETTINGS["enable_take_profit"] is False
        assert DEFAULT_SYSTEM_SETTINGS["take_profit_percentage"] == 10.0
        assert DEFAULT_SYSTEM_SETTINGS["take_profit_use_ai"] is True

    def test_app_state_includes_sl_tp_settings(self):
        """Test that AppState.system_settings includes SL/TP settings."""
        from webui.utils.state import AppState

        state = AppState()

        assert "enable_stop_loss" in state.system_settings
        assert "stop_loss_percentage" in state.system_settings
        assert "stop_loss_use_ai" in state.system_settings
        assert "enable_take_profit" in state.system_settings
        assert "take_profit_percentage" in state.system_settings
        assert "take_profit_use_ai" in state.system_settings
