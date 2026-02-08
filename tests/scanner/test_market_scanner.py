"""
Unit tests for the market_scanner module
"""

import pytest
from unittest.mock import patch, MagicMock
from tradingagents.scanner.market_scanner import MarketScanner, run_scan
from tradingagents.scanner.scanner_result import ScannerResult
from tradingagents.scanner.cache import clear_cache


class TestMarketScannerInit:
    """Tests for MarketScanner initialization"""

    def test_default_config(self):
        """Test default configuration"""
        scanner = MarketScanner()

        assert scanner.num_results == 20
        assert scanner.min_price == 5.0
        assert scanner.min_volume == 500000
        assert scanner.use_llm is True
        assert scanner.use_llm_sentiment is False
        assert scanner.use_options_flow is True
        assert scanner.use_dynamic_universe is False
        assert scanner.cache_ttl == 300

    def test_custom_config(self):
        """Test custom configuration"""
        config = {
            "num_results": 10,
            "min_price": 10.0,
            "min_volume": 1000000,
            "use_llm": False,
            "scanner_use_llm_sentiment": True,
            "scanner_use_options_flow": False,
            "scanner_dynamic_universe": True,
            "scanner_cache_ttl": 600,
        }
        scanner = MarketScanner(config)

        assert scanner.num_results == 10
        assert scanner.min_price == 10.0
        assert scanner.min_volume == 1000000
        assert scanner.use_llm is False
        assert scanner.use_llm_sentiment is True
        assert scanner.use_options_flow is False
        assert scanner.use_dynamic_universe is True
        assert scanner.cache_ttl == 600


class TestMarketScannerScan:
    """Tests for MarketScanner.scan method"""

    def setup_method(self):
        clear_cache()

    @patch("tradingagents.scanner.market_scanner.get_top_movers")
    def test_scan_no_movers(self, mock_movers):
        """Test scan when no movers found"""
        mock_movers.return_value = []

        scanner = MarketScanner()
        results = scanner.scan()

        assert results == []

    @patch("tradingagents.scanner.market_scanner.batch_screen_options")
    @patch("tradingagents.scanner.market_scanner.score_news")
    @patch("tradingagents.scanner.market_scanner.score_technical")
    @patch("tradingagents.scanner.market_scanner.get_top_movers")
    def test_scan_full_pipeline(
        self, mock_movers, mock_tech, mock_news, mock_options
    ):
        """Test full scan pipeline"""
        # Mock movers
        mock_movers.return_value = [
            {
                "symbol": "AAPL",
                "company_name": "Apple Inc.",
                "price": 175.0,
                "change_percent": 2.5,
                "volume": 50000000,
                "volume_ratio": 1.5,
                "sector": "Technology",
                "market_cap": 2800000000000,
                "chart_data": [170, 172, 174, 175],
            },
            {
                "symbol": "MSFT",
                "company_name": "Microsoft",
                "price": 400.0,
                "change_percent": 1.5,
                "volume": 30000000,
                "volume_ratio": 1.2,
                "sector": "Technology",
                "market_cap": 3000000000000,
                "chart_data": [395, 397, 399, 400],
            },
        ]

        # Mock technical scores
        mock_tech.return_value = {
            "rsi": 55.0,
            "macd_signal": "bullish",
            "price_vs_50ma": "above",
            "price_vs_200ma": "above",
            "technical_score": 70,
        }

        # Mock news scores
        mock_news.return_value = {
            "news_sentiment": "neutral",
            "news_count": 3,
            "news_score": 55,
            "news_items": [],
        }

        # Mock options scores
        mock_options.return_value = {
            "AAPL": {
                "options_score": 65,
                "signal": "neutral",
                "has_unusual_activity": False,
            },
            "MSFT": {
                "options_score": 70,
                "signal": "bullish",
                "has_unusual_activity": True,
            },
        }

        scanner = MarketScanner({"use_llm": False, "num_results": 2})
        results = scanner.scan()

        assert len(results) == 2
        assert all(isinstance(r, ScannerResult) for r in results)
        assert results[0].symbol in ["AAPL", "MSFT"]

    @patch("tradingagents.scanner.market_scanner.batch_screen_options")
    @patch("tradingagents.scanner.market_scanner.score_news")
    @patch("tradingagents.scanner.market_scanner.score_technical")
    @patch("tradingagents.scanner.market_scanner.get_top_movers")
    def test_scan_without_options(
        self, mock_movers, mock_tech, mock_news, mock_options
    ):
        """Test scan with options disabled"""
        mock_movers.return_value = [
            {
                "symbol": "AAPL",
                "company_name": "Apple",
                "price": 175.0,
                "change_percent": 2.0,
                "volume": 50000000,
                "volume_ratio": 1.5,
                "sector": "Tech",
                "market_cap": None,
                "chart_data": [],
            }
        ]
        mock_tech.return_value = {"technical_score": 60}
        mock_news.return_value = {"news_score": 55, "news_sentiment": "neutral", "news_count": 0}

        scanner = MarketScanner({
            "use_llm": False,
            "scanner_use_options_flow": False,
        })
        results = scanner.scan()

        # Options should not be called
        mock_options.assert_not_called()
        assert len(results) == 1

    @patch("tradingagents.scanner.market_scanner.batch_screen_options")
    @patch("tradingagents.scanner.market_scanner.score_news")
    @patch("tradingagents.scanner.market_scanner.score_technical")
    @patch("tradingagents.scanner.market_scanner.get_top_movers")
    def test_scan_progress_callback(
        self, mock_movers, mock_tech, mock_news, mock_options
    ):
        """Test progress callback is called"""
        mock_movers.return_value = []

        progress_calls = []

        def callback(stage, progress):
            progress_calls.append((stage, progress))

        scanner = MarketScanner()
        scanner.scan(progress_callback=callback)

        # Should have at least fetching stage
        assert len(progress_calls) > 0
        assert progress_calls[0][0] == "fetching"

    @patch("tradingagents.scanner.market_scanner.get_top_movers")
    def test_scan_clears_expired_cache(self, mock_movers):
        """Test that scan clears expired cache entries"""
        mock_movers.return_value = []

        with patch("tradingagents.scanner.market_scanner.clear_expired") as mock_clear:
            mock_clear.return_value = 5

            scanner = MarketScanner()
            scanner.scan()

            mock_clear.assert_called_once()


