"""
Options Data Utilities for TradingAgents
Fetches and analyzes options market positioning using yfinance.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
from .external_data_logger import log_external_error, log_api_error

warnings.filterwarnings("ignore")


def get_options_chain(symbol: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], List[str]]:
    """
    Fetch options chain data for a symbol.

    Returns:
        Tuple of (calls_df, puts_df, expiration_dates)
    """
    try:
        ticker = yf.Ticker(symbol)
        expirations = ticker.options

        if not expirations:
            return None, None, []

        # Get the nearest expiration (weekly/monthly)
        nearest_exp = expirations[0]

        chain = ticker.option_chain(nearest_exp)
        calls = chain.calls
        puts = chain.puts

        return calls, puts, list(expirations)
    except Exception as e:
        log_external_error(
            system="options",
            operation="get_options_chain",
            error=e,
            symbol=symbol
        )
        return None, None, []


def get_multiple_expirations_chain(symbol: str, num_expirations: int = 3) -> Dict:
    """
    Fetch options chains for multiple expiration dates.

    Returns:
        Dict with expiration dates as keys, each containing calls and puts DataFrames
    """
    try:
        ticker = yf.Ticker(symbol)
        expirations = ticker.options

        if not expirations:
            return {}

        chains = {}
        for exp in expirations[:num_expirations]:
            try:
                chain = ticker.option_chain(exp)
                chains[exp] = {
                    'calls': chain.calls,
                    'puts': chain.puts
                }
            except:
                continue

        return chains
    except Exception as e:
        print(f"[OPTIONS] Error fetching multiple chains for {symbol}: {e}")
        return {}


def calculate_put_call_ratio(calls: pd.DataFrame, puts: pd.DataFrame) -> Dict:
    """
    Calculate put/call ratios for volume and open interest.

    Returns:
        Dict with volume_ratio, oi_ratio, and interpretation
    """
    try:
        total_call_volume = calls['volume'].sum() if 'volume' in calls.columns else 0
        total_put_volume = puts['volume'].sum() if 'volume' in puts.columns else 0

        total_call_oi = calls['openInterest'].sum() if 'openInterest' in calls.columns else 0
        total_put_oi = puts['openInterest'].sum() if 'openInterest' in puts.columns else 0

        # Handle division by zero
        volume_ratio = total_put_volume / total_call_volume if total_call_volume > 0 else 0
        oi_ratio = total_put_oi / total_call_oi if total_call_oi > 0 else 0

        # Interpretation
        if volume_ratio < 0.7:
            volume_sentiment = "Very Bullish"
        elif volume_ratio < 0.9:
            volume_sentiment = "Bullish"
        elif volume_ratio < 1.1:
            volume_sentiment = "Neutral"
        elif volume_ratio < 1.3:
            volume_sentiment = "Bearish"
        else:
            volume_sentiment = "Very Bearish"

        return {
            'volume_ratio': round(volume_ratio, 2),
            'oi_ratio': round(oi_ratio, 2),
            'total_call_volume': int(total_call_volume),
            'total_put_volume': int(total_put_volume),
            'total_call_oi': int(total_call_oi),
            'total_put_oi': int(total_put_oi),
            'volume_sentiment': volume_sentiment
        }
    except Exception as e:
        print(f"[OPTIONS] Error calculating put/call ratio: {e}")
        return {
            'volume_ratio': 0,
            'oi_ratio': 0,
            'volume_sentiment': 'Unknown'
        }


def calculate_max_pain(calls: pd.DataFrame, puts: pd.DataFrame, current_price: float) -> Dict:
    """
    Calculate max pain - the strike price where option holders lose the most.
    This is often a price magnet near expiration.

    Returns:
        Dict with max_pain strike and analysis
    """
    try:
        # Get unique strikes
        all_strikes = sorted(set(calls['strike'].tolist() + puts['strike'].tolist()))

        if not all_strikes:
            return {'max_pain': 0, 'distance_pct': 0}

        max_pain_values = []

        for strike in all_strikes:
            total_pain = 0

            # Pain for call holders (calls expire worthless if price < strike)
            for _, call in calls.iterrows():
                if strike < call['strike']:
                    # Call expires worthless
                    total_pain += call.get('openInterest', 0) * call['strike'] * 100
                else:
                    # Call has value
                    total_pain += call.get('openInterest', 0) * (strike - call['strike']) * 100

            # Pain for put holders (puts expire worthless if price > strike)
            for _, put in puts.iterrows():
                if strike > put['strike']:
                    # Put expires worthless
                    total_pain += put.get('openInterest', 0) * put['strike'] * 100
                else:
                    # Put has value
                    total_pain += put.get('openInterest', 0) * (put['strike'] - strike) * 100

            max_pain_values.append((strike, total_pain))

        # Find strike with minimum total pain (max pain for holders)
        max_pain_strike = min(max_pain_values, key=lambda x: x[1])[0]

        distance_pct = ((max_pain_strike - current_price) / current_price) * 100 if current_price > 0 else 0

        return {
            'max_pain': max_pain_strike,
            'distance_pct': round(distance_pct, 2),
            'interpretation': f"Price may gravitate toward ${max_pain_strike} by expiration ({distance_pct:+.1f}% from current)"
        }
    except Exception as e:
        print(f"[OPTIONS] Error calculating max pain: {e}")
        return {'max_pain': 0, 'distance_pct': 0}


def get_key_oi_levels(calls: pd.DataFrame, puts: pd.DataFrame, current_price: float, top_n: int = 5) -> Dict:
    """
    Identify key open interest levels that act as support/resistance.

    Returns:
        Dict with highest OI strikes for calls (resistance) and puts (support)
    """
    try:
        # Get top call OI strikes (potential resistance)
        calls_sorted = calls.nlargest(top_n, 'openInterest')[['strike', 'openInterest', 'volume']]
        call_levels = []
        for _, row in calls_sorted.iterrows():
            pct_away = ((row['strike'] - current_price) / current_price) * 100
            call_levels.append({
                'strike': row['strike'],
                'oi': int(row['openInterest']),
                'volume': int(row.get('volume', 0)),
                'pct_away': round(pct_away, 1)
            })

        # Get top put OI strikes (potential support)
        puts_sorted = puts.nlargest(top_n, 'openInterest')[['strike', 'openInterest', 'volume']]
        put_levels = []
        for _, row in puts_sorted.iterrows():
            pct_away = ((row['strike'] - current_price) / current_price) * 100
            put_levels.append({
                'strike': row['strike'],
                'oi': int(row['openInterest']),
                'volume': int(row.get('volume', 0)),
                'pct_away': round(pct_away, 1)
            })

        # Identify the most significant levels
        highest_call_oi = call_levels[0] if call_levels else None
        highest_put_oi = put_levels[0] if put_levels else None

        return {
            'call_resistance_levels': call_levels,
            'put_support_levels': put_levels,
            'primary_resistance': highest_call_oi,
            'primary_support': highest_put_oi
        }
    except Exception as e:
        print(f"[OPTIONS] Error getting key OI levels: {e}")
        return {}


def calculate_iv_metrics(calls: pd.DataFrame, puts: pd.DataFrame, current_price: float) -> Dict:
    """
    Calculate implied volatility metrics from options chain.

    Returns:
        Dict with IV metrics and expected move
    """
    try:
        # Get ATM options (closest to current price)
        calls['distance'] = abs(calls['strike'] - current_price)
        puts['distance'] = abs(puts['strike'] - current_price)

        atm_call = calls.nsmallest(1, 'distance').iloc[0] if len(calls) > 0 else None
        atm_put = puts.nsmallest(1, 'distance').iloc[0] if len(puts) > 0 else None

        # Get IV from ATM options
        call_iv = atm_call['impliedVolatility'] if atm_call is not None and 'impliedVolatility' in calls.columns else 0
        put_iv = atm_put['impliedVolatility'] if atm_put is not None and 'impliedVolatility' in puts.columns else 0

        # Average ATM IV
        atm_iv = (call_iv + put_iv) / 2 if (call_iv > 0 and put_iv > 0) else max(call_iv, put_iv)
        atm_iv_pct = atm_iv * 100

        # Calculate IV skew (put IV - call IV)
        # Positive skew = puts more expensive = fear/hedging
        # Negative skew = calls more expensive = greed/speculation
        iv_skew = (put_iv - call_iv) * 100

        if iv_skew > 5:
            skew_interpretation = "High put premium - fear/hedging activity"
        elif iv_skew > 2:
            skew_interpretation = "Moderate put premium - some caution"
        elif iv_skew > -2:
            skew_interpretation = "Balanced - neutral sentiment"
        elif iv_skew > -5:
            skew_interpretation = "Moderate call premium - bullish speculation"
        else:
            skew_interpretation = "High call premium - aggressive bullishness"

        # Calculate expected move (using ATM straddle approximation)
        # Expected move ≈ ATM straddle price / current price
        atm_call_price = atm_call['lastPrice'] if atm_call is not None else 0
        atm_put_price = atm_put['lastPrice'] if atm_put is not None else 0
        straddle_price = atm_call_price + atm_put_price
        expected_move_pct = (straddle_price / current_price) * 100 if current_price > 0 else 0
        expected_move_dollars = straddle_price

        return {
            'atm_iv': round(atm_iv_pct, 1),
            'call_iv': round(call_iv * 100, 1),
            'put_iv': round(put_iv * 100, 1),
            'iv_skew': round(iv_skew, 2),
            'skew_interpretation': skew_interpretation,
            'expected_move_pct': round(expected_move_pct, 2),
            'expected_move_dollars': round(expected_move_dollars, 2),
            'straddle_price': round(straddle_price, 2)
        }
    except Exception as e:
        print(f"[OPTIONS] Error calculating IV metrics: {e}")
        return {
            'atm_iv': 0,
            'iv_skew': 0,
            'expected_move_pct': 0
        }


def detect_unusual_activity(calls: pd.DataFrame, puts: pd.DataFrame, volume_threshold: float = 2.0) -> Dict:
    """
    Detect unusual options activity based on volume vs open interest.

    High volume relative to OI suggests new positioning.

    Returns:
        Dict with unusual activity alerts
    """
    try:
        unusual_calls = []
        unusual_puts = []

        # Analyze calls
        for _, row in calls.iterrows():
            oi = row.get('openInterest', 0)
            vol = row.get('volume', 0)

            if oi > 100 and vol > 0:  # Minimum thresholds
                vol_oi_ratio = vol / oi if oi > 0 else 0

                if vol_oi_ratio >= volume_threshold:
                    unusual_calls.append({
                        'strike': row['strike'],
                        'volume': int(vol),
                        'oi': int(oi),
                        'vol_oi_ratio': round(vol_oi_ratio, 1),
                        'last_price': round(row.get('lastPrice', 0), 2),
                        'bid': round(row.get('bid', 0), 2),
                        'ask': round(row.get('ask', 0), 2)
                    })

        # Analyze puts
        for _, row in puts.iterrows():
            oi = row.get('openInterest', 0)
            vol = row.get('volume', 0)

            if oi > 100 and vol > 0:
                vol_oi_ratio = vol / oi if oi > 0 else 0

                if vol_oi_ratio >= volume_threshold:
                    unusual_puts.append({
                        'strike': row['strike'],
                        'volume': int(vol),
                        'oi': int(oi),
                        'vol_oi_ratio': round(vol_oi_ratio, 1),
                        'last_price': round(row.get('lastPrice', 0), 2),
                        'bid': round(row.get('bid', 0), 2),
                        'ask': round(row.get('ask', 0), 2)
                    })

        # Sort by volume/OI ratio
        unusual_calls = sorted(unusual_calls, key=lambda x: x['vol_oi_ratio'], reverse=True)[:5]
        unusual_puts = sorted(unusual_puts, key=lambda x: x['vol_oi_ratio'], reverse=True)[:5]

        # Overall assessment
        total_unusual_call_vol = sum(c['volume'] for c in unusual_calls)
        total_unusual_put_vol = sum(p['volume'] for p in unusual_puts)

        if total_unusual_call_vol > total_unusual_put_vol * 1.5:
            activity_bias = "Bullish - more unusual call activity"
        elif total_unusual_put_vol > total_unusual_call_vol * 1.5:
            activity_bias = "Bearish - more unusual put activity"
        else:
            activity_bias = "Mixed - unusual activity on both sides"

        return {
            'unusual_calls': unusual_calls,
            'unusual_puts': unusual_puts,
            'activity_bias': activity_bias,
            'has_unusual_activity': len(unusual_calls) > 0 or len(unusual_puts) > 0
        }
    except Exception as e:
        print(f"[OPTIONS] Error detecting unusual activity: {e}")
        return {
            'unusual_calls': [],
            'unusual_puts': [],
            'has_unusual_activity': False
        }


def get_current_price(symbol: str) -> float:
    """Get current stock price."""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")
        if len(data) > 0:
            return data['Close'].iloc[-1]
        return 0
    except:
        return 0


def get_full_options_analysis(symbol: str, curr_date: str = None) -> str:
    """
    Get comprehensive options market positioning analysis for a stock.

    Returns:
        Formatted string with full options analysis
    """
    try:
        # Get current price
        current_price = get_current_price(symbol)
        if current_price == 0:
            return f"Error: Could not fetch current price for {symbol}"

        # Get options chain
        calls, puts, expirations = get_options_chain(symbol)

        if calls is None or puts is None or len(expirations) == 0:
            return f"Error: No options data available for {symbol}. This may be a stock without listed options."

        nearest_exp = expirations[0]

        # Calculate all metrics
        pc_ratio = calculate_put_call_ratio(calls, puts)
        max_pain = calculate_max_pain(calls, puts, current_price)
        key_levels = get_key_oi_levels(calls, puts, current_price)
        iv_metrics = calculate_iv_metrics(calls, puts, current_price)
        unusual = detect_unusual_activity(calls, puts)

        # Format the report
        report = f"""
