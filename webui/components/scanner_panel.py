"""
Scanner Panel - UI component for market scanner
"""

import os
import dash_bootstrap_components as dbc
from dash import html, dcc
import plotly.graph_objects as go


def _is_alpaca_configured():
    """Check if Alpaca API credentials are configured."""
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    return bool(api_key and secret_key)


def _create_config_warning():
    """Create a warning alert for missing API configuration."""
    return dbc.Alert(
        [
            html.I(className="bi bi-exclamation-triangle-fill me-2"),
            html.Strong("API Configuration Required: "),
            "The scanner needs Alpaca API credentials to fetch real market data. ",
            "Without configuration, results shown are based on fallback data with neutral scores. ",
            html.A(
                "Configure your .env file",
                href="https://github.com/rminchev1/TradingCrew#configuration",
                target="_blank",
                className="alert-link"
            ),
            " to enable full scanner functionality."
        ],
        color="warning",
        className="mb-3",
        style={"fontSize": "0.85rem"}
    )


def create_scanner_panel():
    """Create the market scanner panel."""
    return dbc.Card(
        dbc.CardBody([
            # Persistent storage for scanner results (survives page refresh)
            dcc.Store(id="scanner-results-store", storage_type="local"),

            dbc.Row([
                dbc.Col([
                    html.H4("Market Scanner", className="mb-0"),
                    html.Small("Find trading opportunities in real-time", className="text-muted"),
                ], width=8),
                dbc.Col([
                    dbc.Button(
                        [html.I(className="bi bi-search me-2"), "Scan Market"],
                        id="scanner-btn",
                        color="primary",
                        className="w-100"
                    ),
                ], width=4, className="d-flex align-items-center"),
            ], className="mb-3"),

            # Timestamp display (shows when last scan was performed)
            html.Div(id="scanner-timestamp-display", className="text-muted small text-end mb-2"),

            # Configuration warning (shown when Alpaca not configured)
            _create_config_warning() if not _is_alpaca_configured() else None,

            html.Hr(),

            # Progress indicator (hidden by default)
            html.Div(
                id="scanner-progress-container",
                children=[
                    dbc.Progress(
                        id="scanner-progress-bar",
                        value=0,
                        striped=True,
                        animated=True,
                        className="mb-2"
                    ),
                    html.Div(id="scanner-progress-text", className="text-center text-muted small"),
                ],
                style={"display": "none"}
            ),

            # Error message
            dbc.Alert(
                id="scanner-error-alert",
                color="danger",
                is_open=False,
                dismissable=True,
                className="mt-2"
            ),

            # Results container
            html.Div(id="scanner-results-container", children=[
                html.Div(
                    "Click 'Scan Market' to find trading opportunities based on technical indicators and news sentiment.",
                    className="text-center text-muted py-4"
                )
            ]),
        ]),
        className="mb-4"
    )


