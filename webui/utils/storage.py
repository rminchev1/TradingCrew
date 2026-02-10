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
    # Scanner Settings
    "scanner_num_results": 20,
    "scanner_use_llm_sentiment": False,
    "scanner_use_options_flow": True,
    "scanner_cache_ttl": 300,
    "scanner_dynamic_universe": True,
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
        "scanner_num_results",
        "scanner_use_llm_sentiment",
        "scanner_use_options_flow",
        "scanner_cache_ttl",
        "scanner_dynamic_universe",
        "alpaca_use_paper",  # Include paper mode (not sensitive)
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
