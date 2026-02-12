"""
Status and refresh-related callbacks for TradingAgents WebUI
"""

from dash import Input, Output, html
import dash_bootstrap_components as dbc
from datetime import datetime
import pytz

from webui.utils.state import app_state
from webui.config.constants import COLORS


def register_status_callbacks(app):
    """Register all status and refresh-related callbacks"""
    
    @app.callback(
        Output("status-table", "children"),
        Input("refresh-interval", "n_intervals")
    )
    def update_status_table(n_intervals):
        """Update the agent status table"""
        current_state = app_state.get_current_state()
        if not current_state:
            return dbc.Table()

        # Group agents by team, showing only selected analysts
        teams = {
            "Analyst Team": getattr(app_state, 'active_analysts', []),
            "Research Team": ["Bull Researcher", "Bear Researcher", "Research Manager"],
            "Trading Team": ["Trader"],
            "Risk Management": ["Risky Analyst", "Safe Analyst", "Neutral Analyst", "Portfolio Manager"]
        }
        
        # Create table header
        table_header = [
            html.Thead(html.Tr([
                html.Th("Team"),
                html.Th("Agent"),
                html.Th("Status")
            ]))
        ]
        
        # Create table rows
        rows = []
        team_order = ["Analyst Team", "Research Team", "Trading Team", "Risk Management"]
        for team_name in team_order:
            agents = teams.get(team_name, [])
            if not agents:  # Skip team if no agents are active (e.g., no analysts selected)
                continue
            
            for agent in agents:
                status = current_state["agent_statuses"].get(agent, "pending")
                
                # Set status icon and color
                if status == "completed":
                    status_icon = "✅"
                    status_text = "COMPLETED"
                    status_color = COLORS["completed"]
                elif status == "in_progress" and app_state.pipeline_paused:
                    status_icon = "⏸️"
                    status_text = "PAUSED"
                    status_color = COLORS["in_progress"]
                elif status == "in_progress":
                    status_icon = "🔄"
                    status_text = "IN PROGRESS"
                    status_color = COLORS["in_progress"]
                else:
                    status_icon = "⏸️"
                    status_text = "PENDING"
                    status_color = COLORS["pending"]
                
                # Create a row
                row = html.Tr([
                    html.Td(team_name),
                    html.Td(agent),
                    html.Td(html.Span(f"{status_icon} {status_text}", style={"color": status_color}))
                ])
                rows.append(row)
        
        table_body = [html.Tbody(rows)]
        
        return dbc.Table(table_header + table_body, bordered=True, hover=True, responsive=True, striped=True)

    @app.callback(
        [Output("tool-calls-text", "children"),
         Output("llm-calls-text", "children"),
         Output("reports-text", "children")],
        [Input("refresh-interval", "n_intervals")]
    )
    def update_progress_stats(n_intervals):
        """Update the progress statistics"""
        return (
            f"🧰 Tool Calls: {app_state.tool_calls_count}",
            f"🤖 LLM Calls: {app_state.llm_calls_count}",
            f"📊 Generated Reports: {app_state.generated_reports_count}"
        )

    @app.callback(
        [Output("refresh-interval", "disabled"),
         Output("medium-refresh-interval", "disabled"),
         Output("refresh-status", "children"),
         Output("refresh-status", "className")],
        [Input("app-store", "data"),
         Input("refresh-interval", "n_intervals")]
    )
    def manage_refresh_intervals_and_status(store_data, n_intervals):
        """
        Manage the refresh intervals and their associated status message.
        """
        # Fast refresh (1 s) needed while analysis is in progress, paused (to stay responsive), or when UI still needs an immediate update.
        refresh_disabled = not (app_state.analysis_running or app_state.pipeline_paused or app_state.needs_ui_update)

        # The medium-rate interval (5 s) is kept ON at all times so that the tabs/summary
        # can still update even after the analysis thread has ended.  Its lightweight
        # cadence avoids performance issues but guarantees late data (e.g., final
        # decisions) gets rendered without a manual browser refresh.
        medium_refresh_disabled = False

        # Clear the needs-update flag after we've signalled at least one more cycle.
        if app_state.needs_ui_update and not refresh_disabled:
            app_state.needs_ui_update = False

        # Enhanced status message for different modes
        if app_state.pipeline_paused:
            paused_count = len(app_state.paused_symbols)
            if paused_count > 0:
                status_msg = f"⏸️ Pipeline paused ({paused_count} symbol{'s' if paused_count != 1 else ''} waiting)"
            else:
                status_msg = "⏸️ Pipeline paused - will pause at next breakpoint"
            status_class = "text-warning mt-2"
            return refresh_disabled, medium_refresh_disabled, status_msg, status_class
        elif app_state.market_hour_enabled:
            if app_state.analysis_running:
                status_msg = "🔄 Market hour mode - Analysis in progress"
                status_class = "text-warning mt-2"
            else:
                # Format next execution time
                try:
                    from webui.utils.market_hours import get_next_market_datetime
                    import datetime
                    
                    next_times = []
                    for hour in app_state.market_hours:
                        next_dt = get_next_market_datetime(hour)
                        formatted_time = next_dt.strftime("%I:%M %p on %A")
                        next_times.append(f"{hour}:00 → {formatted_time}")
                    
                    next_info = "; ".join(next_times[:2])  # Show first 2 to avoid clutter
                    status_msg = f"⏰ Market hour mode - Next: {next_info}"
                    status_class = "text-info mt-2"
                except Exception as e:
                    status_msg = "⏰ Market hour mode - Waiting for next market hour"
                    status_class = "text-info mt-2"
        elif app_state.loop_enabled:
            if app_state.analysis_running:
                status_msg = "🔄 Loop mode active - Analysis in progress"
                status_class = "text-warning mt-2"
            else:
                # Show next run time if available
                if app_state.next_loop_run_time:
                    next_time_str = app_state.next_loop_run_time.strftime("%I:%M %p %Z")
                    status_msg = f"⏳ Loop mode - Next run: {next_time_str} ({app_state.loop_interval_minutes} min intervals)"
                else:
                    status_msg = f"⏳ Loop mode - Waiting for next iteration ({app_state.loop_interval_minutes} min intervals)"
                status_class = "text-info mt-2"
        else:
            status_msg = (
                "🔄 Auto-refreshing during analysis" if app_state.analysis_running else "🔄 Finalizing results"
            ) if not refresh_disabled else "⏸️ Updates paused until analysis starts"
            status_class = "text-success mt-2" if not refresh_disabled else "text-secondary mt-2"

        return refresh_disabled, medium_refresh_disabled, status_msg, status_class

    @app.callback(
        [Output("market-time-display", "children"),
         Output("market-status-display", "children"),
         Output("market-status-display", "className")],
        Input("clock-interval", "n_intervals")
    )
    def update_market_time(n_intervals):
        """Update the market time display every second."""
        eastern = pytz.timezone('US/Eastern')
        now_eastern = datetime.now(eastern)

        # Format time string with timezone abbreviation
        time_str = now_eastern.strftime("%I:%M:%S %p")
        tz_abbr = now_eastern.strftime("%Z")  # EST or EDT

        # Check if market is open (9:30 AM - 4:00 PM ET, Mon-Fri)
        weekday = now_eastern.weekday()  # 0=Monday, 6=Sunday
        hour = now_eastern.hour
        minute = now_eastern.minute

        market_open_time = 9 * 60 + 30  # 9:30 AM in minutes
        market_close_time = 16 * 60  # 4:00 PM in minutes
        current_time_minutes = hour * 60 + minute

        if weekday >= 5:  # Weekend
            status = "Closed (Weekend)"
            status_color = "small text-danger"
        elif current_time_minutes < market_open_time:
            mins_until_open = market_open_time - current_time_minutes
            hrs, mins = divmod(mins_until_open, 60)
            status = f"Opens in {hrs}h {mins}m"
            status_color = "small text-warning"
        elif current_time_minutes >= market_close_time:
            status = "Closed"
            status_color = "small text-danger"
        else:
            mins_until_close = market_close_time - current_time_minutes
            hrs, mins = divmod(mins_until_close, 60)
            status = f"Open ({hrs}h {mins}m left)"
            status_color = "small text-success"

        return f"{time_str} {tz_abbr}", status, status_color