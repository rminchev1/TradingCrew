"""
Unit tests for the history module (SQLite-based analysis history)
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime


class TestGenerateRunId:
    """Tests for run ID generation"""

    def test_generate_run_id_format(self, tmp_storage):
        """Test that run IDs are generated with correct format"""
        from webui.utils.history import generate_run_id

        run_id = generate_run_id(["AAPL", "NVDA"])

        # Should contain date and symbols
        assert "_" in run_id
        parts = run_id.split("_")
        assert len(parts) >= 3  # date, time, symbols

    def test_generate_run_id_with_many_symbols(self, tmp_storage):
        """Test run ID generation with more than 3 symbols"""
        from webui.utils.history import generate_run_id

        run_id = generate_run_id(["A", "B", "C", "D", "E"])

        # Should include +N suffix for extra symbols
        assert "+2" in run_id

    def test_generate_run_id_with_crypto_symbol(self, tmp_storage):
        """Test run ID generation handles crypto symbols"""
        from webui.utils.history import generate_run_id

        run_id = generate_run_id(["BTC/USD", "ETH/USD"])

        # Slashes should be replaced
        assert "/" not in run_id
        assert "BTC-USD" in run_id

    def test_generate_run_id_with_custom_timestamp(self, tmp_storage):
        """Test run ID generation with custom timestamp"""
        from webui.utils.history import generate_run_id

        timestamp = datetime(2024, 6, 15, 10, 30, 0)
        run_id = generate_run_id(["AAPL"], timestamp)

        assert "20240615_103000" in run_id


class TestSaveAnalysisRun:
    """Tests for saving analysis runs"""

    def test_save_analysis_run(self, tmp_storage, mock_app_state):
        """Test saving an analysis run"""
        from webui.utils.history import save_analysis_run

        symbols = ["AAPL", "NVDA"]
        run_id = save_analysis_run(mock_app_state, symbols)

        assert run_id is not None
        assert "_AAPL_NVDA" in run_id

    def test_save_analysis_run_persists_reports(self, tmp_storage, mock_app_state):
        """Test that saving a run persists all reports"""
        from webui.utils.history import save_analysis_run, load_analysis_run

        symbols = ["AAPL"]
        run_id = save_analysis_run(mock_app_state, symbols)

        # Load and verify reports
        run = load_analysis_run(run_id)

        assert run is not None
        assert "AAPL" in run["symbol_states"]
        reports = run["symbol_states"]["AAPL"]["reports"]
        assert "market_report" in reports
        assert reports["market_report"] == "AAPL market analysis"

    def test_save_analysis_run_with_empty_symbols(self, tmp_storage, mock_app_state):
        """Test saving with empty symbols list"""
        from webui.utils.history import save_analysis_run

        run_id = save_analysis_run(mock_app_state, [])

        # Should still create a run (empty but valid)
        assert run_id is not None


class TestListAnalysisRuns:
    """Tests for listing analysis runs"""

    def test_list_analysis_runs(self, tmp_storage, mock_app_state):
        """Test listing analysis runs"""
        from webui.utils.history import save_analysis_run, list_analysis_runs

        # Save a few runs
        save_analysis_run(mock_app_state, ["AAPL"])
        save_analysis_run(mock_app_state, ["NVDA"])

        runs = list_analysis_runs()

        assert len(runs) >= 2

    def test_list_analysis_runs_returns_metadata(self, tmp_storage, mock_app_state):
        """Test that list returns expected metadata"""
        from webui.utils.history import save_analysis_run, list_analysis_runs

        save_analysis_run(mock_app_state, ["TSLA"])

        runs = list_analysis_runs()
        run = runs[0]  # Most recent

        assert "run_id" in run
        assert "timestamp" in run
        assert "symbols" in run
        assert "reports_count" in run

    def test_list_analysis_runs_sorted_newest_first(self, tmp_storage, mock_app_state):
        """Test that runs are sorted newest first"""
        from webui.utils.history import save_analysis_run, list_analysis_runs
        import time

        run_id_1 = save_analysis_run(mock_app_state, ["A"])
        time.sleep(1.1)  # Need 1+ second for SQLite timestamp precision
        run_id_2 = save_analysis_run(mock_app_state, ["B"])

        runs = list_analysis_runs()
        run_ids = [r["run_id"] for r in runs]

        assert run_ids.index(run_id_2) < run_ids.index(run_id_1)

    def test_list_analysis_runs_limit(self, tmp_storage, mock_app_state):
        """Test list respects limit parameter"""
        from webui.utils.history import save_analysis_run, list_analysis_runs

        for i in range(5):
            mock_app_state.symbol_states = {f"SYM{i}": {"current_reports": {}, "agent_prompts": {}}}
            save_analysis_run(mock_app_state, [f"SYM{i}"])

        runs = list_analysis_runs(limit=2)

        assert len(runs) == 2


class TestLoadAnalysisRun:
    """Tests for loading analysis runs"""

    def test_load_analysis_run(self, tmp_storage, mock_app_state):
        """Test loading an analysis run"""
        from webui.utils.history import save_analysis_run, load_analysis_run

        run_id = save_analysis_run(mock_app_state, ["AAPL"])

        run = load_analysis_run(run_id)

        assert run is not None
        assert run["run_id"] == run_id
        assert run["symbols"] == ["AAPL"]

    def test_load_nonexistent_run(self, tmp_storage):
        """Test loading a run that doesn't exist"""
        from webui.utils.history import load_analysis_run

        run = load_analysis_run("nonexistent-run-id")

        assert run is None

    def test_load_run_includes_symbol_states(self, tmp_storage, mock_app_state):
        """Test that loaded run includes symbol states"""
        from webui.utils.history import save_analysis_run, load_analysis_run

        run_id = save_analysis_run(mock_app_state, ["AAPL"])

        run = load_analysis_run(run_id)

        assert "symbol_states" in run
        assert "AAPL" in run["symbol_states"]


