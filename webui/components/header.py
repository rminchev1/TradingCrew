"""
webui/components/header.py - Header component for the web UI.
"""

import dash_bootstrap_components as dbc
from dash import html

def create_header():
    """Create the header component for the web UI."""
    return dbc.Card(
        dbc.CardBody([
            html.H1("AI Trading Hub", className="text-start mb-1 fw-bold"),
            html.P("Autonomous Multi-Agent Trading Platform", className="text-start text-muted mb-0")
        ]),
        className="mb-4"
    ) 