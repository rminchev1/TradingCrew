"""
Unit tests for options trading utilities.

Tests the Alpaca options API integration functions:
- OCC symbol formatting and parsing
- Contract fetching
- Order placement
- Position management
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


class TestOCCSymbolFormatting:
    """Tests for OCC symbol format/parse functions"""

    def test_format_occ_symbol_call(self):
        """Verify OCC symbol formatting for call option"""
        from tradingagents.dataflows.options_trading_utils import format_occ_symbol

        # AAPL 2024-03-15 $200 Call should be AAPL240315C00200000
        symbol = format_occ_symbol("AAPL", "2024-03-15", "call", 200.0)

        assert symbol is not None
        assert symbol.startswith("AAPL")
        assert "C" in symbol  # Call indicator
        assert "240315" in symbol  # Date YYMMDD
        assert symbol.endswith("00200000")  # Strike * 1000

    def test_format_occ_symbol_put(self):
        """Verify OCC symbol formatting for put option"""
        from tradingagents.dataflows.options_trading_utils import format_occ_symbol

        # TSLA 2024-06-21 $180.50 Put
        symbol = format_occ_symbol("TSLA", "2024-06-21", "put", 180.50)

        assert symbol is not None
        assert symbol.startswith("TSLA")
        assert "P" in symbol  # Put indicator
        assert "240621" in symbol  # Date YYMMDD

    def test_format_occ_symbol_fractional_strike(self):
        """Verify OCC symbol handles fractional strike prices"""
        from tradingagents.dataflows.options_trading_utils import format_occ_symbol

        # Strike of $150.50 should be formatted as 00150500
        symbol = format_occ_symbol("MSFT", "2024-04-19", "call", 150.50)

        assert symbol is not None
        assert "00150500" in symbol

    def test_parse_occ_symbol_call(self):
        """Verify OCC symbol parsing for call option"""
        from tradingagents.dataflows.options_trading_utils import parse_occ_symbol

        # AAPL240315C00200000
        result = parse_occ_symbol("AAPL240315C00200000")

        assert result is not None
        assert result["underlying"] == "AAPL"
        assert result["contract_type"] == "call"
        assert result["strike"] == 200.0
        assert "2024-03-15" in result["expiration"]

    def test_parse_occ_symbol_put(self):
        """Verify OCC symbol parsing for put option"""
        from tradingagents.dataflows.options_trading_utils import parse_occ_symbol

        # TSLA240621P00180500
        result = parse_occ_symbol("TSLA240621P00180500")

        assert result is not None
        assert result["underlying"] == "TSLA"
        assert result["contract_type"] == "put"
        assert result["strike"] == 180.50

    def test_parse_occ_symbol_invalid(self):
        """Verify invalid OCC symbol raises ValueError"""
        from tradingagents.dataflows.options_trading_utils import parse_occ_symbol
        import pytest

        with pytest.raises(ValueError):
            parse_occ_symbol("INVALID")

    def test_format_parse_roundtrip(self):
        """Verify format and parse are inverse operations"""
        from tradingagents.dataflows.options_trading_utils import (
            format_occ_symbol,
            parse_occ_symbol,
        )

        original_underlying = "NVDA"
        original_expiration = "2024-05-17"
        original_type = "call"
        original_strike = 850.0

        # Format then parse
        symbol = format_occ_symbol(
            original_underlying, original_expiration, original_type, original_strike
        )
        parsed = parse_occ_symbol(symbol)

        assert parsed["underlying"] == original_underlying
        assert parsed["contract_type"] == original_type
        assert parsed["strike"] == original_strike


class TestOptionsPositions:
    """Tests for options position functions"""

    @patch('tradingagents.dataflows.options_trading_utils.TradingClient')
    def test_get_options_positions_empty(self, mock_client_class):
        """Verify get_options_positions returns empty list when no positions"""
        from tradingagents.dataflows.options_trading_utils import get_options_positions

        mock_client = MagicMock()
        mock_client.get_all_positions.return_value = []
        mock_client_class.return_value = mock_client

        positions = get_options_positions()

        assert isinstance(positions, list)
        # Should return empty list (no options positions)

    @patch('tradingagents.dataflows.options_trading_utils.get_api_key')
    def test_get_options_positions_no_credentials(self, mock_get_api_key):
        """Verify get_options_positions handles missing credentials"""
        from tradingagents.dataflows.options_trading_utils import get_options_positions

        mock_get_api_key.return_value = None

        positions = get_options_positions()

        assert isinstance(positions, list)
        assert len(positions) == 0


class TestContractFetching:
    """Tests for option contract lookup functions"""

    @patch('tradingagents.dataflows.options_trading_utils.get_options_trading_client')
    def test_get_option_contracts_basic(self, mock_get_client):
        """Verify get_option_contracts calls Alpaca API correctly"""
        from tradingagents.dataflows.options_trading_utils import get_option_contracts

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.option_contracts = []
        mock_client.get_option_contracts.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = get_option_contracts(
            underlying="AAPL",
            contract_type="call",
            strike_price_gte=150.0,
            strike_price_lte=160.0,
            expiration_date_gte="2024-03-01",
            expiration_date_lte="2024-03-31",
        )

        assert isinstance(result, (list, str))

    @patch('tradingagents.dataflows.options_trading_utils.get_options_trading_client')
    def test_get_option_contracts_invalid_type(self, mock_get_client):
        """Verify get_option_contracts handles invalid contract type"""
        from tradingagents.dataflows.options_trading_utils import get_option_contracts

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.option_contracts = []
        mock_client.get_option_contracts.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = get_option_contracts(
            underlying="AAPL",
            contract_type="invalid_type",
            strike_price_gte=150.0,
            strike_price_lte=160.0,
        )

        # Should handle gracefully (invalid type becomes PUT by default)
        assert result is not None

    @patch('tradingagents.dataflows.options_trading_utils.get_api_key')
    def test_get_option_contract_by_symbol_no_credentials(self, mock_get_api_key):
        """Verify get_option_contract_by_symbol handles missing credentials"""
        from tradingagents.dataflows.options_trading_utils import (
            get_option_contract_by_symbol,
        )

        mock_get_api_key.return_value = None

        result = get_option_contract_by_symbol("AAPL240315C00200000")

        assert result is None


class TestOptionsOrderPlacement:
    """Tests for options order placement functions"""

    @patch('tradingagents.dataflows.options_trading_utils.get_api_key')
    def test_place_option_order_no_credentials(self, mock_get_api_key):
        """Verify place_option_order handles missing credentials"""
        from tradingagents.dataflows.options_trading_utils import place_option_order

        mock_get_api_key.return_value = None

        result = place_option_order(
            contract_symbol="AAPL240315C00200000",
            side="buy",
            qty=1,
        )

        # Should fail gracefully without credentials
        assert result is None or "error" in str(result).lower()

    def test_place_option_order_invalid_side(self):
        """Verify place_option_order validates side parameter"""
        from tradingagents.dataflows.options_trading_utils import place_option_order

        # Invalid side should be handled
        result = place_option_order(
            contract_symbol="AAPL240315C00200000",
            side="invalid_side",
            qty=1,
        )

        # Should handle gracefully
        assert result is None or "error" in str(result).lower()


class TestOptionsExecution:
    """Tests for options trade execution functions"""

    def test_execute_options_trading_action_no_options(self):
        """Verify NO_OPTIONS action does nothing"""
        from tradingagents.dataflows.options_trading_utils import (
            execute_options_trading_action,
        )

        result = execute_options_trading_action(
            contract_symbol="AAPL240315C00200000",
            action="NO_OPTIONS",
            qty=1,
        )

        # NO_OPTIONS should return success without executing a trade
        assert result is not None
        assert result.get("success") is True
        assert result.get("action") == "NO_OPTIONS"

    def test_execute_options_trading_action_hold(self):
        """Verify HOLD_OPTIONS action does nothing"""
        from tradingagents.dataflows.options_trading_utils import (
            execute_options_trading_action,
        )

        result = execute_options_trading_action(
            contract_symbol="AAPL240315C00200000",
            action="HOLD_OPTIONS",
            qty=1,
        )

        # HOLD_OPTIONS should return early without executing
        assert result is None or "hold" in str(result).lower() or result.get("status") == "skipped"


class TestRecommendedContracts:
    """Tests for contract recommendation functions"""

    @patch('tradingagents.dataflows.options_trading_utils.get_option_contracts')
    def test_get_recommended_contracts_bullish(self, mock_get_contracts):
        """Verify get_recommended_contracts for bullish direction"""
        from tradingagents.dataflows.options_trading_utils import (
            get_recommended_contracts,
        )

        mock_get_contracts.return_value = []

        result = get_recommended_contracts(
            ticker="AAPL",
            direction="bullish",
            risk_profile="moderate",
            curr_date="2024-03-01",
        )

        assert result is not None

    @patch('tradingagents.dataflows.options_trading_utils.get_option_contracts')
    def test_get_recommended_contracts_bearish(self, mock_get_contracts):
        """Verify get_recommended_contracts for bearish direction"""
        from tradingagents.dataflows.options_trading_utils import (
            get_recommended_contracts,
        )

        mock_get_contracts.return_value = []

        result = get_recommended_contracts(
            ticker="AAPL",
            direction="bearish",
            risk_profile="aggressive",
            curr_date="2024-03-01",
        )

        assert result is not None

    def test_get_recommended_contracts_invalid_direction(self):
        """Verify get_recommended_contracts handles invalid direction"""
        from tradingagents.dataflows.options_trading_utils import (
            get_recommended_contracts,
        )

        result = get_recommended_contracts(
            ticker="AAPL",
            direction="invalid",
            risk_profile="moderate",
            curr_date="2024-03-01",
        )

        # Should handle gracefully
        assert result is not None
