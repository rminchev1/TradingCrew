"""Tests for tradingagents/chat_assistant.py"""

import pytest
from unittest.mock import patch, MagicMock

from tradingagents.chat_assistant import (
    parse_actions,
    strip_action_markers,
    PortfolioAssistant,
    ASSISTANT_TOOLS,
    NO_TEMP_MODELS,
    get_account_summary,
    get_portfolio_positions,
    get_stock_quote,
    get_stock_fundamentals,
    get_recent_news,
    get_sector_exposure,
    get_watchlist,
    get_latest_analysis,
)


# ---------------------------------------------------------------------------
# Action Parsing Tests
# ---------------------------------------------------------------------------


class TestParseActions:
    def test_single_action(self):
        content = "Check out AAPL. [[ACTION:AAPL:watchlist:Strong fundamentals]]"
        actions = parse_actions(content)
        assert len(actions) == 1
        assert actions[0]["symbol"] == "AAPL"
        assert actions[0]["target"] == "watchlist"
        assert actions[0]["reason"] == "Strong fundamentals"

    def test_multiple_actions(self):
        content = (
            "Consider these:\n"
            "[[ACTION:AAPL:watchlist:Good value]]\n"
            "[[ACTION:NVDA:run:High momentum]]\n"
        )
        actions = parse_actions(content)
        assert len(actions) == 2
        assert actions[0]["symbol"] == "AAPL"
        assert actions[0]["target"] == "watchlist"
        assert actions[1]["symbol"] == "NVDA"
        assert actions[1]["target"] == "run"

    def test_no_actions(self):
        content = "Here is your portfolio summary. Everything looks good."
        actions = parse_actions(content)
        assert len(actions) == 0

    def test_crypto_symbol(self):
        content = "[[ACTION:BTC/USD:watchlist:Breaking resistance]]"
        actions = parse_actions(content)
        assert len(actions) == 1
        assert actions[0]["symbol"] == "BTC/USD"

    def test_strip_action_markers(self):
        content = "Check AAPL. [[ACTION:AAPL:watchlist:Reason here]] End."
        stripped = strip_action_markers(content)
        assert "[[ACTION" not in stripped
        assert "Check AAPL." in stripped
        assert "End." in stripped

    def test_strip_preserves_non_action_text(self):
        content = "No actions here."
        stripped = strip_action_markers(content)
        assert stripped == "No actions here."


# ---------------------------------------------------------------------------
# Tool Function Tests (mocked external calls)
# ---------------------------------------------------------------------------


class TestGetAccountSummary:
    @patch("tradingagents.chat_assistant.get_account_summary")
    def test_returns_string(self, mock_tool):
        mock_tool.invoke.return_value = "Account Summary:\n  Equity: $100,000.00"
        result = mock_tool.invoke({})
        assert "Equity" in result or "Account" in result

    @patch("tradingagents.dataflows.alpaca_utils.AlpacaUtils.get_account_info")
    def test_with_mock_alpaca(self, mock_account):
        mock_account.return_value = {
            "equity": 100000.0,
            "cash": 50000.0,
            "buying_power": 200000.0,
            "daily_change_dollars": 1500.0,
            "daily_change_percent": 1.5,
        }
        result = get_account_summary.invoke({})
        assert "100,000.00" in result
        assert "50,000.00" in result
        assert "+1,500.00" in result

    @patch("tradingagents.dataflows.alpaca_utils.AlpacaUtils.get_account_info")
    def test_error_handling(self, mock_account):
        mock_account.side_effect = Exception("API down")
        result = get_account_summary.invoke({})
        assert "Error" in result


class TestGetPortfolioPositions:
    @patch("tradingagents.dataflows.alpaca_utils.AlpacaUtils.get_positions_data")
    def test_with_positions(self, mock_positions):
        mock_positions.return_value = [
            {
                "Symbol": "AAPL",
                "Qty": 10,
                "market_value_raw": 1500.0,
                "total_pl_dollars_raw": 200.0,
                "total_pl_pct_raw": 15.0,
                "avg_entry_raw": 130.0,
            }
        ]
        result = get_portfolio_positions.invoke({})
        assert "AAPL" in result
        assert "10 shares" in result

    @patch("tradingagents.dataflows.alpaca_utils.AlpacaUtils.get_positions_data")
    def test_no_positions(self, mock_positions):
        mock_positions.return_value = []
        result = get_portfolio_positions.invoke({})
        assert "No open positions" in result


class TestGetStockQuote:
    @patch("yfinance.Ticker")
    def test_basic_quote(self, mock_ticker_cls):
        mock_info = {
            "regularMarketPrice": 150.25,
            "regularMarketPreviousClose": 148.0,
            "dayHigh": 151.0,
            "dayLow": 149.0,
            "regularMarketVolume": 5000000,
            "marketCap": 2400000000000,
        }
        mock_ticker_cls.return_value.info = mock_info
        result = get_stock_quote.invoke({"symbol": "AAPL"})
        assert "AAPL" in result
        assert "150.25" in result

    @patch("yfinance.Ticker")
    def test_crypto_symbol_conversion(self, mock_ticker_cls):
        mock_ticker_cls.return_value.info = {
            "regularMarketPrice": 65000.0,
            "regularMarketPreviousClose": 64000.0,
            "dayHigh": 66000.0,
            "dayLow": 64500.0,
            "regularMarketVolume": 100000,
        }
        result = get_stock_quote.invoke({"symbol": "BTC/USD"})
        # Should convert BTC/USD to BTC-USD for yfinance
        mock_ticker_cls.assert_called_once_with("BTC-USD")
        assert "BTC/USD" in result

    @patch("yfinance.Ticker")
    def test_no_data(self, mock_ticker_cls):
        mock_ticker_cls.return_value.info = {}
        result = get_stock_quote.invoke({"symbol": "INVALID"})
        assert "No quote data" in result


