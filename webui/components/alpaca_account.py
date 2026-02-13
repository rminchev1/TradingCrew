"""
webui/components/alpaca_account.py - Alpaca account information components
"""

import dash_bootstrap_components as dbc
from dash import html, dcc
import pandas as pd
from datetime import datetime
import pytz
import os
from tradingagents.dataflows.alpaca_utils import AlpacaUtils


def _is_alpaca_configured():
    """Check if Alpaca API credentials are configured."""
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    return bool(api_key and secret_key)


def _render_not_configured_message(section_name="Alpaca"):
    """Render a message when Alpaca is not configured."""
    return html.Div([
        html.Div([
            html.I(className="fas fa-key fa-2x mb-3 text-muted"),
            html.H5(f"{section_name} Not Configured", className="text-muted"),
            html.P([
                "Set your Alpaca API keys in ",
                html.Strong("System Settings"),
                " or in your ",
                html.Code(".env"),
                " file to view this data."
            ], className="text-muted small mb-0")
        ], className="text-center p-4")
    ], className="enhanced-table-container")


def _get_pl_color(pl_str: str) -> str:
    """Return the appropriate Bootstrap text class for a P/L value string."""
    try:
        value = float(pl_str.replace("$", "").replace(",", ""))
    except ValueError:
        return "text-muted"
    if value > 0:
        return "text-success"
    elif value < 0:
        return "text-danger"
    return "text-muted"


def _pl_bar(pl_pct_raw):
    """Return a small colored bar proportional to P/L %."""
    color_class = "positive" if pl_pct_raw >= 0 else "negative"
    width = min(abs(pl_pct_raw), 100)
    return html.Div(
        html.Div(
            className=f"pl-bar {color_class}",
            style={"width": f"{max(width, 2)}%"}
        ),
        className="pl-bar-container"
    )


def render_portfolio_summary(positions_data=None, account_info=None):
    """Render portfolio summary bar: total value, total P/L, position count, best/worst."""
    if not _is_alpaca_configured():
        return html.Div()

    try:
        if positions_data is None:
            positions_data = AlpacaUtils.get_positions_data()
        if account_info is None:
            account_info = AlpacaUtils.get_account_info()

        if not positions_data:
            return html.Div()

        total_market_value = sum(p.get("market_value_raw", 0) for p in positions_data)
        total_cost_basis = sum(p.get("cost_basis_raw", 0) for p in positions_data)
        total_unrealized_pl = sum(p.get("total_pl_dollars_raw", 0) for p in positions_data)
        total_pl_pct = (total_unrealized_pl / total_cost_basis * 100) if total_cost_basis != 0 else 0
        num_positions = len(positions_data)

        # Best and worst performer
        best = max(positions_data, key=lambda p: p.get("total_pl_percent_raw", 0))
        worst = min(positions_data, key=lambda p: p.get("total_pl_percent_raw", 0))

        pl_color = "positive" if total_unrealized_pl >= 0 else "negative"
        pl_sign = "+" if total_unrealized_pl >= 0 else ""

        return html.Div([
            dbc.Row([
                dbc.Col(html.Div([
                    html.Div("Total Value", className="stat-label"),
                    html.Div(f"${total_market_value:,.2f}", className="stat-value")
                ], className="portfolio-stat"), width=6, md=3),
                dbc.Col(html.Div([
                    html.Div("Unrealized P/L", className="stat-label"),
                    html.Div(
                        f"{pl_sign}${abs(total_unrealized_pl):,.2f} ({pl_sign}{abs(total_pl_pct):.2f}%)",
                        className=f"stat-value {pl_color}"
                    )
                ], className="portfolio-stat"), width=6, md=3),
                dbc.Col(html.Div([
                    html.Div("Positions", className="stat-label"),
                    html.Div(str(num_positions), className="stat-value")
                ], className="portfolio-stat"), width=6, md=3),
                dbc.Col(html.Div([
                    html.Div("Best / Worst", className="stat-label"),
                    html.Div([
                        html.Span(
                            f"{best['Symbol']} {best.get('total_pl_percent_raw', 0):+.1f}%",
                            className="text-success small fw-bold"
                        ),
                        html.Span(" / ", className="text-muted"),
                        html.Span(
                            f"{worst['Symbol']} {worst.get('total_pl_percent_raw', 0):+.1f}%",
                            className="text-danger small fw-bold"
                        ),
                    ])
                ], className="portfolio-stat"), width=6, md=3),
            ], className="g-0")
        ], className="portfolio-summary-bar")

    except Exception as e:
        print(f"Error rendering portfolio summary: {e}")
        return html.Div()


