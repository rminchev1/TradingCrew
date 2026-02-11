"""
Ticker Progress Panel - Shows agent progress for all tickers being analyzed
"""

import dash_bootstrap_components as dbc
from dash import html
from datetime import datetime
from zoneinfo import ZoneInfo


# Agent abbreviations mapping - ordered by execution phase
ANALYST_AGENTS = {
    "MA": "Market Analyst",
    "OP": "Options Analyst",
    "SA": "Social Analyst",
    "NA": "News Analyst",
    "FA": "Fundamentals Analyst",
    "MC": "Macro Analyst",
}

RESEARCH_AGENTS = {
    "BR": "Bull Researcher",
    "BB": "Bear Researcher",
    "RM": "Research Manager",
}

TRADING_AGENTS = {
    "TR": "Trader",
}

RISK_AGENTS = {
    "RI": "Risky Analyst",
    "SF": "Safe Analyst",
    "NE": "Neutral Analyst",
    "PM": "Portfolio Manager",
}

# Combined mapping
AGENT_ABBREVIATIONS = {**ANALYST_AGENTS, **RESEARCH_AGENTS, **TRADING_AGENTS, **RISK_AGENTS}

# Reverse mapping for lookup
AGENT_TO_ABBREV = {v: k for k, v in AGENT_ABBREVIATIONS.items()}


def format_timestamp_est(unix_timestamp):
    """Format a Unix timestamp to EST/EDT time string."""
    if not unix_timestamp:
        return None
    try:
        # Convert Unix timestamp to datetime in EST/EDT
        est_tz = ZoneInfo("America/New_York")
        dt = datetime.fromtimestamp(unix_timestamp, tz=est_tz)
        # Determine if we're in EDT (Daylight) or EST (Standard)
        tz_abbrev = "EDT" if dt.dst() else "EST"
        return dt.strftime(f"%m/%d %I:%M %p {tz_abbrev}")
    except Exception:
        return None


def create_ticker_progress_panel():
    """Create the ticker progress panel container."""
    return html.Div(
        id="ticker-progress-container",
        children=[
            html.Div(
                "No active analyses. Start an analysis to track progress.",
                className="text-center text-muted py-4"
            )
        ]
    )


def render_agent_badge(abbrev, status):
    """Render a single agent badge with status color and tooltip."""
    colors = {
        "completed": "success",
        "in_progress": "warning",
        "pending": "secondary"
    }

    status_icons = {
        "completed": "✓",
        "in_progress": "●",
        "pending": "○"
    }

    agent_name = AGENT_ABBREVIATIONS.get(abbrev, abbrev)
    icon = status_icons.get(status, "")

    # Wrap badge in span with title for tooltip
    return html.Span(
        dbc.Badge(
            abbrev,
            color=colors.get(status, "secondary"),
            className="agent-badge",
        ),
        title=f"{agent_name}: {status}",
        style={"cursor": "help"},
        className="me-1"
    )


def calculate_progress(agent_statuses):
    """Calculate completion percentage from agent statuses."""
    if not agent_statuses:
        return 0

    completed = sum(1 for s in agent_statuses.values() if s == "completed")
    total = len(agent_statuses)

    return int((completed / total) * 100) if total > 0 else 0


def get_overall_status(agent_statuses):
    """Determine overall status from agent statuses."""
    if not agent_statuses:
        return "pending", "Pending", "secondary"

    if all(s == "completed" for s in agent_statuses.values()):
        return "completed", "Complete", "success"
    elif any(s == "in_progress" for s in agent_statuses.values()):
        return "in_progress", "In Progress", "warning"
    else:
        return "pending", "Pending", "secondary"


