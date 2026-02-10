"""
Log Panel Component for TradingAgents WebUI
Real-time log streaming panel.
"""

import dash_bootstrap_components as dbc
from dash import html, dcc


def create_log_panel():
    """Create the live log panel component."""

    # Build header content (clickable for collapse)
    header_content = dbc.Row([
        dbc.Col([
            html.I(
                id="log-panel-chevron",
                className="bi bi-chevron-right me-2 chevron-icon"
            ),
            html.Span("📋", className="me-2 panel-icon"),
            html.Span("Application Logs", className="fw-semibold panel-title"),
        ], width="auto", className="d-flex align-items-center"),
        dbc.Col([
            dbc.Badge(
                "0",
                id="log-count-badge",
                color="secondary",
                className="badge-pill",
                pill=True
            ),
        ], width="auto", className="ms-auto d-flex align-items-center"),
    ], className="align-items-center g-0", justify="between")

    # Controls row (inside card body, not header)
    controls_row = html.Div([
        # Streaming toggle
        dbc.Checklist(
            options=[{"label": "Streaming", "value": True}],
            value=[True],
            id="log-streaming-toggle",
            switch=True,
            inline=True,
            className="me-3"
        ),
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
            [html.I(className="bi bi-trash")],
            id="clear-logs-btn",
            color="outline-danger",
            size="sm",
            title="Clear logs"
        ),
    ], className="d-flex align-items-center mb-2")

    return dbc.Card([
        # Clickable header
        html.Div(
            header_content,
            id="log-panel-header",
            n_clicks=0,
            style={"cursor": "pointer"},
            className="collapsible-header card-header"
        ),
        # Collapsible body
        dbc.Collapse(
            dbc.CardBody([
                # Controls row
                controls_row,

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

                # Interval for log updates (1 second) - disabled by default until streaming is on
                dcc.Interval(
                    id="log-update-interval",
                    interval=1000,
                    n_intervals=0,
                    disabled=False
                )
            ], className="p-2 collapsible-body"),
            id="log-panel-collapse",
            is_open=False
        ),
    ], className="mb-3 collapsible-card", id="log-panel")


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
