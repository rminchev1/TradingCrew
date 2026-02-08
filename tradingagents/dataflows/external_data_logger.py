"""
External Data Fetch Logger

Centralized logging for all external API/data source failures.
Provides consistent error tracking and reporting for debugging and monitoring.
"""

import datetime
import traceback
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum


class ExternalSystem(Enum):
    """Enum of external systems that can be logged."""
    ALPACA = "Alpaca"
    FINNHUB = "Finnhub"
    FRED = "FRED"
    REDDIT = "Reddit"
    COINDESK = "CoinDesk/CryptoCompare"
    GOOGLE_NEWS = "Google News"
    OPENAI = "OpenAI"
    SIMFIN = "SimFin"
    DEFILLAMA = "DeFiLlama"
    YAHOO_FINANCE = "Yahoo Finance"
    STOCKSTATS = "StockStats"
    EARNINGS = "Earnings Calendar"
    OPTIONS = "Options Data"
    UNKNOWN = "Unknown"


@dataclass
class ExternalDataError:
    """Represents a single external data fetch error."""
    timestamp: datetime.datetime
    system: ExternalSystem
    operation: str
    error_message: str
    error_type: str
    symbol: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    traceback_str: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "system": self.system.value,
            "operation": self.operation,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "symbol": self.symbol,
            "params": self.params,
        }

    def format_log_message(self) -> str:
        """Format as a human-readable log message."""
        parts = [
            f"[EXTERNAL DATA ERROR] {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"  System: {self.system.value}",
            f"  Operation: {self.operation}",
        ]
        if self.symbol:
            parts.append(f"  Symbol: {self.symbol}")
        parts.append(f"  Error Type: {self.error_type}")
        parts.append(f"  Error Message: {self.error_message}")
        if self.params:
            params_str = ", ".join(f"{k}={v}" for k, v in self.params.items())
            parts.append(f"  Parameters: {params_str}")
        return "\n".join(parts)


