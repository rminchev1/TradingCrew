"""
webui/components/system_settings.py - System Settings Page Component
Global configuration options for API keys, LLM models, and analysis settings.
"""

import dash_bootstrap_components as dbc
from dash import html, dcc
import os


def create_api_key_input(key_id, label, env_var, has_test=True):
    """Create a password-masked API key input with reveal toggle and optional test button."""
    # Check if env var is set
    env_value = os.getenv(env_var)
    has_env_value = bool(env_value)

    cols = [
        dbc.Col(dbc.Label(label, className="mb-0"), width=3),
        dbc.Col(
            dbc.InputGroup([
                dbc.Input(
                    id=f"setting-{key_id}",
                    type="password",
                    placeholder=f"{'••••••••' if has_env_value else f'Enter {label}'}",
                    className="border-end-0"
                ),
                dbc.Button(
                    html.I(className="fas fa-eye"),
                    id=f"reveal-{key_id}",
                    color="secondary",
                    outline=True,
                    className="border-start-0"
                )
            ], size="sm"),
            width=5 if has_test else 7
        ),
    ]

    if has_test:
        cols.append(dbc.Col(
            dbc.Button("Test", id=f"test-{key_id}", size="sm", color="info", outline=True),
            width=2
        ))

    cols.append(dbc.Col(
        html.Span(
            id=f"status-{key_id}",
            children=[
                html.I(className="fas fa-check-circle text-success me-1") if has_env_value else html.I(className="fas fa-times-circle text-warning me-1"),
                "From env" if has_env_value else "Not set"
            ]
        ),
        width=2
    ))

    return dbc.Row(cols, className="mb-2 align-items-center")


def create_settings_card(title, content, icon=None):
    """Create a card wrapper for a settings section."""
    header_content = [html.Span(title, className="fw-semibold")]
    if icon:
        header_content.insert(0, html.I(className=f"{icon} me-2"))

    return dbc.Card([
        dbc.CardHeader(header_content),
        dbc.CardBody(content, className="py-3")
    ], className="mb-3")


def create_api_keys_section():
    """Create the API Keys & Credentials section."""
    return html.Div([
        # OpenAI
        create_api_key_input("openai-api-key", "OpenAI API Key", "OPENAI_API_KEY"),

        html.Hr(className="my-2"),

        # Alpaca
        create_api_key_input("alpaca-api-key", "Alpaca API Key", "ALPACA_API_KEY"),
        create_api_key_input("alpaca-secret-key", "Alpaca Secret Key", "ALPACA_SECRET_KEY", has_test=False),

        # Paper/Live Mode
        dbc.Row([
            dbc.Col(dbc.Label("Trading Mode", className="mb-0"), width=3),
            dbc.Col(
                dbc.Select(
                    id="setting-alpaca-paper-mode",
                    options=[
                        {"label": "Paper Trading (Recommended)", "value": "True"},
                        {"label": "Live Trading", "value": "False"}
                    ],
                    value=os.getenv("ALPACA_USE_PAPER", "True"),
                    size="sm"
                ),
                width=5
            ),
            dbc.Col(width=2),
            dbc.Col(
                html.Span(
                    id="status-alpaca-mode",
                    children=[
                        html.I(className="fas fa-flask text-info me-1"),
                        "PAPER MODE"
                    ]
                ),
                width=2
            )
        ], className="mb-2 align-items-center"),

        html.Hr(className="my-2"),

        # Finnhub
        create_api_key_input("finnhub-api-key", "Finnhub API Key", "FINNHUB_API_KEY"),

        # FRED
        create_api_key_input("fred-api-key", "FRED API Key", "FRED_API_KEY"),

        # CoinDesk
        create_api_key_input("coindesk-api-key", "CoinDesk API Key", "COINDESK_API_KEY"),

        html.Hr(className="my-2"),

        # Reddit API
        html.Div([
            html.Small("Reddit API (for live social sentiment)", className="text-muted d-block mb-2"),
        ]),
        create_api_key_input("reddit-client-id", "Reddit Client ID", "REDDIT_CLIENT_ID"),
        create_api_key_input("reddit-client-secret", "Reddit Client Secret", "REDDIT_CLIENT_SECRET", has_test=False),

        # Reddit User Agent
        dbc.Row([
            dbc.Col(dbc.Label("Reddit User Agent", className="mb-0"), width=3),
            dbc.Col(
                dbc.Input(
                    id="setting-reddit-user-agent",
                    type="text",
                    placeholder="TradingCrew/1.0",
                    value=os.getenv("REDDIT_USER_AGENT", "TradingCrew/1.0"),
                    size="sm"
                ),
                width=5
            ),
            dbc.Col(width=2),
            dbc.Col(
                html.Small("App identifier", className="text-muted"),
                width=2
            )
        ], className="mb-2 align-items-center"),
    ])


