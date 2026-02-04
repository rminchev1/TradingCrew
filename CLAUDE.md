# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AlpacaTradingAgent is a multi-agent LLM-powered trading framework built on LangGraph that integrates with Alpaca API for real-time stock and crypto trading. It uses 5 specialized analyst agents (Market, Social Sentiment, News, Fundamentals, Macro) that work collaboratively through structured debates to make trading decisions.

## Commands

### Run Web UI
```bash
python run_webui_dash.py                    # Default localhost:7860
python run_webui_dash.py --port 8080        # Custom port
python run_webui_dash.py --debug            # Debug mode
```

### Run CLI
```bash
python -m cli.main              # Interactive mode
python -m cli.main NVDA         # Single stock
python -m cli.main "BTC/USD"    # Single crypto
python -m cli.main "NVDA,ETH/USD,AAPL"  # Multiple assets
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Docker
```bash
docker-compose up -d
```

## Architecture

### Multi-Agent System (LangGraph-based)
The framework uses a graph-based architecture where specialized agents collaborate:

1. **Analyst Team** (5 parallel agents in `tradingagents/agents/analysts/`):
   - Market Analyst → market conditions & trends
   - Social Sentiment Analyst → Reddit, Twitter sentiment
   - News Analyst → financial news via Finnhub
   - Fundamentals Analyst → company financials
   - Macro Analyst → Fed data via FRED API

2. **Research Team** (`tradingagents/agents/researchers/`):
   - Bull Researcher + Bear Researcher engage in structured debates
   - Research Manager orchestrates the debate

3. **Risk Management** (`tradingagents/agents/risk_mgmt/`):
   - Aggressive/Neutral/Safe debators evaluate risk
   - Risk Manager synthesizes perspectives

4. **Trader** (`tradingagents/agents/trader/`):
   - Executes trades via Alpaca API

### Key Orchestration Files
- `tradingagents/graph/trading_graph.py` - Main TradingAgentsGraph class, entry point for analysis
- `tradingagents/graph/setup.py` - Graph setup & parallel execution logic
- `tradingagents/graph/propagation.py` - Message propagation between agents
- `tradingagents/graph/conditional_logic.py` - Routing between agents

### Data Pipeline
- `tradingagents/dataflows/interface.py` - Unified data access layer (large file, ~60KB)
- `tradingagents/dataflows/alpaca_utils.py` - Alpaca API wrapper for trading
- Each data source has its own utility module (finnhub_utils.py, macro_utils.py, reddit_utils.py, etc.)

### Web UI (Dash-based)
- `webui/app_dash.py` - Main Dash application
- `webui/layout.py` - UI layout assembly
- `webui/components/` - Modular UI components (analysis, chart_panel, reports_panel, etc.)
- `webui/callbacks/` - Dash callbacks for reactivity
- `webui/utils/state.py` - Application state management

## Configuration

### Environment Variables (`.env`)
Required API keys:
- `ALPACA_API_KEY`, `ALPACA_SECRET_KEY` - Trading execution
- `ALPACA_USE_PAPER=True` - Paper trading (set False for live)
- `OPENAI_API_KEY` - LLM agents
- `FINNHUB_API_KEY` - Financial news/data
- `FRED_API_KEY` - Macroeconomic data
- `COINDESK_API_KEY` - Crypto news

### Default Config (`tradingagents/default_config.py`)
Key settings:
- `deep_think_llm`: "o3-mini" (reasoning model)
- `quick_think_llm`: "gpt-4o-mini" (fast model)
- `max_debate_rounds`: 4
- `max_risk_discuss_rounds`: 3
- `allow_shorts`: False (Investment mode: BUY/HOLD/SELL)
- `parallel_analysts`: True (run analysts concurrently)

## Code Patterns

### Symbol Formats
- Stocks: `NVDA`, `AAPL`
- Crypto: `BTC/USD`, `ETH/USD` (always include `/USD` suffix)
- Mixed: `"NVDA, ETH/USD, AAPL"`

### Python API Usage
```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

ta = TradingAgentsGraph(debug=True, config=DEFAULT_CONFIG.copy())
_, decision = ta.propagate("NVDA", "2024-05-10")
```

### State Classes
- `AgentState` - Main graph state
- `InvestDebateState` - Investment debate state
- `RiskDebateState` - Risk discussion state
- Located in `tradingagents/agents/utils/`

### LLM Notes
- Temperature parameter not supported by o3/gpt-5 models (handled in trading_graph.py)
- Use `gpt-4o-mini` or `gpt-5-mini` for cost-effective testing
