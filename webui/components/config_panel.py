"""
webui/components/config_panel.py - Compact configuration panel for the web UI.
Redesigned for pro trader workflow with collapsible advanced settings.
"""

import dash_bootstrap_components as dbc
from dash import html, dcc
from datetime import datetime


def create_trading_control_panel():
    """Create the compact trading control panel for the right sidebar."""
    return html.Div([
        # Run Queue Status Section (replaces ticker input)
        html.Div([
            html.Div([
                html.I(className="fas fa-list-check me-2 text-success"),
                html.Span("Run Queue: ", className="text-muted"),
                html.Span(id="config-run-queue-count", children="0", className="fw-bold text-success"),
                html.Span(" symbols", className="text-muted ms-1"),
            ], className="d-flex align-items-center run-queue-status"),
            html.Small(
                "Add symbols via Watchlist > Run Queue tab",
                className="text-muted d-block mt-1"
            ),
        ], className="mb-3 p-2 run-queue-status-container"),

        # Active Settings Summary (inline display)
        html.Div(
            id="active-settings-summary",
            children=[
                html.Div([
                    dbc.Badge("Shallow", color="info", className="me-1", id="depth-badge"),
                    dbc.Badge("5 Analysts", color="secondary", className="me-1", id="analysts-badge"),
                    dbc.Badge("Long Only", color="success", className="me-1", id="mode-badge"),
                ], className="d-flex flex-wrap gap-1")
            ],
            className="mb-2 active-settings-row"
        ),

        # Quick Actions Row
        dbc.Row([
            dbc.Col([
                dbc.Button(
                    [html.I(className="fas fa-cog me-2"), "Settings"],
                    id="toggle-settings-btn",
                    color="secondary",
                    outline=True,
                    size="md",
                    className="w-100"
                ),
            ], width=5),
            dbc.Col([
                html.Div(id="control-button-container", children=[
                    dbc.Button(
                        [html.I(className="fas fa-play me-2"), "Start Analysis"],
                        id="control-btn",
                        color="success",
                        size="md",
                        className="w-100 fw-bold"
                    )
                ])
            ], width=7),
        ], className="mb-3"),

        # Collapsible Settings Section
        dbc.Collapse(
            dbc.Card([
                dbc.CardBody([
                    # Analyst Selection
                    html.H6("Select Analysts", className="mb-2 text-muted"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Checklist(
                                id="analyst-checklist",
                                options=[
                                    {"label": " Market", "value": "market"},
                                    {"label": " Options", "value": "options"},
                                    {"label": " Social", "value": "social"},
                                ],
                                value=["market", "options", "social"],
                                inline=True,
                                className="mb-1"
                            ),
                        ], width=12),
                        dbc.Col([
                            dbc.Checklist(
                                id="analyst-checklist-2",
                                options=[
                                    {"label": " News", "value": "news"},
                                    {"label": " Fundamentals", "value": "fundamentals"},
                                    {"label": " Macro", "value": "macro"},
                                ],
                                value=["news", "fundamentals", "macro"],
                                inline=True,
                            ),
                        ], width=12),
                    ], className="mb-3"),

                    # Hidden individual checkboxes for backward compatibility
                    html.Div([
                        dbc.Checkbox(id="analyst-market", value=True, style={"display": "none"}),
                        dbc.Checkbox(id="analyst-social", value=True, style={"display": "none"}),
                        dbc.Checkbox(id="analyst-news", value=True, style={"display": "none"}),
                        dbc.Checkbox(id="analyst-fundamentals", value=True, style={"display": "none"}),
                        dbc.Checkbox(id="analyst-macro", value=True, style={"display": "none"}),
                        dbc.Checkbox(id="analyst-options", value=True, style={"display": "none"}),
                    ], style={"display": "none"}),

                    html.Hr(className="my-2"),

                    # Research Depth & Trading Mode
                    dbc.Row([
                        dbc.Col([
                            html.H6("Research Depth", className="mb-1 text-muted"),
                            dbc.RadioItems(
                                id="research-depth",
                                options=[
                                    {"label": "Shallow", "value": "Shallow"},
                                    {"label": "Medium", "value": "Medium"},
                                    {"label": "Deep", "value": "Deep"},
                                ],
                                value="Shallow",
                                inline=True,
                                className="small"
                            ),
                            html.Div(id="research-depth-info", className="small text-muted mt-1"),
                        ], md=6),
                        dbc.Col([
                            html.H6("Trading Mode", className="mb-1 text-muted"),
                            dbc.Switch(
                                id="allow-shorts",
                                label="Allow Shorts",
                                value=False,
                                className="small"
                            ),
                            html.Div(id="trading-mode-info", className="small text-muted"),
                        ], md=6),
                    ], className="mb-3"),

                    html.Hr(className="my-2"),

                    # Scheduling
                    html.H6("Scheduling", className="mb-2 text-muted"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Switch(
                                id="loop-enabled",
                                label="Loop Mode",
                                value=False,
                                className="small"
                            ),
                        ], md=4),
                        dbc.Col([
                            dbc.InputGroup([
                                dbc.Input(
                                    id="loop-interval",
                                    type="number",
                                    value=60,
                                    min=1,
                                    max=1440,
                                    size="sm"
                                ),
                                dbc.InputGroupText("min", className="small"),
                            ], size="sm"),
                        ], md=4),
                        dbc.Col([
                            dbc.Switch(
                                id="market-hour-enabled",
                                label="Market Hours",
                                value=False,
                                className="small"
                            ),
                        ], md=4),
                    ], className="mb-2"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Input(
                                id="market-hours-input",
                                type="text",
                                placeholder="Hours: 10,15",
                                value="",
                                size="sm"
                            ),
                        ], md=6),
                        dbc.Col([
                            html.Div(id="market-hours-validation", className="small"),
                        ], md=6),
                    ], className="mb-2"),
                    html.Div(id="scheduling-mode-info", className="small text-muted"),

                    html.Hr(className="my-2"),

                    # Auto Trading
                    html.H6("Auto Trading", className="mb-2 text-muted"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Switch(
                                id="trade-after-analyze",
                                label="Trade After Analysis",
                                value=False,
                                className="small"
                            ),
                        ], md=6),
                        dbc.Col([
                            dbc.InputGroup([
                                dbc.InputGroupText("$", className="small"),
                                dbc.Input(
                                    id="trade-dollar-amount",
                                    type="number",
                                    value=4500,
                                    min=1,
                                    max=10000000,
                                    size="sm"
                                ),
                            ], size="sm"),
                        ], md=6),
                    ], className="mb-2"),
                    html.Div(id="trade-after-analyze-info", className="small text-muted"),

                    html.Hr(className="my-2"),

                    # LLM Models
                    html.H6("LLM Models", className="mb-2 text-muted"),
                    dbc.Row([
                        dbc.Col([
                            html.Small("Quick:", className="text-muted"),
                            dbc.Select(
                                id="quick-llm",
                                options=[
                                    {"label": "gpt-5-nano", "value": "gpt-5-nano"},
                                    {"label": "gpt-5-mini", "value": "gpt-5-mini"},
                                    {"label": "gpt-4o-mini", "value": "gpt-4o-mini"},
                                    {"label": "gpt-4.1-nano", "value": "gpt-4.1-nano"},
                                ],
                                value="gpt-5-nano",
                                size="sm"
                            ),
                        ], md=6),
                        dbc.Col([
                            html.Small("Deep:", className="text-muted"),
                            dbc.Select(
                                id="deep-llm",
                                options=[
                                    {"label": "gpt-5-nano", "value": "gpt-5-nano"},
                                    {"label": "gpt-5-mini", "value": "gpt-5-mini"},
                                    {"label": "o3-mini", "value": "o3-mini"},
                                    {"label": "gpt-4o", "value": "gpt-4o"},
                                ],
                                value="gpt-5-nano",
                                size="sm"
                            ),
                        ], md=6),
                    ]),
                ], className="p-2")
            ], className="settings-card"),
            id="settings-collapse",
            is_open=False
        ),

        # Result text area
        html.Div(id="result-text", className="mt-2 small"),
    ], className="trading-control-panel")


