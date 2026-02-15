"""
tradingagents/dataflows/portfolio_risk.py

Pre-execution risk guardrails and portfolio-wide context for trading decisions.

Provides:
- PortfolioContext: snapshot of the full portfolio (equity, positions, sectors)
- validate_trade(): enforces hard limits before order execution
- format_portfolio_context_for_prompt(): formats context for LLM injection
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class PositionInfo:
    """Snapshot of a single position."""
    symbol: str
    qty: float
    market_value: float
    avg_entry: float
    sector: str
    unrealized_pl: float
    side: str  # "long" or "short"


@dataclass
class PortfolioContext:
    """Full portfolio snapshot for risk checks and prompt injection."""
    equity: float
    buying_power: float
    cash: float
    positions: List[PositionInfo] = field(default_factory=list)
    sector_breakdown: Dict[str, float] = field(default_factory=dict)
    # Risk limits (from system settings)
    max_per_trade_pct: float = 3.0
    max_single_position_pct: float = 8.0
    max_total_exposure_pct: float = 15.0

    @property
    def total_exposure(self) -> float:
        """Sum of absolute market values of all positions."""
        return sum(abs(p.market_value) for p in self.positions)

    @property
    def remaining_deployment_capacity(self) -> float:
        """How much more capital can be deployed before hitting total exposure limit."""
        limit = self.equity * (self.max_total_exposure_pct / 100.0)
        return max(0.0, limit - self.total_exposure)

    def get_position_for_symbol(self, symbol: str) -> Optional[PositionInfo]:
        """Look up a position by symbol (case-insensitive, normalizes crypto slashes)."""
        normalized = symbol.upper().replace("/", "")
        for pos in self.positions:
            if pos.symbol.upper().replace("/", "") == normalized:
                return pos
        return None


@dataclass
class TradeValidationResult:
    """Output of validate_trade()."""
    allowed: bool
    original_amount: float
    adjusted_amount: float
    rejections: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    checks_performed: Dict[str, bool] = field(default_factory=dict)


def build_portfolio_context(settings: Dict[str, Any]) -> Optional[PortfolioContext]:
    """Build a PortfolioContext from live Alpaca data.

    Args:
        settings: system_settings dict containing risk limit percentages.

    Returns:
        PortfolioContext or None if Alpaca data is unavailable.
    """
    try:
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils

        account_info = AlpacaUtils.get_account_info()
        positions_data = AlpacaUtils.get_positions_data()

        equity = float(account_info.get("equity", 0))
        buying_power = float(account_info.get("buying_power", 0))
        cash = float(account_info.get("cash", 0))

        positions: List[PositionInfo] = []
        sector_breakdown: Dict[str, float] = {}

        for pos in positions_data:
            symbol = pos.get("Symbol", "")
            qty = float(pos.get("Qty", 0))
            market_value = float(pos.get("market_value_raw", 0))
            avg_entry = float(pos.get("avg_entry_raw", 0))
            side = pos.get("side", "long")
            unrealized_pl = float(pos.get("total_pl_dollars_raw", 0))

            # Determine sector
            is_crypto = "/" in symbol or "USD" in symbol.upper()
            if is_crypto:
                sector = "Crypto"
            else:
                try:
                    from tradingagents.dataflows.sector_utils import identify_sector
                    sector_info = identify_sector(symbol)
                    sector = sector_info.get("sector", "Unknown")
                except Exception:
                    sector = "Unknown"

            positions.append(PositionInfo(
                symbol=symbol,
                qty=qty,
                market_value=market_value,
                avg_entry=avg_entry,
                sector=sector,
                unrealized_pl=unrealized_pl,
                side=side,
            ))

            # Aggregate sector exposure
            sector_breakdown[sector] = sector_breakdown.get(sector, 0.0) + abs(market_value)

        ctx = PortfolioContext(
            equity=equity,
            buying_power=buying_power,
            cash=cash,
            positions=positions,
            sector_breakdown=sector_breakdown,
            max_per_trade_pct=float(settings.get("risk_max_per_trade_pct", 3.0)),
            max_single_position_pct=float(settings.get("risk_max_single_position_pct", 8.0)),
            max_total_exposure_pct=float(settings.get("risk_max_total_exposure_pct", 15.0)),
        )
        print(f"[RISK] Built portfolio context: equity=${equity:,.2f}, "
              f"{len(positions)} positions, total_exposure=${ctx.total_exposure:,.2f}")
        return ctx

    except Exception as e:
        print(f"[RISK] Failed to build portfolio context: {e}")
        import traceback
        traceback.print_exc()
        return None


# Minimum dollar amount for a trade to be considered viable after resizing
_MIN_TRADE_AMOUNT = 10.0


def validate_trade(
    symbol: str,
    dollar_amount: float,
    signal: str,
    context: Optional[PortfolioContext],
    guardrails_enabled: bool = True,
) -> TradeValidationResult:
    """Validate a proposed trade against portfolio risk limits.

    Runs 4 sequential checks:
      1. Per-trade limit
      2. Single position limit
      3. Total exposure limit
      4. Buying power

    If a check fails, the amount is resized downward when possible.
    If resizing drops below _MIN_TRADE_AMOUNT, the trade is rejected.

    Args:
        symbol: Ticker symbol.
        dollar_amount: Proposed trade amount in dollars.
        signal: Recommended action (BUY, SELL, HOLD, LONG, SHORT, NEUTRAL).
        context: PortfolioContext (may be None).
        guardrails_enabled: Master toggle from system settings.

    Returns:
        TradeValidationResult with adjusted amount, rejections, and warnings.
    """
    result = TradeValidationResult(
        allowed=True,
        original_amount=dollar_amount,
        adjusted_amount=dollar_amount,
    )

    # Pass-through if guardrails disabled
    if not guardrails_enabled:
        result.checks_performed["guardrails_enabled"] = False
        return result
    result.checks_performed["guardrails_enabled"] = True

    # HOLD / NEUTRAL signals don't deploy capital — always pass
    signal_upper = (signal or "").upper()
    if signal_upper in ("HOLD", "NEUTRAL"):
        result.checks_performed["signal_passthrough"] = True
        return result

    # If no context available, warn but allow (fallback)
    if context is None:
        result.warnings.append("Portfolio context unavailable — guardrail checks skipped")
        result.checks_performed["context_available"] = False
        return result
    result.checks_performed["context_available"] = True

    equity = context.equity
    if equity <= 0:
        result.allowed = False
        result.adjusted_amount = 0.0
        result.rejections.append("Account equity is zero or negative — cannot trade")
        return result

    amount = dollar_amount

    # --- Check 1: Per-trade limit ---
    per_trade_limit = equity * (context.max_per_trade_pct / 100.0)
    if amount > per_trade_limit:
        result.warnings.append(
            f"Per-trade limit: ${amount:,.2f} exceeds {context.max_per_trade_pct}% of equity "
            f"(${per_trade_limit:,.2f}). Resizing to ${per_trade_limit:,.2f}."
        )
        amount = per_trade_limit
    result.checks_performed["per_trade_limit"] = True

    # --- Check 2: Single position limit ---
    existing_position = context.get_position_for_symbol(symbol)
    existing_value = abs(existing_position.market_value) if existing_position else 0.0
    single_limit = equity * (context.max_single_position_pct / 100.0)
    if existing_value + amount > single_limit:
        available = max(0.0, single_limit - existing_value)
        if available < _MIN_TRADE_AMOUNT:
            result.allowed = False
            result.adjusted_amount = 0.0
            result.rejections.append(
                f"Single position limit: existing ${existing_value:,.2f} + proposed ${amount:,.2f} "
                f"exceeds {context.max_single_position_pct}% of equity (${single_limit:,.2f}). "
                f"Only ${available:,.2f} available — below minimum."
            )
            return result
        result.warnings.append(
            f"Single position limit: resized from ${amount:,.2f} to ${available:,.2f} "
            f"(existing position ${existing_value:,.2f} + trade must stay under ${single_limit:,.2f})."
        )
        amount = available
    result.checks_performed["single_position_limit"] = True

    # --- Check 3: Total exposure limit ---
    remaining = context.remaining_deployment_capacity
    if amount > remaining:
        if remaining < _MIN_TRADE_AMOUNT:
            result.allowed = False
            result.adjusted_amount = 0.0
            result.rejections.append(
                f"Total exposure limit: only ${remaining:,.2f} capacity remaining "
                f"({context.max_total_exposure_pct}% of equity). Trade rejected."
            )
            return result
        result.warnings.append(
            f"Total exposure limit: resized from ${amount:,.2f} to ${remaining:,.2f} "
            f"(portfolio exposure at ${context.total_exposure:,.2f}/{equity * context.max_total_exposure_pct / 100.0:,.2f})."
        )
        amount = remaining
    result.checks_performed["total_exposure_limit"] = True

    # --- Check 4: Buying power ---
    if amount > context.buying_power:
        available_bp = context.buying_power
        if available_bp < _MIN_TRADE_AMOUNT:
            result.allowed = False
            result.adjusted_amount = 0.0
            result.rejections.append(
                f"Buying power: only ${available_bp:,.2f} available. Trade rejected."
            )
            return result
        result.warnings.append(
            f"Buying power: resized from ${amount:,.2f} to ${available_bp:,.2f}."
        )
        amount = available_bp
    result.checks_performed["buying_power"] = True

    result.adjusted_amount = amount
    return result


def format_portfolio_context_for_prompt(ctx: Optional[PortfolioContext]) -> str:
    """Format PortfolioContext as human-readable text for LLM prompt injection.

    Returns empty string if ctx is None.
    """
    if ctx is None:
        return ""

    lines = [
        "=== PORTFOLIO-WIDE CONTEXT ===",
        f"Account Equity: ${ctx.equity:,.2f}",
        f"Buying Power: ${ctx.buying_power:,.2f}",
        f"Cash: ${ctx.cash:,.2f}",
        f"Total Exposure: ${ctx.total_exposure:,.2f} "
        f"({ctx.total_exposure / ctx.equity * 100:.1f}% of equity)" if ctx.equity > 0 else f"Total Exposure: ${ctx.total_exposure:,.2f}",
        f"Remaining Deployment Capacity: ${ctx.remaining_deployment_capacity:,.2f}",
        "",
    ]

    if ctx.positions:
        lines.append(f"Open Positions ({len(ctx.positions)}):")
        for pos in ctx.positions:
            pl_sign = "+" if pos.unrealized_pl >= 0 else ""
            lines.append(
                f"  - {pos.symbol}: {pos.qty} shares @ ${pos.avg_entry:,.2f} "
                f"(MV ${pos.market_value:,.2f}, P/L {pl_sign}${pos.unrealized_pl:,.2f}, "
                f"Sector: {pos.sector})"
            )
        lines.append("")
    else:
        lines.append("Open Positions: None")
        lines.append("")

    if ctx.sector_breakdown:
        lines.append("Sector Exposure:")
        for sector, value in sorted(ctx.sector_breakdown.items(), key=lambda x: -x[1]):
            pct = (value / ctx.equity * 100) if ctx.equity > 0 else 0
            lines.append(f"  - {sector}: ${value:,.2f} ({pct:.1f}%)")
        lines.append("")

    lines.append(
        f"Risk Limits: {ctx.max_per_trade_pct}% per trade, "
        f"{ctx.max_single_position_pct}% single position, "
        f"{ctx.max_total_exposure_pct}% total exposure"
    )
    lines.append("=== END PORTFOLIO CONTEXT ===")

    return "\n".join(lines)
