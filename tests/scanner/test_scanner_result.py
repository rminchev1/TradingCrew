"""
Unit tests for the scanner_result module
"""

import pytest
from tradingagents.scanner.scanner_result import ScannerResult


class TestScannerResult:
    """Tests for ScannerResult dataclass"""

    def test_create_with_symbol_only(self):
        """Test creating result with just symbol"""
        result = ScannerResult(symbol="AAPL")
        assert result.symbol == "AAPL"
        assert result.price == 0.0
        assert result.technical_score == 50
        assert result.options_score == 50.0
        assert result.options_signal == "neutral"

    def test_create_with_all_fields(self):
        """Test creating result with all fields"""
        result = ScannerResult(
            symbol="NVDA",
            company_name="NVIDIA Corporation",
            price=450.50,
            change_percent=3.5,
            volume=50000000,
            volume_ratio=2.5,
            rsi=65.5,
            macd_signal="bullish",
            price_vs_50ma="above",
            price_vs_200ma="above",
            technical_score=75,
            news_sentiment="bullish",
            news_count=5,
            news_score=70,
            options_score=80.0,
            options_signal="bullish",
            combined_score=75,
            rationale="Strong momentum",
            chart_data=[440, 445, 448, 450, 450.5],
            sector="Technology",
            market_cap=1100000000000,
        )
        assert result.symbol == "NVDA"
        assert result.price == 450.50
        assert result.options_score == 80.0
        assert result.options_signal == "bullish"

    def test_default_values(self):
        """Test default values are set correctly"""
        result = ScannerResult(symbol="TEST")

        assert result.company_name == ""
        assert result.price == 0.0
        assert result.change_percent == 0.0
        assert result.volume == 0
        assert result.volume_ratio == 1.0
        assert result.rsi == 50.0
        assert result.macd_signal == "neutral"
        assert result.price_vs_50ma == "neutral"
        assert result.price_vs_200ma == "neutral"
        assert result.technical_score == 50
        assert result.news_sentiment == "neutral"
        assert result.news_count == 0
        assert result.news_score == 50
        assert result.options_score == 50.0
        assert result.options_signal == "neutral"
        assert result.combined_score == 50
        assert result.rationale == ""
        assert result.chart_data == []
        assert result.sector == ""
        assert result.market_cap is None


class TestTotalScore:
    """Tests for total_score property"""

    def test_total_score_default(self):
        """Test total score with default values (all 50)"""
        result = ScannerResult(symbol="TEST")
        # 50 * 0.5 + 50 * 0.3 + 50 * 0.2 = 25 + 15 + 10 = 50
        assert result.total_score == 50.0

    def test_total_score_weighted(self):
        """Test total score weighting"""
        result = ScannerResult(
            symbol="TEST",
            technical_score=100,
            news_score=100,
            options_score=100,
        )
        # 100 * 0.5 + 100 * 0.3 + 100 * 0.2 = 50 + 30 + 20 = 100
        assert result.total_score == 100.0

    def test_total_score_mixed(self):
        """Test total score with mixed values"""
        result = ScannerResult(
            symbol="TEST",
            technical_score=80,  # 80 * 0.5 = 40
            news_score=60,  # 60 * 0.3 = 18
            options_score=70,  # 70 * 0.2 = 14
        )
        expected = 80 * 0.5 + 60 * 0.3 + 70 * 0.2  # 40 + 18 + 14 = 72
        assert result.total_score == expected

    def test_total_score_technical_weight_highest(self):
        """Test that technical score has highest weight"""
        # If only technical is high, total should reflect that
        result = ScannerResult(
            symbol="TEST",
            technical_score=100,
            news_score=0,
            options_score=0,
        )
        assert result.total_score == 50.0  # 100 * 0.5

        # If only options is high, total should be lower
        result2 = ScannerResult(
            symbol="TEST",
            technical_score=0,
            news_score=0,
            options_score=100,
        )
        assert result2.total_score == 20.0  # 100 * 0.2


class TestToDict:
    """Tests for to_dict method"""

    def test_to_dict_contains_all_fields(self):
        """Test that to_dict includes all fields"""
        result = ScannerResult(symbol="AAPL")
        d = result.to_dict()

        expected_keys = [
            "symbol",
            "company_name",
            "price",
            "change_percent",
            "volume",
            "volume_ratio",
            "rsi",
            "macd_signal",
            "price_vs_50ma",
            "price_vs_200ma",
            "technical_score",
            "news_sentiment",
            "news_count",
            "news_score",
            "options_score",
            "options_signal",
            "combined_score",
            "total_score",
            "rationale",
            "chart_data",
            "sector",
            "market_cap",
        ]

        for key in expected_keys:
            assert key in d, f"Missing key: {key}"

    def test_to_dict_includes_total_score(self):
        """Test that to_dict includes computed total_score"""
        result = ScannerResult(
            symbol="TEST",
            technical_score=80,
            news_score=60,
            options_score=70,
        )
        d = result.to_dict()
        assert "total_score" in d
        assert d["total_score"] == result.total_score

    def test_to_dict_values_correct(self):
        """Test that to_dict values match object attributes"""
        result = ScannerResult(
            symbol="NVDA",
            price=450.0,
            options_score=75.0,
            options_signal="bullish",
        )
        d = result.to_dict()

        assert d["symbol"] == "NVDA"
        assert d["price"] == 450.0
        assert d["options_score"] == 75.0
        assert d["options_signal"] == "bullish"


class TestFromDict:
    """Tests for from_dict class method"""

    def test_from_dict_basic(self):
        """Test creating ScannerResult from dict"""
        data = {
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "price": 175.0,
            "change_percent": 1.5,
            "volume": 50000000,
            "volume_ratio": 1.2,
            "rsi": 55.0,
            "macd_signal": "bullish",
            "price_vs_50ma": "above",
            "price_vs_200ma": "above",
            "technical_score": 70,
            "news_sentiment": "neutral",
            "news_count": 3,
            "news_score": 55,
            "options_score": 65.0,
            "options_signal": "neutral",
            "combined_score": 65,
            "rationale": "Test rationale",
            "chart_data": [170, 172, 174, 175],
            "sector": "Technology",
            "market_cap": 2800000000000,
        }

        result = ScannerResult.from_dict(data)

        assert result.symbol == "AAPL"
        assert result.price == 175.0
        assert result.options_score == 65.0

    def test_from_dict_ignores_total_score(self):
        """Test that from_dict ignores total_score (computed property)"""
        data = {
            "symbol": "TEST",
            "total_score": 999,  # Should be ignored
        }

        result = ScannerResult.from_dict(data)
        assert result.total_score != 999

    def test_roundtrip(self):
        """Test that to_dict -> from_dict preserves data"""
        original = ScannerResult(
            symbol="MSFT",
            price=400.0,
            technical_score=75,
            news_score=65,
            options_score=80.0,
            options_signal="bullish",
        )

        d = original.to_dict()
        restored = ScannerResult.from_dict(d)

        assert restored.symbol == original.symbol
        assert restored.price == original.price
        assert restored.technical_score == original.technical_score
        assert restored.options_score == original.options_score
        assert restored.options_signal == original.options_signal
