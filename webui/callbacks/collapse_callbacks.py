"""
Collapse callbacks for collapsible panels
"""

from dash import Input, Output, State, callback_context, ALL, MATCH
from dash.exceptions import PreventUpdate


# List of all collapsible panel IDs
COLLAPSIBLE_PANELS = [
    "alpaca-panel",
    "scanner-panel",
    "progress-panel",
    "config-panel",
    "chart-panel",
    "status-panel",
    "decision-panel",
    "reports-panel",
]


def register_collapse_callbacks(app):
    """Register all collapse-related callbacks."""

    # Generate callbacks for each panel
    for panel_id in COLLAPSIBLE_PANELS:
        _create_toggle_callback(app, panel_id)


def _create_toggle_callback(app, panel_id):
    """Create a toggle callback for a specific panel."""

    @app.callback(
        Output(f"{panel_id}-collapse", "is_open"),
        Output(f"{panel_id}-chevron", "className"),
        Input(f"{panel_id}-header", "n_clicks"),
        State(f"{panel_id}-collapse", "is_open"),
        prevent_initial_call=True
    )
    def toggle_collapse(n_clicks, is_open):
        if n_clicks is None:
            raise PreventUpdate

        new_state = not is_open
        chevron_class = "bi bi-chevron-down me-2 chevron-icon" if new_state else "bi bi-chevron-right me-2 chevron-icon"

        return new_state, chevron_class

    # Rename the callback function to be unique
    toggle_collapse.__name__ = f"toggle_{panel_id.replace('-', '_')}"

    return toggle_collapse
