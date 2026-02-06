"""
webui/components/header.py - Header component for the web UI.
"""

import dash_bootstrap_components as dbc
from dash import html, dcc


def create_header():
    """Create the header component for the web UI."""
    return dbc.Card(
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H1("AI Trading Hub", className="text-start mb-1 fw-bold"),
                    html.P("Autonomous Multi-Agent Trading Platform", className="text-start text-muted mb-0")
                ], width="auto", className="flex-grow-1"),
                dbc.Col([
                    html.Div([
                        dbc.Button(
                            [html.I(className="fas fa-moon me-2"), "Dark"],
                            id="theme-toggle-btn",
                            color="outline-secondary",
                            size="sm",
                            className="theme-toggle-btn"
                        ),
                        dcc.Store(id="theme-store", data={"theme": "dark"}, storage_type="local")
                    ], className="d-flex align-items-center")
                ], width="auto", className="d-flex align-items-center")
            ], className="align-items-center")
        ]),
        className="mb-4"
    )
