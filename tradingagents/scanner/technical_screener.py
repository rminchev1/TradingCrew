"""
Technical Screener - Calculates technical indicator scores using Alpaca API
"""

import os
import sys
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .cache import cached

try:
    from tradingagents.dataflows.alpaca_utils import AlpacaUtils
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    AlpacaUtils = None


def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """Calculate RSI for a price series."""
    if len(prices) < period + 1:
        return 50.0

    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    return round(rsi.iloc[-1], 2) if not pd.isna(rsi.iloc[-1]) else 50.0


def calculate_macd(prices: pd.Series) -> Tuple[float, float, str]:
    """
    Calculate MACD and signal.

    Returns:
        (macd_line, signal_line, signal_type)
    """
    if len(prices) < 26:
        return 0.0, 0.0, "neutral"

    exp12 = prices.ewm(span=12, adjust=False).mean()
    exp26 = prices.ewm(span=26, adjust=False).mean()
    macd_line = exp12 - exp26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()

    macd_val = macd_line.iloc[-1]
    signal_val = signal_line.iloc[-1]

    # Determine signal
    if macd_val > signal_val and macd_val > 0:
        signal_type = "bullish"
    elif macd_val < signal_val and macd_val < 0:
        signal_type = "bearish"
    else:
        signal_type = "neutral"

    return round(macd_val, 4), round(signal_val, 4), signal_type


def calculate_ma_position(prices: pd.Series, period: int) -> str:
    """Check if current price is above or below moving average."""
    if len(prices) < period:
        return "neutral"

    ma = prices.rolling(window=period).mean().iloc[-1]
    current = prices.iloc[-1]

    if pd.isna(ma):
        return "neutral"

    if current > ma * 1.02:  # 2% above
        return "above"
    elif current < ma * 0.98:  # 2% below
        return "below"
    else:
        return "neutral"


@cached(ttl_seconds=300)  # Cache for 5 minutes
def _fetch_historical_data(symbol: str, days: int = 365) -> pd.DataFrame:
    """
    Fetch historical data for technical analysis using Alpaca.

    Args:
        symbol: Stock ticker
        days: Number of days of history

    Returns:
        DataFrame with OHLCV data
    """
    if not ALPACA_AVAILABLE:
        return pd.DataFrame()

    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days + 10)  # Extra buffer

        df = AlpacaUtils.get_stock_data(
            symbol=symbol,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            timeframe="1Day"
        )

        return df

    except Exception as e:
        print(f"[TECHNICAL] Error fetching data for {symbol}: {e}")
        return pd.DataFrame()


def score_technical(symbol: str) -> Dict[str, Any]:
    """
    Calculate technical score for a symbol.

    Returns dict with:
        - rsi: RSI value
        - macd_signal: "bullish", "bearish", "neutral"
        - price_vs_50ma: "above", "below", "neutral"
        - price_vs_200ma: "above", "below", "neutral"
        - technical_score: 0-100
    """
    try:
        # Get 1 year of data for proper indicator calculation
        hist = _fetch_historical_data(symbol, days=365)

        if hist.empty or len(hist) < 50:
            return {
                "rsi": 50.0,
                "macd_signal": "neutral",
                "price_vs_50ma": "neutral",
                "price_vs_200ma": "neutral",
                "technical_score": 50,
            }

        # Handle different column name formats (Alpaca returns lowercase)
        close_col = 'close' if 'close' in hist.columns else 'Close'

        if close_col not in hist.columns:
            return {
                "rsi": 50.0,
                "macd_signal": "neutral",
                "price_vs_50ma": "neutral",
                "price_vs_200ma": "neutral",
                "technical_score": 50,
            }

        close = hist[close_col]

        # Calculate indicators
        rsi = calculate_rsi(close)
        _, _, macd_signal = calculate_macd(close)
        price_vs_50ma = calculate_ma_position(close, 50)
        price_vs_200ma = calculate_ma_position(close, 200) if len(close) >= 200 else "neutral"

        # Calculate technical score (0-100)
        score = 50  # Start neutral

        # RSI scoring (-20 to +20)
        if rsi < 30:  # Oversold - potential buy
            score += 15
        elif rsi < 40:
            score += 10
        elif rsi > 70:  # Overbought - caution
            score -= 10
        elif rsi > 60:
            score += 5  # Momentum

        # MACD scoring (-20 to +20)
        if macd_signal == "bullish":
            score += 20
        elif macd_signal == "bearish":
            score -= 15

        # MA scoring (-10 to +20)
        if price_vs_50ma == "above":
            score += 10
        elif price_vs_50ma == "below":
            score -= 5

        if price_vs_200ma == "above":
            score += 10
        elif price_vs_200ma == "below":
            score -= 5

        # Clamp score to 0-100
        score = max(0, min(100, score))

        return {
            "rsi": rsi,
            "macd_signal": macd_signal,
            "price_vs_50ma": price_vs_50ma,
            "price_vs_200ma": price_vs_200ma,
            "technical_score": score,
        }

    except Exception as e:
        print(f"[TECHNICAL] Error scoring {symbol}: {e}")
        return {
            "rsi": 50.0,
            "macd_signal": "neutral",
            "price_vs_50ma": "neutral",
            "price_vs_200ma": "neutral",
            "technical_score": 50,
        }


def batch_score_technical(symbols: list) -> Dict[str, Dict[str, Any]]:
    """Score multiple symbols efficiently."""
    results = {}
    for symbol in symbols:
        results[symbol] = score_technical(symbol)
    return results
