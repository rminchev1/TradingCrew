"""
Tests for the Sector/Correlation Analyst.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from langchain_core.messages import AIMessage
import pandas as pd
import numpy as np


class TestSectorCorrelationAnalyst:
    """Tests for the sector correlation analyst node."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_state = {
            "messages": [],
            "trade_date": "2024-01-15",
            "company_of_interest": "AAPL",
        }

    def test_analyst_creation(self):
        """Test that the analyst node can be created."""
        from tradingagents.agents.analysts.sector_correlation_analyst import create_sector_correlation_analyst

        mock_llm = MagicMock()
        mock_toolkit = MagicMock()

        analyst_node = create_sector_correlation_analyst(mock_llm, mock_toolkit)

        assert callable(analyst_node)

    def test_crypto_skip_sector_analysis(self):
        """Test that crypto assets skip sector analysis."""
        from tradingagents.agents.analysts.sector_correlation_analyst import create_sector_correlation_analyst

        mock_llm = MagicMock()
        mock_toolkit = MagicMock()

        analyst_node = create_sector_correlation_analyst(mock_llm, mock_toolkit)

        # Test with BTC/USD
        crypto_state = {
            "messages": [],
            "trade_date": "2024-01-15",
            "company_of_interest": "BTC/USD",
        }

        result = analyst_node(crypto_state)

        # Should return a report without calling the LLM
        assert "sector_correlation_report" in result
        assert "cryptocurrency" in result["sector_correlation_report"].lower() or "not available" in result["sector_correlation_report"].lower()

    def test_crypto_eth_skip_sector_analysis(self):
        """Test that ETH/USD also skips sector analysis."""
        from tradingagents.agents.analysts.sector_correlation_analyst import create_sector_correlation_analyst

        mock_llm = MagicMock()
        mock_toolkit = MagicMock()

        analyst_node = create_sector_correlation_analyst(mock_llm, mock_toolkit)

        crypto_state = {
            "messages": [],
            "trade_date": "2024-01-15",
            "company_of_interest": "ETH/USD",
        }

        result = analyst_node(crypto_state)

        assert "sector_correlation_report" in result
        assert "HOLD" in result["sector_correlation_report"]

    @patch('tradingagents.agents.analysts.sector_correlation_analyst.capture_agent_prompt')
    @patch('tradingagents.agents.analysts.sector_correlation_analyst.ChatPromptTemplate')
    def test_stock_analysis_calls_tools(self, mock_template_class, mock_capture):
        """Test that stock analysis properly invokes tools."""
        from tradingagents.agents.analysts.sector_correlation_analyst import create_sector_correlation_analyst

        # Mock LLM that returns a result with FINAL TRANSACTION PROPOSAL
        mock_response = MagicMock()
        mock_response.content = """# Sector Analysis for AAPL

## Summary
AAPL is a leader in the technology sector.

| Metric | Value | Signal | Overnight Bias |
|--------|-------|--------|----------------|
| Sector Rank | #1 of 15 | Leader | Bullish |
| RS vs Sector | 1.05 | Rising | Bullish |
| Sector Momentum | #1 of 11 | Inflow | Bullish |
| SPY Correlation | 0.85 | High | Market-dependent |

FINAL TRANSACTION PROPOSAL: **BUY** - Strong sector leader with rising relative strength.
"""
        mock_response.additional_kwargs = {}

        # Mock the chain behavior - when using | operator with prompt
        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value=mock_response)

        mock_llm = MagicMock()
        mock_bound_llm = MagicMock()
        mock_bound_llm.__or__ = MagicMock(return_value=mock_chain)  # prompt | llm returns chain
        mock_llm.bind_tools = MagicMock(return_value=mock_bound_llm)

        # Mock the prompt template
        mock_prompt = MagicMock()
        mock_prompt.partial = MagicMock(return_value=mock_prompt)
        mock_prompt.format_messages = MagicMock(return_value=[MagicMock(content="test prompt")])
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)  # prompt | bound_llm returns chain
        mock_template_class.from_messages = MagicMock(return_value=mock_prompt)

        # Create a mock toolkit with the required tools
        mock_toolkit = MagicMock()
        mock_toolkit.get_sector_peers = MagicMock()
        mock_toolkit.get_sector_peers.name = "get_sector_peers"
        mock_toolkit.get_peer_comparison = MagicMock()
        mock_toolkit.get_peer_comparison.name = "get_peer_comparison"
        mock_toolkit.get_relative_strength = MagicMock()
        mock_toolkit.get_relative_strength.name = "get_relative_strength"
        mock_toolkit.get_sector_rotation = MagicMock()
        mock_toolkit.get_sector_rotation.name = "get_sector_rotation"

        analyst_node = create_sector_correlation_analyst(mock_llm, mock_toolkit)

        result = analyst_node(self.mock_state)

        # Should return sector_correlation_report
        assert "sector_correlation_report" in result
        assert "FINAL TRANSACTION PROPOSAL" in result["sector_correlation_report"]
        assert "BUY" in result["sector_correlation_report"] or "HOLD" in result["sector_correlation_report"] or "SELL" in result["sector_correlation_report"]

    @patch('tradingagents.agents.analysts.sector_correlation_analyst.capture_agent_prompt')
    @patch('tradingagents.agents.analysts.sector_correlation_analyst.ChatPromptTemplate')
    def test_analyst_returns_messages(self, mock_template_class, mock_capture):
        """Test that analyst returns messages in expected format."""
        from tradingagents.agents.analysts.sector_correlation_analyst import create_sector_correlation_analyst

        mock_response = MagicMock()
        mock_response.content = "Test report content\nFINAL TRANSACTION PROPOSAL: **HOLD** - Testing"
        mock_response.additional_kwargs = {}

        # Mock the chain behavior
        mock_chain = MagicMock()
        mock_chain.invoke = MagicMock(return_value=mock_response)

        mock_llm = MagicMock()
        mock_bound_llm = MagicMock()
        mock_bound_llm.__or__ = MagicMock(return_value=mock_chain)
        mock_llm.bind_tools = MagicMock(return_value=mock_bound_llm)

        # Mock the prompt template
        mock_prompt = MagicMock()
        mock_prompt.partial = MagicMock(return_value=mock_prompt)
        mock_prompt.format_messages = MagicMock(return_value=[MagicMock(content="test prompt")])
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)
        mock_template_class.from_messages = MagicMock(return_value=mock_prompt)

        mock_toolkit = MagicMock()
        mock_toolkit.get_sector_peers = MagicMock()
        mock_toolkit.get_sector_peers.name = "get_sector_peers"
        mock_toolkit.get_peer_comparison = MagicMock()
        mock_toolkit.get_peer_comparison.name = "get_peer_comparison"
        mock_toolkit.get_relative_strength = MagicMock()
        mock_toolkit.get_relative_strength.name = "get_relative_strength"
        mock_toolkit.get_sector_rotation = MagicMock()
        mock_toolkit.get_sector_rotation.name = "get_sector_rotation"

        analyst_node = create_sector_correlation_analyst(mock_llm, mock_toolkit)

        result = analyst_node(self.mock_state)

        # Should return messages list
        assert "messages" in result
        assert len(result["messages"]) > 0


