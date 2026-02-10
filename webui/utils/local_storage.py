"""
webui/utils/local_storage.py - Local SQLite database for persistent storage

Replaces browser localStorage with server-side storage that persists
across browsers and sessions.
"""

import sqlite3
import json
import os
from pathlib import Path
from threading import Lock

# Database file location
DB_DIR = Path(__file__).parent.parent.parent / "data"
DB_PATH = DB_DIR / "tradingcrew.db"

# Thread lock for SQLite operations
_db_lock = Lock()


def _ensure_db_dir():
    """Ensure the data directory exists"""
    DB_DIR.mkdir(parents=True, exist_ok=True)


def _get_connection():
    """Get a database connection"""
    _ensure_db_dir()
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database with required tables"""
    with _db_lock:
        conn = _get_connection()
        cursor = conn.cursor()

        # Key-value store for settings and other data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Analyst reports table for persistent report storage
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analyst_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                report_type TEXT NOT NULL,
                report_content TEXT,
                prompt_content TEXT,
                session_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, report_type, session_id)
            )
        """)

        # Index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analyst_reports_symbol
            ON analyst_reports(symbol)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analyst_reports_session
            ON analyst_reports(session_id)
        """)

        # Analysis runs table for tracking complete analysis sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_runs (
                run_id TEXT PRIMARY KEY,
                symbols TEXT NOT NULL,
                tool_calls_count INTEGER DEFAULT 0,
                llm_calls_count INTEGER DEFAULT 0,
                generated_reports_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Index for faster date-based lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analysis_runs_created
            ON analysis_runs(created_at DESC)
        """)

        conn.commit()
        conn.close()


def get_value(key: str, default=None):
    """Get a value from the store"""
    with _db_lock:
        conn = _get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT value FROM kv_store WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()

        if row:
            try:
                return json.loads(row["value"])
            except json.JSONDecodeError:
                return row["value"]
        return default


def set_value(key: str, value):
    """Set a value in the store"""
    with _db_lock:
        conn = _get_connection()
        cursor = conn.cursor()

        json_value = json.dumps(value)
        cursor.execute("""
            INSERT INTO kv_store (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
        """, (key, json_value))

        conn.commit()
        conn.close()


def delete_value(key: str):
    """Delete a value from the store"""
    with _db_lock:
        conn = _get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM kv_store WHERE key = ?", (key,))

        conn.commit()
        conn.close()


def get_all_keys():
    """Get all keys in the store"""
    with _db_lock:
        conn = _get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT key FROM kv_store")
        rows = cursor.fetchall()
        conn.close()

        return [row["key"] for row in rows]


# ============================================================================
# Convenience functions for specific data types
# ============================================================================

# Settings
DEFAULT_SETTINGS = {
    "analyst_checklist": ["market", "options", "social"],
    "analyst_checklist_2": ["news", "fundamentals", "macro"],
    "research_depth": "Shallow",
    "allow_shorts": False,
    "loop_enabled": False,
    "loop_interval": 60,
    "market_hour_enabled": False,
    "market_hours_input": "",
    "trade_after_analyze": False,
    "trade_dollar_amount": 4500,
    "quick_llm": "gpt-4.1-nano",
    "deep_llm": "o4-mini",
}


def get_settings():
    """Get all settings"""
    settings = get_value("settings", DEFAULT_SETTINGS.copy())
    # Merge with defaults to ensure all keys exist
    merged = DEFAULT_SETTINGS.copy()
    merged.update(settings)
    return merged


def save_settings(settings: dict):
    """Save settings"""
    set_value("settings", settings)


def get_setting(key: str, default=None):
    """Get a single setting"""
    settings = get_settings()
    return settings.get(key, default)


def save_setting(key: str, value):
    """Save a single setting"""
    settings = get_settings()
    settings[key] = value
    save_settings(settings)


# Watchlist
def get_watchlist():
    """Get watchlist symbols"""
    return get_value("watchlist", {"symbols": []})


def save_watchlist(data: dict):
    """Save watchlist"""
    set_value("watchlist", data)


# Run Queue
def get_run_queue():
    """Get run queue symbols"""
    return get_value("run_queue", {"symbols": []})


def save_run_queue(data: dict):
    """Save run queue"""
    set_value("run_queue", data)


# ============================================================================
# Analyst Reports Storage
# ============================================================================

