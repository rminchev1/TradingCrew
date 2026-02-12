"""
UX Enhancement Callbacks for TradingAgents WebUI
- Agent quick summary below signal
- Active settings summary display
- Analysis completion toast notifications
"""

from dash import Input, Output, State, html, callback_context
import dash_bootstrap_components as dbc
import dash

from webui.utils.state import app_state


def register_ux_callbacks(app):
    """Register all UX enhancement callbacks."""

    # =========================================================================
    # Active Settings Summary - Shows current config inline
    # =========================================================================
    @app.callback(
        Output("active-settings-summary", "children"),
        [Input("research-depth", "value"),
         Input("analyst-checklist", "value"),
         Input("analyst-checklist-2", "value"),
         Input("allow-shorts", "value"),
         Input("trade-after-analyze", "value"),
         Input("loop-enabled", "value"),
         Input("market-hour-enabled", "value")]
    )
    def update_active_settings_summary(depth, analysts1, analysts2, allow_shorts,
                                        auto_trade, loop_enabled, market_hour_enabled):
        """Update the inline settings summary badges."""
        badges = []

        # Research depth badge
        depth_colors = {"Shallow": "info", "Medium": "warning", "Deep": "success"}
        depth_color = depth_colors.get(depth, "secondary")
        badges.append(dbc.Badge(depth or "Shallow", color=depth_color, className="me-1"))

        # Analysts count badge
        analysts1 = analysts1 or []
        analysts2 = analysts2 or []
        analyst_count = len(analysts1) + len(analysts2)
        badges.append(dbc.Badge(f"{analyst_count} Analysts", color="secondary", className="me-1"))

        # Trading mode badge
        if allow_shorts:
            badges.append(dbc.Badge("Shorts OK", color="danger", className="me-1"))
        else:
            badges.append(dbc.Badge("Long Only", color="success", className="me-1"))

        # Auto trade badge
        if auto_trade:
            badges.append(dbc.Badge("Auto Trade", color="warning", className="me-1"))

        # Scheduling mode badge
        if loop_enabled:
            badges.append(dbc.Badge("Loop", color="primary", className="me-1"))
        elif market_hour_enabled:
            badges.append(dbc.Badge("Scheduled", color="primary", className="me-1"))

        return html.Div(badges, className="d-flex flex-wrap gap-1")

    # =========================================================================
    # Analysis Completion Toast Notification
    # =========================================================================
    @app.callback(
        [Output("analysis-toast", "is_open"),
         Output("analysis-toast", "children"),
         Output("analysis-toast", "icon")],
        [Input("slow-refresh-interval", "n_intervals")],
        [State("run-watchlist-store", "data"),
         State("analysis-toast", "is_open")]
    )
    def show_analysis_completion_toast(n_intervals, run_watchlist_data, is_currently_open):
        """Show toast notification when analysis completes for a symbol."""
        # Get symbols from Run Queue
        run_store = run_watchlist_data or {"symbols": []}
        symbols = run_store.get("symbols", [])

        if not symbols:
            return False, "", "primary"

        # Check if any symbol just completed analysis
        for symbol in symbols:
            symbol_state = app_state.symbol_states.get(symbol, {})

            # Check if this symbol just completed (has final decision and wasn't notified)
            final_decision = symbol_state.get("final_decision", {})
            notified = symbol_state.get("toast_notified", False)

            if final_decision and not notified:
                decision = final_decision.get("decision", "HOLD")
                confidence = final_decision.get("confidence", 0)

                # Mark as notified
                if symbol in app_state.symbol_states:
                    app_state.symbol_states[symbol]["toast_notified"] = True

                # Determine icon based on decision
                if decision.upper() in ["BUY", "LONG"]:
                    icon = "success"
                    icon_class = "fas fa-arrow-up text-success"
                elif decision.upper() in ["SELL", "SHORT"]:
                    icon = "danger"
                    icon_class = "fas fa-arrow-down text-danger"
                else:
                    icon = "warning"
                    icon_class = "fas fa-pause text-warning"

                toast_content = html.Div([
                    html.Div([
                        html.I(className=f"{icon_class} me-2"),
                        html.Strong(f"{symbol}: {decision.upper()}")
                    ], className="d-flex align-items-center mb-1"),
                    html.Small(f"Confidence: {confidence}%", className="text-muted")
                ])

                return True, toast_content, icon

        # No new completions
        return is_currently_open if is_currently_open else False, dash.no_update, dash.no_update


