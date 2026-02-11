"""
Unit tests for options trader agent.

Tests the options trader agent and recommendation parsing:
- Options trader node creation
- Recommendation extraction
- Validation logic
"""

import pytest
from unittest.mock import MagicMock, patch


class TestOptionsTraderCreation:
    """Tests for options trader node creation"""

    def test_create_options_trader_basic(self):
        """Verify options trader node can be created"""
        from tradingagents.agents.trader.options_trader import create_options_trader

        mock_llm = MagicMock()
        mock_memory = MagicMock()
        mock_memory.get_memories.return_value = []

        options_trader_node = create_options_trader(mock_llm, mock_memory)

        assert options_trader_node is not None
        assert callable(options_trader_node)

    def test_create_options_trader_with_config(self):
        """Verify options trader respects config settings"""
        from tradingagents.agents.trader.options_trader import create_options_trader

        mock_llm = MagicMock()
        mock_memory = MagicMock()
        mock_memory.get_memories.return_value = []

        config = {
            "enable_options_trading": True,
            "options_trading_level": 2,
            "options_max_contracts": 5,
        }

        options_trader_node = create_options_trader(mock_llm, mock_memory, config)

        assert options_trader_node is not None
        assert callable(options_trader_node)


class TestOptionsRecommendationExtraction:
    """Tests for options recommendation extraction"""

    def test_extract_buy_call_recommendation(self):
        """Verify extraction of BUY_CALL recommendation"""
        from tradingagents.agents.utils.agent_trading_modes import (
            extract_options_recommendation,
        )

        content = """
        Based on the analysis, I recommend:

        FINAL OPTIONS PROPOSAL: **BUY_CALL** - AAPL $180 Call, 30 DTE, 2 contracts @ $3.50
        """

        result = extract_options_recommendation(content)

        assert result is not None
        assert result.get("action") == "BUY_CALL"

    def test_extract_buy_put_recommendation(self):
        """Verify extraction of BUY_PUT recommendation"""
        from tradingagents.agents.utils.agent_trading_modes import (
            extract_options_recommendation,
        )

        content = """
        FINAL OPTIONS PROPOSAL: **BUY_PUT** - TSLA $200 Put, 14 DTE, 1 contract @ $5.25
        """

        result = extract_options_recommendation(content)

        assert result is not None
        assert result.get("action") == "BUY_PUT"

    def test_extract_no_options_recommendation(self):
        """Verify extraction of NO_OPTIONS recommendation"""
        from tradingagents.agents.utils.agent_trading_modes import (
            extract_options_recommendation,
        )

        content = """
        FINAL OPTIONS PROPOSAL: **NO_OPTIONS** - Current market conditions do not warrant options trading
        """

        result = extract_options_recommendation(content)

        assert result is not None
        assert result.get("action") == "NO_OPTIONS"

    def test_extract_missing_recommendation(self):
        """Verify handling of missing recommendation"""
        from tradingagents.agents.utils.agent_trading_modes import (
            extract_options_recommendation,
        )

        content = """
        This is some analysis text without a final proposal.
        """

        result = extract_options_recommendation(content)

        # Should return None or empty dict when no recommendation found
        assert result is None or result.get("action") is None


class TestOptionsRecommendationValidation:
    """Tests for options recommendation validation"""

    def test_validate_valid_recommendation(self):
        """Verify valid recommendation passes validation"""
        from tradingagents.agents.utils.agent_trading_modes import (
            validate_options_recommendation,
        )

        recommendation = {
            "action": "BUY_CALL",
            "qty": 2,
            "dte": 30,
        }

        config = {
            "options_max_contracts": 10,
            "options_min_dte": 7,
            "options_max_dte": 45,
        }

        is_valid, error = validate_options_recommendation(recommendation, config)

        assert is_valid is True
        assert error is None or error == ""

    def test_validate_exceeds_max_contracts(self):
        """Verify validation catches too many contracts"""
        from tradingagents.agents.utils.agent_trading_modes import (
            validate_options_recommendation,
        )

        recommendation = {
            "action": "BUY_CALL",
            "qty": 100,  # Way over limit
            "dte": 30,
        }

        config = {
            "options_max_contracts": 10,
            "options_min_dte": 7,
            "options_max_dte": 45,
        }

        is_valid, error = validate_options_recommendation(recommendation, config)

        assert is_valid is False
        assert error is not None

    def test_validate_dte_too_short(self):
        """Verify validation catches DTE below minimum"""
        from tradingagents.agents.utils.agent_trading_modes import (
            validate_options_recommendation,
        )

        recommendation = {
            "action": "BUY_PUT",
            "qty": 1,
            "dte": 3,  # Below minimum
        }

        config = {
            "options_max_contracts": 10,
            "options_min_dte": 7,
            "options_max_dte": 45,
        }

        is_valid, error = validate_options_recommendation(recommendation, config)

        assert is_valid is False
        assert error is not None

    def test_validate_dte_too_long(self):
        """Verify validation catches DTE above maximum"""
        from tradingagents.agents.utils.agent_trading_modes import (
            validate_options_recommendation,
        )

        recommendation = {
            "action": "BUY_CALL",
            "qty": 1,
            "dte": 90,  # Above maximum
        }

        config = {
            "options_max_contracts": 10,
            "options_min_dte": 7,
            "options_max_dte": 45,
        }

        is_valid, error = validate_options_recommendation(recommendation, config)

        assert is_valid is False
        assert error is not None

    def test_validate_no_options_always_valid(self):
        """Verify NO_OPTIONS is always valid"""
        from tradingagents.agents.utils.agent_trading_modes import (
            validate_options_recommendation,
        )

        recommendation = {
            "action": "NO_OPTIONS",
        }

        config = {
            "options_max_contracts": 10,
            "options_min_dte": 7,
            "options_max_dte": 45,
        }

        is_valid, error = validate_options_recommendation(recommendation, config)

        assert is_valid is True


