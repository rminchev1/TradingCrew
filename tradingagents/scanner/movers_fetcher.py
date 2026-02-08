"""
Movers Fetcher - Gets top movers using Alpaca API
"""

import os
import sys
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime, timedelta
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .cache import cached
from .universe_fetcher import DEFAULT_UNIVERSE, get_dynamic_universe

try:
    from tradingagents.dataflows.alpaca_utils import (
        AlpacaUtils,
        get_alpaca_trading_client,
        ticker_to_company_fallback,
    )
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    AlpacaUtils = None
    get_alpaca_trading_client = None
    ticker_to_company_fallback = {}


# Re-export for backwards compatibility
STOCK_UNIVERSE = DEFAULT_UNIVERSE


@cached(ttl_seconds=300)  # Cache for 5 minutes
def _fetch_stock_data(symbol: str, days: int = 5) -> pd.DataFrame:
    """
    Fetch historical data for a single stock using Alpaca.

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
        start_date = end_date - timedelta(days=days + 5)  # Extra buffer for weekends

        df = AlpacaUtils.get_stock_data(
            symbol=symbol,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            timeframe="1Day"
        )

        return df

    except Exception as e:
        print(f"[MOVERS] Error fetching data for {symbol}: {e}")
        return pd.DataFrame()


@cached(ttl_seconds=300)  # Cache for 5 minutes
def _get_company_info(symbol: str) -> Dict[str, Any]:
    """
    Get company info from Alpaca.

    Args:
        symbol: Stock ticker

    Returns:
        Dict with company name and sector
    """
    if not ALPACA_AVAILABLE:
        return {"name": symbol, "sector": "Unknown"}

    try:
        client = get_alpaca_trading_client()
        asset = client.get_asset(symbol)

        return {
            "name": asset.name if asset and asset.name else ticker_to_company_fallback.get(symbol, symbol),
            "sector": getattr(asset, 'sector', 'Unknown') if asset else "Unknown",
        }

    except Exception as e:
        return {
            "name": ticker_to_company_fallback.get(symbol, symbol),
            "sector": "Unknown"
        }


def get_top_movers(
    min_price: float = 5.0,
    min_volume: int = 500000,
    limit: int = 50,
    use_dynamic_universe: bool = False,
) -> List[Dict[str, Any]]:
    """
    Get top movers from the stock universe based on daily price change.

    Args:
        min_price: Minimum stock price filter
        min_volume: Minimum volume filter
        limit: Maximum number of stocks to return
        use_dynamic_universe: If True, fetch universe dynamically from Alpaca

    Returns:
        List of dicts with symbol and basic data
    """
    # Get stock universe
    if use_dynamic_universe:
        universe = get_dynamic_universe(max_symbols=200)
    else:
        universe = STOCK_UNIVERSE

    print(f"[SCANNER] Fetching data for {len(universe)} stocks using Alpaca...")

    results = []
    batch_size = 20
    processed = 0

    # Process in batches
    for i in range(0, len(universe), batch_size):
        batch = universe[i:i + batch_size]

        for symbol in batch:
            try:
                # Fetch historical data
                hist = _fetch_stock_data(symbol, days=5)

                if hist.empty or len(hist) < 2:
                    continue

                # Get latest and previous data
                # Handle different column name formats
                close_col = 'close' if 'close' in hist.columns else 'Close'
                volume_col = 'volume' if 'volume' in hist.columns else 'Volume'

                if close_col not in hist.columns or volume_col not in hist.columns:
                    continue

                latest = hist.iloc[-1]
                prev_close = hist.iloc[-2][close_col] if len(hist) >= 2 else latest[close_col]

                price = float(latest[close_col])
                volume = int(latest[volume_col])
                change_pct = ((price - prev_close) / prev_close) * 100 if prev_close > 0 else 0

                # Apply filters
                if price < min_price or volume < min_volume:
                    continue

                # Get company info
                info = _get_company_info(symbol)

                # Calculate average volume
                avg_volume = hist[volume_col].mean() if len(hist) > 0 else volume
                volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0

                # Get chart data (last 5 closes)
                chart_data = hist[close_col].tolist()[-5:]

                results.append({
                    "symbol": symbol,
                    "company_name": info.get("name", symbol),
                    "price": round(price, 2),
                    "change_percent": round(change_pct, 2),
                    "volume": volume,
                    "volume_ratio": round(volume_ratio, 2),
                    "sector": info.get("sector", "Unknown"),
                    "market_cap": None,  # Not available from Alpaca bars
                    "chart_data": chart_data,
                })

                processed += 1

            except Exception as e:
                print(f"[SCANNER] Error processing {symbol}: {e}")
                continue

        # Small delay between batches to be nice to API
        if i + batch_size < len(universe):
            time.sleep(0.2)

    # Sort by absolute change percentage (biggest movers first)
    results.sort(key=lambda x: abs(x["change_percent"]), reverse=True)

    print(f"[SCANNER] Found {len(results)} stocks after filtering")

    return results[:limit]


def get_gainers(movers: List[Dict], limit: int = 20) -> List[Dict]:
    """Get top gainers from movers list."""
    gainers = [m for m in movers if m["change_percent"] > 0]
    gainers.sort(key=lambda x: x["change_percent"], reverse=True)
    return gainers[:limit]


def get_losers(movers: List[Dict], limit: int = 20) -> List[Dict]:
    """Get top losers from movers list."""
    losers = [m for m in movers if m["change_percent"] < 0]
    losers.sort(key=lambda x: x["change_percent"])
    return losers[:limit]


def get_volume_leaders(movers: List[Dict], limit: int = 20) -> List[Dict]:
    """Get stocks with highest volume ratio (unusual volume)."""
    by_volume = sorted(movers, key=lambda x: x["volume_ratio"], reverse=True)
    return by_volume[:limit]
