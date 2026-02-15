"""
tests/webui/test_portfolio_panel.py
Tests for the Portfolio Overview panel component and its render helpers.
"""

import pytest
from unittest.mock import patch, MagicMock
from tradingagents.dataflows.portfolio_risk import PortfolioContext, PositionInfo


class TestCreatePortfolioPanel:
    """Tests for the create_portfolio_panel() function."""

    def test_create_portfolio_panel_returns_card(self):
        """Verify create_portfolio_panel returns a dbc.Card component."""
        from webui.components.portfolio_panel import create_portfolio_panel
        import dash_bootstrap_components as dbc

        result = create_portfolio_panel()
        assert isinstance(result, dbc.Card)

    def test_create_portfolio_panel_has_expected_ids(self):
        """Verify the panel contains all 4 placeholder container IDs."""
        from webui.components.portfolio_panel import create_portfolio_panel

        panel = create_portfolio_panel()
        # Convert to string representation to check IDs are present
        panel_str = str(panel)
        assert "portfolio-metrics-row" in panel_str
        assert "portfolio-risk-bars" in panel_str
        assert "portfolio-sector-chart" in panel_str
        assert "portfolio-config-summary" in panel_str


class TestRenderPortfolioMetrics:
    """Tests for the render_portfolio_metrics() helper."""

    def _make_context(self, equity=100000, positions=None):
        """Create a PortfolioContext for testing."""
        if positions is None:
            positions = [
                PositionInfo(
                    symbol="AAPL", qty=10, market_value=5000,
                    avg_entry=480, sector="Technology",
                    unrealized_pl=200, side="long",
                ),
                PositionInfo(
                    symbol="MSFT", qty=5, market_value=3000,
                    avg_entry=580, sector="Technology",
                    unrealized_pl=-50, side="long",
                ),
            ]
        return PortfolioContext(
            equity=equity,
            buying_power=80000,
            cash=50000,
            positions=positions,
            sector_breakdown={"Technology": 8000},
            max_per_trade_pct=3.0,
            max_single_position_pct=8.0,
            max_total_exposure_pct=15.0,
        )

    def test_render_portfolio_metrics_with_context(self):
        """Verify stat cards contain equity/exposure/P&L values."""
        from webui.components.portfolio_panel import render_portfolio_metrics

        ctx = self._make_context()
        result = render_portfolio_metrics(ctx)
        result_str = str(result)

        # Should contain equity value
        assert "$100,000.00" in result_str
        # Total exposure = 5000 + 3000 = 8000
        assert "$8,000.00" in result_str
        # Unrealized P/L = 200 + (-50) = 150
        assert "$150.00" in result_str

    def test_render_portfolio_metrics_no_positions(self):
        """Verify graceful handling when no positions exist."""
        from webui.components.portfolio_panel import render_portfolio_metrics

        ctx = self._make_context(positions=[])
        result = render_portfolio_metrics(ctx)
        result_str = str(result)

        # Should still show equity
        assert "$100,000.00" in result_str
        # Exposure should be zero
        assert "$0.00" in result_str

    def test_render_portfolio_metrics_zero_equity(self):
        """Verify no division by zero when equity is 0."""
        from webui.components.portfolio_panel import render_portfolio_metrics

        ctx = self._make_context(equity=0, positions=[])
        result = render_portfolio_metrics(ctx)
        # Should not raise an error
        assert result is not None


