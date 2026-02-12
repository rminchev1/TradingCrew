# CLAUDE.md

This file provides guidance to Claude Code when working with this repository. Follow these patterns to work efficiently without rediscovering conventions.

---

## MANDATORY REQUIREMENTS

### 1. Tests Are Required
**Every new feature, bug fix, or code change MUST include corresponding tests.**

- Create tests in the appropriate `tests/` subdirectory
- Tests must verify the new/changed functionality works correctly
- **MUST run `pytest` and verify ALL tests pass BEFORE committing**
- Do NOT skip this step - untested code should not be merged

**Pre-Commit Checklist:**
```bash
# ALWAYS run before git commit:
pytest                    # Run all tests
pytest tests/webui/ -v    # If changing WebUI code
pytest tests/scanner/ -v  # If changing scanner code
pytest tests/dataflows/ -v # If changing dataflows code
```

**If tests fail, DO NOT commit.** Fix the issues first.

### 2. Descriptive Release Messages
**Every release MUST have a meaningful, descriptive message.**

When creating a release tag, the message must include:
- Update `docs/CHANGELOG.md` with the new version and changes
- Clear summary of what's new
- List of features added
- List of bugs fixed
- Any breaking changes

Example format:
```
Release vX.Y.Z - Short Description

## What's New
- Feature: Added user-configurable parallel ticker setting
- Feature: Loop mode now shows next run time in EST/EDT

## Bug Fixes
- Fixed account bar not refreshing after trades
- Fixed market hours validation error

## Changes
- Updated default LLM model to o4-mini
- Improved error handling in scanner
```

### 3. Documentation Maintenance
**Documentation must be kept up-to-date with code changes.**

Documentation lives in the `docs/` folder:
```
docs/
  README.md              # Documentation index
  getting-started.md     # Quick start guide
  user-guide.md          # Complete user guide
  CHANGELOG.md           # Version history (UPDATE ON EVERY RELEASE)
  troubleshooting.md     # Common issues and solutions
  features/              # Feature-specific docs
    web-ui.md
    cli.md
    market-scanner.md
    loop-mode.md
    trading.md
  configuration/         # Configuration docs
    api-keys.md
    settings.md
```

When to update docs:
- **New feature**: Add to relevant feature doc or create new one
- **UI change**: Update `features/web-ui.md`
- **New setting**: Update `configuration/settings.md`
- **New API key**: Update `configuration/api-keys.md`
- **Bug fix affecting users**: Update `troubleshooting.md` if relevant
- **Every release**: Update `CHANGELOG.md` with version, date, and changes

### 4. Update CLAUDE.md After Meaningful Changes
**After completing any meaningful feature, refactor, or architectural change, CLAUDE.md MUST be updated.**

This is NOT optional. CLAUDE.md is the single source of truth for development patterns. Stale docs cause rediscovery of conventions and bugs.

**What to update:**
- **New UI pattern**: Add to Architecture Patterns or Common Development Tasks
- **New callback pattern**: Update Callback Patterns or add a new section
- **File added/removed/renamed**: Update Key File Reference table
- **New gotcha discovered**: Add to Critical Gotchas
- **Setting added**: Ensure the "Adding a New System Setting" section is still accurate
- **Architecture change**: Update the relevant Architecture section

**How to update:**
1. Read the current CLAUDE.md section you plan to modify (avoid stale edits)
2. Make surgical edits — update only what changed, don't rewrite entire sections
3. Keep the same formatting style (tables, code blocks, bullet lists)
4. If a section is now wrong, fix it; if a section is missing, add it

---

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
  callbacks/             # 17 callback modules (register_*_callbacks(app) functions, incl. panel_visibility)
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
6 Analyst Agents (sequential*) → Bull/Bear Debate → Research Manager Decision
                                                            ↓
                                Trader → Risk Debators (3) → Portfolio Manager → Trade Decision
