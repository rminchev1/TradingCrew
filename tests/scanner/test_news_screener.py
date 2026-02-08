"""
Unit tests for the news_screener module
"""

import pytest
from unittest.mock import patch, MagicMock
from tradingagents.scanner.news_screener import (
    analyze_sentiment,
    analyze_sentiment_llm,
    get_news_for_symbol,
    score_news,
    batch_score_news,
    BULLISH_KEYWORDS,
    BEARISH_KEYWORDS,
)
from tradingagents.scanner.cache import clear_cache


class TestAnalyzeSentiment:
    """Tests for keyword-based sentiment analysis"""

    def test_bullish_keywords(self):
        """Test detection of bullish headlines"""
        headlines = [
            "Stock surges on strong earnings beat",
            "Company gains after positive revenue growth",
            "Analysts upgrade rating following breakthrough innovation",
        ]
        for headline in headlines:
            assert analyze_sentiment(headline) == "bullish"

    def test_bearish_keywords(self):
        """Test detection of bearish headlines"""
        headlines = [
            "Stock plunges on earnings miss",
            "Company faces lawsuit and investigation",
            "Analysts downgrade after weak guidance",
        ]
        for headline in headlines:
            assert analyze_sentiment(headline) == "bearish"

    def test_neutral_headlines(self):
        """Test neutral headlines"""
        headlines = [
            "Company announces quarterly results",
            "CEO to speak at conference",
            "Stock trades sideways ahead of Fed decision",
        ]
        for headline in headlines:
            assert analyze_sentiment(headline) == "neutral"

    def test_empty_text(self):
        """Test empty text returns neutral"""
        assert analyze_sentiment("") == "neutral"
        assert analyze_sentiment(None) == "neutral"

    def test_mixed_keywords(self):
        """Test headlines with both bullish and bearish keywords"""
        # When balanced, should be neutral
        headline = "Stock gains despite concerns about debt"
        result = analyze_sentiment(headline)
        # One bullish (gains), one bearish (concerns) - neutral
        assert result == "neutral"

    def test_case_insensitive(self):
        """Test that analysis is case insensitive"""
        # Need multiple keywords to overcome neutral threshold
        assert analyze_sentiment("STOCK SURGES ON STRONG GROWTH") == "bullish"
        assert analyze_sentiment("stock PLUNGES in massive CRASH") == "bearish"


