"""
webui/components/chart_panel.py - Chart panel with symbol-based pagination and technical indicators

Uses TradingView lightweight-charts for professional charting experience.
"""

import dash_bootstrap_components as dbc
from dash import dcc, html


def create_symbol_pagination(pagination_id, max_symbols=1):
    """Create a custom pagination component using symbol names instead of page numbers"""
    return html.Div(id=f"{pagination_id}-container",
                   children=[
                       html.Div("No symbols available",
                               className="text-muted text-center",
                               style={"padding": "10px"})
                   ],
                   className="symbol-pagination-container")


def create_timeframe_buttons():
    """Create the timeframe selection buttons"""
    return dbc.ButtonGroup([
        dbc.Button("5m", id="period-5m", color="secondary", outline=True, size="sm", className="me-1"),
        dbc.Button("15m", id="period-15m", color="secondary", outline=True, size="sm", className="me-1"),
        dbc.Button("30m", id="period-30m", color="secondary", outline=True, size="sm", className="me-1"),
        dbc.Button("1H", id="period-1h", color="secondary", outline=True, size="sm", className="me-1"),
        dbc.Button("4H", id="period-4h", color="secondary", outline=True, size="sm", className="me-1"),
        dbc.Button("1D", id="period-1d", color="secondary", outline=True, size="sm", className="me-1"),
        dbc.Button("1W", id="period-1w", color="secondary", outline=True, size="sm", className="me-1"),
        dbc.Button("1M", id="period-1mo", color="secondary", outline=True, size="sm", className="me-1"),
        dbc.Button("1Y", id="period-1y", color="secondary", outline=True, size="sm"),
    ], className="flex-wrap")


def create_indicator_checklist():
    """Create the indicator toggle checklist"""
    return dbc.DropdownMenu(
        label="📊 Indicators",
        children=[
            dbc.DropdownMenuItem(
                dbc.Checklist(
                    options=[
                        {"label": " SMA (20, 50)", "value": "sma"},
                        {"label": " EMA (12, 26)", "value": "ema"},
                        {"label": " Bollinger Bands", "value": "bb"},
                        {"label": " RSI (14)", "value": "rsi"},
                        {"label": " MACD (12/26/9)", "value": "macd"},
                        {"label": " OBV", "value": "obv"},
                    ],
                    value=["sma", "bb", "rsi", "macd"],  # Default selected indicators
                    id="indicator-checklist",
                    inline=False,
                    className="px-2 py-1"
                ),
                toggle=False  # Keep dropdown open when clicking items
            ),
        ],
        toggle_class_name="btn btn-outline-secondary btn-sm",
        className="ms-2"
    )


def create_chart_panel():
    """Create the chart panel for the web UI with symbol-based pagination and technical indicators."""
    return dbc.Card(
        dbc.CardBody([
            html.H4("Stock Chart & Technical Analysis", className="mb-3"),
            html.Hr(),
            # Symbol pagination and refresh button
            dbc.Row([
                dbc.Col([
                    create_symbol_pagination("chart-pagination")
                ], width=8),
                dbc.Col([
                    dbc.Button("⛶", id="chart-fullscreen-btn", color="outline-secondary", size="sm", className="float-end ms-2", title="Toggle Fullscreen"),
                    dbc.Button(
                        [html.Span(className="live-dot"), " LIVE"],
                        id="chart-live-btn", color="outline-success", size="sm",
                        className="float-end ms-2 chart-live-btn", title="Toggle Live Updates"
                    ),
                    dbc.Button("🔄", id="manual-chart-refresh", color="outline-secondary", size="sm", className="float-end", title="Refresh Chart"),
                ], width=4)
            ], className="mb-2"),
            # Current symbol display and last updated
            html.Div(id="current-symbol-display", className="text-center my-2"),
            html.Div(id="chart-last-updated", className="text-muted text-center small mb-2"),
            # Timeframe buttons and indicator dropdown
            dbc.Row([
                dbc.Col([
                    create_timeframe_buttons()
                ], width="auto", className="flex-grow-1"),
                dbc.Col([
                    create_indicator_checklist()
                ], width="auto")
            ], className="mb-3 align-items-center"),
            # Chart wrapper for fullscreen support
            html.Div(
                id="chart-fullscreen-wrapper",
                className="chart-fullscreen-wrapper",
                children=[
                    # Fullscreen header (only visible in fullscreen mode)
                    html.Div(
                        id="fullscreen-header",
                        className="fullscreen-header",
                        children=[
                            html.Span(id="fullscreen-symbol-display", className="fullscreen-symbol"),
                            dbc.Button("✕", id="exit-fullscreen-btn", color="light", size="sm", className="exit-fullscreen-btn"),
                        ]
                    ),
                    # OHLC data legend (updates on crosshair move)
                    html.Div(
                        id="chart-ohlc-legend",
                        className="chart-ohlc-legend",
                        children=[
                            html.Span("O", className="ohlc-label"),
                            html.Span("-", id="ohlc-open", className="ohlc-value"),
                            html.Span("H", className="ohlc-label"),
                            html.Span("-", id="ohlc-high", className="ohlc-value"),
                            html.Span("L", className="ohlc-label"),
                            html.Span("-", id="ohlc-low", className="ohlc-value"),
                            html.Span("C", className="ohlc-label"),
                            html.Span("-", id="ohlc-close", className="ohlc-value"),
                            html.Span("", id="ohlc-change", className="ohlc-change"),
                            html.Span("Vol", className="ohlc-label ohlc-vol-label"),
                            html.Span("-", id="ohlc-volume", className="ohlc-value"),
                        ]
                    ),
                    # Overlay indicator legend (SMA, EMA, BB — updates on crosshair)
                    html.Div(id="chart-indicator-legend", className="chart-indicator-legend"),
                    # TradingView chart container (main price chart)
                    html.Div(
                        id="tv-chart-container",
                        className="tradingview-chart",
                        style={"height": "450px", "width": "100%", "minHeight": "350px"}
                    ),
                    # RSI indicator pane with legend
                    html.Div(id="rsi-pane-legend", className="pane-legend"),
                    html.Div(
                        id="tv-rsi-container",
                        className="tradingview-indicator-pane",
                        style={"height": "120px", "width": "100%", "display": "none"}
                    ),
                    # MACD indicator pane with legend
                    html.Div(id="macd-pane-legend", className="pane-legend"),
                    html.Div(
                        id="tv-macd-container",
                        className="tradingview-indicator-pane",
                        style={"height": "120px", "width": "100%", "display": "none"}
                    ),
                    # OBV indicator pane with legend
                    html.Div(id="obv-pane-legend", className="pane-legend"),
                    html.Div(
                        id="tv-obv-container",
                        className="tradingview-indicator-pane",
                        style={"height": "120px", "width": "100%", "display": "none"}
                    ),
                ]
            ),
            # Data stores for chart
            dcc.Store(id="tv-chart-data-store", data=None),
            dcc.Store(id="tv-chart-config-store", data={"showRsi": True, "showMacd": True, "showObv": False}),
            # Hidden div for clientside callback output
            html.Div(id="tv-chart-update-trigger", style={"display": "none"}),
            # Hidden pagination component for control callback compatibility
            html.Div([
                dbc.Pagination(
                    id="chart-pagination",
                    max_value=1,
                    active_page=1,
                    fully_expanded=True,
                    first_last=True,
                    previous_next=True,
                    className="d-none"
                ),
                # Hidden chart-container div for backward compatibility
                html.Div(id="chart-container", style={"display": "none"})
            ], style={"display": "none"})
        ]),
        className="mb-4"
    )
