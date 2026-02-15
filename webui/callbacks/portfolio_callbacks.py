"""
webui/callbacks/portfolio_callbacks.py
Callback to refresh the Portfolio Overview panel on the slow refresh interval.
"""

from dash import Input, Output, callback_context
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
        ],
        prevent_initial_call=False,
    )
    def update_portfolio_panel(n_intervals, settings_store_data):
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

        # Config summary is always available (doesn't need Alpaca)
        settings = app_state.system_settings
        config_section = render_config_summary(settings)

        if not _is_alpaca_configured():
            not_configured = _render_not_configured_message()
            return not_configured, not_configured, not_configured, config_section

        # If triggered by a settings change, bypass cached context so new
        # risk limits are reflected immediately.
        triggered = callback_context.triggered_id
        use_cache = triggered != "system-settings-store"

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
