"""
Sector Utilities - Dynamic sector identification using yfinance.

Uses yfinance to dynamically identify a stock's sector, then maps to appropriate ETF.
Falls back to curated peer lists for common sectors.
"""

from typing import Dict, List, Optional, Tuple
import functools


# Map yfinance sector names to ETF symbols
YFINANCE_SECTOR_TO_ETF = {
    "technology": "XLK",
    "communication services": "XLC",
    "healthcare": "XLV",
    "financials": "XLF",
    "consumer cyclical": "XLY",
    "consumer defensive": "XLP",
    "industrials": "XLI",
    "energy": "XLE",
    "utilities": "XLU",
    "basic materials": "XLB",
    "real estate": "XLRE",
}

# Additional industry-specific ETF mappings for more precise benchmarks
INDUSTRY_TO_ETF = {
    "semiconductors": "SMH",
    "semiconductor equipment & materials": "SMH",
    "software - infrastructure": "IGV",
    "software - application": "IGV",
    "biotechnology": "XBI",
    "banks - regional": "KRE",
    "banks - diversified": "KBE",
    "oil & gas exploration & production": "XOP",
    "oil & gas integrated": "XLE",
    "aerospace & defense": "ITA",
    "internet retail": "IBUY",
    "auto manufacturers": "CARZ",
    "solar": "TAN",
    "medical devices": "IHI",
    "health information services": "XLV",  # Telehealth falls here
    "drug manufacturers": "XLV",
}

# Legacy sector ETF mappings (for backward compatibility)
SECTOR_ETFS = {
    "technology": "XLK",
    "semiconductors": "SMH",
    "fintech": "ARKF",
    "healthcare": "XLV",
    "energy": "XLE",
    "ev_cleantech": "QCLN",
    "retail": "XRT",
    "financials": "XLF",
    "media_entertainment": "XLC",
    "industrials": "XLI",
    "consumer_discretionary": "XLY",
    "consumer_staples": "XLP",
    "utilities": "XLU",
    "materials": "XLB",
    "real_estate": "XLRE",
}

# All sector ETFs for rotation analysis
ALL_SECTOR_ETFS = [
    "XLK",   # Technology
    "XLF",   # Financials
    "XLE",   # Energy
    "XLV",   # Healthcare
    "XLI",   # Industrials
    "XLY",   # Consumer Discretionary
    "XLP",   # Consumer Staples
    "XLU",   # Utilities
    "XLB",   # Materials
    "XLRE",  # Real Estate
    "XLC",   # Communication Services
]

# Sector classification: Offensive vs Defensive
SECTOR_CLASSIFICATION = {
    "XLK": "offensive",   # Technology
    "XLY": "offensive",   # Consumer Discretionary
    "XLF": "offensive",   # Financials
    "XLI": "offensive",   # Industrials
    "XLC": "offensive",   # Communication Services
    "XLE": "offensive",   # Energy
    "XLB": "cyclical",    # Materials
    "XLRE": "cyclical",   # Real Estate
    "XLV": "defensive",   # Healthcare
    "XLP": "defensive",   # Consumer Staples
    "XLU": "defensive",   # Utilities
}

# Sector universes - mapping sectors to their constituent stocks
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
    "industrials": [
        "BA", "CAT", "DE", "GE", "HON", "LMT", "RTX", "NOC",
        "UNP", "UPS", "FDX", "MMM",
    ],
    "consumer_discretionary": [
        "AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "LOW", "TJX",
        "BKNG", "MAR", "CMG", "YUM",
    ],
    "consumer_staples": [
        "PG", "KO", "PEP", "COST", "WMT", "PM", "MO", "CL",
        "KMB", "EL", "GIS", "K",
    ],
    "utilities": [
        "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL",
        "ED", "WEC", "ES", "DTE",
    ],
}


def _build_ticker_to_sector_map() -> Dict[str, List[str]]:
    """Build reverse lookup: ticker -> list of sectors it belongs to."""
    ticker_map = {}
    for sector, tickers in SECTOR_UNIVERSES.items():
        for ticker in tickers:
            if ticker not in ticker_map:
                ticker_map[ticker] = []
            ticker_map[ticker].append(sector)
    return ticker_map


# Pre-built reverse lookup
TICKER_TO_SECTORS = _build_ticker_to_sector_map()