class TestMarketScannerScoring:
    """Tests for score calculation logic"""

    def setup_method(self):
        clear_cache()

    @patch("tradingagents.scanner.market_scanner.batch_screen_options")
    @patch("tradingagents.scanner.market_scanner.score_news")
    @patch("tradingagents.scanner.market_scanner.score_technical")
    @patch("tradingagents.scanner.market_scanner.get_top_movers")
    def test_combined_score_with_options(
        self, mock_movers, mock_tech, mock_news, mock_options
    ):
        """Test combined score calculation with options"""
        mock_movers.return_value = [
            {
                "symbol": "TEST",
                "company_name": "Test",
                "price": 100.0,
                "change_percent": 1.0,
                "volume": 1000000,
                "volume_ratio": 1.0,
                "sector": "",
                "market_cap": None,
                "chart_data": [],
            }
        ]
        mock_tech.return_value = {"technical_score": 80}
        mock_news.return_value = {"news_score": 60, "news_sentiment": "neutral", "news_count": 0}
        mock_options.return_value = {
            "TEST": {"options_score": 70, "signal": "neutral", "has_unusual_activity": False}
        }

        scanner = MarketScanner({"use_llm": False, "scanner_use_options_flow": True})
        results = scanner.scan()

        # Combined = 80*0.5 + 60*0.3 + 70*0.2 = 40 + 18 + 14 = 72
        assert results[0].combined_score == 72

    @patch("tradingagents.scanner.market_scanner.batch_screen_options")
    @patch("tradingagents.scanner.market_scanner.score_news")
    @patch("tradingagents.scanner.market_scanner.score_technical")
    @patch("tradingagents.scanner.market_scanner.get_top_movers")
    def test_combined_score_without_options(
        self, mock_movers, mock_tech, mock_news, mock_options
    ):
        """Test combined score calculation without options"""
        mock_movers.return_value = [
            {
                "symbol": "TEST",
                "company_name": "Test",
                "price": 100.0,
                "change_percent": 1.0,
                "volume": 1000000,
                "volume_ratio": 1.0,
                "sector": "",
                "market_cap": None,
                "chart_data": [],
            }
        ]
        mock_tech.return_value = {"technical_score": 80}
        mock_news.return_value = {"news_score": 60, "news_sentiment": "neutral", "news_count": 0}

        scanner = MarketScanner({"use_llm": False, "scanner_use_options_flow": False})
        results = scanner.scan()

        # Combined = 80*0.6 + 60*0.4 = 48 + 24 = 72
        assert results[0].combined_score == 72

    @patch("tradingagents.scanner.market_scanner.batch_screen_options")
    @patch("tradingagents.scanner.market_scanner.score_news")
    @patch("tradingagents.scanner.market_scanner.score_technical")
    @patch("tradingagents.scanner.market_scanner.get_top_movers")
    def test_volume_ratio_bonus(
        self, mock_movers, mock_tech, mock_news, mock_options
    ):
        """Test volume ratio bonus in scoring"""
        mock_movers.return_value = [
            {
                "symbol": "HIGH_VOL",
                "company_name": "High Volume",
                "price": 100.0,
                "change_percent": 1.0,
                "volume": 10000000,
                "volume_ratio": 3.5,  # High volume ratio
                "sector": "",
                "market_cap": None,
                "chart_data": [],
            }
        ]
        mock_tech.return_value = {"technical_score": 50}
        mock_news.return_value = {"news_score": 50, "news_sentiment": "neutral", "news_count": 0}
        mock_options.return_value = {
            "HIGH_VOL": {"options_score": 50, "signal": "neutral", "has_unusual_activity": False}
        }

        scanner = MarketScanner({"use_llm": False})
        results = scanner.scan()

        # Base would be 50, but volume ratio > 3.0 should add +10
        assert results[0].combined_score >= 60