```
*WebUI forces `parallel_analysts=False` for proper report status updates; tickers still run in parallel.

### Execution Threading Model
```
User clicks Start → on_control_button_click() → background analysis_thread()
                                                        ↓
                ThreadPoolExecutor (max_parallel_tickers workers)
                    ├─ Thread 1: analyze_single_ticker(AAPL)
                    │     └─ run_analysis() → graph.stream() loop
                    │           └─ check_pipeline_interrupt() ← pause/stop checkpoint
                    ├─ Thread 2: analyze_single_ticker(NVDA)
                    └─ Thread 3: analyze_single_ticker(TSLA)
```

Three execution modes share this pattern:
- **Single run**: Analyzes all symbols once
- **Loop mode**: Repeats at interval, checks `stop_loop` between iterations
- **Market hour mode**: Runs at scheduled EST/EDT times

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

### Dynamic Panel Visibility (DOM Removal Pattern)
Dashboard panels can be hidden/shown from the Settings page. Hidden panels are **fully removed from the DOM** (not CSS `display:none`) to keep the page lightweight.

**How it works:**
1. `create_trading_content()` in `layout.py` renders empty wrapper `<div>`s (e.g., `panel-wrapper-account-bar`)
2. `panel_visibility_callbacks.py` has a single callback that reads `system-settings-store` and populates each wrapper with the panel content (via `_build_*()` functions) or `[]` (empty) if hidden
3. `suppress_callback_exceptions=True` (set in `webui/config/constants.py`) allows callbacks targeting IDs inside hidden panels to silently fail

**9 togglable panels** (setting key → wrapper ID):
| Setting Key | Wrapper ID | Builder Function |
|---|---|---|
| `show_panel_account_bar` | `panel-wrapper-account-bar` | `_build_account_bar()` |
| `show_panel_scanner` | `panel-wrapper-scanner` | `_build_scanner_section()` |
| `show_panel_watchlist` | `panel-wrapper-watchlist` | `_build_watchlist_section()` |
| `show_panel_chart` | `panel-wrapper-main-trading-row` | `_build_main_trading_row()` |
| `show_panel_trading` | `panel-wrapper-main-trading-row` | `_build_main_trading_row()` |
| `show_panel_positions` | `panel-wrapper-positions` | `_build_positions_section()` |
| `show_panel_options` | `panel-wrapper-options` | `_build_options_section()` |
| `show_panel_reports` | `panel-wrapper-reports` | `_build_reports_section()` |
| `show_panel_logs` | `panel-wrapper-logs` | `_build_log_panel()` |

**Chart + Trading Controls** share a wrapper (`panel-wrapper-main-trading-row`). `_build_main_trading_row(show_chart, show_trading)` dynamically adjusts column widths — full-width when one is hidden, empty when both hidden.

**Critical rule — Store/Interval Relocation:**
When a panel can be removed from the DOM, any `dcc.Store` or `dcc.Interval` inside it will also be destroyed. These MUST be relocated to global scope in `create_stores()` / `create_intervals()` in `layout.py`. Relocated stores/intervals:
- `scanner-results-store`, `watchlist-store`, `watchlist-reorder-store`, `run-watchlist-store`, `log-last-index` → `create_stores()`
- `watchlist-refresh-interval`, `log-update-interval` → `create_intervals()`

**When adding a new panel to the visibility system**, update these files:
1. `webui/utils/storage.py` — add `show_panel_<name>` to `DEFAULT_SYSTEM_SETTINGS` + `safe_keys`
2. `webui/utils/state.py` — add to `AppState.system_settings`
3. `webui/components/system_settings.py` — add toggle in `create_dashboard_panels_section()`
4. `webui/callbacks/system_settings_callbacks.py` — add to all 4 callbacks (load/save/reset/import)
5. `webui/layout.py` — add wrapper div + builder function
6. `webui/callbacks/panel_visibility_callbacks.py` — add Output + builder call
7. Relocate any stores/intervals from the panel component to global scope

### Pipeline Control (Pause/Resume/Stop)
Pipeline execution can be paused, resumed, and stopped using `threading.Event` primitives in `AppState`:
- **`_pause_event`**: When cleared, `check_pipeline_interrupt()` blocks the calling thread. When set, execution continues.
- **`_stop_event`**: When set, all threads exit at the next checkpoint.
- **Checkpoints**: Inserted in the `graph.stream()` loop in `webui/components/analysis.py`. Each LangGraph node completion yields a chunk, providing a natural breakpoint.
- **Methods**: `pause_pipeline()`, `resume_pipeline()`, `stop_pipeline()`, `reset_pipeline_controls()`, `check_pipeline_interrupt(symbol)`

```
UI States:  Idle → [Start] → Running → [Pause] → Paused → [Resume] → Running
                                  ↓                           ↓
                               [Stop]                      [Stop]
                                  ↓                           ↓
                                Idle                        Idle
