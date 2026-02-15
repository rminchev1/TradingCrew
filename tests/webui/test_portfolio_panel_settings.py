"""
tests/webui/test_portfolio_panel_settings.py
Tests that show_panel_portfolio is properly wired into all settings files.
"""

import pytest


class TestPortfolioSettingsIntegration:
    """Tests for show_panel_portfolio in defaults, state, and safe_keys."""

    def test_show_panel_portfolio_in_defaults(self):
        """Verify key exists in DEFAULT_SYSTEM_SETTINGS with True default."""
        from webui.utils.storage import DEFAULT_SYSTEM_SETTINGS

        assert "show_panel_portfolio" in DEFAULT_SYSTEM_SETTINGS
        assert DEFAULT_SYSTEM_SETTINGS["show_panel_portfolio"] is True

    def test_show_panel_portfolio_in_app_state(self):
        """Verify key exists in AppState.system_settings."""
        from webui.utils.state import AppState

        state = AppState()
        assert "show_panel_portfolio" in state.system_settings
        assert state.system_settings["show_panel_portfolio"] is True

    def test_show_panel_portfolio_in_safe_keys(self):
        """Verify key is in safe_keys for export."""
        from webui.utils.storage import export_settings

        # Export a settings dict with the key — it should appear in the result
        settings = {"show_panel_portfolio": False}
        result = export_settings(settings)
        assert "show_panel_portfolio" in result

    def test_show_panel_portfolio_export_round_trip(self):
        """Verify export/import preserves the setting."""
        import json
        from webui.utils.storage import export_settings, import_settings

        original = {"show_panel_portfolio": False}
        json_str = export_settings(original)
        imported = import_settings(json_str)
        assert imported["show_panel_portfolio"] is False
