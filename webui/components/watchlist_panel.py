"""
webui/components/watchlist_panel.py - Watchlist component for tracking symbols

Drag & drop styles are in webui/assets/custom.css
Drag & drop JavaScript is in webui/assets/watchlist_dragdrop.js
"""

import dash_bootstrap_components as dbc
from dash import html

from webui.components.run_watchlist import create_run_watchlist_panel


def create_watchlist_panel():
    """Create the watchlist panel component"""
    return html.Div([
        # Add symbol input row
        dbc.Row([
            dbc.Col([
                dbc.InputGroup([
                    dbc.Input(
                        id="watchlist-add-input",
                        type="text",
                        placeholder="Add symbol (e.g., AAPL)",
                        className="watchlist-input"
                    ),
                    dbc.Button(
                        html.I(className="fas fa-plus"),
                        id="watchlist-add-btn",
                        color="primary",
                        className="watchlist-add-btn"
                    ),
                ], size="sm")
            ], width=12)
        ], className="mb-3"),

        # Watchlist items container
        html.Div(
            id="watchlist-items-container",
            className="watchlist-items-container",
            children=[
                html.Div(
                    "Add symbols to your watchlist",
                    className="text-muted text-center py-4 watchlist-empty-msg"
                )
            ]
        ),

        # Note: watchlist-reorder-store, watchlist-store, and watchlist-refresh-interval
        # are defined in layout.py create_stores()/create_intervals() for panel visibility support
    ], className="watchlist-panel")


def create_watchlist_item(symbol, price=None, change=None, change_pct=None, index=0):
    """Create a single watchlist item row with drag and drop support"""
    # Determine color based on change
    if change_pct is not None:
        if change_pct > 0:
            change_color = "text-success"
            change_icon = "fa-caret-up"
            change_text = f"+{change_pct:.2f}%"
        elif change_pct < 0:
            change_color = "text-danger"
            change_icon = "fa-caret-down"
            change_text = f"{change_pct:.2f}%"
        else:
            change_color = "text-muted"
            change_icon = "fa-minus"
            change_text = "0.00%"
    else:
        change_color = "text-muted"
        change_icon = "fa-minus"
        change_text = "--"

    price_text = f"${price:.2f}" if price else "--"

    return html.Div([
        # Symbol and price info
        dbc.Row([
            # Drag handle + Symbol
            dbc.Col([
                html.I(className="fas fa-grip-vertical watchlist-drag-handle"),
                html.Span(symbol, className="watchlist-symbol fw-bold"),
            ], width=3, className="d-flex align-items-center"),

            # Price
            dbc.Col([
                html.Span(price_text, className="watchlist-price"),
            ], width=3, className="d-flex align-items-center justify-content-end"),

            # Change
            dbc.Col([
                html.Span([
                    html.I(className=f"fas {change_icon} me-1"),
                    change_text
                ], className=f"watchlist-change {change_color}")
            ], width=3, className="d-flex align-items-center justify-content-end"),

            # Actions
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button(
                        html.I(className="fas fa-chart-line"),
                        id={"type": "watchlist-chart-btn", "symbol": symbol},
                        color="link",
                        size="sm",
                        className="watchlist-action-btn",
                        title="View Chart"
                    ),
                    dbc.Button(
                        html.I(className="fas fa-robot"),
                        id={"type": "watchlist-analyze-btn", "symbol": symbol},
                        color="link",
                        size="sm",
                        className="watchlist-action-btn",
                        title="Analyze"
                    ),
                    dbc.Button(
                        html.I(className="fas fa-play"),
                        id={"type": "watchlist-add-run-btn", "symbol": symbol},
                        color="link",
                        size="sm",
                        className="watchlist-action-btn text-success",
                        title="Add to Portfolio"
                    ),
                    dbc.Button(
                        html.I(className="fas fa-times"),
                        id={"type": "watchlist-remove-btn", "symbol": symbol},
                        color="link",
                        size="sm",
                        className="watchlist-action-btn text-danger",
                        title="Remove"
                    ),
                ], size="sm")
            ], width=3, className="d-flex align-items-center justify-content-end"),
        ], className="align-items-center"),
    ],
        className="watchlist-item",
        id={"type": "watchlist-item", "symbol": symbol},
        draggable="true",
        **{"data-symbol": symbol, "data-index": str(index)}
    )


def create_watchlist_section():
    """Create the collapsible watchlist section for the layout with tabs"""
    return dbc.Card([
        html.Div(
            dbc.Row([
                dbc.Col([
                    html.I(id="watchlist-panel-chevron", className="bi bi-chevron-down me-2"),
                    html.Span("⭐", className="me-2"),
                    html.Span("Watchlist", className="fw-semibold small"),
                    dbc.Badge(
                        id="watchlist-count-badge",
                        children="0",
                        color="primary",
                        className="ms-2"
                    ),
                    html.Span(" / ", className="text-muted mx-1"),
                    html.Span("▶", className="me-1 text-success"),
                    html.Span("Portfolio", className="fw-semibold small"),
                    dbc.Badge(
                        id="run-watchlist-count-badge",
                        children="0",
                        color="success",
                        className="ms-2"
                    ),
                ], width="auto"),
            ], className="align-items-center"),
            id="watchlist-panel-header",
            n_clicks=0,
            className="card-header py-2",
            style={"cursor": "pointer", "padding": "10px 16px"}
        ),
        dbc.Collapse(
            dbc.CardBody([
                # Tabs for Watchlist and Portfolio
                dbc.Tabs([
                    dbc.Tab(
                        label="⭐ Watchlist",
                        tab_id="watchlist-tab",
                        children=create_watchlist_panel(),
                        className="pt-2"
                    ),
                    dbc.Tab(
                        label="▶ Portfolio",
                        tab_id="run-queue-tab",
                        children=create_run_watchlist_panel(),
                        className="pt-2"
                    ),
                ], id="watchlist-tabs", active_tab="watchlist-tab", className="watchlist-tabs"),
            ], className="p-2"),
            id="watchlist-panel-collapse",
            is_open=True
        ),
    ], className="mb-2")
