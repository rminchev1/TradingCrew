# TradingCrew Documentation

Welcome to the TradingCrew documentation. TradingCrew is a multi-agent LLM-powered trading framework that uses 6 specialized analyst agents working collaboratively to make trading decisions.

## Quick Links

- [Getting Started](getting-started.md) - Get up and running in 5 minutes
- [User Guide](user-guide.md) - Complete walkthrough of all features
- [Changelog](CHANGELOG.md) - Version history and release notes

## Features

- [Web UI](features/web-ui.md) - Browser-based trading workstation
- [CLI](features/cli.md) - Command-line interface for scripts and automation
- [Market Scanner](features/market-scanner.md) - Find trading opportunities
- [Loop Mode](features/loop-mode.md) - Scheduled recurring analysis
- [Trading](features/trading.md) - Paper and live trading with Alpaca

## Configuration

- [API Keys](configuration/api-keys.md) - Set up required API credentials
- [Settings](configuration/settings.md) - Configure analysis and trading options

## Support

- [Troubleshooting](troubleshooting.md) - Common issues and solutions
- [GitHub Issues](https://github.com/rminchev1/TradingCrew/issues) - Report bugs or request features

## How It Works

TradingCrew uses a structured multi-agent workflow:

```
Analyst Team (6 agents in parallel)
        ↓
Research Team (Bull vs Bear debate)
        ↓
Trading Team (trade planning)
        ↓
Risk Management (3-way risk debate)
        ↓
Portfolio Manager (final BUY/HOLD/SELL decision)
```

### The Analyst Team

| Agent | Focus Area |
|-------|-----------|
| Market Analyst | Technical indicators (RSI, MACD, Bollinger Bands) |
| Options Analyst | Options chain, put/call ratios, max pain |
| Social Sentiment | Reddit and Twitter sentiment analysis |
| News Analyst | Financial news via Finnhub API |
| Fundamentals Analyst | Earnings, balance sheets, SEC filings |
| Macro Analyst | FRED API economic indicators |

### Supported Assets

- **Stocks**: Full analysis with options, fundamentals, and technicals
- **Crypto**: BTC/USD, ETH/USD with DeFi and CoinDesk data
- **Mixed**: Analyze multiple asset types in a single session
