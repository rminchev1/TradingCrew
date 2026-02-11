# Troubleshooting

Common issues and their solutions.

## API Issues

### "OpenAI API Key Invalid"

**Symptoms**:
- Analysis fails to start
- Error mentions API key

**Solutions**:
1. Verify key starts with `sk-`
2. Check for extra spaces
3. Ensure account has credits
4. Generate a new key if expired

### "Alpaca Connection Failed"

**Symptoms**:
- Charts don't load
- Portfolio shows empty
- Scanner disabled

**Solutions**:
1. Check both API Key and Secret are set
2. Verify paper vs live mode matches your keys
3. Ensure account is active
4. Check Alpaca status page

### "Rate Limited"

**Symptoms**:
- Requests fail intermittently
- "429 Too Many Requests" error

**Solutions**:
1. Wait a few minutes and retry
2. Reduce parallel tickers setting
3. Increase loop interval
4. Upgrade API tier

### "Finnhub/FRED Data Missing"

**Symptoms**:
- News analyst returns empty
- Macro data unavailable

**Solutions**:
1. Check API key is set
2. Verify free tier limits
3. Wait for rate limit reset
4. Analysis continues with available data

## Web UI Issues

### Page Won't Load

**Symptoms**:
- Blank page
- Connection refused

**Solutions**:
1. Check if another process uses port 7860:
   ```bash
   lsof -i :7860
   ```
2. Try different port:
   ```bash
   python run_webui_dash.py --port 8080
   ```
3. Check for Python errors in terminal

### Charts Not Displaying

**Symptoms**:
- Empty chart area
- "No data" message

**Solutions**:
1. Verify Alpaca API configured
2. Check symbol is valid
3. Ensure market has data (may be closed)
4. Try a major symbol like `AAPL`

### Settings Not Saving

**Symptoms**:
- Settings reset on refresh
- Changes don't persist

**Solutions**:
1. Click "Save Settings" button
2. Check browser allows localStorage
3. Clear browser cache and retry
4. Try a different browser

### Reports Panel Empty

**Symptoms**:
- No reports showing
- Tabs are empty

**Solutions**:
1. Run an analysis first
2. Check Log Panel for errors
3. Verify database file exists
4. Check browser console for errors

## Analysis Issues

### Analysis Stuck

**Symptoms**:
- Progress stops
- No updates for several minutes

**Solutions**:
1. Check Log Panel for errors
2. Verify API keys are valid
3. Check internet connection
4. Restart the web UI

### "Recursion Limit Reached"

**Symptoms**:
- Analysis stops mid-way
- Error about max recursion

**Solutions**:
1. Increase Max Recursion Limit in Settings
2. Reduce research depth
3. Simplify symbol list

### Wrong Recommendations

**Symptoms**:
- Unexpected BUY/SELL signals
- Contradictory analysis

**Solutions**:
1. Check input symbol is correct
2. Review analyst reports for data quality
3. Increase debate rounds for more thorough analysis
4. Verify market data is current

### Slow Analysis

**Symptoms**:
- Analysis takes very long
- Timeouts

**Solutions**:
1. Use faster LLM models
2. Reduce debate rounds
3. Disable unused analysts
4. Check API rate limits

## Trading Issues

### Orders Not Executing

**Symptoms**:
- Trade button clicked but no order
- Position not appearing

**Solutions**:
1. Check market hours (stocks)
2. Verify account has buying power
3. Ensure not in paper mode if expecting live trades
4. Check Alpaca dashboard for order status

### Position Not Showing

**Symptoms**:
- Order filled but position missing

**Solutions**:
1. Refresh the Portfolio panel
2. Check Orders tab for fill confirmation
3. Allow a few seconds for sync
4. Check Alpaca dashboard directly

### Wrong Mode (Paper/Live)

**Symptoms**:
- Unexpected mode indicator
- Orders going to wrong account

**Solutions**:
1. Check `.env` file: `ALPACA_USE_PAPER=True/False`
2. Restart the application after changing
3. Verify in Settings page

## Loop Mode Issues

### Loop Not Starting

**Symptoms**:
- Toggle on but no activity
- No next run time shown

**Solutions**:
1. Ensure Portfolio has symbols
2. Check no other analysis running
3. Verify interval is set (1-1440)

### Missed Iterations

**Symptoms**:
- Runs skipped
- Irregular intervals

**Solutions**:
1. Keep browser tab open/active
2. Prevent system sleep
3. Check for API errors in logs

### Market Hours Not Working

**Symptoms**:
- Runs outside specified times
- Times ignored

**Solutions**:
1. Use correct format: `10:30,14:15`
2. Verify timezone (EST/EDT)
3. Enable Market Hours Mode toggle

## Database Issues

### "Database Locked"

**Symptoms**:
- Errors saving reports
- SQLite lock errors

**Solutions**:
1. Restart the application
2. Check for zombie processes
3. Ensure only one instance running

### Reports Missing

**Symptoms**:
- Historical reports gone
- Empty report history

**Solutions**:
1. Check database file exists
2. Verify file permissions
3. Check disk space

## Performance Issues

### High Memory Usage

**Solutions**:
1. Reduce parallel tickers
2. Clear old reports
3. Restart periodically
4. Use `--max-threads` option

### High CPU Usage

**Solutions**:
1. Reduce parallelization
2. Use faster/smaller LLM models
3. Increase loop intervals

## Getting Help

### Collect Debug Info

Before reporting issues:

1. Enable debug mode:
   ```bash
   python run_webui_dash.py --debug
   ```

2. Check browser console (F12 → Console)

3. Review terminal output

4. Note the exact error message

### Report Issues

Open an issue at:
[github.com/rminchev1/TradingCrew/issues](https://github.com/rminchev1/TradingCrew/issues)

Include:
- Python version
- OS and version
- Error messages
- Steps to reproduce
- Configuration (without API keys)
