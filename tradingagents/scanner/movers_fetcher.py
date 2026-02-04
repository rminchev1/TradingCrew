"""
Movers Fetcher - Gets top movers from Yahoo Finance screeners
"""

import yfinance as yf
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime, timedelta
import time


# Predefined universe of liquid US stocks (S&P 500 + popular tech/growth)
STOCK_UNIVERSE = [
    # Tech Giants
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "TSLA",
    # Semiconductors
    "AMD", "INTC", "QCOM", "AVGO", "MU", "AMAT", "LRCX", "KLAC", "MRVL", "ON",
    # Software/Cloud
    "CRM", "ADBE", "NOW", "SNOW", "PLTR", "DDOG", "NET", "ZS", "CRWD", "PANW",
    # Fintech/Payments
    "V", "MA", "PYPL", "SQ", "COIN", "AFRM", "SOFI",
    # E-commerce/Consumer
    "SHOP", "ETSY", "EBAY", "W", "CHWY", "CVNA",
    # Social/Media
    "SNAP", "PINS", "RBLX", "U", "MTCH", "SPOT", "ROKU",
    # EV/Clean Energy
    "RIVN", "LCID", "NIO", "XPEV", "LI", "ENPH", "SEDG", "FSLR",
    # Healthcare/Biotech
    "JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "BMY", "GILD", "AMGN", "BIIB",
    "MRNA", "BNTX", "REGN", "VRTX", "ISRG", "DXCM", "ILMN",
    # Financials
    "JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "SCHW", "AXP",
    # Retail
    "WMT", "COST", "TGT", "HD", "LOW", "NKE", "SBUX", "MCD", "DIS",
    # Industrial/Defense
    "BA", "CAT", "DE", "GE", "HON", "LMT", "RTX", "NOC",
    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG", "PXD", "OXY",
    # Telecom
    "T", "VZ", "TMUS",
    # Other Popular
    "NFLX", "ABNB", "UBER", "LYFT", "DASH", "ZM", "DOCU", "OKTA",
    "TWLO", "MDB", "ESTC", "TTD", "BILL", "HUBS", "VEEV", "WDAY",
]


def get_top_movers(
    min_price: float = 5.0,
    min_volume: int = 500000,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get top movers from the stock universe based on daily price change.

    Args:
        min_price: Minimum stock price filter
        min_volume: Minimum volume filter
        limit: Maximum number of stocks to return

    Returns:
        List of dicts with symbol and basic data
    """
    print(f"[SCANNER] Fetching data for {len(STOCK_UNIVERSE)} stocks...")

    results = []
    batch_size = 20

    # Process in batches to avoid rate limiting
    for i in range(0, len(STOCK_UNIVERSE), batch_size):
        batch = STOCK_UNIVERSE[i:i + batch_size]
        batch_str = " ".join(batch)

        try:
            # Fetch data for batch
            tickers = yf.Tickers(batch_str)

            for symbol in batch:
                try:
                    ticker = tickers.tickers.get(symbol)
                    if not ticker:
                        continue

                    # Get recent history (5 days for change calculation)
                    hist = ticker.history(period="5d")
                    if hist.empty or len(hist) < 2:
                        continue

                    # Get current/latest data
                    latest = hist.iloc[-1]
                    prev_close = hist.iloc[-2]["Close"] if len(hist) >= 2 else latest["Close"]

                    price = latest["Close"]
                    volume = int(latest["Volume"])
                    change_pct = ((price - prev_close) / prev_close) * 100 if prev_close > 0 else 0

                    # Apply filters
                    if price < min_price or volume < min_volume:
                        continue

                    # Get company info
                    info = ticker.info or {}
                    company_name = info.get("shortName", info.get("longName", symbol))
                    sector = info.get("sector", "Unknown")
                    market_cap = info.get("marketCap")

                    # Calculate average volume (20-day approx from 5-day data)
                    avg_volume = hist["Volume"].mean() if len(hist) > 0 else volume
                    volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0

                    results.append({
                        "symbol": symbol,
                        "company_name": company_name,
                        "price": round(price, 2),
                        "change_percent": round(change_pct, 2),
                        "volume": volume,
                        "volume_ratio": round(volume_ratio, 2),
                        "sector": sector,
                        "market_cap": market_cap,
                        "chart_data": hist["Close"].tolist()[-5:],  # Last 5 days
                    })

                except Exception as e:
                    print(f"[SCANNER] Error processing {symbol}: {e}")
                    continue

            # Small delay between batches
            time.sleep(0.5)

        except Exception as e:
            print(f"[SCANNER] Error fetching batch: {e}")
            continue

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
