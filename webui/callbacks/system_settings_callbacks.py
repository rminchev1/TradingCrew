"""
webui/callbacks/system_settings_callbacks.py
Callbacks for the System Settings page: save, test, reset, import/export, reveal toggle.
"""

import json
import base64
from dash import callback, Input, Output, State, ctx, no_update, ALL, MATCH
from dash.exceptions import PreventUpdate
import os

from webui.utils.storage import DEFAULT_SYSTEM_SETTINGS, export_settings, import_settings
from webui.utils.state import app_state
from tradingagents.dataflows.config import (
    validate_openai_key,
    validate_alpaca_keys,
    validate_finnhub_key,
    validate_fred_key,
)
from dash import html


def sync_settings_to_app_state(settings):
    """Sync settings dict to app_state.system_settings for use by analysis engine."""
    if settings:
        app_state.system_settings.update(settings)
        print(f"[SETTINGS] Synced {len(settings)} settings to app_state")


def register_system_settings_callbacks(app):
    """Register all system settings callbacks."""

    # =========================================================================
    # Load settings from store on page load
    # =========================================================================
    @app.callback(
        [
            Output("setting-openai-api-key", "value", allow_duplicate=True),
            Output("setting-alpaca-api-key", "value", allow_duplicate=True),
            Output("setting-alpaca-secret-key", "value", allow_duplicate=True),
            Output("setting-alpaca-paper-mode", "value", allow_duplicate=True),
            Output("setting-finnhub-api-key", "value", allow_duplicate=True),
            Output("setting-fred-api-key", "value", allow_duplicate=True),
            Output("setting-coindesk-api-key", "value", allow_duplicate=True),
            Output("setting-reddit-client-id", "value", allow_duplicate=True),
            Output("setting-reddit-client-secret", "value", allow_duplicate=True),
            Output("setting-reddit-user-agent", "value", allow_duplicate=True),
            Output("setting-deep-think-llm", "value", allow_duplicate=True),
            Output("setting-quick-think-llm", "value", allow_duplicate=True),
            Output("setting-max-debate-rounds", "value", allow_duplicate=True),
            Output("setting-max-risk-rounds", "value", allow_duplicate=True),
            Output("setting-parallel-analysts", "value", allow_duplicate=True),
            Output("setting-online-tools", "value", allow_duplicate=True),
            Output("setting-max-recur-limit", "value", allow_duplicate=True),
            Output("setting-max-parallel-tickers", "value", allow_duplicate=True),
            Output("setting-scanner-num-results", "value", allow_duplicate=True),
            Output("setting-scanner-llm-sentiment", "value", allow_duplicate=True),
            Output("setting-scanner-options-flow", "value", allow_duplicate=True),
            Output("setting-scanner-cache-ttl", "value", allow_duplicate=True),
            Output("setting-scanner-dynamic-universe", "value", allow_duplicate=True),
            # Options trading settings
            Output("setting-enable-options-trading", "value", allow_duplicate=True),
            Output("setting-options-trading-level", "value", allow_duplicate=True),
            Output("setting-options-max-contracts", "value", allow_duplicate=True),
            Output("setting-options-max-position-value", "value", allow_duplicate=True),
            Output("setting-options-min-dte", "value", allow_duplicate=True),
            Output("setting-options-max-dte", "value", allow_duplicate=True),
            Output("setting-options-min-delta", "value", allow_duplicate=True),
            Output("setting-options-max-delta", "value", allow_duplicate=True),
            Output("setting-options-min-open-interest", "value", allow_duplicate=True),
        ],
        Input("system-settings-store", "data"),
        prevent_initial_call=True
    )
    def load_settings_from_store(stored_settings):
        """Load settings from localStorage when page loads."""
        if stored_settings is None:
            stored_settings = {}

        # Merge with defaults
        settings = DEFAULT_SYSTEM_SETTINGS.copy()
        settings.update(stored_settings)

        # Sync to app_state for use by analysis engine
        sync_settings_to_app_state(settings)

        # Update Reddit live client with credentials if available
        try:
            from tradingagents.dataflows.reddit_live import RedditLiveClient
            RedditLiveClient.update_credentials(
                client_id=settings.get("reddit_client_id"),
                client_secret=settings.get("reddit_client_secret"),
                user_agent=settings.get("reddit_user_agent"),
            )
        except Exception as e:
            print(f"[SETTINGS] Could not update Reddit credentials: {e}")

        return (
            settings.get("openai_api_key") or "",
            settings.get("alpaca_api_key") or "",
            settings.get("alpaca_secret_key") or "",
            settings.get("alpaca_use_paper", "True"),
            settings.get("finnhub_api_key") or "",
            settings.get("fred_api_key") or "",
            settings.get("coindesk_api_key") or "",
            settings.get("reddit_client_id") or "",
            settings.get("reddit_client_secret") or "",
            settings.get("reddit_user_agent") or "TradingCrew/1.0",
            settings.get("deep_think_llm", "o4-mini"),
            settings.get("quick_think_llm", "gpt-4.1-nano"),
            settings.get("max_debate_rounds", 4),
            settings.get("max_risk_discuss_rounds", 3),
            settings.get("parallel_analysts", True),
            settings.get("online_tools", True),
            settings.get("max_recur_limit", 200),
            settings.get("max_parallel_tickers", 3),
            settings.get("scanner_num_results", 20),
            settings.get("scanner_use_llm_sentiment", False),
            settings.get("scanner_use_options_flow", True),
            settings.get("scanner_cache_ttl", 300),
            settings.get("scanner_dynamic_universe", True),
            # Options trading settings
            settings.get("enable_options_trading", False),
            settings.get("options_trading_level", 2),
            settings.get("options_max_contracts", 10),
            settings.get("options_max_position_value", 5000),
            settings.get("options_min_dte", 7),
            settings.get("options_max_dte", 45),
            settings.get("options_min_delta", 0.20),
            settings.get("options_max_delta", 0.70),
            settings.get("options_min_open_interest", 100),
        )

    # =========================================================================
    # Save settings to store
    # =========================================================================
    @app.callback(
        [
            Output("system-settings-store", "data"),
            Output("settings-toast", "is_open", allow_duplicate=True),
            Output("settings-toast", "children", allow_duplicate=True),
            Output("settings-toast", "icon", allow_duplicate=True),
            Output("settings-toast", "header", allow_duplicate=True),
        ],
        Input("settings-save-btn", "n_clicks"),
        [
            State("setting-openai-api-key", "value"),
            State("setting-alpaca-api-key", "value"),
            State("setting-alpaca-secret-key", "value"),
            State("setting-alpaca-paper-mode", "value"),
            State("setting-finnhub-api-key", "value"),
            State("setting-fred-api-key", "value"),
            State("setting-coindesk-api-key", "value"),
            State("setting-reddit-client-id", "value"),
            State("setting-reddit-client-secret", "value"),
            State("setting-reddit-user-agent", "value"),
            State("setting-deep-think-llm", "value"),
            State("setting-quick-think-llm", "value"),
            State("setting-max-debate-rounds", "value"),
            State("setting-max-risk-rounds", "value"),
            State("setting-parallel-analysts", "value"),
            State("setting-online-tools", "value"),
            State("setting-max-recur-limit", "value"),
            State("setting-max-parallel-tickers", "value"),
            State("setting-scanner-num-results", "value"),
            State("setting-scanner-llm-sentiment", "value"),
            State("setting-scanner-options-flow", "value"),
            State("setting-scanner-cache-ttl", "value"),
            State("setting-scanner-dynamic-universe", "value"),
            # Options trading settings
            State("setting-enable-options-trading", "value"),
            State("setting-options-trading-level", "value"),
            State("setting-options-max-contracts", "value"),
            State("setting-options-max-position-value", "value"),
            State("setting-options-min-dte", "value"),
            State("setting-options-max-dte", "value"),
            State("setting-options-min-delta", "value"),
            State("setting-options-max-delta", "value"),
            State("setting-options-min-open-interest", "value"),
            State("system-settings-store", "data"),
        ],
        prevent_initial_call=True
    )
    def save_settings(
        n_clicks,
        openai_key, alpaca_key, alpaca_secret, alpaca_paper,
        finnhub_key, fred_key, coindesk_key,
        reddit_client_id, reddit_client_secret, reddit_user_agent,
        deep_llm, quick_llm,
        max_debate, max_risk, parallel_analysts, online_tools, max_recur, max_parallel_tickers,
        scanner_results, scanner_llm, scanner_options, scanner_cache, scanner_dynamic,
        enable_options_trading, options_trading_level, options_max_contracts, options_max_position_value,
        options_min_dte, options_max_dte, options_min_delta, options_max_delta, options_min_open_interest,
        current_store
    ):
        """Save settings to localStorage."""
        if not n_clicks:
            raise PreventUpdate

        # Build settings dict
        settings = {
            "openai_api_key": openai_key if openai_key else None,
            "alpaca_api_key": alpaca_key if alpaca_key else None,
            "alpaca_secret_key": alpaca_secret if alpaca_secret else None,
            "alpaca_use_paper": alpaca_paper,
            "finnhub_api_key": finnhub_key if finnhub_key else None,
            "fred_api_key": fred_key if fred_key else None,
            "coindesk_api_key": coindesk_key if coindesk_key else None,
            "reddit_client_id": reddit_client_id if reddit_client_id else None,
            "reddit_client_secret": reddit_client_secret if reddit_client_secret else None,
            "reddit_user_agent": reddit_user_agent if reddit_user_agent else "TradingCrew/1.0",
            "deep_think_llm": deep_llm,
            "quick_think_llm": quick_llm,
            "max_debate_rounds": max_debate,
            "max_risk_discuss_rounds": max_risk,
            "parallel_analysts": parallel_analysts,
            "online_tools": online_tools,
            "max_recur_limit": max_recur,
            "max_parallel_tickers": max_parallel_tickers,
            "scanner_num_results": scanner_results,
            "scanner_use_llm_sentiment": scanner_llm,
            "scanner_use_options_flow": scanner_options,
            "scanner_cache_ttl": scanner_cache,
            "scanner_dynamic_universe": scanner_dynamic,
            # Options trading settings
            "enable_options_trading": enable_options_trading,
            "options_trading_level": int(options_trading_level) if options_trading_level else 2,
            "options_max_contracts": options_max_contracts,
            "options_max_position_value": options_max_position_value,
            "options_min_dte": options_min_dte,
            "options_max_dte": options_max_dte,
            "options_min_delta": options_min_delta,
            "options_max_delta": options_max_delta,
            "options_min_open_interest": options_min_open_interest,
        }

        # Sync to app_state for use by analysis engine
        sync_settings_to_app_state(settings)

        # Update Reddit live client with new credentials
        try:
            from tradingagents.dataflows.reddit_live import RedditLiveClient
            RedditLiveClient.update_credentials(
                client_id=reddit_client_id,
                client_secret=reddit_client_secret,
                user_agent=reddit_user_agent,
            )
        except Exception as e:
            print(f"[SETTINGS] Could not update Reddit credentials: {e}")

        return (
            settings,
            True,
            "Settings saved successfully!",
            "success",
            "Settings Saved"
        )

    # =========================================================================
    # Reset to defaults
    # =========================================================================
    @app.callback(
        [
            Output("setting-openai-api-key", "value", allow_duplicate=True),
            Output("setting-alpaca-api-key", "value", allow_duplicate=True),
            Output("setting-alpaca-secret-key", "value", allow_duplicate=True),
            Output("setting-alpaca-paper-mode", "value", allow_duplicate=True),
            Output("setting-finnhub-api-key", "value", allow_duplicate=True),
            Output("setting-fred-api-key", "value", allow_duplicate=True),
            Output("setting-coindesk-api-key", "value", allow_duplicate=True),
            Output("setting-reddit-client-id", "value", allow_duplicate=True),
            Output("setting-reddit-client-secret", "value", allow_duplicate=True),
            Output("setting-reddit-user-agent", "value", allow_duplicate=True),
            Output("setting-deep-think-llm", "value", allow_duplicate=True),
            Output("setting-quick-think-llm", "value", allow_duplicate=True),
            Output("setting-max-debate-rounds", "value", allow_duplicate=True),
            Output("setting-max-risk-rounds", "value", allow_duplicate=True),
            Output("setting-parallel-analysts", "value", allow_duplicate=True),
            Output("setting-online-tools", "value", allow_duplicate=True),
            Output("setting-max-recur-limit", "value", allow_duplicate=True),
            Output("setting-max-parallel-tickers", "value", allow_duplicate=True),
            Output("setting-scanner-num-results", "value", allow_duplicate=True),
            Output("setting-scanner-llm-sentiment", "value", allow_duplicate=True),
            Output("setting-scanner-options-flow", "value", allow_duplicate=True),
            Output("setting-scanner-cache-ttl", "value", allow_duplicate=True),
            Output("setting-scanner-dynamic-universe", "value", allow_duplicate=True),
            # Options trading settings
            Output("setting-enable-options-trading", "value", allow_duplicate=True),
            Output("setting-options-trading-level", "value", allow_duplicate=True),
            Output("setting-options-max-contracts", "value", allow_duplicate=True),
            Output("setting-options-max-position-value", "value", allow_duplicate=True),
            Output("setting-options-min-dte", "value", allow_duplicate=True),
            Output("setting-options-max-dte", "value", allow_duplicate=True),
            Output("setting-options-min-delta", "value", allow_duplicate=True),
            Output("setting-options-max-delta", "value", allow_duplicate=True),
            Output("setting-options-min-open-interest", "value", allow_duplicate=True),
            Output("settings-toast", "is_open", allow_duplicate=True),
            Output("settings-toast", "children", allow_duplicate=True),
            Output("settings-toast", "icon", allow_duplicate=True),
            Output("settings-toast", "header", allow_duplicate=True),
        ],
        Input("settings-reset-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def reset_to_defaults(n_clicks):
        """Reset all settings to their default values."""
        if not n_clicks:
            raise PreventUpdate

        defaults = DEFAULT_SYSTEM_SETTINGS

        return (
            "",  # API keys reset to empty (user must re-enter)
            "",
            "",
            defaults.get("alpaca_use_paper", "True"),
            "",
            "",
            "",
            "",  # Reddit client ID
            "",  # Reddit client secret
            defaults.get("reddit_user_agent", "TradingCrew/1.0"),
            defaults.get("deep_think_llm", "o4-mini"),
            defaults.get("quick_think_llm", "gpt-4.1-nano"),
            defaults.get("max_debate_rounds", 4),
            defaults.get("max_risk_discuss_rounds", 3),
            defaults.get("parallel_analysts", True),
            defaults.get("online_tools", True),
            defaults.get("max_recur_limit", 200),
            defaults.get("max_parallel_tickers", 3),
            defaults.get("scanner_num_results", 20),
            defaults.get("scanner_use_llm_sentiment", False),
            defaults.get("scanner_use_options_flow", True),
            defaults.get("scanner_cache_ttl", 300),
            defaults.get("scanner_dynamic_universe", True),
            # Options trading settings
            defaults.get("enable_options_trading", False),
            defaults.get("options_trading_level", 2),
            defaults.get("options_max_contracts", 10),
            defaults.get("options_max_position_value", 5000),
            defaults.get("options_min_dte", 7),
            defaults.get("options_max_dte", 45),
            defaults.get("options_min_delta", 0.20),
            defaults.get("options_max_delta", 0.70),
            defaults.get("options_min_open_interest", 100),
            True,
            "Settings reset to defaults. Click 'Save' to persist.",
            "info",
            "Settings Reset"
        )

    # =========================================================================
    # Export settings
    # =========================================================================
    @app.callback(
        Output("settings-export-download", "data"),
        Input("settings-export-btn", "n_clicks"),
        State("system-settings-store", "data"),
        prevent_initial_call=True
    )
    def export_settings_handler(n_clicks, stored_settings):
        """Export settings as a JSON file (excludes API keys for security)."""
        if not n_clicks:
            raise PreventUpdate

        if stored_settings is None:
            stored_settings = DEFAULT_SYSTEM_SETTINGS.copy()

        json_str = export_settings(stored_settings)

        return dict(
            content=json_str,
            filename="trading_agents_settings.json"
        )

    # =========================================================================
    # Import settings
    # =========================================================================
    @app.callback(
        [
            Output("setting-deep-think-llm", "value", allow_duplicate=True),
            Output("setting-quick-think-llm", "value", allow_duplicate=True),
            Output("setting-max-debate-rounds", "value", allow_duplicate=True),
            Output("setting-max-risk-rounds", "value", allow_duplicate=True),
            Output("setting-parallel-analysts", "value", allow_duplicate=True),
            Output("setting-online-tools", "value", allow_duplicate=True),
            Output("setting-max-recur-limit", "value", allow_duplicate=True),
            Output("setting-max-parallel-tickers", "value", allow_duplicate=True),
            Output("setting-scanner-num-results", "value", allow_duplicate=True),
            Output("setting-scanner-llm-sentiment", "value", allow_duplicate=True),
            Output("setting-scanner-options-flow", "value", allow_duplicate=True),
            Output("setting-scanner-cache-ttl", "value", allow_duplicate=True),
            Output("setting-scanner-dynamic-universe", "value", allow_duplicate=True),
            # Options trading settings
            Output("setting-enable-options-trading", "value", allow_duplicate=True),
            Output("setting-options-trading-level", "value", allow_duplicate=True),
            Output("setting-options-max-contracts", "value", allow_duplicate=True),
            Output("setting-options-max-position-value", "value", allow_duplicate=True),
            Output("setting-options-min-dte", "value", allow_duplicate=True),
            Output("setting-options-max-dte", "value", allow_duplicate=True),
            Output("setting-options-min-delta", "value", allow_duplicate=True),
            Output("setting-options-max-delta", "value", allow_duplicate=True),
            Output("setting-options-min-open-interest", "value", allow_duplicate=True),
            Output("settings-toast", "is_open", allow_duplicate=True),
            Output("settings-toast", "children", allow_duplicate=True),
            Output("settings-toast", "icon", allow_duplicate=True),
            Output("settings-toast", "header", allow_duplicate=True),
        ],
        Input("settings-import-upload", "contents"),
        State("settings-import-upload", "filename"),
        prevent_initial_call=True
    )
    def import_settings_handler(contents, filename):
        """Import settings from a JSON file."""
        if contents is None:
            raise PreventUpdate

        try:
            # Decode the uploaded file
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string).decode('utf-8')

            # Parse JSON
            imported = import_settings(decoded)

            return (
                imported.get("deep_think_llm", "o4-mini"),
                imported.get("quick_think_llm", "gpt-4.1-nano"),
                imported.get("max_debate_rounds", 4),
                imported.get("max_risk_discuss_rounds", 3),
                imported.get("parallel_analysts", True),
                imported.get("online_tools", True),
                imported.get("max_recur_limit", 200),
                imported.get("max_parallel_tickers", 3),
                imported.get("scanner_num_results", 20),
                imported.get("scanner_use_llm_sentiment", False),
                imported.get("scanner_use_options_flow", True),
                imported.get("scanner_cache_ttl", 300),
                imported.get("scanner_dynamic_universe", True),
                # Options trading settings
                imported.get("enable_options_trading", False),
                imported.get("options_trading_level", 2),
                imported.get("options_max_contracts", 10),
                imported.get("options_max_position_value", 5000),
                imported.get("options_min_dte", 7),
                imported.get("options_max_dte", 45),
                imported.get("options_min_delta", 0.20),
                imported.get("options_max_delta", 0.70),
                imported.get("options_min_open_interest", 100),
                True,
                f"Settings imported from {filename}. Click 'Save' to persist.",
                "success",
                "Settings Imported"
            )
        except Exception as e:
            return (
                no_update, no_update, no_update, no_update, no_update, no_update,
                no_update, no_update, no_update, no_update, no_update, no_update,
                no_update, no_update, no_update, no_update, no_update, no_update,
                no_update, no_update, no_update, no_update,
                True,
                f"Error importing settings: {str(e)}",
                "danger",
                "Import Failed"
            )

    # =========================================================================
    # API Key reveal toggles
    # =========================================================================
    @app.callback(
        Output("setting-openai-api-key", "type"),
        Input("reveal-openai-api-key", "n_clicks"),
        State("setting-openai-api-key", "type"),
        prevent_initial_call=True
    )
    def toggle_openai_reveal(n_clicks, current_type):
        if not n_clicks:
            raise PreventUpdate
        return "text" if current_type == "password" else "password"

    @app.callback(
        Output("setting-alpaca-api-key", "type"),
        Input("reveal-alpaca-api-key", "n_clicks"),
        State("setting-alpaca-api-key", "type"),
        prevent_initial_call=True
    )
    def toggle_alpaca_key_reveal(n_clicks, current_type):
        if not n_clicks:
            raise PreventUpdate
        return "text" if current_type == "password" else "password"

    @app.callback(
        Output("setting-alpaca-secret-key", "type"),
        Input("reveal-alpaca-secret-key", "n_clicks"),
        State("setting-alpaca-secret-key", "type"),
        prevent_initial_call=True
    )
    def toggle_alpaca_secret_reveal(n_clicks, current_type):
        if not n_clicks:
            raise PreventUpdate
        return "text" if current_type == "password" else "password"

    @app.callback(
        Output("setting-finnhub-api-key", "type"),
        Input("reveal-finnhub-api-key", "n_clicks"),
        State("setting-finnhub-api-key", "type"),
        prevent_initial_call=True
    )
    def toggle_finnhub_reveal(n_clicks, current_type):
        if not n_clicks:
            raise PreventUpdate
        return "text" if current_type == "password" else "password"

    @app.callback(
        Output("setting-fred-api-key", "type"),
        Input("reveal-fred-api-key", "n_clicks"),
        State("setting-fred-api-key", "type"),
        prevent_initial_call=True
    )
    def toggle_fred_reveal(n_clicks, current_type):
        if not n_clicks:
            raise PreventUpdate
        return "text" if current_type == "password" else "password"

    @app.callback(
        Output("setting-coindesk-api-key", "type"),
        Input("reveal-coindesk-api-key", "n_clicks"),
        State("setting-coindesk-api-key", "type"),
        prevent_initial_call=True
    )
    def toggle_coindesk_reveal(n_clicks, current_type):
        if not n_clicks:
            raise PreventUpdate
        return "text" if current_type == "password" else "password"

    # =========================================================================
    # Test API connections
    # =========================================================================
    @app.callback(
        [
            Output("status-openai-api-key", "children"),
        ],
        Input("test-openai-api-key", "n_clicks"),
        State("setting-openai-api-key", "value"),
        prevent_initial_call=True
    )
    def test_openai_connection(n_clicks, api_key):
        if not n_clicks:
            raise PreventUpdate

        # Use env var if no value entered
        key_to_test = api_key if api_key else os.getenv("OPENAI_API_KEY")

        if not key_to_test:
            return [[
                html.I(className="fas fa-times-circle text-warning me-1"),
                "Not set"
            ]]

        is_valid = validate_openai_key(key_to_test)

        if is_valid:
            return [[
                html.I(className="fas fa-check-circle text-success me-1"),
                "Valid"
            ]]
        else:
            return [[
                html.I(className="fas fa-times-circle text-danger me-1"),
                "Invalid"
            ]]

    @app.callback(
        [
            Output("status-alpaca-api-key", "children"),
        ],
        Input("test-alpaca-api-key", "n_clicks"),
        [
            State("setting-alpaca-api-key", "value"),
            State("setting-alpaca-secret-key", "value"),
            State("setting-alpaca-paper-mode", "value"),
        ],
        prevent_initial_call=True
    )
    def test_alpaca_connection(n_clicks, api_key, secret_key, paper_mode):
        if not n_clicks:
            raise PreventUpdate

        # Use env vars if no values entered
        key_to_test = api_key if api_key else os.getenv("ALPACA_API_KEY")
        secret_to_test = secret_key if secret_key else os.getenv("ALPACA_SECRET_KEY")
        paper = paper_mode == "True"

        if not key_to_test or not secret_to_test:
            return [[
                html.I(className="fas fa-times-circle text-warning me-1"),
                "Keys not set"
            ]]

        is_valid = validate_alpaca_keys(key_to_test, secret_to_test, paper)

        if is_valid:
            return [[
                html.I(className="fas fa-check-circle text-success me-1"),
                "Valid"
            ]]
        else:
            return [[
                html.I(className="fas fa-times-circle text-danger me-1"),
                "Invalid"
            ]]

    @app.callback(
        [
            Output("status-finnhub-api-key", "children"),
        ],
        Input("test-finnhub-api-key", "n_clicks"),
        State("setting-finnhub-api-key", "value"),
        prevent_initial_call=True
    )
    def test_finnhub_connection(n_clicks, api_key):
        if not n_clicks:
            raise PreventUpdate

        key_to_test = api_key if api_key else os.getenv("FINNHUB_API_KEY")

        if not key_to_test:
            return [[
                html.I(className="fas fa-times-circle text-warning me-1"),
                "Not set"
            ]]

        is_valid = validate_finnhub_key(key_to_test)

        if is_valid:
            return [[
                html.I(className="fas fa-check-circle text-success me-1"),
                "Valid"
            ]]
        else:
            return [[
                html.I(className="fas fa-times-circle text-danger me-1"),
                "Invalid"
            ]]

    @app.callback(
        [
            Output("status-fred-api-key", "children"),
        ],
        Input("test-fred-api-key", "n_clicks"),
        State("setting-fred-api-key", "value"),
        prevent_initial_call=True
    )
    def test_fred_connection(n_clicks, api_key):
        if not n_clicks:
            raise PreventUpdate

        key_to_test = api_key if api_key else os.getenv("FRED_API_KEY")

        if not key_to_test:
            return [[
                html.I(className="fas fa-times-circle text-warning me-1"),
                "Not set"
            ]]

        is_valid = validate_fred_key(key_to_test)

        if is_valid:
            return [[
                html.I(className="fas fa-check-circle text-success me-1"),
                "Valid"
            ]]
        else:
            return [[
                html.I(className="fas fa-times-circle text-danger me-1"),
                "Invalid"
            ]]

    @app.callback(
        [
            Output("status-coindesk-api-key", "children"),
        ],
        Input("test-coindesk-api-key", "n_clicks"),
        State("setting-coindesk-api-key", "value"),
        prevent_initial_call=True
    )
    def test_coindesk_connection(n_clicks, api_key):
        if not n_clicks:
            raise PreventUpdate

        key_to_test = api_key if api_key else os.getenv("COINDESK_API_KEY")

        if not key_to_test:
            return [[
                html.I(className="fas fa-times-circle text-warning me-1"),
                "Not set"
            ]]

        # CoinDesk doesn't have a simple validation endpoint, just check if key is set
        return [[
            html.I(className="fas fa-check-circle text-info me-1"),
            "Set (not validated)"
        ]]

    # =========================================================================
    # Update Alpaca mode display
    # =========================================================================
    @app.callback(
        Output("status-alpaca-mode", "children"),
        Input("setting-alpaca-paper-mode", "value"),
        prevent_initial_call=True
    )
    def update_alpaca_mode_display(paper_mode):
        if paper_mode == "True":
            return [
                html.I(className="fas fa-flask text-info me-1"),
                "PAPER MODE"
            ]
        else:
            return [
                html.I(className="fas fa-exclamation-triangle text-danger me-1"),
                "LIVE MODE"
            ]

    # =========================================================================
    # Reddit API reveal toggles
    # =========================================================================
    @app.callback(
        Output("setting-reddit-client-id", "type"),
        Input("reveal-reddit-client-id", "n_clicks"),
        State("setting-reddit-client-id", "type"),
        prevent_initial_call=True
    )
    def toggle_reddit_client_id_reveal(n_clicks, current_type):
        if not n_clicks:
            raise PreventUpdate
        return "text" if current_type == "password" else "password"

    @app.callback(
        Output("setting-reddit-client-secret", "type"),
        Input("reveal-reddit-client-secret", "n_clicks"),
        State("setting-reddit-client-secret", "type"),
        prevent_initial_call=True
    )
    def toggle_reddit_client_secret_reveal(n_clicks, current_type):
        if not n_clicks:
            raise PreventUpdate
        return "text" if current_type == "password" else "password"

    # =========================================================================
    # Test Reddit API connection
    # =========================================================================
    @app.callback(
        [
            Output("status-reddit-client-id", "children"),
        ],
        Input("test-reddit-client-id", "n_clicks"),
        [
            State("setting-reddit-client-id", "value"),
            State("setting-reddit-client-secret", "value"),
            State("setting-reddit-user-agent", "value"),
        ],
        prevent_initial_call=True
    )
    def test_reddit_connection(n_clicks, client_id, client_secret, user_agent):
        if not n_clicks:
            raise PreventUpdate

        # Use env vars if no values entered
        id_to_test = client_id if client_id else os.getenv("REDDIT_CLIENT_ID")
        secret_to_test = client_secret if client_secret else os.getenv("REDDIT_CLIENT_SECRET")
        agent_to_test = user_agent if user_agent else os.getenv("REDDIT_USER_AGENT", "TradingCrew/1.0")

        if not id_to_test or not secret_to_test:
            return [[
                html.I(className="fas fa-times-circle text-warning me-1"),
                "Not configured"
            ]]

        try:
            from tradingagents.dataflows.reddit_live import RedditLiveClient

            # Update and test
            RedditLiveClient.update_credentials(
                client_id=id_to_test,
                client_secret=secret_to_test,
                user_agent=agent_to_test,
            )

            client = RedditLiveClient.get_instance()
            success, message = client.test_connection()

            if success:
                return [[
                    html.I(className="fas fa-check-circle text-success me-1"),
                    "Connected"
                ]]
            else:
                return [[
                    html.I(className="fas fa-times-circle text-danger me-1"),
                    "Failed"
                ]]

        except Exception as e:
            return [[
                html.I(className="fas fa-times-circle text-danger me-1"),
                f"Error: {str(e)[:20]}"
            ]]
