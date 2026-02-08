"""
Unit tests for the movers_fetcher module
"""

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from tradingagents.scanner.movers_fetcher import (
    get_top_movers,
    get_gainers,
    get_losers,
    get_volume_leaders,
    STOCK_UNIVERSE,
)
from tradingagents.scanner.cache import clear_cache


class TestStockUniverse:
    """Tests for STOCK_UNIVERSE constant"""

    def test_universe_not_empty(self):
        """Test that universe is not empty"""
        assert len(STOCK_UNIVERSE) > 0

    def test_universe_has_major_stocks(self):
        """Test universe includes major stocks"""
        major = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
        for stock in major:
            assert stock in STOCK_UNIVERSE

    def test_universe_no_duplicates(self):
        """Test universe has no duplicates"""
        assert len(STOCK_UNIVERSE) == len(set(STOCK_UNIVERSE))


class TestGetTopMovers:
    """Tests for get_top_movers function"""

    def setup_method(self):
        clear_cache()

    @patch("tradingagents.scanner.movers_fetcher._fetch_stock_data")
    @patch("tradingagents.scanner.movers_fetcher._get_company_info")
    def test_get_movers_success(self, mock_info, mock_fetch):
        """Test successful movers fetch"""
        # Mock stock data
        mock_fetch.return_value = pd.DataFrame({
            "close": [100, 102, 105, 108, 110],
            "volume": [1000000, 1100000, 1200000, 1300000, 1500000],
        })
        mock_info.return_value = {"name": "Test Corp", "sector": "Technology"}

        result = get_top_movers(min_price=5, min_volume=100000, limit=5)

        assert len(result) <= 5
        if len(result) > 0:
            assert "symbol" in result[0]
            assert "price" in result[0]
            assert "change_percent" in result[0]

    @patch("tradingagents.scanner.movers_fetcher._fetch_stock_data")
    def test_get_movers_no_data(self, mock_fetch):
        """Test movers fetch with no data"""
        mock_fetch.return_value = pd.DataFrame()

        result = get_top_movers(limit=5)

        # Should return empty or whatever passes filters
        assert isinstance(result, list)

    @patch("tradingagents.scanner.movers_fetcher._fetch_stock_data")
    @patch("tradingagents.scanner.movers_fetcher._get_company_info")
    def test_get_movers_filters_by_price(self, mock_info, mock_fetch):
        """Test that movers are filtered by min_price"""
        mock_fetch.return_value = pd.DataFrame({
            "close": [2, 2.1, 2.2, 2.3, 2.4],  # Below min price
            "volume": [1000000] * 5,
        })
        mock_info.return_value = {"name": "Penny Stock", "sector": "Unknown"}

        result = get_top_movers(min_price=5.0, limit=50)

        # All stocks should be filtered out due to price
        # (depends on universe, but cheap stocks filtered)
        for mover in result:
            assert mover["price"] >= 5.0

    @patch("tradingagents.scanner.movers_fetcher._fetch_stock_data")
    @patch("tradingagents.scanner.movers_fetcher._get_company_info")
    def test_get_movers_filters_by_volume(self, mock_info, mock_fetch):
        """Test that movers are filtered by min_volume"""
        mock_fetch.return_value = pd.DataFrame({
            "close": [100] * 5,
            "volume": [100] * 5,  # Below min volume
        })
        mock_info.return_value = {"name": "Low Vol", "sector": "Unknown"}

        result = get_top_movers(min_volume=500000, limit=50)

        for mover in result:
            assert mover["volume"] >= 500000

    @patch("tradingagents.scanner.movers_fetcher._fetch_stock_data")
    @patch("tradingagents.scanner.movers_fetcher._get_company_info")
    def test_get_movers_sorted_by_change(self, mock_info, mock_fetch):
        """Test that movers are sorted by absolute change"""
        def mock_data(symbol, days=5):
            # Return different changes for different symbols
            changes = {"AAPL": 5, "MSFT": -10, "GOOGL": 3}
            base = 100
            change = changes.get(symbol, 1)
            return pd.DataFrame({
                "close": [base, base + change],
                "volume": [1000000, 1000000],
            })

        mock_fetch.side_effect = mock_data
        mock_info.return_value = {"name": "Test", "sector": "Tech"}

        result = get_top_movers(limit=50)

        # Should be sorted by absolute change (biggest first)
        if len(result) >= 2:
            for i in range(len(result) - 1):
                assert abs(result[i]["change_percent"]) >= abs(result[i + 1]["change_percent"])

    @patch("tradingagents.scanner.movers_fetcher.get_dynamic_universe")
    @patch("tradingagents.scanner.movers_fetcher._fetch_stock_data")
    @patch("tradingagents.scanner.movers_fetcher._get_company_info")
    def test_get_movers_dynamic_universe(self, mock_info, mock_fetch, mock_universe):
        """Test using dynamic universe"""
        mock_universe.return_value = ["AAPL", "MSFT"]
        mock_fetch.return_value = pd.DataFrame({
            "close": [100, 105],
            "volume": [1000000, 1100000],
        })
        mock_info.return_value = {"name": "Test", "sector": "Tech"}

        result = get_top_movers(use_dynamic_universe=True, limit=10)

        mock_universe.assert_called_once()


