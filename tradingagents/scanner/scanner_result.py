"""
Scanner Result Data Structure
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class ScannerResult:
    """Represents a single stock suggestion from the market scanner."""

    symbol: str
    company_name: str = ""
    price: float = 0.0
    change_percent: float = 0.0
    volume: int = 0
    volume_ratio: float = 1.0  # vs 20-day avg

    # Technical indicators
    rsi: float = 50.0
    macd_signal: str = "neutral"  # "bullish", "bearish", "neutral"
    price_vs_50ma: str = "neutral"  # "above", "below", "neutral"
    price_vs_200ma: str = "neutral"
    technical_score: int = 50  # 0-100

    # News & sentiment
    news_sentiment: str = "neutral"  # "bullish", "bearish", "neutral"
    news_count: int = 0  # news items in 24h
    news_score: int = 50  # 0-100

    # Options flow
    options_score: float = 50.0  # 0-100
    options_signal: str = "neutral"  # "bullish", "bearish", "neutral"

    # Combined
    combined_score: int = 50  # 0-100
    rationale: str = ""  # LLM-generated 2-3 sentences

    # Chart data for sparkline
    chart_data: List[float] = field(default_factory=list)  # 5-day close prices

    # Additional info
    sector: str = ""
    market_cap: Optional[float] = None

    @property
    def total_score(self) -> float:
        """
        Calculate total score including options.

        Weighted: 50% technical, 30% news, 20% options
        """
        return (
            self.technical_score * 0.5 +
            self.news_score * 0.3 +
            self.options_score * 0.2
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "company_name": self.company_name,
            "price": self.price,
            "change_percent": self.change_percent,
            "volume": self.volume,
            "volume_ratio": self.volume_ratio,
            "rsi": self.rsi,
            "macd_signal": self.macd_signal,
            "price_vs_50ma": self.price_vs_50ma,
            "price_vs_200ma": self.price_vs_200ma,
            "technical_score": self.technical_score,
            "news_sentiment": self.news_sentiment,
            "news_count": self.news_count,
            "news_score": self.news_score,
            "options_score": self.options_score,
            "options_signal": self.options_signal,
            "combined_score": self.combined_score,
            "total_score": self.total_score,
            "rationale": self.rationale,
            "chart_data": self.chart_data,
            "sector": self.sector,
            "market_cap": self.market_cap,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScannerResult":
        """Create from dictionary."""
        # Remove computed properties that aren't constructor args
        data = {k: v for k, v in data.items() if k != "total_score"}
        return cls(**data)
