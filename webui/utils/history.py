"""
Analysis History Storage for TradingAgents WebUI
Persists analysis runs to JSON files for later retrieval.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


# History storage directory
HISTORY_DIR = Path(__file__).parent.parent.parent / "analysis_history"


def ensure_history_dir():
    """Ensure the history directory exists."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


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
    Save the current analysis run to a JSON file.

    Args:
        app_state: The AppState object containing all analysis data
        symbols: List of symbols that were analyzed

    Returns:
        The run_id if successful, None otherwise
    """
    try:
        ensure_history_dir()

        timestamp = datetime.now()
        run_id = generate_run_id(symbols, timestamp)

        # Collect data to save
        run_data = {
            "run_id": run_id,
            "timestamp": timestamp.isoformat(),
            "symbols": symbols,
            "symbol_states": {},
            "tool_calls_count": app_state.tool_calls_count,
            "llm_calls_count": app_state.llm_calls_count,
            "generated_reports_count": app_state.generated_reports_count,
        }

        # Save state for each symbol
        for symbol in symbols:
            state = app_state.symbol_states.get(symbol, {})
            if state:
                # Extract serializable data
                symbol_data = {
                    "agent_statuses": state.get("agent_statuses", {}),
                    "reports": {},
                    "prompts": {},
                    "final_decision": state.get("final_decision", {}),
                    "analysis_complete": state.get("analysis_complete", False),
                    "session_id": state.get("session_id"),
                }

                # Get reports
                reports = state.get("reports", {})
                for report_type, report_data in reports.items():
                    if isinstance(report_data, dict):
                        symbol_data["reports"][report_type] = report_data.get("report", "")
                    else:
                        symbol_data["reports"][report_type] = str(report_data) if report_data else ""

                # Also check current_reports for backwards compatibility
                current_reports = state.get("current_reports", {})
                for report_type, report_content in current_reports.items():
                    if report_content and report_type not in symbol_data["reports"]:
                        symbol_data["reports"][report_type] = str(report_content)

                # Get prompts
                agent_prompts = state.get("agent_prompts", {})
                for prompt_type, prompt_content in agent_prompts.items():
                    if prompt_content:
                        symbol_data["prompts"][prompt_type] = str(prompt_content)

                run_data["symbol_states"][symbol] = symbol_data

        # Save to file
        file_path = HISTORY_DIR / f"{run_id}.json"
        with open(file_path, 'w') as f:
            json.dump(run_data, f, indent=2, default=str)

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
        ensure_history_dir()

        runs = []
        for file_path in HISTORY_DIR.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                runs.append({
                    "run_id": data.get("run_id", file_path.stem),
                    "timestamp": data.get("timestamp"),
                    "symbols": data.get("symbols", []),
                    "reports_count": data.get("generated_reports_count", 0),
                    "file_path": str(file_path)
                })
            except Exception as e:
                print(f"[HISTORY] Error reading {file_path}: {e}")
                continue

        # Sort by timestamp (newest first)
        runs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return runs[:limit]

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
        ensure_history_dir()

        file_path = HISTORY_DIR / f"{run_id}.json"

        if not file_path.exists():
            print(f"[HISTORY] Run not found: {run_id}")
            return None

        with open(file_path, 'r') as f:
            data = json.load(f)

        print(f"[HISTORY] Loaded analysis run: {run_id}")
        return data

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
        file_path = HISTORY_DIR / f"{run_id}.json"

        if file_path.exists():
            file_path.unlink()
            print(f"[HISTORY] Deleted analysis run: {run_id}")
            return True

        return False

    except Exception as e:
        print(f"[HISTORY] Error deleting run {run_id}: {e}")
        return False


def format_run_label(run: Dict[str, Any]) -> str:
    """Format a run for display in dropdown."""
    try:
        timestamp = datetime.fromisoformat(run["timestamp"])
        date_str = timestamp.strftime("%m/%d %H:%M")
    except:
        date_str = "Unknown"

    symbols = run.get("symbols", [])
    if len(symbols) <= 3:
        symbols_str = ", ".join(symbols)
    else:
        symbols_str = f"{', '.join(symbols[:3])} +{len(symbols) - 3}"

    return f"{date_str} - {symbols_str}"
