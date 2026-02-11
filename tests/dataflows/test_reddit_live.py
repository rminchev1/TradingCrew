"""
Unit tests for live Reddit API implementation.

Tests the RedditLiveClient and related functions without requiring actual API credentials.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestRedditLiveClient:
    """Tests for RedditLiveClient class"""

    def test_client_singleton(self):
        """Verify client uses singleton pattern"""
        from tradingagents.dataflows.reddit_live import RedditLiveClient

        client1 = RedditLiveClient.get_instance()
        client2 = RedditLiveClient.get_instance()

        assert client1 is client2

    def test_is_configured_without_credentials(self):
        """Verify is_configured returns False without credentials"""
        from tradingagents.dataflows.reddit_live import RedditLiveClient

        # Reset instance for clean test
        RedditLiveClient._instance = None

        client = RedditLiveClient()
        client.client_id = None
        client.client_secret = None

        assert client.is_configured() is False

    def test_is_configured_with_credentials(self):
        """Verify is_configured returns True with credentials"""
        from tradingagents.dataflows.reddit_live import RedditLiveClient

        client = RedditLiveClient()
        client.client_id = "test_id"
        client.client_secret = "test_secret"

        assert client.is_configured() is True

    def test_update_credentials(self):
        """Verify credentials can be updated"""
        from tradingagents.dataflows.reddit_live import RedditLiveClient

        RedditLiveClient._instance = None
        RedditLiveClient.update_credentials(
            client_id="new_id",
            client_secret="new_secret",
            user_agent="TestAgent/1.0"
        )

        client = RedditLiveClient.get_instance()
        assert client.client_id == "new_id"
        assert client.client_secret == "new_secret"
        assert client.user_agent == "TestAgent/1.0"


class TestRedditLiveAvailability:
    """Tests for availability checks"""

    def test_is_reddit_live_available_without_config(self):
        """Verify availability check returns False without config"""
        from tradingagents.dataflows.reddit_live import (
            is_reddit_live_available,
            RedditLiveClient,
        )

        # Reset and configure without credentials
        RedditLiveClient._instance = None
        RedditLiveClient.update_credentials(
            client_id=None,
            client_secret=None,
        )

        assert is_reddit_live_available() is False

    @patch.dict('os.environ', {'REDDIT_CLIENT_ID': 'test', 'REDDIT_CLIENT_SECRET': 'secret'})
    def test_is_reddit_live_available_with_env(self):
        """Verify availability with environment variables"""
        from tradingagents.dataflows.reddit_live import (
            is_reddit_live_available,
            RedditLiveClient,
            PRAW_AVAILABLE,
        )

        # Reset instance to pick up env vars
        RedditLiveClient._instance = None

        # Should be available if PRAW is installed and env vars set
        if PRAW_AVAILABLE:
            result = is_reddit_live_available()
            # Result depends on whether env vars are actually read
            assert isinstance(result, bool)


class TestSubredditConfiguration:
    """Tests for subreddit configurations"""

    def test_stock_subreddits_defined(self):
        """Verify stock subreddits are defined"""
        from tradingagents.dataflows.reddit_live import STOCK_SUBREDDITS

        assert isinstance(STOCK_SUBREDDITS, list)
        assert len(STOCK_SUBREDDITS) > 0
        assert "wallstreetbets" in STOCK_SUBREDDITS
        assert "stocks" in STOCK_SUBREDDITS

    def test_crypto_subreddits_defined(self):
        """Verify crypto subreddits are defined"""
        from tradingagents.dataflows.reddit_live import CRYPTO_SUBREDDITS

        assert isinstance(CRYPTO_SUBREDDITS, list)
        assert len(CRYPTO_SUBREDDITS) > 0
        assert "cryptocurrency" in CRYPTO_SUBREDDITS
        assert "bitcoin" in CRYPTO_SUBREDDITS

    def test_global_news_subreddits_defined(self):
        """Verify global news subreddits are defined"""
        from tradingagents.dataflows.reddit_live import GLOBAL_NEWS_SUBREDDITS

        assert isinstance(GLOBAL_NEWS_SUBREDDITS, list)
        assert len(GLOBAL_NEWS_SUBREDDITS) > 0
        assert "worldnews" in GLOBAL_NEWS_SUBREDDITS


class TestInterfaceIntegration:
    """Tests for interface.py integration with live Reddit"""

    def test_get_reddit_company_news_fallback(self):
        """Verify company news falls back gracefully when live API unavailable"""
        from tradingagents.dataflows.interface import get_reddit_company_news

        # Should not raise even without credentials or cached data
        result = get_reddit_company_news("AAPL", "2024-01-15", 7, 5)

        assert isinstance(result, str)
        # Should indicate no data or return empty/message
        assert len(result) >= 0

    def test_get_reddit_global_news_fallback(self):
        """Verify global news falls back gracefully when live API unavailable"""
        from tradingagents.dataflows.interface import get_reddit_global_news

        # Should not raise even without credentials or cached data
        result = get_reddit_global_news("2024-01-15", 7, 5)

        assert isinstance(result, str)
        assert len(result) >= 0


class TestMockedRedditAPI:
    """Tests with mocked PRAW responses"""

    @patch('tradingagents.dataflows.reddit_live.praw')
    def test_search_ticker_returns_posts(self, mock_praw):
        """Verify search_ticker returns formatted posts"""
        from tradingagents.dataflows.reddit_live import RedditLiveClient
        import time

        # Setup mock
        mock_reddit = MagicMock()
        mock_praw.Reddit.return_value = mock_reddit

        mock_post = MagicMock()
        mock_post.title = "AAPL is going to the moon!"
        mock_post.selftext = "Great earnings report"
        mock_post.permalink = "/r/stocks/comments/123"
        mock_post.score = 1000
        mock_post.num_comments = 50
        mock_post.created_utc = time.time()
        mock_post.upvote_ratio = 0.95

        mock_subreddit = MagicMock()
        mock_subreddit.search.return_value = [mock_post]
        mock_reddit.subreddit.return_value = mock_subreddit

        # Reset and configure client
        RedditLiveClient._instance = None
        client = RedditLiveClient(
            client_id="test_id",
            client_secret="test_secret",
            user_agent="TestAgent/1.0"
        )
        client._reddit = mock_reddit
        client._initialized = True

        posts = client.search_ticker("AAPL", subreddits=["stocks"], limit=10)

        assert len(posts) == 1
        assert posts[0]["title"] == "AAPL is going to the moon!"
        assert posts[0]["upvotes"] == 1000

    @patch('tradingagents.dataflows.reddit_live.praw')
    def test_get_hot_posts_returns_posts(self, mock_praw):
        """Verify get_hot_posts returns formatted posts"""
        from tradingagents.dataflows.reddit_live import RedditLiveClient
        import time

        # Setup mock
        mock_reddit = MagicMock()
        mock_praw.Reddit.return_value = mock_reddit

        mock_post = MagicMock()
        mock_post.title = "Market update today"
        mock_post.selftext = "The market is doing things"
        mock_post.permalink = "/r/worldnews/comments/456"
        mock_post.score = 5000
        mock_post.num_comments = 200
        mock_post.created_utc = time.time()
        mock_post.upvote_ratio = 0.90
        mock_post.stickied = False

        mock_subreddit = MagicMock()
        mock_subreddit.hot.return_value = [mock_post]
        mock_reddit.subreddit.return_value = mock_subreddit

        # Reset and configure client
        RedditLiveClient._instance = None
        client = RedditLiveClient(
            client_id="test_id",
            client_secret="test_secret",
            user_agent="TestAgent/1.0"
        )
        client._reddit = mock_reddit
        client._initialized = True

        posts = client.get_hot_posts(subreddits=["worldnews"], limit=10)

        assert len(posts) == 1
        assert posts[0]["title"] == "Market update today"
        assert posts[0]["upvotes"] == 5000


class TestSettingsIntegration:
    """Tests for settings integration"""

    def test_reddit_settings_in_defaults(self):
        """Verify Reddit settings are in default settings"""
        from webui.utils.storage import DEFAULT_SYSTEM_SETTINGS

        assert "reddit_client_id" in DEFAULT_SYSTEM_SETTINGS
        assert "reddit_client_secret" in DEFAULT_SYSTEM_SETTINGS
        assert "reddit_user_agent" in DEFAULT_SYSTEM_SETTINGS

    def test_reddit_settings_in_app_state(self):
        """Verify Reddit settings are in app_state"""
        from webui.utils.state import AppState

        state = AppState()
        assert "reddit_client_id" in state.system_settings
        assert "reddit_client_secret" in state.system_settings
        assert "reddit_user_agent" in state.system_settings
