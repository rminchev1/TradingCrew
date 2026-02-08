"""
Market Scanner Module

Scans US stock market for trading opportunities based on
momentum/technical indicators, news catalysts, and options flow.
"""

from .market_scanner import MarketScanner, run_scan
from .scanner_result import ScannerResult
from .cache import cached, clear_cache, clear_expired, get_cache_stats, invalidate
from .universe_fetcher import (
    get_dynamic_universe,
    get_sector_universe,
    get_all_sectors,
    get_combined_universe,
    SECTOR_UNIVERSES,
    DEFAULT_UNIVERSE,
)
from .options_screener import (
    screen_options_flow,
    batch_screen_options,
    get_options_summary,
)
from .movers_fetcher import (
    get_top_movers,
    get_gainers,
    get_losers,
    get_volume_leaders,
    STOCK_UNIVERSE,
)
from .technical_screener import score_technical, batch_score_technical
from .news_screener import score_news, batch_score_news, analyze_sentiment_llm

__all__ = [
    # Main scanner
    "MarketScanner",
    "run_scan",
    "ScannerResult",
    # Caching
    "cached",
    "clear_cache",
    "clear_expired",
    "get_cache_stats",
    "invalidate",
    # Universe
    "get_dynamic_universe",
    "get_sector_universe",
    "get_all_sectors",
    "get_combined_universe",
    "SECTOR_UNIVERSES",
    "DEFAULT_UNIVERSE",
    "STOCK_UNIVERSE",
    # Options
    "screen_options_flow",
    "batch_screen_options",
    "get_options_summary",
    # Movers
    "get_top_movers",
    "get_gainers",
    "get_losers",
    "get_volume_leaders",
    # Technical
    "score_technical",
    "batch_score_technical",
    # News
    "score_news",
    "batch_score_news",
    "analyze_sentiment_llm",
]
