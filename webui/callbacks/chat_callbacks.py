"""
webui/callbacks/chat_callbacks.py - Callbacks for the Portfolio Assistant chat drawer.
"""

import threading
from datetime import datetime

import dash
from dash import Input, Output, State, ctx, ALL, no_update, html

from webui.utils.state import app_state

# Track last-rendered state to avoid unnecessary re-renders that destroy
# action buttons (pattern-matching buttons lose n_clicks when recreated).
_last_rendered_msg_count = 0
_last_rendered_processing = False


def register_chat_callbacks(app):
    """Register all chat-related callbacks."""

    # ------------------------------------------------------------------
    # Toggle chat drawer open/close
    # ------------------------------------------------------------------
    @app.callback(
        Output("chat-drawer", "is_open"),
        Output("chat-poll-interval", "disabled"),
        Input("chat-toggle-btn", "n_clicks"),
        State("chat-drawer", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_chat_drawer(n_clicks, is_open):
        if not n_clicks:
            return no_update, no_update
        new_state = not is_open
        # Enable polling only when drawer is open
        return new_state, not new_state

    # ------------------------------------------------------------------
    # Send message (button click or Enter key)
    # ------------------------------------------------------------------
    @app.callback(
        Output("chat-input", "value"),
        Output("chat-typing-indicator", "style", allow_duplicate=True),
        Output("chat-messages-container", "children", allow_duplicate=True),
        Input("chat-send-btn", "n_clicks"),
        Input("chat-input", "n_submit"),
        State("chat-input", "value"),
        State("system-settings-store", "data"),
        prevent_initial_call=True,
    )
    def send_message(n_clicks, n_submit, message, settings_data):
        if not message or not message.strip():
            return no_update, no_update, no_update

        message = message.strip()
        timestamp = datetime.now().strftime("%H:%M")

        # Append user message
        with app_state._lock:
            app_state.chat_messages.append({
                "role": "user",
                "content": message,
                "timestamp": timestamp,
            })
            if app_state.chat_processing:
                # Already processing, don't spawn another thread
                # Still re-render to show the new user message
                return "", no_update, _render_all_messages()

            app_state.chat_processing = True
            app_state.chat_error = None

        # Spawn background thread
        thread = threading.Thread(
            target=_run_chat_assistant,
            args=(list(app_state.chat_messages), settings_data),
            daemon=True,
        )
        thread.start()

        # Clear input, show typing indicator, render messages immediately
        _update_render_tracking()
        return "", {"display": "flex"}, _render_all_messages()

    # ------------------------------------------------------------------
    # Poll for chat updates (re-render ONLY when state changed)
    # ------------------------------------------------------------------
    @app.callback(
        Output("chat-messages-container", "children"),
        Output("chat-typing-indicator", "style"),
        Input("chat-poll-interval", "n_intervals"),
        prevent_initial_call=True,
    )
    def poll_chat_updates(n_intervals):
        global _last_rendered_msg_count, _last_rendered_processing

        msg_count = len(app_state.chat_messages)
        processing = app_state.chat_processing

        # Only re-render messages when something actually changed
        if msg_count == _last_rendered_msg_count and processing == _last_rendered_processing:
            return no_update, no_update

        _last_rendered_msg_count = msg_count
        _last_rendered_processing = processing

        messages = _render_all_messages()
        typing_style = {"display": "flex"} if processing else {"display": "none"}
        return messages, typing_style

    # ------------------------------------------------------------------
    # Clear chat
    # ------------------------------------------------------------------
    @app.callback(
        Output("chat-messages-container", "children", allow_duplicate=True),
        Output("chat-typing-indicator", "style", allow_duplicate=True),
        Input("chat-clear-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def clear_chat(n_clicks):
        if not n_clicks:
            return no_update, no_update
        app_state.reset_chat()
        _reset_render_tracking()
        return [
            html.Div(
                "Ask me about your portfolio, stock quotes, news, or analysis.",
                className="text-muted small text-center py-3",
            )
        ], {"display": "none"}

    # ------------------------------------------------------------------
    # Handle action button clicks (pattern-matching callback)
    # ------------------------------------------------------------------
    @app.callback(
        Output("watchlist-store", "data", allow_duplicate=True),
        Output("run-watchlist-store", "data", allow_duplicate=True),
        Input({"type": "chat-action-btn", "action": ALL, "symbol": ALL}, "n_clicks"),
        State("watchlist-store", "data"),
        State("run-watchlist-store", "data"),
        prevent_initial_call=True,
    )
    def handle_chat_action(n_clicks_list, watchlist_data, run_data):
        if not ctx.triggered_id or not any(n_clicks_list):
            return no_update, no_update

        triggered = ctx.triggered_id
        action = triggered.get("action", "")
        symbol = triggered.get("symbol", "")

        if not symbol:
            return no_update, no_update

        watchlist_data = watchlist_data or {"symbols": []}
        run_data = run_data or {"symbols": []}

        if action == "watchlist":
            symbols = list(watchlist_data.get("symbols", []))
            if symbol not in symbols:
                symbols.append(symbol)
                watchlist_data = {"symbols": symbols}
                _add_system_message(f"Added {symbol} to watchlist.")
                # Persist to SQLite
                try:
                    from webui.utils.local_storage import save_watchlist
                    save_watchlist(watchlist_data)
                except Exception:
                    pass
            else:
                _add_system_message(f"{symbol} is already on the watchlist.")
            return watchlist_data, no_update

        elif action == "run":
            symbols = list(run_data.get("symbols", []))
            if symbol not in symbols:
                symbols.append(symbol)
                run_data = {"symbols": symbols}
                _add_system_message(f"Added {symbol} to the run queue.")
                # Persist to SQLite
                try:
                    from webui.utils.local_storage import save_run_queue
                    save_run_queue(run_data)
                except Exception:
                    pass
            else:
                _add_system_message(f"{symbol} is already in the run queue.")
            return no_update, run_data

        return no_update, no_update


# ---------------------------------------------------------------------------
# Helper functions (module-level, used by callbacks)
# ---------------------------------------------------------------------------


def _update_render_tracking():
    """Sync the render-tracking counters with current state."""
    global _last_rendered_msg_count, _last_rendered_processing
    _last_rendered_msg_count = len(app_state.chat_messages)
    _last_rendered_processing = app_state.chat_processing


def _reset_render_tracking():
    """Reset the render-tracking counters (e.g. after clear)."""
    global _last_rendered_msg_count, _last_rendered_processing
    _last_rendered_msg_count = 0
    _last_rendered_processing = False


def _run_chat_assistant(messages_snapshot, settings_data):
    """Background thread: run the PortfolioAssistant and append response."""
    try:
        from tradingagents.chat_assistant import PortfolioAssistant
        import os

        # Determine API key and model from settings
        settings = settings_data or {}
        api_key = (
            settings.get("openai_api_key")
            or app_state.system_settings.get("openai_api_key")
            or os.environ.get("OPENAI_API_KEY", "")
        )
        model = (
            settings.get("quick_think_llm")
            or app_state.system_settings.get("quick_think_llm", "gpt-4.1-nano")
        )

        if not api_key:
            with app_state._lock:
                app_state.chat_messages.append({
                    "role": "assistant",
                    "content": "No OpenAI API key configured. Please set it in Settings > API Keys.",
                    "timestamp": datetime.now().strftime("%H:%M"),
                })
                app_state.chat_processing = False
            return

        assistant = PortfolioAssistant(model_name=model, api_key=api_key)

        # Build history for the assistant (only role + content)
        history = [{"role": m["role"], "content": m["content"]} for m in messages_snapshot]

        response = assistant.respond(history)

        with app_state._lock:
            app_state.chat_messages.append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().strftime("%H:%M"),
            })
            app_state.chat_processing = False

    except Exception as e:
        with app_state._lock:
            app_state.chat_messages.append({
                "role": "assistant",
                "content": f"Sorry, an error occurred: {e}",
                "timestamp": datetime.now().strftime("%H:%M"),
            })
            app_state.chat_processing = False
            app_state.chat_error = str(e)


def _render_all_messages():
    """Render all chat messages as Dash components."""
    from webui.components.chat_drawer import render_chat_message

    messages = app_state.chat_messages
    if not messages:
        return [
            html.Div(
                "Ask me about your portfolio, stock quotes, news, or analysis.",
                className="text-muted small text-center py-3",
            )
        ]

    return [render_chat_message(msg) for msg in messages]


def _add_system_message(content):
    """Add a system/confirmation message to the chat."""
    with app_state._lock:
        app_state.chat_messages.append({
            "role": "assistant",
            "content": content,
            "timestamp": datetime.now().strftime("%H:%M"),
        })
