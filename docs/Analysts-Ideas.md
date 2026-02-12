# Analyst Agent Ideas

Ideas for new analyst agents to add to the TradingCrew multi-agent framework, based on gaps identified in the current 6-analyst pipeline.

---

## Current Analysts (Reference)

| # | Analyst | Data Sources | Report Field | Focus |
|---|---------|-------------|--------------|-------|
| 1 | Market Analyst | Alpaca, StockStats | `market_report` | Technical indicators (RSI, MACD, Bollinger, etc.), EOD chart patterns |
| 2 | News Analyst | Finnhub, CoinDesk | `news_report` | After-hours catalysts, analyst upgrades, earnings announcements |
| 3 | Social Media Analyst | Reddit API | `sentiment_report` | Retail sentiment, buzz intensity, contrarian signals |
| 4 | Fundamentals Analyst | OpenAI, SimFin, DeFiLlama, Earnings | `fundamentals_report` | Financials, insider trading, DeFi metrics (crypto) |
| 5 | Macro Analyst | FRED API | `macro_report` | Economic indicators, yield curve, Fed schedule, VIX |
| 6 | Options Analyst | Alpaca Options | `options_report` | Put/call ratios, IV skew, max pain, unusual activity |

---

## High-Impact Ideas

### 1. Volume & Institutional Flow Analyst

**Gap:** Volume data is available via Alpaca and options volume via `get_options_positioning`, but no analyst focuses on money flow patterns. The Market Analyst uses volume only as a secondary confirmation signal.

**Value:** Detect accumulation/distribution patterns, unusual volume spikes, dark pool prints, and large block trade activity. Institutional positioning often precedes overnight gaps — exactly the kind of signal the EOD framework needs.

**Existing tools it would use:**
- `get_alpaca_data` — OHLCV with volume
- `get_stock_data_table` — 90-day historical data
- `get_indicators_table` — OBV, MFI already computed
- `get_options_positioning` — unusual options volume

**New tools needed:** None (existing data sufficient)

**Report field:** `volume_flow_report`

---

### 2. Sector/Correlation Analyst

**Gap:** Every analyst evaluates the ticker in isolation. No agent compares the stock's behavior against its sector peers, the broader index (SPY/QQQ), or correlated instruments.

**Value:** A stock trading at relative strength vs. its sector has very different overnight risk than one lagging. Sector rotation signals (money moving from tech to energy, etc.) are powerful overnight catalysts.

**Existing tools it would use:**
- `get_alpaca_data` — pull data for peers/indices alongside the target ticker
- `get_indicators_table` — relative strength comparison
- `get_macro_analysis` — sector-level macro drivers

**New tools needed:** Possibly a `get_sector_peers` tool to identify peer tickers automatically.

**Report field:** `sector_correlation_report`

---

### 3. Event Catalyst / Earnings Risk Analyst

**Gap:** The Fundamentals Analyst mentions earnings dates via `get_earnings_calendar` and `get_earnings_surprise_analysis`, but these are used for general context — not for quantifying overnight event risk. Fed meetings, CPI releases, and earnings are all binary events that dominate overnight moves.

**Value:** Specifically quantify the probability and magnitude of overnight gaps from known catalysts. Historical earnings surprise data is already available but underutilized. This agent would answer: "Should we even hold through this event?"

**Existing tools it would use:**
- `get_earnings_calendar` — upcoming earnings dates
- `get_earnings_surprise_analysis` — historical surprise patterns
- `get_macro_analysis` — Fed schedule, economic calendar
- `get_options_positioning` — implied move from IV

**New tools needed:** None (existing data sufficient)

**Report field:** `event_catalyst_report`

---

### 4. FedWatch / Fed Policy Analyst

**Gap:** The Macro Analyst pulls the current Federal Funds Rate and yield curve from FRED, but does NOT track **market-implied rate change probabilities** (CME FedWatch). The FOMC calendar is also hardcoded for 2024 and outdated. There is no forward-looking rate expectation data.

**Value:** FedWatch-style probabilities are the single most market-moving macro signal for overnight positioning:
- Probability shifts move markets instantly (e.g., cut probability jumping from 40% to 85% after a weak CPI print)
- Forward-looking — FRED gives where rates *are*; FedWatch gives where markets *expect* them to go
- Changes intraday — perfect for EOD framework to catch end-of-day shifts
- Directly drives sector allocation — high cut probability favors growth/tech, low favors financials/value

**Implementation approach — two options:**

**Option A: Enhance Macro Analyst (simpler)**
Add a `get_fed_rate_expectations()` tool to `macro_utils.py` using FRED Fed Funds Futures data (`FF1`, `FF2`, etc.). Calculate implied probabilities:
```
Implied Rate = 100 - Futures Price
Cut Probability = (Current Rate - Implied Rate) / 0.25
```
This is exactly how CME FedWatch works under the hood. Since FRED API is already integrated, this requires no new API keys.

**Option B: Standalone Fed Policy Analyst (richer)**
Create a dedicated agent combining:
- FedWatch rate probabilities (from FRED futures data)
- Dot-plot projections
- Fed speaker sentiment analysis
- Rate trajectory analysis
- Dynamic FOMC calendar (derived from futures expiration dates)

