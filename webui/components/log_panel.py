"""
Log Panel Component for TradingAgents WebUI
Real-time log streaming panel.
"""

import dash_bootstrap_components as dbc
from dash import html, dcc


def create_log_panel():
    """Create the live log panel component."""

    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.Div([
                    html.I(className="fas fa-terminal me-2"),
                    html.Span("Application Logs", className="fw-bold"),
                    dbc.Badge(
                        "0",
                        id="log-count-badge",
                        color="secondary",
                        className="ms-2",
                        pill=True
                    ),
                ], className="d-flex align-items-center"),
                html.Div([
                    # Auto-scroll toggle
                    dbc.Checklist(
                        options=[{"label": "Auto-scroll", "value": True}],
                        value=[True],
                        id="log-auto-scroll",
                        switch=True,
                        inline=True,
                        className="me-3"
                    ),
                    # Log level filter
                    dbc.Select(
                        id="log-level-filter",
                        options=[
                            {"label": "All Levels", "value": "ALL"},
                            {"label": "Debug+", "value": "DEBUG"},
                            {"label": "Info+", "value": "INFO"},
                            {"label": "Warning+", "value": "WARNING"},
                            {"label": "Error+", "value": "ERROR"},
                        ],
                        value="ALL",
                        size="sm",
                        className="me-2",
                        style={"width": "120px"}
                    ),
                    # Clear logs button
                    dbc.Button(
                        [html.I(className="fas fa-trash-alt")],
                        id="clear-logs-btn",
                        color="outline-danger",
                        size="sm",
                        title="Clear logs"
                    ),
                    # Collapse toggle
                    dbc.Button(
                        html.I(className="fas fa-chevron-right", id="log-panel-chevron"),
                        id="log-panel-toggle",
                        color="link",
                        size="sm",
                        className="ms-2 text-muted",
                        title="Expand/Collapse logs"
                    ),
                ], className="d-flex align-items-center")
            ], className="d-flex justify-content-between align-items-center w-100")
        ], className="py-2"),

        dbc.Collapse([
            dbc.CardBody([
                # Log container with monospace font and scrollable
                html.Div(
                    id="log-container",
                    className="log-container",
                    style={
                        "height": "300px",
                        "overflowY": "auto",
                        "overflowX": "auto",
                        "fontFamily": "Monaco, 'Courier New', monospace",
                        "fontSize": "12px",
                        "backgroundColor": "#1e1e1e",
                        "color": "#d4d4d4",
                        "padding": "10px",
                        "borderRadius": "4px",
                        "whiteSpace": "pre-wrap",
                        "wordBreak": "break-word"
                    },
                    children=[
                        html.Div("Waiting for logs...", className="text-muted")
                    ]
                ),

                # Hidden store for log state
                dcc.Store(id="log-last-index", data=0),

                # Interval for log updates (1 second)
                dcc.Interval(
                    id="log-update-interval",
                    interval=1000,  # 1 second for balanced performance
                    n_intervals=0
                )
            ], className="p-2")
        ], id="log-panel-collapse", is_open=False)
    ], className="log-panel-card mb-3")


def format_log_entry(log: dict) -> html.Div:
    """Format a single log entry for display."""
    level_colors = {
        "DEBUG": "#6c757d",
        "INFO": "#17a2b8",
        "WARNING": "#ffc107",
        "ERROR": "#dc3545",
        "CRITICAL": "#dc3545"
    }

    level_color = level_colors.get(log["level"], "#6c757d")

    return html.Div([
        html.Span(f"[{log['timestamp']}] ", style={"color": "#858585"}),
        html.Span(
            f"[{log['level']:8s}] ",
            style={"color": level_color, "fontWeight": "bold" if log["level"] in ["ERROR", "CRITICAL"] else "normal"}
        ),
        html.Span(f"[{log['logger']}] ", style={"color": "#569cd6"}),
        html.Span(log["message"], style={"color": "#d4d4d4"})
    ], className="log-entry", style={"marginBottom": "2px"})
