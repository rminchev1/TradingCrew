"""
webui/components/chart_panel.py - Chart panel with symbol-based pagination and technical indicators
"""

import dash_bootstrap_components as dbc
from dash import dcc, html
from webui.utils.charts import create_welcome_chart


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
                    dbc.Button("🔄 Refresh Chart", id="manual-chart-refresh", color="outline-secondary", size="sm", className="float-end"),
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
            # Chart container with dynamic height
            html.Div(
                dcc.Graph(
                    id="chart-container",
                    figure=create_welcome_chart(),
                    config={
                        'displayModeBar': True,
                        'responsive': True,
                        'scrollZoom': True,
                        'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'eraseshape'],
                        'modeBarButtonsToRemove': ['lasso2d', 'select2d']
                    },
                    style={"height": "100%", "width": "100%", "minHeight": "400px"}
                ),
                id="chart-wrapper",
                style={"height": "auto", "minHeight": "400px", "width": "100%", "overflow": "hidden"}
            ),
            # Hidden original pagination component for control callback compatibility
            html.Div([
                dbc.Pagination(
                    id="chart-pagination",
                    max_value=1,
                    fully_expanded=True,
                    first_last=True,
                    previous_next=True,
                    className="d-none"  # Bootstrap class to hide the element
                )
            ], style={"display": "none"})  # Additional CSS hiding
        ]),
        className="mb-4"
    )
