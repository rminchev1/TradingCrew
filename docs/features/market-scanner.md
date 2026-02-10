# Market Scanner

The Market Scanner helps you discover trading opportunities by scanning for stocks meeting specific criteria.

## Requirements

The Market Scanner requires:
- **Alpaca API keys** configured
- Active market data subscription (included with Alpaca accounts)

Without API keys configured, the scanner will be disabled.

## Accessing the Scanner

In the Web UI:
1. Click the **Scanner** button in the sidebar
2. Or navigate to the Scanner tab

## Pre-built Scans

### Top Gainers

Stocks with the highest percentage gains today.

- **Criteria**: Highest % change
- **Filters**: Minimum volume, minimum price
- **Returns**: Top N gainers (configurable)

### Top Losers

Stocks with the biggest percentage losses today.

- **Criteria**: Lowest % change
- **Filters**: Minimum volume, minimum price
- **Returns**: Top N losers (configurable)

### Volume Spikes

Stocks with unusually high trading volume.

- **Criteria**: Volume > 2x average
- **Filters**: Minimum price
- **Returns**: Sorted by volume ratio

### News Movers

Stocks moving on news catalysts.

- **Criteria**: Significant price move + recent news
- **Data Sources**: Finnhub, Google News
- **Returns**: Stocks with news correlation

## Scanner Settings

Configure in Settings > Market Scanner:

| Setting | Description | Default |
|---------|-------------|---------|
| Results Count | Number of stocks returned | 20 |
| LLM Sentiment | Use GPT for news analysis | Off |
| Options Flow | Include options data | On |
| Cache TTL | How long to cache results | 300s |
| Dynamic Universe | Use top 200 liquid stocks | On |

### Results Count

Controls how many stocks appear in results (5-50).

### LLM Sentiment

When enabled, uses GPT to analyze news sentiment for each result.

**Note**: This incurs additional API costs.

### Options Flow

Includes put/call ratio and unusual options activity data.

### Cache TTL

Results are cached to reduce API calls. Adjust from 60-3600 seconds.

### Dynamic Universe

- **On**: Scans top 200 most liquid stocks (recommended)
- **Off**: Uses predefined stock list

## Using Scanner Results

### View Details

Click on any result to see:
- Price and change
- Volume data
- News headlines (if available)
- Technical indicators

### Add to Watchlist

Click the **+** button to add a stock to your watchlist.

### Add to Run Queue

Click **Queue** to add for batch analysis.

### Run Analysis

Click **Analyze** to immediately run full analysis.

## Scan Filters

### Minimum Volume

Filter out low-volume stocks:
- Ensures liquidity
- Reduces noise from penny stocks

### Minimum Price

Filter by minimum stock price:
- Avoids sub-penny stocks
- Focuses on tradeable securities

### Sector Filter

Limit results to specific sectors:
- Technology
- Healthcare
- Finance
- Energy
- etc.

## Best Practices

1. **Run scans at market open** - Highest activity and opportunities
2. **Combine with analysis** - Don't trade on scan results alone
3. **Use volume confirmation** - Verify moves have volume support
4. **Check news** - Understand why stocks are moving
5. **Enable caching** - Reduces API usage during frequent scans

## Example Workflow

1. Run "Top Gainers" scan at 9:45 AM
2. Add interesting stocks to watchlist
3. Run "Volume Spikes" for confirmation
4. Queue top candidates for full analysis
5. Execute Run Queue for detailed reports
6. Make trading decisions based on analysis

## Troubleshooting

### Scanner Disabled

Message: "Scanner requires Alpaca API configuration"

**Solution**: Configure Alpaca API keys in Settings.

### No Results

- Check if market is open
- Verify API connection
- Try different scan parameters

### Stale Data

- Check cache TTL setting
- Clear cache by changing a setting and saving
- Verify market data subscription

See [Troubleshooting](../troubleshooting.md) for more help.
