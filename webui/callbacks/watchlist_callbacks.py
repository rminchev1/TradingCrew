"""
Watchlist callbacks for TradingAgents WebUI
"""

from dash import Input, Output, State, callback_context, html, ALL, MATCH, clientside_callback
import dash_bootstrap_components as dbc
import dash
from webui.components.watchlist_panel import create_watchlist_item
from webui.components.run_watchlist import create_run_watchlist_item
from webui.utils import local_storage


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

    # =========================================================================
    # INITIALIZATION CALLBACKS - Load from database on page load
    # =========================================================================

    # Initialize watchlist from database on page load
    @app.callback(
        Output("watchlist-store", "data", allow_duplicate=True),
        Input("watchlist-refresh-interval", "n_intervals"),
        State("watchlist-store", "data"),
        prevent_initial_call="initial_duplicate"
    )
    def init_watchlist_from_db(n_intervals, current_data):
        """Load watchlist from database on first load only"""
        # Only load on first call (n_intervals=0) to avoid overwriting user changes
        if n_intervals and n_intervals > 0:
            return dash.no_update
        db_data = local_storage.get_watchlist()
        print(f"[WATCHLIST] Initialized from database: {db_data}")
        return db_data

    # Initialize run queue from database on page load
    @app.callback(
        Output("run-watchlist-store", "data", allow_duplicate=True),
        Input("watchlist-refresh-interval", "n_intervals"),
        State("run-watchlist-store", "data"),
        prevent_initial_call="initial_duplicate"
    )
    def init_run_queue_from_db(n_intervals, current_data):
        """Load run queue from database on first load only"""
        # Only load on first call (n_intervals=0) to avoid overwriting user changes
        if n_intervals and n_intervals > 0:
            return dash.no_update
        db_data = local_storage.get_run_queue()
        print(f"[RUN_QUEUE] Initialized from database: {db_data}")
        return db_data

    # Clientside callback to poll for pending reorder from JavaScript fallback
    app.clientside_callback(
        """
        function(n_intervals, currentData) {
            if (window._watchlistReorderPending) {
                const pending = window._watchlistReorderPending;
                // Check if this is a new reorder (timestamp changed)
                if (!currentData || pending.timestamp > (currentData.timestamp || 0)) {
                    window._watchlistReorderPending = null;  // Clear after processing
                    return {order: pending.order, timestamp: pending.timestamp};
                }
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("watchlist-reorder-store", "data"),
        Input("watchlist-refresh-interval", "n_intervals"),
        State("watchlist-reorder-store", "data"),
        prevent_initial_call=True
    )

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
        ctx = callback_context

        # Check if actually triggered by user action
        if not ctx.triggered:
            return dash.no_update, dash.no_update

        triggered_value = ctx.triggered[0].get("value")

        # Must have a click or submit
        if not triggered_value:
            return dash.no_update, dash.no_update

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

        # Add to list
        symbols.append(symbol)
        store_data["symbols"] = symbols

        # Save to database
        local_storage.save_watchlist(store_data)
        print(f"[WATCHLIST] Added {symbol} to watchlist")

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
                    local_storage.save_watchlist(store_data)
                    # Verify save worked
                    saved = local_storage.get_watchlist()
                    print(f"[WATCHLIST] Removed {symbol} from watchlist. Saved: {saved}")
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
        Input("watchlist-reorder-store", "data"),
        State("watchlist-store", "data"),
        prevent_initial_call=True
    )
    def handle_watchlist_reorder(reorder_data, store_data):
        """Handle watchlist reorder from drag and drop"""
        if not reorder_data or not store_data:
            return dash.no_update

        try:
            new_order = reorder_data.get("order", [])
            timestamp = reorder_data.get("timestamp", 0)

            if not new_order or timestamp == 0:
                return dash.no_update

            # Validate that all symbols exist in the current list
            current_symbols = set(store_data.get("symbols", []))
            new_symbols = set(new_order)

            if current_symbols != new_symbols:
                print(f"[WATCHLIST] Reorder mismatch: current={current_symbols}, new={new_symbols}")
                return dash.no_update

            # Update the store with new order
            store_data["symbols"] = new_order
            local_storage.save_watchlist(store_data)
            print(f"[WATCHLIST] Reordered to: {new_order}")
            return store_data

        except Exception as e:
            print(f"[WATCHLIST] Error handling reorder: {e}")
            return dash.no_update

    # Add to Run Queue when analyze button clicked
    @app.callback(
        Output("run-watchlist-store", "data", allow_duplicate=True),
        Input({"type": "watchlist-analyze-btn", "symbol": ALL}, "n_clicks"),
        State("run-watchlist-store", "data"),
        prevent_initial_call=True
    )
    def analyze_from_watchlist(n_clicks_list, store_data):
        """Add symbol to Run Queue for analysis"""
        ctx = callback_context

        if not ctx.triggered:
            return dash.no_update

        # Get the triggered prop_id and parse it
        triggered_prop = ctx.triggered[0]["prop_id"]
        if not triggered_prop or triggered_prop == ".":
            return dash.no_update

        # Check if a button was actually clicked (n_clicks >= 1)
        triggered_value = ctx.triggered[0].get("value")
        if not triggered_value or triggered_value < 1:
            return dash.no_update

        # Parse the button ID from the prop_id
        import json
        try:
            id_json = triggered_prop.rsplit(".", 1)[0]
            button_id = json.loads(id_json)
        except (json.JSONDecodeError, ValueError, IndexError):
            return dash.no_update

        if not isinstance(button_id, dict) or button_id.get("type") != "watchlist-analyze-btn":
            return dash.no_update

        symbol = button_id.get("symbol")
        if symbol:
            if not store_data:
                store_data = {"symbols": []}

            symbols = store_data.get("symbols", [])
            if symbol.upper() not in symbols:
                symbols.append(symbol.upper())
                store_data["symbols"] = symbols
                local_storage.save_run_queue(store_data)
                print(f"[WATCHLIST] Added {symbol} to Run Queue for analysis")
                return store_data

        return dash.no_update

    # Update chart when chart button clicked
    @app.callback(
        Output("chart-store", "data", allow_duplicate=True),
        Input({"type": "watchlist-chart-btn", "symbol": ALL}, "n_clicks"),
        State("chart-store", "data"),
        prevent_initial_call=True
    )
    def view_chart_from_watchlist(n_clicks_list, chart_store):
        """View chart for a watchlist symbol"""
        ctx = callback_context

        if not ctx.triggered:
            return dash.no_update

        triggered_id = ctx.triggered_id
        if not triggered_id:
            return dash.no_update

        if isinstance(triggered_id, dict) and triggered_id.get("type") == "watchlist-chart-btn":
            # Check that button was actually clicked
            triggered_value = ctx.triggered[0].get("value")
            if not triggered_value or triggered_value < 1:
                return dash.no_update

            symbol = triggered_id.get("symbol")
            if symbol:
                # Update chart store to show this symbol
                if chart_store is None:
                    chart_store = {}
                chart_store["last_symbol"] = symbol

                return chart_store

        return dash.no_update

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
                    local_storage.save_watchlist(store_data)
                    print(f"[WATCHLIST] Added {symbol} from scanner")
                    return store_data

        return dash.no_update

    # =========================================================================
    # RUN QUEUE CALLBACKS
    # =========================================================================

    # Add symbol to Run Queue from watchlist
    @app.callback(
        Output("run-watchlist-store", "data", allow_duplicate=True),
        Input({"type": "watchlist-add-run-btn", "symbol": ALL}, "n_clicks"),
        State("run-watchlist-store", "data"),
        prevent_initial_call=True
    )
    def add_to_run_queue(n_clicks_list, store_data):
        """Add a symbol from watchlist to the Run Queue"""
        ctx = callback_context

        if not ctx.triggered:
            return dash.no_update

        # Get the triggered prop_id and parse it
        triggered_prop = ctx.triggered[0]["prop_id"]
        if not triggered_prop or triggered_prop == ".":
            return dash.no_update

        # Check if a button was actually clicked (n_clicks >= 1)
        triggered_value = ctx.triggered[0].get("value")
        if not triggered_value or triggered_value < 1:
            return dash.no_update

        # Parse the button ID from the prop_id
        import json
        try:
            id_json = triggered_prop.rsplit(".", 1)[0]
            button_id = json.loads(id_json)
        except (json.JSONDecodeError, ValueError, IndexError):
            return dash.no_update

        if not isinstance(button_id, dict) or button_id.get("type") != "watchlist-add-run-btn":
            return dash.no_update

        symbol = button_id.get("symbol")
        if symbol:
            if not store_data:
                store_data = {"symbols": []}

            symbols = store_data.get("symbols", [])
            if symbol not in symbols:
                symbols.append(symbol)
                store_data["symbols"] = symbols
                local_storage.save_run_queue(store_data)
                print(f"[RUN_QUEUE] Added {symbol} to Run Queue")
                return store_data

        return dash.no_update

    # Remove symbol from Run Queue
    @app.callback(
        Output("run-watchlist-store", "data", allow_duplicate=True),
        Input({"type": "run-watchlist-remove-btn", "symbol": ALL}, "n_clicks"),
        State("run-watchlist-store", "data"),
        prevent_initial_call=True
    )
    def remove_from_run_queue(n_clicks_list, store_data):
        """Remove a symbol from the Run Queue"""
        ctx = callback_context

        if not ctx.triggered:
            return dash.no_update

        # Get the triggered prop_id and parse it
        triggered_prop = ctx.triggered[0]["prop_id"]
        if not triggered_prop or triggered_prop == ".":
            return dash.no_update

        # Check if a button was actually clicked (n_clicks >= 1)
        triggered_value = ctx.triggered[0].get("value")
        if not triggered_value or triggered_value < 1:
            return dash.no_update

        # Parse the button ID from the prop_id
        import json
        try:
            id_json = triggered_prop.rsplit(".", 1)[0]
            button_id = json.loads(id_json)
        except (json.JSONDecodeError, ValueError, IndexError):
            return dash.no_update

        if not isinstance(button_id, dict) or button_id.get("type") != "run-watchlist-remove-btn":
            return dash.no_update

        symbol = button_id.get("symbol")
        if symbol and store_data:
            symbols = store_data.get("symbols", [])
            if symbol in symbols:
                symbols.remove(symbol)
                store_data["symbols"] = symbols
                local_storage.save_run_queue(store_data)
                print(f"[RUN_QUEUE] Removed {symbol} from Run Queue")
                return store_data

        return dash.no_update

    # Clear all symbols from Run Queue
    @app.callback(
        Output("run-watchlist-store", "data", allow_duplicate=True),
        Input("run-watchlist-clear-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def clear_run_queue(n_clicks):
        """Clear all symbols from the Run Queue"""
        if n_clicks:
            empty_data = {"symbols": []}
            local_storage.save_run_queue(empty_data)
            print("[RUN_QUEUE] Cleared Run Queue")
            return empty_data
        return dash.no_update

    # Update Run Queue display
    @app.callback(
        [Output("run-watchlist-items-container", "children"),
         Output("run-watchlist-count", "children"),
         Output("run-watchlist-count-badge", "children"),
         Output("config-run-queue-count", "children")],
        Input("run-watchlist-store", "data")
    )
    def update_run_queue_display(store_data):
        """Update the Run Queue items display"""
        if not store_data or not store_data.get("symbols"):
            empty_msg = html.Div(
                "Add symbols from Watchlist",
                className="text-muted text-center py-4 run-watchlist-empty-msg"
            )
            return [empty_msg], "0", "0", "0"

        symbols = store_data.get("symbols", [])
        items = []

        for index, symbol in enumerate(symbols):
            item = create_run_watchlist_item(symbol, index=index)
            items.append(item)

        count = str(len(symbols))
        return items, count, count, count

    # Note: Database sync is handled directly in each callback that modifies
    # the stores (add, remove, reorder, clear) since we use memory storage.
