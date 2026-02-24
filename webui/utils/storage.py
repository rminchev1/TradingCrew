"""
Storage utility for persisting user settings in localStorage
"""

import json
from typing import Dict, Any

# Default settings structure for trading panel
# Note: ticker_input removed - Run Queue is now persisted via run-watchlist-store
DEFAULT_SETTINGS = {
    "analyst_market": True,
    "analyst_options": True,
    "analyst_social": True,
    "analyst_news": True,
    "analyst_fundamentals": True,
    "analyst_macro": True,
    "research_depth": "Shallow",
    "allow_shorts": False,
    "loop_enabled": False,
    "loop_interval": 60,
    "market_hour_enabled": False,
    "market_hours_input": "",
    "trade_after_analyze": False,
    "trade_dollar_amount": 4500,
    "quick_llm": "gpt-4.1-nano",
    "deep_llm": "o4-mini"
}

# Default system settings structure
DEFAULT_SYSTEM_SETTINGS = {
    # API Keys (None = use env var, value = override env var)
    "openai_api_key": None,
    "alpaca_api_key": None,
    "alpaca_secret_key": None,
    "alpaca_use_paper": "True",
    "finnhub_api_key": None,
    "fred_api_key": None,
    "coindesk_api_key": None,
    # Reddit API
    "reddit_client_id": None,
    "reddit_client_secret": None,
    "reddit_user_agent": "TradingCrew/1.0",
    # LLM Models
    "deep_think_llm": "o4-mini",
    "quick_think_llm": "gpt-4.1-nano",
    # Analysis Settings
    "max_debate_rounds": 4,
    "max_risk_discuss_rounds": 3,
    "parallel_analysts": True,
    "online_tools": True,
    "max_recur_limit": 200,
    "max_parallel_tickers": 3,
    # Rate Limiting / Throughput Control
    "ticker_cooldown_seconds": 10,  # Delay after each ticker completes (rate limit protection)
    "llm_max_retries": 6,  # Max retries for LLM API calls (with exponential backoff)
    # Scanner Settings
    "scanner_num_results": 20,
    "scanner_use_llm_sentiment": False,
    "scanner_use_options_flow": True,
    "scanner_cache_ttl": 300,
    "scanner_dynamic_universe": True,
    # Options Trading Settings
    "enable_options_trading": False,
    "options_trading_level": 2,
    "options_max_contracts": 10,
    "options_max_position_value": 5000,
    "options_min_dte": 7,
    "options_max_dte": 45,
    "options_min_delta": 0.20,
    "options_max_delta": 0.70,
    "options_min_open_interest": 100,
    # Risk Guardrails (pre-execution validation)
    "risk_guardrails_enabled": False,
    "risk_max_per_trade_pct": 3.0,
    "risk_max_single_position_pct": 8.0,
    "risk_max_total_exposure_pct": 15.0,
    # Stop-Loss and Take-Profit Settings
    "enable_stop_loss": False,
    "stop_loss_percentage": 5.0,
    "stop_loss_use_ai": True,
    "enable_take_profit": False,
    "take_profit_percentage": 10.0,
    "take_profit_use_ai": True,
    # Dashboard Panel Visibility
    "show_panel_account_bar": True,
    "show_panel_scanner": True,
    "show_panel_watchlist": True,
    "show_panel_chart": True,
    "show_panel_trading": True,
    "show_panel_positions": True,
    "show_panel_options": True,
    "show_panel_portfolio": True,
    "show_panel_reports": True,
    "show_panel_logs": True,
}


def get_default_settings() -> Dict[str, Any]:
    """Get the default settings structure"""
    return DEFAULT_SETTINGS.copy()


def get_default_system_settings() -> Dict[str, Any]:
    """Get the default system settings structure"""
    return DEFAULT_SYSTEM_SETTINGS.copy()


def export_settings(settings: dict) -> str:
    """Export settings to JSON string (excludes API keys for security)."""
    # Filter out sensitive keys
    safe_keys = [
        "deep_think_llm",
        "quick_think_llm",
        "max_debate_rounds",
        "max_risk_discuss_rounds",
        "parallel_analysts",
        "online_tools",
        "max_recur_limit",
        "max_parallel_tickers",
        "ticker_cooldown_seconds",
        "llm_max_retries",
        "scanner_num_results",
        "scanner_use_llm_sentiment",
        "scanner_use_options_flow",
        "scanner_cache_ttl",
        "scanner_dynamic_universe",
        "alpaca_use_paper",  # Include paper mode (not sensitive)
        # Options trading settings (not sensitive)
        "enable_options_trading",
        "options_trading_level",
        "options_max_contracts",
        "options_max_position_value",
        "options_min_dte",
        "options_max_dte",
        "options_min_delta",
        "options_max_delta",
        "options_min_open_interest",
        # Risk Guardrails (not sensitive)
        "risk_guardrails_enabled",
        "risk_max_per_trade_pct",
        "risk_max_single_position_pct",
        "risk_max_total_exposure_pct",
        # Stop-Loss and Take-Profit settings (not sensitive)
        "enable_stop_loss",
        "stop_loss_percentage",
        "stop_loss_use_ai",
        "enable_take_profit",
        "take_profit_percentage",
        "take_profit_use_ai",
        # Dashboard Panel Visibility (not sensitive)
        "show_panel_account_bar",
        "show_panel_scanner",
        "show_panel_watchlist",
        "show_panel_chart",
        "show_panel_trading",
        "show_panel_positions",
        "show_panel_options",
        "show_panel_portfolio",
        "show_panel_reports",
        "show_panel_logs",
    ]
    safe_settings = {k: v for k, v in settings.items() if k in safe_keys}
    return json.dumps(safe_settings, indent=2)


def import_settings(json_str: str) -> dict:
    """Import settings from JSON string."""
    return json.loads(json_str)


def create_storage_store_component():
    """Create a dcc.Store component for localStorage persistence"""
    from dash import dcc
    return dcc.Store(id='settings-store', storage_type='local', data=DEFAULT_SETTINGS)
