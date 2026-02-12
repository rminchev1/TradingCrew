"""
Trading and Alpaca-related callbacks for TradingAgents WebUI
"""

from dash import Input, Output, State, html, ctx, ALL
import dash_bootstrap_components as dbc
import dash.dependencies
import dash
import json

from webui.components.alpaca_account import (
    render_positions_table,
    render_orders_table,
    render_compact_account_bar,
    render_options_positions_table,
    render_options_orders_table,
)


def register_trading_callbacks(app):
    """Register all trading and Alpaca-related callbacks"""

    @app.callback(
        [Output("positions-table-container", "children"),
         Output("orders-table-container", "children"),
         Output("account-bar-wrapper", "children"),
         Output("options-positions-table-container", "children"),
         Output("options-orders-table-container", "children")],
        [Input("slow-refresh-interval", "n_intervals"),
         Input("refresh-alpaca-btn", "n_clicks"),
         Input("orders-pagination", "active_page"),
         Input("options-orders-pagination", "active_page")]
    )
    def update_enhanced_alpaca_tables(n_intervals, alpaca_refresh, orders_page, options_orders_page):
        """Update the enhanced positions, orders tables, account bar, and options tables"""

        page = orders_page if orders_page is not None else 1
        options_page = options_orders_page if options_orders_page is not None else 1

        positions_table = render_positions_table()
        orders_table = render_orders_table(page=page)
        account_bar = render_compact_account_bar()
        options_positions_table = render_options_positions_table()
        options_orders_table = render_options_orders_table(page=options_page)

        return positions_table, orders_table, account_bar, options_positions_table, options_orders_table

    @app.callback(
        [Output('liquidate-confirm', 'displayed'),
         Output('liquidate-confirm', 'message')],
        [Input({'type': 'liquidate-btn', 'index': dash.dependencies.ALL}, 'n_clicks')],
        prevent_initial_call=True
    )
    def show_liquidate_confirmation(n_clicks_list):
        """Show confirmation dialog for liquidation"""
        if not any(n_clicks_list) or not any(n_clicks_list):
            return False, ""
        
        # Get the button that was clicked
        from dash import ctx
        if not ctx.triggered:
            return False, ""
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        # Safely parse the JSON string
        try:
            button_data = json.loads(button_id)
            symbol = button_data['index']
        except (json.JSONDecodeError, KeyError):
            return False, ""
        
        message = f"Are you sure you want to liquidate your entire position in {symbol}? This action cannot be undone."
        return True, message

    @app.callback(
        Output('liquidation-status', 'children'),
        [Input('liquidate-confirm', 'submit_n_clicks')],
        [State('liquidate-confirm', 'message')],
        prevent_initial_call=True
    )
    def handle_liquidation(submit_n_clicks, message):
        """Handle the actual liquidation when confirmed"""
        if not submit_n_clicks:
            return ""
        
        try:
            # Extract symbol from confirmation message
            symbol = message.split(" in ")[1].split("?")[0]
            
            # Import AlpacaUtils for liquidation
            from tradingagents.dataflows.alpaca_utils import AlpacaUtils
            
            # Execute liquidation
            result = AlpacaUtils.close_position(symbol)
            
            if result.get("success"):
                return dbc.Alert([
                    html.I(className="fas fa-check-circle me-2"),
                    f"Successfully liquidated position in {symbol}. Order ID: {result.get('order_id', 'N/A')}"
                ], color="success", duration=5000, className="mt-3")
            else:
                return dbc.Alert([
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    f"Failed to liquidate position in {symbol}: {result.get('error', 'Unknown error')}"
                ], color="danger", duration=8000, className="mt-3")
                
        except Exception as e:
            return dbc.Alert([
                html.I(className="fas fa-exclamation-triangle me-2"),
                f"Error during liquidation: {str(e)}"
            ], color="danger", duration=8000, className="mt-3")

    # =========================================================================
    # Options Position Close Handlers
    # =========================================================================
    @app.callback(
        [Output('close-option-confirm', 'displayed'),
         Output('close-option-confirm', 'message')],
        [Input({'type': 'close-option-btn', 'index': dash.dependencies.ALL}, 'n_clicks')],
        prevent_initial_call=True
    )
    def show_close_option_confirmation(n_clicks_list):
        """Show confirmation dialog for closing options position"""
        if not any(n_clicks_list):
            return False, ""

        if not ctx.triggered:
            return False, ""

        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        try:
            button_data = json.loads(button_id)
            symbol = button_data['index']
        except (json.JSONDecodeError, KeyError):
            return False, ""

        message = f"Are you sure you want to close your options position in {symbol}? This action cannot be undone."
        return True, message

    @app.callback(
        Output('close-option-status', 'children'),
        [Input('close-option-confirm', 'submit_n_clicks')],
        [State('close-option-confirm', 'message')],
        prevent_initial_call=True
    )
    def handle_close_option(submit_n_clicks, message):
        """Handle the actual options position close when confirmed"""
        if not submit_n_clicks:
            return ""

        try:
            # Extract symbol from confirmation message
            symbol = message.split(" in ")[1].split("?")[0]

            # Import AlpacaUtils for closing position
            from tradingagents.dataflows.alpaca_utils import AlpacaUtils

            # Execute close (options use the same close_position API)
            result = AlpacaUtils.close_position(symbol)

            if result.get("success"):
                return dbc.Alert([
                    html.I(className="fas fa-check-circle me-2"),
                    f"Successfully closed options position in {symbol}. Order ID: {result.get('order_id', 'N/A')}"
                ], color="success", duration=5000, className="mt-3")
            else:
                return dbc.Alert([
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    f"Failed to close options position: {result.get('error', 'Unknown error')}"
                ], color="danger", duration=8000, className="mt-3")

        except Exception as e:
            return dbc.Alert([
                html.I(className="fas fa-exclamation-triangle me-2"),
                f"Error closing options position: {str(e)}"
            ], color="danger", duration=8000, className="mt-3")

    # =========================================================================
    # Symbol Click Handlers - Update chart when clicking positions/orders
    # =========================================================================
    @app.callback(
        Output("chart-store", "data", allow_duplicate=True),
        [Input({"type": "position-symbol-link", "symbol": ALL}, "n_clicks")],
        [State("chart-store", "data")],
        prevent_initial_call=True
    )
    def handle_position_symbol_click(n_clicks_list, chart_store):
        """Update chart when clicking a position symbol."""
        if not any(n_clicks_list):
            return dash.no_update

        if not ctx.triggered:
            return dash.no_update

        # Get the clicked symbol
        triggered = ctx.triggered[0]
        prop_id = triggered["prop_id"]

        if "position-symbol-link" in prop_id:
            try:
                button_id = json.loads(prop_id.split(".")[0])
                symbol = button_id.get("symbol")

                if symbol:
                    chart_store = chart_store or {}
                    chart_store["last_symbol"] = symbol
                    return chart_store
            except (json.JSONDecodeError, KeyError):
                pass

        return dash.no_update

    @app.callback(
        Output("chart-store", "data", allow_duplicate=True),
        [Input({"type": "order-symbol-link", "symbol": ALL, "index": ALL}, "n_clicks")],
        [State("chart-store", "data")],
        prevent_initial_call=True
    )
    def handle_order_symbol_click(n_clicks_list, chart_store):
        """Update chart when clicking an order symbol."""
        if not any(n_clicks_list):
            return dash.no_update

        if not ctx.triggered:
            return dash.no_update

        # Get the clicked symbol
        triggered = ctx.triggered[0]
        prop_id = triggered["prop_id"]

        if "order-symbol-link" in prop_id:
            try:
                button_id = json.loads(prop_id.split(".")[0])
                symbol = button_id.get("symbol")

                if symbol:
                    chart_store = chart_store or {}
                    chart_store["last_symbol"] = symbol
                    return chart_store
            except (json.JSONDecodeError, KeyError):
                pass

        return dash.no_update
