"""
Tests for tradingagents/dataflows/portfolio_risk.py

Covers: PortfolioContext, build_portfolio_context, validate_trade, format_portfolio_context_for_prompt.
"""

import pytest
from unittest.mock import patch, MagicMock

from tradingagents.dataflows.portfolio_risk import (
    PositionInfo,
    PortfolioContext,
    TradeValidationResult,
    build_portfolio_context,
    validate_trade,
    format_portfolio_context_for_prompt,
    _MIN_TRADE_AMOUNT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_position(symbol="AAPL", qty=10, market_value=1500.0, avg_entry=150.0,
                   sector="Technology", unrealized_pl=50.0, side="long"):
    return PositionInfo(
        symbol=symbol, qty=qty, market_value=market_value, avg_entry=avg_entry,
        sector=sector, unrealized_pl=unrealized_pl, side=side,
    )


def _make_context(equity=100_000.0, buying_power=50_000.0, cash=50_000.0,
                  positions=None, per_trade=3.0, single=8.0, total=15.0):
    return PortfolioContext(
        equity=equity,
        buying_power=buying_power,
        cash=cash,
        positions=positions or [],
        max_per_trade_pct=per_trade,
        max_single_position_pct=single,
        max_total_exposure_pct=total,
    )


# ===========================================================================
# TestPortfolioContext
# ===========================================================================

class TestPortfolioContext:
    """Tests for PortfolioContext dataclass properties and methods."""

    def test_total_exposure_empty(self):
        ctx = _make_context(positions=[])
        assert ctx.total_exposure == 0.0

    def test_total_exposure_sums_abs_market_values(self):
        positions = [
            _make_position(symbol="AAPL", market_value=5000.0),
            _make_position(symbol="TSLA", market_value=-3000.0),  # short
        ]
        ctx = _make_context(positions=positions)
        assert ctx.total_exposure == 8000.0  # abs(5000) + abs(-3000)

    def test_remaining_deployment_capacity(self):
        # equity=100k, total_exposure_pct=15% → limit=15k, exposure=5k → remaining=10k
        positions = [_make_position(market_value=5000.0)]
        ctx = _make_context(equity=100_000, positions=positions, total=15.0)
        assert ctx.remaining_deployment_capacity == 10_000.0

    def test_remaining_deployment_capacity_capped_at_zero(self):
        # Over the limit already
        positions = [_make_position(market_value=20_000.0)]
        ctx = _make_context(equity=100_000, positions=positions, total=15.0)
        assert ctx.remaining_deployment_capacity == 0.0

    def test_get_position_for_symbol_found(self):
        pos = _make_position(symbol="AAPL")
        ctx = _make_context(positions=[pos])
        assert ctx.get_position_for_symbol("AAPL") is pos

    def test_get_position_for_symbol_case_insensitive(self):
        pos = _make_position(symbol="aapl")
        ctx = _make_context(positions=[pos])
        assert ctx.get_position_for_symbol("AAPL") is pos

    def test_get_position_for_symbol_crypto_normalization(self):
        pos = _make_position(symbol="BTC/USD")
        ctx = _make_context(positions=[pos])
        assert ctx.get_position_for_symbol("BTCUSD") is pos
        assert ctx.get_position_for_symbol("BTC/USD") is pos

    def test_get_position_for_symbol_not_found(self):
        ctx = _make_context(positions=[_make_position(symbol="AAPL")])
        assert ctx.get_position_for_symbol("MSFT") is None


# ===========================================================================
# TestBuildPortfolioContext
# ===========================================================================

class TestBuildPortfolioContext:
    """Tests for build_portfolio_context() factory."""

    @patch("tradingagents.dataflows.sector_utils.identify_sector")
    @patch("tradingagents.dataflows.alpaca_utils.AlpacaUtils")
    def test_builds_context_with_positions(self, mock_alpaca_cls, mock_identify):
        mock_alpaca_cls.get_account_info.return_value = {
            "equity": 100_000.0, "buying_power": 50_000.0, "cash": 50_000.0,
            "last_equity": 99_000.0, "daily_change_dollars": 1000.0, "daily_change_percent": 1.01,
        }
        mock_alpaca_cls.get_positions_data.return_value = [
            {
                "Symbol": "AAPL", "Qty": 10, "market_value_raw": 1500.0,
                "avg_entry_raw": 150.0, "side": "long", "total_pl_dollars_raw": 50.0,
            },
        ]
        mock_identify.return_value = {"sector": "Technology"}

        settings = {"risk_max_per_trade_pct": 5.0, "risk_max_single_position_pct": 10.0,
                     "risk_max_total_exposure_pct": 20.0}
        ctx = build_portfolio_context(settings)

        assert ctx is not None
        assert ctx.equity == 100_000.0
        assert ctx.buying_power == 50_000.0
        assert len(ctx.positions) == 1
        assert ctx.positions[0].symbol == "AAPL"
        assert ctx.positions[0].sector == "Technology"
        assert ctx.max_per_trade_pct == 5.0
        assert ctx.max_single_position_pct == 10.0
        assert ctx.max_total_exposure_pct == 20.0

    @patch("tradingagents.dataflows.alpaca_utils.AlpacaUtils")
    def test_empty_positions(self, mock_alpaca_cls):
        mock_alpaca_cls.get_account_info.return_value = {
            "equity": 50_000.0, "buying_power": 50_000.0, "cash": 50_000.0,
            "last_equity": 50_000.0, "daily_change_dollars": 0, "daily_change_percent": 0,
        }
        mock_alpaca_cls.get_positions_data.return_value = []

        ctx = build_portfolio_context({})
        assert ctx is not None
        assert len(ctx.positions) == 0
        assert ctx.total_exposure == 0.0

    @patch("tradingagents.dataflows.alpaca_utils.AlpacaUtils")
    def test_crypto_position_gets_crypto_sector(self, mock_alpaca_cls):
        mock_alpaca_cls.get_account_info.return_value = {
            "equity": 100_000.0, "buying_power": 50_000.0, "cash": 50_000.0,
            "last_equity": 100_000.0, "daily_change_dollars": 0, "daily_change_percent": 0,
        }
        mock_alpaca_cls.get_positions_data.return_value = [
            {
                "Symbol": "BTC/USD", "Qty": 0.5, "market_value_raw": 25_000.0,
                "avg_entry_raw": 50_000.0, "side": "long", "total_pl_dollars_raw": 0.0,
            },
        ]

        ctx = build_portfolio_context({})
        assert ctx.positions[0].sector == "Crypto"

    @patch("tradingagents.dataflows.alpaca_utils.AlpacaUtils")
    def test_returns_none_on_error(self, mock_alpaca_cls):
        mock_alpaca_cls.get_account_info.side_effect = Exception("API error")
        ctx = build_portfolio_context({})
        assert ctx is None


# ===========================================================================
# TestValidateTrade
# ===========================================================================

class TestValidateTrade:
    """Tests for validate_trade() risk checks."""

    def test_guardrails_disabled_passes_all(self):
        ctx = _make_context(equity=100_000)
        result = validate_trade("AAPL", 999_999, "BUY", ctx, guardrails_enabled=False)
        assert result.allowed is True
        assert result.adjusted_amount == 999_999
        assert result.checks_performed.get("guardrails_enabled") is False

    def test_hold_signal_passes(self):
        ctx = _make_context(equity=100_000)
        result = validate_trade("AAPL", 5000, "HOLD", ctx)
        assert result.allowed is True
        assert result.checks_performed.get("signal_passthrough") is True

    def test_neutral_signal_passes(self):
        ctx = _make_context(equity=100_000)
        result = validate_trade("AAPL", 5000, "NEUTRAL", ctx)
        assert result.allowed is True

    def test_no_context_warns_but_allows(self):
        result = validate_trade("AAPL", 5000, "BUY", None)
        assert result.allowed is True
        assert len(result.warnings) == 1
        assert "unavailable" in result.warnings[0]

    def test_zero_equity_rejects(self):
        ctx = _make_context(equity=0)
        result = validate_trade("AAPL", 5000, "BUY", ctx)
        assert result.allowed is False
        assert "zero or negative" in result.rejections[0]

    def test_per_trade_resize(self):
        # equity=100k, per_trade=3% → limit=3000, request=5000 → resize to 3000
        ctx = _make_context(equity=100_000, buying_power=100_000, per_trade=3.0, total=100.0)
        result = validate_trade("AAPL", 5000, "BUY", ctx)
        assert result.allowed is True
        assert result.adjusted_amount == 3000.0
        assert len(result.warnings) >= 1
        assert "Per-trade limit" in result.warnings[0]

    def test_single_position_reject_at_cap(self):
        # equity=100k, single=8% → limit=8000, existing=7995, request=100 → available=5 < min
        existing = _make_position(symbol="AAPL", market_value=7995.0)
        ctx = _make_context(equity=100_000, buying_power=100_000, positions=[existing],
                            per_trade=100.0, single=8.0, total=100.0)
        result = validate_trade("AAPL", 100, "BUY", ctx)
        assert result.allowed is False
        assert "Single position limit" in result.rejections[0]

    def test_single_position_resize(self):
        # equity=100k, single=8% → limit=8000, existing=5000, request=5000 → resize to 3000
        existing = _make_position(symbol="AAPL", market_value=5000.0)
        ctx = _make_context(equity=100_000, buying_power=100_000, positions=[existing],
                            per_trade=100.0, single=8.0, total=100.0)
        result = validate_trade("AAPL", 5000, "BUY", ctx)
        assert result.allowed is True
        assert result.adjusted_amount == 3000.0

    def test_total_exposure_resize(self):
        # equity=100k, total=15% → limit=15000, existing exposure=10000, request=10000 → resize to 5000
        existing = _make_position(symbol="MSFT", market_value=10_000.0)
        ctx = _make_context(equity=100_000, buying_power=100_000, positions=[existing],
                            per_trade=100.0, single=100.0, total=15.0)
        result = validate_trade("AAPL", 10_000, "BUY", ctx)
        assert result.allowed is True
        assert result.adjusted_amount == 5000.0

    def test_total_exposure_reject_when_full(self):
        # exposure=15000 already, remaining=0
        existing = _make_position(symbol="MSFT", market_value=15_000.0)
        ctx = _make_context(equity=100_000, buying_power=100_000, positions=[existing],
                            per_trade=100.0, single=100.0, total=15.0)
        result = validate_trade("AAPL", 1000, "BUY", ctx)
        assert result.allowed is False
        assert "Total exposure limit" in result.rejections[0]

    def test_buying_power_resize(self):
        # buying_power=2000, request=5000 → resize to 2000
        ctx = _make_context(equity=100_000, buying_power=2000, per_trade=100.0,
                            single=100.0, total=100.0)
        result = validate_trade("AAPL", 5000, "BUY", ctx)
        assert result.allowed is True
        assert result.adjusted_amount == 2000.0

    def test_buying_power_reject_below_minimum(self):
        ctx = _make_context(equity=100_000, buying_power=5.0, per_trade=100.0,
                            single=100.0, total=100.0)
        result = validate_trade("AAPL", 5000, "BUY", ctx)
        assert result.allowed is False
        assert "Buying power" in result.rejections[0]

    def test_minimum_amount_floor(self):
        assert _MIN_TRADE_AMOUNT == 10.0

    def test_sell_signal_also_validated(self):
        # SELL is a capital-deploying action (closing short / entering inverse)
        ctx = _make_context(equity=100_000, buying_power=50_000, per_trade=3.0, total=100.0)
        result = validate_trade("AAPL", 5000, "SELL", ctx)
        assert result.allowed is True
        # Should still be resized by per-trade limit
        assert result.adjusted_amount == 3000.0

    def test_all_checks_pass_no_resize(self):
        # Small trade within all limits
        ctx = _make_context(equity=100_000, buying_power=50_000, per_trade=5.0,
                            single=10.0, total=20.0)
        result = validate_trade("AAPL", 1000, "BUY", ctx)
        assert result.allowed is True
        assert result.adjusted_amount == 1000.0
        assert len(result.warnings) == 0
        assert len(result.rejections) == 0


# ===========================================================================
# TestFormatPortfolioContext
# ===========================================================================

class TestFormatPortfolioContext:
    """Tests for format_portfolio_context_for_prompt()."""

    def test_none_returns_empty_string(self):
        assert format_portfolio_context_for_prompt(None) == ""

    def test_output_contains_equity(self):
        ctx = _make_context(equity=100_000, buying_power=50_000, cash=50_000)
        text = format_portfolio_context_for_prompt(ctx)
        assert "100,000.00" in text
        assert "PORTFOLIO-WIDE CONTEXT" in text

    def test_output_contains_positions(self):
        pos = _make_position(symbol="AAPL", market_value=1500.0, unrealized_pl=50.0)
        ctx = _make_context(equity=100_000, positions=[pos])
        text = format_portfolio_context_for_prompt(ctx)
        assert "AAPL" in text
        assert "Open Positions (1)" in text

    def test_output_contains_sector_breakdown(self):
        pos = _make_position(symbol="AAPL", market_value=1500.0, sector="Technology")
        ctx = _make_context(equity=100_000, positions=[pos])
        ctx.sector_breakdown = {"Technology": 1500.0}
        text = format_portfolio_context_for_prompt(ctx)
        assert "Sector Exposure" in text
        assert "Technology" in text

    def test_output_contains_risk_limits(self):
        ctx = _make_context(per_trade=3.0, single=8.0, total=15.0)
        text = format_portfolio_context_for_prompt(ctx)
        assert "3.0% per trade" in text
        assert "8.0% single position" in text
        assert "15.0% total exposure" in text

    def test_no_positions_message(self):
        ctx = _make_context(positions=[])
        text = format_portfolio_context_for_prompt(ctx)
        assert "Open Positions: None" in text