def render_ticker_progress_row(symbol, agent_statuses, is_analyzing=False, active_analysts=None,
                                start_time=None, completed_time=None):
    """Render a single ticker's progress with badges grouped by phase.

    Args:
        symbol: The ticker symbol
        agent_statuses: Dict of agent name -> status
        is_analyzing: Whether this ticker is currently being analyzed
        active_analysts: List of active analyst names
        start_time: Unix timestamp when analysis started
        completed_time: Unix timestamp when analysis completed (None if not done)
    """

    # Filter to only count active analysts + research/trading/risk agents
    active_analysts = active_analysts or list(ANALYST_AGENTS.values())

    # Build list of agents to show (active analysts + all other phases)
    agents_to_show = []
    for abbrev, agent_name in ANALYST_AGENTS.items():
        if agent_name in active_analysts:
            agents_to_show.append((abbrev, agent_name))

    # Always show research, trading, and risk agents
    for agent_dict in [RESEARCH_AGENTS, TRADING_AGENTS, RISK_AGENTS]:
        for abbrev, agent_name in agent_dict.items():
            agents_to_show.append((abbrev, agent_name))

    # Calculate progress based on visible agents only
    visible_statuses = {name: agent_statuses.get(name, "pending") for _, name in agents_to_show}
    percent = calculate_progress(visible_statuses)
    status, status_text, progress_color = get_overall_status(visible_statuses)

    # Status icon
    status_icons = {
        "completed": "bi-check-circle-fill",
        "in_progress": "bi-arrow-repeat",
        "pending": "bi-clock"
    }
    status_icon = status_icons.get(status, "bi-clock")

    # Build agent badges grouped by phase
    def make_badge_group(agents_dict, label, filter_active=False):
        badges = []
        for abbrev, agent_name in agents_dict.items():
            if filter_active and agent_name not in active_analysts:
                continue
            agent_status = agent_statuses.get(agent_name, "pending")
            badges.append(render_agent_badge(abbrev, agent_status))
        if not badges:
            return None
        return html.Span([
            html.Small(f"{label}: ", className="text-muted me-1"),
            *badges
        ], className="me-3")

    badge_groups = [
        make_badge_group(ANALYST_AGENTS, "Analysts", filter_active=True),
        make_badge_group(RESEARCH_AGENTS, "Research"),
        make_badge_group(TRADING_AGENTS, "Trade"),
        make_badge_group(RISK_AGENTS, "Risk"),
    ]
    badge_groups = [g for g in badge_groups if g is not None]

    return html.Div([
        # Header row: Symbol + Progress Bar + Status
        dbc.Row([
            dbc.Col([
                html.Strong(symbol, className="ticker-symbol"),
                html.I(className=f"bi {status_icon} ms-2 text-{progress_color}") if is_analyzing else None,
            ], width=2, className="d-flex align-items-center"),
            dbc.Col([
                dbc.Progress(
                    value=percent,
                    color=progress_color,
                    className="ticker-progress-bar",
                    style={"height": "8px"}
                )
            ], width=7, className="d-flex align-items-center"),
            dbc.Col([
                html.Span(
                    f"{percent}% {status_text}",
                    className=f"text-{progress_color} small fw-bold"
                )
            ], width=3, className="text-end"),
        ], className="align-items-center mb-2"),

        # Agent badges row - grouped by phase
        html.Div(badge_groups, className="agent-badges-row"),

        # Timestamps row - Started / Completed
        html.Div([
            html.Small([
                html.Span("Started: ", className="text-muted"),
                html.Span(format_timestamp_est(start_time) or "—", className="text-info"),
            ], className="me-4"),
            html.Small([
                html.Span("Completed: ", className="text-muted"),
                html.Span(
                    format_timestamp_est(completed_time) or ("In progress..." if is_analyzing else "—"),
                    className="text-success" if completed_time else "text-warning" if is_analyzing else "text-muted"
                ),
            ]),
        ], className="mt-1 timestamps-row"),

    ], className="ticker-progress-item")


def render_all_ticker_progress(symbol_states, analyzing_symbols=None, active_analysts=None):
    """Render progress rows for all tickers."""
    if not symbol_states:
        return html.Div(
            "No active analyses. Start an analysis to track progress.",
            className="text-center text-muted py-4"
        )

    analyzing_symbols = analyzing_symbols or set()
    active_analysts = active_analysts or list(ANALYST_AGENTS.values())

    # Sort tickers: analyzing first, then by completion
    def sort_key(item):
        symbol, state = item
        is_analyzing = symbol in analyzing_symbols
        agent_statuses = state.get("agent_statuses", {})
        percent = calculate_progress(agent_statuses)
        # Analyzing tickers first (0), then by reverse percent (higher first)
        return (0 if is_analyzing else 1, -percent, symbol)

    sorted_items = sorted(symbol_states.items(), key=sort_key)

    rows = []
    for symbol, state in sorted_items:
        agent_statuses = state.get("agent_statuses", {})
        is_analyzing = symbol in analyzing_symbols
        start_time = state.get("session_start_time")
        completed_time = state.get("analysis_completed_time")
        rows.append(render_ticker_progress_row(
            symbol, agent_statuses, is_analyzing, active_analysts,
            start_time=start_time, completed_time=completed_time
        ))

    # Summary header
    total = len(symbol_states)
    completed = sum(
        1 for state in symbol_states.values()
        if all(s == "completed" for s in state.get("agent_statuses", {}).values())
    )
    in_progress = len(analyzing_symbols)

    header = html.Div([
        dbc.Row([
            dbc.Col([
                html.Small([
                    dbc.Badge(f"{total}", color="primary", className="me-1"),
                    " Total",
                ], className="me-3"),
                html.Small([
                    dbc.Badge(f"{in_progress}", color="warning", className="me-1"),
                    " Active",
                ], className="me-3"),
                html.Small([
                    dbc.Badge(f"{completed}", color="success", className="me-1"),
                    " Complete",
                ]),
            ]),
        ], className="mb-3"),
    ])

    return html.Div([header] + rows)
