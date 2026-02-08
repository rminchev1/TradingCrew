"""
webui/components/run_watchlist.py - Run Queue panel for symbols to analyze

The Run Queue is the active trading queue that serves as the source of symbols
for analysis. Users add symbols from the regular watchlist to the Run Queue.
"""

import dash_bootstrap_components as dbc
from dash import html, dcc


def create_run_watchlist_panel():
    """Create the Run Queue panel component"""
    return html.Div([
        # Header with count
        html.Div([
            html.I(className="fas fa-list-check me-2 text-success"),
            html.Span("Symbols to analyze: ", className="text-muted small"),
            html.Span(id="run-watchlist-count", children="0", className="fw-bold text-success")
        ], className="mb-3 d-flex align-items-center"),

        # Items container
        html.Div(
            id="run-watchlist-items-container",
            className="run-watchlist-items-container",
            children=[
                html.Div(
                    "Add symbols from Watchlist",
                    className="text-muted text-center py-4 run-watchlist-empty-msg"
                )
            ]
        ),

        # Clear all button
        dbc.Button(
            [html.I(className="fas fa-trash me-2"), "Clear All"],
            id="run-watchlist-clear-btn",
            color="outline-danger",
            size="sm",
            className="mt-3 w-100"
        ),

        # Store for run queue (persisted in localStorage)
        dcc.Store(
            id="run-watchlist-store",
            storage_type="local",
            data={"symbols": []}
        )
    ], className="run-watchlist-panel")


def create_run_watchlist_item(symbol, index=0):
    """Create a single run queue item"""
    return html.Div([
        # Play icon
        html.I(className="fas fa-play text-success me-2"),
        # Symbol name
        html.Span(symbol, className="fw-bold flex-grow-1 run-watchlist-symbol"),
        # Remove button
        dbc.Button(
            html.I(className="fas fa-times"),
            id={"type": "run-watchlist-remove-btn", "symbol": symbol},
            color="link",
            size="sm",
            className="text-danger p-0 run-watchlist-remove-btn",
            title="Remove from Run Queue"
        )
    ],
        className="run-watchlist-item d-flex align-items-center",
        id={"type": "run-watchlist-item", "symbol": symbol},
        **{"data-symbol": symbol, "data-index": str(index)}
    )
