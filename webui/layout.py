"""
Layout module for TradingAgents WebUI
Organizes the main application layout and component assembly
"""

from dash import dcc, html
import dash_bootstrap_components as dbc

from webui.components.header import create_header
from webui.components.config_panel import create_config_panel
from webui.components.status_panel import create_status_panel
from webui.components.chart_panel import create_chart_panel
from webui.components.decision_panel import create_decision_panel
from webui.components.reports_panel import create_reports_panel
from webui.components.alpaca_account import render_alpaca_account_section
from webui.components.scanner_panel import create_scanner_panel
from webui.components.ticker_progress_panel import create_ticker_progress_panel
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
            disabled=True
        ),
        dcc.Interval(
            id='slow-refresh-interval',
            interval=REFRESH_INTERVALS["slow"],
            n_intervals=0,
            disabled=False
        )
    ]


def create_stores():
    """Create store components for state management"""
    from webui.utils.storage import create_storage_store_component
    return [
        dcc.Store(id='app-store'),
        dcc.Store(id='chart-store', data={'last_symbol': None, 'selected_period': '1y'}),
        create_storage_store_component()
    ]


def create_footer():
    """Create the footer section"""
    return html.Div(
        html.Small("TradingAgents Framework - Status updates automatically", className="text-muted"),
        className="text-center py-3"
    )


def create_collapsible_section(section_id, title, icon, content, default_open=True):
    """Create a collapsible section with header toggle."""
    return dbc.Card([
        html.Div(
            dbc.Row([
                dbc.Col([
                    html.I(
                        id=f"{section_id}-chevron",
                        className=f"bi bi-chevron-{'down' if default_open else 'right'} me-2"
                    ),
                    html.Span(icon, className="me-2"),
                    html.Span(title, className="fw-semibold"),
                ], width="auto"),
            ], className="align-items-center"),
            id=f"{section_id}-header",
            n_clicks=0,
            className="card-header",
            style={"cursor": "pointer", "padding": "12px 16px"}
        ),
        dbc.Collapse(
            content,
            id=f"{section_id}-collapse",
            is_open=default_open
        ),
    ], className="mb-3")


def create_main_layout():
    """Create the main application layout"""

    header = create_header()

    # Alpaca Account Section (collapsible)
    alpaca_section = create_collapsible_section(
        "alpaca-panel",
        "Account & Positions",
        "💰",
        dbc.CardBody(render_alpaca_account_section(), className="p-3")
    )

    # Scanner Section (collapsible)
    scanner_section = create_collapsible_section(
        "scanner-panel",
        "Market Scanner",
        "🔍",
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Small("Find trading opportunities in real-time", className="text-muted"),
                ], md=8),
                dbc.Col([
                    dbc.Button(
                        [html.I(className="bi bi-search me-2"), "Scan Market"],
                        id="scanner-btn",
                        color="primary",
                        size="sm",
                        className="w-100"
                    ),
                ], md=4),
            ], className="mb-3 align-items-center"),
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
                html.Div("Click 'Scan Market' to find opportunities.", className="text-center text-muted py-3")
            ]),
        ], className="p-3")
    )

    # Config Section (collapsible)
    config_content = create_config_panel()
    config_section = create_collapsible_section(
        "config-panel",
        "Analysis Configuration",
        "⚙️",
        config_content.children if hasattr(config_content, 'children') else config_content
    )

    # Chart Section (collapsible)
    chart_content = create_chart_panel()
    chart_section = create_collapsible_section(
        "chart-panel",
        "Price Chart",
        "📈",
        chart_content.children if hasattr(chart_content, 'children') else chart_content
    )

    # Status Section (collapsible)
    status_content = create_status_panel()
    status_section = create_collapsible_section(
        "status-panel",
        "Analysis Status",
        "📊",
        status_content.children if hasattr(status_content, 'children') else status_content
    )

    # Decision Section (collapsible)
    decision_content = create_decision_panel()
    decision_section = create_collapsible_section(
        "decision-panel",
        "Decision Summary",
        "🎯",
        decision_content.children if hasattr(decision_content, 'children') else decision_content
    )

    # Reports Section (collapsible)
    reports_content = create_reports_panel()
    reports_section = create_collapsible_section(
        "reports-panel",
        "Agent Reports",
        "📋",
        reports_content.children if hasattr(reports_content, 'children') else reports_content
    )

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

        header,

        # Row 1: Account (full width)
        alpaca_section,

        # Row 2: Scanner (full width)
        scanner_section,

        # Row 3: Agent Progress (full width)
        create_collapsible_section(
            "progress-panel",
            "Agent Progress",
            "📊",
            dbc.CardBody(create_ticker_progress_panel(), className="p-3")
        ),

        # Row 4: Config + Chart/Status/Decision
        dbc.Row([
            dbc.Col([config_section], lg=5, className="mb-3"),
            dbc.Col([
                chart_section,
                status_section,
                decision_section,
            ], lg=7),
        ]),

        # Row 4: Reports (full width)
        reports_section,

        create_footer(),
    ], fluid=True, className="p-3", style={"backgroundColor": COLORS["background"]})

    return layout