def save_analyst_report(symbol: str, report_type: str, report_content: str,
                        prompt_content: str = None, session_id: str = None):
    """
    Save an analyst report to persistent storage.

    Args:
        symbol: The trading symbol (e.g., "NVDA", "BTC/USD")
        report_type: The type of report (e.g., "market_report", "news_report")
        report_content: The actual report content
        prompt_content: Optional prompt that generated the report
        session_id: Optional session ID for grouping reports
    """
    if not report_content or not report_content.strip():
        return

    with _db_lock:
        conn = _get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO analyst_reports (symbol, report_type, report_content, prompt_content, session_id, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(symbol, report_type, session_id) DO UPDATE SET
                report_content = excluded.report_content,
                prompt_content = COALESCE(excluded.prompt_content, analyst_reports.prompt_content),
                updated_at = CURRENT_TIMESTAMP
        """, (symbol, report_type, report_content, prompt_content, session_id))

        conn.commit()
        conn.close()
        print(f"[LOCAL_STORAGE] Saved {report_type} for {symbol} (session: {session_id})")


def get_analyst_reports(symbol: str, session_id: str = None) -> dict:
    """
    Get all analyst reports for a symbol.

    Args:
        symbol: The trading symbol
        session_id: Optional session ID to filter by

    Returns:
        Dictionary of report_type -> report_content
    """
    with _db_lock:
        conn = _get_connection()
        cursor = conn.cursor()

        if session_id:
            cursor.execute("""
                SELECT report_type, report_content, prompt_content, updated_at
                FROM analyst_reports
                WHERE symbol = ? AND session_id = ?
                ORDER BY updated_at DESC
            """, (symbol, session_id))
        else:
            # Get the most recent reports for each type
            cursor.execute("""
                SELECT report_type, report_content, prompt_content, updated_at
                FROM analyst_reports
                WHERE symbol = ?
                AND id IN (
                    SELECT MAX(id) FROM analyst_reports
                    WHERE symbol = ?
                    GROUP BY report_type
                )
                ORDER BY updated_at DESC
            """, (symbol, symbol))

        rows = cursor.fetchall()
        conn.close()

        reports = {}
        for row in rows:
            reports[row["report_type"]] = {
                "content": row["report_content"],
                "prompt": row["prompt_content"],
                "updated_at": row["updated_at"]
            }

        return reports


def get_analyst_report(symbol: str, report_type: str, session_id: str = None) -> dict:
    """
    Get a specific analyst report.

    Args:
        symbol: The trading symbol
        report_type: The type of report
        session_id: Optional session ID to filter by

    Returns:
        Dictionary with content, prompt, and updated_at, or None
    """
    with _db_lock:
        conn = _get_connection()
        cursor = conn.cursor()

        if session_id:
            cursor.execute("""
                SELECT report_content, prompt_content, updated_at
                FROM analyst_reports
                WHERE symbol = ? AND report_type = ? AND session_id = ?
                ORDER BY updated_at DESC
                LIMIT 1
            """, (symbol, report_type, session_id))
        else:
            cursor.execute("""
                SELECT report_content, prompt_content, updated_at
                FROM analyst_reports
                WHERE symbol = ? AND report_type = ?
                ORDER BY updated_at DESC
                LIMIT 1
            """, (symbol, report_type))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "content": row["report_content"],
                "prompt": row["prompt_content"],
                "updated_at": row["updated_at"]
            }
        return None


def list_report_sessions(symbol: str = None, limit: int = 50) -> list:
    """
    List all report sessions.

    Args:
        symbol: Optional symbol to filter by
        limit: Maximum number of sessions to return

    Returns:
        List of session dictionaries with metadata
    """
    with _db_lock:
        conn = _get_connection()
        cursor = conn.cursor()

        if symbol:
            cursor.execute("""
                SELECT session_id, symbol,
                       COUNT(DISTINCT report_type) as report_count,
                       MIN(created_at) as started_at,
                       MAX(updated_at) as completed_at
                FROM analyst_reports
                WHERE symbol = ? AND session_id IS NOT NULL
                GROUP BY session_id, symbol
                ORDER BY completed_at DESC
                LIMIT ?
            """, (symbol, limit))
        else:
            cursor.execute("""
                SELECT session_id,
                       GROUP_CONCAT(DISTINCT symbol) as symbols,
                       COUNT(DISTINCT report_type) as report_count,
                       MIN(created_at) as started_at,
                       MAX(updated_at) as completed_at
                FROM analyst_reports
                WHERE session_id IS NOT NULL
                GROUP BY session_id
                ORDER BY completed_at DESC
                LIMIT ?
            """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        sessions = []
        for row in rows:
            # sqlite3.Row doesn't have .get(), so use try/except for optional columns
            try:
                symbols = row["symbols"]
            except (KeyError, IndexError):
                try:
                    symbols = row["symbol"]
                except (KeyError, IndexError):
                    symbols = ""

            sessions.append({
                "session_id": row["session_id"],
                "symbols": symbols,
                "report_count": row["report_count"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"]
            })

        return sessions


def delete_report_session(session_id: str) -> bool:
    """
    Delete all reports for a session.

    Args:
        session_id: The session ID to delete

    Returns:
        True if any reports were deleted
    """
    with _db_lock:
        conn = _get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM analyst_reports WHERE session_id = ?
        """, (session_id,))

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if deleted:
            print(f"[LOCAL_STORAGE] Deleted reports for session: {session_id}")

        return deleted


