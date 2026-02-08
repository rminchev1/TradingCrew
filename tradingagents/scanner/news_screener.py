"""
News Screener - Analyzes news sentiment for stocks
"""

import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .cache import cached

try:
    from tradingagents.dataflows.finnhub_utils import FinnhubDataFetcher
except ImportError:
    FinnhubDataFetcher = None

try:
    from tradingagents.dataflows.googlenews_utils import getNewsData
except ImportError:
    getNewsData = None

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None


# Simple sentiment keywords (fallback)
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
    Simple keyword-based sentiment analysis (fallback).

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


@cached(ttl_seconds=1800)  # Cache LLM responses for 30 minutes
def analyze_sentiment_llm(headline: str, symbol: str = "") -> Dict[str, Any]:
    """
    Use GPT-4o-mini for accurate news sentiment analysis.

    Args:
        headline: News headline to analyze
        symbol: Optional stock symbol for context

    Returns:
        Dict with sentiment, confidence, and reasoning
    """
    if not OPENAI_AVAILABLE:
        return {
            "sentiment": analyze_sentiment(headline),
            "confidence": 0.5,
            "reasoning": "Keyword-based (LLM unavailable)",
            "llm_used": False,
        }

    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return {
                "sentiment": analyze_sentiment(headline),
                "confidence": 0.5,
                "reasoning": "Keyword-based (no API key)",
                "llm_used": False,
            }

        client = OpenAI(api_key=api_key)

        prompt = f"""Analyze the sentiment of this financial news headline for stock trading purposes.

Headline: "{headline}"
{f"Stock: {symbol}" if symbol else ""}

Respond with ONLY a JSON object (no markdown, no explanation):
{{"sentiment": "bullish" or "bearish" or "neutral", "confidence": 0.0-1.0, "reasoning": "brief 5-10 word explanation"}}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.1,
        )

        result_text = response.choices[0].message.content.strip()

        # Parse JSON response
        import json
        # Handle potential markdown code blocks
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()

        result = json.loads(result_text)

        return {
            "sentiment": result.get("sentiment", "neutral"),
            "confidence": result.get("confidence", 0.7),
            "reasoning": result.get("reasoning", ""),
            "llm_used": True,
        }

    except Exception as e:
        print(f"[NEWS_LLM] Error analyzing sentiment: {e}")
        return {
            "sentiment": analyze_sentiment(headline),
            "confidence": 0.5,
            "reasoning": f"Keyword-based (LLM error: {str(e)[:30]})",
            "llm_used": False,
        }


def get_news_for_symbol(
    symbol: str,
    days: int = 2,
    use_llm: bool = False,
) -> List[Dict[str, Any]]:
    """
    Get recent news for a symbol from available sources.

    Args:
        symbol: Stock ticker symbol
        days: Number of days to look back
        use_llm: Whether to use LLM for sentiment analysis

    Returns:
        List of news items with title, source, and sentiment
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
                    if use_llm:
                        sentiment_result = analyze_sentiment_llm(title, symbol)
                        sentiment = sentiment_result["sentiment"]
                    else:
                        sentiment = analyze_sentiment(title)

                    news_items.append({
                        "title": title,
                        "source": item.get("source", "Finnhub"),
                        "sentiment": sentiment,
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
                        if use_llm:
                            sentiment_result = analyze_sentiment_llm(title, symbol)
                            sentiment = sentiment_result["sentiment"]
                        else:
                            sentiment = analyze_sentiment(title)

                        news_items.append({
                            "title": title,
                            "source": item.get("source", "Google News"),
                            "sentiment": sentiment,
                            "datetime": item.get("date", ""),
                        })
        except Exception as e:
            print(f"[NEWS] Google News error for {symbol}: {e}")

    return news_items


def score_news(symbol: str, use_llm: bool = False) -> Dict[str, Any]:
    """
    Calculate news score for a symbol.

    Args:
        symbol: Stock ticker symbol
        use_llm: Whether to use LLM for sentiment analysis

    Returns dict with:
        - news_sentiment: overall sentiment
        - news_count: number of recent news items
        - news_score: 0-100
        - news_items: list of news items
    """
    try:
        news_items = get_news_for_symbol(symbol, use_llm=use_llm)

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
            score = 50 + int(sentiment_ratio * 40)  # Can swing +/-40 points
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


def batch_score_news(symbols: list, use_llm: bool = False) -> Dict[str, Dict[str, Any]]:
    """Score news for multiple symbols."""
    results = {}
    for symbol in symbols:
        results[symbol] = score_news(symbol, use_llm=use_llm)
    return results
