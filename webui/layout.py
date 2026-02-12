"""
Layout module for TradingAgents WebUI
Pro Trader optimized layout with chart-first design
"""

from dash import dcc, html
import dash_bootstrap_components as dbc

from webui.components.header import create_header
from webui.components.config_panel import create_trading_control_panel
from webui.components.status_panel import create_status_panel
from webui.components.chart_panel import create_chart_panel
from webui.components.decision_panel import create_compact_decision_panel
from webui.components.reports_panel import create_reports_panel
from webui.components.alpaca_account import render_compact_account_bar, render_positions_orders_section, render_options_section
from webui.components.scanner_panel import create_scanner_panel
from webui.components.ticker_progress_panel import create_ticker_progress_panel
from webui.components.watchlist_panel import create_watchlist_section
from webui.components.log_panel import create_log_panel
from webui.components.system_settings import create_system_settings_page
from webui.config.constants import COLORS, REFRESH_INTERVALS


def create_intervals():
    """Create interval components for auto-refresh"""
    return [
        dcc.Interval(
            id='refresh-interval',
            interval=REFRESH_INTERVALS["fast"],
            n_intervals=0,
            disabled=True
        ),
        dcc.Interval(
            id='medium-refresh-interval',
            interval=REFRESH_INTERVALS["medium"],
            n_intervals=0,
            disabled=False
        ),
        dcc.Interval(
            id='slow-refresh-interval',
            interval=REFRESH_INTERVALS["slow"],
            n_intervals=0,
            disabled=False
        ),
        dcc.Interval(
            id='clock-interval',
            interval=1000,  # 1 second for market time clock
            n_intervals=0,
            disabled=False
        )
    ]


def create_stores():
    """Create store components for state management"""
    from webui.utils.storage import create_storage_store_component
    return [
        dcc.Store(id='app-store'),
        dcc.Store(id='chart-store', data={'last_symbol': None, 'selected_period': '1d'}),
        create_storage_store_component()
    ]


def create_footer():
    """Create the footer section"""
    return html.Div(
        html.Small("TradingAgents Framework - Pro Trader Edition", className="text-muted"),
        className="text-center py-2"
    )


def create_collapsible_section(section_id, title, icon, content, default_open=True, compact=False):
    """Create a collapsible section with header toggle."""
    header_class = "card-header py-2" if compact else "card-header"
    return dbc.Card([
        html.Div(
            dbc.Row([
                dbc.Col([
                    html.I(
                        id=f"{section_id}-chevron",
                        className=f"bi bi-chevron-{'down' if default_open else 'right'} me-2"
                    ),
                    html.Span(icon, className="me-2"),
                    html.Span(title, className="fw-semibold" if not compact else "fw-semibold small"),
                ], width="auto"),
            ], className="align-items-center"),
            id=f"{section_id}-header",
            n_clicks=0,
            className=header_class,
            style={"cursor": "pointer", "padding": "10px 16px" if compact else "12px 16px"}
        ),
        dbc.Collapse(
            content,
            id=f"{section_id}-collapse",
            is_open=default_open
        ),
    ], className="mb-2" if compact else "mb-3")