class TestDeleteAnalysisRun:
    """Tests for deleting analysis runs"""

    def test_delete_analysis_run(self, tmp_storage, mock_app_state):
        """Test deleting an analysis run"""
        from webui.utils.history import save_analysis_run, load_analysis_run, delete_analysis_run

        run_id = save_analysis_run(mock_app_state, ["AAPL"])

        # Verify exists
        assert load_analysis_run(run_id) is not None

        # Delete
        result = delete_analysis_run(run_id)
        assert result is True

        # Verify deleted
        assert load_analysis_run(run_id) is None

    def test_delete_nonexistent_run(self, tmp_storage):
        """Test deleting a run that doesn't exist"""
        from webui.utils.history import delete_analysis_run

        result = delete_analysis_run("nonexistent-run-id")

        assert result is False


class TestCreateSymbolButtons:
    """Tests for create_symbol_buttons function used in history view"""

    def test_create_symbol_buttons_basic(self, tmp_storage):
        """Test creating symbol buttons with basic input"""
        from webui.callbacks.history_callbacks import create_symbol_buttons

        buttons = create_symbol_buttons(["AAPL", "NVDA"], active_index=0)

        # Should be a ButtonGroup
        assert buttons is not None
        # First button should have AAPL and be active (primary color)
        assert len(buttons.children) == 2

    def test_create_symbol_buttons_active_state(self, tmp_storage):
        """Test that active button is correctly marked"""
        from webui.callbacks.history_callbacks import create_symbol_buttons

        buttons = create_symbol_buttons(["A", "B", "C"], active_index=1)

        # Second button (index 1) should be active
        assert buttons.children[0].color == "outline-primary"  # Not active
        assert buttons.children[1].color == "primary"  # Active
        assert buttons.children[2].color == "outline-primary"  # Not active

    def test_create_symbol_buttons_history_mode(self, tmp_storage):
        """Test symbol buttons in history mode include folder icon"""
        from webui.callbacks.history_callbacks import create_symbol_buttons

        buttons = create_symbol_buttons(["AAPL"], active_index=0, is_history=True)

        # History mode should prefix with folder icon
        assert "📁" in buttons.children[0].children

    def test_create_symbol_buttons_button_ids(self, tmp_storage):
        """Test that buttons have correct pattern-matching IDs"""
        from webui.callbacks.history_callbacks import create_symbol_buttons

        buttons = create_symbol_buttons(["A", "B"], active_index=0)

        # Check IDs are pattern-matching dicts with correct type
        assert buttons.children[0].id == {"type": "report-symbol-btn", "index": 0}
        assert buttons.children[1].id == {"type": "report-symbol-btn", "index": 1}