```

### Symbol Selection (Dropdown Pattern)
Both the **Chart** and **Reports** panels use `dbc.Select` dropdowns for symbol selection (not button grids). They sync via hidden `dbc.Pagination` components.

**Components:**
| Panel | Select ID | Populate Callback | Change Handler |
|-------|-----------|-------------------|----------------|
| Chart | `chart-symbol-select` | `update_chart_symbol_select()` in `chart_callbacks.py` | `handle_chart_symbol_select()` |
| Reports | `report-symbol-select` | `update_report_symbol_select()` in `report_callbacks.py` | `handle_report_symbol_select()` |

**How it works:**
1. Populate callbacks run on `app-store` + `refresh-interval`, read `app_state.symbol_states` to build options (`[{"label": "AAPL", "value": "1"}, ...]`), and set value based on `app_state.current_symbol`
2. Change handlers fire on Select value change, set `app_state.current_symbol`, and output to both `chart-pagination.active_page` and `report-pagination.active_page`
3. The hidden paginations trigger downstream chart data / report content callbacks
4. Populate callbacks use `State("...-symbol-select", "value")` and compare with new value — only output `dash.no_update` for value when unchanged, to avoid re-triggering the change handler on every refresh

**History mode:** When `history-selector` changes, `load_historical_run()` in `history_callbacks.py` outputs directly to `report-symbol-select.options` and `.value` with `📁`-prefixed labels.

**CSS:** `.symbol-select` class in `custom.css` styles both dropdowns. Light theme override: `body.theme-bw .symbol-select`.

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

### Thread-Local Storage for Parallel Ticker Analysis
```python
# CRITICAL: Global variables cause race conditions in parallel execution!
# BAD - race condition when analyzing AAPL and NVDA in parallel:
app_state.analyzing_symbol = symbol  # Gets overwritten by other threads!

# GOOD - use thread-local storage (webui/utils/state.py):
from webui.utils.state import get_thread_symbol, set_thread_symbol, clear_thread_symbol

# In analysis thread:
set_thread_symbol(symbol)      # Set at start
current = get_thread_symbol()  # Get current thread's symbol
clear_thread_symbol()          # Clear at end

# Tool tracking uses this pattern (tradingagents/agents/utils/agent_utils.py):
def _get_current_symbol():
    symbol = get_thread_symbol()  # Prefer thread-local
    if symbol:
        return symbol
    return app_state.analyzing_symbol  # Fallback for CLI/single-ticker
```

### LangGraph Execution Model
```python
# The graph is compiled WITHOUT checkpointing:
workflow.compile()  # No MemorySaver or persistence

# WebUI uses graph.stream() which yields after each node completes:
for chunk in graph.graph.stream(initial_state, stream_mode="values", config={"recursion_limit": 100}):
    # Each chunk = one node completed (analyst, debater, manager, etc.)
    # This is where pause/stop checkpoints live
    app_state.check_pipeline_interrupt(symbol=ticker)

