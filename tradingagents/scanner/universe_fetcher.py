"""
Universe Fetcher - Dynamic stock universe management
"""

import os
import sys
from typing import List, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .cache import cached

try:
    from tradingagents.dataflows.alpaca_utils import get_alpaca_trading_client
except ImportError:
    get_alpaca_trading_client = None


# Predefined sector-based universes
SECTOR_UNIVERSES = {
    "technology": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
        "AMD", "INTC", "QCOM", "AVGO", "MU", "AMAT", "LRCX",
        "CRM", "ADBE", "NOW", "SNOW", "PLTR", "DDOG", "NET", "CRWD",
    ],
    "semiconductors": [
        "NVDA", "AMD", "INTC", "QCOM", "AVGO", "MU", "AMAT", "LRCX",
        "KLAC", "MRVL", "ON", "NXPI", "TXN", "ADI", "MCHP",
    ],
    "fintech": [
        "V", "MA", "PYPL", "SQ", "COIN", "AFRM", "SOFI", "UPST",
        "HOOD", "NU", "MELI", "ADYEN",
    ],
    "healthcare": [
        "JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "BMY", "GILD",
        "AMGN", "BIIB", "MRNA", "BNTX", "REGN", "VRTX", "ISRG",
    ],
    "energy": [
        "XOM", "CVX", "COP", "SLB", "EOG", "PXD", "OXY", "MPC",
        "VLO", "PSX", "DVN", "HAL", "BKR",
    ],
    "ev_cleantech": [
        "TSLA", "RIVN", "LCID", "NIO", "XPEV", "LI", "ENPH", "SEDG",
        "FSLR", "PLUG", "RUN", "CHPT",
    ],
    "retail": [
        "WMT", "COST", "TGT", "HD", "LOW", "NKE", "SBUX", "MCD",
        "AMZN", "EBAY", "ETSY", "W", "CHWY",
    ],
    "financials": [
        "JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "SCHW", "AXP",
        "USB", "PNC", "TFC", "COF",
    ],
    "media_entertainment": [
        "DIS", "NFLX", "CMCSA", "WBD", "PARA", "SPOT", "RBLX",
        "U", "TTWO", "EA", "MTCH",
    ],
}


# Default universe (large liquid stocks)
DEFAULT_UNIVERSE = [
    # Tech Giants
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
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


@cached(ttl_seconds=3600)  # Cache for 1 hour
def get_dynamic_universe(
    max_symbols: int = 200,
    asset_class: str = "us_equity",
) -> List[str]:
    """
    Fetch top liquid stocks dynamically from Alpaca.

    Filters for liquid stocks using:
    - Tradable status
    - Shortable flag (indicates institutional liquidity)
    - Easy to borrow flag (high availability = high volume)

    Args:
        max_symbols: Maximum number of symbols to return (default 200)
        asset_class: Asset class to filter ("us_equity" or "crypto")

    Returns:
        List of ticker symbols (top 200 liquid stocks)
    """
    if get_alpaca_trading_client is None:
        print("[UNIVERSE] Alpaca client not available, using default universe")
        return DEFAULT_UNIVERSE[:max_symbols]

    try:
        from alpaca.trading.requests import GetAssetsRequest
        from alpaca.trading.enums import AssetClass, AssetStatus

        client = get_alpaca_trading_client()

        # Create request for tradable assets
        asset_class_enum = AssetClass.US_EQUITY if asset_class == "us_equity" else AssetClass.CRYPTO
        request = GetAssetsRequest(
            asset_class=asset_class_enum,
            status=AssetStatus.ACTIVE
        )

        assets = client.get_all_assets(request)

        # Categorize by liquidity indicators
        tier1_liquid = []  # shortable + easy_to_borrow (most liquid)
        tier2_liquid = []  # shortable only
        tier3_tradable = []  # just tradable

        for asset in assets:
            if not asset.tradable:
                continue

            symbol = asset.symbol

            # Skip symbols with special characters (warrants, units, etc.)
            if not symbol.isalpha():
                continue

            # Skip very short symbols (often ETFs or special instruments)
            if len(symbol) < 2:
                continue

            if asset_class == "us_equity":
                easy_to_borrow = getattr(asset, 'easy_to_borrow', False)

                if asset.shortable and easy_to_borrow:
                    tier1_liquid.append(symbol)
                elif asset.shortable:
                    tier2_liquid.append(symbol)
                else:
                    tier3_tradable.append(symbol)
            else:
                # For crypto, just add tradable ones
                tier1_liquid.append(symbol)

        # Build final list prioritizing by liquidity tier
        result = []
        for tier in [tier1_liquid, tier2_liquid, tier3_tradable]:
            remaining = max_symbols - len(result)
            if remaining <= 0:
                break
            result.extend(tier[:remaining])

        print(f"[UNIVERSE] Fetched {len(result)} liquid stocks from Alpaca (Tier1: {len(tier1_liquid)}, Tier2: {len(tier2_liquid)})")
        return result[:max_symbols]

    except Exception as e:
        print(f"[UNIVERSE] Error fetching dynamic universe: {e}")
        print("[UNIVERSE] Falling back to default universe")
        return DEFAULT_UNIVERSE[:max_symbols]


def get_sector_universe(sector: str) -> List[str]:
    """
    Get stocks for a specific sector.

    Args:
        sector: Sector name (technology, semiconductors, fintech, etc.)

    Returns:
        List of ticker symbols for that sector
    """
    sector_lower = sector.lower()

    if sector_lower in SECTOR_UNIVERSES:
        return SECTOR_UNIVERSES[sector_lower]

    # Try partial match
    for key in SECTOR_UNIVERSES:
        if sector_lower in key or key in sector_lower:
            return SECTOR_UNIVERSES[key]

    print(f"[UNIVERSE] Unknown sector '{sector}', returning default universe")
    return DEFAULT_UNIVERSE


def get_all_sectors() -> List[str]:
    """Get list of available sectors."""
    return list(SECTOR_UNIVERSES.keys())


def get_combined_universe(sectors: Optional[List[str]] = None) -> List[str]:
    """
    Get a combined universe from multiple sectors (deduplicated).

    Args:
        sectors: List of sector names. If None, returns all sectors combined.

    Returns:
        Deduplicated list of ticker symbols
    """
    if sectors is None:
        sectors = list(SECTOR_UNIVERSES.keys())

    combined = set()
    for sector in sectors:
        combined.update(get_sector_universe(sector))

    return list(combined)
