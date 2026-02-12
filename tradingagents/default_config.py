import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    # "data_dir": "/Users/yluo/Documents/Code/ScAI/FR1-data",
    "data_dir": "data/ScAI/FR1-data",
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # LLM settings
    "deep_think_llm": "o4-mini",
    "quick_think_llm": "gpt-4.1-nano",
    # Debate and discussion settings
    "max_debate_rounds": 4,
    "max_risk_discuss_rounds": 3,
    "max_recur_limit": 200,
    # Trading settings
    "allow_shorts": False,  # False = Investment mode (BUY/HOLD/SELL), True = Trading mode (LONG/NEUTRAL/SHORT)
    # Execution settings
    "parallel_analysts": True,  # True = Run analysts in parallel for faster execution, False = Sequential execution
    # Tool settings
    "online_tools": True,
    # API keys (these will be overridden by environment variables if present)
    "openai_api_key": None,
    "finnhub_api_key": None,
    "alpaca_api_key": None,
    "alpaca_secret_key": None,
    "alpaca_use_paper": "True",  # Set to "True" to use paper trading, "False" for live trading
    "coindesk_api_key": None,
    # Scanner settings
    "scanner_num_results": 20,  # Number of top stocks to return from scanner
    "scanner_use_llm_sentiment": False,  # Use GPT-4o-mini for news sentiment (more accurate but costs money)
    "scanner_use_options_flow": True,  # Include options flow analysis in scanner
    "scanner_cache_ttl": 300,  # Cache TTL in seconds (5 minutes default)
    "scanner_dynamic_universe": True,  # True = top 200 liquid stocks from Alpaca, False = predefined ~100 stocks
    # Options Trading settings
    "enable_options_trading": False,  # Master switch for options trading mode
    "options_trading_level": 2,  # Alpaca options tier: 1=covered, 2=buy calls/puts, 3=spreads
    "options_max_contracts": 10,  # Maximum contracts per trade
    "options_max_position_value": 5000,  # Maximum $ value in options positions
    "options_min_dte": 7,  # Minimum days to expiration
    "options_max_dte": 45,  # Maximum days to expiration
    "options_min_delta": 0.20,  # Minimum delta for entries
    "options_max_delta": 0.70,  # Maximum delta for entries
    "options_min_open_interest": 100,  # Minimum open interest for liquidity
    # Stop-Loss and Take-Profit Settings
    "enable_stop_loss": False,  # Enable automatic stop-loss orders
    "stop_loss_percentage": 5.0,  # Default SL % below entry (for BUY) or above (for SHORT)
    "stop_loss_use_ai": True,  # Use AI-recommended SL levels vs fixed percentage
    "enable_take_profit": False,  # Enable automatic take-profit orders
    "take_profit_percentage": 10.0,  # Default TP % above entry (for BUY) or below (for SHORT)
    "take_profit_use_ai": True,  # Use AI-recommended TP levels vs fixed percentage
}
