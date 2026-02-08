"""
Options Screener - Options flow screening for scanner
"""

import os
import sys
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .cache import cached

try:
    from tradingagents.dataflows.options_utils import (
        get_options_chain,
        calculate_put_call_ratio,
        calculate_iv_metrics,
        detect_unusual_activity,
        get_current_price,
    )
    OPTIONS_AVAILABLE = True
except ImportError:
    OPTIONS_AVAILABLE = False


@cached(ttl_seconds=600)  # Cache for 10 minutes
def screen_options_flow(symbol: str) -> Dict[str, Any]:
    """
    Analyze options flow for a single stock and return a screening score.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Dict with:
            - options_score: 0-100 score based on options flow
            - signal: "bullish", "bearish", or "neutral"
            - put_call_ratio: P/C volume ratio
            - iv_percentile: ATM IV (as proxy for IV rank)
            - has_unusual_activity: bool
            - details: Additional metrics
    """
    if not OPTIONS_AVAILABLE:
        return _default_options_result()

    try:
        # Get current price
        current_price = get_current_price(symbol)
        if current_price == 0:
            return _default_options_result()

        # Get options chain
        calls, puts, expirations = get_options_chain(symbol)
        if calls is None or puts is None or len(expirations) == 0:
            return _default_options_result()

        # Calculate metrics
        pc_ratio = calculate_put_call_ratio(calls, puts)
        iv_metrics = calculate_iv_metrics(calls, puts, current_price)
        unusual = detect_unusual_activity(calls, puts)

        # Calculate options score (0-100)
        score = 50  # Start neutral

        # Put/Call ratio scoring (-25 to +25)
        volume_ratio = pc_ratio.get('volume_ratio', 1.0)
        if volume_ratio < 0.5:
            score += 25  # Very bullish
        elif volume_ratio < 0.7:
            score += 15  # Bullish
        elif volume_ratio < 0.9:
            score += 5  # Slightly bullish
        elif volume_ratio > 1.5:
            score -= 25  # Very bearish
        elif volume_ratio > 1.3:
            score -= 15  # Bearish
        elif volume_ratio > 1.1:
            score -= 5  # Slightly bearish

        # IV skew scoring (-15 to +15)
        iv_skew = iv_metrics.get('iv_skew', 0)
        if iv_skew < -5:
            score += 15  # Calls expensive - bullish speculation
        elif iv_skew < -2:
            score += 8
        elif iv_skew > 5:
            score -= 10  # Puts expensive - hedging/fear
        elif iv_skew > 2:
            score -= 5

        # Unusual activity scoring (-10 to +10)
        if unusual.get('has_unusual_activity'):
            activity_bias = unusual.get('activity_bias', '')
            if 'Bullish' in activity_bias:
                score += 10
            elif 'Bearish' in activity_bias:
                score -= 10

        # Clamp score to 0-100
        score = max(0, min(100, score))

        # Determine signal
        if score >= 65:
            signal = "bullish"
        elif score <= 35:
            signal = "bearish"
        else:
            signal = "neutral"

        return {
            "options_score": score,
            "signal": signal,
            "put_call_ratio": volume_ratio,
            "iv_percentile": iv_metrics.get('atm_iv', 0),
            "has_unusual_activity": unusual.get('has_unusual_activity', False),
            "details": {
                "volume_sentiment": pc_ratio.get('volume_sentiment', 'Unknown'),
                "iv_skew": iv_metrics.get('iv_skew', 0),
                "skew_interpretation": iv_metrics.get('skew_interpretation', ''),
                "activity_bias": unusual.get('activity_bias', ''),
                "expected_move_pct": iv_metrics.get('expected_move_pct', 0),
                "total_call_volume": pc_ratio.get('total_call_volume', 0),
                "total_put_volume": pc_ratio.get('total_put_volume', 0),
            }
        }

    except Exception as e:
        print(f"[OPTIONS_SCREENER] Error screening {symbol}: {e}")
        return _default_options_result()


def _default_options_result() -> Dict[str, Any]:
    """Return default options result when data unavailable."""
    return {
        "options_score": 50,
        "signal": "neutral",
        "put_call_ratio": 1.0,
        "iv_percentile": 0,
        "has_unusual_activity": False,
        "details": {},
    }


def batch_screen_options(
    symbols: List[str],
    max_workers: int = 3
) -> Dict[str, Dict[str, Any]]:
    """
    Screen options flow for multiple symbols in parallel.

    Args:
        symbols: List of ticker symbols
        max_workers: Number of parallel threads

    Returns:
        Dict mapping symbol to options screening result
    """
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(screen_options_flow, sym): sym for sym in symbols}

        for future in as_completed(futures):
            symbol = futures[future]
            try:
                results[symbol] = future.result()
            except Exception as e:
                print(f"[OPTIONS_SCREENER] Error in batch for {symbol}: {e}")
                results[symbol] = _default_options_result()

    return results


def get_options_summary(symbol: str) -> str:
    """
    Get a human-readable options flow summary for a symbol.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Formatted string summary
    """
    result = screen_options_flow(symbol)

    if result["options_score"] == 50 and not result.get("details"):
        return f"{symbol}: No options data available"

    details = result.get("details", {})
    summary_parts = [
        f"{symbol} Options Flow:",
        f"  Score: {result['options_score']}/100 ({result['signal'].upper()})",
        f"  P/C Ratio: {result['put_call_ratio']:.2f} ({details.get('volume_sentiment', 'N/A')})",
        f"  ATM IV: {result['iv_percentile']:.1f}%",
    ]

    if result['has_unusual_activity']:
        summary_parts.append(f"  Unusual Activity: {details.get('activity_bias', 'Yes')}")

    if details.get('expected_move_pct'):
        summary_parts.append(f"  Expected Move: +/-{details['expected_move_pct']:.1f}%")

    return "\n".join(summary_parts)