class TestSectorAnalystIntegration:
    """Integration tests for sector analyst with graph setup."""

    def test_analyst_available_in_graph_setup(self):
        """Test that sector analyst is available for graph setup."""
        from tradingagents.agents.analysts import create_sector_correlation_analyst

        # Should be importable
        assert callable(create_sector_correlation_analyst)

    def test_sector_state_field_exists(self):
        """Test that sector_correlation_report field exists in AgentState."""
        from tradingagents.agents.utils.agent_states import AgentState

        # AgentState should have sector_correlation_report annotation
        annotations = AgentState.__annotations__
        assert "sector_correlation_report" in annotations

    def test_conditional_logic_for_sector(self):
        """Test that conditional logic handles sector analyst."""
        from tradingagents.graph.conditional_logic import ConditionalLogic

        logic = ConditionalLogic()

        # Should have should_continue_sector method
        assert hasattr(logic, "should_continue_sector")

        # Mock state with tool calls
        mock_message = MagicMock()
        mock_message.tool_calls = [{"name": "test_tool"}]
        mock_state = {"messages": [mock_message]}

        result = logic.should_continue_sector(mock_state)
        assert result == "tools_sector"

        # Mock state without tool calls
        mock_message_no_tools = MagicMock()
        mock_message_no_tools.tool_calls = []
        mock_state_no_tools = {"messages": [mock_message_no_tools]}

        result_no_tools = logic.should_continue_sector(mock_state_no_tools)
        assert result_no_tools == "Msg Clear Sector"


class TestSectorReportContent:
    """Tests for the content/format of sector reports."""

    def test_crypto_report_format(self):
        """Test that crypto reports have expected format."""
        from tradingagents.agents.analysts.sector_correlation_analyst import create_sector_correlation_analyst

        mock_llm = MagicMock()
        mock_toolkit = MagicMock()

        analyst_node = create_sector_correlation_analyst(mock_llm, mock_toolkit)

        crypto_state = {
            "messages": [],
            "trade_date": "2024-01-15",
            "company_of_interest": "SOL/USD",
        }

        result = analyst_node(crypto_state)
        report = result["sector_correlation_report"]

        # Crypto report should mention it's not available
        assert "not available" in report.lower() or "cryptocurrency" in report.lower()
        # Should still have FINAL TRANSACTION PROPOSAL
        assert "FINAL TRANSACTION PROPOSAL" in report

    def test_various_crypto_formats(self):
        """Test that various crypto formats are detected."""
        from tradingagents.agents.analysts.sector_correlation_analyst import create_sector_correlation_analyst

        mock_llm = MagicMock()
        mock_toolkit = MagicMock()

        analyst_node = create_sector_correlation_analyst(mock_llm, mock_toolkit)

        crypto_tickers = ["BTC/USD", "ETH/USD", "BTCUSD", "ETHUSD"]

        for ticker in crypto_tickers:
            state = {
                "messages": [],
                "trade_date": "2024-01-15",
                "company_of_interest": ticker,
            }

            result = analyst_node(state)

            # All crypto should skip sector analysis
            assert "sector_correlation_report" in result
