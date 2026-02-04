"""
Scanner Panel - UI component for market scanner
"""

import dash_bootstrap_components as dbc
from dash import html, dcc
import plotly.graph_objects as go


def create_scanner_panel():
    """Create the market scanner panel."""
    return dbc.Card(
        dbc.CardBody([
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
    """Create a card for a single scanner result."""
    # Determine color based on change
    change_color = "success" if result.change_percent >= 0 else "danger"
    change_icon = "caret-up-fill" if result.change_percent >= 0 else "caret-down-fill"

    # Sentiment badge color
    sentiment_colors = {
        "bullish": "success",
        "bearish": "danger",
        "neutral": "secondary"
    }

    # MACD signal badge
    macd_colors = {
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
        dbc.CardHeader([
            dbc.Row([
                dbc.Col([
                    html.H5(result.symbol, className="mb-0 fw-bold"),
                    html.Small(result.company_name[:25] + "..." if len(result.company_name) > 25 else result.company_name,
                              className="text-muted"),
                ], width=8),
                dbc.Col([
                    html.Div([
                        html.Span(f"${result.price:.2f}", className="fw-bold"),
                        html.Br(),
                        html.Span([
                            html.I(className=f"bi bi-{change_icon} me-1"),
                            f"{result.change_percent:+.2f}%"
                        ], className=f"text-{change_color}")
                    ], className="text-end")
                ], width=4),
            ]),
        ]),
        dbc.CardBody([
            # Sparkline chart
            dcc.Graph(
                figure=sparkline,
                config={"displayModeBar": False},
                style={"height": "60px", "margin": "-10px"}
            ),

            html.Hr(className="my-2"),

            # Key metrics row
            dbc.Row([
                dbc.Col([
                    html.Small("RSI", className="text-muted d-block"),
                    html.Span(f"{result.rsi:.1f}", className="fw-bold"),
                ], width=3, className="text-center"),
                dbc.Col([
                    html.Small("Vol Ratio", className="text-muted d-block"),
                    html.Span(f"{result.volume_ratio:.1f}x", className="fw-bold"),
                ], width=3, className="text-center"),
                dbc.Col([
                    html.Small("MACD", className="text-muted d-block"),
                    dbc.Badge(result.macd_signal.upper(), color=macd_colors.get(result.macd_signal, "secondary"), pill=True),
                ], width=3, className="text-center"),
                dbc.Col([
                    html.Small("News", className="text-muted d-block"),
                    dbc.Badge(result.news_sentiment.upper(), color=sentiment_colors.get(result.news_sentiment, "secondary"), pill=True),
                ], width=3, className="text-center"),
            ], className="mb-2"),

            html.Hr(className="my-2"),

            # Scores
            dbc.Row([
                dbc.Col([
                    html.Small("Tech Score", className="text-muted d-block"),
                    dbc.Badge(f"{result.technical_score}", color=score_color(result.technical_score), className="me-1"),
                ], width=4, className="text-center"),
                dbc.Col([
                    html.Small("News Score", className="text-muted d-block"),
                    dbc.Badge(f"{result.news_score}", color=score_color(result.news_score), className="me-1"),
                ], width=4, className="text-center"),
                dbc.Col([
                    html.Small("Combined", className="text-muted d-block"),
                    dbc.Badge(f"{result.combined_score}", color=score_color(result.combined_score), className="fw-bold"),
                ], width=4, className="text-center"),
            ], className="mb-3"),

            # Rationale
            html.Div([
                html.Small(result.rationale if result.rationale else "No rationale available.",
                          className="text-muted fst-italic")
            ], className="mb-3", style={"minHeight": "50px"}),

            # Sector badge
            html.Div([
                dbc.Badge(result.sector if result.sector else "Unknown", color="light", text_color="dark", className="me-2"),
                html.Small(f"{result.news_count} news items", className="text-muted"),
            ], className="mb-2"),
        ]),
        dbc.CardFooter([
            dbc.Button(
                [html.I(className="bi bi-graph-up me-1"), "Analyze"],
                id={"type": "scanner-analyze-btn", "symbol": result.symbol},
                color="outline-primary",
                size="sm",
                className="w-100"
            ),
        ]),
    ], className="h-100 shadow-sm")


def create_sparkline(data, is_positive=True):
    """Create a simple sparkline chart."""
    if not data or len(data) < 2:
        data = [100, 100]  # Default flat line

    color = "#28a745" if is_positive else "#dc3545"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(len(data))),
        y=data,
        mode='lines',
        line=dict(color=color, width=2),
        fill='tozeroy',
        fillcolor=f"rgba({40 if is_positive else 220}, {167 if is_positive else 53}, {69 if is_positive else 69}, 0.1)",
        hoverinfo='skip'
    ))

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
        height=60
    )

    return fig


def create_scanner_results_grid(results):
    """Create a grid of ticker cards from scanner results."""
    if not results:
        return html.Div(
            "No results found. Try scanning again later.",
            className="text-center text-muted py-4"
        )

    # Create cards in a grid layout (4 columns, 2 rows for 8 results)
    cards = []
    for result in results:
        card_col = dbc.Col(
            create_ticker_card(result),
            xs=12, sm=6, md=4, lg=3,
            className="mb-3"
        )
        cards.append(card_col)

    return dbc.Row(cards)