class TestOptionsActions:
    """Tests for options action definitions"""

    def test_options_actions_defined(self):
        """Verify OPTIONS_ACTIONS is properly defined"""
        from tradingagents.agents.utils.agent_trading_modes import TradingModeConfig

        assert hasattr(TradingModeConfig, "OPTIONS_ACTIONS")
        assert isinstance(TradingModeConfig.OPTIONS_ACTIONS, list)
        assert len(TradingModeConfig.OPTIONS_ACTIONS) > 0

    def test_options_actions_contains_expected(self):
        """Verify OPTIONS_ACTIONS contains expected actions"""
        from tradingagents.agents.utils.agent_trading_modes import TradingModeConfig

        expected_actions = [
            "BUY_CALL",
            "BUY_PUT",
            "SELL_CALL",
            "SELL_PUT",
            "NO_OPTIONS",
            "HOLD_OPTIONS",
        ]

        for action in expected_actions:
            assert action in TradingModeConfig.OPTIONS_ACTIONS, \
                f"Missing action: {action}"

    def test_options_actions_vs_trading_actions_distinct(self):
        """Verify OPTIONS_ACTIONS and TRADING_ACTIONS are distinct"""
        from tradingagents.agents.utils.agent_trading_modes import TradingModeConfig

        options_set = set(TradingModeConfig.OPTIONS_ACTIONS)
        trading_set = set(TradingModeConfig.TRADING_ACTIONS)

        # These should be mostly distinct (no overlap)
        overlap = options_set & trading_set
        assert len(overlap) == 0, f"Unexpected overlap: {overlap}"


class TestOptionsAnalystCreation:
    """Tests for options analyst with options trading mode"""

    def test_create_options_analyst_basic(self):
        """Verify options analyst can be created"""
        from tradingagents.agents.analysts.options_analyst import create_options_analyst

        mock_llm = MagicMock()
        mock_toolkit = MagicMock()
        mock_toolkit.get_options_positioning = MagicMock()

        options_analyst_node = create_options_analyst(mock_llm, mock_toolkit)

        assert options_analyst_node is not None
        assert callable(options_analyst_node)

    def test_create_options_analyst_with_config(self):
        """Verify options analyst with options trading config"""
        from tradingagents.agents.analysts.options_analyst import create_options_analyst

        mock_llm = MagicMock()
        mock_toolkit = MagicMock()
        mock_toolkit.get_options_positioning = MagicMock()

        config = {
            "enable_options_trading": True,
            "options_trading_level": 2,
        }

        options_analyst_node = create_options_analyst(
            mock_llm, mock_toolkit, config=config
        )

        assert options_analyst_node is not None
        assert callable(options_analyst_node)


class TestOptionsContext:
    """Tests for options trading context generation"""

    def test_get_options_trading_context_basic(self):
        """Verify options trading context is generated"""
        from tradingagents.agents.utils.agent_trading_modes import (
            get_options_trading_context,
        )

        config = {
            "options_trading_level": 2,
            "options_max_contracts": 10,
            "options_min_dte": 7,
            "options_max_dte": 45,
        }

        context = get_options_trading_context(config, [])

        assert context is not None
        assert "instructions" in context
        assert len(context["instructions"]) > 0

    def test_get_options_trading_context_with_positions(self):
        """Verify options trading context includes positions"""
        from tradingagents.agents.utils.agent_trading_modes import (
            get_options_trading_context,
        )

        config = {
            "options_trading_level": 2,
            "options_max_contracts": 10,
        }

        positions = [
            {
                "symbol": "AAPL240315C00200000",
                "qty": 2,
                "underlying": "AAPL",
                "contract_type": "call",
                "strike": 200.0,
                "avg_entry_price": 3.50,
                "unrealized_pl": 100.0,
            }
        ]

        context = get_options_trading_context(config, positions)

        assert context is not None
        assert "instructions" in context
