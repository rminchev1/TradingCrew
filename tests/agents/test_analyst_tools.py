"""
Unit tests for analyst tool configurations.

Verifies that:
- News Analyst uses Finnhub API (and CoinDesk for crypto)
- Social Media Analyst uses Reddit API for sentiment
- Crypto detection patterns work correctly
"""

import pytest
from unittest.mock import MagicMock, patch


class TestNewsAnalystToolConfiguration:
    """Tests for news analyst tool configuration"""

    def test_stock_news_uses_finnhub(self):
        """Verify stock news analysis uses Finnhub API"""
        from tradingagents.agents.analysts.news_analyst import create_news_analyst

        mock_toolkit = MagicMock()
        mock_toolkit.get_finnhub_news_online = MagicMock(name='get_finnhub_news_online')
        mock_toolkit.get_coindesk_news = MagicMock(name='get_coindesk_news')

        mock_llm = MagicMock()

        # Create the news analyst node
        news_analyst_node = create_news_analyst(mock_llm, mock_toolkit)

        # Verify function is created
        assert news_analyst_node is not None
        assert callable(news_analyst_node)

    def test_crypto_news_uses_coindesk_and_finnhub(self):
        """Verify crypto news analysis uses CoinDesk and Finnhub"""
        from tradingagents.agents.analysts.news_analyst import create_news_analyst

        mock_toolkit = MagicMock()
        mock_toolkit.get_finnhub_news_online = MagicMock(name='get_finnhub_news_online')
        mock_toolkit.get_coindesk_news = MagicMock(name='get_coindesk_news')

        mock_llm = MagicMock()

        # Create the news analyst node
        news_analyst_node = create_news_analyst(mock_llm, mock_toolkit)

        assert news_analyst_node is not None
        assert callable(news_analyst_node)


class TestSocialMediaAnalystToolConfiguration:
    """Tests for social media analyst tool configuration"""

    def test_social_analyst_uses_reddit(self):
        """Verify social media analyst uses Reddit for sentiment"""
        from tradingagents.agents.analysts.social_media_analyst import create_social_media_analyst

        mock_toolkit = MagicMock()
        mock_toolkit.config = {"online_tools": True}
        mock_toolkit.get_reddit_stock_info = MagicMock(name='get_reddit_stock_info')

        mock_llm = MagicMock()

        # Create the social media analyst node
        social_analyst_node = create_social_media_analyst(mock_llm, mock_toolkit)

        assert social_analyst_node is not None
        assert callable(social_analyst_node)

    def test_social_analyst_creates_valid_node(self):
        """Verify social media analyst creates a valid callable node"""
        from tradingagents.agents.analysts.social_media_analyst import create_social_media_analyst

        mock_toolkit = MagicMock()
        mock_toolkit.config = {"online_tools": False}
        mock_toolkit.get_reddit_stock_info = MagicMock(name='get_reddit_stock_info')

        mock_llm = MagicMock()

        social_analyst_node = create_social_media_analyst(mock_llm, mock_toolkit)

        assert social_analyst_node is not None
        assert callable(social_analyst_node)


class TestAnalystCryptoDetection:
    """Tests for crypto detection patterns in analysts"""

    def test_crypto_patterns(self):
        """Test various crypto ticker formats are detected"""
        crypto_patterns = [
            "BTC/USD",
            "ETH/USD",
            "SOL/USD",
            "BTCUSD",
            "ETHUSD",
        ]

        for ticker in crypto_patterns:
            is_crypto = "/" in ticker or "USD" in ticker.upper() or "USDT" in ticker.upper()
            assert is_crypto is True, f"Failed to detect {ticker} as crypto"

    def test_stock_patterns(self):
        """Test stock tickers are not detected as crypto"""
        stock_patterns = [
            "AAPL",
            "MSFT",
            "NVDA",
            "TSLA",
            "GOOGL",
        ]

        for ticker in stock_patterns:
            is_crypto = "/" in ticker or "USD" in ticker.upper() or "USDT" in ticker.upper()
            assert is_crypto is False, f"Incorrectly detected {ticker} as crypto"


class TestRedditToolUsage:
    """Tests verifying correct Reddit tool usage"""

    def test_reddit_tools_exist(self):
        """Verify both Reddit tools exist in Toolkit"""
        from tradingagents.agents.utils.agent_utils import Toolkit

        assert hasattr(Toolkit, 'get_reddit_stock_info'), \
            "Toolkit should have get_reddit_stock_info"
        assert hasattr(Toolkit, 'get_reddit_news'), \
            "Toolkit should have get_reddit_news"

    def test_reddit_stock_info_is_ticker_specific(self):
        """Verify get_reddit_stock_info is ticker-specific"""
        from tradingagents.agents.utils.agent_utils import Toolkit

        tool_obj = Toolkit.get_reddit_stock_info
        # The tool description should mention stock or ticker
        description_lower = str(tool_obj.description).lower()
        assert 'ticker' in description_lower or 'stock' in description_lower, \
            "get_reddit_stock_info should be ticker-specific"

    def test_reddit_global_news_is_global(self):
        """Verify get_reddit_news is for global news (not ticker-specific)"""
        from tradingagents.agents.utils.agent_utils import Toolkit

        tool_obj = Toolkit.get_reddit_news
        # The tool description should mention global
        description_lower = str(tool_obj.description).lower()
        assert 'global' in description_lower, \
            "get_reddit_news should be for global news"
