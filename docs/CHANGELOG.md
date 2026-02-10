# Changelog

All notable changes to TradingCrew are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

*No unreleased changes yet.*

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
