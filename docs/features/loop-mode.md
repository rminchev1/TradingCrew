# Loop Mode

Loop Mode enables scheduled, recurring analysis of your symbols at regular intervals.

## Overview

When Loop Mode is enabled:
- Analysis runs automatically at set intervals
- Processes all symbols in your Run Queue
- Shows next run time in EST/EDT timezone
- Continues until manually stopped

## Enabling Loop Mode

### In the Web UI

1. Add symbols to the **Run Queue**
2. Set the **Loop Interval** (in minutes)
3. Toggle **Loop Mode** on
4. Analysis begins immediately, then repeats

### Configuration

| Setting | Range | Description |
|---------|-------|-------------|
| Loop Interval | 1-1440 min | Time between runs |

Common intervals:
- **5 minutes** - Active day trading
- **15 minutes** - Regular monitoring
- **60 minutes** - Hourly updates
- **240 minutes** - 4-hour check-ins
- **1440 minutes** - Daily analysis

## Status Display

When Loop Mode is active, the status bar shows:

```
Loop mode - Next run: 10:45 AM EST (15 min intervals)
```

This displays:
- Current mode indicator
- Next scheduled run time (in EST/EDT)
- Configured interval

## Combining with Market Hours

Use Loop Mode with Market Hours Mode for targeted analysis:

### Example: Regular Market Hours

```
Market Hours: 09:30,11:00,14:00,15:30
Loop Mode: Enabled
Interval: 60 minutes
```

Result: Analysis runs at those specific times only.

### Example: Pre-market Monitoring

```
Market Hours: 06:00,07:00,08:00
Loop Mode: Enabled
Interval: 60 minutes
```

Result: Hourly analysis during pre-market hours.

## Run Queue Integration

Loop Mode processes the **Run Queue**, not the Watchlist.

### Setting Up

1. Add symbols to Run Queue:
   - Click **+ Add to Queue** next to any symbol
   - Use comma-separated input
   - Add from Scanner results

2. Symbols remain in queue between iterations
3. Clear queue to reset

### Parallel Processing

The **Max Parallel Tickers** setting controls concurrency:
- Found in Settings > Analysis Defaults
- Range: 1-10 tickers simultaneously
- Higher = faster but more API usage

## Best Practices

### 1. Start Conservative

Begin with longer intervals:
- Less API cost
- Time to review results
- Adjust based on needs

### 2. Use with Market Hours

Avoid analyzing during closed markets:
- No new price data
- Wastes API calls
- Configure Market Hours appropriately

### 3. Monitor Costs

Each iteration uses OpenAI API:
- More symbols = more cost
- Deeper research = more cost
- Track usage in OpenAI dashboard

### 4. Review Results

Check reports between iterations:
- Note changing recommendations
- Track confidence trends
- Adjust positions accordingly

## Stopping Loop Mode

### Manual Stop

Click the Loop Mode toggle off in the UI.

### Automatic Stop

Loop Mode stops if:
- Run Queue is empty
- Critical error occurs
- Browser/tab is closed

## Use Cases

### Day Trading

```
Symbols: High-volume momentum stocks
Interval: 5-15 minutes
Hours: 09:30-16:00
```

Monitor fast-moving stocks for entry/exit signals.

### Swing Trading

```
Symbols: Position candidates
Interval: 60-240 minutes
Hours: Market hours only
```

Track developing setups throughout the day.

### Portfolio Monitoring

```
Symbols: Current holdings
Interval: 240-480 minutes
Hours: Any time
```

Regular check on portfolio positions.

### Crypto (24/7)

```
Symbols: BTC/USD, ETH/USD
Interval: 60 minutes
Hours: Not set (runs continuously)
```

Round-the-clock crypto monitoring.

## Troubleshooting

### Loop Not Starting

- Verify Run Queue has symbols
- Check that Loop Mode toggle is on
- Ensure no other analysis is running

### Missed Iterations

- Browser tab must remain open
- System sleep interrupts loop
- Network issues may delay runs

### Unexpected Stops

- Check Log Panel for errors
- Verify API keys are valid
- Ensure sufficient API credits

See [Troubleshooting](../troubleshooting.md) for more solutions.
