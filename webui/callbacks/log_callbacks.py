"""
Log Panel Callbacks for TradingAgents WebUI
Handles real-time log streaming to the UI.
"""

from dash import Input, Output, State, html, no_update
import dash

from webui.utils.log_handler import get_log_handler
from webui.components.log_panel import format_log_entry


# Log level priority for filtering
LOG_LEVEL_PRIORITY = {
    "DEBUG": 0,
    "INFO": 1,
    "WARNING": 2,
    "ERROR": 3,
    "CRITICAL": 4
}


def register_log_callbacks(app):
    """Register all log-related callbacks."""

    # =========================================================================
    # Toggle Log Streaming (enable/disable interval)
    # =========================================================================
    @app.callback(
        Output("log-update-interval", "disabled"),
        [Input("log-streaming-toggle", "value")],
        prevent_initial_call=True
    )
    def toggle_log_streaming(streaming_value):
        """Toggle log streaming on/off."""
        # If streaming is checked (value contains True), interval is NOT disabled
        is_streaming = bool(streaming_value and True in streaming_value)
        return not is_streaming

    # =========================================================================
    # Clear Logs
    # =========================================================================
    @app.callback(
        [Output("log-container", "children", allow_duplicate=True),
         Output("log-last-index", "data", allow_duplicate=True),
         Output("log-count-badge", "children", allow_duplicate=True)],
        [Input("clear-logs-btn", "n_clicks")],
        prevent_initial_call=True
    )
    def clear_logs(n_clicks):
        """Clear all logs from the display."""
        if n_clicks:
            handler = get_log_handler()
            handler.clear()
            return [html.Div("Logs cleared", className="text-muted")], 0, "0"
        return no_update, no_update, no_update

    # =========================================================================
    # Stream Logs (Real-time Update)
    # =========================================================================
    @app.callback(
        [Output("log-container", "children", allow_duplicate=True),
         Output("log-last-index", "data", allow_duplicate=True),
         Output("log-count-badge", "children", allow_duplicate=True)],
        [Input("log-update-interval", "n_intervals")],
        [State("log-last-index", "data"),
         State("log-level-filter", "value"),
         State("log-container", "children")],
        prevent_initial_call=True
    )
    def stream_logs(n_intervals, last_index, level_filter, current_children):
        """Stream new logs to the UI."""
        try:
            handler = get_log_handler()

            # Get minimum log level for filtering
            min_level = LOG_LEVEL_PRIORITY.get(level_filter, 0) if level_filter != "ALL" else 0

            # Get new logs since last update
            new_logs = handler.get_logs_since(last_index or 0)

            if not new_logs:
                # No new logs, just update count
                total_count = handler.get_total_count()
                return no_update, no_update, str(total_count)

            # Filter logs by level
            filtered_logs = [
                log for log in new_logs
                if LOG_LEVEL_PRIORITY.get(log["level"], 0) >= min_level
            ]

            # Get the latest index
            latest_index = new_logs[-1]["index"] if new_logs else last_index

            # Format new log entries
            new_entries = [format_log_entry(log) for log in filtered_logs]

            # Combine with existing logs (keep last 200 entries max for performance)
            if current_children and isinstance(current_children, list):
                # Filter out placeholder messages
                existing = [
                    child for child in current_children
                    if isinstance(child, dict) and child.get("props", {}).get("className") != "text-muted"
                ]
                all_entries = existing + new_entries
            else:
                all_entries = new_entries

            # Limit to last 200 entries for performance
            if len(all_entries) > 200:
                all_entries = all_entries[-200:]

            # Update count badge
            total_count = handler.get_total_count()

            if not all_entries:
                all_entries = [html.Div("No logs matching filter", className="text-muted")]

            return all_entries, latest_index, str(total_count)
        except Exception as e:
            # Don't let log callback errors break the app
            return no_update, no_update, no_update

    # =========================================================================
    # Refresh logs when filter changes
    # =========================================================================
    @app.callback(
        Output("log-container", "children", allow_duplicate=True),
        [Input("log-level-filter", "value")],
        prevent_initial_call=True
    )
    def refresh_logs_on_filter_change(level_filter):
        """Refresh all logs when the filter changes."""
        try:
            handler = get_log_handler()

            # Get minimum log level for filtering
            min_level = LOG_LEVEL_PRIORITY.get(level_filter, 0) if level_filter != "ALL" else 0

            # Get all logs and filter
            all_logs = handler.get_all_logs()
            filtered_logs = [
                log for log in all_logs
                if LOG_LEVEL_PRIORITY.get(log["level"], 0) >= min_level
            ]

            if not filtered_logs:
                return [html.Div("No logs matching filter", className="text-muted")]

            # Limit to last 200
            if len(filtered_logs) > 200:
                filtered_logs = filtered_logs[-200:]

            return [format_log_entry(log) for log in filtered_logs]
        except Exception:
            return no_update
