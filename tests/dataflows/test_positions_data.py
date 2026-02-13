"""
Unit tests for positions data layer changes in alpaca_utils.py.

Tests:
- get_positions_data() returns all required fields including new raw values
- get_account_info() returns equity and last_equity fields
- Edge cases: zero equity, empty positions, zero cost basis
"""

import pytest
from unittest.mock import patch, MagicMock


def _make_mock_position(**overrides):
    """Create a mock Alpaca Position object with sensible defaults."""
    defaults = {
        "symbol": "AAPL",
        "qty": "100",
        "current_price": "150.00",
        "avg_entry_price": "140.00",
        "market_value": "15000.00",
        "unrealized_intraday_pl": "200.00",
        "unrealized_pl": "1000.00",
        "side": "long",
        "asset_class": "us_equity",
        "change_today": "0.013",
    }
    defaults.update(overrides)
    pos = MagicMock()
    for key, val in defaults.items():
        setattr(pos, key, val)
    return pos


def _make_mock_account(**overrides):
    """Create a mock Alpaca Account object."""
    defaults = {
        "buying_power": "50000.00",
        "cash": "25000.00",
        "equity": "75000.00",
        "last_equity": "74000.00",
    }
    defaults.update(overrides)
    account = MagicMock()
    for key, val in defaults.items():
        setattr(account, key, val)
    return account


class TestGetPositionsData:
    """Tests for AlpacaUtils.get_positions_data()."""

    @patch("tradingagents.dataflows.alpaca_utils.get_alpaca_trading_client")
    def test_returns_raw_numeric_fields(self, mock_client_fn):
        """Verify raw numeric fields are present for sorting/computation."""
        mock_client = MagicMock()
        mock_client.get_all_positions.return_value = [_make_mock_position()]
        mock_client_fn.return_value = mock_client

        from tradingagents.dataflows.alpaca_utils import AlpacaUtils
        result = AlpacaUtils.get_positions_data()

        assert len(result) == 1
        pos = result[0]

        # Raw numeric fields
        assert pos["current_price"] == 150.0
        assert pos["market_value_raw"] == 15000.0
        assert pos["cost_basis_raw"] == 14000.0  # 140 * 100
        assert pos["avg_entry_raw"] == 140.0
        assert isinstance(pos["today_pl_dollars_raw"], float)
        assert isinstance(pos["total_pl_dollars_raw"], float)
        assert isinstance(pos["today_pl_percent_raw"], float)
        assert isinstance(pos["total_pl_percent_raw"], float)

    @patch("tradingagents.dataflows.alpaca_utils.get_alpaca_trading_client")
    def test_returns_side_and_asset_class(self, mock_client_fn):
        """Verify side and asset_class fields are included."""
        mock_client = MagicMock()
        mock_client.get_all_positions.return_value = [_make_mock_position(side="long", asset_class="us_equity")]
        mock_client_fn.return_value = mock_client

        from tradingagents.dataflows.alpaca_utils import AlpacaUtils
        result = AlpacaUtils.get_positions_data()

        pos = result[0]
        assert pos["side"] == "long"
        assert pos["asset_class"] == "us_equity"

    @patch("tradingagents.dataflows.alpaca_utils.get_alpaca_trading_client")
    def test_returns_change_today(self, mock_client_fn):
        """Verify change_today is a float."""
        mock_client = MagicMock()
        mock_client.get_all_positions.return_value = [_make_mock_position(change_today="0.025")]
        mock_client_fn.return_value = mock_client

        from tradingagents.dataflows.alpaca_utils import AlpacaUtils
        result = AlpacaUtils.get_positions_data()

        assert result[0]["change_today"] == 0.025

    @patch("tradingagents.dataflows.alpaca_utils.get_alpaca_trading_client")
    def test_returns_formatted_display_fields(self, mock_client_fn):
        """Verify formatted string fields remain for backward compatibility."""
        mock_client = MagicMock()
        mock_client.get_all_positions.return_value = [_make_mock_position()]
        mock_client_fn.return_value = mock_client

        from tradingagents.dataflows.alpaca_utils import AlpacaUtils
        result = AlpacaUtils.get_positions_data()

        pos = result[0]
        assert pos["Symbol"] == "AAPL"
        assert "$" in pos["Market Value"]
        assert "$" in pos["Avg Entry"]
        assert "$" in pos["Cost Basis"]
        assert "$" in pos["Current Price"]
        assert "%" in pos["Today's P/L (%)"]
        assert "%" in pos["Total P/L (%)"]

    @patch("tradingagents.dataflows.alpaca_utils.get_alpaca_trading_client")
    def test_empty_positions_returns_empty_list(self, mock_client_fn):
        """Empty portfolio returns empty list."""
        mock_client = MagicMock()
        mock_client.get_all_positions.return_value = []
        mock_client_fn.return_value = mock_client

        from tradingagents.dataflows.alpaca_utils import AlpacaUtils
        result = AlpacaUtils.get_positions_data()
        assert result == []

    @patch("tradingagents.dataflows.alpaca_utils.get_alpaca_trading_client")
    def test_zero_cost_basis_no_division_error(self, mock_client_fn):
        """Zero cost basis should not cause ZeroDivisionError."""
        mock_client = MagicMock()
        mock_client.get_all_positions.return_value = [
            _make_mock_position(avg_entry_price="0", qty="0", market_value="0",
                                unrealized_intraday_pl="0", unrealized_pl="0")
        ]
        mock_client_fn.return_value = mock_client

        from tradingagents.dataflows.alpaca_utils import AlpacaUtils
        result = AlpacaUtils.get_positions_data()

        assert len(result) == 1
        assert result[0]["today_pl_percent_raw"] == 0
        assert result[0]["total_pl_percent_raw"] == 0

    @patch("tradingagents.dataflows.alpaca_utils.get_alpaca_trading_client")
    def test_options_positions_filtered_out(self, mock_client_fn):
        """Options contracts should be excluded from stock positions."""
        stock_pos = _make_mock_position(symbol="AAPL")
        # Options symbol format: e.g. AAPL230120C00150000
        option_pos = _make_mock_position(symbol="AAPL230120C00150000")

        mock_client = MagicMock()
        mock_client.get_all_positions.return_value = [stock_pos, option_pos]
        mock_client_fn.return_value = mock_client

        from tradingagents.dataflows.alpaca_utils import AlpacaUtils
        result = AlpacaUtils.get_positions_data()

        symbols = [p["Symbol"] for p in result]
        assert "AAPL" in symbols
        assert "AAPL230120C00150000" not in symbols