# OPTIONS MARKET POSITIONING ANALYSIS: {symbol}

**Current Stock Price:** ${current_price:.2f}
**Nearest Expiration:** {nearest_exp}
**Available Expirations:** {len(expirations)} dates

---

## 1. SENTIMENT INDICATORS

### Put/Call Ratios
| Metric | Value | Interpretation |
|--------|-------|----------------|
| Volume P/C Ratio | {pc_ratio['volume_ratio']:.2f} | {pc_ratio['volume_sentiment']} |
| Open Interest P/C Ratio | {pc_ratio['oi_ratio']:.2f} | {"Bullish" if pc_ratio['oi_ratio'] < 1 else "Bearish"} bias |

**Volume Breakdown:**
- Total Call Volume: {pc_ratio['total_call_volume']:,}
- Total Put Volume: {pc_ratio['total_put_volume']:,}
- Total Call OI: {pc_ratio['total_call_oi']:,}
- Total Put OI: {pc_ratio['total_put_oi']:,}

### IV Skew Analysis
- **Put IV:** {iv_metrics.get('put_iv', 0):.1f}%
- **Call IV:** {iv_metrics.get('call_iv', 0):.1f}%
- **Skew:** {iv_metrics.get('iv_skew', 0):+.2f}%
- **Interpretation:** {iv_metrics.get('skew_interpretation', 'N/A')}

