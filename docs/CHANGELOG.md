# Changelog

All notable changes to TradingCrew are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

---

## [0.4.0] - 2025-02-14

### Added
- **Sector/Correlation Analyst**: New analyst evaluating relative strength, sector rotation, and peer comparison
  - Dynamic sector identification using yfinance API
  - LLM validation to correct data provider misclassifications (e.g., Bitcoin miners as "Financial Services")
  - Business summary context for accurate sector determination
  - Analyzes correlation with SPY/QQQ and sector rotation signals
  - Includes max pain term structure and key OI levels across expirations
- **Multi-Expiration Options Analysis**: Options Analyst now analyzes next 4 expirations
  - Aggregate P/C ratios across all expirations
  - IV term structure (backwardation/contango detection)
  - Max pain term structure showing price drift expectations
  - Key OI levels consolidated from all chains
  - Positioning divergence analysis (near-term vs longer-term)
- **Electron Desktop Wrapper**: Cross-platform native app wrapper for TradingCrew
  - macOS, Windows, and Linux builds
  - System tray integration with quick actions
  - Auto-starts Python backend on launch
- **Chart Auto-Load from Watchlist**: Chart now auto-loads first watchlist symbol on startup

### Changed
- **12-Month Analysis Standardization**: All analysis tools now default to 365-day lookback
  - Market analyst, sector analyst, macro tools all use 12-month data
  - Chart panel displays 252 trading days (~12 months)
  - Consistent historical context across all analysts
- **Parallel Execution Stagger**: Increased stagger delay to 1-30 seconds between ticker submissions
  - Prevents API/LLM overload when starting large watchlists
  - Applies to single run, loop mode, and market hour modes

### Fixed
- Python 3.10 compatibility for test patch targets in webui module

---

## [0.3.0] - 2025-02-12

### Added
- **Symbol Select Dropdowns**: Replaced button grid with clean `dbc.Select` dropdowns for symbol selection in both Chart and Reports panels
  - Synced across panels via hidden pagination components
  - History mode shows folder-prefixed labels for historical runs
  - Dropdown auto-populates from `app_state.symbol_states` on each refresh
- **Stop-Loss and Take-Profit Orders**: Automatic protective orders for stock positions
  - Configure in Settings > System Settings > Risk Management (SL/TP)
  - Enable/disable stop-loss and take-profit independently
  - Set default percentage-based levels (SL: 5%, TP: 10%)
  - AI extraction: Parse trader agent's analysis for recommended SL/TP prices
  - Bracket orders for stocks (atomic entry + SL + TP)
  - Separate orders for crypto (no bracket support)
  - Validation ensures SL/TP levels make sense (e.g., SL below entry for BUY)
- **New Alpaca Order Functions**:
  - `place_bracket_order()` - Atomic bracket order placement
  - `place_stop_order()` - Standalone stop order
  - `place_limit_order()` - Standalone limit order
  - `extract_sl_tp_from_analysis()` - AI extraction from markdown tables
- **CLAUDE.md Self-Update Requirement**: New mandatory rule to keep CLAUDE.md in sync with code changes

### Changed
- `execute_trading_action()` now accepts optional `sl_tp_config` and `analysis_text` parameters
- Trading execution flow integrates SL/TP placement automatically when enabled
- Removed redundant centered symbol display from chart panel (dropdown already shows selected symbol)
- Moved chart "Last updated" timestamp to a discrete inline position next to control buttons
- Removed ~300 lines of button-grid CSS and replaced with compact dropdown styles

---

## [0.2.9] - 2025-02-11

### Added
- **Agent Progress Timestamps**: Analysis start and completion times now displayed in EST/EDT format for each ticker in the Agent Progress panel
- **Live Reddit API Integration**: Social Media Analyst can now fetch real-time Reddit data using PRAW instead of relying on cached JSONL files
  - Configure Reddit API credentials in Settings > API Keys
  - Searches subreddits: wallstreetbets, stocks, investing, stockmarket, options (for stocks)
  - Searches subreddits: cryptocurrency, bitcoin, ethereum, CryptoMarkets (for crypto)
  - Graceful fallback to cached data if API not configured or fails

