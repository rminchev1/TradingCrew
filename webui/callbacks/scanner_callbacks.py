"""
Scanner callbacks for TradingAgents WebUI
"""

import threading
from dash import Input, Output, State, callback_context, ALL, MATCH, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from dash import html

from webui.utils.state import app_state
from webui.components.scanner_panel import create_scanner_results_grid


def register_scanner_callbacks(app):
    """Register all scanner-related callbacks."""

    @app.callback(
        Output("scanner-btn", "disabled"),
        Output("scanner-btn", "children"),
        Input("medium-refresh-interval", "n_intervals"),
        Input("scanner-btn", "n_clicks"),
    )
    def update_scanner_button_state(n_intervals, n_clicks):
        """Update the scanner button state based on whether scanner is running."""
        if app_state.is_scanner_running():
            return True, [
                dbc.Spinner(size="sm", spinner_class_name="me-2"),
                "Scanning..."
            ]
        return False, [html.I(className="bi bi-search me-2"), "Scan Market"]

    @app.callback(
        Output("scanner-progress-container", "style"),
        Output("scanner-progress-bar", "value"),
        Output("scanner-progress-text", "children"),
        Input("medium-refresh-interval", "n_intervals"),
    )
    def update_scanner_progress(n_intervals):
        """Update the scanner progress bar."""
        if app_state.is_scanner_running():
            progress = app_state.scanner_progress * 100
            stage_messages = {
                "fetching": "Fetching top movers...",
                "technical": "Calculating technical indicators...",
                "news": "Analyzing news sentiment...",
                "ranking": "Ranking candidates...",
                "rationale": "Generating rationales...",
                "complete": "Scan complete!"
            }
            stage_msg = stage_messages.get(app_state.scanner_stage, "Processing...")
            return {"display": "block"}, progress, stage_msg
        return {"display": "none"}, 0, ""

    @app.callback(
        Output("scanner-error-alert", "children"),
        Output("scanner-error-alert", "is_open"),
        Input("medium-refresh-interval", "n_intervals"),
    )
    def update_scanner_error(n_intervals):
        """Show scanner error if any."""
        if app_state.scanner_error:
            return app_state.scanner_error, True
        return "", False

    @app.callback(
        Output("scanner-results-container", "children"),
        Input("medium-refresh-interval", "n_intervals"),
        Input("scanner-btn", "n_clicks"),
        prevent_initial_call=False
    )
    def update_scanner_results_and_start(n_intervals, n_clicks):
        """Update the scanner results display and start scanner if button clicked."""
        ctx = callback_context

        # Check if the button was clicked (not just interval refresh)
        triggered_id = ctx.triggered[0]["prop_id"] if ctx.triggered else ""

        if "scanner-btn" in triggered_id and n_clicks:
            # Button was clicked - start the scanner if not already running
            if not app_state.is_scanner_running():
                # Start scanner in background thread
                def run_scanner():
                    try:
                        from tradingagents.scanner import MarketScanner
                        from tradingagents.default_config import DEFAULT_CONFIG

                        app_state.start_scanner()

                        # Use default config for scanner settings
                        scanner = MarketScanner(config=DEFAULT_CONFIG)

                        def progress_callback(stage, progress):
                            app_state.update_scanner_progress(stage, progress)

                        results = scanner.scan(progress_callback=progress_callback)
                        app_state.set_scanner_results(results)

                    except Exception as e:
                        print(f"[SCANNER] Error: {e}")
                        import traceback
                        traceback.print_exc()
                        app_state.set_scanner_error(str(e))

                thread = threading.Thread(target=run_scanner, daemon=True)
                thread.start()

                # Return loading state immediately
                return html.Div(
                    [
                        dbc.Spinner(color="primary", type="grow"),
                        html.P("Starting market scan...", className="mt-2 text-muted")
                    ],
                    className="text-center py-4"
                )

        # Regular update - show current state
        if app_state.is_scanner_running():
            return html.Div(
                [
                    dbc.Spinner(color="primary", type="grow"),
                    html.P("Scanning market for opportunities...", className="mt-2 text-muted")
                ],
                className="text-center py-4"
            )

        results = app_state.get_scanner_results()
        if results:
            return create_scanner_results_grid(results)

        return html.Div(
            "Click 'Scan Market' to find trading opportunities based on technical indicators and news sentiment.",
            className="text-center text-muted py-4"
        )

    @app.callback(
        Output("ticker-input", "value", allow_duplicate=True),
        Input({"type": "scanner-analyze-btn", "symbol": ALL}, "n_clicks"),
        State("ticker-input", "value"),
        prevent_initial_call=True
    )
    def add_scanner_result_to_analysis(n_clicks_list, current_value):
        """Add a scanner result to the analysis input when Analyze button is clicked."""
        ctx = callback_context

        if not ctx.triggered:
            raise PreventUpdate

        # Find which button was clicked
        triggered_id = ctx.triggered[0]["prop_id"]

        if not triggered_id or triggered_id == ".":
            raise PreventUpdate

        # Parse the button ID to get the symbol
        import json
        try:
            # Extract the JSON part from the prop_id (format: '{"type":"scanner-analyze-btn","symbol":"AAPL"}.n_clicks')
            id_json = triggered_id.split(".")[0]
            button_id = json.loads(id_json)
            symbol = button_id.get("symbol")
        except (json.JSONDecodeError, KeyError, IndexError):
            raise PreventUpdate

        if not symbol:
            raise PreventUpdate

        # Add symbol to ticker input
        # If there's already a value, append with comma
        if current_value and current_value.strip():
            # Check if symbol is already in the list
            existing_symbols = [s.strip().upper() for s in current_value.split(",")]
            if symbol.upper() not in existing_symbols:
                return f"{current_value}, {symbol}"
            else:
                # Symbol already in list, don't duplicate
                raise PreventUpdate
        else:
            return symbol
