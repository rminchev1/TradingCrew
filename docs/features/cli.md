# Command Line Interface (CLI)

TradingCrew includes a powerful CLI for running analysis from the terminal.

## Installation

The CLI is available after installing TradingCrew:

```bash
pip install -e .
```

## Basic Usage

### Interactive Mode

```bash
tradingcrew
# or
python -m cli.main
```

This launches an interactive session where you can:
- Enter symbols one at a time
- Configure analysis options
- View results in the terminal

### Single Symbol

```bash
# Stock
tradingcrew NVDA

# Crypto (include /USD)
tradingcrew "BTC/USD"
```

### Multiple Symbols

```bash
# Comma-separated
tradingcrew "NVDA,AAPL,TSLA"

# Mixed assets
tradingcrew "NVDA,BTC/USD,AAPL"
```

**Note**: Wrap in quotes when using special characters like `/` or `,`.

## Command Syntax

```bash
tradingcrew [OPTIONS] [SYMBOLS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| SYMBOLS | Ticker symbol(s) to analyze |

### Options

| Option | Description |
|--------|-------------|
| `--debug` | Enable debug output |
| `--config FILE` | Use custom config file |
| `--help` | Show help message |

## Output Format

The CLI displays:

1. **Progress Indicators** - Shows which agent is working
2. **Analyst Reports** - Key findings from each analyst
3. **Debate Summary** - Bull vs Bear arguments
4. **Risk Assessment** - Risk team evaluation
5. **Final Decision** - BUY/HOLD/SELL recommendation

Example output:

```
Analyzing NVDA...

[Market Analyst] Bullish momentum, RSI at 65
[Options Analyst] Put/Call ratio: 0.8 (bullish)
[News Analyst] Positive sentiment on earnings
[Fundamentals] Strong revenue growth YoY
[Macro] Favorable rate environment

Bull Researcher: Strong technical setup...
Bear Researcher: Valuation concerns at current levels...

Risk Assessment: Medium risk, position sizing 5%

DECISION: BUY
Confidence: 78%
Reasoning: Strong technicals with positive catalyst
```

## Configuration

### Environment Variables

Set in `.env` file:

```bash
OPENAI_API_KEY=sk-...
ALPACA_API_KEY=PK...
ALPACA_SECRET_KEY=...
ALPACA_USE_PAPER=True
```

### Default Config

Located in `tradingagents/default_config.py`:

```python
DEFAULT_CONFIG = {
    "deep_think_llm": "o3-mini",
    "quick_think_llm": "gpt-4o-mini",
    "max_debate_rounds": 4,
    "max_risk_discuss_rounds": 3,
    "allow_shorts": False,
    "parallel_analysts": True,
}
```

## Scripting Examples

### Batch Analysis Script

```bash
#!/bin/bash
# analyze_portfolio.sh

symbols="NVDA AAPL MSFT GOOGL AMZN"

for symbol in $symbols; do
    echo "Analyzing $symbol..."
    tradingcrew "$symbol" >> analysis_results.txt
    sleep 60  # Rate limiting
done
```

### Cron Job

```bash
# Run daily at 9:30 AM
30 9 * * 1-5 /usr/bin/tradingcrew "NVDA,AAPL,TSLA" >> /var/log/trading.log 2>&1
```

### Python Integration

```python
import subprocess

symbols = ["NVDA", "AAPL", "TSLA"]

for symbol in symbols:
    result = subprocess.run(
        ["tradingcrew", symbol],
        capture_output=True,
        text=True
    )
    print(f"{symbol}: {result.stdout}")
```

## Tips

1. **Use quotes** for symbols with special characters
2. **Check API keys** before running
3. **Rate limiting** - Add delays between batch runs
4. **Redirect output** for logging: `tradingcrew NVDA >> log.txt`
5. **Debug mode** helps troubleshoot issues

## See Also

- [Python API](../getting-started.md#using-the-python-api)
- [Web UI](web-ui.md)
- [Configuration](../configuration/settings.md)