# graph.invoke() is used in non-debug CLI mode (no streaming, no interrupts)
```

**Key facts:**
- No checkpoint-based resumption — pause works by blocking the thread, not saving state
- `recursion_limit=100` prevents infinite debate loops
- Each tool call has a 120s timeout (`agent_utils.py:timing_wrapper`)
- Debate rounds: investment = `2 * max_debate_rounds` messages, risk = `3 * max_risk_discuss_rounds` messages

### Analyst Tool Separation (IMPORTANT)
Each analyst has specific data sources - do NOT mix them:

| Analyst | Data Source | Tools |
|---------|-------------|-------|
| News Analyst | Finnhub API (CoinDesk for crypto) | `get_finnhub_news_online`, `get_coindesk_news` |
| Social Media Analyst | Reddit API only | `get_reddit_stock_info` |
| Market Analyst | Alpaca API | `get_alpaca_data`, `get_YFin_data` |
| Macro Analyst | FRED API | `get_macro_data` |

**Do NOT give News Analyst Reddit tools or Social Media Analyst news tools.**

### Callback Patterns
```python
# Use prevent_initial_call to avoid running on page load:
@app.callback(..., prevent_initial_call=True)

# Use allow_duplicate=True when multiple callbacks output to same component:
Output("component-id", "value", allow_duplicate=True)

# Access app_state from callbacks:
from webui.utils.state import app_state

# Dynamic buttons: Buttons rendered dynamically (e.g., control-button-container)
# may not exist in the DOM initially. Use suppress_callback_exceptions=True (already set)
# and guard callbacks with: if not n_clicks: return dash.no_update
```

### Database Operations
```python
# SQLite with threading - always use the lock:
from webui.utils.local_storage import save_settings, get_settings

# Tables: kv_store, analyst_reports, analysis_runs, scanner_results
```

### ChromaDB (Memory System)
```python
# ChromaDB is used for financial situation memory (bull/bear memory)
# Location: tradingagents/agents/utils/memory.py
# Uses embedded (in-memory) client, NOT http client

self.chroma_client = chromadb.Client(Settings(allow_reset=True))
```

**Known issue — `chromadb-client` package conflict:**
If `chromadb-client` (the thin/HTTP-only package) is installed alongside `chromadb`, it overwrites `chromadb/is_thin_client.py` to `is_thin_client = True`, which blocks the embedded client with:
```
RuntimeError: Chroma is running in http-only client mode
```
**Fix:** Uninstall `chromadb-client` and reinstall `chromadb`:
```bash
pip uninstall chromadb-client -y
pip install --force-reinstall chromadb
```

### Python Environment
The app runs using **pyenv Python 3.11.4** (`/Users/radoslavminchev/.pyenv/versions/3.11.4/`), not conda. Always use the correct pip when installing packages:
```bash
/Users/radoslavminchev/.pyenv/versions/3.11.4/bin/pip install <package>
```

**NumPy version constraint:** pandas and numexpr are compiled against NumPy 1.x. If `pip install --force-reinstall` pulls in NumPy 2.x, pandas will crash with `_ARRAY_API not found`. Fix with:
```bash
pip install "numpy<2"
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

# Reddit API (for live social sentiment)
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=TradingCrew/1.0
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

**Releases are triggered by pushing tags to main. GitHub Actions automatically runs tests, builds, and publishes to PyPI.**

### Version Files
- **Primary**: `pyproject.toml` → `version = "X.Y.Z"` (MUST update before tagging)
- **Secondary**: `setup.py` (keep in sync)

### Release Steps
1. Ensure all tests pass: `pytest`
2. Make feature commits with tests
3. Update version in `pyproject.toml`
4. Commit: `git commit -m "Bump version to X.Y.Z"`
5. Push commits: `git push`
6. Create annotated tag with **DESCRIPTIVE MESSAGE** (REQUIRED):

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z - Short Summary

## What's New
- Feature: Description of new feature
- Feature: Another new feature