def render_positions_table(sort_key="symbol", sort_direction="asc", search_filter="", equity=0):
    """Render the enhanced positions table with sort/filter toolbar, new columns, and partial close."""
    if not _is_alpaca_configured():
        return _render_not_configured_message("Positions")

    try:
        positions_data = AlpacaUtils.get_positions_data()

        pos_sort_val = f"{sort_key}-{sort_direction}"

        if not positions_data:
            return html.Div([
                # Toolbar (always shown so sort/filter controls exist in DOM)
                _render_positions_toolbar(shown=0, total=0, sort_value=pos_sort_val, search_value=search_filter),
                html.Div([
                    html.I(className="fas fa-inbox fa-3x mb-3 text-muted", style={"opacity": "0.3"}),
                    html.H5("No Open Positions", className="text-muted mb-2"),
                    html.P("Start trading to see your positions here", className="text-muted small mb-0"),
                ], className="text-center p-5")
            ], className="enhanced-table-container")

        # Compute portfolio weight for each position
        total_equity = equity if equity > 0 else sum(p.get("market_value_raw", 0) for p in positions_data)
        for p in positions_data:
            p["weight"] = (p.get("market_value_raw", 0) / total_equity * 100) if total_equity > 0 else 0

        # Track total count before filtering
        total_count = len(positions_data)

        # Filter
        if search_filter:
            positions_data = [p for p in positions_data if search_filter.upper() in p["Symbol"].upper()]

        shown_count = len(positions_data)

        # Sort
        sort_map = {
            "symbol": lambda p: p["Symbol"].lower(),
            "market_value": lambda p: p.get("market_value_raw", 0),
            "today_pl": lambda p: p.get("today_pl_dollars_raw", 0),
            "total_pl": lambda p: p.get("total_pl_dollars_raw", 0),
            "weight": lambda p: p.get("weight", 0),
            "current_price": lambda p: p.get("current_price", 0),
        }
        key_fn = sort_map.get(sort_key, sort_map["symbol"])
        positions_data.sort(key=key_fn, reverse=(sort_direction == "desc"))

        # Build table rows
        table_rows = []
        for position in positions_data:
            today_pl_color = _get_pl_color(position["Today's P/L ($)"])
            total_pl_color = _get_pl_color(position["Total P/L ($)"])
            side = position.get("side", "long")
            side_badge_class = "long" if side == "long" else "short"
            weight = position.get("weight", 0)

            row = html.Tr([
                # Position: Symbol + Qty + Side badge
                html.Td([
                    html.Div([
                        html.A(
                            html.Strong(position["Symbol"], className="symbol-text"),
                            id={"type": "position-symbol-link", "symbol": position["Symbol"]},
                            href="#",
                            className="symbol-link",
                            title=f"Click to view {position['Symbol']} chart"
                        ),
                        html.Span(
                            side.upper(),
                            className=f"side-badge {side_badge_class} ms-2"
                        ),
                        html.Br(),
                        html.Small(f"{position['Qty']} shares", className="text-muted")
                    ])
                ], className="symbol-cell"),
                # Current Price
                html.Td([
                    html.Div([
                        html.Div(position.get("Current Price", "-"), className="fw-bold"),
                        html.Small(f"Entry: {position['Avg Entry']}", className="text-muted")
                    ])
                ], className="price-cell"),
                # Market Value + Cost Basis
                html.Td([
                    html.Div([
                        html.Div(position["Market Value"], className="fw-bold"),
                        html.Small(f"Cost: {position['Cost Basis']}", className="text-muted")
                    ])
                ], className="value-cell"),
                # Today's P/L with mini bar
                html.Td([
                    html.Div([
                        html.Div(position["Today's P/L ($)"], className=f"fw-bold {today_pl_color}"),
                        html.Small(position["Today's P/L (%)"], className=f"{today_pl_color}"),
                        _pl_bar(position.get("today_pl_percent_raw", 0))
                    ])
                ], className="pnl-cell"),
                # Total P/L with mini bar
                html.Td([
                    html.Div([
                        html.Div(position["Total P/L ($)"], className=f"fw-bold {total_pl_color}"),
                        html.Small(position["Total P/L (%)"], className=f"{total_pl_color}"),
                        _pl_bar(position.get("total_pl_percent_raw", 0))
                    ])
                ], className="pnl-cell"),
                # Weight %
                html.Td([
                    html.Div([
                        html.Div(f"{weight:.1f}%", className="fw-bold"),
                    ])
                ], className="weight-cell"),
                # Actions: Partial close dropdown
                html.Td([
                    dbc.DropdownMenu([
                        dbc.DropdownMenuItem(
                            "Close 25%",
                            id={"type": "partial-close-btn", "symbol": position["Symbol"], "pct": "25"}
                        ),
                        dbc.DropdownMenuItem(
                            "Close 50%",
                            id={"type": "partial-close-btn", "symbol": position["Symbol"], "pct": "50"}
                        ),
                        dbc.DropdownMenuItem(
                            "Close 75%",
                            id={"type": "partial-close-btn", "symbol": position["Symbol"], "pct": "75"}
                        ),
                        dbc.DropdownMenuItem(divider=True),
                        dbc.DropdownMenuItem(
                            [html.I(className="fas fa-times-circle me-1"), "Liquidate"],
                            id={"type": "partial-close-btn", "symbol": position["Symbol"], "pct": "100"},
                            className="text-danger"
                        ),
                    ],
                    label="Close",
                    size="sm",
                    color="danger",
                    toggle_class_name="liquidate-btn",
                    align_end=True
                    )
                ], className="action-cell")
            ], className="table-row-hover", id=f"position-row-{position['Symbol']}")

            table_rows.append(row)

        # Build table with toolbar and scrollable body
        table = html.Div([
            _render_positions_toolbar(shown=shown_count, total=total_count, sort_value=pos_sort_val, search_value=search_filter),
            html.Div([
                html.Table([
                    html.Thead([
                        html.Tr([
                            html.Th("Position", className="table-header"),
                            html.Th("Price", className="table-header"),
                            html.Th("Value", className="table-header"),
                            html.Th("Today P/L", className="table-header"),
                            html.Th("Total P/L", className="table-header"),
                            html.Th("Wt%", className="table-header"),
                            html.Th("Actions", className="table-header text-center")
                        ])
                    ]),
                    html.Tbody(table_rows)
                ], className="enhanced-table enhanced-positions")
            ], className="positions-scroll-container")
        ], className="enhanced-table-container")

        return table

    except Exception as e:
        print(f"Error rendering positions table: {e}")
        return html.Div([
            _render_positions_toolbar(shown=0, total=0, sort_value=f"{sort_key}-{sort_direction}", search_value=search_filter),
            html.Div([
                html.I(className="fas fa-exclamation-triangle fa-2x mb-3 text-warning"),
                html.H5("Unable to Load Positions", className="text-warning"),
                html.P("Check your Alpaca API keys", className="text-muted"),
                html.Small(f"Error: {str(e)}", className="text-muted")
            ], className="text-center p-4")
        ], className="enhanced-table-container error-state")


