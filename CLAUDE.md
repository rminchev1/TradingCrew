# CLAUDE.md

This file provides guidance to Claude Code when working with this repository. Follow these patterns to work efficiently without rediscovering conventions.

## Project Overview

TradingCrew is a multi-agent LLM-powered trading framework built on LangGraph that integrates with Alpaca API for real-time stock and crypto trading. It uses 6 specialized analyst agents that work collaboratively through structured debates to make trading decisions.

## Quick Reference

### Commands
```bash
# Web UI
python run_webui_dash.py                    # Default localhost:7860
python run_webui_dash.py --port 8080        # Custom port

# CLI
python -m cli.main NVDA                     # Single stock
python -m cli.main "BTC/USD"                # Crypto (MUST include /USD)
python -m cli.main "NVDA,ETH/USD,AAPL"      # Multiple

# Tests
pytest tests/                               # All tests
pytest tests/scanner/ -v                    # Scanner tests

# Dependencies
pip install -r requirements.txt
```

### Key Directories
```
tradingagents/           # Core framework
  agents/                # Agent implementations (analysts/, researchers/, risk_mgmt/, trader/)
  dataflows/             # Data APIs (interface.py is ~1500 lines - unified data access)
  graph/                 # LangGraph orchestration (trading_graph.py is main entry)
  scanner/               # Market scanner
  default_config.py      # Configuration defaults

webui/                   # Dash-based Web UI
  components/            # 19 UI components (create_*() functions)
  callbacks/             # 16 callback modules (register_*_callbacks(app) functions)
  utils/state.py         # Global AppState class (thread-safe)
  utils/local_storage.py # SQLite persistence
  utils/storage.py       # Default settings, export/import
  layout.py              # Main layout assembly
  app_dash.py            # App factory and Flask routes

tests/                   # pytest test suite
```

---

## Architecture Patterns

### Multi-Agent Flow
```
6 Analyst Agents (parallel) → Bull/Bear Debate → Research Manager Decision
                                                          ↓
                              Risk Debators (3) → Portfolio Manager → Trade Decision
```

### Agent Types
| Agent | File Location | Report Field |
|-------|--------------|--------------|
| Market Analyst | `agents/analysts/market_analyst.py` | `market_report` |
| Social Analyst | `agents/analysts/social_media_analyst.py` | `sentiment_report` |
| News Analyst | `agents/analysts/news_analyst.py` | `news_report` |
| Fundamentals Analyst | `agents/analysts/fundamentals_analyst.py` | `fundamentals_report` |
| Macro Analyst | `agents/analysts/macro_analyst.py` | `macro_report` |
| Options Analyst | `agents/analysts/options_analyst.py` | `options_report` |

### State Classes (in `tradingagents/agents/utils/agent_states.py`)
- `AgentState` - Main graph state with all report fields
- `InvestDebateState` - Bull/Bear debate state
- `RiskDebateState` - Risk discussion state

### WebUI State Management
- **In-memory**: `webui/utils/state.py` → `AppState` class (thread-safe with `_lock`)
- **Persistent**: `webui/utils/local_storage.py` → SQLite database (`tradingcrew.db`)
- **Settings defaults**: `webui/utils/storage.py` → `DEFAULT_SYSTEM_SETTINGS`

---

## Common Development Tasks

### Adding a New System Setting

**Files to modify** (in order):

1. **`webui/utils/storage.py`** - Add to `DEFAULT_SYSTEM_SETTINGS` and `safe_keys`:
```python
DEFAULT_SYSTEM_SETTINGS = {
    # ... existing settings ...
    "my_new_setting": "default_value",  # Add here
}

def export_settings(settings):
    safe_keys = [
        # ... existing keys ...
        "my_new_setting",  # Add here for export/import
    ]
```

2. **`webui/utils/state.py`** - Add to `system_settings` dict in `AppState.__init__`:
```python
self.system_settings = {
    # ... existing settings ...
    "my_new_setting": "default_value",
}
```

3. **`webui/components/system_settings.py`** - Add UI input in appropriate section:
```python
def create_analysis_section():
    return html.Div([
        # ... existing rows ...
        dbc.Row([
            dbc.Col(dbc.Label("My Setting", className="mb-0"), width=4),
            dbc.Col(
                dbc.Input(
                    id="setting-my-new-setting",  # ID pattern: setting-{key-with-dashes}
                    type="number",  # or "text"
                    min=1, max=10, value=5,
                    size="sm"
                ),
                width=3
            ),
            dbc.Col(html.Small("Description here", className="text-muted"), width=5)
        ], className="mb-2 align-items-center"),
    ])
```

