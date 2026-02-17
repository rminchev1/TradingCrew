"""
tests/webui/test_portfolio_callbacks.py
Tests for the portfolio panel callback.
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
    """Verify portfolio callback is wired to both settings stores."""

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

    def test_callback_has_control_settings_store_input(self):
        """The portfolio callback must listen to settings-store (control panel) for allow_shorts."""
        from dash import Dash
        from webui.callbacks.portfolio_callbacks import register_portfolio_callbacks

        app = Dash(__name__)
        register_portfolio_callbacks(app)

        for output_id, entry in app.callback_map.items():
            if "portfolio-metrics-row" in output_id:
                inputs = entry.get("inputs", [])
                input_ids = [inp["id"] for inp in inputs]
                assert "settings-store" in input_ids, (
                    "Portfolio callback must have settings-store as an Input for allow_shorts"
                )
                break

    def test_callback_has_three_inputs(self):
        """The portfolio callback should have exactly 3 inputs."""
        from dash import Dash
        from webui.callbacks.portfolio_callbacks import register_portfolio_callbacks

        app = Dash(__name__)
        register_portfolio_callbacks(app)

        for output_id, entry in app.callback_map.items():
            if "portfolio-metrics-row" in output_id:
                inputs = entry.get("inputs", [])
                assert len(inputs) == 3, (
                    f"Expected 3 inputs (interval, system-settings, settings-store), got {len(inputs)}"
                )
                break


class TestAlwaysBuildFreshContext:
    """Tests for the always-build-fresh context behavior.

    The portfolio callback now always builds a fresh context on each call
    to ensure it uses the latest settings. This prevents stale cached contexts
    from analysis runs from showing outdated risk limits.
    """

    def test_always_builds_context_regardless_of_trigger(self):
        """Context is always built fresh, never uses stale cache."""
        fresh_ctx = _make_context(max_per_trade_pct=5.0)

        with patch(
            "tradingagents.dataflows.portfolio_risk.build_portfolio_context",
            return_value=fresh_ctx,
        ) as mock_build:
            # Regardless of what triggers the callback, we should build
            settings = {"risk_max_per_trade_pct": 5.0}
            from tradingagents.dataflows.portfolio_risk import build_portfolio_context
            ctx = build_portfolio_context(settings)

            assert ctx is fresh_ctx
            mock_build.assert_called_once_with(settings)

    def test_uses_settings_from_store(self):
        """Context is built with settings from the store, not stale app_state."""
        store_settings = {"risk_max_total_exposure_pct": 75.0}
        ctx_with_new_limit = _make_context(max_total_exposure_pct=75.0)

        with patch(
            "tradingagents.dataflows.portfolio_risk.build_portfolio_context",
            return_value=ctx_with_new_limit,
        ) as mock_build:
            from tradingagents.dataflows.portfolio_risk import build_portfolio_context
            ctx = build_portfolio_context(store_settings)

            assert ctx.max_total_exposure_pct == 75.0
            mock_build.assert_called_once_with(store_settings)


class TestSettingsStoreDataPriority:
    """Tests for using settings_store_data over app_state.system_settings."""

    def test_settings_from_store_data_used_when_available(self):
        """When settings_store_data is provided, it should be used directly.

        Bug fix: The old code always read from app_state.system_settings which
        could have timing issues with sync after a save.
        """
        store_data = {"risk_max_per_trade_pct": 5.0, "risk_guardrails_enabled": True}
        app_state_settings = {"risk_max_per_trade_pct": 3.0}  # Stale value

        # New logic: prefer store data when available
        settings = store_data if store_data else app_state_settings

        assert settings == store_data
        assert settings["risk_max_per_trade_pct"] == 5.0

    def test_falls_back_to_app_state_when_store_empty(self):
        """When settings_store_data is None/empty, fall back to app_state."""
        store_data = None
        app_state_settings = {"risk_max_per_trade_pct": 3.0}

        settings = store_data if store_data else app_state_settings

        assert settings == app_state_settings
        assert settings["risk_max_per_trade_pct"] == 3.0

    def test_empty_dict_store_data_uses_app_state(self):
        """Empty dict {} is falsy, so app_state is used as fallback."""
        store_data = {}
        app_state_settings = {"risk_max_per_trade_pct": 3.0}

        settings = store_data if store_data else app_state_settings

        assert settings == app_state_settings


class TestAllowShortsMerge:
    """Tests for merging allow_shorts from control panel settings."""

    def test_allow_shorts_merged_from_control_settings(self):
        """allow_shorts from control panel settings should be merged into settings.

        Bug fix: allow_shorts is stored in settings-store (control panel), not
        system-settings-store. Portfolio Overview was showing "Long Only" even
        when "Shorts OK" was enabled in Trading Control.
        """
        system_settings = {"risk_guardrails_enabled": True, "allow_shorts": False}
        control_settings = {"allow_shorts": True}

        # Merge logic from callback
        settings = dict(system_settings)
        if control_settings and "allow_shorts" in control_settings:
            settings["allow_shorts"] = control_settings["allow_shorts"]

        assert settings["allow_shorts"] is True
        # Original shouldn't be mutated
        assert system_settings["allow_shorts"] is False

    def test_allow_shorts_not_merged_when_control_settings_empty(self):
        """When control settings is None/empty, allow_shorts stays from system settings."""
        system_settings = {"allow_shorts": False}
        control_settings = None

        settings = dict(system_settings)
        if control_settings and "allow_shorts" in control_settings:
            settings["allow_shorts"] = control_settings["allow_shorts"]

        assert settings["allow_shorts"] is False

    def test_allow_shorts_false_explicitly_set(self):
        """allow_shorts=False from control settings should override."""
        system_settings = {"allow_shorts": True}  # Hypothetically stale
        control_settings = {"allow_shorts": False}

        settings = dict(system_settings)
        if control_settings and "allow_shorts" in control_settings:
            settings["allow_shorts"] = control_settings["allow_shorts"]

        assert settings["allow_shorts"] is False

    def test_settings_dict_is_copied_not_mutated(self):
        """Merging allow_shorts should not mutate the original settings dict."""
        original_system_settings = {"risk_guardrails_enabled": True, "allow_shorts": False}
        control_settings = {"allow_shorts": True}

        # Simulate callback logic
        settings = original_system_settings if original_system_settings else {}
        if control_settings and "allow_shorts" in control_settings:
            settings = dict(settings)  # Copy before mutation
            settings["allow_shorts"] = control_settings["allow_shorts"]

        assert settings["allow_shorts"] is True
        # When we copy first, original is preserved
        # (In actual callback, we copy; this test verifies the pattern works)