class TestGetGainers:
    """Tests for get_gainers function"""

    def test_gainers_filters_positive(self):
        """Test that only positive changes are included"""
        movers = [
            {"symbol": "A", "change_percent": 5.0},
            {"symbol": "B", "change_percent": -3.0},
            {"symbol": "C", "change_percent": 2.0},
            {"symbol": "D", "change_percent": -1.0},
        ]

        gainers = get_gainers(movers)

        assert len(gainers) == 2
        assert all(g["change_percent"] > 0 for g in gainers)

    def test_gainers_sorted_descending(self):
        """Test that gainers are sorted by change descending"""
        movers = [
            {"symbol": "A", "change_percent": 2.0},
            {"symbol": "B", "change_percent": 5.0},
            {"symbol": "C", "change_percent": 3.0},
        ]

        gainers = get_gainers(movers)

        assert gainers[0]["change_percent"] == 5.0
        assert gainers[1]["change_percent"] == 3.0
        assert gainers[2]["change_percent"] == 2.0

    def test_gainers_respects_limit(self):
        """Test that limit is respected"""
        movers = [{"symbol": f"S{i}", "change_percent": i} for i in range(1, 30)]

        gainers = get_gainers(movers, limit=5)

        assert len(gainers) == 5

    def test_gainers_empty_list(self):
        """Test with no gainers"""
        movers = [
            {"symbol": "A", "change_percent": -5.0},
            {"symbol": "B", "change_percent": -3.0},
        ]

        gainers = get_gainers(movers)

        assert len(gainers) == 0


class TestGetLosers:
    """Tests for get_losers function"""

    def test_losers_filters_negative(self):
        """Test that only negative changes are included"""
        movers = [
            {"symbol": "A", "change_percent": 5.0},
            {"symbol": "B", "change_percent": -3.0},
            {"symbol": "C", "change_percent": -5.0},
        ]

        losers = get_losers(movers)

        assert len(losers) == 2
        assert all(l["change_percent"] < 0 for l in losers)

    def test_losers_sorted_ascending(self):
        """Test that losers are sorted by change ascending (worst first)"""
        movers = [
            {"symbol": "A", "change_percent": -2.0},
            {"symbol": "B", "change_percent": -5.0},
            {"symbol": "C", "change_percent": -3.0},
        ]

        losers = get_losers(movers)

        assert losers[0]["change_percent"] == -5.0
        assert losers[1]["change_percent"] == -3.0
        assert losers[2]["change_percent"] == -2.0

    def test_losers_respects_limit(self):
        """Test that limit is respected"""
        movers = [{"symbol": f"S{i}", "change_percent": -i} for i in range(1, 30)]

        losers = get_losers(movers, limit=5)

        assert len(losers) == 5


