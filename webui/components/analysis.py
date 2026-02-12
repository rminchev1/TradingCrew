"""
webui/components/analysis.py
"""

import time
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.dataflows.alpaca_utils import AlpacaUtils
from tradingagents.agents.utils.agent_trading_modes import extract_recommendation
from webui.utils.state import app_state
from webui.utils.charts import create_chart


def execute_trade_after_analysis(ticker, allow_shorts, trade_amount):
    """Execute trade based on analysis results"""
    try:
        print(f"[TRADE] Starting trade execution for {ticker}")

        # Get the current state for this symbol
        state = app_state.get_state(ticker)
        if not state:
            print(f"[TRADE] No state found for {ticker}, skipping trade execution")
            return

        if not state.get("analysis_complete"):
            print(f"[TRADE] Analysis not complete for {ticker}, skipping trade execution")
            print(f"[TRADE] Analysis status: {state.get('analysis_complete', 'Unknown')}")
            return

        print(f"[TRADE] Analysis complete for {ticker}, checking for recommended action")

        # Get the recommended action
        recommended_action = state.get("recommended_action")
        print(f"[TRADE] Direct recommended_action: {recommended_action}")

        if not recommended_action:
            # Try to extract from final trade decision
            final_decision = state["current_reports"].get("final_trade_decision")
            print(f"[TRADE] Final decision available: {bool(final_decision)}")
            if final_decision:
                trading_mode = "trading" if allow_shorts else "investment"
                print(f"[TRADE] Extracting recommendation using mode: {trading_mode}")
                recommended_action = extract_recommendation(final_decision, trading_mode)
                print(f"[TRADE] Extracted recommendation: {recommended_action}")

        if not recommended_action:
            print(f"[TRADE] No recommended action found for {ticker}, skipping trade execution")
            print(f"[TRADE] Available reports: {list(state['current_reports'].keys())}")
            return

        print(f"[TRADE] Executing trade for {ticker}: {recommended_action} with ${trade_amount}")

        # Get current position
        current_position = AlpacaUtils.get_current_position_state(ticker)
        print(f"[TRADE] Current position for {ticker}: {current_position}")

        # Build SL/TP configuration from system settings
        system_settings = app_state.system_settings
        sl_tp_config = {
            "enable_stop_loss": system_settings.get("enable_stop_loss", False),
            "stop_loss_percentage": system_settings.get("stop_loss_percentage", 5.0),
            "stop_loss_use_ai": system_settings.get("stop_loss_use_ai", True),
            "enable_take_profit": system_settings.get("enable_take_profit", False),
            "take_profit_percentage": system_settings.get("take_profit_percentage", 10.0),
            "take_profit_use_ai": system_settings.get("take_profit_use_ai", True),
        }

        # Log SL/TP config
        sl_enabled = sl_tp_config["enable_stop_loss"]
        tp_enabled = sl_tp_config["enable_take_profit"]
        if sl_enabled or tp_enabled:
            print(f"[TRADE] SL/TP enabled - SL: {sl_enabled} ({sl_tp_config['stop_loss_percentage']}%), TP: {tp_enabled} ({sl_tp_config['take_profit_percentage']}%)")
            print(f"[TRADE] AI levels - SL: {sl_tp_config['stop_loss_use_ai']}, TP: {sl_tp_config['take_profit_use_ai']}")

        # Get trader analysis text for AI SL/TP extraction
        trader_analysis = state["current_reports"].get("trader_investment_plan", "")

        # Execute the trading action with SL/TP support
        result = AlpacaUtils.execute_trading_action(
            symbol=ticker,
            current_position=current_position,
            signal=recommended_action,
            dollar_amount=trade_amount,
            allow_shorts=allow_shorts,
            sl_tp_config=sl_tp_config,
            analysis_text=trader_analysis
        )
        
        # Check individual action results and provide detailed feedback
        successful_actions = []
        failed_actions = []
        
        for action_result in result.get("actions", []):
            if "result" in action_result:
                action_info = action_result["result"]
                if action_info.get("success"):
                    successful_actions.append(f"{action_result['action']}: {action_info.get('message', 'Success')}")
                else:
                    failed_actions.append(f"{action_result['action']} failed: {action_info.get('error', 'Unknown error')}")
            else:
                successful_actions.append(f"{action_result['action']}: {action_result.get('message', 'Action completed')}")
        
        # Print results based on overall success
        if result.get("success"):
            print(f"[TRADE] Successfully executed trading actions for {ticker}")
            for success in successful_actions:
                print(f"[TRADE] {success}")
            
            # Store trading results in state for UI display
            state["trading_results"] = result
            
            # Signal that a trade occurred to trigger Alpaca data refresh
            app_state.signal_trade_occurred()
        else:
            print(f"[TRADE] Trading execution failed for {ticker}")
            for success in successful_actions:
                print(f"[TRADE] {success}")
            for failure in failed_actions:
                print(f"[TRADE] {failure}")
            
            # Store error information
            state["trading_results"] = {"error": "One or more trading actions failed", "details": failed_actions}
            
    except Exception as e:
        print(f"[TRADE] Error executing trade for {ticker}: {e}")
        import traceback
        traceback.print_exc()
        state = app_state.get_state(ticker)
        if state:
            state["trading_results"] = {"error": f"Trading execution error: {str(e)}"}