4. **`webui/callbacks/system_settings_callbacks.py`** - Add to THREE callbacks:

   a. `load_settings_from_store()` - Add Output and return value:
   ```python
   Output("setting-my-new-setting", "value", allow_duplicate=True),
   # ... in return tuple:
   settings.get("my_new_setting", "default_value"),
   ```

   b. `save_settings()` - Add State and include in settings dict:
   ```python
   State("setting-my-new-setting", "value"),
   # ... in function params and settings dict:
   "my_new_setting": my_new_setting_value,
   ```

   c. `reset_to_defaults()` - Add Output and return value:
   ```python
   Output("setting-my-new-setting", "value", allow_duplicate=True),
   # ... in return tuple:
   defaults.get("my_new_setting", "default_value"),
   ```

   d. `import_settings_handler()` - Add Output and return value (same pattern)

### Adding a New UI Component

1. **Create component file** `webui/components/my_component.py`:
```python
import dash_bootstrap_components as dbc
from dash import html

def create_my_component():
    """Create the my component panel."""
    return dbc.Card([
        dbc.CardHeader("My Component"),
        dbc.CardBody([
            html.Div(id="my-component-content"),
            dbc.Button("Action", id="my-component-btn", color="primary")
        ])
    ], id="my-component-card", className="mb-3")
```

2. **Add to layout** in `webui/layout.py`:
```python
from webui.components.my_component import create_my_component

def create_main_layout():
    return html.Div([
        # ... existing components ...
        create_my_component(),
    ])
```

3. **Create callbacks file** `webui/callbacks/my_callbacks.py`:
```python
from dash import Input, Output, State
from webui.utils.state import app_state

def register_my_callbacks(app):
    @app.callback(
        Output("my-component-content", "children"),
        Input("my-component-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def handle_action(n_clicks):
        if not n_clicks:
            return ""
        # Access global state:
        # app_state.some_property
        return "Action completed!"
```

4. **Register callbacks** in `webui/callbacks/__init__.py`:
```python
from .my_callbacks import register_my_callbacks

def register_all_callbacks(app):
    # ... existing registrations ...
    register_my_callbacks(app)
```

### Adding a Config Panel Setting (non-system setting)

For settings in the main config panel (loop mode, trade settings, etc.):

1. **`webui/components/config_panel.py`** - Add UI input
2. **`webui/callbacks/control_callbacks.py`** - Add to `save_settings_to_db()` and `restore_settings_from_db()` callbacks
3. **`webui/utils/state.py`** - Add to `AppState.__init__` if needed for runtime access

---

## Critical Gotchas

### Symbol Format for Crypto
```python
# ALWAYS preserve the /USD suffix for crypto
ticker = "BTC/USD"  # Correct
ticker = "BTC"      # WRONG - will fail

# Detection pattern:
is_crypto = "/" in ticker or "USD" in ticker.upper()
```

### LLM Temperature Parameter
```python
# These models DON'T support temperature - will error if you pass it:
no_temp_models = ["o3", "o4-mini", "gpt-5", "gpt-5-mini", "gpt-5-nano"]

# Handled in tradingagents/graph/trading_graph.py lines 70-76
```

### Thread Safety in WebUI
```python
# Always use the lock when accessing shared state:
class AppState:
    def __init__(self):
        self._lock = threading.Lock()

    def update_agent_status(self, agent, status, symbol=None):
        with self._lock:
            # Safe to modify state
```

### Callback Patterns
```python
# Use prevent_initial_call to avoid running on page load:
@app.callback(..., prevent_initial_call=True)

# Use allow_duplicate=True when multiple callbacks output to same component:
Output("component-id", "value", allow_duplicate=True)

# Access app_state from callbacks:
from webui.utils.state import app_state
```

### Database Operations
```python
# SQLite with threading - always use the lock:
from webui.utils.local_storage import save_settings, get_settings

# Tables: kv_store, analyst_reports, analysis_runs, scanner_results
```

---

## Configuration Reference

### Environment Variables (`.env`)
```env
OPENAI_API_KEY=sk-...
ALPACA_API_KEY=...
ALPACA_SECRET_KEY=...
ALPACA_USE_PAPER=True
FINNHUB_API_KEY=...
FRED_API_KEY=...
COINDESK_API_KEY=...
```

### Default Config (`tradingagents/default_config.py`)
```python
DEFAULT_CONFIG = {
    "deep_think_llm": "o4-mini",       # Reasoning model
    "quick_think_llm": "gpt-4.1-nano", # Fast model
    "max_debate_rounds": 4,
    "max_risk_discuss_rounds": 3,
    "allow_shorts": False,             # BUY/HOLD/SELL mode
    "parallel_analysts": True,
    "online_tools": True,              # Use live APIs vs cache
    "max_parallel_tickers": 3,         # Concurrent ticker analyses
}
```

