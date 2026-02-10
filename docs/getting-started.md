# Getting Started

Get TradingCrew up and running in 5 minutes.

## Prerequisites

- Python 3.10 or higher
- An OpenAI API key (for LLM agents)
- An Alpaca account (free, for market data and trading)

## Installation

### Option 1: Install from Source

```bash
# Clone the repository
git clone https://github.com/rminchev1/TradingCrew.git
cd TradingCrew

# Install dependencies
pip install -e .
```

### Option 2: Install from PyPI

```bash
pip install tradingcrew
```

### Option 3: Docker

```bash
docker-compose up -d
```

## Configuration

### 1. Create Environment File

Copy the sample environment file:

```bash
cp env.sample .env
```

### 2. Add Your API Keys

Edit `.env` with your API keys:

```bash
# Required
OPENAI_API_KEY=sk-...
ALPACA_API_KEY=PK...
ALPACA_SECRET_KEY=...
ALPACA_USE_PAPER=True

# Optional (enhanced features)
FINNHUB_API_KEY=...
FRED_API_KEY=...
COINDESK_API_KEY=...
```

See [API Keys Configuration](configuration/api-keys.md) for details on obtaining each key.

## Your First Analysis

### Using the Web UI (Recommended)

```bash
# Start the web interface
python run_webui_dash.py
```

Open your browser to `http://localhost:7860` and:

1. Enter a symbol (e.g., `NVDA`) in the Symbol Input field
2. Click **Run Analysis**
3. Watch the agents work in the Reports panel
4. View the final recommendation in the Decision tab

### Using the CLI

```bash
# Interactive mode
python -m cli.main

# Analyze a single stock
python -m cli.main NVDA

# Analyze crypto
python -m cli.main "BTC/USD"

# Analyze multiple assets
python -m cli.main "NVDA,AAPL,ETH/USD"
```

### Using the Python API

```python
from tradingagents import TradingAgentsGraph, DEFAULT_CONFIG

# Initialize
ta = TradingAgentsGraph(debug=True, config=DEFAULT_CONFIG.copy())

# Run analysis
_, decision = ta.propagate("NVDA", "2024-05-10")

print(decision)
```

## Next Steps

- [User Guide](user-guide.md) - Learn all the features
- [Web UI Guide](features/web-ui.md) - Master the web interface
- [Settings](configuration/settings.md) - Customize your analysis