def create_config_panel():
    """Create the configuration panel for the web UI (legacy - for backward compatibility)."""
    return dbc.Card(
        dbc.CardBody([
            html.H4("Analysis Configuration", className="mb-3"),
            html.Hr(),
            # Run Queue Status (replaces ticker input)
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className="fas fa-list-check me-2 text-success"),
                        html.Span("Run Queue: ", className="text-muted"),
                        html.Span(id="config-run-queue-count-legacy", children="0", className="fw-bold text-success"),
                        html.Span(" symbols", className="text-muted ms-1"),
                    ], className="d-flex align-items-center mb-2"),
                    html.Small(
                        "Add symbols via Watchlist > Run Queue tab",
                        className="text-muted"
                    ),
                ], width=12),
            ]),
            html.H5("Select Analysts:", className="mt-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Checkbox(id="analyst-market", label="Market Analyst", value=True, className="mb-2"),
                ], width=6),
                dbc.Col([
                    dbc.Checkbox(id="analyst-social", label="Social Media Analyst", value=True, className="mb-2"),
                ], width=6),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Checkbox(id="analyst-news", label="News Analyst", value=True, className="mb-2"),
                ], width=6),
                dbc.Col([
                    dbc.Checkbox(id="analyst-fundamentals", label="Fundamentals Analyst", value=True, className="mb-2"),
                ], width=6),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Checkbox(id="analyst-macro", label="Macro Analyst", value=True, className="mb-2"),
                ], width=6),
                dbc.Col([
                    # Empty column for alignment
                ], width=6),
            ]),
            html.H5("Research Depth:", className="mt-3"),
            # 50/50 split for research depth selection and information
            dbc.Row([
                dbc.Col([
                    dbc.RadioItems(
                        id="research-depth",
                        options=[
                            {"label": "Shallow", "value": "Shallow"},
                            {"label": "Medium", "value": "Medium"},
                            {"label": "Deep", "value": "Deep"},
                        ],
                        value="Shallow",
                        inline=False,
                        className="mb-3"
                    ),
                ], width=6),
                dbc.Col([
                    # Interactive research depth information
                    html.Div(id="research-depth-info", className="mb-3"),
                ], width=6),
            ]),
            # Execution Mode section removed - always use sequential execution
            html.H5("Trading Mode:", className="mt-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Switch(
                        id="allow-shorts",
                        label="Allow Shorts (Trading Mode)",
                        value=False,
                        className="mb-2"
                    ),
                ], width=6),
                dbc.Col([
                    html.Div(id="trading-mode-info", className="mb-3"),
                ], width=6),
            ]),
            html.H5("Scheduling Configuration:", className="mt-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Switch(
                        id="loop-enabled",
                        label="Enable Loop Mode",
                        value=False,
                        className="mb-2"
                    ),
                ], width=6),
                dbc.Col([
                    dbc.Label("Loop Interval (minutes)", className="mb-1"),
                    dbc.Input(
                        id="loop-interval",
                        type="number",
                        placeholder="60",
                        value=60,
                        min=1,
                        max=1440,  # Max 24 hours
                        className="mb-2"
                    ),
                ], width=6),
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Switch(
                        id="market-hour-enabled",
                        label="Trade at Market Hour",
                        value=False,
                        className="mb-2"
                    ),
                ], width=6),
                dbc.Col([
                    dbc.Label("Trading Hours (e.g., 10,15 for 10AM & 3PM)", className="mb-1"),
                    dbc.Input(
                        id="market-hours-input",
                        type="text",
                        placeholder="e.g., 11,13",
                        value="",
                        className="mb-2"
                    ),
                ], width=6),
            ]),
            # Market hours validation message
            html.Div(id="market-hours-validation", className="mb-2"),
            # Add scheduling mode information display
            html.Div(id="scheduling-mode-info", className="mb-3"),
            html.H5("Automated Trading:", className="mt-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Switch(
                        id="trade-after-analyze",
                        label="Trade After Analyze",
                        value=False,
                        className="mb-2"
                    ),
                ], width=6),
                dbc.Col([
                    dbc.Label("Order Amount ($)", className="mb-1"),
                    dbc.Input(
                        id="trade-dollar-amount",
                        type="number",
                        placeholder="4500",
                        value=4500,
                        min=1,
                        max=10000000,
                        className="mb-2"
                    ),
                ], width=6),
            ]),
            # Add trading mode information display
            html.Div(id="trade-after-analyze-info", className="mb-3"),
            html.H5("LLM Quick Thinker Model:", className="mt-3"),
            dbc.Select(
                id="quick-llm",
                options=[
                    {"label": "gpt-5", "value": "gpt-5"},
                    {"label": "gpt-5-mini", "value": "gpt-5-mini"},
                    {"label": "gpt-5-nano", "value": "gpt-5-nano"},
                    {"label": "gpt-4.1", "value": "gpt-4.1"},
                    {"label": "gpt-4.1-nano", "value": "gpt-4.1-nano"},
                    {"label": "gpt-4.1-mini", "value": "gpt-4.1-mini"},
                    {"label": "gpt-4o", "value": "gpt-4o"},
                    {"label": "gpt-4o-mini", "value": "gpt-4o-mini"},
                    {"label": "o3-mini", "value": "o3-mini"},
                    {"label": "o3", "value": "o3"},
                    {"label": "o1", "value": "o1"},
                ],
                value="gpt-5-nano",
                className="mb-2"
            ),
            html.H5("LLM Deep Thinker Model:", className="mt-3"),
            dbc.Select(
                id="deep-llm",
                options=[
                    {"label": "gpt-5", "value": "gpt-5"},
                    {"label": "gpt-5-mini", "value": "gpt-5-mini"},
                    {"label": "gpt-5-nano", "value": "gpt-5-nano"},
                    {"label": "gpt-4.1", "value": "gpt-4.1"},
                    {"label": "gpt-4.1-nano", "value": "gpt-4.1-nano"},
                    {"label": "gpt-4.1-mini", "value": "gpt-4.1-mini"},
                    {"label": "gpt-4o", "value": "gpt-4o"},
                    {"label": "gpt-4o-mini", "value": "gpt-4o-mini"},
                    {"label": "o3-mini", "value": "o3-mini"},
                    {"label": "o3", "value": "o3"},
                    {"label": "o1", "value": "o1"},
                ],
                value="gpt-5-nano",
                className="mb-3"
            ),
            # Dynamic Start/Stop button
            html.Div(id="control-button-container", children=[
                dbc.Button(
                    "Start Analysis",
                    id="control-btn",
                    color="primary",
                    size="lg",
                    className="w-100 mt-2"
                )
            ]),
            html.Div(id="result-text", className="mt-3")
        ]),
        className="mb-4",
    )