### Changed
- **Renamed Run Queue to Portfolio**: The "Run Queue" section is now called "Portfolio" throughout the UI and documentation, better reflecting its purpose as a portfolio of stocks the analysts are working with
- **Replaced Google News with Finnhub**: News Analyst now uses Finnhub API exclusively instead of Google News web scraping, providing more reliable and consistent news data

### Fixed
- **Parallel Ticker Tool Output Race Condition**: Fixed bug where tool outputs were tagged with wrong ticker during parallel analysis. Now uses thread-local storage for proper per-ticker isolation
- **News Analyst Tool Configuration**: News Analyst now uses Finnhub API exclusively for news data (CoinDesk added for crypto). Clear separation of responsibilities between analysts
- **Social Media Analyst Tool Configuration**: Social Media Analyst now uses Reddit API exclusively for social sentiment analysis. Previously had overlapping tools with News Analyst
- **Max Parallel Tickers TypeError**: Fixed error when max_parallel_tickers setting was None

---

## [0.2.8] - 2025-02-10

### Added
- **Configurable Max Parallel Tickers**: Users can now set how many tickers are analyzed simultaneously (1-10) in Settings > Analysis Defaults
- **Loop Mode Next Run Display**: Shows when the next Loop Mode iteration will run in EST/EDT timezone
- **Mandatory Requirements in CLAUDE.md**: Added requirements for tests and descriptive release messages

### Changed
- Moved parallel tickers configuration from hardcoded value to user-configurable setting
- Updated status bar to show next run time during Loop Mode

---

## [0.2.7] - 2025-02-10

### Added
- Loop mode next run time display in EST/EDT timezone

### Note
This release had a version mismatch issue with PyPI. Use v0.2.8 instead.

---

## [0.2.6] - 2025-02-09

### Fixed
- **Account Bar Refresh**: Fixed issue where account balance bar wasn't updating properly after trades or portfolio changes

---

## [0.2.5] - 2025-02-08

### Added
- **Log Streaming Toggle**: Button to pause/resume real-time log updates
- **Collapsible Log Panel**: Log panel can now be collapsed to save screen space

### Changed
- Standardized log panel behavior across different views

---

## [0.2.4] - 2025-02-07

### Changed
- **Scanner API Warning**: Market Scanner is now disabled when Alpaca API keys are not configured
- Clear messaging when scanner is unavailable due to missing configuration

---

## [0.2.3] - 2025-02-06

### Added
- Scanner API configuration warning message
- Better error handling for missing API configurations

---

## [0.2.2] - 2025-02-05

### Changed
- API key fields now show "Not Configured" status when keys are missing
- Improved visual feedback for API configuration status

---

## [0.2.1] - 2025-02-04

### Fixed
- Excluded database files (*.db) from package distribution
- Fixed package data configuration for proper installation

---

## [0.2.0] - 2025-02-03

### Added
- **Persistent SQLite Storage**: Analysis reports now persist in SQLite database
- Report history accessible across sessions
- Database fallback for run queue when localStorage unavailable

### Changed
- Migrated from session-only storage to persistent database storage
- Improved data reliability across page refreshes

---

## [0.1.x] - Earlier Releases

### Features from Earlier Development
- TradingView-style interactive charts
- Watchlist persistence with drag-and-drop reordering
- Market hour scheduling for automated analysis
- Run queue for batch symbol processing
- Multi-agent LLM analysis framework
- Bull vs Bear research debate system
- Risk management with 3-way debate
- Paper and live trading via Alpaca
- CLI and Web UI interfaces
- Support for stocks and crypto assets

---

## Version Numbering

- **Major (X.0.0)**: Breaking changes or major new features
- **Minor (0.X.0)**: New features, backwards compatible
- **Patch (0.0.X)**: Bug fixes and small improvements

## Upgrade Notes

### Upgrading to 0.2.x

1. Database migrations are automatic
2. Browser localStorage settings are preserved
3. Re-test API connections after upgrade

### Fresh Installation

```bash
pip install --upgrade tradingcrew
```

## Reporting Issues

Found a bug or have a feature request?

Open an issue: [github.com/rminchev1/TradingCrew/issues](https://github.com/rminchev1/TradingCrew/issues)
