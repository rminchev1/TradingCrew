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
