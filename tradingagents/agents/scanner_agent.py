"""
Scanner Agent - LLM-based ranking and rationale generation for market scanner
"""

import os
from typing import List
from langchain_openai import ChatOpenAI

# Import scanner result type
try:
    from tradingagents.scanner.scanner_result import ScannerResult
except ImportError:
    ScannerResult = None


def get_scanner_llm():
    """Get the LLM for scanner rationale generation."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        api_key=api_key,
    )


def generate_rationales(results: List["ScannerResult"]) -> List["ScannerResult"]:
    """
    Generate LLM rationales for scanner results.

    Args:
        results: List of ScannerResult objects with scores but no rationales

    Returns:
        Same list with rationale field populated
    """
    if not results:
        return results

    try:
        llm = get_scanner_llm()
    except Exception as e:
        print(f"[SCANNER-AGENT] Could not initialize LLM: {e}")
        return results

    # Build prompt with all candidates
    candidates_text = []
    for i, r in enumerate(results, 1):
        candidates_text.append(f"""
{i}. {r.symbol} ({r.company_name})
   - Price: ${r.price:.2f} ({r.change_percent:+.2f}%)
   - Volume: {r.volume:,} ({r.volume_ratio:.1f}x avg)
   - RSI: {r.rsi:.1f}
   - MACD: {r.macd_signal}
   - Price vs 50MA: {r.price_vs_50ma}
   - Price vs 200MA: {r.price_vs_200ma}
   - Technical Score: {r.technical_score}/100
   - News Sentiment: {r.news_sentiment} ({r.news_count} articles)
   - News Score: {r.news_score}/100
   - Combined Score: {r.combined_score}/100
   - Sector: {r.sector}
""")

    prompt = f"""You are a stock market analyst. For each of the following {len(results)} stock candidates,
write a concise 2-3 sentence rationale explaining why this stock is interesting for trading today.

Focus on:
- Key technical signals (RSI, MACD, moving averages)
- Volume patterns (unusual activity)
- News/sentiment drivers
- Risk factors to watch

Be specific and actionable. Avoid generic statements.

CANDIDATES:
{"".join(candidates_text)}

Respond with ONLY a JSON array of rationales in order, like:
["Rationale for stock 1...", "Rationale for stock 2...", ...]

Do not include any other text or explanation."""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()

        # Parse JSON response
        import json

        # Handle potential markdown code blocks
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        rationales = json.loads(content)

        if len(rationales) == len(results):
            for i, rationale in enumerate(rationales):
                results[i].rationale = rationale
        else:
            print(f"[SCANNER-AGENT] Rationale count mismatch: got {len(rationales)}, expected {len(results)}")

    except Exception as e:
        print(f"[SCANNER-AGENT] Error generating rationales: {e}")
        # Rationales will remain empty, market_scanner.py has fallback

    return results


def rank_candidates(candidates: List[dict], limit: int = 8) -> List[dict]:
    """
    Use LLM to rank and select top candidates.

    This is an optional enhancement that can be used instead of
    simple score-based ranking.

    Args:
        candidates: List of candidate dicts with scores
        limit: Number of top candidates to return

    Returns:
        Ranked list of top candidates
    """
    if len(candidates) <= limit:
        return candidates

    try:
        llm = get_scanner_llm()
    except Exception as e:
        print(f"[SCANNER-AGENT] Could not initialize LLM for ranking: {e}")
        # Fall back to score-based ranking
        return sorted(candidates, key=lambda x: x.get("combined_score", 0), reverse=True)[:limit]

    # Build summary of candidates
    summary_lines = []
    for i, c in enumerate(candidates[:20], 1):  # Only consider top 20 by score
        summary_lines.append(
            f"{i}. {c['symbol']}: ${c['price']:.2f} ({c['change_percent']:+.1f}%), "
            f"Tech={c['technical_score']}, News={c['news_score']}, Combined={c['combined_score']}"
        )

    prompt = f"""You are a stock trading expert. From these {len(summary_lines)} candidates,
select the {limit} BEST opportunities for end-of-day trading.

Consider:
1. Balanced technical and news scores (avoid one-sided signals)
2. Reasonable volatility (avoid extreme movers that may reverse)
3. Diversity (don't select too many from same sector)
4. Risk/reward balance

CANDIDATES:
{chr(10).join(summary_lines)}

Respond with ONLY the numbers of your top {limit} picks in order of preference, like:
[3, 7, 1, 12, 5, 8, 2, 15]

Do not include any other text."""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()

        import json
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        indices = json.loads(content)

        # Convert 1-based indices to 0-based and select candidates
        selected = []
        for idx in indices[:limit]:
            if 1 <= idx <= len(candidates):
                selected.append(candidates[idx - 1])

        # Fill remaining slots if needed
        if len(selected) < limit:
            for c in candidates:
                if c not in selected:
                    selected.append(c)
                    if len(selected) >= limit:
                        break

        return selected

    except Exception as e:
        print(f"[SCANNER-AGENT] Error in LLM ranking: {e}")
        return sorted(candidates, key=lambda x: x.get("combined_score", 0), reverse=True)[:limit]