---

## 2. EXPECTED MOVE & VOLATILITY

| Metric | Value |
|--------|-------|
| ATM Implied Volatility | {iv_metrics.get('atm_iv', 0):.1f}% |
| Expected Move (to expiry) | ±${iv_metrics.get('expected_move_dollars', 0):.2f} (±{iv_metrics.get('expected_move_pct', 0):.1f}%) |
| ATM Straddle Price | ${iv_metrics.get('straddle_price', 0):.2f} |

**Volatility Assessment:** {"High IV - options are expensive, big move expected" if iv_metrics.get('atm_iv', 0) > 40 else "Moderate IV - normal volatility expectations" if iv_metrics.get('atm_iv', 0) > 25 else "Low IV - options are cheap, quiet period expected"}

---

## 3. KEY PRICE LEVELS (from Options OI)

### Max Pain Analysis
- **Max Pain Strike:** ${max_pain.get('max_pain', 0):.2f}
- **Distance from Current:** {max_pain.get('distance_pct', 0):+.1f}%
- **Interpretation:** {max_pain.get('interpretation', 'N/A')}

### Resistance Levels (High Call OI)
| Strike | Open Interest | Volume | Distance |
|--------|---------------|--------|----------|
"""
        # Add call resistance levels
        for level in key_levels.get('call_resistance_levels', [])[:3]:
            report += f"| ${level['strike']:.2f} | {level['oi']:,} | {level['volume']:,} | {level['pct_away']:+.1f}% |\n"

        report += """
