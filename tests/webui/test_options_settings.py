"""
Unit tests for options trading settings in WebUI.

Tests:
- Options settings in DEFAULT_SYSTEM_SETTINGS
- Options settings in AppState
- Options settings export/import
"""

import pytest
from unittest.mock import MagicMock, patch


class TestOptionsSettingsDefaults:
    """Tests for options settings default values"""

    def test_options_settings_in_defaults(self):
        """Verify options settings exist in DEFAULT_SYSTEM_SETTINGS"""
        from webui.utils.storage import DEFAULT_SYSTEM_SETTINGS

        expected_keys = [
            "enable_options_trading",
            "options_trading_level",
            "options_max_contracts",
            "options_max_position_value",
            "options_min_dte",
            "options_max_dte",
            "options_min_delta",
            "options_max_delta",
            "options_min_open_interest",
        ]

        for key in expected_keys:
            assert key in DEFAULT_SYSTEM_SETTINGS, \
                f"Missing default setting: {key}"

    def test_options_trading_disabled_by_default(self):
        """Verify options trading is disabled by default"""
        from webui.utils.storage import DEFAULT_SYSTEM_SETTINGS

        assert DEFAULT_SYSTEM_SETTINGS.get("enable_options_trading") is False

    def test_options_trading_level_default(self):
        """Verify options trading level has valid default"""
        from webui.utils.storage import DEFAULT_SYSTEM_SETTINGS

        level = DEFAULT_SYSTEM_SETTINGS.get("options_trading_level")
        assert level in [1, 2, 3], "options_trading_level should be 1, 2, or 3"

    def test_options_max_contracts_reasonable(self):
        """Verify max contracts has reasonable default"""
        from webui.utils.storage import DEFAULT_SYSTEM_SETTINGS

        max_contracts = DEFAULT_SYSTEM_SETTINGS.get("options_max_contracts")
        assert max_contracts is not None
        assert max_contracts > 0
        assert max_contracts <= 100  # Reasonable upper limit

    def test_options_dte_range_valid(self):
        """Verify DTE range defaults are valid"""
        from webui.utils.storage import DEFAULT_SYSTEM_SETTINGS

        min_dte = DEFAULT_SYSTEM_SETTINGS.get("options_min_dte")
        max_dte = DEFAULT_SYSTEM_SETTINGS.get("options_max_dte")

        assert min_dte is not None
        assert max_dte is not None
        assert min_dte > 0
        assert max_dte > min_dte

    def test_options_delta_range_valid(self):
        """Verify delta range defaults are valid"""
        from webui.utils.storage import DEFAULT_SYSTEM_SETTINGS

        min_delta = DEFAULT_SYSTEM_SETTINGS.get("options_min_delta")
        max_delta = DEFAULT_SYSTEM_SETTINGS.get("options_max_delta")

        assert min_delta is not None
        assert max_delta is not None
        assert 0 < min_delta < 1
        assert 0 < max_delta < 1
        assert min_delta < max_delta


class TestOptionsSettingsExport:
    """Tests for options settings export"""

    def test_options_settings_in_safe_keys(self):
        """Verify options settings are included in export safe keys"""
        import json
        from webui.utils.storage import export_settings

        # Create a test settings dict with options settings
        settings = {
            "enable_options_trading": True,
            "options_trading_level": 2,
            "options_max_contracts": 10,
            "options_max_position_value": 5000,
            "options_min_dte": 7,
            "options_max_dte": 45,
            "options_min_delta": 0.20,
            "options_max_delta": 0.70,
            "options_min_open_interest": 100,
        }

        exported_json = export_settings(settings)
        exported = json.loads(exported_json)

        # Verify options settings are exported
        assert "enable_options_trading" in exported
        assert exported["enable_options_trading"] is True
        assert "options_trading_level" in exported
        assert exported["options_trading_level"] == 2

    def test_export_excludes_sensitive_data(self):
        """Verify export excludes sensitive API keys"""
        from webui.utils.storage import export_settings

        settings = {
            "enable_options_trading": True,
            "alpaca_api_key": "secret_key",  # Should NOT be exported
        }

        exported = export_settings(settings)

        # Options settings should be exported
        assert "enable_options_trading" in exported

        # Sensitive keys should NOT be exported
        assert "alpaca_api_key" not in exported