def _render_positions_toolbar(shown=0, total=0, sort_value="symbol-asc", search_value=""):
    """Render the search/sort/export toolbar above the positions table."""
    # Build count badge text: "3/16" when filtered, "16" when showing all
    if total > 0 and shown != total:
        count_text = f"{shown}/{total}"
    else:
        count_text = str(total)

    return html.Div([
        # Position count badge
        html.Span(
            count_text,
            className="positions-count-badge",
            title=f"Showing {shown} of {total} positions"
        ),
        # Search input
        dbc.Input(
            id="positions-search-input",
            type="text",
            placeholder="Search symbol...",
            className="search-input",
            size="sm",
            debounce=True,
            value=search_value or "",
        ),
        # Sort dropdown
        dbc.Select(
            id="positions-sort-select",
            options=[
                {"label": "Symbol A-Z", "value": "symbol-asc"},
                {"label": "Symbol Z-A", "value": "symbol-desc"},
                {"label": "Value (High)", "value": "market_value-desc"},
                {"label": "Value (Low)", "value": "market_value-asc"},
                {"label": "Today P/L (Best)", "value": "today_pl-desc"},
                {"label": "Today P/L (Worst)", "value": "today_pl-asc"},
                {"label": "Total P/L (Best)", "value": "total_pl-desc"},
                {"label": "Total P/L (Worst)", "value": "total_pl-asc"},
                {"label": "Weight (High)", "value": "weight-desc"},
                {"label": "Weight (Low)", "value": "weight-asc"},
            ],
            value=sort_value,
            className="sort-select",
            size="sm",
        ),
        # CSV Export button
        dbc.Button([
            html.I(className="fas fa-download me-1"),
            "CSV"
        ],
        id="positions-export-csv-btn",
        color="secondary",
        size="sm",
        outline=True,
        className="export-btn ms-auto"
        ),
    ], className="positions-toolbar")

