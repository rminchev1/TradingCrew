"""
TradingAgents - Multi-Agent LLM Financial Trading Framework

A sophisticated trading framework that uses multiple AI agents for market analysis,
research debates, risk management, and trade execution.
"""

__version__ = "0.1.0"
__author__ = "TradingAgents Team"

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

__all__ = [
    "TradingAgentsGraph",
    "DEFAULT_CONFIG",
    "__version__",
]
