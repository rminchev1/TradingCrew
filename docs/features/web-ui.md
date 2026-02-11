# Web UI

The TradingCrew Web UI is a browser-based trading workstation built with Dash and Bootstrap.

## Starting the Web UI

```bash
# Default (localhost:7860)
python run_webui_dash.py

# Custom port
python run_webui_dash.py --port 8080

# Debug mode (auto-reload on code changes)
python run_webui_dash.py --debug

# Public URL for sharing
python run_webui_dash.py --share
```

Or using the installed command:

```bash
tradingcrew-web
```

## Interface Layout

### Header Bar

- **Logo** - TradingCrew branding
- **Account Info** - Cash, portfolio value, P&L
- **Paper/Live Mode** - Current trading mode indicator

### Left Sidebar

- **Symbol Input** - Enter symbols for analysis
- **Analysis Options** - Configure research depth, trading mode
- **Watchlist** - Saved symbols for quick access
- **Portfolio** - Symbols queued for batch analysis

### Main Content Area

- **Chart Panel** - Interactive price charts
- **Reports Panel** - Analysis results in tabbed view
- **Portfolio Panel** - Positions and orders

### Bottom Section

- **Log Panel** - Real-time execution logs
- **Status Bar** - Current operation status

## Symbol Input

### Stock Symbols

Enter standard ticker symbols:
- `NVDA` - NVIDIA
- `AAPL` - Apple
- `TSLA` - Tesla

### Crypto Symbols

Always include the `/USD` suffix:
- `BTC/USD` - Bitcoin
- `ETH/USD` - Ethereum
- `SOL/USD` - Solana

### Multiple Symbols

Comma-separated for batch:
- `NVDA,AAPL,TSLA`
- `BTC/USD,ETH/USD`
- `NVDA,BTC/USD,AAPL` (mixed)

## Analysis Controls

### Research Depth

| Level | Debate Rounds | Use Case |
|-------|---------------|----------|
| Shallow | 1 | Quick scans |
| Medium | 2 | Regular analysis |
| Deep | 4 | Important decisions |

### Trading Mode

- **Long Only** - BUY, HOLD, or SELL recommendations
- **Allow Shorts** - Can also recommend SHORT positions

### Analyst Selection

Toggle individual analysts:
- Market Analyst (technical analysis)
- Options Analyst (options chain)
- Social Analyst (sentiment)
- News Analyst (headlines)
- Fundamentals Analyst (financials)
- Macro Analyst (economic data)

Disable analysts you don't need to save API costs.

### Auto Trade

When enabled, trades execute automatically after analysis completes based on the recommendation.

**Warning**: Use with caution, especially in Live mode.

## Chart Panel

### Features

- **Real-time Data** - Live prices from Alpaca
- **Candlestick Charts** - OHLC price data
- **Volume Bars** - Trading volume
- **Technical Indicators** - RSI, MACD, Bollinger Bands

### Controls

- **Zoom** - Scroll to zoom in/out
- **Pan** - Drag to move the chart
- **Reset** - Double-click to reset view

## Reports Panel

### Tabs

1. **Reports** - Individual analyst findings
2. **Debate** - Bull vs Bear discussion
3. **Risk** - Risk management assessment
4. **Decision** - Final recommendation
5. **Tool Calls** - Technical execution details

### Report History

Previous analyses are saved and accessible:
- Click on a past report to view
- Reports persist in SQLite database
- Access across sessions

## Portfolio Panel

### Positions Tab

Shows open positions with:
- Symbol and quantity
- Entry price
- Current price
- Unrealized P&L
- **Liquidate** button

### Orders Tab

Recent orders showing:
- Order type
- Side (buy/sell)
- Quantity
- Status
- Fill details

## Log Panel

### Features

- Real-time execution logs
- Agent activity tracking
- API call logging
- Error messages

### Controls

- **Toggle Streaming** - Pause/resume log updates
- **Collapse** - Minimize the log panel
- **Clear** - Remove log entries

## Settings Page

Access via the gear icon or Settings link.

### API Keys

Configure and test API connections:
- OpenAI
- Alpaca
- Finnhub
- FRED
- CoinDesk

### LLM Models

Select models for:
- Deep Think (complex reasoning)
- Quick Think (fast analysis)

### Analysis Defaults

- Max debate rounds
- Max risk rounds
- Parallel analysts toggle
- Online tools toggle
- Max recursion limit
- Max parallel tickers

### Scanner Settings

- Results count
- LLM sentiment toggle
- Options flow
- Cache TTL
- Dynamic universe

## Data Persistence

### Browser Storage (localStorage)

- Watchlist
- Run queue
- UI preferences
- System settings

### SQLite Database

- Analysis reports
- Historical decisions
- Tool call logs

Data persists across page refreshes and browser restarts.

## Troubleshooting

### Page Won't Load

```bash
# Check if port is in use
lsof -i :7860

# Try a different port
python run_webui_dash.py --port 8080
```

### Charts Not Loading

- Verify Alpaca API keys are set
- Check if market is open for real-time data
- Ensure symbol is valid

### Analysis Not Starting

- Check OpenAI API key is valid
- Verify account has API credits
- Review error messages in Log panel

See [Troubleshooting](../troubleshooting.md) for more solutions.