**Also fixes:** Hardcoded 2024 FOMC calendar in `macro_utils.py:336-344`.

**New tools needed:** `get_fed_rate_expectations` (calculate from FRED futures data — no new API)

**Report field:** `fed_policy_report` (if standalone) or enhance `macro_report`

---

### 5. Technical Pattern Recognition Analyst

**Gap:** The Market Analyst focuses on indicators (RSI, MACD, Bollinger Bands, etc.) but doesn't do chart pattern recognition — double bottoms, head & shoulders, flag breakouts, channel boundaries, etc.

**Value:** Many overnight setups are driven by pattern completions (e.g., a breakout above a descending trendline at close). The 90-day historical data from `get_stock_data_table` provides plenty of context for pattern detection.

**Existing tools it would use:**
- `get_stock_data_table` — 90 days OHLCV
- `get_indicators_table` — support/resistance via Bollinger/ATR
- `get_alpaca_data` — raw price data

**New tools needed:** None (LLM can identify patterns from price data, or add a dedicated pattern detection library)

**Report field:** `pattern_report`

---

## Medium-Impact Ideas

### 6. Crypto-Specific Analyst

**Gap:** Current analysts apply stock-oriented analysis to crypto. Crypto has unique dynamics — Bitcoin dominance, altcoin correlation, on-chain metrics, DeFi TVL flows. `get_defillama_fundamentals` exists but is only lightly used by the Fundamentals Analyst.

**Value:** Crypto-native signals like BTC dominance shifts, stablecoin flows, protocol TVL changes, and altcoin season indicators. Only useful if crypto is traded frequently.

**Existing tools it would use:**
- `get_defillama_fundamentals` — TVL, protocol data
- `get_coindesk_news` — crypto news
- `get_alpaca_data` — BTC/ETH correlation data

**New tools needed:** On-chain data API (e.g., Glassnode, CryptoQuant) for wallet flows, exchange reserves, etc.

**Report field:** `crypto_report`

---

### 7. Overnight Gap / Volatility Risk Analyst

**Gap:** No agent specifically models overnight gap risk — the probability and expected magnitude of a gap up/down at next open based on historical patterns, current IV, and after-hours activity.

**Value:** Directly answers the position sizing question: "Given expected overnight volatility, what's the max safe position size?" Combines options IV data with historical gap statistics.

**Existing tools it would use:**
- `get_options_positioning` — IV, expected move
- `get_stock_data_table` — historical gap analysis (open vs. previous close)
- `get_alpaca_data` — recent price action

**New tools needed:** None (can calculate gap statistics from existing OHLCV data)

**Report field:** `gap_risk_report`

---

## Lower Priority Ideas

### 8. Signal Convergence / Confluence Analyst

**Gap:** The Bull/Bear researchers already synthesize all 6 reports, but they argue a side rather than objectively measuring signal alignment.

**Value:** A purely quantitative "conviction score" — when 5/6 analysts are bullish, that's a different setup than 3/3. Could be a lightweight scoring pass rather than a full agent.

**Note:** Overlaps significantly with what the researchers already do. Lower priority unless a quantitative pre-filter before the debate is desired.

**Report field:** `confluence_report`

---

## Priority Matrix

| Rank | Analyst Idea | New APIs? | Effort | Signal Value |
|------|-------------|-----------|--------|--------------|
| 1 | Sector/Correlation | No | Medium | Very High |
| 2 | Volume & Institutional Flow | No | Low | Very High |
| 3 | FedWatch / Fed Policy | No (FRED) | Medium | High |
| 4 | Event Catalyst / Earnings Risk | No | Low | High |
| 5 | Technical Pattern Recognition | No | Medium | Medium-High |
| 6 | Overnight Gap / Volatility Risk | No | Low | Medium |
| 7 | Crypto-Specific | Yes | High | Medium (crypto only) |
| 8 | Signal Convergence | No | Low | Low (overlap) |

---

## Architecture Notes

### Adding a New Analyst Agent

Files to modify (per CLAUDE.md patterns):
1. `tradingagents/agents/analysts/<new_analyst>.py` — Agent implementation
2. `tradingagents/agents/utils/agent_states.py` — Add report field to `AgentState`
3. `tradingagents/dataflows/interface.py` — Add any new `@tool` functions
4. `tradingagents/graph/setup.py` — Add node to LangGraph workflow
5. `tradingagents/graph/trading_graph.py` — Wire into execution flow
6. `webui/callbacks/status_callbacks.py` — Add status tracking for new agent
7. `webui/components/reports_panel.py` — Display new report in UI

### Considerations
- Each new analyst adds ~10-30s to analysis time (LLM call + tool calls)
- Parallel analyst mode runs all concurrently, so wall-clock impact is minimal
- WebUI forces sequential mode for proper status updates — more agents = longer sequential time
- All new analysts feed into the existing Bull/Bear debate → Trader → Risk debate pipeline
- New report fields automatically become available to researchers and risk agents
