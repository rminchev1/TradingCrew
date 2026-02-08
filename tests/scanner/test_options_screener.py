"""
Unit tests for the options_screener module
"""

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from tradingagents.scanner.options_screener import (
    screen_options_flow,
    batch_screen_options,
    get_options_summary,
    _default_options_result,
)
from tradingagents.scanner.cache import clear_cache


class TestDefaultOptionsResult:
    """Tests for _default_options_result function"""

    def test_default_result_structure(self):
        """Test default result has correct structure"""
        result = _default_options_result()

        assert "options_score" in result
        assert "signal" in result
        assert "put_call_ratio" in result
        assert "iv_percentile" in result
        assert "has_unusual_activity" in result
        assert "details" in result

    def test_default_result_values(self):
        """Test default result has neutral values"""
        result = _default_options_result()

        assert result["options_score"] == 50
        assert result["signal"] == "neutral"
        assert result["put_call_ratio"] == 1.0
        assert result["iv_percentile"] == 0
        assert result["has_unusual_activity"] is False
        assert result["details"] == {}


class TestScreenOptionsFlow:
    """Tests for screen_options_flow function"""

    def setup_method(self):
        """Clear cache before each test"""
        clear_cache()

    @patch("tradingagents.scanner.options_screener.OPTIONS_AVAILABLE", False)
    def test_options_unavailable(self):
        """Test behavior when options module not available"""
        result = screen_options_flow("AAPL")
        assert result == _default_options_result()

    @patch("tradingagents.scanner.options_screener.get_current_price")
    @patch("tradingagents.scanner.options_screener.get_options_chain")
    @patch("tradingagents.scanner.options_screener.OPTIONS_AVAILABLE", True)
    def test_no_price_data(self, mock_chain, mock_price):
        """Test behavior when price data unavailable"""
        mock_price.return_value = 0

        result = screen_options_flow("INVALID")
        assert result["options_score"] == 50
        assert result["signal"] == "neutral"

    @patch("tradingagents.scanner.options_screener.get_current_price")
    @patch("tradingagents.scanner.options_screener.get_options_chain")
    @patch("tradingagents.scanner.options_screener.calculate_put_call_ratio")
    @patch("tradingagents.scanner.options_screener.calculate_iv_metrics")
    @patch("tradingagents.scanner.options_screener.detect_unusual_activity")
    @patch("tradingagents.scanner.options_screener.OPTIONS_AVAILABLE", True)
    def test_bullish_options_flow(
        self, mock_unusual, mock_iv, mock_pc, mock_chain, mock_price
    ):
        """Test bullish options signal detection"""
        mock_price.return_value = 150.0
        mock_chain.return_value = (
            pd.DataFrame({"strike": [150]}),  # calls
            pd.DataFrame({"strike": [150]}),  # puts
            ["2024-01-19"],  # expirations
        )
        mock_pc.return_value = {
            "volume_ratio": 0.4,  # Very bullish
            "volume_sentiment": "Very Bullish",
        }
        mock_iv.return_value = {
            "atm_iv": 30.0,
            "iv_skew": -6,  # Calls expensive
        }
        mock_unusual.return_value = {
            "has_unusual_activity": True,
            "activity_bias": "Bullish",
        }

        result = screen_options_flow("AAPL")

        assert result["options_score"] > 65
        assert result["signal"] == "bullish"

    @patch("tradingagents.scanner.options_screener.get_current_price")
    @patch("tradingagents.scanner.options_screener.get_options_chain")
    @patch("tradingagents.scanner.options_screener.calculate_put_call_ratio")
    @patch("tradingagents.scanner.options_screener.calculate_iv_metrics")
    @patch("tradingagents.scanner.options_screener.detect_unusual_activity")
    @patch("tradingagents.scanner.options_screener.OPTIONS_AVAILABLE", True)
    def test_bearish_options_flow(
        self, mock_unusual, mock_iv, mock_pc, mock_chain, mock_price
    ):
        """Test bearish options signal detection"""
        mock_price.return_value = 150.0
        mock_chain.return_value = (
            pd.DataFrame({"strike": [150]}),
            pd.DataFrame({"strike": [150]}),
            ["2024-01-19"],
        )
        mock_pc.return_value = {
            "volume_ratio": 1.6,  # Very bearish
            "volume_sentiment": "Very Bearish",
        }
        mock_iv.return_value = {
            "atm_iv": 40.0,
            "iv_skew": 6,  # Puts expensive (fear)
        }
        mock_unusual.return_value = {
            "has_unusual_activity": True,
            "activity_bias": "Bearish",
        }

        result = screen_options_flow("AAPL")

        assert result["options_score"] < 35
        assert result["signal"] == "bearish"

    @patch("tradingagents.scanner.options_screener.get_current_price")
    @patch("tradingagents.scanner.options_screener.get_options_chain")
    @patch("tradingagents.scanner.options_screener.calculate_put_call_ratio")
    @patch("tradingagents.scanner.options_screener.calculate_iv_metrics")
    @patch("tradingagents.scanner.options_screener.detect_unusual_activity")
    @patch("tradingagents.scanner.options_screener.OPTIONS_AVAILABLE", True)
    def test_neutral_options_flow(
        self, mock_unusual, mock_iv, mock_pc, mock_chain, mock_price
    ):
        """Test neutral options signal"""
        mock_price.return_value = 150.0
        mock_chain.return_value = (
            pd.DataFrame({"strike": [150]}),
            pd.DataFrame({"strike": [150]}),
            ["2024-01-19"],
        )
        mock_pc.return_value = {
            "volume_ratio": 1.0,  # Neutral
            "volume_sentiment": "Neutral",
        }
        mock_iv.return_value = {
            "atm_iv": 25.0,
            "iv_skew": 0,
        }
        mock_unusual.return_value = {
            "has_unusual_activity": False,
            "activity_bias": "Mixed",
        }

        result = screen_options_flow("AAPL")

        assert 35 <= result["options_score"] <= 65
        assert result["signal"] == "neutral"