def create_ticker_card(result):
    """Create a compact card for a single scanner result."""
    # Determine color based on change
    change_color = "success" if result.change_percent >= 0 else "danger"
    change_icon = "caret-up-fill" if result.change_percent >= 0 else "caret-down-fill"

    # Sentiment badge color
    sentiment_colors = {
        "bullish": "success",
        "bearish": "danger",
        "neutral": "secondary"
    }

    # Score color based on value
    def score_color(score):
        if score >= 70:
            return "success"
        elif score >= 50:
            return "warning"
        else:
            return "danger"

    # Create mini sparkline chart
    sparkline = create_sparkline(result.chart_data, result.change_percent >= 0)

    return dbc.Card([
        # Compact header with symbol and price
        dbc.CardBody([
            # Top row: Symbol, Price, Change
            dbc.Row([
                dbc.Col([
                    html.Span(result.symbol, className="fw-bold fs-5 text-primary"),
                ], width=4),
                dbc.Col([
                    html.Span(f"${result.price:.2f}", className="fw-bold"),
                ], width=4, className="text-center"),
                dbc.Col([
                    html.Span([
                        html.I(className=f"bi bi-{change_icon} me-1"),
                        f"{result.change_percent:+.1f}%"
                    ], className=f"text-{change_color} fw-bold")
                ], width=4, className="text-end"),
            ], className="mb-2 align-items-center"),

            # Company name
            html.Div(
                result.company_name[:30] + "..." if len(result.company_name) > 30 else result.company_name,
                className="text-muted small mb-2",
                style={"whiteSpace": "nowrap", "overflow": "hidden", "textOverflow": "ellipsis"}
            ),

            # Sparkline chart
            dcc.Graph(
                figure=sparkline,
                config={"displayModeBar": False},
                style={"height": "40px", "margin": "-5px -10px"}
            ),

            # Metrics row - compact badges
            html.Div([
                dbc.Badge(f"RSI {result.rsi:.0f}", color="info", className="me-1 mb-1"),
                dbc.Badge(f"{result.volume_ratio:.1f}x Vol", color="secondary", className="me-1 mb-1"),
                dbc.Badge(
                    result.macd_signal.upper(),
                    color=sentiment_colors.get(result.macd_signal, "secondary"),
                    className="me-1 mb-1"
                ),
                dbc.Badge(
                    f"News: {result.news_sentiment[:4].upper()}",
                    color=sentiment_colors.get(result.news_sentiment, "secondary"),
                    className="mb-1"
                ),
            ], className="mb-2", style={"lineHeight": "1.8"}),

            # Score bar
            html.Div([
                html.Div([
                    html.Small("Score: ", className="text-muted"),
                    html.Span(f"{result.combined_score}", className=f"fw-bold text-{score_color(result.combined_score)}"),
                    html.Small("/100", className="text-muted"),
                ], className="d-flex align-items-center justify-content-between"),
                dbc.Progress(
                    value=result.combined_score,
                    color=score_color(result.combined_score),
                    style={"height": "6px"},
                    className="mt-1"
                ),
            ], className="mb-2"),

            # Action buttons row
            dbc.ButtonGroup([
                dbc.Button(
                    [html.I(className="bi bi-robot me-1"), "Analyze"],
                    id={"type": "scanner-analyze-btn", "symbol": result.symbol},
                    color="outline-primary",
                    size="sm",
                    n_clicks=0,
                ),
                dbc.Button(
                    [html.I(className="bi bi-star me-1"), "Watch"],
                    id={"type": "scanner-add-watchlist-btn", "symbol": result.symbol},
                    color="outline-secondary",
                    size="sm",
                    n_clicks=0,
                ),
            ], className="w-100 mt-2"),
        ], className="p-2"),
    ], className="scanner-result-card h-100", style={
        "minWidth": "180px",
        "backgroundColor": "#1a2332",
        "border": "1px solid #334155",
        "borderRadius": "8px"
    })


def create_sparkline(data, is_positive=True):
    """Create a simple sparkline chart."""
    if not data or len(data) < 2:
        data = [100, 100]  # Default flat line

    color = "#10B981" if is_positive else "#EF4444"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(len(data))),
        y=data,
        mode='lines',
        line=dict(color=color, width=1.5),
        fill='tozeroy',
        fillcolor=f"rgba({16 if is_positive else 239}, {185 if is_positive else 68}, {129 if is_positive else 68}, 0.15)",
        hoverinfo='skip'
    ))

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
        height=40
    )

    return fig


def create_scanner_results_grid(results):
    """Create a scrollable grid of ticker cards from scanner results."""
    if not results:
        return html.Div(
            "No results found. Try scanning again later.",
            className="text-center text-muted py-4"
        )

    # Create cards in a horizontal scrollable container
    cards = []
    for result in results:
        card_wrapper = html.Div(
            create_ticker_card(result),
            style={
                "minWidth": "200px",
                "maxWidth": "220px",
                "flex": "0 0 auto"
            },
            className="me-2"
        )
        cards.append(card_wrapper)

    return html.Div([
        # Scrollable card container
        html.Div(
            cards,
            style={
                "display": "flex",
                "overflowX": "auto",
                "paddingBottom": "10px",
                "gap": "8px"
            },
            className="scanner-cards-scroll"
        ),
        # Scroll hint
        html.Div(
            [
                html.I(className="bi bi-arrow-left-right me-1"),
                "Scroll to see more"
            ],
            className="text-muted small text-center mt-2"
        ) if len(results) > 3 else None
    ])
