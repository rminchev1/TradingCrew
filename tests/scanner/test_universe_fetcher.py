"""
Unit tests for the universe_fetcher module
"""

import pytest
from unittest.mock import patch, MagicMock
from tradingagents.scanner.universe_fetcher import (
    get_sector_universe,
    get_all_sectors,
    get_combined_universe,
    get_dynamic_universe,
    SECTOR_UNIVERSES,
    DEFAULT_UNIVERSE,
)
from tradingagents.scanner.cache import clear_cache


class TestSectorUniverses:
    """Tests for sector-based universes"""

    def test_sector_universes_not_empty(self):
        """Test that all sector universes have stocks"""
        for sector, stocks in SECTOR_UNIVERSES.items():
            assert len(stocks) > 0, f"Sector {sector} is empty"

    def test_sector_universes_has_expected_sectors(self):
        """Test that expected sectors exist"""
        expected_sectors = [
            "technology",
            "semiconductors",
            "fintech",
            "healthcare",
            "energy",
        ]
        for sector in expected_sectors:
            assert sector in SECTOR_UNIVERSES

    def test_get_sector_universe_valid(self):
        """Test getting a valid sector universe"""
        tech_stocks = get_sector_universe("technology")
        assert len(tech_stocks) > 0
        assert "AAPL" in tech_stocks or "MSFT" in tech_stocks

    def test_get_sector_universe_case_insensitive(self):
        """Test that sector lookup is case insensitive"""
        tech1 = get_sector_universe("Technology")
        tech2 = get_sector_universe("TECHNOLOGY")
        tech3 = get_sector_universe("technology")
        assert tech1 == tech2 == tech3

    def test_get_sector_universe_partial_match(self):
        """Test partial sector name matching"""
        semi = get_sector_universe("semi")
        assert len(semi) > 0
        # Should match semiconductors
        assert "NVDA" in semi or "AMD" in semi

    def test_get_sector_universe_unknown(self):
        """Test unknown sector returns default universe"""
        result = get_sector_universe("nonexistent_sector")
        assert result == DEFAULT_UNIVERSE


class TestGetAllSectors:
    """Tests for get_all_sectors function"""

    def test_get_all_sectors_returns_list(self):
        """Test that get_all_sectors returns a list"""
        sectors = get_all_sectors()
        assert isinstance(sectors, list)
        assert len(sectors) > 0

    def test_get_all_sectors_matches_dict_keys(self):
        """Test that returned sectors match SECTOR_UNIVERSES keys"""
        sectors = get_all_sectors()
        assert set(sectors) == set(SECTOR_UNIVERSES.keys())


class TestGetCombinedUniverse:
    """Tests for get_combined_universe function"""

    def test_combined_universe_single_sector(self):
        """Test combining a single sector"""
        combined = get_combined_universe(["technology"])
        tech = get_sector_universe("technology")
        assert set(combined) == set(tech)

    def test_combined_universe_multiple_sectors(self):
        """Test combining multiple sectors"""
        combined = get_combined_universe(["technology", "semiconductors"])
        tech = set(get_sector_universe("technology"))
        semi = set(get_sector_universe("semiconductors"))
        assert set(combined) == tech.union(semi)

    def test_combined_universe_no_duplicates(self):
        """Test that combined universe has no duplicates"""
        combined = get_combined_universe(["technology", "semiconductors"])
        assert len(combined) == len(set(combined))

    def test_combined_universe_all_sectors(self):
        """Test combining all sectors (None parameter)"""
        combined = get_combined_universe(None)
        assert len(combined) > 0
        # Should include stocks from multiple sectors
        assert "AAPL" in combined  # tech
        assert "XOM" in combined or "CVX" in combined  # energy


class TestDefaultUniverse:
    """Tests for DEFAULT_UNIVERSE"""

    def test_default_universe_not_empty(self):
        """Test that default universe is not empty"""
        assert len(DEFAULT_UNIVERSE) > 0

    def test_default_universe_has_major_stocks(self):
        """Test that default universe includes major stocks"""
        major_stocks = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
        for stock in major_stocks:
            assert stock in DEFAULT_UNIVERSE

    def test_default_universe_no_duplicates(self):
        """Test that default universe has no duplicates"""
        assert len(DEFAULT_UNIVERSE) == len(set(DEFAULT_UNIVERSE))


class TestGetDynamicUniverse:
    """Tests for get_dynamic_universe function (mocked)"""

    def setup_method(self):
        """Clear cache before each test"""
        clear_cache()

    @patch("tradingagents.scanner.universe_fetcher.get_alpaca_trading_client")
    def test_dynamic_universe_success(self, mock_get_client):
        """Test successful dynamic universe fetch"""
        # Mock the Alpaca client and assets
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Create mock assets
        mock_assets = []
        for symbol in ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]:
            asset = MagicMock()
            asset.symbol = symbol
            asset.tradable = True
            asset.shortable = True
            mock_assets.append(asset)

        mock_client.get_all_assets.return_value = mock_assets

        result = get_dynamic_universe(max_symbols=10)

        assert len(result) > 0
        assert "AAPL" in result

    @patch("tradingagents.scanner.universe_fetcher.get_alpaca_trading_client", None)
    def test_dynamic_universe_no_client(self):
        """Test fallback when Alpaca client not available"""
        # When client is None, should fall back to DEFAULT_UNIVERSE
        result = get_dynamic_universe(max_symbols=50)
        assert len(result) <= 50
        # Should return subset of default universe
        for symbol in result:
            assert symbol in DEFAULT_UNIVERSE

    @patch("tradingagents.scanner.universe_fetcher.get_alpaca_trading_client")
    def test_dynamic_universe_error_fallback(self, mock_get_client):
        """Test fallback on API error"""
        mock_get_client.side_effect = Exception("API Error")

        result = get_dynamic_universe(max_symbols=50)

        # Should fall back to default universe
        assert len(result) <= 50

    def test_dynamic_universe_respects_max_symbols(self):
        """Test that max_symbols is respected"""
        result = get_dynamic_universe(max_symbols=10)
        assert len(result) <= 10