class TestBatchScreenOptions:
    """Tests for batch_screen_options function"""

    def setup_method(self):
        clear_cache()

    @patch("tradingagents.scanner.options_screener.screen_options_flow")
    def test_batch_screen_multiple_symbols(self, mock_screen):
        """Test batch screening multiple symbols"""
        mock_screen.return_value = {
            "options_score": 60,
            "signal": "neutral",
            "put_call_ratio": 0.9,
            "iv_percentile": 25.0,
            "has_unusual_activity": False,
            "details": {},
        }

        symbols = ["AAPL", "MSFT", "GOOGL"]
        results = batch_screen_options(symbols, max_workers=2)

        assert len(results) == 3
        assert "AAPL" in results
        assert "MSFT" in results
        assert "GOOGL" in results
        assert mock_screen.call_count == 3

    @patch("tradingagents.scanner.options_screener.screen_options_flow")
    def test_batch_screen_handles_errors(self, mock_screen):
        """Test batch screening handles individual errors"""
        def side_effect(symbol):
            if symbol == "ERROR":
                raise Exception("Test error")
            return _default_options_result()

        mock_screen.side_effect = side_effect

        symbols = ["AAPL", "ERROR", "MSFT"]
        results = batch_screen_options(symbols)

        assert len(results) == 3
        # ERROR should get default result
        assert results["ERROR"]["options_score"] == 50

    def test_batch_screen_empty_list(self):
        """Test batch screening empty list"""
        results = batch_screen_options([])
        assert results == {}


class TestGetOptionsSummary:
    """Tests for get_options_summary function"""

    def setup_method(self):
        clear_cache()

    @patch("tradingagents.scanner.options_screener.screen_options_flow")
    def test_summary_format(self, mock_screen):
        """Test summary string format"""
        mock_screen.return_value = {
            "options_score": 75,
            "signal": "bullish",
            "put_call_ratio": 0.6,
            "iv_percentile": 35.0,
            "has_unusual_activity": True,
            "details": {
                "volume_sentiment": "Bullish",
                "activity_bias": "Strong bullish flow",
                "expected_move_pct": 5.5,
            },
        }

        summary = get_options_summary("AAPL")

        assert "AAPL" in summary
        assert "75" in summary  # Score
        assert "BULLISH" in summary
        assert "0.60" in summary  # P/C ratio
        assert "35.0%" in summary  # IV

    @patch("tradingagents.scanner.options_screener.screen_options_flow")
    def test_summary_no_data(self, mock_screen):
        """Test summary when no options data available"""
        mock_screen.return_value = {
            "options_score": 50,
            "signal": "neutral",
            "put_call_ratio": 1.0,
            "iv_percentile": 0,
            "has_unusual_activity": False,
            "details": {},
        }

        summary = get_options_summary("NODATA")
        assert "NODATA" in summary
        assert "No options data" in summary


class TestOptionsScoreCalculation:
    """Tests for options score calculation logic"""

    @patch("tradingagents.scanner.options_screener.get_current_price")
    @patch("tradingagents.scanner.options_screener.get_options_chain")
    @patch("tradingagents.scanner.options_screener.calculate_put_call_ratio")
    @patch("tradingagents.scanner.options_screener.calculate_iv_metrics")
    @patch("tradingagents.scanner.options_screener.detect_unusual_activity")
    @patch("tradingagents.scanner.options_screener.OPTIONS_AVAILABLE", True)
    def test_score_clamped_to_100(
        self, mock_unusual, mock_iv, mock_pc, mock_chain, mock_price
    ):
        """Test that score is clamped to max 100"""
        clear_cache()
        mock_price.return_value = 150.0
        mock_chain.return_value = (
            pd.DataFrame({"strike": [150]}),
            pd.DataFrame({"strike": [150]}),
            ["2024-01-19"],
        )
        # All extremely bullish signals
        mock_pc.return_value = {"volume_ratio": 0.3, "volume_sentiment": "Very Bullish"}
        mock_iv.return_value = {"atm_iv": 20.0, "iv_skew": -10}
        mock_unusual.return_value = {
            "has_unusual_activity": True,
            "activity_bias": "Bullish",
        }

        result = screen_options_flow("AAPL")
        assert result["options_score"] <= 100

    @patch("tradingagents.scanner.options_screener.get_current_price")
    @patch("tradingagents.scanner.options_screener.get_options_chain")
    @patch("tradingagents.scanner.options_screener.calculate_put_call_ratio")
    @patch("tradingagents.scanner.options_screener.calculate_iv_metrics")
    @patch("tradingagents.scanner.options_screener.detect_unusual_activity")
    @patch("tradingagents.scanner.options_screener.OPTIONS_AVAILABLE", True)
    def test_score_clamped_to_0(
        self, mock_unusual, mock_iv, mock_pc, mock_chain, mock_price
    ):
        """Test that score is clamped to min 0"""
        clear_cache()
        mock_price.return_value = 150.0
        mock_chain.return_value = (
            pd.DataFrame({"strike": [150]}),
            pd.DataFrame({"strike": [150]}),
            ["2024-01-19"],
        )
        # All extremely bearish signals
        mock_pc.return_value = {"volume_ratio": 2.0, "volume_sentiment": "Very Bearish"}
        mock_iv.return_value = {"atm_iv": 60.0, "iv_skew": 10}
        mock_unusual.return_value = {
            "has_unusual_activity": True,
            "activity_bias": "Bearish",
        }

        result = screen_options_flow("AAPL")
        assert result["options_score"] >= 0
