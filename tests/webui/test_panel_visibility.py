"""
Unit tests for dashboard panel visibility (hide/show) settings.

Tests:
- Panel visibility settings in DEFAULT_SYSTEM_SETTINGS
- Panel visibility settings in AppState
- Panel visibility settings export/import
- Panel builder functions exist and return content
- Dashboard panels UI section
"""

import json
import pytest
from unittest.mock import MagicMock, patch


PANEL_KEYS = [
    "show_panel_account_bar",
    "show_panel_scanner",
    "show_panel_watchlist",
    "show_panel_chart",
    "show_panel_trading",
    "show_panel_positions",
    "show_panel_options",
    "show_panel_reports",
    "show_panel_logs",
]


class TestPanelVisibilityDefaults:
    """Tests for panel visibility default values."""

    def test_panel_settings_in_defaults(self):
        """Verify all panel visibility settings exist in DEFAULT_SYSTEM_SETTINGS."""
        from webui.utils.storage import DEFAULT_SYSTEM_SETTINGS
        for key in PANEL_KEYS:
            assert key in DEFAULT_SYSTEM_SETTINGS, f"Missing default: {key}"

    def test_all_panels_visible_by_default(self):
        """Verify all panels default to True (visible)."""
        from webui.utils.storage import DEFAULT_SYSTEM_SETTINGS
        for key in PANEL_KEYS:
            assert DEFAULT_SYSTEM_SETTINGS[key] is True, f"{key} should default to True"

    def test_panel_settings_in_app_state(self):
        """Verify panel settings exist in AppState.system_settings."""
        from webui.utils.state import AppState
        state = AppState()
        for key in PANEL_KEYS:
            assert key in state.system_settings, f"Missing in AppState: {key}"

    def test_app_state_matches_defaults(self):
        """Verify AppState values match DEFAULT_SYSTEM_SETTINGS."""
        from webui.utils.state import AppState
        from webui.utils.storage import DEFAULT_SYSTEM_SETTINGS
        state = AppState()
        for key in PANEL_KEYS:
            assert state.system_settings[key] == DEFAULT_SYSTEM_SETTINGS[key]


class TestPanelVisibilityExport:
    """Tests for panel visibility settings export/import."""

    def test_panel_settings_in_safe_keys(self):
        """Verify panel settings are included in export (safe keys)."""
        from webui.utils.storage import export_settings
        settings = {"show_panel_account_bar": False, "show_panel_chart": True}
        exported = json.loads(export_settings(settings))
        assert "show_panel_account_bar" in exported
        assert exported["show_panel_account_bar"] is False
        assert exported["show_panel_chart"] is True

    def test_all_panel_keys_exported(self):
        """Verify all 9 panel settings are exportable."""
        from webui.utils.storage import export_settings
        settings = {key: False for key in PANEL_KEYS}
        exported = json.loads(export_settings(settings))
        for key in PANEL_KEYS:
            assert key in exported, f"{key} not exported"

    def test_panel_settings_not_sensitive(self):
        """Panel settings should be exported while API keys are excluded."""
        from webui.utils.storage import export_settings
        settings = {
            "show_panel_logs": False,
            "alpaca_api_key": "secret_key_value",
        }
        exported = json.loads(export_settings(settings))
        assert "show_panel_logs" in exported
        assert "alpaca_api_key" not in exported


class TestPanelBuilderFunctions:
    """Tests for panel builder functions in layout module."""

    def test_build_account_bar_callable(self):
        """Verify _build_account_bar exists and is callable."""
        from webui.layout import _build_account_bar
        assert callable(_build_account_bar)

    def test_build_scanner_section_callable(self):
        """Verify _build_scanner_section exists and is callable."""
        from webui.layout import _build_scanner_section
        assert callable(_build_scanner_section)

    def test_build_watchlist_section_callable(self):
        """Verify _build_watchlist_section exists and is callable."""
        from webui.layout import _build_watchlist_section
        assert callable(_build_watchlist_section)

    def test_build_chart_section_callable(self):
        """Verify _build_chart_section exists and is callable."""
        from webui.layout import _build_chart_section
        assert callable(_build_chart_section)

    def test_build_trading_panel_callable(self):
        """Verify _build_trading_panel exists and is callable."""
        from webui.layout import _build_trading_panel
        assert callable(_build_trading_panel)

    def test_build_positions_section_callable(self):
        """Verify _build_positions_section exists and is callable."""
        from webui.layout import _build_positions_section
        assert callable(_build_positions_section)

    def test_build_options_section_callable(self):
        """Verify _build_options_section exists and is callable."""
        from webui.layout import _build_options_section
        assert callable(_build_options_section)

    def test_build_reports_section_callable(self):
        """Verify _build_reports_section exists and is callable."""
        from webui.layout import _build_reports_section
        assert callable(_build_reports_section)

    def test_build_log_panel_callable(self):
        """Verify _build_log_panel exists and is callable."""
        from webui.layout import _build_log_panel
        assert callable(_build_log_panel)

    def test_build_main_trading_row_both_visible(self):
        """Verify main trading row renders when both chart and trading visible."""
        from webui.layout import _build_main_trading_row
        result = _build_main_trading_row(show_chart=True, show_trading=True)
        assert result is not None
        assert result != []

    def test_build_main_trading_row_both_hidden(self):
        """Verify main trading row returns empty when both hidden."""
        from webui.layout import _build_main_trading_row
        result = _build_main_trading_row(show_chart=False, show_trading=False)
        assert result == []

    def test_build_main_trading_row_chart_only(self):
        """Verify main trading row renders with only chart."""
        from webui.layout import _build_main_trading_row
        result = _build_main_trading_row(show_chart=True, show_trading=False)
        assert result is not None
        assert result != []

    def test_build_main_trading_row_trading_only(self):
        """Verify main trading row renders with only trading panel."""
        from webui.layout import _build_main_trading_row
        result = _build_main_trading_row(show_chart=False, show_trading=True)
        assert result is not None
        assert result != []


