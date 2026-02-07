"""
Callbacks package for TradingAgents WebUI
Contains organized callback functions grouped by functionality
"""

from .status_callbacks import register_status_callbacks
from .chart_callbacks import register_chart_callbacks
from .report_callbacks import register_report_callbacks
from .control_callbacks import register_control_callbacks
from .trading_callbacks import register_trading_callbacks
from .storage_callbacks import register_storage_callbacks
from .scanner_callbacks import register_scanner_callbacks
from .collapse_callbacks import register_collapse_callbacks
from .ticker_progress_callbacks import register_ticker_progress_callbacks
from .theme_callbacks import register_theme_callbacks
from .watchlist_callbacks import register_watchlist_callbacks
from .ux_callbacks import register_ux_callbacks
from .history_callbacks import register_history_callbacks
from .log_callbacks import register_log_callbacks

def register_all_callbacks(app):
    """Register all callback functions with the Dash app"""
    register_status_callbacks(app)
    register_chart_callbacks(app)
    register_report_callbacks(app)
    register_control_callbacks(app)
    register_trading_callbacks(app)
    register_storage_callbacks(app)
    register_scanner_callbacks(app)
    register_collapse_callbacks(app)
    register_ticker_progress_callbacks(app)
    register_theme_callbacks(app)
    register_watchlist_callbacks(app)
    register_ux_callbacks(app)
    register_history_callbacks(app)
    register_log_callbacks(app) 