"""
Unit tests for the get_finnhub_news_online function
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


class TestGetFinnhubNewsOnline:
    """Tests for live Finnhub news API function"""

    @patch("tradingagents.dataflows.interface.get_finnhub_client")
    def test_successful_news_fetch(self, mock_get_client):
        """Test successful fetching of news articles"""
        from tradingagents.dataflows.interface import get_finnhub_news_online

        # Setup mock
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.company_news.return_value = [
            {
                "headline": "AAPL Reports Strong Quarterly Earnings",
                "summary": "Apple Inc. reported earnings that beat analyst expectations.",
                "source": "Reuters",
                "url": "https://example.com/article1",
                "datetime": 1707350400,  # 2024-02-08
            },
            {
                "headline": "iPhone Sales Surge in Asia",
                "summary": "Apple's iPhone sales increased 15% in Asian markets.",
                "source": "Bloomberg",
                "url": "https://example.com/article2",
                "datetime": 1707264000,  # 2024-02-07
            },
        ]

        result = get_finnhub_news_online("AAPL", "2024-02-08", 7)

        assert "AAPL Live News (Finnhub)" in result
        assert "AAPL Reports Strong Quarterly Earnings" in result
        assert "iPhone Sales Surge in Asia" in result
        assert "Reuters" in result
        assert "Bloomberg" in result
        mock_client.company_news.assert_called_once()

    @patch("tradingagents.dataflows.interface.get_finnhub_client")
    def test_no_news_found(self, mock_get_client):
        """Test handling when no news is found"""
        from tradingagents.dataflows.interface import get_finnhub_news_online

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.company_news.return_value = []

        result = get_finnhub_news_online("AAPL", "2024-02-08", 7)

        assert "No recent news found for AAPL" in result
        assert "2024-02-01" in result  # Start date (7 days before)
        assert "2024-02-08" in result  # End date

    @patch("tradingagents.dataflows.interface.get_finnhub_client")
    def test_empty_news_list(self, mock_get_client):
        """Test handling when API returns None"""
        from tradingagents.dataflows.interface import get_finnhub_news_online

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.company_news.return_value = None

        result = get_finnhub_news_online("AAPL", "2024-02-08", 7)

        assert "No recent news found for AAPL" in result

    @patch("tradingagents.dataflows.interface.get_finnhub_client")
    @patch("tradingagents.dataflows.interface.log_api_error")
    def test_api_error_handling(self, mock_log_error, mock_get_client):
        """Test error handling when API call fails"""
        from tradingagents.dataflows.interface import get_finnhub_news_online

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.company_news.side_effect = Exception("API rate limit exceeded")

        result = get_finnhub_news_online("AAPL", "2024-02-08", 7)

        assert "Error fetching live news for AAPL" in result
        assert "API rate limit exceeded" in result
        mock_log_error.assert_called_once()

    @patch("tradingagents.dataflows.interface.get_finnhub_client")
    def test_date_range_calculation(self, mock_get_client):
        """Test that date range is calculated correctly"""
        from tradingagents.dataflows.interface import get_finnhub_news_online

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.company_news.return_value = []

        get_finnhub_news_online("AAPL", "2024-02-15", 10)

        # Verify the API was called with correct date range
        mock_client.company_news.assert_called_once_with(
            "AAPL", _from="2024-02-05", to="2024-02-15"
        )

    @patch("tradingagents.dataflows.interface.get_finnhub_client")
    def test_default_lookback_days(self, mock_get_client):
        """Test default lookback of 7 days"""
        from tradingagents.dataflows.interface import get_finnhub_news_online

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.company_news.return_value = []

        get_finnhub_news_online("AAPL", "2024-02-08")

        mock_client.company_news.assert_called_once_with(
            "AAPL", _from="2024-02-01", to="2024-02-08"
        )

    @patch("tradingagents.dataflows.interface.get_finnhub_client")
    def test_limits_to_15_articles(self, mock_get_client):
        """Test that results are limited to 15 articles"""
        from tradingagents.dataflows.interface import get_finnhub_news_online

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Return 20 articles
        mock_client.company_news.return_value = [
            {
                "headline": f"Article {i}",
                "summary": f"Summary {i}",
                "source": "Test",
                "url": f"https://example.com/{i}",
                "datetime": 1707350400,
            }
            for i in range(20)
        ]

        result = get_finnhub_news_online("AAPL", "2024-02-08", 7)

        # Should only include first 15 articles
        assert "Article 0" in result
        assert "Article 14" in result
        assert "Article 15" not in result
        assert "Article 19" not in result

    @patch("tradingagents.dataflows.interface.get_finnhub_client")
    def test_article_formatting(self, mock_get_client):
        """Test that articles are formatted correctly"""
        from tradingagents.dataflows.interface import get_finnhub_news_online

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.company_news.return_value = [
            {
                "headline": "Test Headline",
                "summary": "Test summary content here.",
                "source": "TestSource",
                "url": "https://example.com/test",
                "datetime": 1707350400,
            }
        ]

        result = get_finnhub_news_online("AAPL", "2024-02-08", 7)

        # Check headline format
        assert "### Test Headline" in result
        # Check source is included
        assert "**Source:** TestSource" in result
        # Check date is included
        assert "**Date:**" in result
        # Check summary is included
        assert "Test summary content here." in result
        # Check URL link
        assert "[Read more](https://example.com/test)" in result

    @patch("tradingagents.dataflows.interface.get_finnhub_client")
    def test_missing_article_fields(self, mock_get_client):
        """Test handling of articles with missing fields"""
        from tradingagents.dataflows.interface import get_finnhub_news_online

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.company_news.return_value = [
            {
                # Missing headline, summary, source, url, datetime
            },
            {
                "headline": "Has Headline",
                # Missing other fields
            },
        ]

        result = get_finnhub_news_online("AAPL", "2024-02-08", 7)

        # Should use default values for missing fields
        assert "No headline" in result
        assert "No summary available" in result
        assert "Unknown" in result  # Default source or date
        assert "Has Headline" in result

    @patch("tradingagents.dataflows.interface.get_finnhub_client")
    def test_article_without_url(self, mock_get_client):
        """Test handling of articles without URL"""
        from tradingagents.dataflows.interface import get_finnhub_news_online

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.company_news.return_value = [
            {
                "headline": "No URL Article",
                "summary": "Summary",
                "source": "Test",
                "datetime": 1707350400,
                # No url field
            }
        ]

        result = get_finnhub_news_online("AAPL", "2024-02-08", 7)

        assert "No URL Article" in result
        assert "[Read more]" not in result  # No URL link

    @patch("tradingagents.dataflows.interface.get_finnhub_client")
    def test_timestamp_conversion(self, mock_get_client):
        """Test timestamp to date conversion"""
        from tradingagents.dataflows.interface import get_finnhub_news_online

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.company_news.return_value = [
            {
                "headline": "Test",
                "summary": "Summary",
                "source": "Test",
                "url": "https://example.com",
                "datetime": 1707393600,  # 2024-02-08 12:00:00 UTC
            }
        ]

        result = get_finnhub_news_online("AAPL", "2024-02-08", 7)

        # Should contain formatted date
        assert "2024-02-08" in result

    @patch("tradingagents.dataflows.interface.get_finnhub_client")
    def test_zero_timestamp(self, mock_get_client):
        """Test handling of zero timestamp"""
        from tradingagents.dataflows.interface import get_finnhub_news_online

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.company_news.return_value = [
            {
                "headline": "Test",
                "summary": "Summary",
                "source": "Test",
                "url": "https://example.com",
                "datetime": 0,
            }
        ]

        result = get_finnhub_news_online("AAPL", "2024-02-08", 7)

        assert "Unknown date" in result

    @patch("tradingagents.dataflows.interface.get_finnhub_client")
    def test_different_tickers(self, mock_get_client):
        """Test with different ticker symbols"""
        from tradingagents.dataflows.interface import get_finnhub_news_online

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.company_news.return_value = [
            {
                "headline": "NVDA News",
                "summary": "Nvidia news content",
                "source": "Test",
                "datetime": 1707350400,
            }
        ]

        result = get_finnhub_news_online("NVDA", "2024-02-08", 7)

        assert "NVDA Live News (Finnhub)" in result
        mock_client.company_news.assert_called_once_with(
            "NVDA", _from="2024-02-01", to="2024-02-08"
        )

    @patch("tradingagents.dataflows.interface.get_finnhub_client")
    @patch("tradingagents.dataflows.interface.log_api_error")
    def test_invalid_date_format(self, mock_log_error, mock_get_client):
        """Test handling of invalid date format"""
        from tradingagents.dataflows.interface import get_finnhub_news_online

        result = get_finnhub_news_online("AAPL", "invalid-date", 7)

        assert "Error fetching live news for AAPL" in result
        mock_log_error.assert_called_once()


class TestToolkitGetFinnhubNewsOnline:
    """Tests for the Toolkit wrapper of get_finnhub_news_online"""

    @patch("tradingagents.dataflows.interface.get_finnhub_news_online")
    def test_toolkit_calls_interface(self, mock_interface_fn):
        """Test that Toolkit method calls the interface function"""
        from tradingagents.agents.utils.agent_utils import Toolkit

        mock_interface_fn.return_value = "Test news result"
        toolkit = Toolkit()

        # Call the tool (it's a static method wrapped with @tool)
        result = toolkit.get_finnhub_news_online.invoke(
            {"ticker": "AAPL", "curr_date": "2024-02-08", "look_back_days": 7}
        )

        mock_interface_fn.assert_called_once_with("AAPL", "2024-02-08", 7)
        assert result == "Test news result"

    @patch("tradingagents.dataflows.interface.get_finnhub_news_online")
    def test_toolkit_default_lookback(self, mock_interface_fn):
        """Test Toolkit uses default lookback of 7 days"""
        from tradingagents.agents.utils.agent_utils import Toolkit

        mock_interface_fn.return_value = "Test news result"
        toolkit = Toolkit()

        # Call without look_back_days
        result = toolkit.get_finnhub_news_online.invoke(
            {"ticker": "AAPL", "curr_date": "2024-02-08"}
        )

        mock_interface_fn.assert_called_once_with("AAPL", "2024-02-08", 7)


class TestNewsAnalystIntegration:
    """Integration tests for News Analyst using the new Finnhub live news tool"""

    def test_news_analyst_includes_finnhub_online_tool_for_stocks(self):
        """Test that News Analyst includes get_finnhub_news_online for stock analysis"""
        from tradingagents.agents.analysts.news_analyst import create_news_analyst
        from tradingagents.agents.utils.agent_utils import Toolkit
        from unittest.mock import MagicMock

        # Create mock LLM
        mock_llm = MagicMock()
        mock_result = MagicMock()
        mock_result.content = "Test analysis. FINAL TRANSACTION PROPOSAL: **HOLD**"
        mock_result.additional_kwargs = {}
        mock_llm.bind_tools.return_value.invoke.return_value = mock_result

        # Create toolkit with online_tools disabled
        toolkit = Toolkit()
        toolkit._config = {"online_tools": False}

        # Create analyst
        analyst_node = create_news_analyst(mock_llm, toolkit)

        # Mock state for a stock (not crypto)
        state = {
            "trade_date": "2024-02-08",
            "company_of_interest": "AAPL",
            "messages": [],
        }

        # Invoke the analyst
        result = analyst_node(state)

        # Verify bind_tools was called with tools that include get_finnhub_news_online
        call_args = mock_llm.bind_tools.call_args
        tools = call_args[0][0]
        tool_names = [t.name for t in tools]

        assert "get_finnhub_news_online" in tool_names
        assert "news_report" in result

    def test_news_analyst_uses_different_tools_for_crypto(self):
        """Test that News Analyst uses different tools for crypto"""
        from tradingagents.agents.analysts.news_analyst import create_news_analyst
        from tradingagents.agents.utils.agent_utils import Toolkit
        from unittest.mock import MagicMock

        mock_llm = MagicMock()
        mock_result = MagicMock()
        mock_result.content = "Test analysis. FINAL TRANSACTION PROPOSAL: **HOLD**"
        mock_result.additional_kwargs = {}
        mock_llm.bind_tools.return_value.invoke.return_value = mock_result

        toolkit = Toolkit()
        toolkit._config = {"online_tools": False}

        analyst_node = create_news_analyst(mock_llm, toolkit)

        # Mock state for crypto
        state = {
            "trade_date": "2024-02-08",
            "company_of_interest": "BTC/USD",
            "messages": [],
        }

        result = analyst_node(state)

        call_args = mock_llm.bind_tools.call_args
        tools = call_args[0][0]
        tool_names = [t.name for t in tools]

        # Crypto should use coindesk, not finnhub
        assert "get_finnhub_news_online" not in tool_names
        assert "get_coindesk_news" in tool_names
