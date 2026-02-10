"""
Unit tests for AppState analyst reports persistence integration
"""

import pytest
from unittest.mock import patch, MagicMock


class TestAppStateReportsIntegration:
    """Tests for AppState integration with persistent report storage"""

    def test_load_reports_from_storage(self, tmp_storage, app_state):
        """Test loading reports from storage into state"""
        from webui.utils import local_storage

        session_id = "load-test-session"
        symbol = "LOAD_TEST"

        # Save reports directly to storage
        local_storage.save_analyst_report(symbol, "market_report", "Market content", session_id=session_id)
        local_storage.save_analyst_report(symbol, "news_report", "News content", session_id=session_id)

        # Load into state
        result = app_state.load_reports_from_storage(symbol, session_id)

        assert result is True

        # Verify reports are in state
        state = app_state.get_state(symbol)
        assert state is not None
        assert state["current_reports"]["market_report"] == "Market content"
        assert state["current_reports"]["news_report"] == "News content"

    def test_load_reports_marks_agents_completed(self, tmp_storage, app_state):
        """Test that loading reports marks corresponding agents as completed"""
        from webui.utils import local_storage

        session_id = "agent-status-test"
        symbol = "STATUS_TEST"

        # Save reports
        local_storage.save_analyst_report(symbol, "market_report", "Market content", session_id=session_id)
        local_storage.save_analyst_report(symbol, "fundamentals_report", "Fundamentals content", session_id=session_id)

        # Load into state
        app_state.load_reports_from_storage(symbol, session_id)

        # Verify agent statuses
        state = app_state.get_state(symbol)
        assert state["agent_statuses"]["Market Analyst"] == "completed"
        assert state["agent_statuses"]["Fundamentals Analyst"] == "completed"
        # Unloaded agents should still be pending
        assert state["agent_statuses"]["News Analyst"] == "pending"

    def test_load_reports_with_prompts(self, tmp_storage, app_state):
        """Test that loading reports also loads prompts"""
        from webui.utils import local_storage

        session_id = "prompt-test-session"
        symbol = "PROMPT_TEST"

        # Save report with prompt
        local_storage.save_analyst_report(
            symbol, "market_report", "Market content",
            prompt_content="System prompt for market analyst",
            session_id=session_id
        )

        # Load into state
        app_state.load_reports_from_storage(symbol, session_id)

        # Verify prompt is loaded
        state = app_state.get_state(symbol)
        assert state["agent_prompts"]["market_report"] == "System prompt for market analyst"

    def test_load_reports_nonexistent_returns_false(self, tmp_storage, app_state):
        """Test that loading nonexistent reports returns False"""
        result = app_state.load_reports_from_storage("NONEXISTENT", "fake-session")

        assert result is False

    def test_load_reports_initializes_symbol_state(self, tmp_storage, app_state):
        """Test that load_reports_from_storage initializes state if needed"""
        from webui.utils import local_storage

        session_id = "init-test-session"
        symbol = "INIT_TEST"

        # Save a report
        local_storage.save_analyst_report(symbol, "market_report", "Content", session_id=session_id)

        # Ensure symbol not in state
        assert symbol not in app_state.symbol_states

        # Load reports
        app_state.load_reports_from_storage(symbol, session_id)

        # Verify state was initialized
        assert symbol in app_state.symbol_states
        state = app_state.get_state(symbol)
        assert state["current_reports"]["market_report"] == "Content"

    def test_load_reports_updates_report_count(self, tmp_storage, app_state):
        """Test that loading reports updates the generated reports count"""
        from webui.utils import local_storage

        session_id = "count-test-session"
        symbol = "COUNT_TEST"

        # Save multiple reports
        local_storage.save_analyst_report(symbol, "market_report", "Content 1", session_id=session_id)
        local_storage.save_analyst_report(symbol, "news_report", "Content 2", session_id=session_id)
        local_storage.save_analyst_report(symbol, "fundamentals_report", "Content 3", session_id=session_id)

        initial_count = app_state.generated_reports_count

        # Load reports
        app_state.load_reports_from_storage(symbol, session_id)

        # Report count should increase
        assert app_state.generated_reports_count > initial_count


