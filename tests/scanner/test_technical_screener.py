"""
Unit tests for the technical_screener module
"""

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from tradingagents.scanner.technical_screener import (
    calculate_rsi,
    calculate_macd,
    calculate_ma_position,
    score_technical,
    batch_score_technical,
)
from tradingagents.scanner.cache import clear_cache


class TestCalculateRSI:
    """Tests for RSI calculation"""

    def test_rsi_insufficient_data(self):
        """Test RSI with insufficient data returns neutral"""
        prices = pd.Series([100, 101, 102])  # Only 3 points
        rsi = calculate_rsi(prices, period=14)
        assert rsi == 50.0

    def test_rsi_uptrend(self):
        """Test RSI in strong uptrend"""
        # Create steadily rising prices
        prices = pd.Series([100 + i * 2 for i in range(30)])
        rsi = calculate_rsi(prices)
        assert rsi > 70  # Should be overbought

    def test_rsi_downtrend(self):
        """Test RSI in strong downtrend"""
        # Create steadily falling prices
        prices = pd.Series([200 - i * 2 for i in range(30)])
        rsi = calculate_rsi(prices)
        assert rsi < 30  # Should be oversold

    def test_rsi_sideways(self):
        """Test RSI in sideways market"""
        # Create oscillating prices
        prices = pd.Series([100, 101, 100, 101, 100, 101] * 5)
        rsi = calculate_rsi(prices)
        assert 40 <= rsi <= 60  # Should be near neutral

    def test_rsi_returns_float(self):
        """Test RSI returns rounded float"""
        prices = pd.Series([100 + i for i in range(20)])
        rsi = calculate_rsi(prices)
        assert isinstance(rsi, float)
        # Check it's rounded to 2 decimal places
        assert rsi == round(rsi, 2)


class TestCalculateMACD:
    """Tests for MACD calculation"""

    def test_macd_insufficient_data(self):
        """Test MACD with insufficient data"""
        prices = pd.Series([100, 101, 102])
        macd, signal, signal_type = calculate_macd(prices)
        assert macd == 0.0
        assert signal == 0.0
        assert signal_type == "neutral"

    def test_macd_bullish(self):
        """Test MACD bullish signal"""
        # Create uptrending prices
        prices = pd.Series([100 + i * 0.5 for i in range(50)])
        macd, signal, signal_type = calculate_macd(prices)
        assert macd > 0
        assert signal_type == "bullish"

    def test_macd_bearish(self):
        """Test MACD bearish signal"""
        # Create downtrending prices
        prices = pd.Series([150 - i * 0.5 for i in range(50)])
        macd, signal, signal_type = calculate_macd(prices)
        assert macd < 0
        assert signal_type == "bearish"

    def test_macd_returns_tuple(self):
        """Test MACD returns correct tuple"""
        prices = pd.Series([100 + i for i in range(50)])
        result = calculate_macd(prices)
        assert isinstance(result, tuple)
        assert len(result) == 3
        macd, signal, signal_type = result
        assert isinstance(macd, float)
        assert isinstance(signal, float)
        assert signal_type in ["bullish", "bearish", "neutral"]


class TestCalculateMAPosition:
    """Tests for moving average position calculation"""

    def test_ma_insufficient_data(self):
        """Test MA position with insufficient data"""
        prices = pd.Series([100, 101, 102])
        position = calculate_ma_position(prices, period=50)
        assert position == "neutral"

    def test_ma_price_above(self):
        """Test when price is above MA"""
        # Create prices that end significantly above MA
        prices = pd.Series([100] * 50 + [120])  # Jump at end
        position = calculate_ma_position(prices, 50)
        assert position == "above"

    def test_ma_price_below(self):
        """Test when price is below MA"""
        # Create prices that end significantly below MA
        prices = pd.Series([100] * 50 + [80])  # Drop at end
        position = calculate_ma_position(prices, 50)
        assert position == "below"

    def test_ma_price_near(self):
        """Test when price is near MA (within 2%)"""
        prices = pd.Series([100] * 51)  # Flat prices
        position = calculate_ma_position(prices, 50)
        assert position == "neutral"


