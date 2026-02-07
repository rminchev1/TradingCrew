"""
Custom Log Handler for TradingAgents WebUI
Captures logs and streams them to the UI in real-time.
"""

import logging
import threading
from collections import deque
from datetime import datetime
from typing import List, Dict, Optional


class WebUILogHandler(logging.Handler):
    """Custom log handler that stores logs in a circular buffer for UI streaming."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_logs: int = 500):
        if self._initialized:
            return

        super().__init__()
        self.max_logs = max_logs
        self.log_buffer = deque(maxlen=max_logs)
        self.new_logs = deque(maxlen=max_logs)  # For incremental updates
        self._buffer_lock = threading.Lock()
        self._last_read_index = 0
        self._total_logs = 0
        self._initialized = True

        # Set formatter
        self.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        ))

    def emit(self, record: logging.LogRecord):
        """Handle a log record."""
        try:
            log_entry = self._format_log_entry(record)
            with self._buffer_lock:
                self.log_buffer.append(log_entry)
                self.new_logs.append(log_entry)
                self._total_logs += 1
        except Exception:
            self.handleError(record)

    def _format_log_entry(self, record: logging.LogRecord) -> Dict:
        """Format a log record into a dictionary."""
        return {
            "timestamp": datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3],
            "level": record.levelname,
            "logger": record.name[:30] if len(record.name) > 30 else record.name,
            "message": self.format(record).split(" | ")[-1],  # Get just the message part
            "level_color": self._get_level_color(record.levelname),
            "index": self._total_logs
        }

    def _get_level_color(self, level: str) -> str:
        """Get color class for log level."""
        colors = {
            "DEBUG": "text-secondary",
            "INFO": "text-info",
            "WARNING": "text-warning",
            "ERROR": "text-danger",
            "CRITICAL": "text-danger fw-bold"
        }
        return colors.get(level, "text-muted")

    def get_all_logs(self) -> List[Dict]:
        """Get all logs in the buffer."""
        with self._buffer_lock:
            return list(self.log_buffer)

    def get_new_logs(self) -> List[Dict]:
        """Get new logs since last call and clear the new logs buffer."""
        with self._buffer_lock:
            logs = list(self.new_logs)
            self.new_logs.clear()
            return logs

    def get_logs_since(self, last_index: int) -> List[Dict]:
        """Get logs since a specific index."""
        with self._buffer_lock:
            return [log for log in self.log_buffer if log["index"] > last_index]

    def clear(self):
        """Clear all logs."""
        with self._buffer_lock:
            self.log_buffer.clear()
            self.new_logs.clear()

    def get_total_count(self) -> int:
        """Get total number of logs received."""
        return self._total_logs


# Singleton instance
_log_handler: Optional[WebUILogHandler] = None


def get_log_handler() -> WebUILogHandler:
    """Get the singleton log handler instance."""
    global _log_handler
    if _log_handler is None:
        _log_handler = WebUILogHandler()
    return _log_handler


def setup_log_capture():
    """Set up log capture for the entire application."""
    handler = get_log_handler()
    handler.setLevel(logging.DEBUG)

    # Add handler to root logger
    root_logger = logging.getLogger()
    if handler not in root_logger.handlers:
        root_logger.addHandler(handler)

    # Also capture specific loggers we care about
    loggers_to_capture = [
        "tradingagents",
        "webui",
        "langchain",
        "langgraph",
        "openai",
        "httpx",
        "alpaca",
    ]

    for logger_name in loggers_to_capture:
        logger = logging.getLogger(logger_name)
        if handler not in logger.handlers:
            logger.addHandler(handler)

    # Intercept print statements to capture app logs
    import builtins
    original_print = builtins.print

    def captured_print(*args, **kwargs):
        # Call original print first
        original_print(*args, **kwargs)

        # Capture the message
        try:
            message = " ".join(str(arg) for arg in args)
            if message and message.strip():
                # Determine log level from message prefix
                msg_upper = message.upper()
                if "ERROR" in msg_upper or "FAIL" in msg_upper or "EXCEPTION" in msg_upper:
                    level = "ERROR"
                elif "WARN" in msg_upper:
                    level = "WARNING"
                elif "DEBUG" in msg_upper:
                    level = "DEBUG"
                else:
                    level = "INFO"

                # Determine logger name from prefix
                logger_name = "app"
                if message.startswith("["):
                    end_bracket = message.find("]")
                    if end_bracket > 0:
                        logger_name = message[1:end_bracket].lower()

                # Create simplified log entry directly (more efficient)
                from datetime import datetime
                log_entry = {
                    "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
                    "level": level,
                    "logger": logger_name[:20],
                    "message": message,
                    "level_color": handler._get_level_color(level),
                    "index": handler._total_logs + 1
                }

                with handler._buffer_lock:
                    handler.log_buffer.append(log_entry)
                    handler.new_logs.append(log_entry)
                    handler._total_logs += 1
        except Exception:
            pass  # Never let logging break the app

    builtins.print = captured_print

    return handler
