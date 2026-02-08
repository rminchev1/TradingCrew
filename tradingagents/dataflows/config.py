# -------------------------------- config.py -----------------------
import tradingagents.default_config as default_config
from typing import Dict, Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# =============================================================================
# API Key Validation Functions
# =============================================================================

def validate_openai_key(api_key: str) -> bool:
    """Test OpenAI API key validity by listing models."""
    if not api_key:
        return False
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        # Try to list models - minimal API call
        client.models.list()
        return True
    except Exception:
        return False


def validate_alpaca_keys(api_key: str, secret_key: str, paper: bool = True) -> bool:
    """Test Alpaca API credentials by fetching account info."""
    if not api_key or not secret_key:
        return False
    try:
        from alpaca.trading.client import TradingClient
        client = TradingClient(api_key, secret_key, paper=paper)
        client.get_account()
        return True
    except Exception:
        return False


def validate_finnhub_key(api_key: str) -> bool:
    """Test Finnhub API key by fetching a company profile."""
    if not api_key:
        return False
    try:
        import finnhub
        client = finnhub.Client(api_key=api_key)
        # Try to get AAPL profile - minimal API call
        result = client.company_profile2(symbol='AAPL')
        return bool(result)
    except Exception:
        return False


def validate_fred_key(api_key: str) -> bool:
    """Test FRED API key by fetching a series."""
    if not api_key:
        return False
    try:
        import requests
        # Try to fetch GDP series info - minimal API call
        url = f"https://api.stlouisfed.org/fred/series?series_id=GDP&api_key={api_key}&file_type=json"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return "seriess" in data
        return False
    except Exception:
        return False

# Use default config but allow it to be overridden
_config: Optional[Dict] = None
DATA_DIR: Optional[str] = None


def initialize_config():
    """Initialize the configuration with default values."""
    global _config, DATA_DIR
    if _config is None:
        _config = default_config.DEFAULT_CONFIG.copy()
        DATA_DIR = _config["data_dir"]


def set_config(config: Dict):
    """Update the configuration with custom values."""
    global _config, DATA_DIR
    if _config is None:
        _config = default_config.DEFAULT_CONFIG.copy()
    _config.update(config)
    DATA_DIR = _config["data_dir"]


def get_config() -> Dict:
    """Get the current configuration."""
    if _config is None:
        initialize_config()
    return _config.copy()


def get_api_key(key_name: str, env_var_name: str) -> str:
    """Get API key from environment variables or config."""
    # First check environment variables
    api_key = os.getenv(env_var_name)
    
    # If not found, check config
    if api_key is None and _config is not None and key_name in _config:
        api_key = _config[key_name]
    
    return api_key


def get_openai_api_key() -> str:
    """Get OpenAI API key from environment variables or config."""
    return get_api_key("openai_api_key", "OPENAI_API_KEY")


def get_finnhub_api_key() -> str:
    """Get Finnhub API key from environment variables or config."""
    return get_api_key("finnhub_api_key", "FINNHUB_API_KEY")


def get_alpaca_api_key() -> str:
    """Get Alpaca API key from environment variables or config."""
    return get_api_key("alpaca_api_key", "ALPACA_API_KEY")


def get_alpaca_secret_key() -> str:
    """Get Alpaca secret key from environment variables or config."""
    return get_api_key("alpaca_secret_key", "ALPACA_SECRET_KEY")


def get_alpaca_use_paper() -> str:
    """Get Alpaca paper trading flag from environment variables or config."""
    return get_api_key("alpaca_use_paper", "ALPACA_USE_PAPER")


def get_fred_api_key() -> str:
    """Get FRED API key from environment variables or config."""
    return get_api_key("fred_api_key", "FRED_API_KEY")


# Initialize with default config
initialize_config()