class TestAnalyzeSentimentLLM:
    """Tests for LLM-based sentiment analysis"""

    def setup_method(self):
        clear_cache()

    @patch("tradingagents.scanner.news_screener.OPENAI_AVAILABLE", False)
    def test_llm_unavailable_fallback(self):
        """Test fallback when OpenAI not available"""
        # Need multiple bullish keywords to pass threshold
        result = analyze_sentiment_llm("Stock surges on strong earnings beat and growth")

        assert result["sentiment"] == "bullish"  # Falls back to keyword
        assert result["llm_used"] is False
        assert "unavailable" in result["reasoning"].lower()

    @patch("tradingagents.scanner.news_screener.OPENAI_AVAILABLE", True)
    @patch.dict("os.environ", {}, clear=True)
    def test_no_api_key_fallback(self):
        """Test fallback when no API key"""
        result = analyze_sentiment_llm("Stock gains on news")

        assert result["llm_used"] is False
        assert "no api key" in result["reasoning"].lower()

    @patch("tradingagents.scanner.news_screener.OPENAI_AVAILABLE", True)
    @patch("tradingagents.scanner.news_screener.OpenAI")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_llm_success(self, mock_openai_class):
        """Test successful LLM analysis"""
        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"sentiment": "bullish", "confidence": 0.9, "reasoning": "Strong earnings"}'
        )
        mock_client.chat.completions.create.return_value = mock_response

        result = analyze_sentiment_llm("Company beats earnings expectations")

        assert result["sentiment"] == "bullish"
        assert result["confidence"] == 0.9
        assert result["llm_used"] is True

    @patch("tradingagents.scanner.news_screener.OPENAI_AVAILABLE", True)
    @patch("tradingagents.scanner.news_screener.OpenAI")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_llm_handles_markdown_response(self, mock_openai_class):
        """Test handling of markdown-wrapped JSON response"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '```json\n{"sentiment": "bearish", "confidence": 0.8, "reasoning": "Missed targets"}\n```'
        )
        mock_client.chat.completions.create.return_value = mock_response

        result = analyze_sentiment_llm("Company misses revenue targets")

        assert result["sentiment"] == "bearish"
        assert result["llm_used"] is True

    @patch("tradingagents.scanner.news_screener.OPENAI_AVAILABLE", True)
    @patch("tradingagents.scanner.news_screener.OpenAI")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_llm_error_fallback(self, mock_openai_class):
        """Test fallback on LLM error"""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        # Need multiple bullish keywords to pass threshold
        result = analyze_sentiment_llm("Stock surges on strong earnings beat")

        assert result["sentiment"] == "bullish"  # Falls back to keyword
        assert result["llm_used"] is False
        assert "error" in result["reasoning"].lower()


class TestScoreNews:
    """Tests for score_news function"""

    def setup_method(self):
        clear_cache()

    @patch("tradingagents.scanner.news_screener.get_news_for_symbol")
    def test_no_news(self, mock_get_news):
        """Test scoring when no news available"""
        mock_get_news.return_value = []

        result = score_news("AAPL")

        assert result["news_sentiment"] == "neutral"
        assert result["news_count"] == 0
        assert result["news_score"] == 50
        assert result["news_items"] == []

    @patch("tradingagents.scanner.news_screener.get_news_for_symbol")
    def test_bullish_news(self, mock_get_news):
        """Test scoring with bullish news"""
        mock_get_news.return_value = [
            {"title": "Stock surges", "sentiment": "bullish", "source": "Test"},
            {"title": "Earnings beat", "sentiment": "bullish", "source": "Test"},
            {"title": "Upgrade rating", "sentiment": "bullish", "source": "Test"},
        ]

        result = score_news("AAPL")

        assert result["news_sentiment"] == "bullish"
        assert result["news_count"] == 3
        assert result["news_score"] > 50

    @patch("tradingagents.scanner.news_screener.get_news_for_symbol")
    def test_bearish_news(self, mock_get_news):
        """Test scoring with bearish news"""
        mock_get_news.return_value = [
            {"title": "Stock drops", "sentiment": "bearish", "source": "Test"},
            {"title": "Earnings miss", "sentiment": "bearish", "source": "Test"},
            {"title": "Downgrade", "sentiment": "bearish", "source": "Test"},
        ]

        result = score_news("AAPL")

        assert result["news_sentiment"] == "bearish"
        assert result["news_score"] < 50

    @patch("tradingagents.scanner.news_screener.get_news_for_symbol")
    def test_mixed_news(self, mock_get_news):
        """Test scoring with mixed news"""
        mock_get_news.return_value = [
            {"title": "Good news", "sentiment": "bullish", "source": "Test"},
            {"title": "Bad news", "sentiment": "bearish", "source": "Test"},
            {"title": "Neutral", "sentiment": "neutral", "source": "Test"},
        ]

        result = score_news("AAPL")

        assert result["news_sentiment"] == "neutral"
        assert 40 <= result["news_score"] <= 60

    @patch("tradingagents.scanner.news_screener.get_news_for_symbol")
    def test_high_volume_bonus(self, mock_get_news):
        """Test bonus for high news volume"""
        mock_get_news.return_value = [
            {"title": f"News {i}", "sentiment": "neutral", "source": "Test"}
            for i in range(6)
        ]

        result = score_news("AAPL")

        # Should get volume bonus
        assert result["news_score"] >= 55

    def test_use_llm_parameter(self):
        """Test that use_llm parameter is passed through"""
        with patch("tradingagents.scanner.news_screener.get_news_for_symbol") as mock:
            mock.return_value = []

            score_news("AAPL", use_llm=True)

            mock.assert_called_once_with("AAPL", use_llm=True)


class TestBatchScoreNews:
    """Tests for batch_score_news function"""

    def setup_method(self):
        clear_cache()

    @patch("tradingagents.scanner.news_screener.score_news")
    def test_batch_score_multiple(self, mock_score):
        """Test batch scoring multiple symbols"""
        mock_score.return_value = {
            "news_sentiment": "neutral",
            "news_count": 2,
            "news_score": 55,
            "news_items": [],
        }

        symbols = ["AAPL", "MSFT", "GOOGL"]
        results = batch_score_news(symbols)

        assert len(results) == 3
        assert all(sym in results for sym in symbols)
        assert mock_score.call_count == 3

    @patch("tradingagents.scanner.news_screener.score_news")
    def test_batch_score_with_llm(self, mock_score):
        """Test batch scoring with LLM enabled"""
        mock_score.return_value = {"news_score": 50, "news_items": []}

        batch_score_news(["AAPL"], use_llm=True)

        mock_score.assert_called_with("AAPL", use_llm=True)


class TestGetNewsForSymbol:
    """Tests for get_news_for_symbol function"""

    def setup_method(self):
        clear_cache()

    @patch("tradingagents.scanner.news_screener.FinnhubDataFetcher", None)
    @patch("tradingagents.scanner.news_screener.getNewsData", None)
    def test_no_news_sources(self):
        """Test behavior when no news sources available"""
        result = get_news_for_symbol("AAPL")
        assert result == []

    @patch("tradingagents.scanner.news_screener.FinnhubDataFetcher")
    def test_finnhub_news(self, mock_finnhub_class):
        """Test fetching from Finnhub"""
        mock_fetcher = MagicMock()
        mock_finnhub_class.return_value = mock_fetcher
        mock_fetcher.get_company_news.return_value = [
            {"headline": "Stock surges on strong earnings beat with growth", "source": "Reuters"},
            {"headline": "Company expands operations", "source": "Bloomberg"},
        ]

        result = get_news_for_symbol("AAPL", use_llm=False)

        assert len(result) == 2
        assert result[0]["title"] == "Stock surges on strong earnings beat with growth"
        assert result[0]["sentiment"] == "bullish"

    @patch("tradingagents.scanner.news_screener.FinnhubDataFetcher")
    def test_news_with_llm_sentiment(self, mock_finnhub_class):
        """Test news fetching with LLM sentiment"""
        mock_fetcher = MagicMock()
        mock_finnhub_class.return_value = mock_fetcher
        mock_fetcher.get_company_news.return_value = [
            {"headline": "Ambiguous headline here", "source": "Test"},
        ]

        with patch(
            "tradingagents.scanner.news_screener.analyze_sentiment_llm"
        ) as mock_llm:
            mock_llm.return_value = {"sentiment": "bullish"}

            result = get_news_for_symbol("AAPL", use_llm=True)

            mock_llm.assert_called_once()
            assert result[0]["sentiment"] == "bullish"
