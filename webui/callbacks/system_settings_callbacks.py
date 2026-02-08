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
            Output("setting-openai-api-key", "value"),
            Output("setting-alpaca-api-key", "value"),
            Output("setting-alpaca-secret-key", "value"),
            Output("setting-alpaca-paper-mode", "value"),
            Output("setting-finnhub-api-key", "value"),
            Output("setting-fred-api-key", "value"),
            Output("setting-coindesk-api-key", "value"),
            Output("setting-deep-think-llm", "value"),
            Output("setting-quick-think-llm", "value"),
            Output("setting-max-debate-rounds", "value"),
            Output("setting-max-risk-rounds", "value"),
            Output("setting-parallel-analysts", "value"),
            Output("setting-online-tools", "value"),
            Output("setting-max-recur-limit", "value"),
            Output("setting-scanner-num-results", "value"),
            Output("setting-scanner-llm-sentiment", "value"),
            Output("setting-scanner-options-flow", "value"),
            Output("setting-scanner-cache-ttl", "value"),
            Output("setting-scanner-dynamic-universe", "value"),
        ],
        Input("system-settings-store", "data"),
        prevent_initial_call=False
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

        return (
            settings.get("openai_api_key") or "",
            settings.get("alpaca_api_key") or "",
            settings.get("alpaca_secret_key") or "",
            settings.get("alpaca_use_paper", "True"),
            settings.get("finnhub_api_key") or "",
            settings.get("fred_api_key") or "",
            settings.get("coindesk_api_key") or "",
            settings.get("deep_think_llm", "o3-mini"),
            settings.get("quick_think_llm", "gpt-4o-mini"),
            settings.get("max_debate_rounds", 4),
            settings.get("max_risk_discuss_rounds", 3),
            settings.get("parallel_analysts", True),
            settings.get("online_tools", True),
            settings.get("max_recur_limit", 200),
            settings.get("scanner_num_results", 20),
            settings.get("scanner_use_llm_sentiment", False),
            settings.get("scanner_use_options_flow", True),
            settings.get("scanner_cache_ttl", 300),
            settings.get("scanner_dynamic_universe", True),
        )

    # =========================================================================
    # Save settings to store
    # =========================================================================
    @app.callback(
        [
            Output("system-settings-store", "data"),
            Output("settings-toast", "is_open"),
            Output("settings-toast", "children"),
            Output("settings-toast", "icon"),
            Output("settings-toast", "header"),
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
            State("setting-deep-think-llm", "value"),
            State("setting-quick-think-llm", "value"),
            State("setting-max-debate-rounds", "value"),
            State("setting-max-risk-rounds", "value"),
            State("setting-parallel-analysts", "value"),
            State("setting-online-tools", "value"),
            State("setting-max-recur-limit", "value"),
            State("setting-scanner-num-results", "value"),
            State("setting-scanner-llm-sentiment", "value"),
            State("setting-scanner-options-flow", "value"),
            State("setting-scanner-cache-ttl", "value"),
            State("setting-scanner-dynamic-universe", "value"),
            State("system-settings-store", "data"),
        ],
        prevent_initial_call=True
    )
    def save_settings(
        n_clicks,
        openai_key, alpaca_key, alpaca_secret, alpaca_paper,
        finnhub_key, fred_key, coindesk_key,
        deep_llm, quick_llm,
        max_debate, max_risk, parallel_analysts, online_tools, max_recur,
        scanner_results, scanner_llm, scanner_options, scanner_cache, scanner_dynamic,
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
            "deep_think_llm": deep_llm,
            "quick_think_llm": quick_llm,
            "max_debate_rounds": max_debate,
            "max_risk_discuss_rounds": max_risk,
            "parallel_analysts": parallel_analysts,
            "online_tools": online_tools,
            "max_recur_limit": max_recur,
            "scanner_num_results": scanner_results,
            "scanner_use_llm_sentiment": scanner_llm,
            "scanner_use_options_flow": scanner_options,
            "scanner_cache_ttl": scanner_cache,
            "scanner_dynamic_universe": scanner_dynamic,
        }

        # Sync to app_state for use by analysis engine
        sync_settings_to_app_state(settings)

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
            Output("setting-deep-think-llm", "value", allow_duplicate=True),
            Output("setting-quick-think-llm", "value", allow_duplicate=True),
            Output("setting-max-debate-rounds", "value", allow_duplicate=True),
            Output("setting-max-risk-rounds", "value", allow_duplicate=True),
            Output("setting-parallel-analysts", "value", allow_duplicate=True),
            Output("setting-online-tools", "value", allow_duplicate=True),
            Output("setting-max-recur-limit", "value", allow_duplicate=True),
            Output("setting-scanner-num-results", "value", allow_duplicate=True),
            Output("setting-scanner-llm-sentiment", "value", allow_duplicate=True),
            Output("setting-scanner-options-flow", "value", allow_duplicate=True),
            Output("setting-scanner-cache-ttl", "value", allow_duplicate=True),
            Output("setting-scanner-dynamic-universe", "value", allow_duplicate=True),
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
            defaults.get("deep_think_llm", "o3-mini"),
            defaults.get("quick_think_llm", "gpt-4o-mini"),
            defaults.get("max_debate_rounds", 4),
            defaults.get("max_risk_discuss_rounds", 3),
            defaults.get("parallel_analysts", True),
            defaults.get("online_tools", True),
            defaults.get("max_recur_limit", 200),
            defaults.get("scanner_num_results", 20),
            defaults.get("scanner_use_llm_sentiment", False),
            defaults.get("scanner_use_options_flow", True),
            defaults.get("scanner_cache_ttl", 300),
            defaults.get("scanner_dynamic_universe", True),
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
            Output("setting-scanner-num-results", "value", allow_duplicate=True),
            Output("setting-scanner-llm-sentiment", "value", allow_duplicate=True),
            Output("setting-scanner-options-flow", "value", allow_duplicate=True),
            Output("setting-scanner-cache-ttl", "value", allow_duplicate=True),
            Output("setting-scanner-dynamic-universe", "value", allow_duplicate=True),
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
                imported.get("deep_think_llm", "o3-mini"),
                imported.get("quick_think_llm", "gpt-4o-mini"),
                imported.get("max_debate_rounds", 4),
                imported.get("max_risk_discuss_rounds", 3),
                imported.get("parallel_analysts", True),
                imported.get("online_tools", True),
                imported.get("max_recur_limit", 200),
                imported.get("scanner_num_results", 20),
                imported.get("scanner_use_llm_sentiment", False),
                imported.get("scanner_use_options_flow", True),
                imported.get("scanner_cache_ttl", 300),
                imported.get("scanner_dynamic_universe", True),
                True,
                f"Settings imported from {filename}. Click 'Save' to persist.",
                "success",
                "Settings Imported"
            )
        except Exception as e:
            return (
                no_update, no_update, no_update, no_update, no_update, no_update,
                no_update, no_update, no_update, no_update, no_update, no_update,
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
