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
from webui.components.collapsible_card import create_collapsible_card
from webui.config.constants import COLORS, REFRESH_INTERVALS


def create_intervals():
    """Create interval components for auto-refresh"""
    return [
        # Fast refresh for critical updates during analysis
        dcc.Interval(
            id='refresh-interval',
            interval=REFRESH_INTERVALS["fast"],
            n_intervals=0,
            disabled=True  # Start disabled, only enable when analysis is running
        ),

        # Medium refresh for reports and non-critical updates
        dcc.Interval(
            id='medium-refresh-interval',
            interval=REFRESH_INTERVALS["medium"],
            n_intervals=0,
            disabled=True
        ),

        # Slow refresh for account data
        dcc.Interval(
            id='slow-refresh-interval',
            interval=REFRESH_INTERVALS["slow"],
            n_intervals=0,
            disabled=False  # Always enabled for account data
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
    return dbc.Row(
        [
            dbc.Col(
                dbc.Button("Refresh Status", id="refresh-btn", color="secondary", className="mb-2"),
                width="auto",
                className="d-flex justify-content-center"
            ),
            dbc.Col(
                html.Div("Status updates automatically", className="text-muted small"),
                width="auto",
                className="d-flex align-items-center"
            ),
        ],
        className="d-flex justify-content-center py-3"
    )


def create_main_layout():
    """Create the main application layout"""

    # Create UI components
    header = create_header()

    # Wrap panels in collapsible cards
    alpaca_panel = create_collapsible_card(
        card_id="alpaca-panel",
        title="Account & Positions",
        icon="💰",
        children=render_alpaca_account_section(),
        default_open=True,
        extra_class="alpaca-panel"
    )

    scanner_panel = create_collapsible_card(
        card_id="scanner-panel",
        title="Market Scanner",
        icon="🔍",
        children=create_scanner_panel_content(),
        default_open=True,
        badge_id="scanner-badge",
        extra_class="scanner-panel"
    )

    config_panel = create_collapsible_card(
        card_id="config-panel",
        title="Analysis Configuration",
        icon="⚙️",
        children=create_config_panel_content(),
        default_open=True,
        extra_class="config-panel"
    )

    chart_panel = create_collapsible_card(
        card_id="chart-panel",
        title="Price Chart",
        icon="📈",
        children=create_chart_panel_content(),
        default_open=True,
        extra_class="chart-panel"
    )

    status_panel = create_collapsible_card(
        card_id="status-panel",
        title="Analysis Status",
        icon="📊",
        children=create_status_panel_content(),
        default_open=True,
        badge_id="status-badge",
        extra_class="status-panel"
    )

    decision_panel = create_collapsible_card(
        card_id="decision-panel",
        title="Decision Summary",
        icon="🎯",
        children=create_decision_panel_content(),
        default_open=True,
        extra_class="decision-panel"
    )

    reports_panel = create_collapsible_card(
        card_id="reports-panel",
        title="Agent Reports",
        icon="📋",
        children=create_reports_panel(),
        default_open=True,
        extra_class="reports-panel"
    )

    # Assemble the layout
    layout = dbc.Container(
        [
            # Intervals and stores
            *create_intervals(),
            *create_stores(),

            # Client-side script to handle iframe messages for prompt modal
            html.Script("""
                window.addEventListener('message', function(event) {
                    if (event.data && event.data.type === 'showPrompt') {
                        const buttons = document.querySelectorAll('[id*="show-prompt-"]');
                        const reportType = event.data.reportType;

                        let targetButton = null;
                        for (let button of buttons) {
                            const buttonId = button.getAttribute('id');
                            if (buttonId && buttonId.includes(reportType)) {
                                targetButton = button;
                                break;
                            }
                        }

                        if (!targetButton) {
                            for (let button of buttons) {
                                const buttonData = button.getAttribute('data-dash-props');
                                if (buttonData && buttonData.includes(reportType)) {
                                    targetButton = button;
                                    break;
                                }
                            }
                        }

                        if (targetButton) {
                            targetButton.click();
                        }
                    }
                });
            """),

            # Main content
            header,

            # Top row: Account and Scanner (stack on mobile)
            dbc.Row([
                dbc.Col(alpaca_panel, xs=12, lg=6, className="mb-3 mb-lg-0"),
                dbc.Col(scanner_panel, xs=12, lg=6),
            ], className="mb-3"),

            # Middle row: Config and Chart/Status/Decision
            dbc.Row([
                dbc.Col(config_panel, xs=12, lg=5, className="mb-3 mb-lg-0"),
                dbc.Col([
                    chart_panel,
                    status_panel,
                    decision_panel,
                ], xs=12, lg=7)
            ], className="mb-3"),

            # Bottom: Reports (full width)
            reports_panel,

            html.Div(className="mt-2"),
            create_footer(),
        ],
        fluid=True,
        className="p-3",
        style={"backgroundColor": COLORS["background"]}
    )

    return layout


# Helper functions to extract panel content (without the outer Card wrapper)

def create_scanner_panel_content():
    """Create scanner panel content without outer card."""
    return html.Div([
        dbc.Row([
            dbc.Col([
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
                "Click 'Scan Market' to find trading opportunities.",
                className="text-center text-muted py-3"
            )
        ]),
    ])


def create_config_panel_content():
    """Create config panel content without outer card."""
    from webui.components.config_panel import create_config_panel
    # Get the inner content from config panel
    config_card = create_config_panel()
    # Extract CardBody children
    return config_card.children.children if hasattr(config_card.children, 'children') else config_card.children


def create_chart_panel_content():
    """Create chart panel content without outer card."""
    from webui.components.chart_panel import create_chart_panel
    chart_card = create_chart_panel()
    return chart_card.children.children if hasattr(chart_card.children, 'children') else chart_card.children


def create_status_panel_content():
    """Create status panel content without outer card."""
    from webui.components.status_panel import create_status_panel
    status_card = create_status_panel()
    return status_card.children.children if hasattr(status_card.children, 'children') else status_card.children


def create_decision_panel_content():
    """Create decision panel content without outer card."""
    from webui.components.decision_panel import create_decision_panel
    decision_card = create_decision_panel()
    return decision_card.children.children if hasattr(decision_card.children, 'children') else decision_card.children
