"""
Chart-related callbacks for TradingAgents WebUI
Enhanced with symbol dropdown selector and technical indicators.

Uses TradingView lightweight-charts for professional charting.
"""

from dash import Input, Output, State, ctx, html, dash
import pandas as pd
from datetime import datetime

from webui.utils.state import app_state
from webui.utils.charts import get_yahoo_data, add_indicators
from webui.utils.chart_data import prepare_chart_data


def register_chart_callbacks(app):
    """Register all chart-related callbacks including symbol dropdown"""

    # Track whether we've already attempted to auto-load portfolio symbols
    _auto_load_state = {"attempted": False}

    @app.callback(
        [Output("chart-symbol-select", "options", allow_duplicate=True),
         Output("chart-symbol-select", "value", allow_duplicate=True),
         Output("chart-store", "data", allow_duplicate=True)],
        Input("clock-interval", "n_intervals"),
        State("chart-store", "data"),
        prevent_initial_call=True
    )
    def auto_load_portfolio_chart(n_intervals, chart_store_data):
        """Auto-load portfolio symbols into chart dropdown on initial app load."""
        if _auto_load_state["attempted"]:
            raise dash.exceptions.PreventUpdate

        _auto_load_state["attempted"] = True

        # Don't override if a symbol is already selected
        if chart_store_data and chart_store_data.get("last_symbol"):
            raise dash.exceptions.PreventUpdate

        try:
            from webui.utils.local_storage import get_watchlist
            watchlist = get_watchlist()
            symbols = watchlist.get("symbols", [])
            if symbols:
                app_state.portfolio_symbols = symbols
                options = [{"label": s, "value": str(i + 1)} for i, s in enumerate(symbols)]
                first_symbol = symbols[0]
                store_data = {"last_symbol": first_symbol, "selected_period": "1d"}
                return options, "1", store_data
        except Exception as e:
            print(f"[CHART] Auto-load watchlist symbols failed: {e}")

        raise dash.exceptions.PreventUpdate

    @app.callback(
        [Output("chart-symbol-select", "options"),
         Output("chart-symbol-select", "value")],
        [Input("app-store", "data"),
         Input("refresh-interval", "n_intervals")],
        [State("chart-symbol-select", "value")],
        prevent_initial_call=True
    )
    def update_chart_symbol_select(store_data, n_intervals, current_value):
        """Update the symbol dropdown options for charts.
        Uses analysis symbols when available, falls back to portfolio positions."""
        # Prefer analysis symbols, fall back to portfolio positions
        if app_state.symbol_states:
            symbols = list(app_state.symbol_states.keys())
        elif app_state.portfolio_symbols:
            symbols = app_state.portfolio_symbols
        else:
            return dash.no_update, dash.no_update

        options = [{"label": s, "value": str(i + 1)} for i, s in enumerate(symbols)]

        current_symbol = app_state.current_symbol
        new_value = "1"
        if current_symbol and current_symbol in symbols:
            new_value = str(symbols.index(current_symbol) + 1)

        # Only update value if changed to avoid re-triggering downstream
        if new_value == current_value:
            return options, dash.no_update

        return options, new_value

    def _get_chart_symbols():
        """Get the current symbol list: analysis symbols first, then portfolio."""
        if app_state.symbol_states:
            return list(app_state.symbol_states.keys())
        return app_state.portfolio_symbols or []

    @app.callback(
        [Output("chart-pagination", "active_page", allow_duplicate=True),
         Output("report-pagination", "active_page", allow_duplicate=True),
         Output("chart-store", "data", allow_duplicate=True)],
        [Input("chart-symbol-select", "value")],
        [State("chart-store", "data")],
        prevent_initial_call=True
    )
    def handle_chart_symbol_select(value, chart_store_data):
        """Handle symbol dropdown selection for charts"""
        if not value:
            return dash.no_update, dash.no_update, dash.no_update

        page = int(value)
        symbols = _get_chart_symbols()
        if 0 < page <= len(symbols):
            new_symbol = symbols[page - 1]
            if new_symbol == app_state.current_symbol:
                return dash.no_update, dash.no_update, dash.no_update
            app_state.current_symbol = new_symbol
            # Update chart-store so chart loads even without symbol_states
            updated_store = chart_store_data or {}
            updated_store["last_symbol"] = new_symbol
            return page, page, updated_store
        return page, page, dash.no_update

    @app.callback(
        [Output("tv-chart-data-store", "data"),
         Output("current-symbol-display", "children"),
         Output("chart-store", "data", allow_duplicate=True)],
        [Input("period-1h", "n_clicks"),
         Input("period-4h", "n_clicks"),
         Input("period-1d", "n_clicks"),
         Input("chart-pagination", "active_page"),
         Input("manual-chart-refresh", "n_clicks"),
         Input("indicator-checklist", "value"),
         Input("chart-store", "data")],
        [State("run-watchlist-store", "data")],
        prevent_initial_call=True
    )
    def update_chart(n_1h, n_4h, n_1d,
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
        elif active_page and _get_chart_symbols():
            # Use pagination-based symbol selection (analysis or portfolio symbols)
            symbols_list = _get_chart_symbols()
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

        # Period mapping for timeframe buttons (1H, 4H, 1D only)
        period_map = {
            "period-1h.n_clicks": "1h",
            "period-4h.n_clicks": "4h",
            "period-1d.n_clicks": "1d",
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
        [Output("period-1h", "active"),
         Output("period-4h", "active"),
         Output("period-1d", "active")],
        [Input("period-1h", "n_clicks"),
         Input("period-4h", "n_clicks"),
         Input("period-1d", "n_clicks")]
    )
    def update_active_period_button(n_1h, n_4h, n_1d):
        """Update which period button is active (1H, 4H, 1D)"""
        button_id = ctx.triggered_id if ctx.triggered_id else "period-1d"

        return (
            button_id == "period-1h",
            button_id == "period-4h",
            button_id == "period-1d",
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
            return False, "chart-live-btn chart-live-active", "success"
        else:
            # Disable live mode
            return True, "chart-live-btn", "outline-success"

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
