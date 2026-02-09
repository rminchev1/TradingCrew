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
    "quick_llm": "gpt-4o-mini",
    "deep_llm": "o3-mini",
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


# Initialize database on module load
init_db()