class TestHistoryDebateReports:
    """Tests for debate reports in history storage"""

    def test_save_and_load_debate_reports(self, tmp_storage, mock_app_state_with_debates):
        """Test that debate reports are saved and loaded correctly"""
        from webui.utils.history import save_analysis_run, load_analysis_run

        symbols = ["AAPL"]
        run_id = save_analysis_run(mock_app_state_with_debates, symbols)

        # Load and verify debate reports are present
        run = load_analysis_run(run_id)
        assert run is not None

        reports = run["symbol_states"]["AAPL"]["reports"]
        assert "bull_report" in reports
        assert "bear_report" in reports
        assert reports["bull_report"] == "Bullish thesis for AAPL"
        assert reports["bear_report"] == "Bearish thesis for AAPL"

    def test_save_and_load_risk_debate_reports(self, tmp_storage, mock_app_state_with_debates):
        """Test that risk debate reports are saved and loaded correctly"""
        from webui.utils.history import save_analysis_run, load_analysis_run

        symbols = ["AAPL"]
        run_id = save_analysis_run(mock_app_state_with_debates, symbols)

        # Load and verify risk debate reports are present
        run = load_analysis_run(run_id)
        reports = run["symbol_states"]["AAPL"]["reports"]

        assert "risky_report" in reports
        assert "safe_report" in reports
        assert "neutral_report" in reports
        assert reports["risky_report"] == "Aggressive position recommendation"
        assert reports["safe_report"] == "Conservative position recommendation"
        assert reports["neutral_report"] == "Balanced position recommendation"


class TestFormatRunLabel:
    """Tests for formatting run labels"""

    def test_format_run_label(self, tmp_storage):
        """Test formatting a run label"""
        from webui.utils.history import format_run_label

        run = {
            "timestamp": "2024-06-15 10:30:00",
            "symbols": ["AAPL", "NVDA"]
        }

        label = format_run_label(run)

        assert "06/15" in label
        assert "10:30" in label
        assert "AAPL" in label
        assert "NVDA" in label

    def test_format_run_label_many_symbols(self, tmp_storage):
        """Test formatting with more than 3 symbols"""
        from webui.utils.history import format_run_label

        run = {
            "timestamp": "2024-06-15 10:30:00",
            "symbols": ["A", "B", "C", "D", "E"]
        }

        label = format_run_label(run)

        assert "+2" in label

    def test_format_run_label_missing_timestamp(self, tmp_storage):
        """Test formatting with missing timestamp"""
        from webui.utils.history import format_run_label

        run = {
            "symbols": ["AAPL"]
        }

        label = format_run_label(run)

        assert "Unknown" in label
        assert "AAPL" in label

    def test_format_run_label_iso_format(self, tmp_storage):
        """Test formatting with ISO format timestamp"""
        from webui.utils.history import format_run_label

        run = {
            "timestamp": "2024-06-15T10:30:00",
            "symbols": ["AAPL"]
        }

        label = format_run_label(run)

        assert "06/15" in label
        assert "10:30" in label


# Pytest fixtures
@pytest.fixture
def tmp_storage(tmp_path, monkeypatch):
    """Create a temporary database for testing"""
    from webui.utils import local_storage

    # Override the database path
    test_db_path = tmp_path / "test_tradingcrew.db"
    monkeypatch.setattr(local_storage, "DB_PATH", test_db_path)
    monkeypatch.setattr(local_storage, "DB_DIR", tmp_path)

    # Initialize the database
    local_storage.init_db()

    yield tmp_path

    # Cleanup
    if test_db_path.exists():
        test_db_path.unlink()


@pytest.fixture
def mock_app_state():
    """Create a mock AppState for testing"""
    state = MagicMock()
    state.tool_calls_count = 10
    state.llm_calls_count = 5
    state.generated_reports_count = 3
    state.symbol_states = {
        "AAPL": {
            "current_reports": {
                "market_report": "AAPL market analysis",
                "news_report": "AAPL news analysis"
            },
            "agent_prompts": {
                "market_report": "System prompt for market"
            }
        }
    }
    return state


@pytest.fixture
def mock_app_state_with_debates():
    """Create a mock AppState with debate reports for testing"""
    state = MagicMock()
    state.tool_calls_count = 15
    state.llm_calls_count = 10
    state.generated_reports_count = 9
    state.symbol_states = {
        "AAPL": {
            "current_reports": {
                "market_report": "AAPL market analysis",
                "news_report": "AAPL news analysis",
                "bull_report": "Bullish thesis for AAPL",
                "bear_report": "Bearish thesis for AAPL",
                "risky_report": "Aggressive position recommendation",
                "safe_report": "Conservative position recommendation",
                "neutral_report": "Balanced position recommendation",
                "research_manager_report": "Research manager synthesis",
                "final_trade_decision": "Final decision: BUY"
            },
            "agent_prompts": {
                "market_report": "System prompt for market",
                "bull_report": "Bull researcher prompt",
                "bear_report": "Bear researcher prompt"
            }
        }
    }
    return state
