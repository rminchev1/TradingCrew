"""
Trading and Alpaca-related callbacks for TradingAgents WebUI
"""

from dash import Input, Output, State, html, ctx, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash.dependencies
import dash
import json
import csv
import io
import re
from datetime import datetime

from webui.components.alpaca_account import (
    render_positions_table,
    render_orders_table,
    render_compact_account_bar,
    render_options_positions_table,
    render_options_orders_table,
    render_portfolio_summary,
)


def register_trading_callbacks(app):
    """Register all trading and Alpaca-related callbacks"""

    # =========================================================================
    # Main Refresh Callback
    # =========================================================================
    @app.callback(
        [Output("positions-table-container", "children"),
         Output("orders-table-container", "children"),
         Output("account-bar-wrapper", "children"),
         Output("options-positions-table-container", "children"),
         Output("options-orders-table-container", "children"),
         Output("portfolio-summary-container", "children"),
         Output("orders-pagination", "max_value"),
         Output("orders-page-info", "children")],
        [Input("slow-refresh-interval", "n_intervals"),
         Input("refresh-alpaca-btn", "n_clicks"),
         Input("options-orders-pagination", "active_page")],
        [State("positions-sort-store", "data"),
         State("positions-filter-store", "data"),
         State("orders-sort-store", "data"),
         State("orders-filter-store", "data"),
         State("orders-pagination", "active_page")]
    )
    def update_enhanced_alpaca_tables(n_intervals, alpaca_refresh,
                                      options_orders_page, sort_data, filter_data,
                                      orders_sort_data, orders_filter_data,
                                      orders_page):
        """Update positions, orders, account bar, options, and portfolio summary"""

        page = orders_page if orders_page is not None else 1
        options_page = options_orders_page if options_orders_page is not None else 1

        # Extract positions sort/filter params
        sort_key = (sort_data or {}).get("key", "symbol")
        sort_direction = (sort_data or {}).get("direction", "asc")
        search_filter = (filter_data or {}).get("search", "")

        # Extract orders sort/filter params
        orders_sort_key = (orders_sort_data or {}).get("key", "date")
        orders_sort_dir = (orders_sort_data or {}).get("direction", "desc")
        orders_search = (orders_filter_data or {}).get("search", "")

        # Fetch account info once to pass equity to positions table
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils
        try:
            account_info = AlpacaUtils.get_account_info()
            equity = account_info.get("equity", 0)
        except Exception:
            account_info = None
            equity = 0

        positions_table = render_positions_table(
            sort_key=sort_key, sort_direction=sort_direction,
            search_filter=search_filter, equity=equity
        )
        orders_table, orders_total_pages = render_orders_table(
            page=page, sort_key=orders_sort_key,
            sort_direction=orders_sort_dir, search_filter=orders_search
        )
        account_bar = render_compact_account_bar()
        options_positions_table = render_options_positions_table()
        options_orders_table = render_options_orders_table(page=options_page)
        portfolio_summary = render_portfolio_summary(account_info=account_info)

        return (positions_table, orders_table, account_bar,
                options_positions_table, options_orders_table, portfolio_summary,
                orders_total_pages, f"Page {page} of {orders_total_pages}")

    # =========================================================================
    # Orders Pagination Handler (separate from main refresh)
    # =========================================================================
    @app.callback(
        [Output("orders-table-container", "children", allow_duplicate=True),
         Output("orders-page-info", "children", allow_duplicate=True)],
        [Input("orders-pagination", "active_page")],
        [State("orders-sort-store", "data"),
         State("orders-filter-store", "data")],
        prevent_initial_call=True
    )
    def handle_orders_page_change(active_page, sort_data, filter_data):
        """Re-render orders table when pagination page changes."""
        if not active_page:
            raise PreventUpdate

        sort_key = (sort_data or {}).get("key", "date")
        sort_direction = (sort_data or {}).get("direction", "desc")
        search_filter = (filter_data or {}).get("search", "")

        orders_table, total_pages = render_orders_table(
            page=active_page, sort_key=sort_key,
            sort_direction=sort_direction, search_filter=search_filter
        )
        return orders_table, f"Page {active_page} of {total_pages}"

    # =========================================================================
    # Sort & Filter Handlers
    # =========================================================================
    @app.callback(
        [Output("positions-sort-store", "data"),
         Output("positions-table-container", "children", allow_duplicate=True),
         Output("portfolio-summary-container", "children", allow_duplicate=True)],
        [Input("positions-sort-select", "value")],
        [State("positions-filter-store", "data")],
        prevent_initial_call=True
    )
    def handle_positions_sort(sort_value, filter_data):
        """Update sort store and re-render positions table when sort changes."""
        if not sort_value:
            raise PreventUpdate

        parts = sort_value.split("-", 1)
        if len(parts) == 2:
            key, direction = parts
        else:
            key, direction = sort_value, "asc"

        sort_data = {"key": key, "direction": direction}
        search_filter = (filter_data or {}).get("search", "")

        from tradingagents.dataflows.alpaca_utils import AlpacaUtils
        try:
            account_info = AlpacaUtils.get_account_info()
            equity = account_info.get("equity", 0)
        except Exception:
            account_info = None
            equity = 0

        positions_table = render_positions_table(
            sort_key=key, sort_direction=direction,
            search_filter=search_filter, equity=equity
        )
        portfolio_summary = render_portfolio_summary(account_info=account_info)

        return sort_data, positions_table, portfolio_summary

    @app.callback(
        [Output("positions-filter-store", "data"),
         Output("positions-table-container", "children", allow_duplicate=True),
         Output("portfolio-summary-container", "children", allow_duplicate=True)],
        [Input("positions-search-input", "value")],
        [State("positions-sort-store", "data")],
        prevent_initial_call=True
    )
    def handle_positions_search(search_value, sort_data):
        """Update filter store and re-render positions table when search changes."""
        filter_data = {"search": search_value or ""}
        sort_key = (sort_data or {}).get("key", "symbol")
        sort_direction = (sort_data or {}).get("direction", "asc")

        from tradingagents.dataflows.alpaca_utils import AlpacaUtils
        try:
            account_info = AlpacaUtils.get_account_info()
            equity = account_info.get("equity", 0)
        except Exception:
            account_info = None
            equity = 0

        positions_table = render_positions_table(
            sort_key=sort_key, sort_direction=sort_direction,
            search_filter=search_value or "", equity=equity
        )
        portfolio_summary = render_portfolio_summary(account_info=account_info)

        return filter_data, positions_table, portfolio_summary

    # =========================================================================
    # Orders Sort & Filter Handlers
    # =========================================================================
    @app.callback(
        [Output("orders-sort-store", "data"),
         Output("orders-table-container", "children", allow_duplicate=True),
         Output("orders-pagination", "max_value", allow_duplicate=True),
         Output("orders-pagination", "active_page", allow_duplicate=True),
         Output("orders-page-info", "children", allow_duplicate=True)],
        [Input("orders-sort-select", "value")],
        [State("orders-filter-store", "data")],
        prevent_initial_call=True
    )
    def handle_orders_sort(sort_value, filter_data):
        """Update sort store and re-render orders table when sort changes (reset to page 1)."""
        if not sort_value:
            raise PreventUpdate

        parts = sort_value.split("-", 1)
        if len(parts) == 2:
            key, direction = parts
        else:
            key, direction = sort_value, "desc"

        sort_data = {"key": key, "direction": direction}
        search_filter = (filter_data or {}).get("search", "")

        orders_table, total_pages = render_orders_table(
            page=1, sort_key=key,
            sort_direction=direction, search_filter=search_filter
        )
        return sort_data, orders_table, total_pages, 1, f"Page 1 of {total_pages}"

    @app.callback(
        [Output("orders-filter-store", "data"),
         Output("orders-table-container", "children", allow_duplicate=True),
         Output("orders-pagination", "max_value", allow_duplicate=True),
         Output("orders-pagination", "active_page", allow_duplicate=True),
         Output("orders-page-info", "children", allow_duplicate=True)],
        [Input("orders-search-input", "value")],
        [State("orders-sort-store", "data")],
        prevent_initial_call=True
    )
    def handle_orders_search(search_value, sort_data):
        """Update filter store and re-render orders table when search changes (reset to page 1)."""
        filter_data = {"search": search_value or ""}
        sort_key = (sort_data or {}).get("key", "date")
        sort_direction = (sort_data or {}).get("direction", "desc")

        orders_table, total_pages = render_orders_table(
            page=1, sort_key=sort_key,
            sort_direction=sort_direction, search_filter=search_value or ""
        )
        return filter_data, orders_table, total_pages, 1, f"Page 1 of {total_pages}"

    # =========================================================================
    # Partial Close Handlers
    # =========================================================================
    @app.callback(
        [Output('partial-close-confirm', 'displayed'),
         Output('partial-close-confirm', 'message'),
         Output('positions-pending-close-store', 'data')],
        [Input({'type': 'partial-close-btn', 'symbol': ALL, 'pct': ALL}, 'n_clicks')],
        prevent_initial_call=True
    )
    def show_partial_close_confirmation(n_clicks_list):
        """Show confirmation dialog for partial/full position close."""
        if not n_clicks_list or not any(n_clicks_list):
            return False, "", {}

        if not ctx.triggered:
            return False, "", {}

        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        try:
            button_data = json.loads(button_id)
            symbol = button_data['symbol']
            pct = int(button_data['pct'])
        except (json.JSONDecodeError, KeyError, ValueError):
            return False, "", {}

        if pct >= 100:
            msg = f"Are you sure you want to liquidate your entire position in {symbol}? This action cannot be undone."
        else:
            msg = f"Are you sure you want to close {pct}% of your position in {symbol}?"

        return True, msg, {"symbol": symbol, "pct": pct}

    @app.callback(
        Output('partial-close-status', 'children'),
        [Input('partial-close-confirm', 'submit_n_clicks')],
        [State('positions-pending-close-store', 'data')],
        prevent_initial_call=True
    )
    def handle_partial_close(submit_n_clicks, pending_close):
        """Handle the actual partial/full close when confirmed."""
        if not submit_n_clicks:
            return ""

        if not pending_close:
            return ""

        symbol = pending_close.get("symbol")
        pct = pending_close.get("pct", 100)

        if not symbol:
            return ""

        try:
            from tradingagents.dataflows.alpaca_utils import AlpacaUtils
            result = AlpacaUtils.close_position(symbol, percentage=float(pct))

            if result.get("success"):
                pct_label = f"{pct}% of " if pct < 100 else ""
                return dbc.Alert([
                    html.I(className="fas fa-check-circle me-2"),
                    f"Successfully closed {pct_label}position in {symbol}. Order ID: {result.get('order_id', 'N/A')}"
                ], color="success", duration=5000, className="mt-3")
            else:
                return dbc.Alert([
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    f"Failed to close position in {symbol}: {result.get('error', 'Unknown error')}"
                ], color="danger", duration=8000, className="mt-3")

        except Exception as e:
            return dbc.Alert([
                html.I(className="fas fa-exclamation-triangle me-2"),
                f"Error closing position: {str(e)}"
            ], color="danger", duration=8000, className="mt-3")

    # =========================================================================
    # CSV Export
    # =========================================================================
    @app.callback(
        Output("positions-csv-download", "data"),
        Input("positions-export-csv-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def export_positions_csv(n_clicks):
        """Export current positions to CSV file."""
        if not n_clicks:
            raise PreventUpdate

        from tradingagents.dataflows.alpaca_utils import AlpacaUtils
        positions_data = AlpacaUtils.get_positions_data()
        if not positions_data:
            raise PreventUpdate

        output = io.StringIO()
        fieldnames = [
            "Symbol", "Side", "Qty", "Current Price", "Avg Entry",
            "Cost Basis", "Market Value", "Today P/L ($)", "Today P/L (%)",
            "Total P/L ($)", "Total P/L (%)"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for p in positions_data:
            writer.writerow({
                "Symbol": p.get("Symbol", ""),
                "Side": p.get("side", "long").upper(),
                "Qty": p.get("Qty", 0),
                "Current Price": p.get("Current Price", ""),
                "Avg Entry": p.get("Avg Entry", ""),
                "Cost Basis": p.get("Cost Basis", ""),
                "Market Value": p.get("Market Value", ""),
                "Today P/L ($)": p.get("Today's P/L ($)", ""),
                "Today P/L (%)": p.get("Today's P/L (%)", ""),
                "Total P/L ($)": p.get("Total P/L ($)", ""),
                "Total P/L (%)": p.get("Total P/L (%)", ""),
            })

        filename = f"positions_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        return dict(content=output.getvalue(), filename=filename)

    # =========================================================================
    # Legacy Liquidation Handlers (kept for backward compatibility)
    # =========================================================================
    @app.callback(
        [Output('liquidate-confirm', 'displayed'),
         Output('liquidate-confirm', 'message')],
        [Input({'type': 'liquidate-btn', 'index': dash.dependencies.ALL}, 'n_clicks')],
        prevent_initial_call=True
    )
    def show_liquidate_confirmation(n_clicks_list):
        """Show confirmation dialog for liquidation"""
        if not n_clicks_list or not any(n_clicks_list):
            return False, ""

        if not ctx.triggered:
            return False, ""

        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
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
            symbol = message.split(" in ")[1].split("?")[0]
            from tradingagents.dataflows.alpaca_utils import AlpacaUtils
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
            symbol = message.split(" in ")[1].split("?")[0]
            from tradingagents.dataflows.alpaca_utils import AlpacaUtils
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
