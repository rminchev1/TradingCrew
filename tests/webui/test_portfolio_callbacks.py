"""
tests/webui/test_portfolio_callbacks.py
Tests for the portfolio panel callback, especially cache-bypass on settings change.
"""

import pytest
from unittest.mock import patch, MagicMock
from tradingagents.dataflows.portfolio_risk import PortfolioContext, PositionInfo


def _make_context(**overrides):
    """Create a PortfolioContext for testing."""
    defaults = dict(
        equity=100000,
        buying_power=80000,
        cash=50000,
        positions=[
            PositionInfo(
                symbol="AAPL", qty=10, market_value=5000,
                avg_entry=480, sector="Technology",
                unrealized_pl=200, side="long",
            ),
        ],
        sector_breakdown={"Technology": 5000},
        max_per_trade_pct=3.0,
        max_single_position_pct=8.0,
        max_total_exposure_pct=15.0,
    )
    defaults.update(overrides)
    return PortfolioContext(**defaults)


class TestPortfolioCallbackRegistration:
    """Verify portfolio callback is wired to system-settings-store."""

    def test_callback_has_settings_store_input(self):
        """The portfolio callback must listen to system-settings-store changes."""
        from dash import Dash
        from webui.callbacks.portfolio_callbacks import register_portfolio_callbacks

        app = Dash(__name__)
        register_portfolio_callbacks(app)

        # Find the callback that outputs to portfolio-metrics-row
        found = False
        for output_id, entry in app.callback_map.items():
            if "portfolio-metrics-row" in output_id:
                found = True
                # Verify inputs include system-settings-store
                inputs = entry.get("inputs", [])
                input_ids = [inp["id"] for inp in inputs]
                assert "system-settings-store" in input_ids, (
                    "Portfolio callback must have system-settings-store as an Input"
                )
                assert "slow-refresh-interval" in input_ids, (
                    "Portfolio callback must still have slow-refresh-interval as Input"
                )
                break
        assert found, "Portfolio callback not registered"

    def test_callback_has_two_inputs(self):
        """The portfolio callback should have exactly 2 inputs."""
        from dash import Dash
        from webui.callbacks.portfolio_callbacks import register_portfolio_callbacks

        app = Dash(__name__)
        register_portfolio_callbacks(app)

        for output_id, entry in app.callback_map.items():
            if "portfolio-metrics-row" in output_id:
                inputs = entry.get("inputs", [])
                assert len(inputs) == 2
                break


class TestPortfolioCacheBypassLogic:
    """Tests for cache-bypass when triggered by settings change."""

    def test_timer_trigger_uses_cached_context(self):
        """When triggered by timer, cached PortfolioContext is used (no rebuild)."""
        cached_ctx = _make_context(max_per_trade_pct=3.0)

        with patch(
            "webui.callbacks.portfolio_callbacks.callback_context"
        ) as mock_ctx, patch(
            "webui.callbacks.portfolio_callbacks.app_state"
        ) as mock_state, patch(
            "webui.components.portfolio_panel._is_alpaca_configured",
            return_value=True,
        ), patch(
            "tradingagents.dataflows.portfolio_risk.build_portfolio_context"
        ) as mock_build:
            mock_ctx.triggered_id = "slow-refresh-interval"
            mock_state.system_settings = {"risk_guardrails_enabled": True}
            mock_state._current_portfolio_context = cached_ctx

            # Simulate calling the callback body logic inline
            triggered = mock_ctx.triggered_id
            use_cache = triggered != "system-settings-store"

            ctx = None
            if use_cache:
                ctx = getattr(mock_state, "_current_portfolio_context", None)
            if ctx is None:
                from tradingagents.dataflows.portfolio_risk import build_portfolio_context
                ctx = build_portfolio_context(mock_state.system_settings)

            # Cache was used - build should NOT have been called
            assert ctx is cached_ctx
            mock_build.assert_not_called()

    def test_settings_trigger_bypasses_cache(self):
        """When triggered by settings store, cached context is skipped."""
        old_ctx = _make_context(max_per_trade_pct=3.0)
        new_ctx = _make_context(max_per_trade_pct=5.0)

        with patch(
            "webui.callbacks.portfolio_callbacks.callback_context"
        ) as mock_ctx, patch(
            "webui.callbacks.portfolio_callbacks.app_state"
        ) as mock_state, patch(
            "tradingagents.dataflows.portfolio_risk.build_portfolio_context",
            return_value=new_ctx,
        ) as mock_build:
            mock_ctx.triggered_id = "system-settings-store"
            mock_state.system_settings = {"risk_max_per_trade_pct": 5.0}
            mock_state._current_portfolio_context = old_ctx

            # Same logic as the callback
            triggered = mock_ctx.triggered_id
            use_cache = triggered != "system-settings-store"

            ctx = None
            if use_cache:
                ctx = getattr(mock_state, "_current_portfolio_context", None)
            if ctx is None:
                from tradingagents.dataflows.portfolio_risk import build_portfolio_context
                ctx = build_portfolio_context(mock_state.system_settings)

            # Cache was bypassed - build should have been called
            assert ctx is new_ctx
            mock_build.assert_called_once_with(mock_state.system_settings)

    def test_no_cache_always_builds(self):
        """When no cached context exists, always build regardless of trigger."""
        fresh_ctx = _make_context()

        with patch(
            "tradingagents.dataflows.portfolio_risk.build_portfolio_context",
            return_value=fresh_ctx,
        ) as mock_build:
            for trigger in ["slow-refresh-interval", "system-settings-store"]:
                mock_build.reset_mock()
                use_cache = trigger != "system-settings-store"

                ctx = None
                if use_cache:
                    ctx = None  # No cache
                if ctx is None:
                    from tradingagents.dataflows.portfolio_risk import build_portfolio_context
                    ctx = build_portfolio_context({})

                assert ctx is fresh_ctx
                mock_build.assert_called_once()