def create_trading_content():
    """Create the trading tab content."""
    # ═══════════════════════════════════════════════════════════════════════
    # ROW 1: Compact Account Summary Bar
    # ═══════════════════════════════════════════════════════════════════════
    account_bar = html.Div([
        render_compact_account_bar()
    ], className="account-bar-container mb-3", id="account-bar-wrapper")

    # ═══════════════════════════════════════════════════════════════════════
    # ROW 2: Main Trading Area (Chart Left, Controls Right)
    # ═══════════════════════════════════════════════════════════════════════

    # Left side: Chart (60% width on large screens)
    chart_content = create_chart_panel()
    chart_section = html.Div([
        dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.H5([
                        html.I(className="fas fa-chart-candlestick me-2"),
                        "Price Chart"
                    ], className="mb-0 d-inline"),
                ], className="d-flex align-items-center justify-content-between mb-2"),
                # Chart content (remove outer card wrapper)
                chart_content.children if hasattr(chart_content, 'children') else chart_content
            ], className="p-2")
        ], className="chart-card"),

        # Agent Progress (below chart)
        dbc.Card([
            dbc.CardBody([
                html.H6([
                    html.I(className="fas fa-tasks me-2"),
                    "Agent Progress"
                ], className="mb-2 text-muted"),
                html.Div(
                    create_ticker_progress_panel(),
                    className="agent-progress-compact"
                )
            ], className="p-2")
        ], className="mt-2")
    ], className="chart-section")

    # Right side: Trading Control Panel (40% width on large screens)
    trading_panel = html.Div([
        dbc.Card([
            dbc.CardBody([
                html.H5([
                    html.I(className="fas fa-sliders-h me-2"),
                    "Trading Control"
                ], className="mb-3"),

                # Compact trading controls
                create_trading_control_panel(),

                html.Hr(className="my-3"),

                # Decision/Signal display
                html.Div([
                    html.H6([
                        html.I(className="fas fa-bullseye me-2"),
                        "Trading Signal"
                    ], className="mb-2 text-muted"),
                    create_compact_decision_panel(),
                ]),
            ], className="p-3")
        ], className="trading-panel-card h-100")
    ], className="trading-panel-section")

    main_trading_row = dbc.Row([
        dbc.Col(chart_section, lg=7, xl=8, className="mb-3 mb-lg-0"),
        dbc.Col(trading_panel, lg=5, xl=4),
    ], className="mb-3 main-trading-row")

    # ═══════════════════════════════════════════════════════════════════════
    # ROW 3: Positions & Orders (Side by Side, Collapsible)
    # ═══════════════════════════════════════════════════════════════════════
    positions_orders_section = create_collapsible_section(
        "positions-orders-panel",
        "Stock Positions & Orders",
        "💼",
        dbc.CardBody(render_positions_orders_section(), className="p-2"),
        default_open=True,
        compact=True
    )

    # ═══════════════════════════════════════════════════════════════════════
    # ROW 3b: Options Positions & Orders (Collapsible)
    # ═══════════════════════════════════════════════════════════════════════
    options_section = create_collapsible_section(
        "options-panel",
        "Options Positions & Orders",
        "📜",
        dbc.CardBody(render_options_section(), className="p-2"),
        default_open=False,
        compact=True
    )

    # ═══════════════════════════════════════════════════════════════════════
    # ROW 4: Watchlist (Collapsible)
    # ═══════════════════════════════════════════════════════════════════════
    watchlist_section = create_watchlist_section()

    # ═══════════════════════════════════════════════════════════════════════
    # ROW 5: Agent Reports (Collapsible)
    # ═══════════════════════════════════════════════════════════════════════
    reports_content = create_reports_panel()
    reports_section = create_collapsible_section(
        "reports-panel",
        "Agent Reports & Analysis",
        "📋",
        reports_content,  # Already returns CardBody with proper content
        default_open=False
    )

    # ═══════════════════════════════════════════════════════════════════════
    # ROW 5: Market Scanner (Collapsible, Less Prominent)
    # ═══════════════════════════════════════════════════════════════════════
    scanner_section = create_collapsible_section(
        "scanner-panel",
        "Market Scanner",
        "🔍",
        dbc.CardBody([
            # Persistent storage for scanner results (survives page refresh)
            dcc.Store(id="scanner-results-store", storage_type="local"),

            dbc.Row([
                dbc.Col([
                    html.Small("Find trading opportunities", className="text-muted"),
                ], md=6),
                dbc.Col([
                    # Timestamp display
                    html.Div(id="scanner-timestamp-display", className="text-muted small text-end"),
                ], md=3),
                dbc.Col([
                    dbc.Button(
                        [html.I(className="bi bi-search me-2"), "Scan"],
                        id="scanner-btn",
                        color="primary",
                        size="sm",
                        className="w-100"
                    ),
                ], md=3),
            ], className="mb-2 align-items-center"),
            html.Div(
                id="scanner-progress-container",
                children=[
                    dbc.Progress(id="scanner-progress-bar", value=0, striped=True, animated=True, className="mb-2"),
                    html.Div(id="scanner-progress-text", className="text-center text-muted small"),
                ],
                style={"display": "none"}
            ),
            dbc.Alert(id="scanner-error-alert", color="danger", is_open=False, dismissable=True),
            html.Div(id="scanner-results-container", children=[
                html.Div("Click 'Scan' to find opportunities.", className="text-center text-muted py-2 small")
            ]),
        ], className="p-2"),
        default_open=True,
        compact=True
    )

    # ═══════════════════════════════════════════════════════════════════════
    # Hidden Components for Backward Compatibility
    # ═══════════════════════════════════════════════════════════════════════
    hidden_components = html.Div([
        # Hidden status panel elements
        html.Div(id="status-table", style={"display": "none"}),
        html.Div(id="tool-calls-text", children="🧰 Tool Calls: 0", style={"display": "none"}),
        html.Div(id="llm-calls-text", children="🤖 LLM Calls: 0", style={"display": "none"}),
        html.Div(id="reports-text", children="📊 Generated Reports: 0", style={"display": "none"}),
        html.Div(id="refresh-status", children="⏸️ Updates paused", style={"display": "none"}),
    ], style={"display": "none"})

    return html.Div([
        # Account Summary Bar
        account_bar,

        # Market Scanner & Watchlist (top for quick access)
        scanner_section,
        watchlist_section,

        # Main Trading Area (Chart + Controls)
        main_trading_row,

        # Positions & Orders (Stocks)
        positions_orders_section,

        # Options Positions & Orders
        options_section,

        # Agent Reports
        reports_section,

        # Application Logs (Live Streaming)
        create_log_panel(),

        # Hidden components
        hidden_components,
    ])


def create_main_layout():
    """Create the main application layout - Pro Trader optimized with tabs"""

    # Compact header
    header = create_header()

    # ═══════════════════════════════════════════════════════════════════════
    # ASSEMBLE LAYOUT WITH TABS
    # ═══════════════════════════════════════════════════════════════════════
    layout = dbc.Container([
        *create_intervals(),
        *create_stores(),

        html.Script("""
            window.addEventListener('message', function(event) {
                if (event.data && event.data.type === 'showPrompt') {
                    const buttons = document.querySelectorAll('[id*="show-prompt-"]');
                    for (let button of buttons) {
                        if (button.id.includes(event.data.reportType)) {
                            button.click();
                            break;
                        }
                    }
                }
            });
        """),

        # Header
        header,

        # Toast Notification for Analysis Completion
        html.Div(
            dbc.Toast(
                id="analysis-toast",
                header="Analysis Complete",
                icon="success",
                is_open=False,
                dismissable=True,
                duration=5000,
                style={"position": "fixed", "top": 66, "right": 10, "width": 350, "zIndex": 1050},
            ),
            id="toast-container"
        ),

        # Tab Navigation
        dbc.Tabs([
            dbc.Tab(
                label="Trading",
                tab_id="tab-trading",
                children=create_trading_content(),
                className="pt-3"
            ),
            dbc.Tab(
                label="Settings",
                tab_id="tab-settings",
                children=create_system_settings_page(),
                className="pt-3"
            ),
        ], id="main-tabs", active_tab="tab-trading", className="mb-3"),

        # Footer
        create_footer(),

    ], fluid=True, className="p-3 pro-trader-layout", style={"backgroundColor": COLORS["background"]})

    return layout