def get_recent_symbols(limit: int = 10) -> list:
    """
    Get the most recently analyzed symbols.

    Returns:
        List of symbol strings
    """
    with _db_lock:
        conn = _get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT symbol
            FROM analyst_reports
            ORDER BY updated_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [row["symbol"] for row in rows]


# ============================================================================
# Analysis Runs Storage
# ============================================================================

def save_analysis_run(run_id: str, symbols: list, tool_calls_count: int = 0,
                      llm_calls_count: int = 0, generated_reports_count: int = 0):
    """
    Save an analysis run record.

    Args:
        run_id: Unique identifier for the run (also used as session_id for reports)
        symbols: List of symbols analyzed
        tool_calls_count: Number of tool calls made
        llm_calls_count: Number of LLM calls made
        generated_reports_count: Number of reports generated
    """
    with _db_lock:
        conn = _get_connection()
        cursor = conn.cursor()

        symbols_str = json.dumps(symbols)
        cursor.execute("""
            INSERT INTO analysis_runs (run_id, symbols, tool_calls_count, llm_calls_count, generated_reports_count)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                symbols = excluded.symbols,
                tool_calls_count = excluded.tool_calls_count,
                llm_calls_count = excluded.llm_calls_count,
                generated_reports_count = excluded.generated_reports_count
        """, (run_id, symbols_str, tool_calls_count, llm_calls_count, generated_reports_count))

        conn.commit()
        conn.close()
        print(f"[LOCAL_STORAGE] Saved analysis run: {run_id}")


def list_analysis_runs(limit: int = 50) -> list:
    """
    List all saved analysis runs.

    Args:
        limit: Maximum number of runs to return

    Returns:
        List of run dictionaries sorted by date (newest first)
    """
    with _db_lock:
        conn = _get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT run_id, symbols, tool_calls_count, llm_calls_count,
                   generated_reports_count, created_at
            FROM analysis_runs
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        runs = []
        for row in rows:
            try:
                symbols = json.loads(row["symbols"])
            except (json.JSONDecodeError, TypeError):
                symbols = []

            runs.append({
                "run_id": row["run_id"],
                "symbols": symbols,
                "tool_calls_count": row["tool_calls_count"],
                "llm_calls_count": row["llm_calls_count"],
                "generated_reports_count": row["generated_reports_count"],
                "timestamp": row["created_at"]
            })

        return runs


def get_analysis_run(run_id: str) -> dict:
    """
    Get a specific analysis run with all its reports.

    Args:
        run_id: The run ID to retrieve

    Returns:
        Dictionary with run data and symbol_states containing reports
    """
    with _db_lock:
        conn = _get_connection()
        cursor = conn.cursor()

        # Get run metadata
        cursor.execute("""
            SELECT run_id, symbols, tool_calls_count, llm_calls_count,
                   generated_reports_count, created_at
            FROM analysis_runs
            WHERE run_id = ?
        """, (run_id,))

        run_row = cursor.fetchone()
        if not run_row:
            conn.close()
            return None

        try:
            symbols = json.loads(run_row["symbols"])
        except (json.JSONDecodeError, TypeError):
            symbols = []

        # Get all reports for this run (using run_id as session_id)
        cursor.execute("""
            SELECT symbol, report_type, report_content, prompt_content
            FROM analyst_reports
            WHERE session_id = ?
        """, (run_id,))

        report_rows = cursor.fetchall()
        conn.close()

        # Build symbol_states structure
        symbol_states = {}
        for symbol in symbols:
            symbol_states[symbol] = {
                "reports": {},
                "prompts": {},
                "agent_statuses": {}
            }

        for row in report_rows:
            symbol = row["symbol"]
            if symbol not in symbol_states:
                symbol_states[symbol] = {"reports": {}, "prompts": {}, "agent_statuses": {}}

            report_type = row["report_type"]
            symbol_states[symbol]["reports"][report_type] = row["report_content"]
            if row["prompt_content"]:
                symbol_states[symbol]["prompts"][report_type] = row["prompt_content"]

        return {
            "run_id": run_row["run_id"],
            "symbols": symbols,
            "timestamp": run_row["created_at"],
            "tool_calls_count": run_row["tool_calls_count"],
            "llm_calls_count": run_row["llm_calls_count"],
            "generated_reports_count": run_row["generated_reports_count"],
            "symbol_states": symbol_states
        }


def delete_analysis_run(run_id: str) -> bool:
    """
    Delete an analysis run and all its reports.

    Args:
        run_id: The run ID to delete

    Returns:
        True if deleted, False otherwise
    """
    with _db_lock:
        conn = _get_connection()
        cursor = conn.cursor()

        # Delete reports first (using run_id as session_id)
        cursor.execute("DELETE FROM analyst_reports WHERE session_id = ?", (run_id,))

        # Delete run metadata
        cursor.execute("DELETE FROM analysis_runs WHERE run_id = ?", (run_id,))

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if deleted:
            print(f"[LOCAL_STORAGE] Deleted analysis run: {run_id}")

        return deleted


# Initialize database on module load
init_db()