## Bug Fixes
- Fixed: Description of bug that was fixed
- Fixed: Another bug fix

## Changes
- Changed: Description of change
- Updated: What was updated

## Breaking Changes (if any)
- Breaking: What breaks and how to migrate"
```

7. Push tag: `git push origin vX.Y.Z`
8. GitHub Actions triggers automatically:
   - Runs test suite
   - Builds package
   - Creates GitHub Release with your tag message
   - Publishes to PyPI

### Release Message Requirements
The tag message MUST include:
- **Summary line**: `Release vX.Y.Z - Brief description`
- **What's New**: List of new features
- **Bug Fixes**: List of bugs fixed (if any)
- **Changes**: Other notable changes

**Do NOT create releases with vague messages like "bug fixes" or "updates".**

---

## Testing (MANDATORY)

**Every feature, bug fix, or change requires tests. No exceptions.**

### Pre-Commit Workflow
```bash
# 1. Write your code changes
# 2. Write corresponding tests
# 3. Run ALL tests before committing:
pytest

# 4. Only if ALL tests pass, then commit:
git add <files>
git commit -m "Your message"
```

**NEVER commit code without running tests first. NEVER commit if tests fail.**

### Test Structure
```
tests/
  scanner/           # Scanner component tests (market_scanner, screeners)
  webui/             # UI and state tests (callbacks, state management)
  dataflows/         # Data flow tests (API integrations)
```

### Where to Put Tests
| Change Type | Test Location |
|-------------|---------------|
| Scanner feature | `tests/scanner/test_<feature>.py` |
| WebUI component | `tests/webui/test_<component>.py` |
| WebUI callback | `tests/webui/test_<callback_module>.py` |
| State management | `tests/webui/test_state.py` |
| Pipeline controls | `tests/webui/test_pipeline_controls.py` |
| Data flow/API | `tests/dataflows/test_<module>.py` |
| Settings | `tests/webui/test_settings.py` |

### Running Tests
```bash
pytest                              # All tests (run before committing!)
pytest tests/scanner/ -v            # Verbose scanner tests
pytest tests/webui/ -v              # WebUI tests
pytest -k "test_scan" --tb=short    # Pattern matching
pytest --tb=long                    # Full tracebacks for debugging
```

### Test Pattern
```python
import pytest
from unittest.mock import patch, MagicMock

class TestMyFeature:
    """Tests for MyFeature - describe what you're testing."""

    def setup_method(self):
        """Called before each test - reset state here."""
        pass

    def test_feature_does_expected_thing(self):
        """Test that feature works in normal case."""
        result = my_function("input")
        assert result == "expected_output"

    def test_feature_handles_edge_case(self):
        """Test edge case - empty input."""
        result = my_function("")
        assert result is None

    @patch("module.external_api")
    def test_feature_with_mocked_api(self, mock_api):
        """Test with mocked external dependency."""
        mock_api.return_value = {"data": "value"}
        result = function_that_calls_api()
        assert result == expected
        mock_api.assert_called_once_with("expected_arg")
```

### Test Checklist Before Committing
- [ ] New tests written for new functionality
- [ ] All existing tests still pass (`pytest`)
- [ ] Edge cases covered (empty input, None, errors)
- [ ] Mocked external APIs/services where appropriate

---

## Live API with Fallback Pattern

When adding new external API integrations, follow this pattern (see `tradingagents/dataflows/reddit_live.py`):

```python
# 1. Try live API first
try:
    if is_api_available():
        result = fetch_live_data(params)
        if result:
            return format_result(result)
except Exception as e:
    print(f"[API] Live API error, falling back: {e}")