class ExternalDataLogger:
    """
    Centralized logger for external data fetch failures.

    Usage:
        from tradingagents.dataflows.external_data_logger import external_data_logger, ExternalSystem

        try:
            data = fetch_some_external_data()
        except Exception as e:
            external_data_logger.log_error(
                system=ExternalSystem.ALPACA,
                operation="get_stock_data",
                error=e,
                symbol="NVDA",
                params={"start_date": "2024-01-01"}
            )
    """

    def __init__(self, max_errors: int = 1000):
        """Initialize the logger with a max error limit to prevent memory issues."""
        self._errors: List[ExternalDataError] = []
        self._max_errors = max_errors
        self._error_counts: Dict[str, int] = {}  # Track counts by system

    def log_error(
        self,
        system: ExternalSystem,
        operation: str,
        error: Exception,
        symbol: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        include_traceback: bool = True
    ) -> ExternalDataError:
        """
        Log an external data fetch error.

        Args:
            system: The external system that failed
            operation: The operation that was being performed
            error: The exception that was raised
            symbol: Optional ticker symbol involved
            params: Optional parameters that were used in the request
            include_traceback: Whether to include the full traceback

        Returns:
            The created ExternalDataError object
        """
        error_obj = ExternalDataError(
            timestamp=datetime.datetime.now(),
            system=system,
            operation=operation,
            error_message=str(error),
            error_type=type(error).__name__,
            symbol=symbol,
            params=params,
            traceback_str=traceback.format_exc() if include_traceback else None
        )

        # Print the error immediately
        print(error_obj.format_log_message())

        # Store the error
        self._errors.append(error_obj)

        # Track counts
        system_key = system.value
        self._error_counts[system_key] = self._error_counts.get(system_key, 0) + 1

        # Trim if we exceed max
        if len(self._errors) > self._max_errors:
            self._errors = self._errors[-self._max_errors:]

        return error_obj

    def log_error_simple(
        self,
        system_name: str,
        operation: str,
        error_message: str,
        symbol: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> ExternalDataError:
        """
        Log an error with a string system name (for convenience).

        Args:
            system_name: Name of the external system (will be mapped to ExternalSystem enum)
            operation: The operation that was being performed
            error_message: The error message string
            symbol: Optional ticker symbol involved
            params: Optional parameters that were used

        Returns:
            The created ExternalDataError object
        """
        # Map string to enum
        system_map = {
            "alpaca": ExternalSystem.ALPACA,
            "finnhub": ExternalSystem.FINNHUB,
            "fred": ExternalSystem.FRED,
            "reddit": ExternalSystem.REDDIT,
            "coindesk": ExternalSystem.COINDESK,
            "cryptocompare": ExternalSystem.COINDESK,
            "google": ExternalSystem.GOOGLE_NEWS,
            "googlenews": ExternalSystem.GOOGLE_NEWS,
            "openai": ExternalSystem.OPENAI,
            "simfin": ExternalSystem.SIMFIN,
            "defillama": ExternalSystem.DEFILLAMA,
            "yahoo": ExternalSystem.YAHOO_FINANCE,
            "yfinance": ExternalSystem.YAHOO_FINANCE,
            "stockstats": ExternalSystem.STOCKSTATS,
            "earnings": ExternalSystem.EARNINGS,
            "options": ExternalSystem.OPTIONS,
        }

        system = system_map.get(system_name.lower(), ExternalSystem.UNKNOWN)

        error_obj = ExternalDataError(
            timestamp=datetime.datetime.now(),
            system=system,
            operation=operation,
            error_message=error_message,
            error_type="ExternalAPIError",
            symbol=symbol,
            params=params,
            traceback_str=None
        )

        # Print the error immediately
        print(error_obj.format_log_message())

        # Store the error
        self._errors.append(error_obj)

        # Track counts
        system_key = system.value
        self._error_counts[system_key] = self._error_counts.get(system_key, 0) + 1

        # Trim if we exceed max
        if len(self._errors) > self._max_errors:
            self._errors = self._errors[-self._max_errors:]

        return error_obj

    def get_recent_errors(self, limit: int = 50) -> List[ExternalDataError]:
        """Get the most recent errors."""
        return self._errors[-limit:]

    def get_errors_by_system(self, system: ExternalSystem) -> List[ExternalDataError]:
        """Get all errors for a specific system."""
        return [e for e in self._errors if e.system == system]

    def get_errors_by_symbol(self, symbol: str) -> List[ExternalDataError]:
        """Get all errors for a specific symbol."""
        return [e for e in self._errors if e.symbol and e.symbol.upper() == symbol.upper()]

    def get_error_counts(self) -> Dict[str, int]:
        """Get error counts by system."""
        return dict(self._error_counts)

    def get_error_summary(self) -> str:
        """Get a summary of all errors."""
        if not self._errors:
            return "No external data errors logged."

        lines = [
            "=== External Data Error Summary ===",
            f"Total Errors: {len(self._errors)}",
            "",
            "Errors by System:"
        ]

        for system, count in sorted(self._error_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  - {system}: {count}")

        lines.append("")
        lines.append("Recent Errors (last 5):")

        for error in self._errors[-5:]:
            lines.append(f"  [{error.timestamp.strftime('%H:%M:%S')}] {error.system.value}: {error.operation} - {error.error_message[:80]}...")

        return "\n".join(lines)

    def clear(self):
        """Clear all logged errors."""
        self._errors.clear()
        self._error_counts.clear()

    def has_errors(self) -> bool:
        """Check if any errors have been logged."""
        return len(self._errors) > 0

    def get_session_errors_for_display(self) -> List[Dict[str, Any]]:
        """Get errors formatted for UI display."""
        return [e.to_dict() for e in self._errors]


# Global singleton instance
external_data_logger = ExternalDataLogger()


# Convenience functions for quick logging
def log_external_error(
    system: str,
    operation: str,
    error: Exception,
    symbol: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None
) -> None:
    """
    Quick convenience function to log an external data error.

    Args:
        system: Name of the external system (e.g., "alpaca", "finnhub", "fred")
        operation: The operation that was being performed
        error: The exception that was raised
        symbol: Optional ticker symbol involved
        params: Optional parameters that were used
    """
    # Map string to enum
    system_map = {
        "alpaca": ExternalSystem.ALPACA,
        "finnhub": ExternalSystem.FINNHUB,
        "fred": ExternalSystem.FRED,
        "reddit": ExternalSystem.REDDIT,
        "coindesk": ExternalSystem.COINDESK,
        "cryptocompare": ExternalSystem.COINDESK,
        "google": ExternalSystem.GOOGLE_NEWS,
        "googlenews": ExternalSystem.GOOGLE_NEWS,
        "openai": ExternalSystem.OPENAI,
        "simfin": ExternalSystem.SIMFIN,
        "defillama": ExternalSystem.DEFILLAMA,
        "yahoo": ExternalSystem.YAHOO_FINANCE,
        "yfinance": ExternalSystem.YAHOO_FINANCE,
        "stockstats": ExternalSystem.STOCKSTATS,
        "earnings": ExternalSystem.EARNINGS,
        "options": ExternalSystem.OPTIONS,
    }

    system_enum = system_map.get(system.lower(), ExternalSystem.UNKNOWN)
    external_data_logger.log_error(system_enum, operation, error, symbol, params)


def log_api_error(
    system: str,
    operation: str,
    error_message: str,
    symbol: Optional[str] = None
) -> None:
    """
    Quick convenience function to log an API error with just a message.

    Args:
        system: Name of the external system
        operation: The operation that was being performed
        error_message: The error message string
        symbol: Optional ticker symbol involved
    """
    external_data_logger.log_error_simple(system, operation, error_message, symbol)
