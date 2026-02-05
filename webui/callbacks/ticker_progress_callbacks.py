"""
Ticker Progress Callbacks - Real-time updates for agent progress per ticker
"""

from dash import Input, Output

from webui.utils.state import app_state
from webui.components.ticker_progress_panel import render_all_ticker_progress


def register_ticker_progress_callbacks(app):
    """Register callbacks for ticker progress panel updates."""

    @app.callback(
        Output("ticker-progress-container", "children"),
        [Input("refresh-interval", "n_intervals"),
         Input("medium-refresh-interval", "n_intervals"),
         Input("slow-refresh-interval", "n_intervals")]
    )
    def update_ticker_progress(fast_n, medium_n, slow_n):
        """Update the ticker progress display for all tickers."""
        active_analysts = getattr(app_state, 'active_analysts', None)
        return render_all_ticker_progress(
            app_state.symbol_states,
            app_state.analyzing_symbols,
            active_analysts
        )