class TestRenderRiskUtilization:
    """Tests for the render_risk_utilization() helper."""

    def _make_context(self, equity=100000, positions=None):
        if positions is None:
            positions = [
                PositionInfo(
                    symbol="AAPL", qty=10, market_value=5000,
                    avg_entry=480, sector="Technology",
                    unrealized_pl=200, side="long",
                ),
            ]
        return PortfolioContext(
            equity=equity,
            buying_power=80000,
            cash=50000,
            positions=positions,
            sector_breakdown={"Technology": 5000},
            max_per_trade_pct=3.0,
            max_single_position_pct=8.0,
            max_total_exposure_pct=15.0,
        )

    def test_render_risk_utilization_bars(self):
        """Verify 3 progress bar sections are present."""
        from webui.components.portfolio_panel import render_risk_utilization

        ctx = self._make_context()
        result = render_risk_utilization(ctx)
        result_str = str(result)

        assert "Per-Trade Limit" in result_str
        assert "Largest Position" in result_str
        assert "Total Exposure" in result_str

    def test_render_risk_utilization_correct_percentages(self):
        """Verify the percentage calculations are correct."""
        from webui.components.portfolio_panel import render_risk_utilization

        ctx = self._make_context()
        result = render_risk_utilization(ctx)
        result_str = str(result)

        # Largest position = 5000/100000 = 5.0%
        assert "5.0%" in result_str
        # Total exposure = 5000/100000 = 5.0%
        assert "5.0%" in result_str

    def test_render_risk_utilization_zero_equity(self):
        """Verify graceful handling when equity is 0."""
        from webui.components.portfolio_panel import render_risk_utilization

        ctx = self._make_context(equity=0, positions=[])
        result = render_risk_utilization(ctx)
        result_str = str(result)
        assert "No equity data" in result_str


class TestRenderSectorExposure:
    """Tests for the render_sector_exposure() helper."""

    def test_render_sector_exposure(self):
        """Verify sector names and values appear."""
        from webui.components.portfolio_panel import render_sector_exposure

        ctx = PortfolioContext(
            equity=100000, buying_power=80000, cash=50000,
            positions=[],
            sector_breakdown={"Technology": 5000, "Healthcare": 3000},
            max_per_trade_pct=3.0,
            max_single_position_pct=8.0,
            max_total_exposure_pct=15.0,
        )
        result = render_sector_exposure(ctx)
        result_str = str(result)

        assert "Technology" in result_str
        assert "Healthcare" in result_str
        assert "$5,000" in result_str
        assert "$3,000" in result_str

    def test_render_sector_exposure_no_positions(self):
        """Verify graceful fallback when no positions."""
        from webui.components.portfolio_panel import render_sector_exposure

        ctx = PortfolioContext(
            equity=100000, buying_power=80000, cash=50000,
            positions=[], sector_breakdown={},
        )
        result = render_sector_exposure(ctx)
        result_str = str(result)
        assert "No positions" in result_str


class TestRenderConfigSummary:
    """Tests for the render_config_summary() helper."""

    def test_render_config_summary(self):
        """Verify LLM model names and trading mode badges appear."""
        from webui.components.portfolio_panel import render_config_summary

        settings = {
            "deep_think_llm": "o4-mini",
            "quick_think_llm": "gpt-4.1-nano",
            "max_debate_rounds": 4,
            "max_risk_discuss_rounds": 3,
            "allow_shorts": False,
            "risk_guardrails_enabled": True,
            "enable_stop_loss": True,
            "stop_loss_percentage": 5.0,
            "enable_take_profit": False,
            "online_tools": True,
        }
        result = render_config_summary(settings)
        result_str = str(result)

        assert "o4-mini" in result_str
        assert "gpt-4.1-nano" in result_str
        assert "Long Only" in result_str
        assert "Guardrails ON" in result_str
        assert "SL 5.0%" in result_str
        assert "Live Data" in result_str

    def test_render_config_summary_shorts_enabled(self):
        """Verify Long/Short mode badge when shorts are allowed."""
        from webui.components.portfolio_panel import render_config_summary

        settings = {
            "allow_shorts": True,
            "risk_guardrails_enabled": False,
            "online_tools": False,
        }
        result = render_config_summary(settings)
        result_str = str(result)

        assert "Long/Short" in result_str
        assert "Guardrails OFF" in result_str
        assert "Cached Data" in result_str

    def test_render_config_summary_defaults(self):
        """Verify render works with empty settings (all defaults)."""
        from webui.components.portfolio_panel import render_config_summary

        result = render_config_summary({})
        assert result is not None