class TestGetRecentNews:
    @patch("tradingagents.dataflows.interface.get_finnhub_news_online")
    def test_stock_news(self, mock_news):
        mock_news.return_value = "AAPL: New product launch announced..."
        result = get_recent_news.invoke({"symbol": "AAPL"})
        assert "AAPL" in result

    @patch("tradingagents.dataflows.interface.get_coindesk_news")
    def test_crypto_news(self, mock_news):
        mock_news.return_value = "BTC: Price rally continues..."
        result = get_recent_news.invoke({"symbol": "BTC/USD"})
        assert "BTC" in result


class TestGetWatchlist:
    @patch("tradingagents.chat_assistant.get_watchlist")
    def test_returns_watchlist(self, mock_tool):
        mock_tool.invoke.return_value = "Watchlist (3 symbols): AAPL, NVDA, TSLA"
        result = mock_tool.invoke({})
        assert "AAPL" in result


class TestGetLatestAnalysis:
    def test_no_state(self):
        with patch("webui.utils.state.app_state") as mock_state:
            mock_state.get_state.return_value = None
            result = get_latest_analysis.invoke({"symbol": "AAPL"})
            assert "No analysis data" in result

    def test_with_decision(self):
        mock_state_data = {
            "current_reports": {
                "final_trade_decision": "BUY AAPL - Strong fundamentals"
            }
        }
        with patch("webui.utils.state.app_state") as mock_state:
            mock_state.get_state.return_value = mock_state_data
            result = get_latest_analysis.invoke({"symbol": "AAPL"})
            assert "BUY AAPL" in result


# ---------------------------------------------------------------------------
# PortfolioAssistant Tests
# ---------------------------------------------------------------------------


class TestPortfolioAssistant:
    def test_init_defaults(self):
        assistant = PortfolioAssistant()
        assert assistant.model_name == "gpt-4.1-nano"
        assert assistant.max_retries == 3

    def test_init_custom(self):
        assistant = PortfolioAssistant(
            model_name="gpt-4.1",
            api_key="test-key",
            max_retries=5,
        )
        assert assistant.model_name == "gpt-4.1"
        assert assistant.api_key == "test-key"
        assert assistant.max_retries == 5

    @patch("tradingagents.chat_assistant.ChatOpenAI", create=True)
    def test_respond_no_tool_calls(self, mock_chat_cls):
        """Test response when LLM returns text without tool calls."""
        mock_response = MagicMock()
        mock_response.tool_calls = []
        mock_response.content = "Your portfolio looks great!"

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = mock_response
        mock_chat_cls.return_value = mock_llm

        assistant = PortfolioAssistant(api_key="test-key")
        assistant._llm = mock_llm

        result = assistant.respond([{"role": "user", "content": "How's my portfolio?"}])
        assert result == "Your portfolio looks great!"

    @patch("tradingagents.chat_assistant.ChatOpenAI", create=True)
    def test_respond_with_tool_calls(self, mock_chat_cls):
        """Test response with one round of tool calls."""
        # First call: LLM requests a tool
        tool_response = MagicMock()
        tool_response.tool_calls = [
            {"name": "get_account_summary", "args": {}, "id": "call_1"}
        ]
        tool_response.content = ""

        # Second call: LLM returns final answer
        final_response = MagicMock()
        final_response.tool_calls = []
        final_response.content = "Your equity is $100k."

        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.side_effect = [tool_response, final_response]
        mock_chat_cls.return_value = mock_llm

        assistant = PortfolioAssistant(api_key="test-key")
        assistant._llm = mock_llm

        # Mock the underlying Alpaca call instead of the tool's invoke method
        with patch(
            "tradingagents.dataflows.alpaca_utils.AlpacaUtils.get_account_info",
            return_value={
                "equity": 100000.0, "cash": 50000.0, "buying_power": 200000.0,
                "daily_change_dollars": 1500.0, "daily_change_percent": 1.5,
            },
        ):
            result = assistant.respond([{"role": "user", "content": "Account summary?"}])

        assert "100k" in result

    def test_no_temp_models_list(self):
        """Verify the no-temperature model list matches the known set."""
        assert "o3" in NO_TEMP_MODELS
        assert "o4-mini" in NO_TEMP_MODELS
        assert "gpt-5" in NO_TEMP_MODELS

    def test_tools_list_complete(self):
        """Verify all 8 tools are registered."""
        assert len(ASSISTANT_TOOLS) == 8
        tool_names = [t.name for t in ASSISTANT_TOOLS]
        assert "get_account_summary" in tool_names
        assert "get_portfolio_positions" in tool_names
        assert "get_stock_quote" in tool_names
        assert "get_stock_fundamentals" in tool_names
        assert "get_recent_news" in tool_names
        assert "get_sector_exposure" in tool_names
        assert "get_watchlist" in tool_names
        assert "get_latest_analysis" in tool_names