class TestScoreTechnical:
    """Tests for score_technical function"""

    def setup_method(self):
        clear_cache()

    @patch("tradingagents.scanner.technical_screener._fetch_historical_data")
    def test_score_no_data(self, mock_fetch):
        """Test scoring when no data available"""
        mock_fetch.return_value = pd.DataFrame()

        result = score_technical("INVALID")

        assert result["rsi"] == 50.0
        assert result["macd_signal"] == "neutral"
        assert result["technical_score"] == 50

    @patch("tradingagents.scanner.technical_screener._fetch_historical_data")
    def test_score_insufficient_data(self, mock_fetch):
        """Test scoring with insufficient data"""
        mock_fetch.return_value = pd.DataFrame({"close": [100, 101, 102]})

        result = score_technical("TEST")

        assert result["technical_score"] == 50

    @patch("tradingagents.scanner.technical_screener._fetch_historical_data")
    def test_score_bullish_setup(self, mock_fetch):
        """Test scoring for bullish technical setup"""
        # Create bullish data: uptrend, RSI not overbought
        prices = [100 + i * 0.3 for i in range(250)]
        mock_fetch.return_value = pd.DataFrame({"close": prices})

        result = score_technical("BULL")

        assert result["macd_signal"] == "bullish"
        assert result["price_vs_50ma"] == "above"
        assert result["price_vs_200ma"] == "above"
        assert result["technical_score"] > 60

    @patch("tradingagents.scanner.technical_screener._fetch_historical_data")
    def test_score_bearish_setup(self, mock_fetch):
        """Test scoring for bearish technical setup"""
        # Create bearish data: downtrend
        prices = [200 - i * 0.3 for i in range(250)]
        mock_fetch.return_value = pd.DataFrame({"close": prices})

        result = score_technical("BEAR")

        assert result["macd_signal"] == "bearish"
        assert result["price_vs_50ma"] == "below"
        assert result["technical_score"] < 50

    @patch("tradingagents.scanner.technical_screener._fetch_historical_data")
    def test_score_oversold_bonus(self, mock_fetch):
        """Test RSI oversold detection"""
        # Create oversold condition: recent sharp decline
        prices = [100] * 200 + [100 - i * 3 for i in range(50)]
        mock_fetch.return_value = pd.DataFrame({"close": prices})

        result = score_technical("OVERSOLD")

        # In a steep downtrend, RSI should be low (oversold territory)
        assert result["rsi"] < 50  # RSI should be below neutral
        # Score reflects overall bearish technicals, but oversold adds some points
        assert "technical_score" in result

    @patch("tradingagents.scanner.technical_screener._fetch_historical_data")
    def test_score_handles_column_names(self, mock_fetch):
        """Test handling of different column name formats"""
        # Test lowercase columns (Alpaca format)
        prices = [100 + i for i in range(100)]
        mock_fetch.return_value = pd.DataFrame({"close": prices})

        result = score_technical("TEST")
        assert "technical_score" in result

        # Test uppercase columns (yfinance format)
        mock_fetch.return_value = pd.DataFrame({"Close": prices})

        result = score_technical("TEST2")
        assert "technical_score" in result

    @patch("tradingagents.scanner.technical_screener._fetch_historical_data")
    def test_score_clamped(self, mock_fetch):
        """Test that score is clamped to 0-100"""
        # Extremely bullish setup
        prices = [50 + i for i in range(250)]
        mock_fetch.return_value = pd.DataFrame({"close": prices})

        result = score_technical("EXTREME")

        assert 0 <= result["technical_score"] <= 100


class TestBatchScoreTechnical:
    """Tests for batch_score_technical function"""

    def setup_method(self):
        clear_cache()

    @patch("tradingagents.scanner.technical_screener.score_technical")
    def test_batch_score_multiple(self, mock_score):
        """Test batch scoring multiple symbols"""
        mock_score.return_value = {
            "rsi": 55.0,
            "macd_signal": "neutral",
            "price_vs_50ma": "above",
            "price_vs_200ma": "neutral",
            "technical_score": 60,
        }

        symbols = ["AAPL", "MSFT", "GOOGL"]
        results = batch_score_technical(symbols)

        assert len(results) == 3
        assert all(sym in results for sym in symbols)
        assert mock_score.call_count == 3

    @patch("tradingagents.scanner.technical_screener.score_technical")
    def test_batch_score_empty(self, mock_score):
        """Test batch scoring empty list"""
        results = batch_score_technical([])
        assert results == {}
        mock_score.assert_not_called()


class TestFetchHistoricalData:
    """Tests for _fetch_historical_data function"""

    def setup_method(self):
        clear_cache()

    @patch("tradingagents.scanner.technical_screener.ALPACA_AVAILABLE", False)
    def test_fetch_no_alpaca(self):
        """Test fetch when Alpaca not available"""
        from tradingagents.scanner.technical_screener import _fetch_historical_data

        result = _fetch_historical_data("AAPL")
        assert result.empty

    @patch("tradingagents.scanner.technical_screener.ALPACA_AVAILABLE", True)
    @patch("tradingagents.scanner.technical_screener.AlpacaUtils")
    def test_fetch_success(self, mock_alpaca):
        """Test successful data fetch"""
        from tradingagents.scanner.technical_screener import _fetch_historical_data

        mock_alpaca.get_stock_data.return_value = pd.DataFrame({
            "close": [100, 101, 102],
            "volume": [1000, 1100, 1200],
        })

        result = _fetch_historical_data("AAPL", days=30)

        assert not result.empty
        mock_alpaca.get_stock_data.assert_called_once()

    @patch("tradingagents.scanner.technical_screener.ALPACA_AVAILABLE", True)
    @patch("tradingagents.scanner.technical_screener.AlpacaUtils")
    def test_fetch_error(self, mock_alpaca):
        """Test fetch handles errors gracefully"""
        from tradingagents.scanner.technical_screener import _fetch_historical_data

        mock_alpaca.get_stock_data.side_effect = Exception("API Error")

        result = _fetch_historical_data("ERROR")
        assert result.empty
