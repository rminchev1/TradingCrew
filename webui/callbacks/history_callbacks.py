"""
History Callbacks for TradingAgents WebUI
Handles saving, loading, and displaying analysis history.
"""

from dash import Input, Output, State, html, no_update, ctx
import dash

from webui.utils.state import app_state
from webui.utils.history import (
    save_analysis_run,
    list_analysis_runs,
    load_analysis_run,
    format_run_label
)


def register_history_callbacks(app):
    """Register all history-related callbacks."""

    # =========================================================================
    # Refresh History Dropdown
    # =========================================================================
    @app.callback(
        Output("history-selector", "options"),
        [Input("refresh-history-btn", "n_clicks"),
         Input("save-history-btn", "n_clicks"),
         Input("reports-panel-collapse", "is_open"),
         Input("refresh-interval", "n_intervals")],
        prevent_initial_call=False
    )
    def refresh_history_dropdown(refresh_clicks, save_clicks, is_open, n_intervals):
        """Refresh the history dropdown options."""
        options = [{"label": "📍 Current Session", "value": "current"}]

        # Get saved runs
        runs = list_analysis_runs(limit=30)

        for run in runs:
            label = format_run_label(run)
            options.append({
                "label": f"📁 {label}",
                "value": run["run_id"]
            })

        return options

    # =========================================================================
    # Save Current Analysis to History
    # =========================================================================
    @app.callback(
        [Output("history-selector", "value", allow_duplicate=True),
         Output("save-history-btn", "children", allow_duplicate=True)],
        [Input("save-history-btn", "n_clicks")],
        [State("run-watchlist-store", "data")],
        prevent_initial_call=True
    )
    def save_current_analysis(n_clicks, run_watchlist_data):
        """Save the current analysis to history."""
        if not n_clicks:
            return no_update, no_update

        # Get symbols from Run Queue
        run_store = run_watchlist_data or {"symbols": []}
        symbols = run_store.get("symbols", [])

        if not symbols or not app_state.symbol_states:
            return no_update, [html.I(className="fas fa-exclamation me-1"), "No Data"]

        # Check if there's actual data to save
        has_data = False
        for symbol in symbols:
            state = app_state.symbol_states.get(symbol, {})
            reports = state.get("reports", {})
            if reports:
                has_data = True
                break

        if not has_data:
            return no_update, [html.I(className="fas fa-exclamation me-1"), "No Reports"]

        # Save the run
        run_id = save_analysis_run(app_state, symbols)

        if run_id:
            return run_id, [html.I(className="fas fa-check me-1"), "Saved!"]
        else:
            return no_update, [html.I(className="fas fa-times me-1"), "Error"]

    # =========================================================================
    # Load Historical Run
    # =========================================================================
    @app.callback(
        [Output("report-symbol-select", "options", allow_duplicate=True),
         Output("report-symbol-select", "value", allow_duplicate=True),
         Output("current-symbol-report-display", "children", allow_duplicate=True)],
        [Input("history-selector", "value")],
        prevent_initial_call=True
    )
    def load_historical_run(run_id):
        """Load a historical run into the reports view."""
        if not run_id or run_id == "current":
            # Switch back to current session
            app_state.viewing_history = False
            app_state.historical_run = None
            symbols = list(app_state.symbol_states.keys())
            if symbols:
                options = [{"label": s, "value": str(i + 1)} for i, s in enumerate(symbols)]
                return options, "1", f"📈 {symbols[0]}"
            return [], None, ""

        # Load historical run
        run_data = load_analysis_run(run_id)

        if not run_data:
            return [], None, ""

        # Store the historical data in a special key in app_state
        app_state.historical_run = run_data
        app_state.viewing_history = True

        symbols = run_data.get("symbols", [])
        if symbols:
            options = [{"label": f"📁 {s}", "value": str(i + 1)} for i, s in enumerate(symbols)]
            return options, "1", f"📁 {symbols[0]} (History)"

        return [], None, ""

    # =========================================================================
    # Update Report Content Based on History Selection
    # =========================================================================
    @app.callback(
        [Output("market-analysis-tab-content", "children", allow_duplicate=True),
         Output("social-sentiment-tab-content", "children", allow_duplicate=True),
         Output("news-analysis-tab-content", "children", allow_duplicate=True),
         Output("fundamentals-analysis-tab-content", "children", allow_duplicate=True),
         Output("macro-analysis-tab-content", "children", allow_duplicate=True),
         Output("options-analysis-tab-content", "children", allow_duplicate=True),
         Output("research-manager-tab-content", "children", allow_duplicate=True),
         Output("trader-plan-tab-content", "children", allow_duplicate=True),
         Output("final-decision-tab-content", "children", allow_duplicate=True)],
        [Input("history-selector", "value"),
         Input("report-pagination", "active_page")],
        prevent_initial_call=True
    )
    def update_analyst_reports_from_history(run_id, active_page):
        """Update analyst report content when viewing history."""
        from dash import dcc

        if not run_id or run_id == "current":
            # Let the normal callbacks handle it
            return (no_update,) * 9

        # Load historical data
        run_data = load_analysis_run(run_id)
        if not run_data:
            return (no_update,) * 9

        symbols = run_data.get("symbols", [])
        if not symbols:
            return (no_update,) * 9

        # Get current symbol based on pagination
        page_idx = (active_page or 1) - 1
        if page_idx >= len(symbols):
            page_idx = 0

        symbol = symbols[page_idx]
        symbol_data = run_data.get("symbol_states", {}).get(symbol, {})
        reports = symbol_data.get("reports", {})

        # Map report types to content
        def get_report_content(report_key, title, icon):
            content = reports.get(report_key, "")
            if content:
                return dcc.Markdown(content, className='enhanced-markdown-content')
            return html.Div([
                html.I(className=f"fas {icon} fa-2x text-muted mb-2"),
                html.P(f"No {title} in this historical run", className="text-muted")
            ], className="text-center py-4")

        return (
            get_report_content("market_report", "Market Analysis", "fa-chart-line"),
            get_report_content("sentiment_report", "Social Sentiment", "fa-users"),
            get_report_content("news_report", "News Analysis", "fa-newspaper"),
            get_report_content("fundamentals_report", "Fundamentals", "fa-chart-bar"),
            get_report_content("macro_report", "Macro Analysis", "fa-globe"),
            get_report_content("options_report", "Options Analysis", "fa-chart-area"),
            get_report_content("research_manager_report", "Research Manager", "fa-user-tie"),
            get_report_content("trader_investment_plan", "Trader Plan", "fa-briefcase"),
            get_report_content("final_trade_decision", "Final Decision", "fa-gavel"),
        )

    # =========================================================================
    # Update Researcher Debate Tab from History
    # =========================================================================
    @app.callback(
        Output("researcher-debate-tab-content", "children", allow_duplicate=True),
        [Input("history-selector", "value"),
         Input("report-pagination", "active_page")],
        prevent_initial_call=True
    )
    def update_researcher_debate_from_history(run_id, active_page):
        """Update researcher debate content when viewing history."""
        from dash import dcc

        if not run_id or run_id == "current":
            # Let the normal callbacks handle it
            return no_update

        # Load historical data
        run_data = load_analysis_run(run_id)
        if not run_data:
            return no_update

        symbols = run_data.get("symbols", [])
        if not symbols:
            return no_update

        # Get current symbol based on pagination
        page_idx = (active_page or 1) - 1
        if page_idx >= len(symbols):
            page_idx = 0

        symbol = symbols[page_idx]
        symbol_data = run_data.get("symbol_states", {}).get(symbol, {})
        reports = symbol_data.get("reports", {})

        bull_report = reports.get("bull_report", "")
        bear_report = reports.get("bear_report", "")

        if not bull_report and not bear_report:
            return html.Div([
                html.I(className="fas fa-comments fa-2x text-muted mb-2"),
                html.P("No researcher debate in this historical run", className="text-muted")
            ], className="text-center py-4")

        debate_components = []

        # Bull section
        if bull_report:
            debate_components.append(
                html.Div([
                    html.Div([
                        html.Span("🐂 Bull Researcher", style={"fontWeight": "bold", "color": "#10B981"})
                    ], className="mb-2"),
                    dcc.Markdown(
                        bull_report,
                        className='enhanced-markdown-content',
                        style={
                            "background": "linear-gradient(135deg, #064E3B 0%, #047857 100%)",
                            "border-radius": "8px",
                            "padding": "1rem",
                            "border-left": "4px solid #10B981",
                            "color": "#E2E8F0",
                            "margin-bottom": "1rem"
                        }
                    )
                ])
            )

        # Bear section
        if bear_report:
            debate_components.append(
                html.Div([
                    html.Div([
                        html.Span("🐻 Bear Researcher", style={"fontWeight": "bold", "color": "#EF4444"})
                    ], className="mb-2"),
                    dcc.Markdown(
                        bear_report,
                        className='enhanced-markdown-content',
                        style={
                            "background": "linear-gradient(135deg, #7F1D1D 0%, #B91C1C 100%)",
                            "border-radius": "8px",
                            "padding": "1rem",
                            "border-left": "4px solid #EF4444",
                            "color": "#E2E8F0",
                            "margin-bottom": "1rem"
                        }
                    )
                ])
            )

        return html.Div(
            debate_components,
            style={
                "background": "linear-gradient(135deg, #0F172A 0%, #1E293B 100%)",
                "border-radius": "8px",
                "padding": "1.5rem",
                "min-height": "400px"
            }
        )

    # =========================================================================
    # Update Risk Debate Tab from History
    # =========================================================================
    @app.callback(
        Output("risk-debate-tab-content", "children", allow_duplicate=True),
        [Input("history-selector", "value"),
         Input("report-pagination", "active_page")],
        prevent_initial_call=True
    )
    def update_risk_debate_from_history(run_id, active_page):
        """Update risk debate content when viewing history."""
        from dash import dcc

        if not run_id or run_id == "current":
            # Let the normal callbacks handle it
            return no_update

        # Load historical data
        run_data = load_analysis_run(run_id)
        if not run_data:
            return no_update

        symbols = run_data.get("symbols", [])
        if not symbols:
            return no_update

        # Get current symbol based on pagination
        page_idx = (active_page or 1) - 1
        if page_idx >= len(symbols):
            page_idx = 0

        symbol = symbols[page_idx]
        symbol_data = run_data.get("symbol_states", {}).get(symbol, {})
        reports = symbol_data.get("reports", {})

        risky_report = reports.get("risky_report", "")
        safe_report = reports.get("safe_report", "")
        neutral_report = reports.get("neutral_report", "")

        if not risky_report and not safe_report and not neutral_report:
            return html.Div([
                html.I(className="fas fa-balance-scale fa-2x text-muted mb-2"),
                html.P("No risk debate in this historical run", className="text-muted")
            ], className="text-center py-4")

        debate_components = []

        # Risky section
        if risky_report:
            debate_components.append(
                html.Div([
                    html.Div([
                        html.Span("⚡ Risky Analyst", style={"fontWeight": "bold", "color": "#EF4444"})
                    ], className="mb-2"),
                    dcc.Markdown(
                        risky_report,
                        className='enhanced-markdown-content',
                        style={
                            "background": "linear-gradient(135deg, #7F1D1D 0%, #B91C1C 100%)",
                            "border-radius": "8px",
                            "padding": "1rem",
                            "border-left": "4px solid #EF4444",
                            "color": "#E2E8F0",
                            "margin-bottom": "1rem"
                        }
                    )
                ])
            )

        # Safe section
        if safe_report:
            debate_components.append(
                html.Div([
                    html.Div([
                        html.Span("🛡️ Safe Analyst", style={"fontWeight": "bold", "color": "#10B981"})
                    ], className="mb-2"),
                    dcc.Markdown(
                        safe_report,
                        className='enhanced-markdown-content',
                        style={
                            "background": "linear-gradient(135deg, #064E3B 0%, #047857 100%)",
                            "border-radius": "8px",
                            "padding": "1rem",
                            "border-left": "4px solid #10B981",
                            "color": "#E2E8F0",
                            "margin-bottom": "1rem"
                        }
                    )
                ])
            )

        # Neutral section
        if neutral_report:
            debate_components.append(
                html.Div([
                    html.Div([
                        html.Span("⚖️ Neutral Analyst", style={"fontWeight": "bold", "color": "#3B82F6"})
                    ], className="mb-2"),
                    dcc.Markdown(
                        neutral_report,
                        className='enhanced-markdown-content',
                        style={
                            "background": "linear-gradient(135deg, #1E3A8A 0%, #1D4ED8 100%)",
                            "border-radius": "8px",
                            "padding": "1rem",
                            "border-left": "4px solid #3B82F6",
                            "color": "#E2E8F0",
                            "margin-bottom": "1rem"
                        }
                    )
                ])
            )

        return html.Div(
            debate_components,
            style={
                "background": "linear-gradient(135deg, #0F172A 0%, #1E293B 100%)",
                "border-radius": "8px",
                "padding": "1.5rem",
                "min-height": "400px"
            }
        )

    # Reset save button text after delay
    @app.callback(
        Output("save-history-btn", "children", allow_duplicate=True),
        [Input("save-history-btn", "children")],
        prevent_initial_call=True
    )
    def reset_save_button(current_children):
        """Reset save button text after a delay."""
        import time

        # Only reset if it shows success/error
        if current_children and isinstance(current_children, list):
            text = "".join([c if isinstance(c, str) else "" for c in current_children])
            if "Saved" in text or "Error" in text or "No" in text:
                import threading

                def reset():
                    time.sleep(2)

                threading.Thread(target=reset, daemon=True).start()
                return no_update

        return [html.I(className="fas fa-save me-1"), "Save"]