class TestOptionsSettingsAppState:
    """Tests for options settings in AppState"""

    def test_options_settings_in_app_state(self):
        """Verify options settings exist in AppState.system_settings"""
        from webui.utils.state import AppState

        app_state = AppState()

        expected_keys = [
            "enable_options_trading",
            "options_trading_level",
            "options_max_contracts",
            "options_max_position_value",
            "options_min_dte",
            "options_max_dte",
            "options_min_delta",
            "options_max_delta",
            "options_min_open_interest",
        ]

        for key in expected_keys:
            assert key in app_state.system_settings, \
                f"Missing setting in AppState: {key}"

    def test_app_state_options_match_defaults(self):
        """Verify AppState options match DEFAULT_SYSTEM_SETTINGS"""
        from webui.utils.state import AppState
        from webui.utils.storage import DEFAULT_SYSTEM_SETTINGS

        app_state = AppState()

        options_keys = [
            "enable_options_trading",
            "options_trading_level",
            "options_max_contracts",
        ]

        for key in options_keys:
            assert app_state.system_settings[key] == DEFAULT_SYSTEM_SETTINGS[key], \
                f"AppState.{key} doesn't match DEFAULT_SYSTEM_SETTINGS"


class TestOptionsConfig:
    """Tests for options settings in default_config.py"""

    def test_options_settings_in_default_config(self):
        """Verify options settings exist in DEFAULT_CONFIG"""
        from tradingagents.default_config import DEFAULT_CONFIG

        expected_keys = [
            "enable_options_trading",
            "options_trading_level",
            "options_max_contracts",
            "options_max_position_value",
            "options_min_dte",
            "options_max_dte",
            "options_min_delta",
            "options_max_delta",
            "options_min_open_interest",
        ]

        for key in expected_keys:
            assert key in DEFAULT_CONFIG, \
                f"Missing config setting: {key}"

    def test_config_options_disabled_by_default(self):
        """Verify options trading is disabled by default in config"""
        from tradingagents.default_config import DEFAULT_CONFIG

        assert DEFAULT_CONFIG.get("enable_options_trading") is False


class TestOptionsAgentStates:
    """Tests for options-related agent state fields"""

    def test_options_fields_in_agent_state(self):
        """Verify options fields exist in AgentState"""
        from tradingagents.agents.utils.agent_states import AgentState

        # AgentState is a TypedDict, check its annotations
        annotations = AgentState.__annotations__

        expected_fields = [
            "options_trade_plan",
            "options_recommendation",
            "options_action",
        ]

        for field in expected_fields:
            assert field in annotations, \
                f"Missing field in AgentState: {field}"


class TestOptionsSettingsUIComponents:
    """Tests for options settings UI components"""

    def test_options_trading_section_exists(self):
        """Verify options trading section function exists"""
        from webui.components.system_settings import create_options_trading_section

        section = create_options_trading_section()

        assert section is not None

    def test_options_trading_section_has_enable_toggle(self):
        """Verify options section has enable toggle"""
        from webui.components.system_settings import create_options_trading_section

        section = create_options_trading_section()

        # Convert to string and check for enable toggle ID
        section_str = str(section)
        assert "setting-enable-options-trading" in section_str

    def test_options_trading_section_has_level_selector(self):
        """Verify options section has trading level selector"""
        from webui.components.system_settings import create_options_trading_section

        section = create_options_trading_section()

        section_str = str(section)
        assert "setting-options-trading-level" in section_str