def create_llm_section():
    """Create the LLM Models section."""
    return html.Div([
        dbc.Row([
            dbc.Col(dbc.Label("Deep Think Model", className="mb-0"), width=3),
            dbc.Col(
                dbc.Select(
                    id="setting-deep-think-llm",
                    options=[
                        {"label": "gpt-5.2-pro (Best)", "value": "gpt-5.2-pro"},
                        {"label": "gpt-5.2", "value": "gpt-5.2"},
                        {"label": "gpt-5.1", "value": "gpt-5.1"},
                        {"label": "gpt-5", "value": "gpt-5"},
                        {"label": "o4-mini (Recommended)", "value": "o4-mini"},
                        {"label": "o3-pro", "value": "o3-pro"},
                        {"label": "o3", "value": "o3"},
                        {"label": "o3-mini", "value": "o3-mini"},
                        {"label": "gpt-4.1", "value": "gpt-4.1"},
                        {"label": "gpt-4.1-mini", "value": "gpt-4.1-mini"},
                        {"label": "gpt-4o", "value": "gpt-4o"},
                        {"label": "gpt-4o-mini", "value": "gpt-4o-mini"},
                    ],
                    value="o4-mini",
                    size="sm"
                ),
                width=5
            ),
            dbc.Col(
                html.Small("Complex reasoning tasks", className="text-muted"),
                width=4
            )
        ], className="mb-2 align-items-center"),

        dbc.Row([
            dbc.Col(dbc.Label("Quick Think Model", className="mb-0"), width=3),
            dbc.Col(
                dbc.Select(
                    id="setting-quick-think-llm",
                    options=[
                        {"label": "gpt-5.2-instant (Best)", "value": "gpt-5.2-instant"},
                        {"label": "gpt-5-mini", "value": "gpt-5-mini"},
                        {"label": "gpt-5-nano", "value": "gpt-5-nano"},
                        {"label": "gpt-4.1-nano (Recommended)", "value": "gpt-4.1-nano"},
                        {"label": "gpt-4.1-mini", "value": "gpt-4.1-mini"},
                        {"label": "gpt-4.1", "value": "gpt-4.1"},
                        {"label": "gpt-4o-mini", "value": "gpt-4o-mini"},
                        {"label": "gpt-4o", "value": "gpt-4o"},
                    ],
                    value="gpt-4.1-nano",
                    size="sm"
                ),
                width=5
            ),
            dbc.Col(
                html.Small("Fast analysis tasks", className="text-muted"),
                width=4
            )
        ], className="mb-2 align-items-center"),
    ])


def create_analysis_section():
    """Create the Analysis Defaults section."""
    return html.Div([
        dbc.Row([
            dbc.Col(dbc.Label("Max Debate Rounds", className="mb-0"), width=4),
            dbc.Col(
                dbc.Input(
                    id="setting-max-debate-rounds",
                    type="number",
                    min=1,
                    max=10,
                    value=4,
                    size="sm"
                ),
                width=3
            ),
            dbc.Col(
                html.Small("Bull/Bear debate depth (1-10)", className="text-muted"),
                width=5
            )
        ], className="mb-2 align-items-center"),

        dbc.Row([
            dbc.Col(dbc.Label("Max Risk Rounds", className="mb-0"), width=4),
            dbc.Col(
                dbc.Input(
                    id="setting-max-risk-rounds",
                    type="number",
                    min=1,
                    max=10,
                    value=3,
                    size="sm"
                ),
                width=3
            ),
            dbc.Col(
                html.Small("Risk discussion depth (1-10)", className="text-muted"),
                width=5
            )
        ], className="mb-2 align-items-center"),

        dbc.Row([
            dbc.Col(dbc.Label("Parallel Analysts", className="mb-0"), width=4),
            dbc.Col(
                dbc.Switch(
                    id="setting-parallel-analysts",
                    value=True,
                    className="mt-1"
                ),
                width=3
            ),
            dbc.Col(
                html.Small("Run analysts concurrently", className="text-muted"),
                width=5
            )
        ], className="mb-2 align-items-center"),

        dbc.Row([
            dbc.Col(dbc.Label("Online Tools", className="mb-0"), width=4),
            dbc.Col(
                dbc.Switch(
                    id="setting-online-tools",
                    value=True,
                    className="mt-1"
                ),
                width=3
            ),
            dbc.Col(
                html.Small("Enable external data fetching", className="text-muted"),
                width=5
            )
        ], className="mb-2 align-items-center"),

        dbc.Row([
            dbc.Col(dbc.Label("Max Recursion Limit", className="mb-0"), width=4),
            dbc.Col(
                dbc.Input(
                    id="setting-max-recur-limit",
                    type="number",
                    min=50,
                    max=500,
                    value=200,
                    size="sm"
                ),
                width=3
            ),
            dbc.Col(
                html.Small("Graph execution limit (50-500)", className="text-muted"),
                width=5
            )
        ], className="mb-2 align-items-center"),

        dbc.Row([
            dbc.Col(dbc.Label("Max Parallel Tickers", className="mb-0"), width=4),
            dbc.Col(
                dbc.Input(
                    id="setting-max-parallel-tickers",
                    type="number",
                    min=1,
                    max=10,
                    value=3,
                    size="sm"
                ),
                width=3
            ),
            dbc.Col(
                html.Small("Concurrent ticker analyses (1-10)", className="text-muted"),
                width=5
            )
        ], className="mb-2 align-items-center"),
    ])