class TestGetAccountInfo:
    """Tests for AlpacaUtils.get_account_info()."""

    @patch("tradingagents.dataflows.alpaca_utils.get_alpaca_trading_client")
    def test_returns_equity_fields(self, mock_client_fn):
        """Verify equity and last_equity are in the returned dict."""
        mock_client = MagicMock()
        mock_client.get_account.return_value = _make_mock_account()
        mock_client_fn.return_value = mock_client

        from tradingagents.dataflows.alpaca_utils import AlpacaUtils
        result = AlpacaUtils.get_account_info()

        assert "equity" in result
        assert "last_equity" in result
        assert result["equity"] == 75000.0
        assert result["last_equity"] == 74000.0

    @patch("tradingagents.dataflows.alpaca_utils.get_alpaca_trading_client")
    def test_daily_change_calculated(self, mock_client_fn):
        """Verify daily change is correctly computed from equity."""
        mock_client = MagicMock()
        mock_client.get_account.return_value = _make_mock_account(
            equity="75000.00", last_equity="74000.00"
        )
        mock_client_fn.return_value = mock_client

        from tradingagents.dataflows.alpaca_utils import AlpacaUtils
        result = AlpacaUtils.get_account_info()

        assert result["daily_change_dollars"] == pytest.approx(1000.0)
        assert result["daily_change_percent"] == pytest.approx(1000.0 / 74000.0 * 100)

    @patch("tradingagents.dataflows.alpaca_utils.get_alpaca_trading_client")
    def test_fallback_on_error(self, mock_client_fn):
        """On API error, returns dict with all keys set to 0."""
        mock_client = MagicMock()
        mock_client.get_account.side_effect = Exception("API Error")
        mock_client_fn.return_value = mock_client

        from tradingagents.dataflows.alpaca_utils import AlpacaUtils
        result = AlpacaUtils.get_account_info()

        assert result["equity"] == 0
        assert result["last_equity"] == 0
        assert result["buying_power"] == 0
        assert result["cash"] == 0

    @patch("tradingagents.dataflows.alpaca_utils.get_alpaca_trading_client")
    def test_zero_last_equity_no_division_error(self, mock_client_fn):
        """Zero last_equity should not cause ZeroDivisionError."""
        mock_client = MagicMock()
        mock_client.get_account.return_value = _make_mock_account(
            equity="0", last_equity="0"
        )
        mock_client_fn.return_value = mock_client

        from tradingagents.dataflows.alpaca_utils import AlpacaUtils
        result = AlpacaUtils.get_account_info()

        assert result["daily_change_percent"] == 0
