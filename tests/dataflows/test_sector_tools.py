"""
Tests for sector utilities and tools.
"""

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np


class TestSectorUtils:
    """Tests for sector_utils.py module."""

    @patch('tradingagents.dataflows.sector_utils._get_yfinance_sector_info')
    def test_identify_sector_known_stock(self, mock_yf):
        """Test sector identification for a known stock."""
        from tradingagents.dataflows.sector_utils import identify_sector

        # Mock yfinance response
        mock_yf.return_value = {"sector": "Technology", "industry": "Consumer Electronics"}

        result = identify_sector("AAPL")

        assert result["sector"] == "Technology"
        assert result["sector_etf"] == "XLK"
        assert "AAPL" not in result["peers"]  # Should not include itself

    @patch('tradingagents.dataflows.sector_utils._get_yfinance_sector_info')
    def test_identify_sector_semiconductor(self, mock_yf):
        """Test sector identification for a semiconductor stock."""
        from tradingagents.dataflows.sector_utils import identify_sector

        # Mock yfinance response - NVDA is in semiconductors
        mock_yf.return_value = {"sector": "Technology", "industry": "Semiconductors"}

        result = identify_sector("NVDA")

        # Should get SMH because industry is "Semiconductors"
        assert result["sector"] == "Technology"
        assert result["sector_etf"] == "SMH"  # Semiconductor ETF
        assert len(result["peers"]) > 0

    @patch('tradingagents.dataflows.sector_utils._get_yfinance_sector_info')
    def test_identify_sector_unknown_stock(self, mock_yf):
        """Test sector identification for an unknown stock."""
        from tradingagents.dataflows.sector_utils import identify_sector

        # Mock yfinance returning empty (unknown stock)
        mock_yf.return_value = {}

        result = identify_sector("UNKNOWN123")

        assert result["sector"] == "Unknown"
        assert result["sector_etf"] == "SPY"  # Default benchmark
        assert result["peers"] == []

    @patch('tradingagents.dataflows.sector_utils._get_yfinance_sector_info')
    def test_identify_sector_case_insensitive(self, mock_yf):
        """Test that sector identification is case insensitive."""
        from tradingagents.dataflows.sector_utils import identify_sector

        mock_yf.return_value = {"sector": "Technology", "industry": "Consumer Electronics"}

        result_upper = identify_sector("AAPL")
        result_lower = identify_sector("aapl")

        assert result_upper["sector"] == result_lower["sector"]
        assert result_upper["sector_etf"] == result_lower["sector_etf"]

    def test_get_sector_etf(self):
        """Test getting sector ETF for a sector name."""
        from tradingagents.dataflows.sector_utils import get_sector_etf

        assert get_sector_etf("technology") == "XLK"
        assert get_sector_etf("financials") == "XLF"
        assert get_sector_etf("energy") == "XLE"
        assert get_sector_etf("unknown_sector") == "SPY"  # Default

    def test_get_sector_classification(self):
        """Test sector classification (offensive/defensive/cyclical)."""
        from tradingagents.dataflows.sector_utils import get_sector_classification

        assert get_sector_classification("XLK") == "offensive"
        assert get_sector_classification("XLV") == "defensive"
        assert get_sector_classification("XLB") == "cyclical"
        assert get_sector_classification("UNKNOWN") == "unknown"

    def test_get_all_sector_etfs(self):
        """Test getting all sector ETFs."""
        from tradingagents.dataflows.sector_utils import get_all_sector_etfs

        etfs = get_all_sector_etfs()

        assert len(etfs) == 11  # 11 sector ETFs
        assert "XLK" in etfs
        assert "XLF" in etfs
        assert "SPY" not in etfs  # SPY is not a sector ETF

    @patch('tradingagents.dataflows.sector_utils._get_yfinance_sector_info')
    def test_get_sector_peers(self, mock_yf):
        """Test getting sector peers for a ticker."""
        from tradingagents.dataflows.sector_utils import get_sector_peers

        mock_yf.return_value = {"sector": "Technology", "industry": "Consumer Electronics"}

        sector, etf, peers = get_sector_peers("AAPL", max_peers=5)

        assert sector == "Technology"
        assert etf == "XLK"
        assert len(peers) <= 5
        assert "AAPL" not in peers


