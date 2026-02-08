"""
Scanner callbacks for TradingAgents WebUI
"""

import threading
import json
from datetime import datetime
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
                "options": "Analyzing options flow...",
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
        Output("scanner-timestamp-display", "children"),
        Input("medium-refresh-interval", "n_intervals"),
        Input("scanner-results-store", "data"),
    )
    def update_scanner_timestamp(n_intervals, stored_data):
        """Display the timestamp of the last scan."""
        # First check in-memory state
        timestamp = app_state.get_scanner_timestamp()

        # If not in memory, check stored data
        if not timestamp and stored_data and stored_data.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(stored_data["timestamp"])
            except (ValueError, TypeError):
                timestamp = None

        if timestamp:
            # Format: "Last scan: Feb 8, 2026 at 3:45 PM"
            formatted = timestamp.strftime("%b %d, %Y at %I:%M %p")
            return [
                html.I(className="bi bi-clock me-1"),
                f"Last scan: {formatted}"
            ]

        return ""

    @app.callback(
        Output("scanner-results-store", "data"),
        Input("medium-refresh-interval", "n_intervals"),
        State("scanner-results-store", "data"),
        prevent_initial_call=True
    )
    def persist_scanner_results(n_intervals, current_data):
        """Persist scanner results to localStorage when scan completes."""
        results = app_state.get_scanner_results()
        timestamp = app_state.get_scanner_timestamp()

        if results and timestamp:
            # Serialize results to JSON-compatible format
            serialized_results = []
            for r in results:
                serialized_results.append({
                    "symbol": r.symbol,
                    "company_name": r.company_name,
                    "price": r.price,
                    "change_percent": r.change_percent,
                    "volume": r.volume,
                    "volume_ratio": r.volume_ratio,
                    "rsi": r.rsi,
                    "macd_signal": r.macd_signal,
                    "price_vs_50ma": r.price_vs_50ma,
                    "price_vs_200ma": r.price_vs_200ma,
                    "technical_score": r.technical_score,
                    "news_sentiment": r.news_sentiment,
                    "news_count": r.news_count,
                    "news_score": r.news_score,
                    "options_score": r.options_score,
                    "options_signal": r.options_signal,
                    "combined_score": r.combined_score,
                    "rationale": r.rationale,
                    "chart_data": r.chart_data,
                    "sector": r.sector,
                    "market_cap": r.market_cap,
                })

            new_data = {
                "results": serialized_results,
                "timestamp": timestamp.isoformat()
            }

            # Only update if data changed
            if current_data != new_data:
                return new_data

        raise PreventUpdate

    @app.callback(
        Output("scanner-results-container", "children"),
        Input("medium-refresh-interval", "n_intervals"),
        Input("scanner-btn", "n_clicks"),
        Input("scanner-results-store", "data"),
        prevent_initial_call=False
    )
    def update_scanner_results_and_start(n_intervals, n_clicks, stored_data):
        """Update the scanner results display and start scanner if button clicked."""
        ctx = callback_context

        # Check if the button was clicked - check ALL triggered inputs, not just first
        triggered_ids = [t["prop_id"] for t in ctx.triggered] if ctx.triggered else []
        button_clicked = any("scanner-btn" in tid for tid in triggered_ids) and n_clicks

        if button_clicked:
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

        # Check in-memory results first
        results = app_state.get_scanner_results()
        if results:
            return create_scanner_results_grid(results)

        # If no in-memory results, try loading from localStorage
        if stored_data and stored_data.get("results"):
            try:
                from tradingagents.scanner.scanner_result import ScannerResult

                # Reconstruct ScannerResult objects from stored data
                restored_results = []
                for data in stored_data["results"]:
                    result = ScannerResult(
                        symbol=data.get("symbol", ""),
                        company_name=data.get("company_name", ""),
                        price=data.get("price", 0),
                        change_percent=data.get("change_percent", 0),
                        volume=data.get("volume", 0),
                        volume_ratio=data.get("volume_ratio", 1),
                        rsi=data.get("rsi", 50),
                        macd_signal=data.get("macd_signal", "neutral"),
                        price_vs_50ma=data.get("price_vs_50ma", "neutral"),
                        price_vs_200ma=data.get("price_vs_200ma", "neutral"),
                        technical_score=data.get("technical_score", 50),
                        news_sentiment=data.get("news_sentiment", "neutral"),
                        news_count=data.get("news_count", 0),
                        news_score=data.get("news_score", 50),
                        options_score=data.get("options_score", 50),
                        options_signal=data.get("options_signal", "neutral"),
                        combined_score=data.get("combined_score", 50),
                        rationale=data.get("rationale", ""),
                        chart_data=data.get("chart_data", []),
                        sector=data.get("sector", ""),
                        market_cap=data.get("market_cap"),
                    )
                    restored_results.append(result)

                # Load into app_state for consistency
                timestamp = stored_data.get("timestamp")
                app_state.load_scanner_results(restored_results, timestamp)

                return create_scanner_results_grid(restored_results)

            except Exception as e:
                print(f"[SCANNER] Error restoring results from storage: {e}")

        return html.Div(
            "Click 'Scan Market' to find trading opportunities based on technical indicators and news sentiment.",
            className="text-center text-muted py-4"
        )

    @app.callback(
        Output("run-watchlist-store", "data", allow_duplicate=True),
        Input({"type": "scanner-analyze-btn", "symbol": ALL}, "n_clicks"),
        State("run-watchlist-store", "data"),
        prevent_initial_call=True
    )
    def add_scanner_result_to_run_queue(n_clicks_list, store_data):
        """Add a scanner result to the Run Queue when Analyze button is clicked."""
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

        # Add symbol to Run Queue
        if not store_data:
            store_data = {"symbols": []}

        symbols = store_data.get("symbols", [])
        if symbol.upper() not in symbols:
            symbols.append(symbol.upper())
            store_data["symbols"] = symbols
            print(f"[SCANNER] Added {symbol} to Run Queue")
            return store_data
        else:
            # Symbol already in Run Queue, don't duplicate
            raise PreventUpdate