def render_orders_table(page=1, page_size=12, sort_key="date", sort_direction="desc", search_filter=""):
    """Render the enhanced recent orders table with sort/filter toolbar and scroll container.

    Returns:
        tuple: (html_content, total_pages) - the table HTML and total page count.
    """
    if not _is_alpaca_configured():
        return _render_not_configured_message("Orders"), 1

    try:
        # Fetch all orders at once (up to 100); pagination is handled locally after filter/sort
        orders_data, total_count = AlpacaUtils.get_recent_orders(page=1, page_size=100, return_total=True)
        ord_sort_val = f"{sort_key}-{sort_direction}"

        if not orders_data:
            return html.Div([
                _render_orders_toolbar(shown=0, total=0, sort_value=ord_sort_val, search_value=search_filter),
                html.Div([
                    html.I(className="fas fa-history fa-3x mb-3 text-muted", style={"opacity": "0.3"}),
                    html.H5("No Recent Orders", className="text-muted mb-2"),
                    html.P("No trading activity found", className="text-muted small mb-0")
                ], className="text-center p-5"),
            ], className="enhanced-table-container"), 1

        # Filter
        all_count = len(orders_data)
        if search_filter:
            orders_data = [o for o in orders_data if search_filter.upper() in o["Asset"].upper()]
        shown_count = len(orders_data)

        # Sort
        sort_map = {
            "date": lambda o: o.get("Date", ""),
            "symbol": lambda o: o.get("Asset", "").lower(),
            "side": lambda o: str(o.get("Side", "")).lower(),
            "status": lambda o: str(o.get("Status", "")).lower(),
            "qty": lambda o: o.get("Qty", 0),
            "filled": lambda o: o.get("Filled Qty", 0),
        }
        key_fn = sort_map.get(sort_key, sort_map["date"])
        orders_data.sort(key=key_fn, reverse=(sort_direction == "desc"))

        # Paginate after filter/sort
        start = (page - 1) * page_size
        page_data = orders_data[start:start + page_size]
        total_pages = max(1, (len(orders_data) + page_size - 1) // page_size)

        # Build table rows
        table_rows = []
        for idx, order in enumerate(page_data):
            status_str = str(order.get("Status", "")).lower()
            status_color = {
                "filled": "text-success",
                "canceled": "text-danger",
                "pending_new": "text-warning",
                "accepted": "text-info",
                "rejected": "text-danger",
                "partially_filled": "text-warning",
                "new": "text-info",
            }.get(status_str, "text-muted")

            side_str = str(order.get("Side", "")).lower()
            side_badge_class = "buy" if side_str == "buy" else "sell"

            row = html.Tr([
                # Symbol + Order Type + Date
                html.Td([
                    html.Div([
                        html.A(
                            html.Strong(order["Asset"], className="symbol-text"),
                            id={"type": "order-symbol-link", "symbol": order["Asset"], "index": idx},
                            href="#",
                            className="symbol-link",
                            title=f"Click to view {order['Asset']} chart"
                        ),
                        html.Span(
                            side_str.upper(),
                            className=f"side-badge {side_badge_class} ms-2"
                        ),
                        html.Br(),
                        html.Small(str(order["Order Type"]).replace("OrderType.", "").upper(), className="text-muted")
                    ])
                ], className="symbol-cell"),
                # Date
                html.Td([
                    html.Div([
                        html.Div(order.get("Date", "-"), className="fw-bold"),
                        html.Small(
                            order.get("Order ID Short", "-"),
                            className="text-muted",
                            title=order.get("Order ID", "")
                        )
                    ])
                ], className="date-cell"),
                # Qty + Filled
                html.Td([
                    html.Div([
                        html.Div(f"{order['Qty']}", className="fw-bold"),
                        html.Small(f"{order['Filled Qty']} filled", className="text-muted")
                    ])
                ], className="qty-cell"),
                # Avg Fill Price
                html.Td([
                    html.Div([
                        html.Div(order["Avg. Fill Price"], className="fw-bold"),
                    ])
                ], className="price-cell"),
                # Status badge
                html.Td([
                    html.Span(
                        str(order["Status"]).replace("OrderStatus.", "").replace("_", " ").upper(),
                        className=f"order-status-badge {status_str}"
                    )
                ], className="status-cell")
            ], className="table-row-hover", id=f"order-row-{order.get('Asset', '')}-{page}-{idx}")

            table_rows.append(row)

        # Build table with toolbar and scroll container
        table = html.Div([
            _render_orders_toolbar(shown=shown_count, total=all_count, sort_value=ord_sort_val, search_value=search_filter),
            html.Div([
                html.Table([
                    html.Thead([
                        html.Tr([
                            html.Th("Symbol", className="table-header"),
                            html.Th("Date", className="table-header"),
                            html.Th("Qty", className="table-header"),
                            html.Th("Fill Price", className="table-header"),
                            html.Th("Status", className="table-header"),
                        ])
                    ]),
                    html.Tbody(table_rows)
                ], className="enhanced-table enhanced-orders")
            ], className="orders-scroll-container"),
        ], className="enhanced-table-container")

        return table, total_pages

    except Exception as e:
        print(f"Error rendering orders table: {e}")
        return html.Div([
            _render_orders_toolbar(shown=0, total=0, sort_value=f"{sort_key}-{sort_direction}", search_value=search_filter),
            html.Div([
                html.I(className="fas fa-exclamation-triangle fa-2x mb-3 text-warning"),
                html.H5("Unable to Load Orders", className="text-warning"),
                html.P("Check your Alpaca API keys", className="text-muted"),
                html.Small(f"Error: {str(e)}", className="text-muted")
            ], className="text-center p-4"),
        ], className="enhanced-table-container error-state"), 1


def _render_orders_toolbar(shown=0, total=0, sort_value="date-desc", search_value=""):
    """Render the search/sort toolbar above the orders table."""
    if total > 0 and shown != total:
        count_text = f"{shown}/{total}"
    else:
        count_text = str(total)

    return html.Div([
        html.Span(
            count_text,
            className="positions-count-badge",
            title=f"Showing {shown} of {total} orders"
        ),
        dbc.Input(
            id="orders-search-input",
            type="text",
            placeholder="Search symbol...",
            className="search-input",
            size="sm",
            debounce=True,
            value=search_value or "",
        ),
        dbc.Select(
            id="orders-sort-select",
            options=[
                {"label": "Newest First", "value": "date-desc"},
                {"label": "Oldest First", "value": "date-asc"},
                {"label": "Symbol A-Z", "value": "symbol-asc"},
                {"label": "Symbol Z-A", "value": "symbol-desc"},
                {"label": "Side", "value": "side-asc"},
                {"label": "Status", "value": "status-asc"},
            ],
            value=sort_value,
            className="sort-select",
            size="sm",
        ),
    ], className="positions-toolbar")

def render_account_summary():
    """Render account summary information"""
    # Check if Alpaca is configured
    if not _is_alpaca_configured():
        return _render_not_configured_message("Account")

    try:
        account_info = AlpacaUtils.get_account_info()
        
        buying_power = account_info["buying_power"]
        cash = account_info["cash"]
        daily_change_dollars = account_info["daily_change_dollars"]
        daily_change_percent = account_info["daily_change_percent"]
        
        # Determine value class for daily change based on whether it's positive or negative
        daily_change_class = "positive" if daily_change_dollars >= 0 else "negative"
        change_icon = "fas fa-arrow-up" if daily_change_dollars >= 0 else "fas fa-arrow-down"
        
        summary = html.Div([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Div([
                            html.I(className="fas fa-wallet me-2"),
                            "Buying Power"
                        ], className="summary-label"),
                        html.Div(f"${buying_power:.2f}", className="summary-value")
                    ], className="summary-item enhanced-summary-item")
                ], width=4),
                dbc.Col([
                    html.Div([
                        html.Div([
                            html.I(className="fas fa-dollar-sign me-2"),
                            "Cash"
                        ], className="summary-label"),
                        html.Div(f"${cash:.2f}", className="summary-value")
                    ], className="summary-item enhanced-summary-item")
                ], width=4),
                dbc.Col([
                    html.Div([
                        html.Div([
                            html.I(className=f"{change_icon} me-2"),
                            "Daily Change"
                        ], className="summary-label"),
                        html.Div([
                            f"${daily_change_dollars:.2f} ", 
                            html.Span(f"({daily_change_percent:.2f}%)")
                        ], className=f"summary-value {daily_change_class}")
                    ], className="summary-item enhanced-summary-item")
                ], width=4)
            ])
        ], className="account-summary enhanced-account-summary")
        
        return summary
        
    except Exception as e:
        print(f"Error rendering account summary: {e}")
        return html.Div([
            html.Div([
                html.I(className="fas fa-exclamation-triangle fa-2x mb-3 text-warning"),
                html.H5("Unable to Load Account Summary", className="text-warning"),
                html.P("Check your Alpaca API keys", className="text-muted"),
                html.Small(f"Error: {str(e)}", className="text-muted")
            ], className="text-center p-4")
        ], className="enhanced-account-summary error-state")