class TestSimpleRationale:
    """Tests for _simple_rationale method"""

    def test_rationale_strong_momentum(self):
        """Test rationale for strong momentum"""
        scanner = MarketScanner({"scanner_use_options_flow": False})
        result = ScannerResult(symbol="TEST", change_percent=5.0)

        rationale = scanner._simple_rationale(result)

        assert "Strong momentum" in rationale
        assert "5.0%" in rationale

    def test_rationale_pullback(self):
        """Test rationale for pullback"""
        scanner = MarketScanner({"scanner_use_options_flow": False})
        result = ScannerResult(symbol="TEST", change_percent=-4.0)

        rationale = scanner._simple_rationale(result)

        assert "pullback" in rationale.lower()

    def test_rationale_macd_bullish(self):
        """Test rationale includes MACD signal"""
        scanner = MarketScanner({"scanner_use_options_flow": False})
        result = ScannerResult(symbol="TEST", macd_signal="bullish")

        rationale = scanner._simple_rationale(result)

        assert "MACD" in rationale
        assert "bullish" in rationale.lower()

    def test_rationale_rsi_oversold(self):
        """Test rationale for oversold RSI"""
        scanner = MarketScanner({"scanner_use_options_flow": False})
        result = ScannerResult(symbol="TEST", rsi=25.0)

        rationale = scanner._simple_rationale(result)

        assert "RSI" in rationale
        assert "oversold" in rationale.lower()

    def test_rationale_unusual_volume(self):
        """Test rationale for unusual volume"""
        scanner = MarketScanner({"scanner_use_options_flow": False})
        result = ScannerResult(symbol="TEST", volume_ratio=2.5)

        rationale = scanner._simple_rationale(result)

        assert "volume" in rationale.lower()
        assert "2.5x" in rationale

    def test_rationale_options_signal(self):
        """Test rationale includes options signal when enabled"""
        scanner = MarketScanner({"scanner_use_options_flow": True})
        result = ScannerResult(symbol="TEST", options_signal="bullish")

        rationale = scanner._simple_rationale(result)

        assert "options" in rationale.lower()
        assert "bullish" in rationale.lower()

    def test_rationale_ends_with_period(self):
        """Test rationale ends with period"""
        scanner = MarketScanner({"scanner_use_options_flow": False})
        result = ScannerResult(symbol="TEST")

        rationale = scanner._simple_rationale(result)

        assert rationale.endswith(".")


class TestRunScan:
    """Tests for run_scan convenience function"""

    @patch("tradingagents.scanner.market_scanner.MarketScanner")
    def test_run_scan_creates_scanner(self, mock_scanner_class):
        """Test that run_scan creates scanner and calls scan"""
        mock_scanner = MagicMock()
        mock_scanner.scan.return_value = []
        mock_scanner_class.return_value = mock_scanner

        result = run_scan({"num_results": 5})

        mock_scanner_class.assert_called_once_with({"num_results": 5})
        mock_scanner.scan.assert_called_once()

    @patch("tradingagents.scanner.market_scanner.MarketScanner")
    def test_run_scan_default_config(self, mock_scanner_class):
        """Test run_scan with default config"""
        mock_scanner = MagicMock()
        mock_scanner.scan.return_value = []
        mock_scanner_class.return_value = mock_scanner

        run_scan()

        mock_scanner_class.assert_called_once_with(None)