def create_scanner_section():
    """Create the Market Scanner section."""
    return html.Div([
        dbc.Row([
            dbc.Col(dbc.Label("Results Count", className="mb-0"), width=4),
            dbc.Col(
                dbc.Input(
                    id="setting-scanner-num-results",
                    type="number",
                    min=5,
                    max=50,
                    value=20,
                    size="sm"
                ),
                width=3
            ),
            dbc.Col(
                html.Small("Top N stocks returned (5-50)", className="text-muted"),
                width=5
            )
        ], className="mb-2 align-items-center"),

        dbc.Row([
            dbc.Col(dbc.Label("LLM Sentiment", className="mb-0"), width=4),
            dbc.Col(
                dbc.Switch(
                    id="setting-scanner-llm-sentiment",
                    value=False,
                    className="mt-1"
                ),
                width=3
            ),
            dbc.Col(
                html.Small("GPT for news sentiment (costs $)", className="text-muted"),
                width=5
            )
        ], className="mb-2 align-items-center"),

        dbc.Row([
            dbc.Col(dbc.Label("Options Flow", className="mb-0"), width=4),
            dbc.Col(
                dbc.Switch(
                    id="setting-scanner-options-flow",
                    value=True,
                    className="mt-1"
                ),
                width=3
            ),
            dbc.Col(
                html.Small("Include options analysis", className="text-muted"),
                width=5
            )
        ], className="mb-2 align-items-center"),

        dbc.Row([
            dbc.Col(dbc.Label("Cache TTL (seconds)", className="mb-0"), width=4),
            dbc.Col(
                dbc.Input(
                    id="setting-scanner-cache-ttl",
                    type="number",
                    min=60,
                    max=3600,
                    value=300,
                    size="sm"
                ),
                width=3
            ),
            dbc.Col(
                html.Small("Cache duration (60-3600s)", className="text-muted"),
                width=5
            )
        ], className="mb-2 align-items-center"),

        dbc.Row([
            dbc.Col(dbc.Label("Dynamic Universe", className="mb-0"), width=4),
            dbc.Col(
                dbc.Switch(
                    id="setting-scanner-dynamic-universe",
                    value=True,
                    className="mt-1"
                ),
                width=3
            ),
            dbc.Col(
                html.Small("Top 200 liquid stocks vs predefined", className="text-muted"),
                width=5
            )
        ], className="mb-2 align-items-center"),
    ])


