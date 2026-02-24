"""
webui/components/chat_drawer.py - Portfolio Assistant chat drawer component.

A right-side Offcanvas drawer with a chat interface for querying portfolio data,
looking up market info, and receiving actionable suggestions.
"""

import dash_bootstrap_components as dbc
from dash import html, dcc


def create_chat_toggle_button():
    """Create the chat toggle button for the header."""
    return dbc.Button(
        [html.I(className="fas fa-comments me-2"), "Chat"],
        id="chat-toggle-btn",
        color="outline-info",
        size="sm",
        className="chat-toggle-btn me-2",
    )


def create_chat_drawer():
    """Create the portfolio assistant chat drawer (Offcanvas) with resizable left edge."""
    return html.Div([
        # Store for persisted drawer width (survives page reloads)
        dcc.Store(id="chat-width-store", storage_type="local", data={"width": 420}),

        dbc.Offcanvas(
            [
                # Messages container (scrollable)
                html.Div(
                    id="chat-messages-container",
                    className="chat-messages-container",
                    children=[
                        html.Div(
                            "Ask me about your portfolio, stock quotes, news, or analysis.",
                            className="text-muted small text-center py-3",
                        )
                    ],
                ),
                # Typing indicator
                html.Div(
                    id="chat-typing-indicator",
                    className="chat-typing-indicator",
                    style={"display": "none"},
                    children=[
                        dbc.Spinner(size="sm", color="info", spinner_class_name="me-2"),
                        html.Span("Thinking...", className="text-muted small"),
                    ],
                ),
                # Input area
                html.Div(
                    [
                        dbc.InputGroup(
                            [
                                dbc.Input(
                                    id="chat-input",
                                    placeholder="Ask about your portfolio...",
                                    type="text",
                                    debounce=False,
                                    className="chat-input",
                                ),
                                dbc.Button(
                                    html.I(className="fas fa-paper-plane"),
                                    id="chat-send-btn",
                                    color="primary",
                                    size="sm",
                                ),
                                dbc.Button(
                                    html.I(className="fas fa-trash-alt"),
                                    id="chat-clear-btn",
                                    color="outline-secondary",
                                    size="sm",
                                    title="Clear chat",
                                ),
                            ],
                            size="sm",
                        ),
                    ],
                    className="chat-input-area",
                ),
            ],
            id="chat-drawer",
            title="Portfolio Assistant",
            placement="end",
            backdrop=False,
            scrollable=True,
            is_open=False,
            className="chat-drawer",
            style={"width": "420px"},
        ),
    ])


def render_chat_message(msg):
    """Render a single chat message as a Dash component.

    Args:
        msg: Dict with keys: role ("user"|"assistant"), content (str), timestamp (str).

    Returns:
        html.Div component for the message bubble.
    """
    from tradingagents.chat_assistant import parse_actions, strip_action_markers

    role = msg.get("role", "user")
    content = msg.get("content", "")
    timestamp = msg.get("timestamp", "")

    if role == "user":
        return html.Div(
            [
                html.Div(content, className="chat-bubble-user"),
                html.Div(timestamp, className="chat-timestamp text-end"),
            ],
            className="chat-message-row chat-message-user",
        )
    else:
        # Assistant message: parse actions and render markdown + action buttons
        actions = parse_actions(content)
        display_content = strip_action_markers(content)

        children = [
            dcc.Markdown(
                display_content,
                className="chat-bubble-assistant-md",
            ),
        ]

        if actions:
            action_buttons = []
            for action in actions:
                symbol = action["symbol"]
                target = action["target"]
                reason = action["reason"]

                if target == "watchlist":
                    btn_color = "outline-info"
                    btn_icon = "fas fa-eye"
                    btn_label = f"Add {symbol} to Watchlist"
                elif target == "run":
                    btn_color = "outline-success"
                    btn_icon = "fas fa-play"
                    btn_label = f"Analyze {symbol}"
                else:
                    btn_color = "outline-secondary"
                    btn_icon = "fas fa-plus"
                    btn_label = f"{target} {symbol}"

                action_buttons.append(
                    dbc.Button(
                        [html.I(className=f"{btn_icon} me-1"), btn_label],
                        id={
                            "type": "chat-action-btn",
                            "action": target,
                            "symbol": symbol,
                        },
                        color=btn_color,
                        size="sm",
                        className="me-1 mb-1",
                        title=reason,
                    )
                )

            children.append(
                html.Div(action_buttons, className="chat-actions mt-1")
            )

        children.append(
            html.Div(timestamp, className="chat-timestamp"),
        )

        return html.Div(
            children,
            className="chat-message-row chat-message-assistant",
        )
