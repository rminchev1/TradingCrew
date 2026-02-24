"""
Tests for risk guardrail system settings integration.

Verifies that the 4 risk guardrail keys are present in
DEFAULT_SYSTEM_SETTINGS, AppState.system_settings, and safe_keys for export.
"""

import pytest

from webui.utils.storage import DEFAULT_SYSTEM_SETTINGS, export_settings
from webui.utils.state import AppState


RISK_KEYS = [
    "risk_guardrails_enabled",
    "risk_max_per_trade_pct",
    "risk_max_single_position_pct",
    "risk_max_total_exposure_pct",
]

EXPECTED_DEFAULTS = {
    "risk_guardrails_enabled": False,
    "risk_max_per_trade_pct": 3.0,
    "risk_max_single_position_pct": 8.0,
    "risk_max_total_exposure_pct": 15.0,
}


class TestRiskGuardrailSettingsInStorage:
    """Verify DEFAULT_SYSTEM_SETTINGS contains the 4 risk guardrail keys."""

    def test_keys_present_in_defaults(self):
        for key in RISK_KEYS:
            assert key in DEFAULT_SYSTEM_SETTINGS, f"Missing key in DEFAULT_SYSTEM_SETTINGS: {key}"

    def test_default_values(self):
        for key, expected in EXPECTED_DEFAULTS.items():
            assert DEFAULT_SYSTEM_SETTINGS[key] == expected, (
                f"DEFAULT_SYSTEM_SETTINGS[{key!r}] = {DEFAULT_SYSTEM_SETTINGS[key]!r}, expected {expected!r}"
            )


class TestRiskGuardrailSettingsInAppState:
    """Verify AppState.system_settings contains the 4 risk guardrail keys."""

    def test_keys_present_in_app_state(self):
        state = AppState()
        for key in RISK_KEYS:
            assert key in state.system_settings, f"Missing key in AppState.system_settings: {key}"

    def test_values_match_defaults(self):
        state = AppState()
        for key, expected in EXPECTED_DEFAULTS.items():
            assert state.system_settings[key] == expected, (
                f"AppState.system_settings[{key!r}] = {state.system_settings[key]!r}, expected {expected!r}"
            )


class TestRiskGuardrailSettingsInExport:
    """Verify 4 risk guardrail keys are included in safe_keys for export."""

    def test_keys_exported(self):
        # Build settings with all risk keys set to non-default values
        settings = DEFAULT_SYSTEM_SETTINGS.copy()
        settings["risk_guardrails_enabled"] = True
        settings["risk_max_per_trade_pct"] = 5.0
        settings["risk_max_single_position_pct"] = 12.0
        settings["risk_max_total_exposure_pct"] = 25.0

        exported_json = export_settings(settings)

        import json
        exported = json.loads(exported_json)

        for key in RISK_KEYS:
            assert key in exported, f"Key {key!r} not in exported settings"

        assert exported["risk_guardrails_enabled"] is True
        assert exported["risk_max_per_trade_pct"] == 5.0
        assert exported["risk_max_single_position_pct"] == 12.0
        assert exported["risk_max_total_exposure_pct"] == 25.0
