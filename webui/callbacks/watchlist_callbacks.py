"""
Watchlist callbacks for TradingAgents WebUI
"""

from dash import Input, Output, State, callback_context, html, ALL, MATCH
import dash_bootstrap_components as dbc
import dash
from webui.components.watchlist_panel import create_watchlist_item


def get_stock_quote(symbol):
    """Fetch current price and change for a symbol"""
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d")
        if len(hist) >= 1:
            current_price = hist['Close'].iloc[-1]
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                change = current_price - prev_close
                change_pct = (change / prev_close) * 100
            else:
                change = 0
                change_pct = 0
            return {
                "price": current_price,
                "change": change,
                "change_pct": change_pct
            }
    except Exception as e:
        print(f"[WATCHLIST] Error fetching quote for {symbol}: {e}")
    return None


def register_watchlist_callbacks(app):
    """Register all watchlist-related callbacks"""

    # Add symbol to watchlist
    @app.callback(
        [Output("watchlist-store", "data", allow_duplicate=True),
         Output("watchlist-add-input", "value")],
        [Input("watchlist-add-btn", "n_clicks"),
         Input("watchlist-add-input", "n_submit")],
        [State("watchlist-add-input", "value"),
         State("watchlist-store", "data")],
        prevent_initial_call=True
    )
    def add_to_watchlist(n_clicks, n_submit, symbol, store_data):
        """Add a symbol to the watchlist"""
        if not symbol or not symbol.strip():
            return dash.no_update, dash.no_update

        symbol = symbol.strip().upper()

        # Initialize store if needed
        if not store_data:
            store_data = {"symbols": []}

        symbols = store_data.get("symbols", [])

        # Check if already in watchlist
        if symbol in symbols:
            return dash.no_update, ""

        # Validate symbol by trying to fetch quote
        quote = get_stock_quote(symbol)
        if quote is None:
            # Still add it, might be a valid symbol that failed temporarily
            pass

        # Add to list
        symbols.append(symbol)
        store_data["symbols"] = symbols

        return store_data, ""

    # Remove symbol from watchlist
    @app.callback(
        Output("watchlist-store", "data", allow_duplicate=True),
        Input({"type": "watchlist-remove-btn", "symbol": ALL}, "n_clicks"),
        State("watchlist-store", "data"),
        prevent_initial_call=True
    )
    def remove_from_watchlist(n_clicks_list, store_data):
        """Remove a symbol from the watchlist"""
        ctx = callback_context

        # Check if callback was actually triggered by a click
        if not ctx.triggered:
            return dash.no_update

        # Use triggered_id for reliable pattern-matching detection
        triggered_id = ctx.triggered_id
        if not triggered_id:
            return dash.no_update

        # triggered_id is a dict for pattern-matching components
        if isinstance(triggered_id, dict) and triggered_id.get("type") == "watchlist-remove-btn":
            symbol = triggered_id.get("symbol")

            # Check that the button was actually clicked (n_clicks > 0)
            # Find the click count for this specific button
            triggered_value = ctx.triggered[0].get("value")
            if not triggered_value or triggered_value < 1:
                return dash.no_update

            if symbol and store_data:
                symbols = store_data.get("symbols", [])
                if symbol in symbols:
                    symbols.remove(symbol)
                    store_data["symbols"] = symbols
                    print(f"[WATCHLIST] Removed {symbol} from watchlist")
                    return store_data

        return dash.no_update

    # Update watchlist display
    @app.callback(
        [Output("watchlist-items-container", "children"),
         Output("watchlist-count-badge", "children")],
        [Input("watchlist-store", "data"),
         Input("watchlist-refresh-interval", "n_intervals")]
    )
    def update_watchlist_display(store_data, n_intervals):
        """Update the watchlist items display with current prices"""
        if not store_data or not store_data.get("symbols"):
            return [
                html.Div(
                    "Add symbols to your watchlist",
                    className="text-muted text-center py-4 watchlist-empty-msg"
                )
            ], "0"

        symbols = store_data.get("symbols", [])
        items = []

        for index, symbol in enumerate(symbols):
            quote = get_stock_quote(symbol)
            if quote:
                item = create_watchlist_item(
                    symbol,
                    price=quote.get("price"),
                    change=quote.get("change"),
                    change_pct=quote.get("change_pct"),
                    index=index
                )
            else:
                item = create_watchlist_item(symbol, index=index)
            items.append(item)

        return items, str(len(symbols))

    # Handle watchlist reorder from drag and drop
    @app.callback(
        Output("watchlist-store", "data", allow_duplicate=True),
        Input("watchlist-reorder-input", "value"),
        State("watchlist-store", "data"),
        prevent_initial_call=True
    )
    def handle_watchlist_reorder(reorder_value, store_data):
        """Handle watchlist reorder from drag and drop"""
        if not reorder_value or not store_data:
            return dash.no_update

        # Parse the reorder value (format: "SYM1,SYM2,SYM3|timestamp")
        try:
            parts = reorder_value.split("|")
            if len(parts) != 2:
                return dash.no_update

            new_order = parts[0].split(",")
            new_order = [s.strip() for s in new_order if s.strip()]

            if not new_order:
                return dash.no_update

            # Validate that all symbols exist in the current list
            current_symbols = set(store_data.get("symbols", []))
            new_symbols = set(new_order)

            if current_symbols != new_symbols:
                print(f"[WATCHLIST] Reorder mismatch: current={current_symbols}, new={new_symbols}")
                return dash.no_update

            # Update the store with new order
            store_data["symbols"] = new_order
            print(f"[WATCHLIST] Reordered to: {new_order}")
            return store_data

        except Exception as e:
            print(f"[WATCHLIST] Error handling reorder: {e}")
            return dash.no_update

    # Add to ticker input when analyze button clicked
    @app.callback(
        Output("ticker-input", "value", allow_duplicate=True),
        Input({"type": "watchlist-analyze-btn", "symbol": ALL}, "n_clicks"),
        State("ticker-input", "value"),
        prevent_initial_call=True
    )
    def analyze_from_watchlist(n_clicks_list, current_tickers):
        """Add symbol to ticker input for analysis"""
        ctx = callback_context

        if not ctx.triggered:
            return dash.no_update

        triggered_id = ctx.triggered_id
        if not triggered_id:
            return dash.no_update

        if isinstance(triggered_id, dict) and triggered_id.get("type") == "watchlist-analyze-btn":
            # Check that button was actually clicked
            triggered_value = ctx.triggered[0].get("value")
            if not triggered_value or triggered_value < 1:
                return dash.no_update

            symbol = triggered_id.get("symbol")
            if symbol:
                # Add to existing tickers or replace
                if current_tickers and current_tickers.strip():
                    existing = [s.strip().upper() for s in current_tickers.split(",")]
                    if symbol.upper() not in existing:
                        return f"{current_tickers}, {symbol}"
                    return current_tickers
                return symbol

        return dash.no_update

    # Update chart when chart button clicked
    @app.callback(
        [Output("ticker-input", "value", allow_duplicate=True),
         Output("chart-store", "data", allow_duplicate=True)],
        Input({"type": "watchlist-chart-btn", "symbol": ALL}, "n_clicks"),
        [State("ticker-input", "value"),
         State("chart-store", "data")],
        prevent_initial_call=True
    )
    def view_chart_from_watchlist(n_clicks_list, current_tickers, chart_store):
        """View chart for a watchlist symbol"""
        ctx = callback_context

        if not ctx.triggered:
            return dash.no_update, dash.no_update

        triggered_id = ctx.triggered_id
        if not triggered_id:
            return dash.no_update, dash.no_update

        if isinstance(triggered_id, dict) and triggered_id.get("type") == "watchlist-chart-btn":
            # Check that button was actually clicked
            triggered_value = ctx.triggered[0].get("value")
            if not triggered_value or triggered_value < 1:
                return dash.no_update, dash.no_update

            symbol = triggered_id.get("symbol")
            if symbol:
                # Update chart store to show this symbol
                if chart_store is None:
                    chart_store = {}
                chart_store["last_symbol"] = symbol

                return symbol, chart_store

        return dash.no_update, dash.no_update

    # Collapse toggle for watchlist panel
    @app.callback(
        [Output("watchlist-panel-collapse", "is_open"),
         Output("watchlist-panel-chevron", "className")],
        Input("watchlist-panel-header", "n_clicks"),
        State("watchlist-panel-collapse", "is_open"),
        prevent_initial_call=True
    )
    def toggle_watchlist_collapse(n_clicks, is_open):
        """Toggle watchlist panel collapse"""
        if n_clicks is None:
            return dash.no_update, dash.no_update

        new_state = not is_open
        chevron_class = "bi bi-chevron-down me-2" if new_state else "bi bi-chevron-right me-2"

        return new_state, chevron_class

    # Add from scanner results
    @app.callback(
        Output("watchlist-store", "data", allow_duplicate=True),
        Input({"type": "scanner-add-watchlist-btn", "symbol": ALL}, "n_clicks"),
        State("watchlist-store", "data"),
        prevent_initial_call=True
    )
    def add_scanner_to_watchlist(n_clicks_list, store_data):
        """Add a scanner result to the watchlist"""
        ctx = callback_context

        if not ctx.triggered:
            return dash.no_update

        triggered_id = ctx.triggered_id
        if not triggered_id:
            return dash.no_update

        if isinstance(triggered_id, dict) and triggered_id.get("type") == "scanner-add-watchlist-btn":
            # Check that button was actually clicked
            triggered_value = ctx.triggered[0].get("value")
            if not triggered_value or triggered_value < 1:
                return dash.no_update

            symbol = triggered_id.get("symbol")
            if symbol:
                if not store_data:
                    store_data = {"symbols": []}

                symbols = store_data.get("symbols", [])
                if symbol not in symbols:
                    symbols.append(symbol)
                    store_data["symbols"] = symbols
                    print(f"[WATCHLIST] Added {symbol} from scanner")
                    return store_data

        return dash.no_update