def get_positions_data():
    """Get positions data for table callback"""
    try:
        return AlpacaUtils.get_positions_data()
    except Exception as e:
        print(f"Error getting positions data: {e}")
        return []

def get_recent_orders(page=1, page_size=7, return_total=False):
    """Get recent orders data for table callback"""
    try:
        return AlpacaUtils.get_recent_orders(page=page, page_size=page_size, return_total=return_total)
    except Exception as e:
        print(f"Error getting orders data: {e}")
        if return_total:
            return [], 0
        return []

def get_market_time_info():
    """Get current market time (EST/EDT) and market status."""
    eastern = pytz.timezone('US/Eastern')
    now_eastern = datetime.now(eastern)

    # Format time string with timezone abbreviation
    time_str = now_eastern.strftime("%I:%M:%S %p")
    tz_abbr = now_eastern.strftime("%Z")  # EST or EDT

    # Check if market is open (9:30 AM - 4:00 PM ET, Mon-Fri)
    weekday = now_eastern.weekday()  # 0=Monday, 6=Sunday
    hour = now_eastern.hour
    minute = now_eastern.minute

    market_open_time = 9 * 60 + 30  # 9:30 AM in minutes
    market_close_time = 16 * 60  # 4:00 PM in minutes
    current_time_minutes = hour * 60 + minute

    if weekday >= 5:  # Weekend
        is_open = False
        status = "Closed"
        status_color = "text-danger"
    elif current_time_minutes < market_open_time:
        is_open = False
        mins_until_open = market_open_time - current_time_minutes
        hrs, mins = divmod(mins_until_open, 60)
        status = f"Opens in {hrs}h {mins}m"
        status_color = "text-warning"
    elif current_time_minutes >= market_close_time:
        is_open = False
        status = "Closed"
        status_color = "text-danger"
    else:
        is_open = True
        mins_until_close = market_close_time - current_time_minutes
        hrs, mins = divmod(mins_until_close, 60)
        status = f"Open ({hrs}h {mins}m left)"
        status_color = "text-success"

    return time_str, tz_abbr, status, status_color, is_open


