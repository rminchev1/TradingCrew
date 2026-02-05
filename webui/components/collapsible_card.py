"""
Collapsible Card Component - Reusable wrapper for collapsible panels
"""

import dash_bootstrap_components as dbc
from dash import html


def create_collapsible_card(
    card_id: str,
    title: str,
    icon: str,
    children,
    default_open: bool = True,
    badge_id: str = None,
    extra_class: str = ""
):
    """
    Create a collapsible card with clickable header.

    Args:
        card_id: Unique identifier for the card (used for collapse IDs)
        title: Card title text
        icon: Emoji or icon to display before title
        children: Content to display inside the card body
        default_open: Whether the card starts expanded
        badge_id: Optional ID for a badge element in the header
        extra_class: Additional CSS classes for the card

    Returns:
        dbc.Card component with collapsible body
    """
    # Build badge element if ID provided
    badge_element = html.Span(id=badge_id, className="badge-pill") if badge_id else None

    return dbc.Card([
        # Clickable header
        dbc.CardHeader(
            dbc.Row([
                dbc.Col([
                    html.I(
                        id=f"{card_id}-chevron",
                        className=f"bi bi-chevron-{'down' if default_open else 'right'} me-2 chevron-icon"
                    ),
                    html.Span(icon, className="me-2 panel-icon"),
                    html.Span(title, className="fw-semibold panel-title"),
                ], width="auto", className="d-flex align-items-center"),
                dbc.Col([
                    badge_element
                ], width="auto", className="ms-auto d-flex align-items-center") if badge_element else None,
            ], className="align-items-center g-0", justify="between"),
            id=f"{card_id}-header",
            style={"cursor": "pointer"},
            className="collapsible-header",
            n_clicks=0
        ),
        # Collapsible body
        dbc.Collapse(
            dbc.CardBody(children, className="collapsible-body"),
            id=f"{card_id}-collapse",
            is_open=default_open
        ),
    ], className=f"mb-3 collapsible-card {extra_class}".strip(), id=card_id)


def create_simple_collapsible(
    card_id: str,
    title: str,
    icon: str,
    content_id: str,
    default_open: bool = True
):
    """
    Create a simple collapsible card where content is loaded dynamically.

    Args:
        card_id: Unique identifier for the card
        title: Card title text
        icon: Emoji or icon
        content_id: ID for the content div (for callbacks to populate)
        default_open: Whether the card starts expanded

    Returns:
        dbc.Card component with empty content area
    """
    return create_collapsible_card(
        card_id=card_id,
        title=title,
        icon=icon,
        children=html.Div(id=content_id),
        default_open=default_open
    )
