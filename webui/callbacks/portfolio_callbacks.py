"""
webui/callbacks/portfolio_callbacks.py
Callback to refresh the Portfolio Overview panel on the slow refresh interval.
"""

from dash import Input, Output, State, callback_context
from webui.utils.state import app_state


def register_portfolio_callbacks(app):
    """Register callbacks for the Portfolio Overview panel."""

    @app.callback(
        [
            Output("portfolio-metrics-row", "children"),
            Output("portfolio-risk-bars", "children"),
            Output("portfolio-sector-chart", "children"),
            Output("portfolio-config-summary", "children"),
        ],
        [
            Input("slow-refresh-interval", "n_intervals"),
            Input("system-settings-store", "data"),
            Input("settings-store", "data"),  # Control panel settings (for allow_shorts)
        ],
        prevent_initial_call=False,
    )
    def update_portfolio_panel(n_intervals, settings_store_data, control_settings_data):
        """Refresh all 4 sections of the portfolio overview panel."""
        from webui.components.portfolio_panel import (
            _is_alpaca_configured,
            _render_not_configured_message,
            render_portfolio_metrics,
            render_risk_utilization,
            render_sector_exposure,
            render_config_summary,
        )
        from dash import html

        # Use settings from store when available (ensures fresh values after save),
        # otherwise fall back to app_state.system_settings
        settings = settings_store_data if settings_store_data else app_state.system_settings

        # Merge allow_shorts from control panel settings (it's stored there, not in system settings)
        if control_settings_data and "allow_shorts" in control_settings_data:
            settings = dict(settings)  # Make a copy to avoid mutating the original
            settings["allow_shorts"] = control_settings_data["allow_shorts"]

        # Config summary is always available (doesn't need Alpaca)
        config_section = render_config_summary(settings)

        if not _is_alpaca_configured():
            not_configured = _render_not_configured_message()
            return not_configured, not_configured, not_configured, config_section

        # If triggered by a settings change, bypass cached context so new
        # risk limits are reflected immediately.
        # Check ALL triggered inputs, not just the first one (triggered_id only
        # returns the first), since multiple inputs can fire simultaneously.
        triggered_ids = [t["prop_id"].split(".")[0] for t in callback_context.triggered]
        settings_changed = (
            "system-settings-store" in triggered_ids or
            "settings-store" in triggered_ids  # Control panel settings changed
        )
        use_cache = not settings_changed

        ctx = None
        if use_cache:
            ctx = getattr(app_state, "_current_portfolio_context", None)
        if ctx is None:
            try:
                from tradingagents.dataflows.portfolio_risk import build_portfolio_context
                ctx = build_portfolio_context(settings)
            except Exception as e:
                print(f"[PORTFOLIO] Failed to build context: {e}")

        if ctx is None:
            error_msg = html.Div(
                html.Small("Unable to load portfolio data", className="text-muted"),
                className="text-center p-3",
            )
            return error_msg, error_msg, error_msg, config_section

        return (
            render_portfolio_metrics(ctx),
            render_risk_utilization(ctx),
            render_sector_exposure(ctx),
            config_section,
        )