def render_compact_account_bar():
    """Render a compact horizontal account summary bar for the top of the page."""
    # Get market time info (always show this)
    time_str, tz_abbr, market_status, status_color, is_open = get_market_time_info()
    market_icon = "fa-clock" if is_open else "fa-moon"

    # Check if Alpaca is configured
    if not _is_alpaca_configured():
        return html.Div([
            dbc.Row([
                # Market Time (EST/EDT)
                dbc.Col([
                    html.Div([
                        html.I(className=f"fas {market_icon} me-2 {status_color}"),
                        html.Span(id="market-time-display", children=f"{time_str} {tz_abbr}", className="fw-bold text-white"),
                        html.Span(" · ", className="text-muted mx-1"),
                        html.Span(id="market-status-display", children=market_status, className=f"small {status_color}")
                    ], className="d-flex align-items-center")
                ], width="auto"),
                # Divider
                dbc.Col([
                    html.Span("|", className="text-muted mx-2")
                ], width="auto", className="px-0"),
                # Not configured message
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-key me-2 text-warning"),
                        html.Span("Alpaca API not configured", className="text-muted small")
                    ], className="d-flex align-items-center")
                ], width="auto"),
                # Refresh button on right
                dbc.Col([
                    html.Button([
                        html.I(className="fas fa-sync-alt")
                    ],
                    id="refresh-alpaca-btn",
                    className="btn btn-sm btn-outline-secondary",
                    title="Refresh account data"
                    )
                ], width="auto", className="ms-auto")
            ], className="align-items-center g-0", justify="start")
        ], className="compact-account-bar", id="compact-account-bar")

    try:
        account_info = AlpacaUtils.get_account_info()

        buying_power = account_info["buying_power"]
        cash = account_info["cash"]
        daily_change_dollars = account_info["daily_change_dollars"]
        daily_change_percent = account_info["daily_change_percent"]

        # Determine styling for daily change
        if daily_change_dollars >= 0:
            change_color = "text-success"
            change_icon = "fa-arrow-up"
            change_sign = "+"
        else:
            change_color = "text-danger"
            change_icon = "fa-arrow-down"
            change_sign = ""

        # Get market time info
        time_str, tz_abbr, market_status, status_color, is_open = get_market_time_info()
        market_icon = "fa-clock" if is_open else "fa-moon"

        return html.Div([
            dbc.Row([
                # Market Time (EST/EDT)
                dbc.Col([
                    html.Div([
                        html.I(className=f"fas {market_icon} me-2 {status_color}"),
                        html.Span(id="market-time-display", children=f"{time_str} {tz_abbr}", className="fw-bold text-white"),
                        html.Span(" · ", className="text-muted mx-1"),
                        html.Span(id="market-status-display", children=market_status, className=f"small {status_color}")
                    ], className="d-flex align-items-center")
                ], width="auto"),
                # Divider
                dbc.Col([
                    html.Span("|", className="text-muted mx-2")
                ], width="auto", className="px-0"),
                # Buying Power
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-wallet me-2 text-primary"),
                        html.Span("Buying Power: ", className="text-muted"),
                        html.Span(f"${buying_power:,.2f}", className="fw-bold text-white")
                    ], className="d-flex align-items-center")
                ], width="auto"),
                # Divider
                dbc.Col([
                    html.Span("|", className="text-muted mx-2")
                ], width="auto", className="px-0"),
                # Cash
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-dollar-sign me-2 text-info"),
                        html.Span("Cash: ", className="text-muted"),
                        html.Span(f"${cash:,.2f}", className="fw-bold text-white")
                    ], className="d-flex align-items-center")
                ], width="auto"),
                # Divider
                dbc.Col([
                    html.Span("|", className="text-muted mx-2")
                ], width="auto", className="px-0"),
                # Daily Change
                dbc.Col([
                    html.Div([
                        html.I(className=f"fas {change_icon} me-2 {change_color}"),
                        html.Span("Today: ", className="text-muted"),
                        html.Span(
                            f"{change_sign}${abs(daily_change_dollars):,.2f} ({change_sign}{abs(daily_change_percent):.2f}%)",
                            className=f"fw-bold {change_color}"
                        )
                    ], className="d-flex align-items-center")
                ], width="auto"),
                # Refresh button on right
                dbc.Col([
                    html.Button([
                        html.I(className="fas fa-sync-alt")
                    ],
                    id="refresh-alpaca-btn",
                    className="btn btn-sm btn-outline-secondary",
                    title="Refresh account data"
                    )
                ], width="auto", className="ms-auto")
            ], className="align-items-center g-0", justify="start")
        ], className="compact-account-bar", id="compact-account-bar")

    except Exception as e:
        # Still show market time even if account data fails
        time_str, tz_abbr, market_status, status_color, is_open = get_market_time_info()
        market_icon = "fa-clock" if is_open else "fa-moon"

        return html.Div([
            dbc.Row([
                # Market Time (EST/EDT)
                dbc.Col([
                    html.Div([
                        html.I(className=f"fas {market_icon} me-2 {status_color}"),
                        html.Span(id="market-time-display", children=f"{time_str} {tz_abbr}", className="fw-bold text-white"),
                        html.Span(" · ", className="text-muted mx-1"),
                        html.Span(id="market-status-display", children=market_status, className=f"small {status_color}")
                    ], className="d-flex align-items-center")
                ], width="auto"),
                # Divider
                dbc.Col([
                    html.Span("|", className="text-muted mx-2")
                ], width="auto", className="px-0"),
                # Error message
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-exclamation-triangle me-2 text-warning"),
                        html.Span("Unable to load account data", className="text-muted")
                    ], className="d-flex align-items-center")
                ], width="auto"),
                # Refresh button on right
                dbc.Col([
                    html.Button([
                        html.I(className="fas fa-sync-alt")
                    ],
                    id="refresh-alpaca-btn",
                    className="btn btn-sm btn-outline-secondary",
                    title="Refresh account data"
                    )
                ], width="auto", className="ms-auto")
            ], className="align-items-center g-0", justify="start")
        ], className="compact-account-bar", id="compact-account-bar")


