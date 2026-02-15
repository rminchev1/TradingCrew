"""
webui/callbacks/panel_visibility_callbacks.py
Callback to show/hide dashboard panels based on system settings.
Panels are fully removed from the DOM when hidden.
"""

from dash import Input, Output, no_update
from dash.exceptions import PreventUpdate


def register_panel_visibility_callbacks(app):
    """Register callbacks for panel visibility toggling."""

    @app.callback(
        [
            Output("panel-wrapper-account-bar", "children"),
            Output("panel-wrapper-portfolio", "children"),
            Output("panel-wrapper-scanner", "children"),
            Output("panel-wrapper-watchlist", "children"),
            Output("panel-wrapper-main-trading-row", "children"),
            Output("panel-wrapper-positions", "children"),
            Output("panel-wrapper-options", "children"),
            Output("panel-wrapper-reports", "children"),
            Output("panel-wrapper-logs", "children"),
        ],
        [
            Input("system-settings-store", "data"),
        ],
        # No prevent_initial_call - must fire on page load to render panels
    )
    def render_visible_panels(stored_settings):
        """Render or hide panels based on visibility settings.

        Fires on initial page load and whenever settings are saved.
        Hidden panels return empty list (removed from DOM).
        """
        from webui.utils.storage import DEFAULT_SYSTEM_SETTINGS
        from webui.layout import (
            _build_account_bar, _build_portfolio_section,
            _build_scanner_section,
            _build_watchlist_section, _build_main_trading_row,
            _build_positions_section, _build_options_section,
            _build_reports_section, _build_log_panel,
        )

        if stored_settings is None:
            stored_settings = {}

        settings = DEFAULT_SYSTEM_SETTINGS.copy()
        settings.update(stored_settings)

        show_chart = settings.get("show_panel_chart", True)
        show_trading = settings.get("show_panel_trading", True)

        return (
            _build_account_bar() if settings.get("show_panel_account_bar", True) else [],
            _build_portfolio_section() if settings.get("show_panel_portfolio", True) else [],
            _build_scanner_section() if settings.get("show_panel_scanner", True) else [],
            _build_watchlist_section() if settings.get("show_panel_watchlist", True) else [],
            _build_main_trading_row(show_chart, show_trading) if (show_chart or show_trading) else [],
            _build_positions_section() if settings.get("show_panel_positions", True) else [],
            _build_options_section() if settings.get("show_panel_options", True) else [],
            _build_reports_section() if settings.get("show_panel_reports", True) else [],
            _build_log_panel() if settings.get("show_panel_logs", True) else [],
        )
