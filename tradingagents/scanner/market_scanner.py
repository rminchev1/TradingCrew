"""
Market Scanner - Main orchestration for stock scanning
"""

import os
import sys
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from .scanner_result import ScannerResult
from .movers_fetcher import get_top_movers
from .technical_screener import score_technical
from .news_screener import score_news


class MarketScanner:
    """
    Scans the US stock market for trading opportunities.

    Uses momentum/technical indicators and news catalysts
    to identify and rank potential trades.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the market scanner.

        Args:
            config: Optional configuration dict with:
                - num_results: Number of suggestions to return (default 8)
                - min_price: Minimum stock price (default 5.0)
                - min_volume: Minimum volume (default 500000)
                - use_llm: Whether to use LLM for ranking (default True)
        """
        self.config = config or {}
        self.num_results = self.config.get("num_results", 8)
        self.min_price = self.config.get("min_price", 5.0)
        self.min_volume = self.config.get("min_volume", 500000)
        self.use_llm = self.config.get("use_llm", True)

    def scan(self, progress_callback=None) -> List[ScannerResult]:
        """
        Run a full market scan.

        Args:
            progress_callback: Optional callback(stage, progress) for UI updates

        Returns:
            List of ScannerResult objects (top picks)
        """
        print("[SCANNER] Starting market scan...")
        start_time = time.time()

        # Stage 1: Get top movers
        if progress_callback:
            progress_callback("fetching", 0.1)

        print("[SCANNER] Stage 1: Fetching top movers...")
        movers = get_top_movers(
            min_price=self.min_price,
            min_volume=self.min_volume,
            limit=50  # Get top 50 candidates
        )

        if not movers:
            print("[SCANNER] No movers found!")
            return []

        print(f"[SCANNER] Found {len(movers)} candidates")

        # Stage 2: Calculate technical scores (parallel)
        if progress_callback:
            progress_callback("technical", 0.3)

        print("[SCANNER] Stage 2: Calculating technical scores...")
        symbols = [m["symbol"] for m in movers]

        tech_scores = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(score_technical, sym): sym for sym in symbols}
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    tech_scores[symbol] = future.result()
                except Exception as e:
                    print(f"[SCANNER] Tech score error for {symbol}: {e}")
                    tech_scores[symbol] = {"technical_score": 50}

        # Stage 3: Calculate news scores (parallel, limited)
        if progress_callback:
            progress_callback("news", 0.6)

        print("[SCANNER] Stage 3: Analyzing news sentiment...")
        # Only analyze news for top 20 by technical score to save time
        sorted_by_tech = sorted(
            movers,
            key=lambda m: tech_scores.get(m["symbol"], {}).get("technical_score", 50),
            reverse=True
        )[:20]

        news_scores = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(score_news, m["symbol"]): m["symbol"]
                for m in sorted_by_tech
            }
            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    news_scores[symbol] = future.result()
                except Exception as e:
                    print(f"[SCANNER] News score error for {symbol}: {e}")
                    news_scores[symbol] = {"news_score": 50}

        # Stage 4: Combine scores and rank
        if progress_callback:
            progress_callback("ranking", 0.8)

        print("[SCANNER] Stage 4: Ranking candidates...")
        results = []

        for mover in movers:
            symbol = mover["symbol"]
            tech = tech_scores.get(symbol, {})
            news = news_scores.get(symbol, {"news_score": 50, "news_sentiment": "neutral", "news_count": 0})

            tech_score = tech.get("technical_score", 50)
            news_score = news.get("news_score", 50)

            # Combined score (60% technical, 40% news)
            combined = int(tech_score * 0.6 + news_score * 0.4)

            # Bonus for high volume ratio (unusual activity)
            if mover.get("volume_ratio", 1) > 2.0:
                combined += 5
            if mover.get("volume_ratio", 1) > 3.0:
                combined += 5

            combined = min(100, combined)

            result = ScannerResult(
                symbol=symbol,
                company_name=mover.get("company_name", symbol),
                price=mover.get("price", 0),
                change_percent=mover.get("change_percent", 0),
                volume=mover.get("volume", 0),
                volume_ratio=mover.get("volume_ratio", 1),
                rsi=tech.get("rsi", 50),
                macd_signal=tech.get("macd_signal", "neutral"),
                price_vs_50ma=tech.get("price_vs_50ma", "neutral"),
                price_vs_200ma=tech.get("price_vs_200ma", "neutral"),
                technical_score=tech_score,
                news_sentiment=news.get("news_sentiment", "neutral"),
                news_count=news.get("news_count", 0),
                news_score=news_score,
                combined_score=combined,
                rationale="",  # Will be filled by LLM agent
                chart_data=mover.get("chart_data", []),
                sector=mover.get("sector", ""),
                market_cap=mover.get("market_cap"),
            )
            results.append(result)

        # Sort by combined score
        results.sort(key=lambda r: r.combined_score, reverse=True)

        # Take top N
        top_results = results[:self.num_results]

        # Stage 5: Generate rationales (if LLM enabled)
        if self.use_llm and top_results:
            if progress_callback:
                progress_callback("rationale", 0.9)
            print("[SCANNER] Stage 5: Generating rationales...")
            top_results = self._generate_rationales(top_results)

        if progress_callback:
            progress_callback("complete", 1.0)

        elapsed = time.time() - start_time
        print(f"[SCANNER] Scan complete in {elapsed:.1f}s. Found {len(top_results)} suggestions.")

        return top_results

    def _generate_rationales(self, results: List[ScannerResult]) -> List[ScannerResult]:
        """Generate LLM rationales for results."""
        try:
            from tradingagents.agents.scanner_agent import generate_rationales
            return generate_rationales(results)
        except ImportError as e:
            print(f"[SCANNER] LLM rationale generation not available: {e}")
            # Generate simple rationales without LLM
            for r in results:
                r.rationale = self._simple_rationale(r)
            return results
        except Exception as e:
            print(f"[SCANNER] Error generating rationales: {e}")
            for r in results:
                r.rationale = self._simple_rationale(r)
            return results

    def _simple_rationale(self, result: ScannerResult) -> str:
        """Generate a simple rationale without LLM."""
        parts = []

        # Price action
        if result.change_percent > 3:
            parts.append(f"Strong momentum with {result.change_percent:.1f}% gain")
        elif result.change_percent > 0:
            parts.append(f"Positive momentum ({result.change_percent:.1f}%)")
        elif result.change_percent < -3:
            parts.append(f"Sharp pullback of {result.change_percent:.1f}%")
        else:
            parts.append(f"Consolidating ({result.change_percent:.1f}%)")

        # Technical
        if result.macd_signal == "bullish":
            parts.append("MACD bullish crossover")
        elif result.macd_signal == "bearish":
            parts.append("MACD showing weakness")

        if result.rsi < 30:
            parts.append("RSI oversold - potential bounce")
        elif result.rsi > 70:
            parts.append("RSI overbought - watch for pullback")

        # Volume
        if result.volume_ratio > 2:
            parts.append(f"Unusual volume ({result.volume_ratio:.1f}x average)")

        # News
        if result.news_sentiment == "bullish":
            parts.append("Positive news sentiment")
        elif result.news_sentiment == "bearish":
            parts.append("Negative news - proceed with caution")

        return ". ".join(parts) + "."


def run_scan(config: Optional[Dict] = None) -> List[ScannerResult]:
    """Convenience function to run a scan."""
    scanner = MarketScanner(config)
    return scanner.scan()