def render_options_positions_table():
    """Render the options positions table with close buttons"""
    # Check if Alpaca is configured
    if not _is_alpaca_configured():
        return _render_not_configured_message("Options Positions")

    try:
        positions_data = AlpacaUtils.get_options_positions_data()

        if not positions_data:
            return html.Div([
                html.Div([
                    html.I(className="fas fa-file-contract fa-2x mb-3 text-muted"),
                    html.H6("No Options Positions", className="text-muted"),
                    html.P("No open options contracts", className="text-muted small mb-0")
                ], className="text-center p-4")
            ], className="enhanced-table-container")

        # Create enhanced table rows
        table_rows = []
        for position in positions_data:
            # Helper to decide colour based on the numeric value
            def _get_pl_color(pl_str: str) -> str:
                try:
                    value = float(pl_str.replace("$", "").replace(",", ""))
                except ValueError:
                    return "text-muted"
                if value > 0:
                    return "text-success"
                elif value < 0:
                    return "text-danger"
                else:
                    return "text-muted"

            total_pl_color = _get_pl_color(position["Total P/L ($)"])
            contract_type_color = "text-success" if position["Type"] == "CALL" else "text-danger"

            row = html.Tr([
                html.Td([
                    html.Div([
                        html.Strong(position["Underlying"], className="symbol-text"),
                        html.Br(),
                        html.Small([
                            html.Span(position["Type"], className=f"fw-bold {contract_type_color}"),
                            f" ${position['Strike'].replace('$', '')}"
                        ], className="text-muted")
                    ])
                ], className="symbol-cell"),
                html.Td([
                    html.Div([
                        html.Small(position["Expiration"], className="text-muted")
                    ])
                ], className="exp-cell"),
                html.Td([
                    html.Div([
                        html.Div(f"{position['Qty']} contracts", className="fw-bold"),
                    ])
                ], className="qty-cell"),
                html.Td([
                    html.Div([
                        html.Div(position["Market Value"], className="fw-bold"),
                        html.Small(f"@ {position['Current Price']}", className="text-muted")
                    ])
                ], className="value-cell"),
                html.Td([
                    html.Div([
                        html.Div(position["Total P/L ($)"], className=f"fw-bold {total_pl_color}"),
                        html.Small(position["Total P/L (%)"], className=f"{total_pl_color}")
                    ])
                ], className="pnl-cell"),
                html.Td([
                    dbc.Button([
                        html.I(className="fas fa-times-circle me-1"),
                        "Close"
                    ],
                    id={"type": "close-option-btn", "index": position["Symbol"]},
                    color="danger",
                    size="sm",
                    outline=True,
                    className="liquidate-btn"
                    )
                ], className="action-cell")
            ], className="table-row-hover", id=f"option-position-row-{position['Symbol']}")

            table_rows.append(row)

        # Create enhanced table
        table = html.Div([
            html.Table([
                html.Thead([
                    html.Tr([
                        html.Th("Contract", className="table-header"),
                        html.Th("Expiration", className="table-header"),
                        html.Th("Qty", className="table-header"),
                        html.Th("Value", className="table-header"),
                        html.Th("P/L", className="table-header"),
                        html.Th("Actions", className="table-header text-center")
                    ])
                ]),
                html.Tbody(table_rows)
            ], className="enhanced-table")
        ], className="enhanced-table-container")

        return table

    except Exception as e:
        print(f"Error rendering options positions table: {e}")
        return html.Div([
            html.Div([
                html.I(className="fas fa-exclamation-triangle fa-2x mb-3 text-warning"),
                html.H6("Unable to Load Options", className="text-warning"),
                html.Small(f"Error: {str(e)}", className="text-muted")
            ], className="text-center p-3")
        ], className="enhanced-table-container error-state")