@functools.lru_cache(maxsize=500)
def _get_yfinance_sector_info(ticker: str) -> Dict[str, str]:
    """
    Fetch sector, industry, and business summary from yfinance (cached).

    Returns dict with 'sector', 'industry', 'business_summary', or empty dict on failure.
    """
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        info = stock.info

        # Get business summary (truncate to 500 chars to save tokens)
        business_summary = info.get("longBusinessSummary", "") or ""
        if len(business_summary) > 500:
            business_summary = business_summary[:500] + "..."

        return {
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "business_summary": business_summary,
            "company_name": info.get("longName", "") or info.get("shortName", ticker),
        }
    except Exception as e:
        print(f"[SECTOR] yfinance lookup failed for {ticker}: {e}")
        return {}


def identify_sector(ticker: str) -> Dict[str, any]:
    """
    Dynamically identify the sector, ETF, and peers for a given ticker.

    Uses yfinance to get real sector/industry data, then maps to appropriate ETF.
    Falls back to curated peer lists if available.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dict with:
            - sector: Primary sector name (from yfinance)
            - industry: Industry name (from yfinance)
            - sector_etf: Sector ETF symbol
            - peers: List of peer stocks in the same sector
            - all_sectors: List of all sectors the stock belongs to (legacy)
    """
    ticker = ticker.upper()

    # Get sector info from yfinance
    yf_info = _get_yfinance_sector_info(ticker)
    yf_sector = yf_info.get("sector", "").lower()
    yf_industry = yf_info.get("industry", "").lower()

    # Determine the best ETF benchmark
    sector_etf = "SPY"  # Default fallback

    # First try industry-specific ETF (more precise)
    if yf_industry:
        sector_etf = INDUSTRY_TO_ETF.get(yf_industry, sector_etf)

    # Then try sector-level ETF
    if sector_etf == "SPY" and yf_sector:
        sector_etf = YFINANCE_SECTOR_TO_ETF.get(yf_sector, sector_etf)

    # Get peers from our curated lists if the sector matches
    peers = []
    matched_sector = None

    # Try to match yfinance sector to our curated peer lists
    sector_name_mapping = {
        "technology": ["technology"],
        "healthcare": ["healthcare"],
        "financials": ["financials", "financial services"],
        "energy": ["energy"],
        "industrials": ["industrials"],
        "consumer_discretionary": ["consumer cyclical"],
        "consumer_staples": ["consumer defensive"],
        "utilities": ["utilities"],
        "real_estate": ["real estate"],
        "media_entertainment": ["communication services"],
        "semiconductors": ["semiconductors"],
    }

    for our_sector, yf_names in sector_name_mapping.items():
        if yf_sector in yf_names or any(name in yf_sector for name in yf_names):
            matched_sector = our_sector
            peers = [p for p in SECTOR_UNIVERSES.get(our_sector, []) if p != ticker]
            break

    # Also check if ticker is in our curated lists (legacy support)
    legacy_sectors = TICKER_TO_SECTORS.get(ticker, [])
    if not peers and legacy_sectors:
        matched_sector = legacy_sectors[0]
        peers = [p for p in SECTOR_UNIVERSES.get(matched_sector, []) if p != ticker]

    return {
        "sector": yf_info.get("sector", "Unknown") or "Unknown",
        "industry": yf_info.get("industry", "Unknown") or "Unknown",
        "sector_etf": sector_etf,
        "peers": peers[:15],  # Limit to 15 peers
        "all_sectors": legacy_sectors,
        "matched_curated_sector": matched_sector,
        "business_summary": yf_info.get("business_summary", ""),
        "company_name": yf_info.get("company_name", ticker),
    }


def get_sector_etf(sector: str) -> str:
    """Get the ETF symbol for a given sector."""
    return SECTOR_ETFS.get(sector.lower(), "SPY")


def get_sector_classification(etf: str) -> str:
    """Get whether a sector ETF is offensive, defensive, or cyclical."""
    return SECTOR_CLASSIFICATION.get(etf.upper(), "unknown")


def get_all_sector_etfs() -> List[str]:
    """Get list of all sector ETFs for rotation analysis."""
    return ALL_SECTOR_ETFS.copy()


def get_sector_peers(ticker: str, max_peers: int = 10) -> Tuple[str, str, List[str]]:
    """
    Get sector information and peers for a ticker.

    Args:
        ticker: Stock ticker symbol
        max_peers: Maximum number of peers to return

    Returns:
        Tuple of (sector_name, sector_etf, list_of_peers)
    """
    info = identify_sector(ticker)
    return (
        info["sector"],
        info["sector_etf"],
        info["peers"][:max_peers]
    )