def merge_system_settings_into_config(config):
    """Merge system settings from AppState into the config dict.

    System settings from the UI take precedence over defaults.
    Environment variables are checked as fallback for API keys.
    """
    import os
    system_settings = app_state.system_settings

    # LLM Models (UI values override defaults)
    if system_settings.get("deep_think_llm"):
        config["deep_think_llm"] = system_settings["deep_think_llm"]
    if system_settings.get("quick_think_llm"):
        config["quick_think_llm"] = system_settings["quick_think_llm"]

    # Analysis settings
    if system_settings.get("max_debate_rounds"):
        config["max_debate_rounds"] = system_settings["max_debate_rounds"]
    if system_settings.get("max_risk_discuss_rounds"):
        config["max_risk_discuss_rounds"] = system_settings["max_risk_discuss_rounds"]
    if "parallel_analysts" in system_settings:
        config["parallel_analysts"] = system_settings["parallel_analysts"]
    if "online_tools" in system_settings:
        config["online_tools"] = system_settings["online_tools"]
    if system_settings.get("max_recur_limit"):
        config["max_recur_limit"] = system_settings["max_recur_limit"]

    # Scanner settings
    if system_settings.get("scanner_num_results"):
        config["scanner_num_results"] = system_settings["scanner_num_results"]
    if "scanner_use_llm_sentiment" in system_settings:
        config["scanner_use_llm_sentiment"] = system_settings["scanner_use_llm_sentiment"]
    if "scanner_use_options_flow" in system_settings:
        config["scanner_use_options_flow"] = system_settings["scanner_use_options_flow"]
    if system_settings.get("scanner_cache_ttl"):
        config["scanner_cache_ttl"] = system_settings["scanner_cache_ttl"]
    if "scanner_dynamic_universe" in system_settings:
        config["scanner_dynamic_universe"] = system_settings["scanner_dynamic_universe"]

    # API Keys: UI value > env var > None
    # OpenAI
    openai_key = system_settings.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
    if openai_key:
        config["openai_api_key"] = openai_key

    # Alpaca
    alpaca_key = system_settings.get("alpaca_api_key") or os.getenv("ALPACA_API_KEY")
    alpaca_secret = system_settings.get("alpaca_secret_key") or os.getenv("ALPACA_SECRET_KEY")
    alpaca_paper = system_settings.get("alpaca_use_paper", os.getenv("ALPACA_USE_PAPER", "True"))
    if alpaca_key:
        config["alpaca_api_key"] = alpaca_key
    if alpaca_secret:
        config["alpaca_secret_key"] = alpaca_secret
    config["alpaca_use_paper"] = alpaca_paper

    # Finnhub
    finnhub_key = system_settings.get("finnhub_api_key") or os.getenv("FINNHUB_API_KEY")
    if finnhub_key:
        config["finnhub_api_key"] = finnhub_key

    # FRED
    fred_key = system_settings.get("fred_api_key") or os.getenv("FRED_API_KEY")
    if fred_key:
        config["fred_api_key"] = fred_key

    # CoinDesk
    coindesk_key = system_settings.get("coindesk_api_key") or os.getenv("COINDESK_API_KEY")
    if coindesk_key:
        config["coindesk_api_key"] = coindesk_key

    return config