# 2. Fallback to cached/alternative data
return get_cached_data(params)
```

**Key principles:**
- Live API should be optional (graceful degradation)
- Credentials configurable via both `.env` AND Settings UI
- Use singleton pattern for API clients (`RedditLiveClient`)
- Always provide informative fallback message if no data

---

## Tool Output Tracking

Tool calls are tracked for UI display in `tradingagents/agents/utils/agent_utils.py`:

```python
# Each tool call records:
tool_call_info = {
    "timestamp": "HH:MM:SS",
    "tool_name": "get_finnhub_news",
    "inputs": {"ticker": "AAPL"},
    "output": "...",  # Result or error
    "execution_time": "1.23s",
    "status": "success",  # or "error", "timeout"
    "agent_type": "NEWS",  # For filtering by analyst
    "symbol": "AAPL"  # For filtering by ticker (thread-safe!)
}
app_state.tool_calls_log.append(tool_call_info)
```

**UI Display**: Modal shows filtered tool outputs via `app_state.get_tool_calls_for_display(agent_filter, symbol_filter)`

---

## Key File Reference

| File | Purpose | Key Functions/Classes |
|------|---------|----------------------|
| `tradingagents/graph/trading_graph.py` | Main orchestration | `TradingAgentsGraph.propagate()` |
| `tradingagents/dataflows/interface.py` | Unified data API (~1500 lines) | `@tool` decorated functions |
| `tradingagents/dataflows/reddit_live.py` | Live Reddit API | `RedditLiveClient`, `fetch_live_company_news()` |
| `tradingagents/agents/utils/agent_utils.py` | Tool tracking & timing | `timing_wrapper()`, `_get_current_symbol()` |
| `tradingagents/default_config.py` | Config defaults | `DEFAULT_CONFIG` dict |
| `webui/app_dash.py` | App factory | `create_app()`, `run_app()` |
| `webui/layout.py` | Layout assembly + panel builders | `create_main_layout()`, `_build_*()` functions, `create_stores()`, `create_intervals()` |
| `webui/utils/state.py` | Global state + thread-local + pipeline control | `AppState`, `get_thread_symbol()`, `check_pipeline_interrupt()` |
| `webui/utils/local_storage.py` | SQLite persistence | `save_settings()`, `get_settings()` |
| `webui/utils/storage.py` | Settings defaults | `DEFAULT_SYSTEM_SETTINGS` |
| `webui/callbacks/control_callbacks.py` | Analysis control | Settings persistence, start/stop/pause/resume |
| `webui/callbacks/status_callbacks.py` | Status table & refresh | `update_status_table()`, `manage_refresh_intervals_and_status()` |
| `webui/callbacks/system_settings_callbacks.py` | System settings | API keys, LLM config, panel visibility |
| `webui/callbacks/panel_visibility_callbacks.py` | Panel hide/show | `render_visible_panels()` — populates wrapper divs |
| `webui/callbacks/chart_callbacks.py` | Chart + symbol select | `update_chart_symbol_select()`, `handle_chart_symbol_select()`, `update_chart()` |
| `webui/callbacks/report_callbacks.py` | Reports + symbol select | `update_report_symbol_select()`, `handle_report_symbol_select()` |
| `webui/callbacks/history_callbacks.py` | History save/load | `load_historical_run()` → populates `report-symbol-select` |
| `webui/components/chart_panel.py` | Chart panel UI | `create_chart_panel()` — `dbc.Select(id="chart-symbol-select")` |
| `webui/components/reports_panel.py` | Reports panel UI | `create_reports_panel()` — `dbc.Select(id="report-symbol-select")` |
| `webui/components/system_settings.py` | Settings page UI | `create_dashboard_panels_section()`, `create_api_keys_section()` |
| `webui/components/analysis.py` | Analysis execution | `run_analysis()` (stream loop with pause/stop checkpoints) |
| `tradingagents/agents/utils/memory.py` | ChromaDB memory | `FinancialSituationMemory` (bull/bear memory) |
| `tradingagents/graph/setup.py` | Graph construction | `setup_graph()`, `_create_parallel_analysts_coordinator()` |
| `tradingagents/graph/conditional_logic.py` | Routing functions | `should_continue_debate()`, `should_continue_risk_analysis()` |

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
# Controlled by config: parallel_analysts (default True in config, but WebUI overrides to False)
# Location: tradingagents/graph/setup.py

# When True: all analysts run concurrently via ThreadPoolExecutor (0.5s stagger between starts)
#   - Each analyst gets a deep-copied state for isolation
#   - Results merged back after all complete
# When False: analysts run as sequential LangGraph nodes (WebUI default)
#   - Each node completion yields a stream chunk → natural breakpoint for pause/stop
#   - WebUI uses False for proper per-agent status updates in the UI

# IMPORTANT: webui/components/analysis.py line 246 forces:
config["parallel_analysts"] = False  # Sequential analysts for proper report updates
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

# Pipeline control
app_state.pipeline_paused       # bool - pipeline is paused
app_state.pipeline_stopped      # bool - pipeline was stopped
app_state.paused_symbols        # set  - symbols currently blocked at a breakpoint
app_state._pause_event          # threading.Event - cleared=paused, set=running
app_state._stop_event           # threading.Event - set=stop requested
```

