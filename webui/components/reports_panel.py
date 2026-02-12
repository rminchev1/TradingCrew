"""
webui/components/reports_panel.py - Enhanced reports panel with organized navigation
"""

import dash_bootstrap_components as dbc
from dash import dcc, html
from webui.components.prompt_modal import create_prompt_modal
from webui.components.tool_outputs_modal import create_tool_outputs_modal


def create_nav_item(tab_id, icon, label, is_active=False):
    """Create a navigation pill item"""
    return dbc.NavItem(
        dbc.NavLink(
            [html.Span(icon, className="me-1"), label],
            id=f"nav-{tab_id}",
            href=f"#{tab_id}",
            active=is_active,
            className="report-nav-link"
        )
    )


def create_reports_panel():
    """Create the reports panel for the web UI with organized grouped navigation"""

    # Navigation structure - grouped by workflow stage
    nav_section = html.Div([
        # Row 0: History selector
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.I(className="fas fa-history me-2 text-muted"),
                    dbc.Select(
                        id="history-selector",
                        options=[{"label": "Current Session", "value": "current"}],
                        value="current",
                        size="sm",
                        className="history-select"
                    ),
                ], className="d-flex align-items-center")
            ], lg=6, md=8),
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button(
                        [html.I(className="fas fa-save me-1"), "Save"],
                        id="save-history-btn",
                        color="outline-primary",
                        size="sm",
                        title="Save current analysis to history"
                    ),
                    dbc.Button(
                        [html.I(className="fas fa-sync-alt")],
                        id="refresh-history-btn",
                        color="outline-secondary",
                        size="sm",
                        title="Refresh history list"
                    ),
                ], size="sm")
            ], lg=6, md=4, className="d-flex justify-content-end")
        ], className="mb-2 history-row"),

        # Row 1: Symbol selector (left) + Current symbol (right)
        dbc.Row([
            dbc.Col([
                dbc.Select(
                    id="report-symbol-select",
                    options=[],
                    placeholder="Select symbol...",
                    size="sm",
                    className="symbol-select"
                )
            ], width="auto", style={"minWidth": "160px"}, className="d-flex align-items-center"),
            dbc.Col([
                html.Div([
                    html.Span(id="current-symbol-report-display", className="current-symbol-badge")
                ], className="text-end")
            ], className="d-flex align-items-center justify-content-end")
        ], className="mb-3 symbol-nav-row g-2"),

        # Row 2: Navigation pills grouped by category
        # Labels include a span for dynamic data indicator (✓ when report has content)
        html.Div([
            # Analysts Group
            html.Div([
                html.Span("Analysts", className="nav-group-label"),
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink([html.Span(id="nav-label-market", children="📊 Market")], id="nav-tab-market", className="report-nav-pill")),
                    dbc.NavItem(dbc.NavLink([html.Span(id="nav-label-options", children="📉 Options")], id="nav-tab-options", className="report-nav-pill")),
                    dbc.NavItem(dbc.NavLink([html.Span(id="nav-label-social", children="📱 Social")], id="nav-tab-social", className="report-nav-pill")),
                    dbc.NavItem(dbc.NavLink([html.Span(id="nav-label-news", children="📰 News")], id="nav-tab-news", className="report-nav-pill")),
                    dbc.NavItem(dbc.NavLink([html.Span(id="nav-label-fundamentals", children="📈 Fundamentals")], id="nav-tab-fundamentals", className="report-nav-pill")),
                    dbc.NavItem(dbc.NavLink([html.Span(id="nav-label-macro", children="🌍 Macro")], id="nav-tab-macro", className="report-nav-pill")),
                ], pills=True, className="nav-pills-group")
            ], className="nav-group"),

            # Research Group
            html.Div([
                html.Span("Research", className="nav-group-label"),
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink([html.Span(id="nav-label-researcher", children="🔍 Debate")], id="nav-tab-researcher", className="report-nav-pill")),
                    dbc.NavItem(dbc.NavLink([html.Span(id="nav-label-research-mgr", children="🎯 Manager")], id="nav-tab-research-mgr", className="report-nav-pill")),
                    dbc.NavItem(dbc.NavLink([html.Span(id="nav-label-trader", children="🧠 Trader")], id="nav-tab-trader", className="report-nav-pill")),
                ], pills=True, className="nav-pills-group")
            ], className="nav-group"),

            # Decision Group
            html.Div([
                html.Span("Decision", className="nav-group-label"),
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink([html.Span(id="nav-label-risk", children="⚖️ Risk")], id="nav-tab-risk", className="report-nav-pill")),
                    dbc.NavItem(dbc.NavLink([html.Span(id="nav-label-final", children="⚡ Final")], id="nav-tab-final", className="report-nav-pill")),
                ], pills=True, className="nav-pills-group")
            ], className="nav-group"),
        ], className="nav-groups-container")
    ], className="reports-nav-section")

    # Tab content containers - using dbc.Tabs but hidden nav (we use custom nav above)
    tabs = dbc.Tabs(
        [
            dbc.Tab(
                html.Div(id="market-analysis-tab-content", children=[
                    dcc.Markdown("📊 **Loading Market Analysis...**", className='enhanced-markdown-content')
                ]),
                label="Market", tab_id="market-analysis"
            ),
            dbc.Tab(
                html.Div(id="options-analysis-tab-content", children=[
                    dcc.Markdown("📉 **Loading Options Analysis...**", className='enhanced-markdown-content')
                ]),
                label="Options", tab_id="options-analysis"
            ),
            dbc.Tab(
                html.Div(id="social-sentiment-tab-content", children=[
                    dcc.Markdown("📱 **Loading Social Sentiment...**", className='enhanced-markdown-content')
                ]),
                label="Social", tab_id="social-sentiment"
            ),
            dbc.Tab(
                html.Div(id="news-analysis-tab-content", children=[
                    dcc.Markdown("📰 **Loading News Analysis...**", className='enhanced-markdown-content')
                ]),
                label="News", tab_id="news-analysis"
            ),
            dbc.Tab(
                html.Div(id="fundamentals-analysis-tab-content", children=[
                    dcc.Markdown("📈 **Loading Fundamentals...**", className='enhanced-markdown-content')
                ]),
                label="Fundamentals", tab_id="fundamentals-analysis"
            ),
            dbc.Tab(
                html.Div(id="macro-analysis-tab-content", children=[
                    dcc.Markdown("🌍 **Loading Macro Analysis...**", className='enhanced-markdown-content')
                ]),
                label="Macro", tab_id="macro-analysis"
            ),
            dbc.Tab(
                html.Div(id="researcher-debate-tab-content", className="debate-content-wrapper", children=[
                    html.P("🔍 Loading Researcher Debate...", className="loading-message")
                ]),
                label="Debate", tab_id="researcher-debate"
            ),
            dbc.Tab(
                html.Div(id="research-manager-tab-content", children=[
                    dcc.Markdown("🎯 **Loading Research Manager...**", className='enhanced-markdown-content')
                ]),
                label="Manager", tab_id="research-manager"
            ),
            dbc.Tab(
                html.Div(id="trader-plan-tab-content", children=[
                    dcc.Markdown("🧠 **Loading Trader Plan...**", className='enhanced-markdown-content')
                ]),
                label="Trader", tab_id="trader-plan"
            ),
            dbc.Tab(
                html.Div(id="risk-debate-tab-content", className="debate-content-wrapper", children=[
                    html.P("⚖️ Loading Risk Debate...", className="loading-message")
                ]),
                label="Risk", tab_id="risk-debate"
            ),
            dbc.Tab(
                html.Div(id="final-decision-tab-content", children=[
                    dcc.Markdown("⚡ **Loading Final Decision...**", className='enhanced-markdown-content')
                ]),
                label="Final", tab_id="final-decision"
            ),
        ],
        id="tabs",
        active_tab="market-analysis",
        className="reports-tabs-hidden-nav"
    )

    # Hidden content containers for backward compatibility with existing callbacks
    hidden_content_containers = html.Div([
        html.Div(id="market-analysis-tab", style={"display": "none"}),
        html.Div(id="social-sentiment-tab", style={"display": "none"}),
        html.Div(id="news-analysis-tab", style={"display": "none"}),
        html.Div(id="fundamentals-analysis-tab", style={"display": "none"}),
        html.Div(id="macro-analysis-tab", style={"display": "none"}),
        html.Div(id="options-analysis-tab", style={"display": "none"}),
        html.Div(id="researcher-debate-tab", style={"display": "none"}),
        html.Div(id="research-manager-tab", style={"display": "none"}),
        html.Div(id="trader-plan-tab", style={"display": "none"}),
        html.Div(id="risk-debate-tab", style={"display": "none"}),
        html.Div(id="final-decision-tab", style={"display": "none"})
    ])

    return dbc.CardBody([
        # Navigation section (symbols + category pills)
        nav_section,

        # Tab content
        tabs,

        # Hidden containers
        hidden_content_containers,

        # Modals
        create_prompt_modal(),
        create_tool_outputs_modal(),

        # Global state storage for modal persistence
        html.Div([
            dcc.Store(id="global-prompt-modal-state", data={
                "is_open": False,
                "report_type": None,
                "title": "Agent Prompt"
            }),
            dcc.Store(id="global-tool-outputs-modal-state", data={
                "is_open": False,
                "report_type": None,
                "title": "Tool Outputs"
            })
        ], style={"display": "none"}),

        # Hidden original pagination component for control callback compatibility
        html.Div([
            dbc.Pagination(
                id="report-pagination",
                max_value=1,
                active_page=1,  # Explicitly set to 1 to avoid None default
                fully_expanded=True,
                first_last=True,
                previous_next=True,
                className="d-none"
            )
        ], style={"display": "none"})
    ], className="reports-panel-body")
