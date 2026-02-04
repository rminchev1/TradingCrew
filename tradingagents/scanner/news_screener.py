"""
News Screener - Analyzes news sentiment for stocks
"""

import os
import sys
from typing import Dict, Any, List
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from tradingagents.dataflows.finnhub_utils import FinnhubDataFetcher
except ImportError:
    FinnhubDataFetcher = None

try:
    from tradingagents.dataflows.googlenews_utils import getNewsData
except ImportError:
    getNewsData = None


# Simple sentiment keywords
BULLISH_KEYWORDS = [
    "surge", "soar", "jump", "rally", "gain", "beat", "exceed", "upgrade",
    "buy", "outperform", "bullish", "growth", "profit", "record", "high",
    "strong", "positive", "success", "breakthrough", "innovation", "partnership",
    "acquisition", "expand", "revenue", "earnings beat", "raised guidance"
]

BEARISH_KEYWORDS = [
    "fall", "drop", "decline", "plunge", "crash", "miss", "downgrade",
    "sell", "underperform", "bearish", "loss", "cut", "layoff", "warning",
    "weak", "negative", "fail", "lawsuit", "investigation", "recall",
    "debt", "bankruptcy", "fraud", "concern", "risk", "lowered guidance"
]


def analyze_sentiment(text: str) -> str:
    """
    Simple keyword-based sentiment analysis.

    Returns: "bullish", "bearish", or "neutral"
    """
    if not text:
        return "neutral"

    text_lower = text.lower()

    bullish_count = sum(1 for kw in BULLISH_KEYWORDS if kw in text_lower)
    bearish_count = sum(1 for kw in BEARISH_KEYWORDS if kw in text_lower)

    if bullish_count > bearish_count + 1:
        return "bullish"
    elif bearish_count > bullish_count + 1:
        return "bearish"
    else:
        return "neutral"


def get_news_for_symbol(symbol: str, days: int = 2) -> List[Dict[str, Any]]:
    """
    Get recent news for a symbol from available sources.

    Returns list of news items with title, source, and sentiment.
    """
    news_items = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Try Finnhub first
    if FinnhubDataFetcher:
        try:
            fetcher = FinnhubDataFetcher()
            finnhub_news = fetcher.get_company_news(
                symbol,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )
            if finnhub_news:
                for item in finnhub_news[:10]:  # Limit to 10 items
                    title = item.get("headline", "")
                    news_items.append({
                        "title": title,
                        "source": item.get("source", "Finnhub"),
                        "sentiment": analyze_sentiment(title),
                        "datetime": item.get("datetime", ""),
                    })
        except Exception as e:
            print(f"[NEWS] Finnhub error for {symbol}: {e}")

    # Try Google News as fallback/supplement
    if getNewsData and len(news_items) < 5:
        try:
            google_news = getNewsData(
                symbol,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                max_pages=1
            )
            if google_news:
                for item in google_news[:5]:
                    title = item.get("title", "")
                    if title and not any(n["title"] == title for n in news_items):
                        news_items.append({
                            "title": title,
                            "source": item.get("source", "Google News"),
                            "sentiment": analyze_sentiment(title),
                            "datetime": item.get("date", ""),
                        })
        except Exception as e:
            print(f"[NEWS] Google News error for {symbol}: {e}")

    return news_items


def score_news(symbol: str) -> Dict[str, Any]:
    """
    Calculate news score for a symbol.

    Returns dict with:
        - news_sentiment: overall sentiment
        - news_count: number of recent news items
        - news_score: 0-100
        - news_items: list of news items
    """
    try:
        news_items = get_news_for_symbol(symbol)

        if not news_items:
            return {
                "news_sentiment": "neutral",
                "news_count": 0,
                "news_score": 50,
                "news_items": [],
            }

        # Count sentiments
        bullish_count = sum(1 for n in news_items if n["sentiment"] == "bullish")
        bearish_count = sum(1 for n in news_items if n["sentiment"] == "bearish")
        neutral_count = len(news_items) - bullish_count - bearish_count

        # Determine overall sentiment
        if bullish_count > bearish_count + 1:
            overall_sentiment = "bullish"
        elif bearish_count > bullish_count + 1:
            overall_sentiment = "bearish"
        else:
            overall_sentiment = "neutral"

        # Calculate news score (0-100)
        # Base score is 50, adjusted by sentiment ratio
        total = len(news_items)
        if total > 0:
            sentiment_ratio = (bullish_count - bearish_count) / total
            score = 50 + int(sentiment_ratio * 40)  # Can swing ±40 points
        else:
            score = 50

        # Bonus for high news volume (market attention)
        if total >= 5:
            score += 5
        elif total >= 10:
            score += 10

        # Clamp score
        score = max(0, min(100, score))

        return {
            "news_sentiment": overall_sentiment,
            "news_count": len(news_items),
            "news_score": score,
            "news_items": news_items[:5],  # Return top 5 for display
        }

    except Exception as e:
        print(f"[NEWS] Error scoring {symbol}: {e}")
        return {
            "news_sentiment": "neutral",
            "news_count": 0,
            "news_score": 50,
            "news_items": [],
        }


def batch_score_news(symbols: list) -> Dict[str, Dict[str, Any]]:
    """Score news for multiple symbols."""
    results = {}
    for symbol in symbols:
        results[symbol] = score_news(symbol)
    return results