def create_risk_management_section():
    """Create the Risk Management (Stop-Loss/Take-Profit) section."""
    return html.Div([
        # Section description
        html.Div([
            html.Small(
                "Configure automatic stop-loss and take-profit orders for stock positions. "
                "Uses Alpaca's bracket order system for atomic execution.",
                className="text-muted d-block mb-3"
            ),
        ]),

        # Stop-Loss Settings
        html.Div([
            html.Small("Stop-Loss Settings", className="text-muted fw-semibold d-block mb-2"),
        ]),

        # Enable Stop-Loss Toggle
        dbc.Row([
            dbc.Col(dbc.Label("Enable Stop-Loss", className="mb-0"), width=4),
            dbc.Col(
                dbc.Switch(
                    id="setting-enable-stop-loss",
                    value=False,
                    className="mt-1"
                ),
                width=3
            ),
            dbc.Col(
                html.Small("Auto-place stop-loss orders", className="text-muted"),
                width=5
            )
        ], className="mb-2 align-items-center"),

        # Stop-Loss Percentage
        dbc.Row([
            dbc.Col(dbc.Label("Default SL %", className="mb-0"), width=4),
            dbc.Col(
                dbc.Input(
                    id="setting-stop-loss-percentage",
                    type="number",
                    min=0.5,
                    max=50.0,
                    step=0.5,
                    value=5.0,
                    size="sm"
                ),
                width=3
            ),
            dbc.Col(
                html.Small("% below entry (fallback)", className="text-muted"),
                width=5
            )
        ], className="mb-2 align-items-center"),

        # Use AI SL Toggle
        dbc.Row([
            dbc.Col(dbc.Label("Use AI Levels", className="mb-0"), width=4),
            dbc.Col(
                dbc.Switch(
                    id="setting-stop-loss-use-ai",
                    value=True,
                    className="mt-1"
                ),
                width=3
            ),
            dbc.Col(
                html.Small("Use trader AI recommendations", className="text-muted"),
                width=5
            )
        ], className="mb-2 align-items-center"),

        html.Hr(className="my-3"),

        # Take-Profit Settings
        html.Div([
            html.Small("Take-Profit Settings", className="text-muted fw-semibold d-block mb-2"),
        ]),

        # Enable Take-Profit Toggle
        dbc.Row([
            dbc.Col(dbc.Label("Enable Take-Profit", className="mb-0"), width=4),
            dbc.Col(
                dbc.Switch(
                    id="setting-enable-take-profit",
                    value=False,
                    className="mt-1"
                ),
                width=3
            ),
            dbc.Col(
                html.Small("Auto-place take-profit orders", className="text-muted"),
                width=5
            )
        ], className="mb-2 align-items-center"),

        # Take-Profit Percentage
        dbc.Row([
            dbc.Col(dbc.Label("Default TP %", className="mb-0"), width=4),
            dbc.Col(
                dbc.Input(
                    id="setting-take-profit-percentage",
                    type="number",
                    min=0.5,
                    max=100.0,
                    step=0.5,
                    value=10.0,
                    size="sm"
                ),
                width=3
            ),
            dbc.Col(
                html.Small("% above entry (fallback)", className="text-muted"),
                width=5
            )
        ], className="mb-2 align-items-center"),

        # Use AI TP Toggle
        dbc.Row([
            dbc.Col(dbc.Label("Use AI Levels", className="mb-0"), width=4),
            dbc.Col(
                dbc.Switch(
                    id="setting-take-profit-use-ai",
                    value=True,
                    className="mt-1"
                ),
                width=3
            ),
            dbc.Col(
                html.Small("Use trader AI recommendations", className="text-muted"),
                width=5
            )
        ], className="mb-2 align-items-center"),

        # Info note about bracket orders
        dbc.Alert(
            [
                html.I(className="fas fa-info-circle me-2"),
                "Bracket orders create atomic entry + SL + TP. Crypto uses separate orders (no bracket support)."
            ],
            color="info",
            className="mt-3 mb-0 py-2",
        ),
    ])


def create_dashboard_panels_section():
    """Create the Dashboard Panels visibility section."""
    panels = [
        ("show-panel-account-bar", "Account Summary Bar", "Top-level account overview"),
        ("show-panel-scanner", "Market Scanner", "Scan for trading opportunities"),
        ("show-panel-watchlist", "Watchlist & Portfolio", "Symbol tracking and run queue"),
        ("show-panel-chart", "Price Chart & Progress", "Chart and agent progress"),
        ("show-panel-trading", "Trading Controls", "Analysis configuration panel"),
        ("show-panel-positions", "Stock Positions & Orders", "Current stock holdings"),
        ("show-panel-options", "Options Positions", "Current options positions"),
        ("show-panel-reports", "Agent Reports", "Analyst report cards"),
        ("show-panel-logs", "Application Logs", "Real-time log streaming"),
    ]

    rows = []
    for setting_id, label, description in panels:
        rows.append(
            dbc.Row([
                dbc.Col(dbc.Label(label, className="mb-0"), width=4),
                dbc.Col(
                    dbc.Switch(
                        id=f"setting-{setting_id}",
                        value=True,
                        className="mt-1"
                    ),
                    width=3
                ),
                dbc.Col(
                    html.Small(description, className="text-muted"),
                    width=5
                )
            ], className="mb-2 align-items-center")
        )

    rows.append(
        dbc.Alert(
            [
                html.I(className="fas fa-info-circle me-2"),
                "Hidden panels are fully removed from the page. "
                "Save settings and switch to Trading tab to apply."
            ],
            color="info",
            className="mt-3 mb-0 py-2",
        )
    )

    return html.Div(rows)