---

## Important Notes

1. **TESTS ARE MANDATORY** - Every code change must have tests. Run `pytest` BEFORE every commit. Never commit if tests fail.
2. **DESCRIPTIVE RELEASE MESSAGES** - Never use vague release messages. List features, fixes, changes.
3. **UPDATE DOCUMENTATION** - Keep docs/ in sync with code changes. Always update CHANGELOG.md on release.
4. **Always read files before editing** - Use Read tool first
5. **Preserve crypto symbol format** - Keep `/USD` suffix
6. **Use thread-safe state access** - AppState has `_lock`
7. **Use thread-local for parallel ticker data** - Use `get_thread_symbol()` not `app_state.analyzing_symbol` in tool tracking
8. **Keep analyst tools separate** - News→Finnhub, Social→Reddit, don't mix
9. **Update pyproject.toml version** before tagging releases
10. **Settings require multiple file updates** - Follow the pattern above
11. **Callbacks need `prevent_initial_call=True`** to avoid load-time execution
12. **Test API connections** before assuming they work
13. **Pipeline control uses `threading.Event`** — `check_pipeline_interrupt()` must be called between stream chunks; it blocks on pause and returns `"stopped"` on stop
14. **`stop_pipeline()` must unblock paused threads** — Always call `_pause_event.set()` before `_stop_event.set()` to prevent deadlocked threads
15. **`reset()` resets pipeline controls** — Any fresh analysis start calls `reset()` which calls `reset_pipeline_controls()` automatically
16. **Dynamic buttons need guard checks** — Callbacks for dynamically-rendered buttons (like `pause-resume-btn`) must check `if not n_clicks: return dash.no_update`
17. **Stores/Intervals must survive panel removal** — If a `dcc.Store` or `dcc.Interval` is inside a hideable panel, relocate it to `create_stores()`/`create_intervals()` in `layout.py`
18. **Never install `chromadb-client` alongside `chromadb`** — It overwrites `is_thin_client=True` and breaks embedded mode. Fix: `pip uninstall chromadb-client && pip install --force-reinstall chromadb`
19. **NumPy must stay < 2.0** — pandas/numexpr are compiled against NumPy 1.x. If a dependency upgrade pulls NumPy 2.x, fix with `pip install "numpy<2"`
20. **App uses pyenv Python 3.11.4** — Not conda. Use `/Users/radoslavminchev/.pyenv/versions/3.11.4/bin/pip` for the correct environment
21. **Symbol selection uses `dbc.Select` dropdowns** — NOT button grids. Chart: `chart-symbol-select`, Reports: `report-symbol-select`. Values are 1-indexed strings mapping to `app_state.symbol_states` keys. Synced via hidden `dbc.Pagination` components.
22. **UPDATE CLAUDE.md after meaningful changes** — Any new feature, pattern change, or architectural update must be reflected in this file. Read the section first, then make surgical edits.
