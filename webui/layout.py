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
# Removed: create_compact_decision_panel (Trading Signal panel removed)
from webui.components.reports_panel import create_reports_panel
from webui.components.alpaca_account import render_compact_account_bar, render_positions_orders_section, render_options_section
from webui.components.scanner_panel import create_scanner_panel
from webui.components.ticker_progress_panel import create_ticker_progress_panel
from webui.components.watchlist_panel import create_watchlist_section
from webui.components.log_panel import create_log_panel
from webui.components.portfolio_panel import create_portfolio_panel
from webui.components.system_settings import create_system_settings_page
from webui.components.chat_drawer import create_chat_drawer
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
        ),
        # Relocated from panels for hide/show support
        dcc.Interval(
            id="watchlist-refresh-interval",
            interval=30000,  # 30 seconds
            n_intervals=0
        ),
        dcc.Interval(
            id="log-update-interval",
            interval=1000,
            n_intervals=0,
            disabled=False
        ),
        # Live chart price updates (disabled by default, toggled by LIVE button)
        dcc.Interval(
            id="chart-live-interval",
            interval=5000,  # 5 seconds
            n_intervals=0,
            disabled=True
        ),
        # Chat assistant polling interval
        dcc.Interval(
            id="chat-poll-interval",
            interval=1000,  # 1 second
            n_intervals=0,
            disabled=True
        ),
    ]


def create_stores():
    """Create store components for state management"""
    from webui.utils.storage import create_storage_store_component
    return [
        dcc.Store(id='app-store'),
        dcc.Store(id='chart-store', data={'last_symbol': None, 'selected_period': '1d'}),
        create_storage_store_component(),
        # System settings store - must be in main layout for startup sync
        dcc.Store(id='system-settings-store', storage_type='local'),
        # Dummy store for startup sync callback (syncs localStorage to app_state)
        dcc.Store(id='settings-sync-dummy'),
        # Relocated from panels for hide/show support
        dcc.Store(id="scanner-results-store", storage_type="local"),
        dcc.Store(id="watchlist-store", storage_type="memory", data={"symbols": []}),
        dcc.Store(id="watchlist-reorder-store", data={"order": [], "timestamp": 0}),
        dcc.Store(id="run-watchlist-store", storage_type="local", data={"symbols": []}),
        dcc.Store(id="log-last-index", data=0),
        # Live chart price data store
        dcc.Store(id="tv-chart-live-store", data=None),
        # Positions panel stores (relocated for hide/show support)
        dcc.Store(id="positions-sort-store", data={"key": "symbol", "direction": "asc"}),
        dcc.Store(id="positions-filter-store", data={"search": ""}),
        dcc.Store(id="positions-pending-close-store", data={}),
        dcc.Download(id="positions-csv-download"),
        # Orders panel stores (relocated for hide/show support)
        dcc.Store(id="orders-sort-store", data={"key": "date", "direction": "desc"}),
        dcc.Store(id="orders-filter-store", data={"search": ""}),
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


def _build_account_bar():
    """Build the account summary bar panel."""
    return html.Div([
        render_compact_account_bar()
    ], className="account-bar-container mb-3", id="account-bar-wrapper")


def _build_portfolio_section():
    """Build the portfolio overview panel."""
    return create_portfolio_panel()


def _build_chart_section():
    """Build the chart + agent progress section."""
    chart_content = create_chart_panel()
    return html.Div([
        dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.H5([
                        html.I(className="fas fa-chart-candlestick me-2"),
                        "Price Chart"
                    ], className="mb-0 d-inline"),
                ], className="d-flex align-items-center justify-content-between mb-2"),
                chart_content.children if hasattr(chart_content, 'children') else chart_content
            ], className="p-2")
        ], className="chart-card"),
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


def _build_trading_panel():
    """Build the trading control panel."""
    return html.Div([
        dbc.Card([
            dbc.CardBody([
                html.H5([
                    html.I(className="fas fa-sliders-h me-2"),
                    "Trading Control"
                ], className="mb-3"),
                create_trading_control_panel(),
            ], className="p-3")
        ], className="trading-panel-card h-100")
    ], className="trading-panel-section")


def _build_main_trading_row(show_chart=True, show_trading=True):
    """Build the main trading row with dynamic column widths."""
    if show_chart and show_trading:
        cols = [
            dbc.Col(_build_chart_section(), lg=7, xl=8, className="mb-3 mb-lg-0"),
            dbc.Col(_build_trading_panel(), lg=5, xl=4),
        ]
    elif show_chart:
        cols = [dbc.Col(_build_chart_section(), lg=12)]
    elif show_trading:
        cols = [dbc.Col(_build_trading_panel(), lg=12)]
    else:
        return []
    return dbc.Row(cols, className="mb-3 main-trading-row")


def _build_positions_section():
    """Build the stock positions & orders panel."""
    return create_collapsible_section(
        "positions-orders-panel",
        "Stock Positions & Orders",
        "\U0001f4bc",
        dbc.CardBody(render_positions_orders_section(), className="p-2"),
        default_open=True,
        compact=True
    )


def _build_options_section():
    """Build the options positions & orders panel."""
    return create_collapsible_section(
        "options-panel",
        "Options Positions & Orders",
        "\U0001f4dc",
        dbc.CardBody(render_options_section(), className="p-2"),
        default_open=False,
        compact=True
    )


def _build_watchlist_section():
    """Build the watchlist panel."""
    return create_watchlist_section()


def _build_reports_section():
    """Build the agent reports panel."""
    reports_content = create_reports_panel()
    return create_collapsible_section(
        "reports-panel",
        "Agent Reports & Analysis",
        "\U0001f4cb",
        reports_content,
        default_open=False
    )


def _build_scanner_section():
    """Build the market scanner panel."""
    return create_collapsible_section(
        "scanner-panel",
        "Market Scanner",
        "\U0001f50d",
        dbc.CardBody([
            # Note: scanner-results-store is in global create_stores()
            dbc.Row([
                dbc.Col([
                    html.Small("Find trading opportunities", className="text-muted"),
                ], md=6),
                dbc.Col([
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


def _build_log_panel():
    """Build the application logs panel."""
    return create_log_panel()


def create_trading_content():
    """Create the trading tab content with wrapper divs for panel visibility."""
    # Hidden Components for Backward Compatibility (always present)
    hidden_components = html.Div([
        html.Div(id="status-table", style={"display": "none"}),
        html.Div(id="tool-calls-text", children="\U0001f9f0 Tool Calls: 0", style={"display": "none"}),
        html.Div(id="llm-calls-text", children="\U0001f916 LLM Calls: 0", style={"display": "none"}),
        html.Div(id="reports-text", children="\U0001f4ca Generated Reports: 0", style={"display": "none"}),
        html.Div(id="refresh-status", children="\u23f8\ufe0f Updates paused", style={"display": "none"}),
    ], style={"display": "none"})

    return html.Div([
        # Panel wrappers - populated by panel_visibility_callbacks
        html.Div(id="panel-wrapper-account-bar"),
        html.Div(id="panel-wrapper-portfolio"),
        html.Div(id="panel-wrapper-scanner"),
        html.Div(id="panel-wrapper-watchlist"),
        html.Div(id="panel-wrapper-main-trading-row"),
        html.Div(id="panel-wrapper-positions"),
        html.Div(id="panel-wrapper-options"),
        html.Div(id="panel-wrapper-reports"),
        html.Div(id="panel-wrapper-logs"),

        # Hidden components (always present)
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

    return html.Div([layout, create_chat_drawer()])