def create_options_trading_section():
    """Create the Options Trading section."""
    return html.Div([
        # Enable Options Trading Toggle
        dbc.Row([
            dbc.Col(dbc.Label("Enable Options Trading", className="mb-0"), width=4),
            dbc.Col(
                dbc.Switch(
                    id="setting-enable-options-trading",
                    value=False,
                    className="mt-1"
                ),
                width=3
            ),
            dbc.Col(
                html.Small("Trade options contracts", className="text-muted"),
                width=5
            )
        ], className="mb-2 align-items-center"),

        # Options Trading Level
        dbc.Row([
            dbc.Col(dbc.Label("Trading Level", className="mb-0"), width=4),
            dbc.Col(
                dbc.Select(
                    id="setting-options-trading-level",
                    options=[
                        {"label": "Level 1 - Covered Calls/Puts", "value": 1},
                        {"label": "Level 2 - Buy Calls/Puts", "value": 2},
                        {"label": "Level 3 - Spreads", "value": 3},
                    ],
                    value=2,
                    size="sm"
                ),
                width=4
            ),
            dbc.Col(
                html.Small("Alpaca options tier", className="text-muted"),
                width=4
            )
        ], className="mb-2 align-items-center"),

        # Max Contracts
        dbc.Row([
            dbc.Col(dbc.Label("Max Contracts", className="mb-0"), width=4),
            dbc.Col(
                dbc.Input(
                    id="setting-options-max-contracts",
                    type="number",
                    min=1,
                    max=100,
                    value=10,
                    size="sm"
                ),
                width=3
            ),
            dbc.Col(
                html.Small("Per trade limit (1-100)", className="text-muted"),
                width=5
            )
        ], className="mb-2 align-items-center"),

        # Max Position Value
        dbc.Row([
            dbc.Col(dbc.Label("Max Position Value ($)", className="mb-0"), width=4),
            dbc.Col(
                dbc.Input(
                    id="setting-options-max-position-value",
                    type="number",
                    min=100,
                    max=100000,
                    value=5000,
                    size="sm"
                ),
                width=3
            ),
            dbc.Col(
                html.Small("Max $ in options", className="text-muted"),
                width=5
            )
        ], className="mb-2 align-items-center"),

        html.Hr(className="my-2"),

        # DTE Range
        html.Div([
            html.Small("Days to Expiration (DTE) Range", className="text-muted d-block mb-2"),
        ]),
        dbc.Row([
            dbc.Col(dbc.Label("Min DTE", className="mb-0"), width=2),
            dbc.Col(
                dbc.Input(
                    id="setting-options-min-dte",
                    type="number",
                    min=0,
                    max=365,
                    value=7,
                    size="sm"
                ),
                width=2
            ),
            dbc.Col(dbc.Label("Max DTE", className="mb-0 text-end"), width=2),
            dbc.Col(
                dbc.Input(
                    id="setting-options-max-dte",
                    type="number",
                    min=1,
                    max=365,
                    value=45,
                    size="sm"
                ),
                width=2
            ),
            dbc.Col(
                html.Small("7-45 days typical", className="text-muted"),
                width=4
            )
        ], className="mb-2 align-items-center"),

        # Delta Range
        html.Div([
            html.Small("Delta Range (strike selection)", className="text-muted d-block mb-2"),
        ]),
        dbc.Row([
            dbc.Col(dbc.Label("Min Delta", className="mb-0"), width=2),
            dbc.Col(
                dbc.Input(
                    id="setting-options-min-delta",
                    type="number",
                    min=0.05,
                    max=0.95,
                    step=0.05,
                    value=0.20,
                    size="sm"
                ),
                width=2
            ),
            dbc.Col(dbc.Label("Max Delta", className="mb-0 text-end"), width=2),
            dbc.Col(
                dbc.Input(
                    id="setting-options-max-delta",
                    type="number",
                    min=0.05,
                    max=0.95,
                    step=0.05,
                    value=0.70,
                    size="sm"
                ),
                width=2
            ),
            dbc.Col(
                html.Small("0.20-0.70 typical", className="text-muted"),
                width=4
            )
        ], className="mb-2 align-items-center"),

        # Min Open Interest
        dbc.Row([
            dbc.Col(dbc.Label("Min Open Interest", className="mb-0"), width=4),
            dbc.Col(
                dbc.Input(
                    id="setting-options-min-open-interest",
                    type="number",
                    min=10,
                    max=10000,
                    value=100,
                    size="sm"
                ),
                width=3
            ),
            dbc.Col(
                html.Small("Liquidity filter", className="text-muted"),
                width=5
            )
        ], className="mb-2 align-items-center"),
    ])


