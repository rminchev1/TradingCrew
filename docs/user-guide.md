# User Guide

This guide covers all TradingCrew features in detail.

## Table of Contents

- [Web UI Overview](#web-ui-overview)
- [Running Analysis](#running-analysis)
- [Managing Your Watchlist](#managing-your-watchlist)
- [Using the Portfolio](#using-the-portfolio)
- [Understanding Reports](#understanding-reports)
- [Portfolio Management](#portfolio-management)
- [Scheduling Analysis](#scheduling-analysis)

## Web UI Overview

The TradingCrew web interface is a full-featured trading workstation with:

- **Symbol Input** - Enter symbols for analysis
- **Watchlist Panel** - Track symbols you're interested in
- **Portfolio** - Batch analyze multiple symbols
- **Chart Panel** - Interactive price charts with indicators
- **Reports Panel** - View analysis results and recommendations
- **Portfolio Panel** - Monitor positions and orders
- **Settings** - Configure API keys and preferences

### Starting the Web UI

```bash
python run_webui_dash.py
```

Options:
- `--port 8080` - Use a different port (default: 7860)
- `--debug` - Enable debug mode
- `--share` - Create a public URL

## Running Analysis

### Single Symbol

1. Enter a symbol in the **Symbol Input** field:
   - Stocks: `NVDA`, `AAPL`, `TSLA`
   - Crypto: `BTC/USD`, `ETH/USD` (always include `/USD`)

2. Click **Run Analysis** or press Enter

3. Monitor progress in the **Reports** panel

### Multiple Symbols

Use the Portfolio for batch analysis:

1. Add symbols to the Portfolio using the **+** button
2. Click **Start Analysis** to analyze all symbols
3. Results appear in the Reports panel as each completes

### Analysis Options

Before running, configure:

- **Research Depth**: Shallow (1 round), Medium (2), or Deep (4 debate rounds)
- **Trading Mode**: Long Only or Allow Shorts
- **Analysts**: Toggle which analysts to use (saves costs)
- **Auto Trade**: Execute trades automatically after analysis

## Managing Your Watchlist

The watchlist persists across sessions (stored in browser localStorage).

### Adding Symbols

- Type a symbol and click the **+** button
- Use the Market Scanner to find and add symbols
- Drag symbols from search results

### Watchlist Actions

Each watchlist item has quick actions:

- **Chart** - View the price chart
- **Analyze** - Run full analysis
- **Remove** - Delete from watchlist

### Reordering

Drag and drop symbols to reorder your watchlist.

## Using the Portfolio

The Portfolio allows batch analysis of multiple symbols that analysts are working with.

### Adding to Portfolio

- Click **+ Add to Portfolio** on any symbol
- Enter multiple comma-separated symbols
- Use scanner results

### Running Analysis

Click **Start Analysis** to analyze all symbols in the Portfolio.

The **Max Parallel Tickers** setting (in Settings) controls how many run concurrently.

### Queue Management

- Clear individual items with **×**
- **Clear All** removes everything
- Queue persists across page refreshes

## Understanding Reports

Analysis reports are organized in tabs:

### Reports Tab

Individual analyst reports with:
- Key findings
- Data sources used
- Confidence levels

### Debate Tab

The Bull vs Bear researcher debate:
- Each side's arguments
- Rebuttals and counter-points
- Research manager summary

### Risk Tab

Risk management discussion:
- Aggressive debator view
- Neutral debator view
- Conservative debator view
- Risk manager synthesis

### Decision Tab

Final recommendation:
- **BUY** / **HOLD** / **SELL**
- Confidence percentage
- Key reasoning
- Position sizing (if applicable)

### Tool Calls Tab

Technical details:
- API calls made
- Timing information
- Data retrieved

## Portfolio Management

### Viewing Positions

The Portfolio panel shows:
- Current open positions
- Entry price and current price
- Unrealized P&L
- Position size

### Viewing Orders

Recent orders show:
- Order type (market, limit)
- Status (filled, pending, canceled)
- Fill price and quantity

### Liquidating Positions

Click **Liquidate** to close a position immediately (market order).

### Account Balance

The account bar shows:
- Cash available
- Portfolio value
- Day's P&L
- Paper/Live mode indicator

## Scheduling Analysis

### Loop Mode

Run analysis on a recurring schedule:

1. Add symbols to the Portfolio
2. Set the **Loop Interval** (1-1440 minutes)
3. Enable **Loop Mode**

The UI shows when the next iteration will run (in EST/EDT).

### Market Hours Mode

Restrict analysis to specific times:

1. Enter times in **Market Hours** field (e.g., `10:30,14:15`)
2. Enable **Market Hours Mode**

Analysis only runs at these times during market hours.

### Combining Modes

Use both modes together:
- Loop Mode runs every N minutes
- Market Hours limits to specific times
- Perfect for regular market monitoring

## Keyboard Shortcuts

- **Enter** - Submit symbol for analysis
- **Escape** - Cancel current operation

## Tips

1. **Start with Paper Trading** - Always use `ALPACA_USE_PAPER=True` initially
2. **Use Shallow Research** for quick scans, Deep for important decisions
3. **Disable unnecessary analysts** to reduce API costs
4. **Check the Tool Calls tab** to understand what data was used
5. **Use the Market Scanner** to discover opportunities