class TestDashboardPanelsUI:
    """Tests for the Dashboard Panels settings UI component."""

    def test_dashboard_panels_section_exists(self):
        """Verify create_dashboard_panels_section function exists."""
        from webui.components.system_settings import create_dashboard_panels_section
        assert callable(create_dashboard_panels_section)

    def test_dashboard_panels_section_returns_content(self):
        """Verify the section returns a non-empty component."""
        from webui.components.system_settings import create_dashboard_panels_section
        section = create_dashboard_panels_section()
        assert section is not None

    def test_dashboard_panels_has_all_switches(self):
        """Verify all 9 toggle switches are present."""
        from webui.components.system_settings import create_dashboard_panels_section
        section = create_dashboard_panels_section()
        section_str = str(section)
        expected_ids = [
            "setting-show-panel-account-bar",
            "setting-show-panel-scanner",
            "setting-show-panel-watchlist",
            "setting-show-panel-chart",
            "setting-show-panel-trading",
            "setting-show-panel-positions",
            "setting-show-panel-options",
            "setting-show-panel-reports",
            "setting-show-panel-logs",
        ]
        for id_str in expected_ids:
            assert id_str in section_str, f"Missing switch: {id_str}"


class TestPanelWrapperIds:
    """Tests for panel wrapper div IDs in the layout."""

    def test_trading_content_has_wrapper_divs(self):
        """Verify create_trading_content has all panel wrapper divs."""
        from webui.layout import create_trading_content
        content = create_trading_content()
        content_str = str(content)
        expected_wrappers = [
            "panel-wrapper-account-bar",
            "panel-wrapper-scanner",
            "panel-wrapper-watchlist",
            "panel-wrapper-main-trading-row",
            "panel-wrapper-positions",
            "panel-wrapper-options",
            "panel-wrapper-reports",
            "panel-wrapper-logs",
        ]
        for wrapper_id in expected_wrappers:
            assert wrapper_id in content_str, f"Missing wrapper: {wrapper_id}"


class TestGlobalStoresRelocated:
    """Tests to verify stores were relocated to global scope."""

    def test_scanner_results_store_in_global(self):
        """Verify scanner-results-store is in create_stores()."""
        from webui.layout import create_stores
        stores = create_stores()
        store_ids = [s.id for s in stores if hasattr(s, 'id')]
        assert "scanner-results-store" in store_ids

    def test_watchlist_store_in_global(self):
        """Verify watchlist-store is in create_stores()."""
        from webui.layout import create_stores
        stores = create_stores()
        store_ids = [s.id for s in stores if hasattr(s, 'id')]
        assert "watchlist-store" in store_ids

    def test_watchlist_reorder_store_in_global(self):
        """Verify watchlist-reorder-store is in create_stores()."""
        from webui.layout import create_stores
        stores = create_stores()
        store_ids = [s.id for s in stores if hasattr(s, 'id')]
        assert "watchlist-reorder-store" in store_ids

    def test_run_watchlist_store_in_global(self):
        """Verify run-watchlist-store is in create_stores()."""
        from webui.layout import create_stores
        stores = create_stores()
        store_ids = [s.id for s in stores if hasattr(s, 'id')]
        assert "run-watchlist-store" in store_ids

    def test_log_last_index_in_global(self):
        """Verify log-last-index is in create_stores()."""
        from webui.layout import create_stores
        stores = create_stores()
        store_ids = [s.id for s in stores if hasattr(s, 'id')]
        assert "log-last-index" in store_ids