class TestSectorToolkit:
    """Tests for sector tools in the Toolkit class."""

    @patch('tradingagents.dataflows.sector_utils._get_yfinance_sector_info')
    @patch('tradingagents.dataflows.alpaca_utils.AlpacaUtils.get_stock_data')
    def test_get_sector_peers_tool(self, mock_get_stock_data, mock_yf):
        """Test the get_sector_peers tool."""
        from tradingagents.agents.utils.agent_utils import Toolkit

        mock_yf.return_value = {"sector": "Technology", "industry": "Consumer Electronics"}

        result = Toolkit.get_sector_peers.invoke({
            "ticker": "AAPL",
            "curr_date": "2024-01-15"
        })

        assert "AAPL" in result
        assert "technology" in result.lower() or "Technology" in result
        assert "XLK" in result

    @patch('tradingagents.dataflows.sector_utils._get_yfinance_sector_info')
    @patch('tradingagents.dataflows.alpaca_utils.AlpacaUtils.get_stock_data')
    def test_get_peer_comparison_tool(self, mock_get_stock_data, mock_yf):
        """Test the get_peer_comparison tool."""
        from tradingagents.agents.utils.agent_utils import Toolkit

        mock_yf.return_value = {"sector": "Technology", "industry": "Consumer Electronics"}

        # Mock stock data
        dates = pd.date_range('2024-01-01', periods=35, freq='D')
        mock_df = pd.DataFrame({
            'close': np.random.uniform(100, 200, 35),
            'volume': np.random.randint(1000000, 10000000, 35)
        }, index=dates)
        mock_get_stock_data.return_value = mock_df

        result = Toolkit.get_peer_comparison.invoke({
            "ticker": "AAPL",
            "curr_date": "2024-01-15",
            "look_back_days": 30
        })

        assert "AAPL" in result
        assert "Peer Comparison" in result

    @patch('tradingagents.dataflows.alpaca_utils.AlpacaUtils.get_stock_data')
    def test_get_relative_strength_tool(self, mock_get_stock_data):
        """Test the get_relative_strength tool."""
        from tradingagents.agents.utils.agent_utils import Toolkit

        # Mock stock data with uptrend
        dates = pd.date_range('2024-01-01', periods=35, freq='D')
        base_prices = np.linspace(100, 120, 35)  # Uptrend
        mock_df = pd.DataFrame({
            'close': base_prices + np.random.normal(0, 1, 35),
            'volume': np.random.randint(1000000, 10000000, 35)
        }, index=dates)
        mock_get_stock_data.return_value = mock_df

        result = Toolkit.get_relative_strength.invoke({
            "ticker": "AAPL",
            "benchmark": "XLK",
            "curr_date": "2024-01-15",
            "look_back_days": 30
        })

        assert "AAPL" in result
        assert "XLK" in result
        assert "Relative Strength" in result

    @patch('tradingagents.dataflows.alpaca_utils.AlpacaUtils.get_stock_data')
    def test_get_sector_rotation_tool(self, mock_get_stock_data):
        """Test the get_sector_rotation tool."""
        from tradingagents.agents.utils.agent_utils import Toolkit

        # Mock stock data
        dates = pd.date_range('2024-01-01', periods=35, freq='D')
        mock_df = pd.DataFrame({
            'close': np.random.uniform(50, 150, 35),
            'volume': np.random.randint(1000000, 10000000, 35)
        }, index=dates)
        mock_get_stock_data.return_value = mock_df

        result = Toolkit.get_sector_rotation.invoke({
            "curr_date": "2024-01-15",
            "look_back_days": 30
        })

        assert "Sector Rotation" in result
        assert "XLK" in result or "Technology" in result
        # Should mention risk-on or risk-off
        assert "RISK" in result.upper() or "risk" in result.lower()

    @patch('tradingagents.dataflows.sector_utils._get_yfinance_sector_info')
    def test_get_sector_peers_crypto_handling(self, mock_yf):
        """Test that sector tools handle crypto appropriately."""
        from tradingagents.dataflows.sector_utils import identify_sector

        # Mock yfinance returning empty for crypto
        mock_yf.return_value = {}

        # Crypto should return unknown sector
        result = identify_sector("BTC/USD")

        # For crypto, we should get unknown sector
        assert result["sector"] == "Unknown"
        assert result["sector_etf"] == "SPY"


class TestSectorToolsEdgeCases:
    """Tests for edge cases in sector tools."""

    @patch('tradingagents.dataflows.sector_utils._get_yfinance_sector_info')
    def test_empty_peers_list(self, mock_yf):
        """Test handling of stocks with no peers."""
        from tradingagents.dataflows.sector_utils import get_sector_peers

        mock_yf.return_value = {}

        sector, etf, peers = get_sector_peers("UNKNOWN_STOCK_XYZ")

        assert sector == "Unknown"
        assert etf == "SPY"
        assert peers == []

    @patch('tradingagents.dataflows.alpaca_utils.AlpacaUtils.get_stock_data')
    def test_insufficient_data_handling(self, mock_get_stock_data):
        """Test handling of insufficient historical data."""
        from tradingagents.agents.utils.agent_utils import Toolkit

        # Return empty DataFrame
        mock_get_stock_data.return_value = pd.DataFrame()

        result = Toolkit.get_relative_strength.invoke({
            "ticker": "AAPL",
            "benchmark": "XLK",
            "curr_date": "2024-01-15",
            "look_back_days": 30
        })

        # Should handle gracefully with error message
        assert "Error" in result or "Unable" in result

    @patch('tradingagents.dataflows.sector_utils._get_yfinance_sector_info')
    def test_ticker_in_multiple_sectors(self, mock_yf):
        """Test that stocks appearing in multiple sectors are handled."""
        from tradingagents.dataflows.sector_utils import identify_sector

        # AMZN is Consumer Cyclical per yfinance
        mock_yf.return_value = {"sector": "Consumer Cyclical", "industry": "Internet Retail"}

        result = identify_sector("AMZN")

        # Should pick a primary sector
        assert result["sector"] == "Consumer Cyclical"
        assert result["sector_etf"] in ["XLY", "IBUY"]  # Consumer Discretionary or Internet Retail
