"""
webui/components/portfolio_panel.py - Portfolio Overview Dashboard Panel

Displays consolidated portfolio health: account metrics, risk limit utilization,
sector exposure, and active configuration summary. Data sourced from
PortfolioContext (tradingagents/dataflows/portfolio_risk.py).
"""

import dash_bootstrap_components as dbc
from dash import html
import os


def _is_alpaca_configured():
    """Check if Alpaca API credentials are configured."""
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    return bool(api_key and secret_key)


def _render_not_configured_message():
    """Render a message when Alpaca is not configured."""
    return html.Div([
        html.Div([
            html.I(className="fas fa-key fa-2x mb-3 text-muted"),
            html.H5("Alpaca Not Configured", className="text-muted"),
            html.P([
                "Set your Alpaca API keys in ",
                html.Strong("System Settings"),
                " or in your ",
                html.Code(".env"),
                " file to view portfolio data."
            ], className="text-muted small mb-0")
        ], className="text-center p-4")
    ])


def create_portfolio_panel():
    """Create the Portfolio Overview panel with placeholder containers."""
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-chart-pie me-2"),
            html.Span("Portfolio Overview", className="fw-semibold"),
        ]),
        dbc.CardBody([
            # Row 1: Key metrics
            html.Div(id="portfolio-metrics-row"),
            # Row 2: Risk bars (left) + Sector exposure (right)
            dbc.Row([
                dbc.Col(
                    html.Div(id="portfolio-risk-bars"),
                    lg=6, className="mb-3 mb-lg-0"
                ),
                dbc.Col(
                    html.Div(id="portfolio-sector-chart"),
                    lg=6
                ),
            ], className="mb-3"),
            # Row 3: Config summary
            html.Div(id="portfolio-config-summary"),
        ], className="p-3")
    ], className="mb-3")


def render_portfolio_metrics(ctx):
    """Build Row 1: 4 stat cards from PortfolioContext.

    Args:
        ctx: PortfolioContext instance (must not be None).

    Returns:
        Dash component with equity, exposure, P/L, remaining capacity.
    """
    equity = ctx.equity
    total_exposure = ctx.total_exposure
    exposure_pct = (total_exposure / equity * 100) if equity > 0 else 0
    unrealized_pl = sum(p.unrealized_pl for p in ctx.positions)
    pl_sign = "+" if unrealized_pl >= 0 else ""
    pl_color = "text-success" if unrealized_pl >= 0 else "text-danger"
    remaining = ctx.remaining_deployment_capacity

    return dbc.Row([
        dbc.Col(html.Div([
            html.Div("Equity", className="stat-label"),
            html.Div(f"${equity:,.2f}", className="stat-value"),
        ], className="portfolio-stat"), width=6, md=3),
        dbc.Col(html.Div([
            html.Div("Total Exposure", className="stat-label"),
            html.Div(f"${total_exposure:,.2f}", className="stat-value"),
            dbc.Progress(
                value=min(exposure_pct, 100),
                color="warning" if exposure_pct > 80 else "info",
                className="mt-1",
                style={"height": "4px"},
            ),
            html.Small(f"{exposure_pct:.1f}% of equity", className="text-muted"),
        ], className="portfolio-stat"), width=6, md=3),
        dbc.Col(html.Div([
            html.Div("Unrealized P/L", className="stat-label"),
            html.Div(
                f"{pl_sign}${abs(unrealized_pl):,.2f}",
                className=f"stat-value {pl_color}",
            ),
        ], className="portfolio-stat"), width=6, md=3),
        dbc.Col(html.Div([
            html.Div("Remaining Capacity", className="stat-label"),
            html.Div(f"${remaining:,.2f}", className="stat-value"),
        ], className="portfolio-stat"), width=6, md=3),
    ], className="g-2 mb-3")


def render_risk_utilization(ctx):
    """Build Row 2 left: 3 progress bars showing risk limit usage.

    Args:
        ctx: PortfolioContext instance (must not be None).

    Returns:
        Dash component with per-trade, single position, and total exposure bars.
    """
    equity = ctx.equity
    if equity <= 0:
        return html.Div(html.Small("No equity data", className="text-muted"))

    # Per-trade limit (show limit amount, no "used" bar since it's per-trade)
    per_trade_limit = equity * (ctx.max_per_trade_pct / 100.0)

    # Largest single position as % of equity
    largest_position = max(
        (abs(p.market_value) for p in ctx.positions), default=0
    )
    single_pct = (largest_position / equity * 100) if equity > 0 else 0
    single_limit_pct = ctx.max_single_position_pct

    # Total exposure as % of equity
    total_exp_pct = (ctx.total_exposure / equity * 100) if equity > 0 else 0
    total_limit_pct = ctx.max_total_exposure_pct

    guardrails_enabled = True  # Will be overridden by caller if needed

    def _bar_color(used, limit):
        ratio = used / limit if limit > 0 else 0
        if ratio >= 0.9:
            return "danger"
        elif ratio >= 0.7:
            return "warning"
        return "success"

    return html.Div([
        html.H6("Risk Limit Utilization", className="text-muted mb-2"),

        # Per-trade limit (informational)
        html.Div([
            html.Div([
                html.Small("Per-Trade Limit", className="text-muted"),
                html.Small(
                    f"${per_trade_limit:,.0f} ({ctx.max_per_trade_pct}%)",
                    className="text-muted float-end",
                ),
            ], className="d-flex justify-content-between"),
            dbc.Progress(value=0, color="info", style={"height": "6px"}),
        ], className="mb-2"),

        # Single position
        html.Div([
            html.Div([
                html.Small("Largest Position", className="text-muted"),
                html.Small(
                    f"{single_pct:.1f}% / {single_limit_pct}%",
                    className="text-muted float-end",
                ),
            ], className="d-flex justify-content-between"),
            dbc.Progress(
                value=min(single_pct / single_limit_pct * 100, 100) if single_limit_pct > 0 else 0,
                color=_bar_color(single_pct, single_limit_pct),
                style={"height": "6px"},
            ),
        ], className="mb-2"),

        # Total exposure
        html.Div([
            html.Div([
                html.Small("Total Exposure", className="text-muted"),
                html.Small(
                    f"{total_exp_pct:.1f}% / {total_limit_pct}%",
                    className="text-muted float-end",
                ),
            ], className="d-flex justify-content-between"),
            dbc.Progress(
                value=min(total_exp_pct / total_limit_pct * 100, 100) if total_limit_pct > 0 else 0,
                color=_bar_color(total_exp_pct, total_limit_pct),
                style={"height": "6px"},
            ),
        ], className="mb-2"),
    ])