def run_analysis(ticker, selected_analysts, research_depth, allow_shorts, quick_llm, deep_llm, progress=None):
    """Run the trading analysis using current/real-time data"""
    try:
        # Always use current date for real-time analysis
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d")

        print(f"Starting real-time analysis for {ticker} with current date: {current_date}")
        current_state = app_state.get_state(ticker)
        if not current_state:
            print(f"Error: No state found for {ticker}")
            return
        current_state["analysis_running"] = True
        current_state["analysis_complete"] = False

        # Create config with selected options
        config = DEFAULT_CONFIG.copy()

        # Merge system settings from UI (API keys, LLM models, etc.)
        config = merge_system_settings_into_config(config)

        # Override with function parameters (these come from the trading panel)
        config["max_debate_rounds"] = research_depth
        config["max_risk_discuss_rounds"] = research_depth
        config["allow_shorts"] = allow_shorts
        config["parallel_analysts"] = False  # Sequential analysts for proper report updates (tickers still run in parallel)
        config["quick_think_llm"] = quick_llm
        config["deep_think_llm"] = deep_llm
        
        # Initialize TradingAgentsGraph
        print(f"[ANALYSIS] Initializing TradingAgentsGraph with analysts: {selected_analysts}")
        print(f"[ANALYSIS] Config: quick_llm={config.get('quick_think_llm')}, deep_llm={config.get('deep_think_llm')}")
        print(f"[ANALYSIS] API keys configured: openai={bool(config.get('openai_api_key'))}, finnhub={bool(config.get('finnhub_api_key'))}")
        graph = TradingAgentsGraph(selected_analysts, config=config, debug=True)
        print(f"[ANALYSIS] TradingAgentsGraph initialized successfully")
        
        # Status updates are now handled in the parallel execution coordinator
        
        # Force an initial UI update
        app_state.needs_ui_update = True
        
        # Run analysis with tracing using current date
        print(f"Starting graph stream for {ticker} with current market data")
        trace = []
        for chunk in graph.graph.stream(
            graph.propagator.create_initial_state(ticker, current_date),
            stream_mode="values",
            config={"recursion_limit": 100}
        ):
            # Track progress
            trace.append(chunk)

            # Process intermediate results - pass explicit symbol for thread-safety in parallel execution
            app_state.process_chunk_updates(chunk, symbol=ticker)

            app_state.needs_ui_update = True
            
            # Update progress bar if provided
            if progress is not None:
                # Simulate progress based on steps completed
                completed_agents = sum(1 for status in current_state["agent_statuses"].values() if status == "completed")
                total_agents = len(current_state["agent_statuses"])
                if total_agents > 0:
                    progress(completed_agents / total_agents)
            
            # Small delay to prevent UI lag
            time.sleep(0.1)
        
        # Extract final results
        final_state = trace[-1]
        decision = graph.process_signal(final_state["final_trade_decision"])
        
        # NEW: Persist the extracted decision so the trading engine can act on it directly
        current_state["recommended_action"] = decision

        # Mark all agents as completed - pass explicit symbol for thread-safety
        for agent in current_state["agent_statuses"]:
            app_state.update_agent_status(agent, "completed", symbol=ticker)
        
        # Set final results
        current_state["analysis_results"] = {
            "ticker": ticker,
            "date": current_date,
            "decision": decision,
            "full_state": final_state,
        }
        
        # Use real chart data with current date (no end_date means most recent data)
        current_state["chart_data"] = create_chart(ticker, period="1y", end_date=None)
        
        current_state["analysis_complete"] = True
        
        # Execute trade if enabled
        trade_enabled = getattr(app_state, 'trade_enabled', False)
        trade_amount = getattr(app_state, 'trade_amount', 1000)
        print(f"[TRADE] Checking trading settings for {ticker}:")
        print(f"[TRADE]   - trade_enabled: {trade_enabled}")
        print(f"[TRADE]   - trade_amount: {trade_amount}")
        print(f"[TRADE]   - allow_shorts: {allow_shorts}")
        
        if trade_enabled:
            print(f"[TRADE] Trading enabled for {ticker}, executing trade with ${trade_amount}")
            execute_trade_after_analysis(ticker, allow_shorts, trade_amount)
        else:
            print(f"[TRADE] Trading disabled for {ticker}, skipping trade execution")
        
        # Final UI update to show completion
        app_state.needs_ui_update = True
        
    except Exception as e:
        print(f"[ANALYSIS ERROR] Analysis failed for {ticker}: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        # Store error in state so UI can display it
        if current_state:
            current_state["current_reports"]["error"] = f"Analysis failed: {type(e).__name__}: {str(e)}"
            current_state["analysis_complete"] = True  # Mark complete so UI updates
        if progress is not None:
            progress(1.0)  # Complete the progress bar
    finally:
        # Mark analysis as no longer running
        print(f"[ANALYSIS] Real-time analysis for {ticker} finished (success={current_state.get('analysis_complete', False) if current_state else False})")
        if current_state:
            current_state["analysis_running"] = False
        
    return "Real-time analysis complete"


def start_analysis(ticker, analysts_market, analysts_social, analysts_news, analysts_fundamentals, analysts_macro,
                 research_depth, allow_shorts, quick_llm, deep_llm, analysts_options=False, progress=None):
    """Start real-time analysis function for the UI"""

    # Debug: Log which analysts are enabled
    print(f"[ANALYSIS] Starting analysis for {ticker}")
    print(f"[ANALYSIS] Analyst flags: market={analysts_market}, options={analysts_options}, social={analysts_social}, news={analysts_news}, fundamentals={analysts_fundamentals}, macro={analysts_macro}")

    # Parse selected analysts - order matches UI layout (Market, Options, Social, News, Fundamentals, Macro)
    selected_analysts = []
    if analysts_market:
        selected_analysts.append("market")
    if analysts_options:
        selected_analysts.append("options")
    if analysts_social:
        selected_analysts.append("social")
    if analysts_news:
        selected_analysts.append("news")
    if analysts_fundamentals:
        selected_analysts.append("fundamentals")
    if analysts_macro:
        selected_analysts.append("macro")

    print(f"[ANALYSIS] Selected analysts: {selected_analysts}")
    
    if not selected_analysts:
        return "Please select at least one analyst type."
    
    # Convert research depth to integer to match UI display values
    if research_depth == "Shallow":
        depth = 1
    elif research_depth == "Medium":
        depth = 3
    else:  # Deep
        depth = 5
        
    # Create an initial chart immediately with current data
    # Add small random delay to stagger API calls in parallel execution
    import random
    time.sleep(random.uniform(0.1, 0.5))

    try:
        print(f"Creating initial chart for {ticker} with current market data")
        current_state = app_state.get_state(ticker)
        if current_state:
            current_state["chart_data"] = create_chart(ticker, period="1y", end_date=None)
    except Exception as e:
        print(f"Error creating initial chart: {e}")
        import traceback
        traceback.print_exc()
    
    # Run analysis with current data
    run_analysis(ticker, selected_analysts, depth, allow_shorts, quick_llm, deep_llm, progress)
    
    # Update the status message with more details
    trading_mode = "Trading Mode (LONG/NEUTRAL/SHORT)" if allow_shorts else "Investment Mode (BUY/HOLD/SELL)"
    trade_text = f" with ${getattr(app_state, 'trade_amount', 1000)} auto-trading" if getattr(app_state, 'trade_enabled', False) else ""
    return f"Real-time analysis started for {ticker} with {len(selected_analysts)} analysts in {trading_mode}{trade_text} using sequential execution and current market data. Status table will update automatically." 