"""
Control and configuration callbacks for TradingAgents WebUI
"""

from dash import Input, Output, State, ctx, html, callback_context
import dash_bootstrap_components as dbc
import dash
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from webui.utils.state import app_state
from webui.components.analysis import start_analysis
from webui.utils.history import save_analysis_run
from webui.utils import local_storage


def get_max_parallel_tickers():
    """Get the max parallel tickers setting from system settings."""
    return app_state.system_settings.get("max_parallel_tickers", 3)


def register_control_callbacks(app):
    """Register all control and configuration callbacks"""

    # =========================================================================
    # SETTINGS PERSISTENCE CALLBACKS (SQLite Database)
    # =========================================================================

    # Save settings to database whenever any setting changes
    @app.callback(
        Output("settings-store", "data"),
        [Input("analyst-checklist", "value"),
         Input("analyst-checklist-2", "value"),
         Input("research-depth", "value"),
         Input("allow-shorts", "value"),
         Input("loop-enabled", "value"),
         Input("loop-interval", "value"),
         Input("market-hour-enabled", "value"),
         Input("market-hours-input", "value"),
         Input("trade-after-analyze", "value"),
         Input("trade-dollar-amount", "value"),
         Input("quick-llm", "value"),
         Input("deep-llm", "value")],
        State("settings-store", "data"),
        prevent_initial_call=True
    )
    def save_settings_to_db(analyst1, analyst2, depth, shorts, loop, interval,
                            market_hour, market_hours_input, trade_after, trade_amount,
                            quick_llm, deep_llm, current_data):
        """Save all settings to SQLite database whenever they change"""
        settings = {
            "analyst_checklist": analyst1 or [],
            "analyst_checklist_2": analyst2 or [],
            "research_depth": depth or "Shallow",
            "allow_shorts": shorts or False,
            "loop_enabled": loop or False,
            "loop_interval": interval or 60,
            "market_hour_enabled": market_hour or False,
            "market_hours_input": market_hours_input or "",
            "trade_after_analyze": trade_after or False,
            "trade_dollar_amount": trade_amount or 4500,
            "quick_llm": quick_llm or "gpt-4.1-nano",
            "deep_llm": deep_llm or "o4-mini",
        }
        # Save to SQLite database
        local_storage.save_settings(settings)
        return settings

    # Restore settings from database on page load
    @app.callback(
        [Output("analyst-checklist", "value"),
         Output("analyst-checklist-2", "value"),
         Output("research-depth", "value"),
         Output("allow-shorts", "value"),
         Output("loop-enabled", "value", allow_duplicate=True),
         Output("loop-interval", "value", allow_duplicate=True),
         Output("market-hour-enabled", "value", allow_duplicate=True),
         Output("market-hours-input", "value", allow_duplicate=True),
         Output("trade-after-analyze", "value"),
         Output("trade-dollar-amount", "value"),
         Output("quick-llm", "value"),
         Output("deep-llm", "value")],
        Input("settings-store", "modified_timestamp"),
        State("settings-store", "data"),
        prevent_initial_call=True
    )
    def restore_settings_from_db(ts, data):
        """Restore settings from SQLite database on page load"""
        # Load from database (not from dcc.Store)
        settings = local_storage.get_settings()

        return (
            settings.get("analyst_checklist", ["market", "options", "social"]),
            settings.get("analyst_checklist_2", ["news", "fundamentals", "macro"]),
            settings.get("research_depth", "Shallow"),
            settings.get("allow_shorts", False),
            settings.get("loop_enabled", False),
            settings.get("loop_interval", 60),
            settings.get("market_hour_enabled", False),
            settings.get("market_hours_input", ""),
            settings.get("trade_after_analyze", False),
            settings.get("trade_dollar_amount", 4500),
            settings.get("quick_llm", "gpt-4.1-nano"),
            settings.get("deep_llm", "o4-mini"),
        )

    # =========================================================================
    # RESEARCH DEPTH AND OTHER CALLBACKS
    # =========================================================================

    @app.callback(
        Output("research-depth-info", "children"),
        [Input("research-depth", "value")]
    )
    def update_research_depth_info(selected_depth):
        """Update the research depth information display based on selection"""
        if not selected_depth:
            return ""
        
        research_depth_info = {
            "Shallow": {
                "description": "Quick research, few debate and strategy discussion rounds",
                "settings": [
                    "max_debate_rounds: 1",
                    "max_risk_discuss_rounds: 1"
                ],
                "use_case": "Fast analysis when you need quick results and don't require extensive deliberation between agents",
                "header_color": "#17a2b8",  # info blue
                "bg_color": "#d1ecf1"
            },
            "Medium": {
                "description": "Middle ground, moderate debate rounds and strategy discussion",
                "settings": [
                    "max_debate_rounds: 3",
                    "max_risk_discuss_rounds: 3"
                ],
                "use_case": "Balanced approach providing reasonable depth while maintaining efficiency",
                "header_color": "#ffc107",  # warning yellow
                "bg_color": "#fff3cd"
            },
            "Deep": {
                "description": "Comprehensive research, in depth debate and strategy discussion",
                "settings": [
                    "max_debate_rounds: 5",
                    "max_risk_discuss_rounds: 5"
                ],
                "use_case": "Most thorough analysis with extensive agent debates and risk discussions",
                "header_color": "#28a745",  # success green
                "bg_color": "#d4edda"
            }
        }
        
        info = research_depth_info.get(selected_depth, {})
        if not info:
            return ""
        
        return dbc.Card([
            dbc.CardHeader([
                html.H6(f"{selected_depth} Mode", 
                       className="mb-0", 
                       style={"fontWeight": "bold", "color": "white"})
            ], style={"backgroundColor": info["header_color"], "border": "none"}),
            dbc.CardBody([
                html.P([
                    html.Strong("Description: ", style={"color": "black"}), 
                    html.Span(info["description"], style={"color": "black"})
                ], className="mb-2"),
                html.P([
                    html.Strong("Settings:", style={"color": "black"}),
                    html.Ul([
                        html.Li(setting, style={"color": "black"}) for setting in info["settings"]
                    ], className="mb-1")
                ], className="mb-2"),
                html.P([
                    html.Strong("Use Case: ", style={"color": "black"}),
                    html.Span(info["use_case"], style={"color": "black"})
                ], className="mb-0")
            ], style={"backgroundColor": info["bg_color"]})
        ])

    @app.callback(
        Output("market-hours-validation", "children"),
        [Input("market-hours-input", "value")]
    )
    def validate_market_hours_input(hours_input):
        """Validate market hours input and show validation message"""
        if not hours_input or not hours_input.strip():
            return ""

        from webui.utils.market_hours import validate_market_hours, format_time

        is_valid, times, error_msg = validate_market_hours(hours_input)

        if not is_valid:
            return html.Span([
                html.I(className="fas fa-times-circle me-1 text-danger"),
                html.Span(error_msg, className="text-danger small")
            ])
        else:
            # Format times for display
            formatted = [format_time(h, m) for h, m in times]

            return html.Span([
                html.I(className="fas fa-check-circle me-1 text-success"),
                html.Span(f"{', '.join(formatted)} EST", className="text-success small")
            ])

    @app.callback(
        [Output("loop-enabled", "value", allow_duplicate=True),
         Output("market-hour-enabled", "value", allow_duplicate=True),
         Output("loop-interval", "disabled"),
         Output("market-hours-input", "disabled")],
        [Input("loop-enabled", "value"),
         Input("market-hour-enabled", "value")],
        prevent_initial_call=True
    )
    def mutual_exclusive_scheduling_modes(loop_enabled, market_hour_enabled):
        """Ensure only one scheduling mode can be enabled at a time"""
        ctx = dash.callback_context
        if not ctx.triggered:
            return loop_enabled, market_hour_enabled, False, False
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == "loop-enabled" and loop_enabled:
            # Loop mode was enabled, disable market hour mode
            return True, False, False, True
        elif trigger_id == "market-hour-enabled" and market_hour_enabled:
            # Market hour mode was enabled, disable loop mode
            return False, True, True, False
        else:
            # Either mode was disabled, enable both inputs
            return loop_enabled, market_hour_enabled, not loop_enabled, not market_hour_enabled

    @app.callback(
        Output("scheduling-mode-info", "children"),
        [Input("loop-enabled", "value"),
         Input("loop-interval", "value"),
         Input("market-hour-enabled", "value"),
         Input("market-hours-input", "value")]
    )
    def update_scheduling_mode_info(loop_enabled, loop_interval, market_hour_enabled, market_hours_input):
        """Update the scheduling mode information display based on settings"""
        if market_hour_enabled:
            # Market Hour Mode
            from webui.utils.market_hours import validate_market_hours, format_market_hours_info

            if not market_hours_input or not market_hours_input.strip():
                return html.Small("Enter trading hours (EST)", className="text-muted")

            is_valid, hours, error_msg = validate_market_hours(market_hours_input)

            if not is_valid:
                return html.Small(error_msg, className="text-danger")

            # Valid market times
            times_info = format_market_hours_info(hours)

            next_executions = []
            for exec_info in times_info["next_executions"]:
                next_executions.append(f"{exec_info['formatted_time']}: {exec_info['next_formatted']}")

            return html.Div([
                html.Small([
                    html.I(className="fas fa-clock me-1"),
                    f"Next: {next_executions[0]}" if next_executions else "Waiting..."
                ], className="text-success")
            ])
        
        elif loop_enabled:
            # Loop Mode
            interval = loop_interval if loop_interval and loop_interval > 0 else 60
            
            return dbc.Card([
                dbc.CardHeader([
                    html.H6("Loop Mode Enabled", 
                           className="mb-0", 
                           style={"fontWeight": "bold", "color": "white"})
                ], style={"backgroundColor": "#fd7e14", "border": "none"}),
                dbc.CardBody([
                    html.P([
                        html.Strong("Description: ", style={"color": "black"}), 
                        html.Span(f"Analysis will run continuously, restarting every {interval} minutes", style={"color": "black"})
                    ], className="mb-2"),
                    html.P([
                        html.Strong("Behavior:", style={"color": "black"}),
                        html.Ul([
                            html.Li("Process all symbols sequentially", style={"color": "black"}),
                            html.Li(f"Wait {interval} minutes after completion", style={"color": "black"}),
                            html.Li("Clear previous results and restart analysis", style={"color": "black"}),
                            html.Li("Continue until manually stopped", style={"color": "black"})
                        ], className="mb-1")
                    ], className="mb-2"),
                    html.P([
                        html.Strong("Note: ", style={"color": "black"}),
                        html.Span("Use 'Stop Analysis' button to terminate the loop", style={"color": "black"})
                    ], className="mb-0")
                ], style={"backgroundColor": "#fff3cd"})
            ])
        
        else:
            # Single Run Mode
            return dbc.Card([
                dbc.CardHeader([
                    html.H6("Single Run Mode", 
                           className="mb-0", 
                           style={"fontWeight": "bold", "color": "white"})
                ], style={"backgroundColor": "#6c757d", "border": "none"}),
                dbc.CardBody([
                    html.P([
                        html.Strong("Description: ", style={"color": "black"}), 
                        html.Span("Analysis will run once for all symbols and then stop", style={"color": "black"})
                    ], className="mb-2"),
                    html.P([
                        html.Strong("Behavior:", style={"color": "black"}),
                        html.Ul([
                            html.Li("Process all symbols sequentially", style={"color": "black"}),
                            html.Li("Stop after completion", style={"color": "black"}),
                            html.Li("Manual restart required for new analysis", style={"color": "black"})
                        ], className="mb-1")
                    ], className="mb-0")
                ], style={"backgroundColor": "#f8f9fa"})
            ])

    @app.callback(
        Output("control-button-container", "children"),
        [Input("refresh-interval", "n_intervals")]
    )
    def update_control_button(n_intervals):
        """Update the control button (Start/Stop) based on current state"""
        if app_state.analysis_running or app_state.loop_enabled or app_state.market_hour_enabled:
            return dbc.Button(
                "Stop Analysis",
                id="control-btn",
                color="danger",
                size="lg",
                className="w-100 mt-2"
            )
        else:
            return dbc.Button(
                "Start Analysis",
                id="control-btn",
                color="primary",
                size="lg",
                className="w-100 mt-2"
            )

    @app.callback(
        Output("trading-mode-info", "children"),
        [Input("allow-shorts", "value")]
    )
    def update_trading_mode_info(allow_shorts):
        """Update the trading mode information display based on allow shorts selection"""
        if allow_shorts is None:
            return ""
        
        if allow_shorts:
            # Short selling enabled
            info = {
                "title": "Short Trading Enabled",
                "description": "The system can recommend both long and short positions",
                "details": [
                    "Can profit from both rising and falling markets",
                    "Increased trading opportunities",
                    "Higher risk and complexity",
                    "Requires margin account with broker"
                ],
                "note": "Short selling involves borrowing shares to sell, hoping to buy back at lower prices",
                "header_color": "#dc3545",  # danger red
                "bg_color": "#f8d7da"
            }
        else:
            # Long-only mode
            info = {
                "title": "Long-Only Mode",
                "description": "The system will only recommend long (buy) positions",
                "details": [
                    "Only profits from rising markets",
                    "Lower complexity and risk",
                    "No margin requirements",
                    "Suitable for conservative investors"
                ],
                "note": "Traditional buy-and-hold approach focusing on asset appreciation",
                "header_color": "#28a745",  # success green
                "bg_color": "#d4edda"
            }
        
        return dbc.Card([
            dbc.CardHeader([
                html.H6(info["title"], 
                       className="mb-0", 
                       style={"fontWeight": "bold", "color": "white"})
            ], style={"backgroundColor": info["header_color"], "border": "none"}),
            dbc.CardBody([
                html.P([
                    html.Strong("Description: ", style={"color": "black"}), 
                    html.Span(info["description"], style={"color": "black"})
                ], className="mb-2"),
                html.P([
                    html.Strong("Features:", style={"color": "black"}),
                    html.Ul([
                        html.Li(detail, style={"color": "black"}) for detail in info["details"]
                    ], className="mb-1")
                ], className="mb-2"),
                html.P([
                    html.Strong("Note: ", style={"color": "black"}),
                    html.Span(info["note"], style={"color": "black"})
                ], className="mb-0")
            ], style={"backgroundColor": info["bg_color"]})
        ])

    @app.callback(
        Output("trade-after-analyze-info", "children"),
        [Input("trade-after-analyze", "value"),
         Input("trade-dollar-amount", "value")]
    )
    def update_trade_after_analyze_info(trade_enabled, dollar_amount):
        """Update the trade after analyze information display"""
        if not trade_enabled:
            return dbc.Card([
                dbc.CardHeader([
                    html.H6("Manual Trading Mode", 
                           className="mb-0", 
                           style={"fontWeight": "bold", "color": "white"})
                ], style={"backgroundColor": "#6c757d", "border": "none"}),
                dbc.CardBody([
                    html.P([
                        html.Strong("Description: ", style={"color": "black"}), 
                        html.Span("Analysis results will be shown for manual review and trading decisions", style={"color": "black"})
                    ], className="mb-2"),
                    html.P([
                        html.Strong("Behavior:", style={"color": "black"}),
                        html.Ul([
                            html.Li("No automatic orders will be placed", style={"color": "black"}),
                            html.Li("Review analysis results manually", style={"color": "black"}),
                            html.Li("Execute trades manually through broker", style={"color": "black"})
                        ], className="mb-1")
                    ], className="mb-0")
                ], style={"backgroundColor": "#f8f9fa"})
            ])
        
        amount = dollar_amount if dollar_amount and dollar_amount > 0 else 1000
        
        return dbc.Card([
            dbc.CardHeader([
                html.H6("Automated Trading Enabled", 
                       className="mb-0", 
                       style={"fontWeight": "bold", "color": "white"})
            ], style={"backgroundColor": "#fd7e14", "border": "none"}),
            dbc.CardBody([
                html.P([
                    html.Strong("Description: ", style={"color": "black"}), 
                    html.Span(f"System will automatically execute trades with ${amount:.2f} per order", style={"color": "black"})
                ], className="mb-2"),
                html.P([
                    html.Strong("Behavior:", style={"color": "black"}),
                    html.Ul([
                        html.Li("Execute trades automatically after analysis", style={"color": "black"}),
                        html.Li("Use fractional shares based on dollar amount", style={"color": "black"}),
                        html.Li("Follow position management rules", style={"color": "black"}),
                        html.Li("All trades execute via Alpaca paper trading", style={"color": "black"})
                    ], className="mb-1")
                ], className="mb-2"),
                html.P([
                    html.Strong("Warning: ", style={"color": "black"}),
                    html.Span("Ensure Alpaca API keys are configured for paper trading", style={"color": "black"})
                ], className="mb-0")
            ], style={"backgroundColor": "#fff3cd"})
        ])

    # Major callback for analysis control
    @app.callback(
        [Output("result-text", "children", allow_duplicate=True),
         Output("app-store", "data"),
         Output("chart-pagination", "max_value", allow_duplicate=True),
         Output("chart-pagination", "active_page", allow_duplicate=True),
         Output("report-pagination", "max_value", allow_duplicate=True),
         Output("report-pagination", "active_page", allow_duplicate=True)],
        [Input("control-btn", "n_clicks"),
         Input("control-btn", "children")],
        [State("run-watchlist-store", "data"),
         State("analyst-checklist", "value"),
         State("analyst-checklist-2", "value"),
         State("research-depth", "value"),
         State("quick-llm", "value"),
         State("deep-llm", "value"),
         State("allow-shorts", "value"),
         State("loop-enabled", "value"),
         State("loop-interval", "value"),
         State("trade-after-analyze", "value"),
         State("trade-dollar-amount", "value"),
         State("market-hour-enabled", "value"),
         State("market-hours-input", "value")],
        prevent_initial_call=True
    )
    def on_control_button_click(n_clicks, button_children, run_watchlist_data, analyst_checklist_1, analyst_checklist_2,
                               research_depth, quick_llm, deep_llm,
                               allow_shorts, loop_enabled, loop_interval, trade_enabled, trade_amount,
                               market_hour_enabled, market_hours_input):
        # Parse selected analysts from checklists
        # Checklist 1: Market, Options, Social
        # Checklist 2: News, Fundamentals, Macro
        analyst_checklist_1 = analyst_checklist_1 or []
        analyst_checklist_2 = analyst_checklist_2 or []
        analysts_market = "market" in analyst_checklist_1
        analysts_options = "options" in analyst_checklist_1
        analysts_social = "social" in analyst_checklist_1
        analysts_news = "news" in analyst_checklist_2
        analysts_fundamentals = "fundamentals" in analyst_checklist_2
        analysts_macro = "macro" in analyst_checklist_2
        """Handle control button clicks"""
        # Detect which property triggered this callback
        triggered_prop = None
        if dash.callback_context.triggered:
            triggered_prop = dash.callback_context.triggered[0]['prop_id']

        # If the callback was invoked solely because the button *label* changed, ignore it
        if triggered_prop == "control-btn.children":
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

        # Ignore callbacks caused by the periodic re-rendering of the button itself
        if triggered_prop == "control-btn.n_clicks" and (n_clicks is None or n_clicks == 0):
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

        # Real user click handling begins here
        if n_clicks is None:
            return "", {}, 1, 1, 1, 1
        
        # Always use current/real-time data for analysis
        from datetime import datetime
        
        # Determine action based on current state
        is_stop_action = app_state.analysis_running or app_state.loop_enabled or app_state.market_hour_enabled
        
        # Handle stop action
        if is_stop_action:
            if app_state.loop_enabled:
                app_state.stop_loop_mode()
                return "Loop analysis stopped.", dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
            elif app_state.market_hour_enabled:
                app_state.stop_market_hour_mode()
                return "Market hour analysis stopped.", dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
            else:
                app_state.analysis_running = False
                return "Analysis stopped.", dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Handle start action
        if app_state.analysis_running:
            return "Analysis already in progress. Please wait.", dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Get symbols from Run Queue store (with database fallback)
        run_store = run_watchlist_data or {"symbols": []}
        symbols = run_store.get("symbols", [])

        # If store is empty, try loading directly from database as fallback
        # This handles race conditions where the store hasn't been populated yet
        if not symbols:
            db_data = local_storage.get_run_queue()
            symbols = db_data.get("symbols", [])
            print(f"[CONTROL] Loaded symbols from database fallback: {symbols}")

        if not symbols:
            return "No symbols in Portfolio. Add symbols from the Watchlist tab.", {}, 1, 1, 1, 1

        if not app_state.analysis_running:
            app_state.reset()

        # Store selected analysts for the status table (order matches UI: Market, Options, Social, News, Fundamentals, Macro)
        app_state.active_analysts = []
        if analysts_market: app_state.active_analysts.append("Market Analyst")
        if analysts_options: app_state.active_analysts.append("Options Analyst")
        if analysts_social: app_state.active_analysts.append("Social Analyst")
        if analysts_news: app_state.active_analysts.append("News Analyst")
        if analysts_fundamentals: app_state.active_analysts.append("Fundamentals Analyst")
        if analysts_macro: app_state.active_analysts.append("Macro Analyst")

        # Set loop configuration
        app_state.loop_interval_minutes = loop_interval if loop_interval and loop_interval > 0 else 60
        
        # Store trading configuration
        app_state.trade_enabled = trade_enabled
        app_state.trade_amount = trade_amount if trade_amount and trade_amount > 0 else 1000
        
        # Validate market hour configuration if enabled
        if market_hour_enabled:
            from webui.utils.market_hours import validate_market_hours
            is_valid, market_hours_list, error_msg = validate_market_hours(market_hours_input)
            if not is_valid:
                return f"Invalid market hours: {error_msg}", {}, 1, 1, 1, 1
        
        num_symbols = len(symbols)

        # Initialize symbol states IMMEDIATELY so pagination works right away
        for symbol in symbols:
            app_state.init_symbol_state(symbol)

        def analysis_thread():
            if market_hour_enabled:
                # Start market hour mode with scheduling logic
                market_hour_config = {
                    'analysts_market': analysts_market,
                    'analysts_social': analysts_social,
                    'analysts_news': analysts_news,
                    'analysts_fundamentals': analysts_fundamentals,
                    'analysts_macro': analysts_macro,
                    'analysts_options': analysts_options,
                    'research_depth': research_depth,
                    'allow_shorts': allow_shorts,
                    'quick_llm': quick_llm,
                    'deep_llm': deep_llm,
                    'trade_enabled': trade_enabled,
                    'trade_amount': trade_amount
                }
                app_state.start_market_hour_mode(symbols, market_hour_config, market_hours_list)
                
                # Market hour scheduling loop
                import datetime
                import pytz
                from webui.utils.market_hours import get_next_market_datetime, is_market_open

                # Track completed runs to avoid duplicates: set of (date, hour, minute)
                initial_run_done = False
                last_run_time = None
                next_time = None  # Will be (hour, minute) tuple

                while not app_state.stop_market_hour:
                    # Get current Eastern time
                    eastern = pytz.timezone('US/Eastern')
                    now_eastern = datetime.datetime.now(eastern)
                    current_hour = now_eastern.hour
                    current_minute = now_eastern.minute
                    current_date = now_eastern.date()

                    # Check if we should run immediately (first iteration, within a scheduled time window)
                    if not initial_run_done:
                        initial_run_done = True
                        # Check if current time has passed any scheduled time that hasn't run yet
                        current_time_mins = current_hour * 60 + current_minute
                        matching_time = None

                        for sched_hour, sched_minute in app_state.market_hours:
                            sched_time_mins = sched_hour * 60 + sched_minute
                            # If we're past the scheduled time (within the same hour), run it
                            if current_time_mins >= sched_time_mins and current_hour == sched_hour:
                                matching_time = (sched_hour, sched_minute)
                                break

                        if matching_time:
                            # Check if market is open
                            is_open, reason = is_market_open()
                            if is_open:
                                h, m = matching_time
                                print(f"[MARKET_HOUR] Currently past scheduled time {h}:{m:02d} - running immediately!")
                                last_run_time = (current_date, h, m)
                                next_time = matching_time

                                # Reset states for new analysis
                                app_state.reset_for_loop()

                                # Initialize symbol states
                                for symbol in symbols:
                                    app_state.init_symbol_state(symbol)

                                # Jump to analysis execution
                                goto_analysis = True
                            else:
                                print(f"[MARKET_HOUR] Within scheduled time but market closed: {reason}")
                                goto_analysis = False
                        else:
                            print(f"[MARKET_HOUR] Current time ({current_hour}:{current_minute:02d}) not matching any schedule")
                            goto_analysis = False
                    else:
                        goto_analysis = False

                    if not goto_analysis:
                        # Check if market is currently open before calculating next time
                        is_open_now, close_reason = is_market_open()
                        if not is_open_now:
                            # Market is closed - wait until next market day
                            if "closed at 4:00 PM" in close_reason or "Weekend" in close_reason:
                                # After hours or weekend - sleep longer, no spam
                                if not hasattr(app_state, '_last_closed_log') or time.time() - app_state._last_closed_log > 3600:
                                    print(f"[MARKET_HOUR] {close_reason}. Waiting for market to open...")
                                    app_state._last_closed_log = time.time()
                                time.sleep(300)  # Check every 5 minutes when market closed
                                continue

                        # Find next execution time
                        next_execution_times = []

                        for sched_time in app_state.market_hours:
                            next_dt = get_next_market_datetime(sched_time)
                            # Skip if we already ran this time today
                            if last_run_time == (next_dt.date(), sched_time[0], sched_time[1]):
                                continue
                            next_execution_times.append((sched_time, next_dt))

                        if not next_execution_times:
                            # All times for today have been executed, wait quietly
                            time.sleep(300)
                            continue

                        # Sort by next execution time
                        next_execution_times.sort(key=lambda x: x[1])
                        next_time, next_dt = next_execution_times[0]

                        h, m = next_time
                        # Only log if this is a new target time
                        log_key = f"{next_dt.date()}_{h}_{m}"
                        if not hasattr(app_state, '_last_next_log') or app_state._last_next_log != log_key:
                            print(f"[MARKET_HOUR] Next execution: {next_dt.strftime('%A, %B %d at %I:%M %p %Z')}")
                            app_state._last_next_log = log_key

                        # Wait until next execution time (compare in Eastern time)
                        now_eastern = datetime.datetime.now(eastern)
                        while now_eastern < next_dt and not app_state.stop_market_hour:
                            time.sleep(30)
                            now_eastern = datetime.datetime.now(eastern)

                        if app_state.stop_market_hour:
                            break

                        # Check if market is actually open at execution time
                        is_open, reason = is_market_open()
                        if not is_open:
                            # Mark as processed to avoid retrying
                            last_run_time = (next_dt.date(), next_time[0], next_time[1])
                            continue

                        # Track this run
                        last_run_time = (next_dt.date(), next_time[0], next_time[1])

                        # Reset states for new analysis
                        app_state.reset_for_loop()

                        # Initialize symbol states
                        for symbol in symbols:
                            app_state.init_symbol_state(symbol)

                    h, m = next_time
                    print(f"[MARKET_HOUR] Market is open, starting analysis at {h}:{m:02d}")
                    
                    # Reset states for new analysis
                    app_state.reset_for_loop()
                    
                    # Initialize symbol states
                    for symbol in symbols:
                        app_state.init_symbol_state(symbol)
                    
                    def analyze_single_ticker_market_hour(symbol, sched_time):
                        """Analyze a single ticker in market hour mode (for parallel execution)."""
                        try:
                            app_state.start_analyzing_symbol(symbol)
                            sh, sm = sched_time
                            print(f"[MARKET_HOUR-PARALLEL] Starting analysis for {symbol} at {sh}:{sm:02d}")
                            start_analysis(
                                symbol,
                                analysts_market, analysts_social, analysts_news, analysts_fundamentals, analysts_macro,
                                research_depth, allow_shorts, quick_llm, deep_llm, analysts_options
                            )
                            print(f"[MARKET_HOUR-PARALLEL] Completed analysis for {symbol}")
                            return symbol, True, None
                        except Exception as e:
                            print(f"[MARKET_HOUR-PARALLEL] Error analyzing {symbol}: {e}")
                            return symbol, False, str(e)
                        finally:
                            app_state.stop_analyzing_symbol(symbol)

                    # Run analysis for all symbols in parallel
                    print(f"[MARKET_HOUR] Starting parallel analysis at {h}:{m:02d}")
                    max_workers = min(get_max_parallel_tickers(), len(symbols))
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        futures = {executor.submit(analyze_single_ticker_market_hour, symbol, next_time): symbol for symbol in symbols}

                        for future in as_completed(futures):
                            if app_state.stop_market_hour:
                                break
                            symbol = futures[future]
                            try:
                                sym, success, error = future.result()
                                if success:
                                    print(f"[MARKET_HOUR] {sym} analysis completed")
                                else:
                                    print(f"[MARKET_HOUR] {sym} analysis failed: {error}")
                            except Exception as e:
                                print(f"[MARKET_HOUR] {symbol} raised exception: {e}")

                    if not app_state.stop_market_hour:
                        # Auto-save analysis after market hour analysis completes
                        try:
                            run_id = save_analysis_run(app_state, symbols)
                            if run_id:
                                print(f"[AUTO-SAVE] Market hour {h}:{m:02d} analysis saved: {run_id}")
                        except Exception as e:
                            print(f"[AUTO-SAVE] Error saving market hour analysis: {e}")

                        print(f"[MARKET_HOUR] Analysis completed for {h}:{m:02d}. Waiting for next execution time.")
            
            elif loop_enabled:
                # Start loop mode
                loop_config = {
                    'analysts_market': analysts_market,
                    'analysts_social': analysts_social,
                    'analysts_news': analysts_news,
                    'analysts_fundamentals': analysts_fundamentals,
                    'analysts_macro': analysts_macro,
                    'analysts_options': analysts_options,
                    'research_depth': research_depth,
                    'allow_shorts': allow_shorts,
                    'quick_llm': quick_llm,
                    'deep_llm': deep_llm,
                    'trade_enabled': trade_enabled,
                    'trade_amount': trade_amount
                }
                app_state.start_loop(symbols, loop_config)
                
                def analyze_single_ticker_loop(symbol):
                    """Analyze a single ticker in loop mode (for parallel execution)."""
                    try:
                        app_state.start_analyzing_symbol(symbol)
                        print(f"[LOOP-PARALLEL] Starting analysis for {symbol}")
                        start_analysis(
                            symbol,
                            analysts_market, analysts_social, analysts_news, analysts_fundamentals, analysts_macro,
                            research_depth, allow_shorts, quick_llm, deep_llm, analysts_options
                        )
                        print(f"[LOOP-PARALLEL] Completed analysis for {symbol}")
                        return symbol, True, None
                    except Exception as e:
                        print(f"[LOOP-PARALLEL] Error analyzing {symbol}: {e}")
                        return symbol, False, str(e)
                    finally:
                        app_state.stop_analyzing_symbol(symbol)

                loop_iteration = 1
                while not app_state.stop_loop:
                    print(f"[LOOP] Starting iteration {loop_iteration} with parallel execution")

                    # Run analysis for all symbols in parallel
                    max_workers = min(get_max_parallel_tickers(), len(symbols))
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        futures = {executor.submit(analyze_single_ticker_loop, symbol): symbol for symbol in symbols}

                        for future in as_completed(futures):
                            if app_state.stop_loop:
                                break
                            symbol = futures[future]
                            try:
                                sym, success, error = future.result()
                                if success:
                                    print(f"[LOOP] {sym} analysis completed")
                                else:
                                    print(f"[LOOP] {sym} analysis failed: {error}")
                            except Exception as e:
                                print(f"[LOOP] {symbol} raised exception: {e}")

                    if app_state.stop_loop:
                        break

                    # Auto-save analysis after each loop iteration
                    try:
                        run_id = save_analysis_run(app_state, symbols)
                        if run_id:
                            print(f"[AUTO-SAVE] Loop iteration {loop_iteration} saved: {run_id}")
                    except Exception as e:
                        print(f"[AUTO-SAVE] Error saving loop iteration: {e}")

                    print(f"[LOOP] Iteration {loop_iteration} completed. Waiting {app_state.loop_interval_minutes} minutes...")

                    # Calculate and store next run time in Eastern timezone
                    import datetime
                    import pytz
                    eastern = pytz.timezone('US/Eastern')
                    next_run = datetime.datetime.now(eastern) + datetime.timedelta(minutes=app_state.loop_interval_minutes)
                    app_state.next_loop_run_time = next_run
                    print(f"[LOOP] Next iteration scheduled at {next_run.strftime('%I:%M %p %Z')}")

                    # Wait for the specified interval (checking for stop every 30 seconds)
                    wait_time = app_state.loop_interval_minutes * 60  # Convert to seconds
                    elapsed = 0
                    while elapsed < wait_time and not app_state.stop_loop:
                        time.sleep(min(30, wait_time - elapsed))
                        elapsed += 30
                    
                    if not app_state.stop_loop:
                        # Reset analysis results for next iteration but keep states for pagination
                        app_state.reset_for_loop()
                        loop_iteration += 1
                
                print("[LOOP] Loop stopped")
            else:
                # Single run mode - parallel ticker execution
                print(f"[PARALLEL] Starting parallel analysis for {len(symbols)} symbols (max {get_max_parallel_tickers()} concurrent)")

                def analyze_single_ticker(symbol):
                    """Analyze a single ticker (for parallel execution)."""
                    try:
                        app_state.start_analyzing_symbol(symbol)
                        print(f"[PARALLEL] Starting analysis for {symbol}")
                        start_analysis(
                            symbol,
                            analysts_market, analysts_social, analysts_news, analysts_fundamentals, analysts_macro,
                            research_depth, allow_shorts, quick_llm, deep_llm, analysts_options
                        )
                        print(f"[PARALLEL] Completed analysis for {symbol}")
                        return symbol, True, None
                    except Exception as e:
                        print(f"[PARALLEL] Error analyzing {symbol}: {e}")
                        import traceback
                        traceback.print_exc()
                        return symbol, False, str(e)
                    finally:
                        app_state.stop_analyzing_symbol(symbol)

                # Execute all tickers in parallel with limited concurrency
                max_workers = min(get_max_parallel_tickers(), len(symbols))
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {executor.submit(analyze_single_ticker, symbol): symbol for symbol in symbols}

                    for future in as_completed(futures):
                        symbol = futures[future]
                        try:
                            sym, success, error = future.result()
                            if success:
                                print(f"[PARALLEL] {sym} analysis completed successfully")
                            else:
                                print(f"[PARALLEL] {sym} analysis failed: {error}")
                        except Exception as e:
                            print(f"[PARALLEL] {symbol} analysis raised exception: {e}")

                # Auto-save analysis after single run completes
                try:
                    run_id = save_analysis_run(app_state, symbols)
                    if run_id:
                        print(f"[AUTO-SAVE] Analysis saved: {run_id}")
                    else:
                        print("[AUTO-SAVE] No data to save or save failed")
                except Exception as e:
                    print(f"[AUTO-SAVE] Error saving analysis: {e}")

            app_state.analysis_running = False

        if not app_state.analysis_running:
            app_state.analysis_running = True
            thread = threading.Thread(target=analysis_thread)
            thread.start()
        
        if market_hour_enabled:
            mode_text = "market hour mode"
            # Format times for display
            from webui.utils.market_hours import format_time
            formatted_times = [format_time(h, m) for h, m in market_hours_list]
            interval_text = f" (at {' and '.join(formatted_times)} EST)"
        elif loop_enabled:
            mode_text = "loop mode"
            interval_text = f" (every {app_state.loop_interval_minutes} minutes)"
        else:
            mode_text = "single run mode"
            interval_text = ""
        
        # Store symbols and pagination data in app-store for page refresh recovery
        store_data = {
            "analysis_started": True, 
            "timestamp": time.time(),
            "symbols": symbols,  # Store the symbols list
            "num_symbols": num_symbols,  # Store the count
            "mode": mode_text,
            "interval_text": interval_text
        }
        
        return f"Starting real-time analysis for {', '.join(symbols)} in {mode_text}{interval_text} using current market data...", store_data, num_symbols, 1, num_symbols, 1

    @app.callback(
        [Output("chart-pagination", "max_value", allow_duplicate=True),
         Output("chart-pagination", "active_page", allow_duplicate=True), 
         Output("report-pagination", "max_value", allow_duplicate=True),
         Output("report-pagination", "active_page", allow_duplicate=True)],
        [Input("app-store", "data")],
        prevent_initial_call=True
    )
    def restore_pagination_on_refresh(store_data):
        """Restore pagination and symbol states after page refresh"""
        if not store_data or not store_data.get("symbols"):
            # No stored data, return defaults
            print("[RESTORE] No stored data found, returning defaults")
            return 1, 1, 1, 1
        
        symbols = store_data.get("symbols", [])
        num_symbols = len(symbols)
        
        # Restore symbol states if they don't exist (e.g., after page refresh)
        if not app_state.symbol_states or len(app_state.symbol_states) != num_symbols:
            print(f"[RESTORE] Restoring symbol states for {symbols} after page refresh")
            for symbol in symbols:
                if symbol not in app_state.symbol_states:
                    app_state.init_symbol_state(symbol)
            
            # Set current symbol to first one if none is set
            if not app_state.current_symbol and symbols:
                app_state.current_symbol = symbols[0]
                print(f"[RESTORE] Set current symbol to {symbols[0]}")
        else:
            print(f"[RESTORE] Symbol states already exist for {list(app_state.symbol_states.keys())}")
        
        print(f"[RESTORE] Restoring pagination: max_value={num_symbols}")
        return num_symbols, 1, num_symbols, 1
    
    @app.callback(
        Output("result-text", "children", allow_duplicate=True),
        [Input("app-store", "data")],
        prevent_initial_call=True
    )
    def restore_analysis_status_on_refresh(store_data):
        """Restore analysis status text after page refresh"""
        if not store_data or not store_data.get("analysis_started"):
            return ""
        
        symbols = store_data.get("symbols", [])
        mode = store_data.get("mode", "mode")
        interval_text = store_data.get("interval_text", "")
        
        if symbols:
            return f"📄 Page refreshed - Analysis data for {', '.join(symbols)} has been restored ({mode}{interval_text}). All symbol pages should now be available."
        
        return "" 