def render_options_orders_table(page=1, page_size=5):
    """Render the options orders table"""
    # Check if Alpaca is configured
    if not _is_alpaca_configured():
        return _render_not_configured_message("Options Orders")

    try:
        orders_data, total_count = AlpacaUtils.get_options_orders(page=page, page_size=page_size, return_total=True)
        total_pages = max(1, (total_count + page_size - 1) // page_size)

        if not orders_data:
            return html.Div([
                html.Div([
                    html.I(className="fas fa-file-contract fa-2x mb-3 text-muted"),
                    html.H6("No Options Orders", className="text-muted"),
                    html.P("No options trading activity", className="text-muted small mb-0")
                ], className="text-center p-4"),
                html.Div([
                    dbc.Pagination(
                        id="options-orders-pagination",
                        max_value=1,
                        active_page=1,
                        size="sm",
                        className="mt-2",
                        style={"display": "none"}
                    )
                ], className="d-flex justify-content-end")
            ], className="enhanced-table-container")

        # Create enhanced table rows
        table_rows = []
        for idx, order in enumerate(orders_data):
            # Status color coding
            status_color = {
                "filled": "text-success",
                "canceled": "text-danger",
                "pending_new": "text-warning",
                "accepted": "text-info",
                "rejected": "text-danger"
            }.get(str(order.get("Status", "")).lower(), "text-muted")

            # Side color coding
            side_str = str(order.get("Side", "")).lower()
            side_color = "text-success" if "buy" in side_str else "text-danger"

            contract_type_color = "text-success" if order.get("Type") == "CALL" else "text-danger"

            row = html.Tr([
                html.Td([
                    html.Small(order.get("Date", "-"), className="text-muted")
                ], className="date-cell"),
                html.Td([
                    html.Div([
                        html.Strong(order["Underlying"], className="symbol-text"),
                        html.Br(),
                        html.Small([
                            html.Span(order["Type"], className=f"fw-bold {contract_type_color}"),
                            f" {order['Strike']}"
                        ], className="text-muted")
                    ])
                ], className="symbol-cell"),
                html.Td([
                    html.Small(order.get("Expiration", "-"), className="text-muted")
                ], className="exp-cell"),
                html.Td([
                    html.Div([
                        html.Span(order["Side"], className=f"fw-bold {side_color}"),
                        html.Br(),
                        html.Small(f"{order['Qty']} contracts", className="text-muted")
                    ])
                ], className="side-cell"),
                html.Td([
                    html.Div(order["Avg. Fill Price"], className="fw-bold")
                ], className="price-cell"),
                html.Td([
                    html.Span([
                        html.I(className=f"fas fa-circle me-1 {status_color}"),
                        str(order["Status"])
                    ], className=f"status-badge {status_color}")
                ], className="status-cell")
            ], className="table-row-hover", id=f"option-order-row-{order.get('Underlying', '')}-{page}-{idx}")

            table_rows.append(row)

        # Create enhanced table with pagination
        table = html.Div([
            html.Table([
                html.Thead([
                    html.Tr([
                        html.Th("Date", className="table-header"),
                        html.Th("Contract", className="table-header"),
                        html.Th("Exp", className="table-header"),
                        html.Th("Side & Qty", className="table-header"),
                        html.Th("Fill Price", className="table-header"),
                        html.Th("Status", className="table-header")
                    ])
                ]),
                html.Tbody(table_rows)
            ], className="enhanced-table"),
            html.Div([
                html.Small(f"Page {page} of {total_pages} ({total_count} orders)", className="text-muted me-3 align-self-center"),
                dbc.Pagination(
                    id="options-orders-pagination",
                    max_value=total_pages,
                    active_page=page,
                    size="sm",
                    first_last=True,
                    previous_next=True
                )
            ], className="d-flex justify-content-end align-items-center mt-2")
        ], className="enhanced-table-container")

        return table

    except Exception as e:
        print(f"Error rendering options orders table: {e}")
        return html.Div([
            html.Div([
                html.I(className="fas fa-exclamation-triangle fa-2x mb-3 text-warning"),
                html.H6("Unable to Load Options Orders", className="text-warning"),
                html.Small(f"Error: {str(e)}", className="text-muted")
            ], className="text-center p-3"),
            html.Div([
                dbc.Pagination(
                    id="options-orders-pagination",
                    max_value=1,
                    active_page=1,
                    size="sm",
                    className="mt-2",
                    style={"display": "none"}
                )
            ], className="d-flex justify-content-end")
        ], className="enhanced-table-container error-state")


def render_options_section():
    """Render the options positions and orders section."""
    return html.Div([
        dbc.Row([
            # Options Positions column
            dbc.Col([
                html.Div([
                    html.H6([
                        html.I(className="fas fa-file-contract me-2"),
                        "Options Positions"
                    ], className="mb-2 d-flex align-items-center"),
                    html.Div(id="options-positions-table-container", children=render_options_positions_table())
                ])
            ], lg=6, className="mb-3 mb-lg-0"),
            # Options Orders column
            dbc.Col([
                html.Div([
                    html.H6([
                        html.I(className="fas fa-scroll me-2"),
                        "Options Orders"
                    ], className="mb-2 d-flex align-items-center"),
                    html.Div(id="options-orders-table-container", children=render_options_orders_table())
                ])
            ], lg=6)
        ]),
        # Hidden div for options close confirmations
        dcc.ConfirmDialog(
            id='close-option-confirm',
            message='',
        ),
        html.Div(id="close-option-status", className="mt-2")
    ])


def render_positions_orders_section():
    """Render positions and orders side by side with portfolio summary above."""
    initial_orders, initial_total_pages = render_orders_table()
    return html.Div([
        # Portfolio summary (full width, above the two columns)
        html.Div(id="portfolio-summary-container", children=render_portfolio_summary()),
        dbc.Row([
            # Positions column
            dbc.Col([
                html.Div([
                    html.H6([
                        html.I(className="fas fa-briefcase me-2"),
                        "Open Positions"
                    ], className="mb-2 d-flex align-items-center"),
                    html.Div(id="positions-table-container", children=render_positions_table())
                ])
            ], lg=6, className="mb-3 mb-lg-0"),
            # Orders column
            dbc.Col([
                html.Div([
                    html.H6([
                        html.I(className="fas fa-history me-2"),
                        "Recent Orders"
                    ], className="mb-2 d-flex align-items-center"),
                    html.Div(id="orders-table-container", children=initial_orders),
                    # Pagination lives OUTSIDE orders-table-container so it persists across re-renders
                    html.Div([
                        html.Small(id="orders-page-info",
                                   children=f"Page 1 of {initial_total_pages}",
                                   className="text-muted me-3 align-self-center"),
                        dbc.Pagination(
                            id="orders-pagination",
                            max_value=initial_total_pages,
                            active_page=1,
                            size="sm",
                            first_last=True,
                            previous_next=True,
                        )
                    ], className="d-flex justify-content-end align-items-center mt-3",
                       style={"display": "none"} if initial_total_pages <= 1 else {})
                ])
            ], lg=6)
        ]),
        # Hidden div for liquidation confirmations (kept for backward compat)
        dcc.ConfirmDialog(id='liquidate-confirm', message=''),
        html.Div(id="liquidation-status", className="mt-2"),
        # Partial close confirmation
        dcc.ConfirmDialog(id='partial-close-confirm', message=''),
        html.Div(id="partial-close-status", className="mt-2"),
    ])


def render_alpaca_account_section():
    """Render the complete Alpaca account section (legacy - for backward compatibility)"""
    return html.Div([
        html.H4([
            html.I(className="fas fa-chart-line me-2"),
            "Alpaca Paper Trading Account",
            html.Button([
                html.I(className="fas fa-sync-alt")
            ],
            id="refresh-alpaca-btn",
            className="btn btn-sm btn-outline-primary ms-auto",
            title="Refresh Alpaca account data"
            )
        ], className="mb-3 d-flex align-items-center"),
        html.Hr(),

        # Account Summary at the top
        render_account_summary(),

        # Open Positions Panel (full width)
        html.Div([
            html.H5([
                html.I(className="fas fa-briefcase me-2"),
                "Open Positions"
            ], className="mb-3"),
            html.Div(id="positions-table-container", children=render_positions_table())
        ], className="mb-4"),

        # Recent Orders Panel (full width, below positions)
        html.Div([
            html.H5([
                html.I(className="fas fa-history me-2"),
                "Recent Orders"
            ], className="mb-3"),
            html.Div(id="orders-table-container", children=render_orders_table())
        ], className="mb-3"),

        # Hidden div for liquidation confirmations
        dcc.ConfirmDialog(
            id='liquidate-confirm',
            message='',
        ),
        html.Div(id="liquidation-status", className="mt-3")
    ], className="mb-4 alpaca-account-section enhanced-alpaca-section") 