### Support Levels (High Put OI)
| Strike | Open Interest | Volume | Distance |
|--------|---------------|--------|----------|
"""
        # Add put support levels
        for level in key_levels.get('put_support_levels', [])[:3]:
            report += f"| ${level['strike']:.2f} | {level['oi']:,} | {level['volume']:,} | {level['pct_away']:+.1f}% |\n"

        report += f"""
---

## 4. UNUSUAL OPTIONS ACTIVITY

**Activity Bias:** {unusual.get('activity_bias', 'Unknown')}

"""
        if unusual.get('unusual_calls'):
            report += "### Unusual Call Activity\n"
            report += "| Strike | Volume | OI | Vol/OI Ratio |\n"
            report += "|--------|--------|----|--------------|\n"
            for c in unusual['unusual_calls'][:3]:
                report += f"| ${c['strike']:.2f} | {c['volume']:,} | {c['oi']:,} | {c['vol_oi_ratio']:.1f}x |\n"
        else:
            report += "*No unusual call activity detected*\n"

        report += "\n"

        if unusual.get('unusual_puts'):
            report += "### Unusual Put Activity\n"
            report += "| Strike | Volume | OI | Vol/OI Ratio |\n"
            report += "|--------|--------|----|--------------|\n"
            for p in unusual['unusual_puts'][:3]:
                report += f"| ${p['strike']:.2f} | {p['volume']:,} | {p['oi']:,} | {p['vol_oi_ratio']:.1f}x |\n"
        else:
            report += "*No unusual put activity detected*\n"

        report += f"""
