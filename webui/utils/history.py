"""
Analysis History Storage for TradingAgents WebUI
Persists analysis runs to SQLite database for later retrieval.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from webui.utils.local_storage import (
    save_analysis_run as db_save_run,
    list_analysis_runs as db_list_runs,
    get_analysis_run as db_get_run,
    delete_analysis_run as db_delete_run,
    save_analyst_report,
)


def generate_run_id(symbols: List[str], timestamp: datetime = None) -> str:
    """Generate a unique run ID based on symbols and timestamp."""
    if timestamp is None:
        timestamp = datetime.now()

    symbols_str = "_".join(sorted([s.replace("/", "-") for s in symbols[:3]]))
    if len(symbols) > 3:
        symbols_str += f"_+{len(symbols) - 3}"

    return f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{symbols_str}"


def save_analysis_run(app_state, symbols: List[str]) -> Optional[str]:
    """
    Save the current analysis run to SQLite database.

    Args:
        app_state: The AppState object containing all analysis data
        symbols: List of symbols that were analyzed

    Returns:
        The run_id if successful, None otherwise
    """
    try:
        timestamp = datetime.now()
        run_id = generate_run_id(symbols, timestamp)

        # Save run metadata
        db_save_run(
            run_id=run_id,
            symbols=symbols,
            tool_calls_count=app_state.tool_calls_count,
            llm_calls_count=app_state.llm_calls_count,
            generated_reports_count=app_state.generated_reports_count
        )

        # Save reports for each symbol (using run_id as session_id)
        for symbol in symbols:
            state = app_state.symbol_states.get(symbol, {})
            if not state:
                continue

            # Save current_reports
            current_reports = state.get("current_reports", {})
            agent_prompts = state.get("agent_prompts", {})

            for report_type, report_content in current_reports.items():
                if report_content:
                    prompt_content = agent_prompts.get(report_type)
                    save_analyst_report(
                        symbol=symbol,
                        report_type=report_type,
                        report_content=str(report_content),
                        prompt_content=str(prompt_content) if prompt_content else None,
                        session_id=run_id
                    )

        print(f"[HISTORY] Saved analysis run: {run_id}")
        return run_id

    except Exception as e:
        print(f"[HISTORY] Error saving analysis run: {e}")
        import traceback
        traceback.print_exc()
        return None


def list_analysis_runs(limit: int = 50) -> List[Dict[str, Any]]:
    """
    List all saved analysis runs.

    Args:
        limit: Maximum number of runs to return

    Returns:
        List of run metadata dictionaries, sorted by timestamp (newest first)
    """
    try:
        runs = db_list_runs(limit=limit)

        # Transform to expected format
        result = []
        for run in runs:
            result.append({
                "run_id": run["run_id"],
                "timestamp": run["timestamp"],
                "symbols": run["symbols"],
                "reports_count": run["generated_reports_count"],
            })

        return result

    except Exception as e:
        print(f"[HISTORY] Error listing runs: {e}")
        return []


def load_analysis_run(run_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a specific analysis run by ID.

    Args:
        run_id: The run ID to load

    Returns:
        The run data dictionary, or None if not found
    """
    try:
        run_data = db_get_run(run_id)

        if not run_data:
            print(f"[HISTORY] Run not found: {run_id}")
            return None

        print(f"[HISTORY] Loaded analysis run: {run_id}")
        return run_data

    except Exception as e:
        print(f"[HISTORY] Error loading run {run_id}: {e}")
        return None


def delete_analysis_run(run_id: str) -> bool:
    """
    Delete a specific analysis run.

    Args:
        run_id: The run ID to delete

    Returns:
        True if deleted, False otherwise
    """
    try:
        return db_delete_run(run_id)

    except Exception as e:
        print(f"[HISTORY] Error deleting run {run_id}: {e}")
        return False


def format_run_label(run: Dict[str, Any]) -> str:
    """Format a run for display in dropdown."""
    try:
        timestamp_str = run.get("timestamp", "")
        if timestamp_str:
            # Handle both datetime objects and strings
            if isinstance(timestamp_str, str):
                # Try parsing ISO format first, then SQLite format
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                except ValueError:
                    try:
                        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        timestamp = None
            else:
                timestamp = timestamp_str

            if timestamp:
                date_str = timestamp.strftime("%m/%d %H:%M")
            else:
                date_str = "Unknown"
        else:
            date_str = "Unknown"
    except Exception:
        date_str = "Unknown"

    symbols = run.get("symbols", [])
    if len(symbols) <= 3:
        symbols_str = ", ".join(symbols)
    else:
        symbols_str = f"{', '.join(symbols[:3])} +{len(symbols) - 3}"

    return f"{date_str} - {symbols_str}"