### WebUI Constants (`webui/config/constants.py`)
```python
COLORS = {
    "primary": "#3B82F6",
    "pending": "#94A3B8",
    "in_progress": "#F59E0B",
    "completed": "#10B981",
}

REFRESH_INTERVALS = {
    "fast": 2000,    # During analysis
    "medium": 10000, # Reports
    "slow": 60000,   # Account data
}
```

---

## Release Process

### Version Files
- **Primary**: `pyproject.toml` → `version = "X.Y.Z"`
- **Secondary**: `setup.py` (keep in sync)

### Release Steps
1. Make feature commits
2. Update version in `pyproject.toml`
3. Commit: `git commit -m "Bump version to X.Y.Z"`
4. Create release commit: `git commit --allow-empty -m "Release vX.Y.Z - Description"`
5. Push commits: `git push`
6. Create annotated tag:
```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z - Description

## What's New
- Feature 1
- Feature 2

## Changes
- Change details"
```
7. Push tag: `git push origin vX.Y.Z`
8. GitHub Actions workflow triggers automatically (runs tests, builds, publishes to PyPI)

### Commit Message Format
```
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## Testing

### Test Structure
```
tests/
  scanner/           # Scanner component tests
  webui/             # UI and state tests
  dataflows/         # Data flow tests
```

### Running Tests
```bash
pytest                              # All tests
pytest tests/scanner/ -v            # Verbose scanner tests
pytest -k "test_scan" --tb=short    # Pattern matching
```

### Test Pattern
```python
import pytest
from unittest.mock import patch, MagicMock

class TestMyFeature:
    def setup_method(self):
        """Called before each test"""
        pass

    @patch("module.external_api")
    def test_something(self, mock_api):
        mock_api.return_value = {"data": "value"}
        # Test logic
        assert result == expected
```

---

## Key File Reference

| File | Purpose | Key Functions/Classes |
|------|---------|----------------------|
| `tradingagents/graph/trading_graph.py` | Main orchestration | `TradingAgentsGraph.propagate()` |
| `tradingagents/dataflows/interface.py` | Unified data API (~1500 lines) | `@tool` decorated functions |
| `tradingagents/default_config.py` | Config defaults | `DEFAULT_CONFIG` dict |
| `webui/app_dash.py` | App factory | `create_app()`, `run_app()` |
| `webui/layout.py` | Layout assembly | `create_main_layout()` |
| `webui/utils/state.py` | Global state | `AppState` class, `app_state` instance |
| `webui/utils/local_storage.py` | SQLite persistence | `save_settings()`, `get_settings()` |
| `webui/utils/storage.py` | Settings defaults | `DEFAULT_SYSTEM_SETTINGS` |
| `webui/callbacks/control_callbacks.py` | Analysis control | Settings persistence, start/stop |
| `webui/callbacks/system_settings_callbacks.py` | System settings | API keys, LLM config |

---

## Parallel Execution

### Ticker Analysis
```python
# Controlled by setting: max_parallel_tickers (default 3)
# Location: webui/callbacks/control_callbacks.py

def get_max_parallel_tickers():
    return app_state.system_settings.get("max_parallel_tickers", 3)

# Uses ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=get_max_parallel_tickers()) as executor:
    futures = {executor.submit(analyze, symbol): symbol for symbol in symbols}
```

### Analyst Execution
```python
# Controlled by config: parallel_analysts (default True)
# Location: tradingagents/graph/setup.py

# When True, all 6 analysts run concurrently via ThreadPoolExecutor
# When False, analysts run sequentially
```

---

## State Flow in WebUI

```
User Action
    ↓
Callback triggered (webui/callbacks/*.py)
    ↓
Update AppState (webui/utils/state.py)
    ↓
Persist if needed (webui/utils/local_storage.py)
    ↓
Return updated component values
    ↓
UI updates
```

### AppState Key Properties
```python
app_state.analysis_running      # bool - analysis in progress
app_state.loop_enabled          # bool - loop mode active
app_state.market_hour_enabled   # bool - market hour mode active
app_state.symbol_states         # dict - per-symbol analysis state
app_state.system_settings       # dict - system configuration
app_state.scanner_running       # bool - scanner in progress
app_state.next_loop_run_time    # datetime - next loop iteration (EST/EDT)
```

---

## Important Notes

1. **Always read files before editing** - Use Read tool first
2. **Preserve crypto symbol format** - Keep `/USD` suffix
3. **Use thread-safe state access** - AppState has `_lock`
4. **Update pyproject.toml version** before tagging releases
5. **Settings require multiple file updates** - Follow the pattern above
6. **Callbacks need `prevent_initial_call=True`** to avoid load-time execution
7. **Test API connections** before assuming they work