---

## 5. TRADING IMPLICATIONS

### For Stock Trading:
"""
        # Generate trading implications
        implications = []

        # Sentiment-based
        if pc_ratio['volume_ratio'] < 0.8:
            implications.append("- **Bullish Sentiment:** Low put/call ratio suggests traders are betting on upside")
        elif pc_ratio['volume_ratio'] > 1.2:
            implications.append("- **Bearish Sentiment:** High put/call ratio suggests caution or hedging")

        # Max pain
        if abs(max_pain.get('distance_pct', 0)) > 2:
            direction = "up" if max_pain.get('distance_pct', 0) > 0 else "down"
            implications.append(f"- **Max Pain Magnet:** Price may drift {direction} toward ${max_pain.get('max_pain', 0):.2f} into expiration")

        # Key levels
        if key_levels.get('primary_resistance'):
            implications.append(f"- **Resistance Watch:** Heavy call OI at ${key_levels['primary_resistance']['strike']:.2f} may cap upside")
        if key_levels.get('primary_support'):
            implications.append(f"- **Support Watch:** Heavy put OI at ${key_levels['primary_support']['strike']:.2f} may provide floor")

        # Volatility
        if iv_metrics.get('atm_iv', 0) > 40:
            implications.append("- **High IV Environment:** Large move expected - consider waiting for direction clarity")
        elif iv_metrics.get('atm_iv', 0) < 20:
            implications.append("- **Low IV Environment:** Quiet period expected - breakout may be coming")

        # Unusual activity
        if unusual.get('has_unusual_activity'):
            implications.append(f"- **Smart Money Alert:** {unusual.get('activity_bias', 'Unusual activity detected')}")

        if implications:
            report += "\n".join(implications)
        else:
            report += "- No significant options-based signals at this time"

        report += "\n"

        return report

    except Exception as e:
        log_external_error(
            system="options",
            operation="get_full_options_analysis",
            error=e,
            symbol=symbol
        )
        return f"Error generating options analysis for {symbol}: {str(e)}"
