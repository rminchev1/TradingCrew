"""
Portfolio Chat Assistant - Lightweight LLM-powered assistant for portfolio queries.

Uses OpenAI function calling with a set of read-only tools to answer portfolio,
market data, and watchlist questions without running a full multi-agent analysis.
"""

import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from langchain_core.tools import tool


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool
def get_account_summary() -> str:
    """Get a summary of the Alpaca trading account including equity, cash, buying power, and daily P&L."""
    try:
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils

        info = AlpacaUtils.get_account_info()
        if not info:
            return "Unable to fetch account info. Check Alpaca API keys."

        equity = info.get("equity", 0)
        cash = info.get("cash", 0)
        buying_power = info.get("buying_power", 0)
        daily_chg = info.get("daily_change_dollars", 0)
        daily_pct = info.get("daily_change_percent", 0)

        return (
            f"Account Summary:\n"
            f"  Equity: ${equity:,.2f}\n"
            f"  Cash: ${cash:,.2f}\n"
            f"  Buying Power: ${buying_power:,.2f}\n"
            f"  Daily P&L: ${daily_chg:+,.2f} ({daily_pct:+.2f}%)"
        )
    except Exception as e:
        return f"Error fetching account info: {e}"


@tool
def get_portfolio_positions() -> str:
    """Get all current stock positions with symbol, quantity, market value, P&L, and average entry price."""
    try:
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils

        positions = AlpacaUtils.get_positions_data()
        if not positions:
            return "No open positions."

        lines = ["Current Positions:"]
        for pos in positions:
            symbol = pos.get("Symbol", "?")
            qty = pos.get("Qty", 0)
            mv = pos.get("market_value_raw", 0)
            pl = pos.get("total_pl_dollars_raw", 0)
            pl_pct = pos.get("total_pl_pct_raw", 0)
            avg = pos.get("avg_entry_raw", 0)
            lines.append(
                f"  {symbol}: {qty} shares @ ${avg:,.2f} avg | "
                f"MV ${mv:,.2f} | P&L ${pl:+,.2f} ({pl_pct:+.2f}%)"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching positions: {e}"


@tool
def get_stock_quote(symbol: str) -> str:
    """Get the latest price quote for a stock or crypto symbol.

    Args:
        symbol: Ticker symbol e.g. 'AAPL', 'BTC/USD'
    """
    try:
        import yfinance as yf

        # Convert crypto format for yfinance
        yf_symbol = symbol.replace("/", "-") if "/" in symbol else symbol
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info

        if not info or info.get("regularMarketPrice") is None:
            return f"No quote data available for {symbol}."

        price = info.get("regularMarketPrice", "N/A")
        prev_close = info.get("regularMarketPreviousClose", 0)
        change = (price - prev_close) if isinstance(price, (int, float)) and prev_close else 0
        pct = (change / prev_close * 100) if prev_close else 0
        high = info.get("dayHigh", "N/A")
        low = info.get("dayLow", "N/A")
        volume = info.get("regularMarketVolume", "N/A")
        mkt_cap = info.get("marketCap")

        parts = [
            f"{symbol} Quote:",
            f"  Price: ${price:,.2f}" if isinstance(price, (int, float)) else f"  Price: {price}",
            f"  Change: ${change:+,.2f} ({pct:+.2f}%)",
            f"  Day Range: ${low} - ${high}",
            f"  Volume: {volume:,}" if isinstance(volume, (int, float)) else f"  Volume: {volume}",
        ]
        if mkt_cap:
            parts.append(f"  Market Cap: ${mkt_cap:,.0f}")
        return "\n".join(parts)
    except Exception as e:
        return f"Error fetching quote for {symbol}: {e}"


@tool
def get_stock_fundamentals(symbol: str) -> str:
    """Get key fundamental data for a stock (P/E, EPS, revenue, margins, etc.).

    Args:
        symbol: Stock ticker symbol e.g. 'AAPL', 'NVDA'
    """
    try:
        from tradingagents.dataflows.interface import get_fundamentals_yfinance

        curr_date = datetime.now().strftime("%Y-%m-%d")
        return get_fundamentals_yfinance(symbol, curr_date)
    except Exception as e:
        return f"Error fetching fundamentals for {symbol}: {e}"


@tool
def get_recent_news(symbol: str) -> str:
    """Get recent news headlines for a stock or crypto symbol.

    Args:
        symbol: Ticker symbol e.g. 'AAPL', 'BTC/USD'
    """
    try:
        is_crypto = "/" in symbol or "USD" in symbol.upper()
        curr_date = datetime.now().strftime("%Y-%m-%d")

        if is_crypto:
            from tradingagents.dataflows.interface import get_coindesk_news
            return get_coindesk_news(symbol, num_sentences=3)
        else:
            from tradingagents.dataflows.interface import get_finnhub_news_online
            return get_finnhub_news_online(symbol, curr_date, look_back_days=7)
    except Exception as e:
        return f"Error fetching news for {symbol}: {e}"


@tool
def get_sector_exposure() -> str:
    """Get portfolio sector exposure breakdown and risk utilization metrics."""
    try:
        from tradingagents.dataflows.portfolio_risk import build_portfolio_context
        from webui.utils.state import app_state

        ctx = build_portfolio_context(app_state.system_settings)
        if ctx is None:
            return "Unable to build portfolio context. Check Alpaca connection."

        lines = [
            f"Portfolio Equity: ${ctx.equity:,.2f}",
            f"Positions: {len(ctx.positions)}",
            "",
            "Sector Breakdown:",
        ]
        for sector, value in sorted(ctx.sector_breakdown.items(), key=lambda x: -x[1]):
            pct = (value / ctx.equity * 100) if ctx.equity else 0
            lines.append(f"  {sector}: ${value:,.2f} ({pct:.1f}%)")

        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching sector exposure: {e}"


@tool
def get_watchlist() -> str:
    """Get the current watchlist symbols."""
    try:
        from webui.utils.local_storage import get_watchlist as _get_wl

        data = _get_wl()
        symbols = data.get("symbols", [])
        if not symbols:
            return "Watchlist is empty."
        return f"Watchlist ({len(symbols)} symbols): {', '.join(symbols)}"
    except Exception as e:
        return f"Error fetching watchlist: {e}"


@tool
def get_latest_analysis(symbol: str) -> str:
    """Get the latest analysis results for a symbol if available.

    Args:
        symbol: Ticker symbol that was previously analyzed
    """
    try:
        from webui.utils.state import app_state

        state = app_state.get_state(symbol)
        if not state:
            return f"No analysis data found for {symbol}."

        reports = state.get("current_reports", {})
        decision = reports.get("final_trade_decision")
        if decision:
            # Truncate if very long
            if len(decision) > 1500:
                decision = decision[:1500] + "\n... (truncated)"
            return f"Latest analysis for {symbol}:\n{decision}"

        # Check which reports are available
        available = [k for k, v in reports.items() if v]
        if available:
            return f"Partial analysis for {symbol}. Reports available: {', '.join(available)}"
        return f"No analysis reports available for {symbol}."
    except Exception as e:
        return f"Error fetching analysis for {symbol}: {e}"


# ---------------------------------------------------------------------------
# All tools list
# ---------------------------------------------------------------------------

ASSISTANT_TOOLS = [
    get_account_summary,
    get_portfolio_positions,
    get_stock_quote,
    get_stock_fundamentals,
    get_recent_news,
    get_sector_exposure,
    get_watchlist,
    get_latest_analysis,
]

# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

ASSISTANT_SYSTEM_PROMPT = """You are a helpful portfolio assistant for a stock and crypto trading platform.
You have access to tools that can fetch live account data, stock quotes, fundamentals, news, and portfolio information.

Guidelines:
- Be concise and direct. Use bullet points and tables where helpful.
- When the user asks about their portfolio, use get_account_summary and get_portfolio_positions.
- When the user asks about a specific stock, use get_stock_quote and/or get_stock_fundamentals.
- When the user asks for news, use get_recent_news.
- When the user asks about sector exposure or risk, use get_sector_exposure.
- For crypto symbols, always preserve the /USD suffix (e.g. BTC/USD, ETH/USD).

Action Markers:
When you want to suggest the user add a symbol to their watchlist or run queue, include
action markers in your response using this exact format:
  [[ACTION:SYMBOL:watchlist:reason]]   - suggest adding SYMBOL to watchlist
  [[ACTION:SYMBOL:run:reason]]         - suggest running full analysis on SYMBOL

Examples:
  [[ACTION:AAPL:watchlist:Strong fundamentals and upcoming earnings]]
  [[ACTION:NVDA:run:High momentum - worth a full multi-agent analysis]]
  [[ACTION:BTC/USD:watchlist:Breaking above key resistance level]]

Only include action markers when it makes sense contextually. Do not force them.
The markers will be rendered as clickable buttons in the UI.
"""

# ---------------------------------------------------------------------------
# Action Parsing
# ---------------------------------------------------------------------------

ACTION_PATTERN = re.compile(r"\[\[ACTION:([A-Za-z0-9/]+):(\w+):([^\]]+)\]\]")


def parse_actions(content: str) -> List[Dict[str, str]]:
    """Parse [[ACTION:SYMBOL:TARGET:REASON]] markers from assistant content.

    Returns list of dicts with keys: symbol, target, reason.
    """
    actions = []
    for match in ACTION_PATTERN.finditer(content):
        actions.append({
            "symbol": match.group(1),
            "target": match.group(2),
            "reason": match.group(3).strip(),
        })
    return actions


def strip_action_markers(content: str) -> str:
    """Remove [[ACTION:...]] markers from content for display."""
    return ACTION_PATTERN.sub("", content).strip()


# ---------------------------------------------------------------------------
# Models that don't support temperature (match trading_graph.py pattern)
# ---------------------------------------------------------------------------

NO_TEMP_MODELS = ["o3", "o4-mini", "gpt-5", "gpt-5-mini", "gpt-5-nano"]


# ---------------------------------------------------------------------------
# PortfolioAssistant
# ---------------------------------------------------------------------------

class PortfolioAssistant:
    """Lightweight LLM assistant with tool-calling for portfolio queries."""

    MAX_TOOL_ITERATIONS = 8

    def __init__(
        self,
        model_name: str = "gpt-4.1-nano",
        api_key: Optional[str] = None,
        max_retries: int = 3,
    ):
        self.model_name = model_name
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.max_retries = max_retries
        self._llm = None

    def _get_llm(self):
        """Lazy-init the LLM with tools bound."""
        if self._llm is None:
            from langchain_openai import ChatOpenAI

            kwargs = {
                "model": self.model_name,
                "api_key": self.api_key,
                "max_retries": self.max_retries,
            }
            if not any(m in self.model_name for m in NO_TEMP_MODELS):
                kwargs["temperature"] = 0.3

            llm = ChatOpenAI(**kwargs)
            self._llm = llm.bind_tools(ASSISTANT_TOOLS)
        return self._llm

    def respond(self, chat_history: List[Dict[str, str]]) -> str:
        """Generate a response given the chat history.

        Args:
            chat_history: List of {role: "user"|"assistant", content: str} dicts.

        Returns:
            Assistant response text (may contain [[ACTION:...]] markers).
        """
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

        llm = self._get_llm()

        # Build messages
        messages = [SystemMessage(content=ASSISTANT_SYSTEM_PROMPT)]
        for msg in chat_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        # Iterative tool-call loop
        for _ in range(self.MAX_TOOL_ITERATIONS):
            response = llm.invoke(messages)

            # If no tool calls, return the text content
            if not response.tool_calls:
                return response.content or ""

            # Process tool calls
            messages.append(response)

            tool_map = {t.name: t for t in ASSISTANT_TOOLS}
            for tc in response.tool_calls:
                tool_fn = tool_map.get(tc["name"])
                if tool_fn:
                    try:
                        result = tool_fn.invoke(tc["args"])
                    except Exception as e:
                        result = f"Tool error: {e}"
                else:
                    result = f"Unknown tool: {tc['name']}"

                from langchain_core.messages import ToolMessage

                messages.append(
                    ToolMessage(content=str(result), tool_call_id=tc["id"])
                )

        # If we exhausted iterations, get a final response without tools
        # by asking the LLM to summarize what it found
        messages.append(
            HumanMessage(
                content="Please provide your final answer based on the information gathered so far."
            )
        )
        final = llm.invoke(messages)
        return final.content or ""