class TestAppStateReportsPersistence:
    """Tests for automatic report persistence when processing chunks"""

    def test_process_chunk_persists_analyst_report(self, tmp_storage, app_state):
        """Test that processing a chunk persists the analyst report"""
        from webui.utils import local_storage

        symbol = "CHUNK_TEST"
        app_state.init_symbol_state(symbol)
        state = app_state.get_state(symbol)

        # Set first analyst to in_progress
        state["agent_statuses"]["Market Analyst"] = "in_progress"

        # Process a chunk with a market report
        chunk = {
            "market_report": "This is the market analysis from chunk processing"
        }
        app_state.process_chunk_updates(chunk, symbol)

        # Verify report is in state
        assert state["current_reports"]["market_report"] == "This is the market analysis from chunk processing"

        # Verify report was persisted to storage
        session_id = state["session_id"]
        stored_report = local_storage.get_analyst_report(symbol, "market_report", session_id)
        assert stored_report is not None
        assert stored_report["content"] == "This is the market analysis from chunk processing"

    def test_process_chunk_persists_debate_reports(self, tmp_storage, app_state):
        """Test that processing debate chunks persists bull/bear reports"""
        from webui.utils import local_storage

        symbol = "DEBATE_TEST"
        app_state.init_symbol_state(symbol)
        state = app_state.get_state(symbol)

        # Process a chunk with investment debate state
        chunk = {
            "investment_debate_state": {
                "bull_history": "Bull argument: The stock has strong momentum",
                "bear_history": "Bear argument: The valuation is stretched",
                "bull_messages": ["Bull argument: The stock has strong momentum"],
                "bear_messages": ["Bear argument: The valuation is stretched"]
            }
        }
        app_state.process_chunk_updates(chunk, symbol)

        # Verify reports are in state
        assert "Bull argument" in state["current_reports"]["bull_report"]
        assert "Bear argument" in state["current_reports"]["bear_report"]

        # Verify reports were persisted
        session_id = state["session_id"]
        bull_report = local_storage.get_analyst_report(symbol, "bull_report", session_id)
        bear_report = local_storage.get_analyst_report(symbol, "bear_report", session_id)
        assert bull_report is not None
        assert bear_report is not None

    def test_process_chunk_persists_final_decision(self, tmp_storage, app_state):
        """Test that processing final decision persists it"""
        from webui.utils import local_storage

        symbol = "DECISION_TEST"
        app_state.init_symbol_state(symbol)
        state = app_state.get_state(symbol)

        # Process a chunk with risk debate final decision
        chunk = {
            "risk_debate_state": {
                "judge_decision": "FINAL DECISION: BUY 100 shares at market price"
            }
        }
        app_state.process_chunk_updates(chunk, symbol)

        # Verify decision is in state
        assert "FINAL DECISION" in state["current_reports"]["final_trade_decision"]

        # Verify decision was persisted
        session_id = state["session_id"]
        decision = local_storage.get_analyst_report(symbol, "final_trade_decision", session_id)
        assert decision is not None
        assert "FINAL DECISION" in decision["content"]


class TestAppStateMultipleSymbols:
    """Tests for handling multiple symbols with persistent storage"""

    def test_load_reports_for_multiple_symbols(self, tmp_storage, app_state):
        """Test loading reports for multiple symbols"""
        from webui.utils import local_storage

        symbols = ["SYM1", "SYM2", "SYM3"]
        session_ids = ["session-1", "session-2", "session-3"]

        # Save reports for each symbol
        for symbol, session_id in zip(symbols, session_ids):
            local_storage.save_analyst_report(symbol, "market_report", f"Report for {symbol}", session_id=session_id)

        # Load each symbol
        for symbol, session_id in zip(symbols, session_ids):
            app_state.load_reports_from_storage(symbol, session_id)

        # Verify all symbols have their reports
        for symbol in symbols:
            state = app_state.get_state(symbol)
            assert state is not None
            assert state["current_reports"]["market_report"] == f"Report for {symbol}"

    def test_reports_isolated_between_symbols(self, tmp_storage, app_state):
        """Test that reports for different symbols don't interfere"""
        from webui.utils import local_storage

        # Save different reports for different symbols
        local_storage.save_analyst_report("AAPL", "market_report", "AAPL market report", session_id="aapl-session")
        local_storage.save_analyst_report("NVDA", "market_report", "NVDA market report", session_id="nvda-session")

        # Load both
        app_state.load_reports_from_storage("AAPL", "aapl-session")
        app_state.load_reports_from_storage("NVDA", "nvda-session")

        # Verify isolation
        aapl_state = app_state.get_state("AAPL")
        nvda_state = app_state.get_state("NVDA")

        assert aapl_state["current_reports"]["market_report"] == "AAPL market report"
        assert nvda_state["current_reports"]["market_report"] == "NVDA market report"


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
def app_state(tmp_storage):
    """Create a fresh AppState instance for testing"""
    from webui.utils.state import AppState

    state = AppState()
    yield state

    # Reset state
    state.reset()