class TestGetVolumeLeaders:
    """Tests for get_volume_leaders function"""

    def test_volume_leaders_sorted(self):
        """Test that volume leaders are sorted by volume ratio"""
        movers = [
            {"symbol": "A", "volume_ratio": 1.5},
            {"symbol": "B", "volume_ratio": 3.0},
            {"symbol": "C", "volume_ratio": 2.0},
        ]

        leaders = get_volume_leaders(movers)

        assert leaders[0]["volume_ratio"] == 3.0
        assert leaders[1]["volume_ratio"] == 2.0
        assert leaders[2]["volume_ratio"] == 1.5

    def test_volume_leaders_respects_limit(self):
        """Test that limit is respected"""
        movers = [{"symbol": f"S{i}", "volume_ratio": i} for i in range(1, 30)]

        leaders = get_volume_leaders(movers, limit=5)

        assert len(leaders) == 5

    def test_volume_leaders_all_included(self):
        """Test that all movers can be volume leaders"""
        movers = [
            {"symbol": "A", "volume_ratio": 1.5, "change_percent": -5.0},
            {"symbol": "B", "volume_ratio": 3.0, "change_percent": 2.0},
        ]

        leaders = get_volume_leaders(movers)

        assert len(leaders) == 2


class TestFetchStockData:
    """Tests for _fetch_stock_data function"""

    def setup_method(self):
        clear_cache()

    @patch("tradingagents.scanner.movers_fetcher.ALPACA_AVAILABLE", False)
    def test_fetch_no_alpaca(self):
        """Test fetch when Alpaca not available"""
        from tradingagents.scanner.movers_fetcher import _fetch_stock_data

        result = _fetch_stock_data("AAPL")
        assert result.empty

    @patch("tradingagents.scanner.movers_fetcher.ALPACA_AVAILABLE", True)
    @patch("tradingagents.scanner.movers_fetcher.AlpacaUtils")
    def test_fetch_success(self, mock_alpaca):
        """Test successful data fetch"""
        from tradingagents.scanner.movers_fetcher import _fetch_stock_data

        mock_alpaca.get_stock_data.return_value = pd.DataFrame({
            "close": [100, 101, 102],
            "volume": [1000, 1100, 1200],
        })

        result = _fetch_stock_data("AAPL", days=5)

        assert not result.empty

    @patch("tradingagents.scanner.movers_fetcher.ALPACA_AVAILABLE", True)
    @patch("tradingagents.scanner.movers_fetcher.AlpacaUtils")
    def test_fetch_error_returns_empty(self, mock_alpaca):
        """Test that errors return empty DataFrame"""
        from tradingagents.scanner.movers_fetcher import _fetch_stock_data

        mock_alpaca.get_stock_data.side_effect = Exception("API Error")

        result = _fetch_stock_data("ERROR")
        assert result.empty


class TestGetCompanyInfo:
    """Tests for _get_company_info function"""

    def setup_method(self):
        clear_cache()

    @patch("tradingagents.scanner.movers_fetcher.ALPACA_AVAILABLE", False)
    def test_info_no_alpaca(self):
        """Test info when Alpaca not available"""
        from tradingagents.scanner.movers_fetcher import _get_company_info

        result = _get_company_info("AAPL")

        assert result["name"] == "AAPL"
        assert result["sector"] == "Unknown"

    @patch("tradingagents.scanner.movers_fetcher.ALPACA_AVAILABLE", True)
    @patch("tradingagents.scanner.movers_fetcher.get_alpaca_trading_client")
    def test_info_success(self, mock_client_func):
        """Test successful info fetch"""
        from tradingagents.scanner.movers_fetcher import _get_company_info

        mock_client = MagicMock()
        mock_client_func.return_value = mock_client

        mock_asset = MagicMock()
        mock_asset.name = "Apple Inc."
        mock_asset.sector = "Technology"
        mock_client.get_asset.return_value = mock_asset

        result = _get_company_info("AAPL")

        assert result["name"] == "Apple Inc."

    @patch("tradingagents.scanner.movers_fetcher.ALPACA_AVAILABLE", True)
    @patch("tradingagents.scanner.movers_fetcher.get_alpaca_trading_client")
    def test_info_error_fallback(self, mock_client_func):
        """Test fallback on error"""
        from tradingagents.scanner.movers_fetcher import _get_company_info

        mock_client_func.side_effect = Exception("API Error")

        result = _get_company_info("AAPL")

        # Should use fallback
        assert "name" in result
        assert "sector" in result
