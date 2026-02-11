# API Keys Configuration

TradingCrew requires several API keys for full functionality.

## Required APIs

### OpenAI API

**Purpose**: Powers all LLM agents for analysis and decision-making.

**Cost**: Pay-per-use (usage-based)

**Setup**:
1. Visit [platform.openai.com](https://platform.openai.com)
2. Create an account or sign in
3. Navigate to API Keys section
4. Click "Create new secret key"
5. Copy the key (starts with `sk-`)

```bash
OPENAI_API_KEY=sk-...
```

**Tips**:
- Set usage limits to avoid surprise bills
- Monitor usage in OpenAI dashboard
- Use `gpt-4o-mini` for cost savings

### Alpaca API

**Purpose**: Market data, trading execution, and portfolio management.

**Cost**: Free (paper trading and basic data)

**Setup**:
1. Visit [alpaca.markets](https://alpaca.markets)
2. Create a free account
3. Go to Paper Trading in dashboard
4. Generate API keys

```bash
ALPACA_API_KEY=PKXXXXXXXXXXXXXXXX
ALPACA_SECRET_KEY=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
ALPACA_USE_PAPER=True
```

**Paper vs Live**:
- Paper keys: For simulated trading (recommended)
- Live keys: For real money trading (use with caution)

## Optional APIs

These enhance functionality but aren't required:

### Finnhub API

**Purpose**: Financial news, company data, and market metrics.

**Cost**: Free tier available (60 calls/minute)

**Setup**:
1. Visit [finnhub.io](https://finnhub.io)
2. Sign up for free account
3. Copy API key from dashboard

```bash
FINNHUB_API_KEY=...
```

**Used by**: News Analyst

### FRED API

**Purpose**: Federal Reserve economic data (interest rates, GDP, inflation).

**Cost**: Free

**Setup**:
1. Visit [fred.stlouisfed.org](https://fred.stlouisfed.org)
2. Create an account
3. Request API key

```bash
FRED_API_KEY=...
```

**Used by**: Macro Analyst

### CoinDesk API

**Purpose**: Cryptocurrency news and data.

**Cost**: Free tier available

**Setup**:
1. Visit [cryptocompare.com](https://www.cryptocompare.com)
2. Create an account
3. Generate API key

```bash
COINDESK_API_KEY=...
```

**Used by**: News Analyst (crypto)

### Reddit API

**Purpose**: Live social sentiment from Reddit (r/wallstreetbets, r/stocks, r/cryptocurrency, etc.)

**Cost**: Free

**Setup**:
1. Visit [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
2. Sign in to your Reddit account
3. Scroll down and click "create another app..."
4. Fill in the form:
   - **name**: TradingCrew (or any name)
   - **type**: Select "script"
   - **description**: Trading sentiment analysis
   - **redirect uri**: http://localhost:8080
5. Click "create app"
6. Copy the client ID (shown under the app name) and client secret

```bash
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=TradingCrew/1.0
```

**Used by**: Social Media Analyst

**Subreddits searched**:
- Stocks: wallstreetbets, stocks, investing, stockmarket, options
- Crypto: cryptocurrency, bitcoin, ethereum, CryptoMarkets, altcoin

**Note**: If not configured, the Social Media Analyst will fall back to cached Reddit data (if available) or indicate no data.

## Configuration Methods

### Method 1: Environment File (Recommended)

Create a `.env` file in the project root:

```bash
# Required
OPENAI_API_KEY=sk-...
ALPACA_API_KEY=PK...
ALPACA_SECRET_KEY=...
ALPACA_USE_PAPER=True

# Optional
FINNHUB_API_KEY=...
FRED_API_KEY=...
COINDESK_API_KEY=...

# Reddit API (for live social sentiment)
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=TradingCrew/1.0
```

### Method 2: System Environment

Set environment variables directly:

```bash
export OPENAI_API_KEY="sk-..."
export ALPACA_API_KEY="PK..."
export ALPACA_SECRET_KEY="..."
```

### Method 3: Web UI Settings

1. Open Settings page
2. Enter keys in API Keys section
3. Click "Test" to verify
4. Click "Save Settings"

**Note**: Keys entered in UI are stored in browser localStorage.

## Testing Connections

### In Web UI

Each API has a "Test" button that:
- Validates the key format
- Makes a test API call
- Shows success/failure status

### In Terminal

```bash
# Test OpenAI
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Test Alpaca
curl https://paper-api.alpaca.markets/v2/account \
  -H "APCA-API-KEY-ID: $ALPACA_API_KEY" \
  -H "APCA-API-SECRET-KEY: $ALPACA_SECRET_KEY"
```

## Security Best Practices

### DO

- Keep keys in `.env` file (gitignored)
- Use paper trading keys for testing
- Set spending limits where available
- Rotate keys periodically
- Use separate keys for dev/prod

### DON'T

- Commit keys to version control
- Share keys publicly
- Use live trading keys unless necessary
- Store keys in plain text files outside `.env`

## Status Indicators

In the Settings page, each API shows:

| Icon | Status |
|------|--------|
| ✅ Green check | Key valid and working |
| ⚠️ Yellow warning | Key not set |
| ❌ Red X | Key invalid or API error |

## Troubleshooting

### "API Key Invalid"

- Check for extra spaces or quotes
- Verify key hasn't expired
- Ensure correct key for paper/live mode

### "Rate Limited"

- Reduce request frequency
- Upgrade API tier if needed
- Wait and retry

### "Connection Failed"

- Check internet connection
- Verify API service is up
- Check firewall settings

See [Troubleshooting](../troubleshooting.md) for more help.
