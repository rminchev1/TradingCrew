# Settings Configuration

TradingCrew offers extensive configuration options for customizing analysis and trading behavior.

## Accessing Settings

### Web UI

Click the **Settings** icon or navigate to the Settings page.

### Configuration File

Edit `tradingagents/default_config.py` for code-level defaults.

### Environment Variables

Set in `.env` file for API keys and mode selection.

## LLM Models

### Deep Think Model

Used for complex reasoning tasks:
- Research debates
- Risk assessment
- Final decisions

| Model | Speed | Quality | Cost |
|-------|-------|---------|------|
| gpt-5.2-pro | Slow | Best | $$$$$ |
| gpt-5.2 | Slow | Excellent | $$$$ |
| o4-mini | Medium | Very Good | $$ |
| o3-mini | Fast | Good | $ |
| gpt-4o | Medium | Very Good | $$ |
| gpt-4o-mini | Fast | Good | $ |

**Recommendation**: `o4-mini` balances quality and cost.

### Quick Think Model

Used for fast analysis tasks:
- Data processing
- Initial analysis
- Tool coordination

| Model | Speed | Cost |
|-------|-------|------|
| gpt-5.2-instant | Fastest | $$$ |
| gpt-4.1-nano | Very Fast | $ |
| gpt-4.1-mini | Fast | $$ |
| gpt-4o-mini | Fast | $$ |

**Recommendation**: `gpt-4.1-nano` for cost efficiency.

## Analysis Settings

### Max Debate Rounds

Controls depth of Bull vs Bear debate.

| Value | Description | Use Case |
|-------|-------------|----------|
| 1 | Single exchange | Quick scans |
| 2 | Two rounds | Regular analysis |
| 4 | Deep debate | Important decisions |

**Range**: 1-10

### Max Risk Rounds

Controls depth of risk management discussion.

| Value | Description |
|-------|-------------|
| 1 | Quick assessment |
| 3 | Standard (default) |
| 5+ | Thorough review |

**Range**: 1-10

### Parallel Analysts

When enabled, all 6 analysts run concurrently.

| Setting | Behavior |
|---------|----------|
| On | Faster, higher API concurrency |
| Off | Sequential, easier to debug |

**Recommendation**: On for speed, Off for debugging.

### Online Tools

Controls whether agents can fetch external data.

| Setting | Behavior |
|---------|----------|
| On | Full analysis with live data |
| Off | Uses cached/historical data only |

### Max Recursion Limit

Prevents infinite loops in graph execution.

**Range**: 50-500
**Default**: 200

Increase if you see "recursion limit" errors with complex analyses.

### Max Parallel Tickers

Controls how many symbols analyze simultaneously.

**Range**: 1-10
**Default**: 3

Higher values:
- Faster batch processing
- More API concurrency
- Higher memory usage

## Scanner Settings

### Results Count

Number of stocks returned by scanner.

**Range**: 5-50
**Default**: 20

### LLM Sentiment

Uses GPT to analyze news sentiment.

| Setting | Behavior |
|---------|----------|
| On | Better sentiment accuracy, costs money |
| Off | Basic keyword sentiment, free |

### Options Flow

Includes options chain analysis.

| Setting | Behavior |
|---------|----------|
| On | Put/call ratios, unusual activity |
| Off | Stock data only |

### Cache TTL

How long scanner results are cached (seconds).

**Range**: 60-3600
**Default**: 300 (5 minutes)

### Dynamic Universe

Stock universe for scanning.

| Setting | Behavior |
|---------|----------|
| On | Top 200 most liquid stocks |
| Off | Predefined stock list |

## Trading Settings

### Trading Mode

Configure in `.env`:

```bash
# Paper trading (simulated)
ALPACA_USE_PAPER=True

# Live trading (real money)
ALPACA_USE_PAPER=False
```

### Allow Shorts

Configure in analysis options:

| Setting | Recommendations |
|---------|-----------------|
| Off | BUY, HOLD, SELL |
| On | BUY, HOLD, SELL, SHORT |

## Persistence

### Browser Storage

Settings saved in browser localStorage:
- Persist across sessions
- Browser-specific
- Cleared if browser data cleared

### Export/Import

Use the Export/Import buttons to:
- Backup your settings
- Transfer between browsers
- Share configurations

**Export format**: JSON file

## Default Configuration

Located in `tradingagents/default_config.py`:

```python
DEFAULT_CONFIG = {
    # LLM Settings
    "deep_think_llm": "o3-mini",
    "quick_think_llm": "gpt-4o-mini",

    # Analysis Settings
    "max_debate_rounds": 4,
    "max_risk_discuss_rounds": 3,
    "parallel_analysts": True,

    # Trading Settings
    "allow_shorts": False,
}
```

## Settings Workflow

### 1. Initial Setup

1. Open Settings page
2. Configure API keys
3. Test each connection
4. Save settings

### 2. Customize Analysis

1. Choose LLM models
2. Set debate rounds
3. Configure parallelization
4. Save settings

### 3. Optimize for Cost

- Use `gpt-4o-mini` for quick think
- Use `o3-mini` for deep think
- Reduce debate rounds
- Disable unused analysts

### 4. Optimize for Quality

- Use `gpt-5.2-pro` for deep think
- Increase debate rounds to 4+
- Enable all analysts
- Enable LLM sentiment

## Reset to Defaults

Click **Reset to Defaults** to restore all settings to their original values.

**Warning**: This clears all customizations including API keys entered in UI.
