# AlpacaTradingAgent: Multi-Agent LLM Trading Framework

> **AlpacaTradingAgent** - A sophisticated multi-agent AI trading framework built on LangGraph, designed for Alpaca users who want to leverage AI agents for automated market analysis and trading.
>
> This project extends the original [TradingAgents](https://github.com/TauricResearch/TradingAgents) framework with real-time Alpaca integration, crypto support, options analysis, and a production-ready web interface.
>
> **Disclaimer**: This project is for educational and research purposes only. It is not financial, investment, or trading advice. Trading involves risk. Users should conduct their own due diligence.

<div align="center">

[![CI](https://github.com/rminchev1/AlpacaTradingAgent/actions/workflows/ci.yml/badge.svg)](https://github.com/rminchev1/AlpacaTradingAgent/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)

[Features](#features) | [Installation](#installation) | [Quick Start](#quick-start) | [Web UI](#web-interface) | [CLI](#cli-usage) | [API](#python-api) | [Contributing](#contributing)

</div>

---

## Features

### 🤖 Multi-Agent Analysis System (6 Specialized Agents)

| Agent | Role |
|-------|------|
| **Market Analyst** | Technical analysis, price trends, indicators (RSI, MACD, Bollinger Bands) |
| **Options Analyst** | Options chain analysis, put/call ratios, max pain, institutional positioning |
| **Social Sentiment Analyst** | Reddit, Twitter sentiment analysis, social momentum |
| **News Analyst** | Live Finnhub news, Google News, market-moving events |
| **Fundamentals Analyst** | Earnings, balance sheets, SEC filings, insider transactions |
| **Macro Analyst** | Fed data (FRED API), yield curves, economic indicators |

### 📈 Dual Asset Support
- **Stocks**: Full analysis with options data, fundamentals, and technicals
- **Crypto**: BTC/USD, ETH/USD with DeFi Llama data and crypto-specific news
- **Mixed Portfolios**: Analyze `NVDA, ETH/USD, AAPL` in a single session

### 🌐 Production-Ready Web Interface
- **Watchlist Management**: Add symbols, drag-and-drop reorder, one-click analysis
- **Run Queue**: Queue multiple symbols for batch analysis
- **Market Scanner**: Pre-built scanners for gainers, losers, volume spikes, news movers
- **Interactive Charts**: Real-time Alpaca data with technical overlays
- **Live Reports**: Tabbed analyst reports, debate transcripts, tool call logs
- **Portfolio View**: Current positions, recent orders, P&L tracking

### ⚡ Automated Trading
- **Paper & Live Trading**: Test safely before going live
- **Auto-Execution**: Optional automatic trade execution
- **Scheduled Analysis**: Run analysis every N hours during market hours
- **Risk Management**: Position sizing, margin controls, stop-loss support

### 🔧 Developer Experience
- **Python Package**: Install via `pip install .`
- **CLI Interface**: Interactive and batch modes
- **CI/CD**: GitHub Actions for testing and releases
- **Extensible**: Add custom analysts, data sources, or strategies

---

## Installation

### Option 1: Install as Package (Recommended)

```bash
# Clone the repository
git clone https://github.com/rminchev1/AlpacaTradingAgent.git
cd AlpacaTradingAgent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install -e .

# Or with development dependencies
pip install -e .[dev]
```

### Option 2: Install from Requirements

```bash
git clone https://github.com/rminchev1/AlpacaTradingAgent.git
cd AlpacaTradingAgent

# Create virtual environment
conda create -n tradingagents python=3.11
conda activate tradingagents

# Install dependencies
pip install -r requirements.txt
```

### Configure API Keys

1. Copy the sample environment file:
   ```bash
   cp env.sample .env
   ```

2. Edit `.env` with your API keys:

| API | Purpose | Required | Get Key |
|-----|---------|----------|---------|
| **ALPACA_API_KEY** | Trading execution | Yes | [Alpaca Markets](https://app.alpaca.markets/signup) |
| **ALPACA_SECRET_KEY** | Trading execution | Yes | [Alpaca Markets](https://app.alpaca.markets/signup) |
| **OPENAI_API_KEY** | LLM agents | Yes | [OpenAI Platform](https://platform.openai.com/api-keys) |
| **FINNHUB_API_KEY** | Stock news & data | Yes | [Finnhub](https://finnhub.io/register) |
| **FRED_API_KEY** | Macro analysis | Yes | [FRED](https://fred.stlouisfed.org/docs/api/api_key.html) |
| **COINDESK_API_KEY** | Crypto news | For crypto | [CryptoCompare](https://www.cryptocompare.com/cryptopian/api-keys) |

3. Set trading mode:
   ```bash
   ALPACA_USE_PAPER=True   # Paper trading (recommended for testing)
   ALPACA_USE_PAPER=False  # Live trading with real money
   ```

---

## Quick Start

### Web Interface (Recommended)

```bash
# If installed as package
tradingagents-web

# Or run directly
python run_webui_dash.py --port 7860
```

Open http://localhost:7860 in your browser.

### CLI

```bash
# If installed as package
tradingagents

# Or run directly
python -m cli.main

# Analyze specific symbols
python -m cli.main NVDA
python -m cli.main "BTC/USD"
python -m cli.main "NVDA,ETH/USD,AAPL"
```

### Python API

```python
from tradingagents import TradingAgentsGraph, DEFAULT_CONFIG

# Initialize
ta = TradingAgentsGraph(debug=True, config=DEFAULT_CONFIG.copy())

# Analyze a stock
_, decision = ta.propagate("NVDA", "2024-05-10")
print(decision)

# Analyze crypto
_, decision = ta.propagate("ETH/USD", "2024-05-10")
print(decision)
```

---

## Web Interface

The Dash-based web UI provides a complete trading workstation:

### Dashboard Features

**Watchlist & Run Queue**
- Add symbols to watchlist for monitoring
- Promote to Run Queue for batch analysis
- Drag-and-drop reordering
- Quick-action buttons: Chart, Analyze, Queue

**Market Scanner**
- Pre-built scans: Top Gainers, Top Losers, Volume Spikes
- News-based movers detection
- One-click add to watchlist or analysis queue

**Analysis Controls**
- Select which analysts to run (Market, Options, Social, News, Fundamentals, Macro)
- Configure LLM models (GPT-4o, GPT-4o-mini, o3-mini)
- Set debate rounds and risk parameters
- Schedule automated recurring analysis

**Reports & Visualization**
- Tabbed reports for each analyst
- Bull vs Bear debate transcripts
- Risk assessment summaries
- Final trading recommendations
- Tool call logs with timing data

**Portfolio Management**
- View current Alpaca positions
- Recent order history
- One-click position liquidation
- Real-time P&L tracking

### Screenshots

<p align="center">
  <img src="assets/config_and_chart.png" style="width: 100%; height: auto;">
</p>

<p align="center">
  <img src="assets/reports.png" style="width: 100%; height: auto;">
</p>

---

## CLI Usage

The CLI supports interactive and batch modes:

```bash
# Interactive mode - select options via prompts
tradingagents

# Single symbol
tradingagents NVDA

# Multiple symbols
tradingagents "NVDA,AAPL,TSLA"

# Crypto
tradingagents "BTC/USD"

# Mixed assets
tradingagents "NVDA,ETH/USD,AAPL"
```

---

## Python API

### Basic Usage

```python
from tradingagents import TradingAgentsGraph, DEFAULT_CONFIG

ta = TradingAgentsGraph(debug=True, config=DEFAULT_CONFIG.copy())
_, decision = ta.propagate("NVDA", "2024-05-10")
```

### Custom Configuration

```python
from tradingagents import TradingAgentsGraph, DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config.update({
    "deep_think_llm": "gpt-4o",        # Reasoning model
    "quick_think_llm": "gpt-4o-mini",  # Fast model
    "max_debate_rounds": 3,             # Bull/Bear debate rounds
    "max_risk_discuss_rounds": 2,       # Risk assessment rounds
    "online_tools": True,               # Use live data
    "parallel_analysts": True,          # Run analysts concurrently
})

ta = TradingAgentsGraph(debug=True, config=config)
```

### Batch Analysis

```python
symbols = ["NVDA", "AAPL", "TSLA", "ETH/USD"]
results = {}

for symbol in symbols:
    _, decision = ta.propagate(symbol, "2024-05-10")
    results[symbol] = decision
    print(f"{symbol}: {decision['action']} - {decision['reasoning'][:100]}...")
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     ANALYST TEAM (6 Agents)                     │
├─────────────────────────────────────────────────────────────────┤
│  Market    Options    Social    News    Fundamentals    Macro   │
│  Analyst   Analyst    Analyst   Analyst   Analyst      Analyst  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     RESEARCHER TEAM                              │
├─────────────────────────────────────────────────────────────────┤
│        Bull Researcher  ◄──► Bear Researcher                    │
│              (Structured Debate - N Rounds)                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     RISK MANAGEMENT                              │
├─────────────────────────────────────────────────────────────────┤
│    Aggressive ◄──► Neutral ◄──► Conservative                    │
│              (Risk Assessment Debate)                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     TRADER AGENT                                 │
├─────────────────────────────────────────────────────────────────┤
│     Final Decision: BUY / HOLD / SELL                           │
│     → Alpaca API Execution (Paper or Live)                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
AlpacaTradingAgent/
├── tradingagents/           # Core trading framework
│   ├── agents/              # AI agents (analysts, researchers, trader)
│   ├── dataflows/           # Data interfaces (Alpaca, Finnhub, FRED, etc.)
│   ├── graph/               # LangGraph workflow orchestration
│   └── scanner/             # Market scanning utilities
├── webui/                   # Dash web interface
│   ├── components/          # UI components
│   ├── callbacks/           # Dash callbacks
│   └── assets/              # CSS, JS assets
├── cli/                     # Command-line interface
├── tests/                   # Unit tests
├── pyproject.toml           # Package configuration
└── requirements.txt         # Dependencies
```

---

## Development

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/dataflows/test_finnhub_news_online.py -v
```

### Building the Package

```bash
# Install build tools
pip install build

# Build source distribution and wheel
python -m build

# Output in dist/
```

### Creating a Release

```bash
# Tag a version
git tag v0.1.0
git push origin v0.1.0

# GitHub Actions will automatically:
# 1. Run tests
# 2. Build package
# 3. Create GitHub Release with artifacts
```

---

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Acknowledgments

This project builds upon the original [TradingAgents](https://github.com/TauricResearch/TradingAgents) framework by Tauric Research. We extend our gratitude to the original authors for their pioneering work in multi-agent financial trading systems.

## Citation

```bibtex
@misc{xiao2025tradingagentsmultiagentsllmfinancial,
      title={TradingAgents: Multi-Agents LLM Financial Trading Framework},
      author={Yijia Xiao and Edward Sun and Di Luo and Wei Wang},
      year={2025},
      eprint={2412.20138},
      archivePrefix={arXiv},
      primaryClass={q-fin.TR},
      url={https://arxiv.org/abs/2412.20138},
}
```

---

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**[⬆ Back to Top](#alpacatradingagent-multi-agent-llm-trading-framework)**

</div>
