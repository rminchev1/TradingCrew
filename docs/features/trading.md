# Trading

TradingCrew integrates with Alpaca for paper and live trading.

## Trading Modes

### Paper Trading (Default)

Paper trading uses simulated money:
- No real money at risk
- Real market data
- Practice strategies safely
- Recommended for beginners

```bash
# In .env
ALPACA_USE_PAPER=True
```

### Live Trading

Live trading uses real money:
- Real orders execute
- Real profits and losses
- Use with caution

```bash
# In .env
ALPACA_USE_PAPER=False
```

**Warning**: Only use Live mode when you fully understand the risks.

## Account Setup

### 1. Create Alpaca Account

1. Visit [alpaca.markets](https://alpaca.markets)
2. Sign up for a free account
3. Complete verification (if required for live trading)

### 2. Get API Keys

1. Log in to Alpaca dashboard
2. Navigate to API Keys section
3. Generate new API key pair
4. Copy both the Key and Secret

### 3. Configure TradingCrew

Add to your `.env` file:

```bash
ALPACA_API_KEY=PKXXXXXXXXXXXXXXXX
ALPACA_SECRET_KEY=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
ALPACA_USE_PAPER=True
```

## Trading Features

### Manual Trading

Use the Portfolio panel to:
- View current positions
- See open orders
- Liquidate positions

### Auto Trading

When enabled:
1. Analysis completes with recommendation
2. Trade executes automatically
3. Position sizing based on configuration

Enable in the Analysis Options panel.

**Caution**: Auto trading executes without confirmation.

### Position Management

From the Portfolio panel:
- View all open positions
- See entry prices and P&L
- Click **Liquidate** to close positions

## Order Types

TradingCrew uses market orders for simplicity:
- Immediate execution
- Fills at current market price
- Suitable for liquid stocks

Future versions may support:
- Limit orders
- Stop orders
- Bracket orders

## Position Sizing

The system calculates position sizes based on:
- Account balance
- Risk parameters
- Recommendation confidence

Default sizing:
- Conservative: 2% of portfolio
- Moderate: 5% of portfolio
- Aggressive: 10% of portfolio

## Supported Assets

### Stocks

All US-listed stocks available on Alpaca:
- NYSE
- NASDAQ
- AMEX

### Crypto

Major cryptocurrencies:
- BTC/USD
- ETH/USD
- Other Alpaca-supported pairs

### Fractional Shares

Alpaca supports fractional shares:
- Trade any dollar amount
- No need for full shares
- Enabled by default

## Safety Features

### Paper Mode Default

TradingCrew defaults to paper trading. You must explicitly enable live mode.

### Mode Indicator

The UI clearly shows current mode:
- 🧪 PAPER MODE - Simulated trading
- 🔴 LIVE MODE - Real money

### Confirmation Dialogs

Dangerous actions require confirmation:
- Switching to Live mode
- Liquidating all positions
- Large orders

## Portfolio Panel

### Positions Tab

| Column | Description |
|--------|-------------|
| Symbol | Stock/crypto ticker |
| Qty | Number of shares |
| Entry | Average entry price |
| Current | Current market price |
| P&L | Unrealized profit/loss |
| Actions | Liquidate button |

### Orders Tab

| Column | Description |
|--------|-------------|
| Symbol | Stock/crypto ticker |
| Side | Buy or Sell |
| Type | Market, Limit, etc. |
| Qty | Order quantity |
| Status | Pending, Filled, Canceled |
| Time | Order timestamp |

### Account Bar

Shows at a glance:
- Cash: Available buying power
- Portfolio: Total position value
- P&L: Day's profit/loss
- Mode: Paper or Live indicator

## Trading Hours

### Stocks

- Pre-market: 4:00 AM - 9:30 AM ET
- Regular: 9:30 AM - 4:00 PM ET
- After-hours: 4:00 PM - 8:00 PM ET

Extended hours trading may have:
- Lower liquidity
- Wider spreads
- Higher volatility

### Crypto

- 24/7 trading
- No market hours restrictions
- Prices update continuously

## Best Practices

1. **Start with Paper Trading**
   - Test strategies risk-free
   - Understand the system
   - Build confidence

2. **Use Small Positions**
   - Limit risk per trade
   - Scale up gradually
   - Never risk more than you can lose

3. **Monitor Positions**
   - Check portfolio regularly
   - Review performance
   - Adjust strategies

4. **Understand Recommendations**
   - Read full analysis
   - Don't blindly follow
   - Use as one input

5. **Set Limits**
   - Maximum position size
   - Daily loss limits
   - Take profits

## Troubleshooting

### Orders Not Executing

- Check market hours
- Verify account has funds
- Ensure API keys are valid

### Position Not Showing

- Allow time for order fill
- Refresh the Portfolio panel
- Check Orders tab for status

### Connection Issues

- Verify API keys
- Check Alpaca status page
- Review network connectivity

See [Troubleshooting](../troubleshooting.md) for more help.
