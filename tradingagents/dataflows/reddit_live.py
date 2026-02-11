"""
Live Reddit API implementation using PRAW.

Fetches real-time Reddit data for sentiment analysis instead of relying on cached JSONL files.
"""

import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from .external_data_logger import log_api_error

# Try to import praw
try:
    import praw
    from praw.exceptions import RedditAPIException
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False
    praw = None
    RedditAPIException = Exception


# Default subreddits for different asset types
STOCK_SUBREDDITS = [
    "wallstreetbets",
    "stocks",
    "investing",
    "stockmarket",
    "options",
]

CRYPTO_SUBREDDITS = [
    "cryptocurrency",
    "bitcoin",
    "ethereum",
    "CryptoMarkets",
    "altcoin",
]

GLOBAL_NEWS_SUBREDDITS = [
    "worldnews",
    "news",
    "economics",
    "finance",
]


class RedditLiveClient:
    """Client for fetching live Reddit data using PRAW."""

    _instance: Optional['RedditLiveClient'] = None
    _reddit: Optional[Any] = None

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """
        Initialize the Reddit client.

        Args:
            client_id: Reddit API client ID (or from env REDDIT_CLIENT_ID)
            client_secret: Reddit API client secret (or from env REDDIT_CLIENT_SECRET)
            user_agent: User agent string (or from env REDDIT_USER_AGENT)
        """
        self.client_id = client_id or os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("REDDIT_CLIENT_SECRET")
        self.user_agent = user_agent or os.getenv("REDDIT_USER_AGENT", "TradingCrew/1.0")
        self._reddit = None
        self._initialized = False
        self._last_error = None

    @classmethod
    def get_instance(cls) -> 'RedditLiveClient':
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def update_credentials(
        cls,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Update credentials and reinitialize client."""
        instance = cls.get_instance()
        if client_id:
            instance.client_id = client_id
        if client_secret:
            instance.client_secret = client_secret
        if user_agent:
            instance.user_agent = user_agent
        instance._reddit = None
        instance._initialized = False
        instance._last_error = None

    def is_configured(self) -> bool:
        """Check if Reddit API credentials are configured."""
        return bool(self.client_id and self.client_secret)

    def _initialize(self) -> bool:
        """Initialize the PRAW Reddit instance."""
        if not PRAW_AVAILABLE:
            self._last_error = "PRAW library not installed. Run: pip install praw"
            return False

        if not self.is_configured():
            self._last_error = "Reddit API credentials not configured"
            return False

        if self._initialized and self._reddit:
            return True

        try:
            self._reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
            )
            # Test the connection by accessing a simple attribute
            _ = self._reddit.read_only
            self._initialized = True
            self._last_error = None
            print("[REDDIT] Successfully initialized live Reddit API connection")
            return True
        except Exception as e:
            self._last_error = f"Failed to initialize Reddit API: {str(e)}"
            log_api_error("Reddit", self._last_error)
            print(f"[REDDIT] {self._last_error}")
            return False

    def get_last_error(self) -> Optional[str]:
        """Get the last error message."""
        return self._last_error

    def search_ticker(
        self,
        ticker: str,
        subreddits: Optional[List[str]] = None,
        limit: int = 25,
        time_filter: str = "week",
    ) -> List[Dict]:
        """
        Search Reddit for posts mentioning a ticker.

        Args:
            ticker: Stock/crypto ticker symbol (e.g., "AAPL", "BTC")
            subreddits: List of subreddits to search (defaults based on asset type)
            limit: Maximum posts per subreddit
            time_filter: Time filter ("hour", "day", "week", "month", "year", "all")

        Returns:
            List of post dictionaries with title, content, score, etc.
        """
        if not self._initialize():
            return []

        # Determine asset type and default subreddits
        is_crypto = "/" in ticker or "USD" in ticker.upper() or "BTC" in ticker.upper() or "ETH" in ticker.upper()

        if subreddits is None:
            subreddits = CRYPTO_SUBREDDITS if is_crypto else STOCK_SUBREDDITS

        # Clean ticker for search (remove /USD suffix for crypto)
        search_ticker = ticker.split("/")[0] if "/" in ticker else ticker

        posts = []

        for subreddit_name in subreddits:
            try:
                subreddit = self._reddit.subreddit(subreddit_name)

                # Search for ticker mentions
                search_results = subreddit.search(
                    search_ticker,
                    limit=limit,
                    time_filter=time_filter,
                    sort="relevance"
                )

                for post in search_results:
                    # Convert UTC timestamp to date string
                    post_date = datetime.utcfromtimestamp(post.created_utc).strftime("%Y-%m-%d")

                    posts.append({
                        "title": post.title,
                        "content": post.selftext[:1000] if post.selftext else "",  # Limit content length
                        "url": f"https://reddit.com{post.permalink}",
                        "upvotes": post.score,
                        "num_comments": post.num_comments,
                        "posted_date": post_date,
                        "subreddit": subreddit_name,
                        "upvote_ratio": post.upvote_ratio,
                    })

            except RedditAPIException as e:
                print(f"[REDDIT] API error searching r/{subreddit_name}: {e}")
                continue
            except Exception as e:
                print(f"[REDDIT] Error searching r/{subreddit_name}: {e}")
                continue

        # Sort by upvotes (most popular first)
        posts.sort(key=lambda x: x["upvotes"], reverse=True)

        return posts

    def get_hot_posts(
        self,
        subreddits: Optional[List[str]] = None,
        limit: int = 10,
        is_crypto: bool = False,
    ) -> List[Dict]:
        """
        Get hot posts from specified subreddits (global news).

        Args:
            subreddits: List of subreddits (defaults to news subreddits)
            limit: Maximum posts per subreddit
            is_crypto: If True, use crypto subreddits as default

        Returns:
            List of post dictionaries
        """
        if not self._initialize():
            return []

        if subreddits is None:
            if is_crypto:
                subreddits = CRYPTO_SUBREDDITS
            else:
                subreddits = GLOBAL_NEWS_SUBREDDITS

        posts = []

        for subreddit_name in subreddits:
            try:
                subreddit = self._reddit.subreddit(subreddit_name)

                for post in subreddit.hot(limit=limit):
                    # Skip stickied posts
                    if post.stickied:
                        continue

                    post_date = datetime.utcfromtimestamp(post.created_utc).strftime("%Y-%m-%d")

                    posts.append({
                        "title": post.title,
                        "content": post.selftext[:1000] if post.selftext else "",
                        "url": f"https://reddit.com{post.permalink}",
                        "upvotes": post.score,
                        "num_comments": post.num_comments,
                        "posted_date": post_date,
                        "subreddit": subreddit_name,
                        "upvote_ratio": post.upvote_ratio,
                    })

            except Exception as e:
                print(f"[REDDIT] Error getting hot posts from r/{subreddit_name}: {e}")
                continue

        # Sort by upvotes
        posts.sort(key=lambda x: x["upvotes"], reverse=True)

        return posts

    def test_connection(self) -> tuple[bool, str]:
        """
        Test the Reddit API connection.

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not PRAW_AVAILABLE:
            return False, "PRAW library not installed"

        if not self.is_configured():
            return False, "Reddit API credentials not configured"

        try:
            if not self._initialize():
                return False, self._last_error or "Failed to initialize"

            # Try to access a subreddit to verify connection
            subreddit = self._reddit.subreddit("stocks")
            # Just access the display_name to verify it works
            _ = subreddit.display_name

            return True, "Reddit API connection successful"

        except Exception as e:
            return False, f"Connection test failed: {str(e)}"


def get_reddit_live_client() -> RedditLiveClient:
    """Get the singleton Reddit client instance."""
    return RedditLiveClient.get_instance()


def is_reddit_live_available() -> bool:
    """Check if live Reddit API is available and configured."""
    client = get_reddit_live_client()
    return PRAW_AVAILABLE and client.is_configured()


def fetch_live_company_news(
    ticker: str,
    limit: int = 25,
    time_filter: str = "week",
) -> List[Dict]:
    """
    Fetch live Reddit posts about a specific ticker.

    Args:
        ticker: Stock/crypto ticker symbol
        limit: Maximum posts to return
        time_filter: Time filter for search

    Returns:
        List of post dictionaries
    """
    client = get_reddit_live_client()
    return client.search_ticker(ticker, limit=limit, time_filter=time_filter)


def fetch_live_global_news(
    limit: int = 25,
    is_crypto: bool = False,
) -> List[Dict]:
    """
    Fetch live global news from Reddit.

    Args:
        limit: Maximum posts per subreddit
        is_crypto: Whether to fetch from crypto subreddits

    Returns:
        List of post dictionaries
    """
    client = get_reddit_live_client()
    return client.get_hot_posts(limit=limit, is_crypto=is_crypto)