def create_settings_actions():
    """Create the action buttons for the settings page."""
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Button(
                        [html.I(className="fas fa-save me-2"), "Save Settings"],
                        id="settings-save-btn",
                        color="primary",
                        className="me-2"
                    ),
                    dbc.Button(
                        [html.I(className="fas fa-undo me-2"), "Reset to Defaults"],
                        id="settings-reset-btn",
                        color="secondary",
                        outline=True,
                        className="me-2"
                    ),
                ], width="auto"),
                dbc.Col([
                    dbc.Button(
                        [html.I(className="fas fa-file-export me-2"), "Export"],
                        id="settings-export-btn",
                        color="info",
                        outline=True,
                        size="sm",
                        className="me-2"
                    ),
                    dcc.Download(id="settings-export-download"),
                    dcc.Upload(
                        id="settings-import-upload",
                        children=dbc.Button(
                            [html.I(className="fas fa-file-import me-2"), "Import"],
                            id="settings-import-btn",
                            color="info",
                            outline=True,
                            size="sm"
                        ),
                        accept=".json"
                    ),
                ], width="auto", className="ms-auto"),
            ], className="align-items-center"),
        ], className="py-2")
    ], className="mt-3")


def create_system_settings_page():
    """Create the full system settings page."""
    return dbc.Container([
        # Note: system-settings-store and settings-sync-dummy are in the main layout (layout.py)
        # This ensures settings are synced to app_state on any page load, not just Settings page

        # Page header
        html.H3([
            html.I(className="fas fa-cog me-2"),
            "System Settings"
        ], className="mb-4"),

        # Description
        html.P(
            "Configure global settings for API keys, LLM models, and analysis parameters. "
            "Settings are saved to your browser's local storage and persist across sessions.",
            className="text-muted mb-4"
        ),

        # Alert for unsaved changes
        dbc.Alert(
            id="settings-unsaved-alert",
            children=[
                html.I(className="fas fa-exclamation-triangle me-2"),
                "You have unsaved changes."
            ],
            color="warning",
            is_open=False,
            dismissable=True,
            className="mb-3"
        ),

        # Success/Error toast
        dbc.Toast(
            id="settings-toast",
            header="Settings",
            icon="success",
            is_open=False,
            dismissable=True,
            duration=4000,
            style={"position": "fixed", "top": 66, "right": 10, "width": 350, "zIndex": 1050},
        ),

        # Settings sections
        dbc.Row([
            dbc.Col([
                # Dashboard Panels Section
                create_settings_card(
                    "Dashboard Panels",
                    create_dashboard_panels_section(),
                    icon="fas fa-th-large"
                ),

                # API Keys Section
                create_settings_card(
                    "API Keys & Credentials",
                    create_api_keys_section(),
                    icon="fas fa-key"
                ),

                # LLM Models Section
                create_settings_card(
                    "LLM Models",
                    create_llm_section(),
                    icon="fas fa-brain"
                ),
            ], lg=6),

            dbc.Col([
                # Analysis Defaults Section
                create_settings_card(
                    "Analysis Defaults",
                    create_analysis_section(),
                    icon="fas fa-sliders-h"
                ),

                # Scanner Settings Section
                create_settings_card(
                    "Market Scanner",
                    create_scanner_section(),
                    icon="fas fa-search-dollar"
                ),

                # Options Trading Section
                create_settings_card(
                    "Options Trading",
                    create_options_trading_section(),
                    icon="fas fa-chart-line"
                ),

                # Risk Management Section
                create_settings_card(
                    "Risk Management (SL/TP)",
                    create_risk_management_section(),
                    icon="fas fa-shield-alt"
                ),
            ], lg=6),
        ]),

        # Action Buttons
        create_settings_actions(),

    ], fluid=True, className="py-4")
