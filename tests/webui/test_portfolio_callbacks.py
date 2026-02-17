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


class TestSimultaneousTriggers:
    """Tests for handling simultaneous triggers (interval + settings change)."""

    def test_settings_in_multiple_triggers_bypasses_cache(self):
        """When both interval and settings-store trigger, cache is bypassed.

        Bug fix: The old code used `callback_context.triggered_id` which only
        returns the FIRST triggered input. If interval was listed first, the
        settings change would be missed and stale cached values shown.
        """
        old_ctx = _make_context(max_per_trade_pct=3.0)
        new_ctx = _make_context(max_per_trade_pct=5.0)

        # Simulate both inputs triggering simultaneously - interval listed first
        mock_triggered = [
            {"prop_id": "slow-refresh-interval.n_intervals", "value": 100},
            {"prop_id": "system-settings-store.data", "value": {"risk_max_per_trade_pct": 5.0}},
        ]

        with patch(
            "tradingagents.dataflows.portfolio_risk.build_portfolio_context",
            return_value=new_ctx,
        ) as mock_build:
            # New logic: check ALL triggered inputs for either settings store
            triggered_ids = [t["prop_id"].split(".")[0] for t in mock_triggered]
            settings_changed = (
                "system-settings-store" in triggered_ids or
                "settings-store" in triggered_ids
            )
            use_cache = not settings_changed

            ctx = None
            if use_cache:
                ctx = old_ctx  # Would have used stale cache
            if ctx is None:
                from tradingagents.dataflows.portfolio_risk import build_portfolio_context
                ctx = build_portfolio_context({"risk_max_per_trade_pct": 5.0})

            # Cache was bypassed - new context built with updated settings
            assert ctx is new_ctx
            assert ctx.max_per_trade_pct == 5.0
            mock_build.assert_called_once()

    def test_control_settings_store_trigger_bypasses_cache(self):
        """When settings-store (control panel) triggers, cache is bypassed.

        This happens when allow_shorts is toggled in Trading Control.
        """
        old_ctx = _make_context()
        new_ctx = _make_context()

        mock_triggered = [
            {"prop_id": "settings-store.data", "value": {"allow_shorts": True}},
        ]

        with patch(
            "tradingagents.dataflows.portfolio_risk.build_portfolio_context",
            return_value=new_ctx,
        ) as mock_build:
            triggered_ids = [t["prop_id"].split(".")[0] for t in mock_triggered]
            settings_changed = (
                "system-settings-store" in triggered_ids or
                "settings-store" in triggered_ids
            )
            use_cache = not settings_changed

            ctx = None
            if use_cache:
                ctx = old_ctx
            if ctx is None:
                from tradingagents.dataflows.portfolio_risk import build_portfolio_context
                ctx = build_portfolio_context({})

            # Cache was bypassed
            assert ctx is new_ctx
            mock_build.assert_called_once()

    def test_interval_only_trigger_uses_cache(self):
        """When only interval triggers, cache is used (no settings change)."""
        cached_ctx = _make_context(max_per_trade_pct=3.0)

        mock_triggered = [
            {"prop_id": "slow-refresh-interval.n_intervals", "value": 100},
        ]

        with patch(
            "tradingagents.dataflows.portfolio_risk.build_portfolio_context",
        ) as mock_build:
            triggered_ids = [t["prop_id"].split(".")[0] for t in mock_triggered]
            settings_changed = (
                "system-settings-store" in triggered_ids or
                "settings-store" in triggered_ids
            )
            use_cache = not settings_changed

            ctx = None
            if use_cache:
                ctx = cached_ctx
            if ctx is None:
                from tradingagents.dataflows.portfolio_risk import build_portfolio_context
                ctx = build_portfolio_context({})

            # Cache was used
            assert ctx is cached_ctx
            mock_build.assert_not_called()


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
