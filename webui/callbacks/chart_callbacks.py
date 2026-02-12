"""
Chart-related callbacks for TradingAgents WebUI
Enhanced with symbol-based pagination and technical indicators.

Uses TradingView lightweight-charts for professional charting.
"""

from dash import Input, Output, State, ctx, html, ALL, dash, ClientsideFunction
import dash_bootstrap_components as dbc
import pandas as pd
from datetime import datetime

from webui.utils.state import app_state
from webui.utils.charts import get_yahoo_data, add_indicators
from webui.utils.chart_data import prepare_chart_data


def create_symbol_button(symbol, index, is_active=False):
    """Create a symbol button for pagination"""
    return dbc.Button(
        symbol,
        id={"type": "symbol-btn", "index": index, "component": "charts"},
        color="primary" if is_active else "outline-primary",
        size="sm",
        className=f"symbol-btn {'active' if is_active else ''}",
    )


def register_chart_callbacks(app):
    """Register all chart-related callbacks including symbol pagination"""

    @app.callback(
        Output("chart-pagination-container", "children", allow_duplicate=True),
        [Input("app-store", "data"),
         Input("refresh-interval", "n_intervals")],
        prevent_initial_call=True
    )
    def update_chart_symbol_pagination(store_data, n_intervals):
        """Update the symbol pagination buttons for charts"""
        if not app_state.symbol_states:
            return html.Div("No symbols available",
                          className="text-muted text-center",
                          style={"padding": "10px"})

        symbols = list(app_state.symbol_states.keys())
        current_symbol = app_state.current_symbol

        # Find active symbol index
        active_index = 0
        if current_symbol and current_symbol in symbols:
            active_index = symbols.index(current_symbol)

        buttons = []
        for i, symbol in enumerate(symbols):
            is_active = i == active_index
            buttons.append(create_symbol_button(symbol, i, is_active))

        if len(symbols) > 1:
            # Add navigation info
            nav_info = html.Div([
                html.I(className="fas fa-chart-line me-2"),
                f"Charts for {len(symbols)} symbols"
            ], className="text-muted small text-center mt-2")

            return html.Div([
                dbc.ButtonGroup(buttons, className="d-flex flex-wrap justify-content-center"),
                nav_info
            ], className="symbol-pagination-wrapper")
        else:
            return dbc.ButtonGroup(buttons, className="d-flex justify-content-center")

    @app.callback(
        [Output("chart-pagination", "active_page", allow_duplicate=True),
         Output("report-pagination", "active_page", allow_duplicate=True),
         Output("chart-pagination-container", "children", allow_duplicate=True)],
        [Input({"type": "symbol-btn", "index": ALL, "component": "charts"}, "n_clicks")],
        prevent_initial_call=True
    )
    def handle_chart_symbol_click(symbol_clicks):
        """Handle symbol button clicks for charts with immediate visual feedback"""
        if not any(symbol_clicks) or not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update

        # Find which button was clicked
        button_id = ctx.triggered[0]["prop_id"]
        if "symbol-btn" in button_id:
            # Extract index from the button ID
            import json
            button_data = json.loads(button_id.split('.')[0])
            clicked_index = button_data["index"]

            # Update current symbol
            symbols = list(app_state.symbol_states.keys())
            if 0 <= clicked_index < len(symbols):
                app_state.current_symbol = symbols[clicked_index]
                page_number = clicked_index + 1

                # ⚡ IMMEDIATE BUTTON UPDATE - No waiting for refresh!
                buttons = []
                for i, symbol in enumerate(symbols):
                    is_active = i == clicked_index  # Active state based on click
                    buttons.append(create_symbol_button(symbol, i, is_active))

                if len(symbols) > 1:
                    # Add navigation info
                    nav_info = html.Div([
                        html.I(className="fas fa-chart-line me-2"),
                        f"Charts for {len(symbols)} symbols"
                    ], className="text-muted small text-center mt-2")

                    button_container = html.Div([
                        dbc.ButtonGroup(buttons, className="d-flex flex-wrap justify-content-center"),
                        nav_info
                    ], className="symbol-pagination-wrapper")
                else:
                    button_container = dbc.ButtonGroup(buttons, className="d-flex justify-content-center")

                return page_number, page_number, button_container

        return dash.no_update, dash.no_update, dash.no_update

    @app.callback(
        [Output("tv-chart-data-store", "data"),
         Output("current-symbol-display", "children"),
         Output("chart-store", "data", allow_duplicate=True)],
        [Input("period-5m", "n_clicks"),
         Input("period-15m", "n_clicks"),
         Input("period-30m", "n_clicks"),
         Input("period-1h", "n_clicks"),
         Input("period-4h", "n_clicks"),
         Input("period-1d", "n_clicks"),
         Input("period-1w", "n_clicks"),
         Input("period-1mo", "n_clicks"),
         Input("period-1y", "n_clicks"),
         Input("chart-pagination", "active_page"),
         Input("manual-chart-refresh", "n_clicks"),
         Input("indicator-checklist", "value"),
         Input("chart-store", "data")],
        [State("run-watchlist-store", "data")],
        prevent_initial_call=True
    )
    def update_chart(n_5m, n_15m, n_30m, n_1h, n_4h, n_1d, n_1w, n_1mo, n_1y,
                     active_page, manual_refresh, indicators, chart_store_data, run_watchlist_data):
        """Update the TradingView chart based on period selection, ticker change, or indicator toggle"""

        # Determine which input triggered the callback
        triggered_prop = ctx.triggered[0]["prop_id"] if ctx.triggered else None

        # Check if chart-store triggered with a new symbol (from watchlist/positions/orders)
        if triggered_prop == "chart-store.data" and chart_store_data:
            quick_symbol = chart_store_data.get("last_symbol")
            if quick_symbol:
                # Use the symbol from chart-store (clicked from watchlist/positions/orders)
                symbol = quick_symbol.upper()
            else:
                return dash.no_update, dash.no_update, dash.no_update
        elif app_state.symbol_states and active_page:
            # Use pagination-based symbol selection
            symbols_list = list(app_state.symbol_states.keys())
            if active_page > len(symbols_list):
                return None, "Page index out of range", chart_store_data
            symbol = symbols_list[active_page - 1]
        elif chart_store_data and chart_store_data.get("last_symbol"):
            # Fallback to last symbol in store
            symbol = chart_store_data["last_symbol"]
        elif run_watchlist_data and run_watchlist_data.get("symbols"):
            # Use first symbol from Run Queue
            symbol = run_watchlist_data["symbols"][0]
        else:
            return None, "", chart_store_data

        # Period mapping for all timeframe buttons
        period_map = {
            "period-5m.n_clicks": "5m",
            "period-15m.n_clicks": "15m",
            "period-30m.n_clicks": "30m",
            "period-1h.n_clicks": "1h",
            "period-4h.n_clicks": "4h",
            "period-1d.n_clicks": "1d",
            "period-1w.n_clicks": "1w",
            "period-1mo.n_clicks": "1mo",
            "period-1y.n_clicks": "1y"
        }

        # Determine selected period
        selected_period = None
        if triggered_prop in period_map:
            selected_period = period_map[triggered_prop]
        elif chart_store_data and "selected_period" in chart_store_data:
            selected_period = chart_store_data["selected_period"]
        else:
            selected_period = "1d"  # Default to 1D

        # Get indicators from state or use default
        if indicators is None:
            if chart_store_data and "indicators" in chart_store_data:
                indicators = chart_store_data["indicators"]
            else:
                indicators = ["sma", "bb"]

        # Fetch data and prepare for TradingView chart
        try:
            # Get OHLCV data from Yahoo Finance
            df = get_yahoo_data(symbol, selected_period)

            if df.empty:
                return None, f"No data for {symbol.upper()}", chart_store_data

            # Add technical indicators
            df = add_indicators(df)

            # Transform to TradingView format
            chart_data = prepare_chart_data(df, indicators, symbol, selected_period)

            symbol_display = f"{symbol.upper()}"

            # Update store data
            updated_store_data = chart_store_data or {}
            updated_store_data["selected_period"] = selected_period
            updated_store_data["last_symbol"] = symbol
            updated_store_data["last_updated"] = datetime.now().isoformat()
            updated_store_data["indicators"] = indicators

            return chart_data, symbol_display, updated_store_data

        except Exception as e:
            print(f"[CHART] Error loading {symbol}: {e}")
            return None, f"Error loading {symbol.upper()}", chart_store_data

    @app.callback(
        Output("chart-last-updated", "children"),
        [Input("chart-store", "data")]
    )
    def update_chart_timestamp(chart_store_data):
        """Update the chart last updated timestamp"""
        if not chart_store_data or "last_updated" not in chart_store_data:
            return ""

        try:
            last_updated = datetime.fromisoformat(chart_store_data["last_updated"])
            return f"Last updated: {last_updated.strftime('%I:%M:%S %p')}"
        except:
            return ""

    @app.callback(
        [Output("period-5m", "active"),
         Output("period-15m", "active"),
         Output("period-30m", "active"),
         Output("period-1h", "active"),
         Output("period-4h", "active"),
         Output("period-1d", "active"),
         Output("period-1w", "active"),
         Output("period-1mo", "active"),
         Output("period-1y", "active")],
        [Input("period-5m", "n_clicks"),
         Input("period-15m", "n_clicks"),
         Input("period-30m", "n_clicks"),
         Input("period-1h", "n_clicks"),
         Input("period-4h", "n_clicks"),
         Input("period-1d", "n_clicks"),
         Input("period-1w", "n_clicks"),
         Input("period-1mo", "n_clicks"),
         Input("period-1y", "n_clicks")]
    )
    def update_active_period_button(n_5m, n_15m, n_30m, n_1h, n_4h, n_1d, n_1w, n_1mo, n_1y):
        """Update which period button is active"""
        button_id = ctx.triggered_id if ctx.triggered_id else "period-1d"

        return (
            button_id == "period-5m",
            button_id == "period-15m",
            button_id == "period-30m",
            button_id == "period-1h",
            button_id == "period-4h",
            button_id == "period-1d",
            button_id == "period-1w",
            button_id == "period-1mo",
            button_id == "period-1y"
        )

    # Clientside callback to render TradingView chart
    app.clientside_callback(
        """
        function(chartData, chartConfig, themeStore) {
            if (!chartData || !chartData.candlestick || chartData.candlestick.length === 0) {
                return window.dash_clientside.no_update;
            }

            // Wait for TradingViewChartManager to be available
            if (typeof window.TradingViewChartManager === 'undefined') {
                console.warn('[TradingView] Chart manager not loaded yet');
                setTimeout(function() {
                    if (window.TradingViewChartManager) {
                        window.TradingViewChartManager.init('tv-chart-container');
                        window.TradingViewChartManager.update('tv-chart-container', chartData, chartConfig);
                    }
                }, 500);
                return window.dash_clientside.no_update;
            }

            // Initialize and update chart
            window.TradingViewChartManager.init('tv-chart-container');
            window.TradingViewChartManager.update('tv-chart-container', chartData, chartConfig);

            return window.dash_clientside.no_update;
        }
        """,
        Output("tv-chart-update-trigger", "children"),
        Input("tv-chart-data-store", "data"),
        Input("tv-chart-config-store", "data"),
        State("theme-store", "data"),
    )

    # =========================================================================
    # Live price update callbacks
    # =========================================================================

    @app.callback(
        [Output("chart-live-interval", "disabled"),
         Output("chart-live-btn", "className"),
         Output("chart-live-btn", "color")],
        Input("chart-live-btn", "n_clicks"),
        State("chart-live-interval", "disabled"),
        prevent_initial_call=True
    )
    def toggle_live_mode(n_clicks, currently_disabled):
        """Toggle live price updates on/off"""
        if not n_clicks:
            return dash.no_update, dash.no_update, dash.no_update

        if currently_disabled:
            # Enable live mode
            return False, "float-end ms-2 chart-live-btn chart-live-active", "success"
        else:
            # Disable live mode
            return True, "float-end ms-2 chart-live-btn", "outline-success"

    @app.callback(
        Output("tv-chart-live-store", "data"),
        Input("chart-live-interval", "n_intervals"),
        State("chart-store", "data"),
        prevent_initial_call=True
    )
    def fetch_live_price(n_intervals, chart_store_data):
        """Fetch latest price from Alpaca for live chart updates"""
        if not chart_store_data or not chart_store_data.get("last_symbol"):
            return dash.no_update

        symbol = chart_store_data["last_symbol"]

        try:
            from tradingagents.dataflows.alpaca_utils import AlpacaUtils
            quote = AlpacaUtils.get_latest_quote(symbol)

            if not quote:
                return dash.no_update

            # Use mid-price (average of bid/ask), fallback to ask or bid
            bid = quote.get("bid_price", 0) or 0
            ask = quote.get("ask_price", 0) or 0

            if bid > 0 and ask > 0:
                price = (bid + ask) / 2
            elif ask > 0:
                price = ask
            elif bid > 0:
                price = bid
            else:
                return dash.no_update

            return {
                "symbol": symbol,
                "price": price,
                "bid": bid,
                "ask": ask,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"[LIVE] Error fetching quote for {symbol}: {e}")
            return dash.no_update

    # Clientside callback to update last bar with live price
    app.clientside_callback(
        """
        function(liveData) {
            if (!liveData || !liveData.price) {
                return window.dash_clientside.no_update;
            }

            if (typeof window.TradingViewChartManager !== 'undefined') {
                window.TradingViewChartManager.updateLastBar(
                    'tv-chart-container',
                    liveData.price,
                    liveData.timestamp
                );
            }

            return window.dash_clientside.no_update;
        }
        """,
        Output("tv-chart-update-trigger", "children", allow_duplicate=True),
        Input("tv-chart-live-store", "data"),
        prevent_initial_call=True
    )
