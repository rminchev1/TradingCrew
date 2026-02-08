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
    # Agent Quick Summary - Brief insights below signal card
    # =========================================================================
    @app.callback(
        Output("agent-quick-summary", "children"),
        [Input("slow-refresh-interval", "n_intervals"),
         Input("chart-pagination", "active_page")],
        [State("run-watchlist-store", "data")]
    )
    def update_agent_quick_summary(n_intervals, active_page, run_watchlist_data):
        """Update the quick agent summary with brief insights."""
        # Get symbols from Run Queue
        run_store = run_watchlist_data or {"symbols": []}
        symbols = run_store.get("symbols", [])

        if not symbols:
            return html.Div(
                "Agent insights will appear here after analysis",
                className="text-muted small text-center py-2"
            )

        # Get current symbol based on pagination
        page_index = (active_page or 1) - 1
        if page_index >= len(symbols):
            page_index = 0
        current_symbol = symbols[page_index]

        # Get reports for this symbol
        symbol_state = app_state.symbol_states.get(current_symbol, {})
        reports = symbol_state.get("reports", {})

        if not reports:
            # Check if symbol is currently being analyzed
            is_analyzing = current_symbol in app_state.analyzing_symbols
            if is_analyzing:
                return html.Div([
                    dbc.Spinner(size="sm", color="primary", spinner_class_name="me-2"),
                    html.Span("Analyzing...", className="text-muted small")
                ], className="text-center py-2")
            return html.Div(
                "Run analysis to see agent insights",
                className="text-muted small text-center py-2"
            )

        # Build quick summary from available reports
        summary_items = []

        # Market analyst
        if "market" in reports:
            market_report = reports["market"].get("report", "")
            if market_report:
                # Extract first key insight (look for trend or sentiment)
                insight = _extract_key_insight(market_report, "Market")
                if insight:
                    summary_items.append(
                        html.Div([
                            html.I(className="fas fa-chart-line me-1 text-info"),
                            html.Span(insight, className="small")
                        ], className="mb-1")
                    )

        # News analyst
        if "news" in reports:
            news_report = reports["news"].get("report", "")
            if news_report:
                insight = _extract_key_insight(news_report, "News")
                if insight:
                    summary_items.append(
                        html.Div([
                            html.I(className="fas fa-newspaper me-1 text-warning"),
                            html.Span(insight, className="small")
                        ], className="mb-1")
                    )

        # Social sentiment
        if "social" in reports:
            social_report = reports["social"].get("report", "")
            if social_report:
                insight = _extract_key_insight(social_report, "Social")
                if insight:
                    summary_items.append(
                        html.Div([
                            html.I(className="fas fa-users me-1 text-primary"),
                            html.Span(insight, className="small")
                        ], className="mb-1")
                    )

        # Final decision confidence
        final_decision = symbol_state.get("final_decision", {})
        if final_decision:
            decision = final_decision.get("decision", "")
            confidence = final_decision.get("confidence", 0)
            if decision:
                decision_color = "success" if decision.upper() in ["BUY", "LONG"] else (
                    "danger" if decision.upper() in ["SELL", "SHORT"] else "warning"
                )
                summary_items.append(
                    html.Div([
                        html.I(className=f"fas fa-bullseye me-1 text-{decision_color}"),
                        html.Span(f"Confidence: {confidence}%", className="small fw-bold")
                    ], className="mb-1")
                )

        if not summary_items:
            return html.Div(
                "Processing agent reports...",
                className="text-muted small text-center py-2"
            )

        return html.Div(summary_items, className="agent-summary-content p-2",
                       style={"backgroundColor": "rgba(59, 130, 246, 0.1)",
                              "borderRadius": "6px", "border": "1px solid rgba(59, 130, 246, 0.2)"})

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


def _extract_key_insight(report_text, report_type):
    """Extract a brief key insight from a report (max 60 chars)."""
    if not report_text:
        return None

    # Clean and truncate
    text = report_text.strip()

    # Look for key phrases
    key_phrases = ["bullish", "bearish", "neutral", "uptrend", "downtrend",
                   "positive", "negative", "strong", "weak", "momentum",
                   "support", "resistance", "breakout", "breakdown"]

    # Find sentences containing key phrases
    sentences = text.replace('\n', ' ').split('.')
    for sentence in sentences[:5]:  # Check first 5 sentences
        sentence = sentence.strip()
        for phrase in key_phrases:
            if phrase.lower() in sentence.lower():
                # Found a relevant sentence, truncate it
                if len(sentence) > 55:
                    return sentence[:52] + "..."
                return sentence

    # Fallback: just return first part of report
    first_line = sentences[0].strip() if sentences else text[:55]
    if len(first_line) > 55:
        return first_line[:52] + "..."
    return first_line if first_line else None