def render_sector_exposure(ctx):
    """Build Row 2 right: horizontal bars per sector.

    Args:
        ctx: PortfolioContext instance (must not be None).

    Returns:
        Dash component with sector breakdown bars.
    """
    if not ctx.sector_breakdown:
        return html.Div([
            html.H6("Sector Exposure", className="text-muted mb-2"),
            html.Small("No positions", className="text-muted"),
        ])

    equity = ctx.equity
    # Sort sectors by value descending
    sorted_sectors = sorted(ctx.sector_breakdown.items(), key=lambda x: -x[1])

    max_value = sorted_sectors[0][1] if sorted_sectors else 1

    rows = []
    for sector, value in sorted_sectors:
        pct = (value / equity * 100) if equity > 0 else 0
        bar_width = (value / max_value * 100) if max_value > 0 else 0

        rows.append(html.Div([
            html.Div([
                html.Small(sector, className="text-muted"),
                html.Small(
                    f"${value:,.0f} ({pct:.1f}%)",
                    className="text-muted float-end",
                ),
            ], className="d-flex justify-content-between"),
            html.Div(
                html.Div(
                    style={
                        "width": f"{max(bar_width, 2)}%",
                        "height": "6px",
                        "backgroundColor": "#3B82F6",
                        "borderRadius": "3px",
                    }
                ),
                style={
                    "height": "6px",
                    "backgroundColor": "rgba(255,255,255,0.1)",
                    "borderRadius": "3px",
                },
            ),
        ], className="mb-2"))

    return html.Div([
        html.H6("Sector Exposure", className="text-muted mb-2"),
        *rows,
    ])


def render_config_summary(settings):
    """Build Row 3: badge tags for active configuration.

    Args:
        settings: system_settings dict.

    Returns:
        Dash component with configuration badges.
    """
    badges = []

    # LLM models
    deep_llm = settings.get("deep_think_llm", "o4-mini")
    quick_llm = settings.get("quick_think_llm", "gpt-4.1-nano")
    badges.append(dbc.Badge(f"Deep: {deep_llm}", color="primary", className="me-1 mb-1"))
    badges.append(dbc.Badge(f"Quick: {quick_llm}", color="info", className="me-1 mb-1"))

    # Debate rounds
    debate_rounds = settings.get("max_debate_rounds", 4)
    risk_rounds = settings.get("max_risk_discuss_rounds", 3)
    badges.append(dbc.Badge(
        f"Debate: {debate_rounds}R / Risk: {risk_rounds}R",
        color="secondary", className="me-1 mb-1",
    ))

    # Trading mode
    allow_shorts = settings.get("allow_shorts", False)
    mode_label = "Long/Short" if allow_shorts else "Long Only"
    badges.append(dbc.Badge(mode_label, color="dark", className="me-1 mb-1"))

    # Risk guardrails
    guardrails = settings.get("risk_guardrails_enabled", False)
    if guardrails:
        badges.append(dbc.Badge("Guardrails ON", color="success", className="me-1 mb-1"))
    else:
        badges.append(dbc.Badge("Guardrails OFF", color="warning", className="me-1 mb-1"))

    # Stop-Loss / Take-Profit
    sl = settings.get("enable_stop_loss", False)
    tp = settings.get("enable_take_profit", False)
    if sl:
        sl_pct = settings.get("stop_loss_percentage", 5.0)
        badges.append(dbc.Badge(f"SL {sl_pct}%", color="danger", className="me-1 mb-1"))
    if tp:
        tp_pct = settings.get("take_profit_percentage", 10.0)
        badges.append(dbc.Badge(f"TP {tp_pct}%", color="success", className="me-1 mb-1"))

    # Online tools
    online = settings.get("online_tools", True)
    badges.append(dbc.Badge(
        "Live Data" if online else "Cached Data",
        color="info" if online else "secondary",
        className="me-1 mb-1",
    ))

    return html.Div([
        html.H6("Active Configuration", className="text-muted mb-2"),
        html.Div(badges, className="d-flex flex-wrap"),
    ])
