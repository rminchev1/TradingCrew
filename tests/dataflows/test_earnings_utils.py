"""
Tests for earnings_utils.py — particularly the non-US exchange guard that
prevents spurious 403 errors when Finnhub is called for international symbols.
"""
import pytest
from unittest.mock import patch, MagicMock

from tradingagents.dataflows.earnings_utils import (
    _is_non_us_exchange_symbol,
    get_finnhub_earnings_calendar,
    get_earnings_calendar_data,
)


class TestIsNonUsExchangeSymbol:
    """Tests for the helper that detects non-US exchange tickers."""

    def test_italian_exchange(self):
        assert _is_non_us_exchange_symbol("IREN.MI") is True

    def test_london_exchange(self):
        assert _is_non_us_exchange_symbol("VOD.L") is True

    def test_paris_exchange(self):
        assert _is_non_us_exchange_symbol("AIR.PA") is True

    def test_frankfurt_exchange(self):
        assert _is_non_us_exchange_symbol("SAP.DE") is True

    def test_toronto_exchange(self):
        assert _is_non_us_exchange_symbol("RY.TO") is True

    def test_us_stock_no_dot(self):
        assert _is_non_us_exchange_symbol("AAPL") is False

    def test_us_stock_with_class_suffix_a(self):
        # BRK.A / BRK.B are US share classes — should not be flagged
        assert _is_non_us_exchange_symbol("BRK.A") is False
        assert _is_non_us_exchange_symbol("BRK.B") is False

    def test_crypto_symbol(self):
        assert _is_non_us_exchange_symbol("BTC/USD") is False

    def test_lowercase_suffix(self):
        # Suffixes should be case-insensitive
        assert _is_non_us_exchange_symbol("iren.mi") is True


class TestGetFinnhubEarningsCalendarNonUs:
    """Ensure non-US symbols return a graceful message without hitting the API."""

    def test_non_us_symbol_skips_api_call(self):
        """IREN.MI should return a descriptive message, not trigger a Finnhub call."""
        # get_finnhub_client is imported locally inside the function, so patch at source
        with patch(
            "tradingagents.dataflows.finnhub_utils.get_finnhub_client"
        ) as mock_client:
            result = get_finnhub_earnings_calendar("IREN.MI", "2025-01-01", "2025-12-31")

            # Finnhub client must NOT be called
            mock_client.assert_not_called()

        assert "not available" in result.lower()
        assert "IREN.MI" in result
        assert ".MI" in result

    def test_non_us_symbol_no_error_logged(self):
        """No error should be logged for a known plan limitation."""
        with patch(
            "tradingagents.dataflows.earnings_utils.log_api_error"
        ) as mock_log:
            get_finnhub_earnings_calendar("VOD.L", "2025-01-01", "2025-12-31")
            mock_log.assert_not_called()

    def test_us_symbol_proceeds_to_api(self):
        """US symbols should still reach the Finnhub client."""
        mock_client = MagicMock()
        mock_client.earnings_calendar.return_value = {"earningsCalendar": []}

        with patch(
            "tradingagents.dataflows.finnhub_utils.get_finnhub_client",
            return_value=mock_client,
        ):
            result = get_finnhub_earnings_calendar("AAPL", "2025-01-01", "2025-12-31")

        mock_client.earnings_calendar.assert_called_once()
        assert "No earnings data found" in result


class TestGetEarningsCalendarData:
    """Integration-level tests for the public dispatcher."""

    def test_non_us_stock_dispatches_correctly(self):
        """get_earnings_calendar_data should propagate the non-US guard."""
        result = get_earnings_calendar_data("IREN.MI", "2025-01-01", "2025-12-31")
        assert "not available" in result.lower()
        assert "IREN.MI" in result

    def test_crypto_returns_crypto_message(self):
        result = get_earnings_calendar_data("BTC/USD", "2025-01-01", "2025-12-31")
        assert "Crypto" in result or "crypto" in result
