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


def get_full_options_analysis(symbol: str, curr_date: str = None, num_expirations: int = 4) -> str:
    """
    Get comprehensive options market positioning analysis for a stock across multiple expirations.

    Analyzes the next 4 expiration dates to understand:
    - Term structure of positioning
    - Where institutional money is concentrated
    - How sentiment changes across time horizons

    Args:
        symbol: Stock ticker symbol
        curr_date: Current date (optional)
        num_expirations: Number of expirations to analyze (default 4)

    Returns:
        Formatted string with full options analysis across multiple expirations
    """
    try:
        # Get current price
        current_price = get_current_price(symbol)
        if current_price == 0:
            return f"Error: Could not fetch current price for {symbol}"

        # Get all available expirations
        ticker = yf.Ticker(symbol)
        all_expirations = ticker.options

        if not all_expirations or len(all_expirations) == 0:
            return f"Error: No options data available for {symbol}. This may be a stock without listed options."

        # Fetch chains for up to 4 expirations
        expirations_to_analyze = all_expirations[:min(num_expirations, len(all_expirations))]
        chains_data = get_multiple_expirations_chain(symbol, num_expirations)

        if not chains_data:
            return f"Error: Could not fetch options chains for {symbol}"

        # Calculate days to expiration for each
        today = datetime.now()
        exp_info = []
        for exp_date in expirations_to_analyze:
            exp_dt = datetime.strptime(exp_date, "%Y-%m-%d")
            dte = (exp_dt - today).days
            exp_info.append({'date': exp_date, 'dte': dte})

        # Aggregate metrics across all expirations
        total_call_oi = 0
        total_put_oi = 0
        total_call_volume = 0
        total_put_volume = 0
        all_max_pains = []
        all_key_levels = {'calls': [], 'puts': []}
        expiration_summaries = []

        for exp_date in expirations_to_analyze:
            if exp_date not in chains_data:
                continue

            calls = chains_data[exp_date]['calls']
            puts = chains_data[exp_date]['puts']

            if calls is None or puts is None or len(calls) == 0:
                continue

            # Calculate metrics for this expiration
            pc_ratio = calculate_put_call_ratio(calls, puts)
            max_pain = calculate_max_pain(calls, puts, current_price)
            key_levels = get_key_oi_levels(calls, puts, current_price, top_n=3)
            iv_metrics = calculate_iv_metrics(calls, puts, current_price)
            unusual = detect_unusual_activity(calls, puts)

            # Accumulate totals
            total_call_oi += pc_ratio.get('total_call_oi', 0)
            total_put_oi += pc_ratio.get('total_put_oi', 0)
            total_call_volume += pc_ratio.get('total_call_volume', 0)
            total_put_volume += pc_ratio.get('total_put_volume', 0)

            # Track max pain for each expiration
            dte = next((e['dte'] for e in exp_info if e['date'] == exp_date), 0)
            all_max_pains.append({
                'date': exp_date,
                'dte': dte,
                'max_pain': max_pain.get('max_pain', 0),
                'distance_pct': max_pain.get('distance_pct', 0)
            })

            # Collect key levels
            for level in key_levels.get('call_resistance_levels', []):
                level['expiration'] = exp_date
                level['dte'] = dte
                all_key_levels['calls'].append(level)
            for level in key_levels.get('put_support_levels', []):
                level['expiration'] = exp_date
                level['dte'] = dte
                all_key_levels['puts'].append(level)

            # Store expiration summary
            expiration_summaries.append({
                'date': exp_date,
                'dte': dte,
                'pc_ratio': pc_ratio,
                'iv_metrics': iv_metrics,
                'max_pain': max_pain,
                'unusual': unusual,
                'key_levels': key_levels
            })

        # Calculate aggregate ratios
        agg_volume_ratio = total_put_volume / total_call_volume if total_call_volume > 0 else 0
        agg_oi_ratio = total_put_oi / total_call_oi if total_call_oi > 0 else 0

        # Determine aggregate sentiment
        if agg_volume_ratio < 0.7:
            agg_sentiment = "Very Bullish"
        elif agg_volume_ratio < 0.9:
            agg_sentiment = "Bullish"
        elif agg_volume_ratio < 1.1:
            agg_sentiment = "Neutral"
        elif agg_volume_ratio < 1.3:
            agg_sentiment = "Bearish"
        else:
            agg_sentiment = "Very Bearish"

        # Sort key levels by OI to find most significant
        all_key_levels['calls'] = sorted(all_key_levels['calls'], key=lambda x: x['oi'], reverse=True)[:5]
        all_key_levels['puts'] = sorted(all_key_levels['puts'], key=lambda x: x['oi'], reverse=True)[:5]

        # Format the report
        report = f"""
# OPTIONS MARKET POSITIONING ANALYSIS: {symbol}
## Multi-Expiration Analysis (Next {len(expiration_summaries)} Expirations)

**Current Stock Price:** ${current_price:.2f}
**Expirations Analyzed:** {', '.join([f"{e['date']} ({e['dte']} DTE)" for e in exp_info[:len(expiration_summaries)]])}
**Total Available Expirations:** {len(all_expirations)}

---

## 1. AGGREGATE SENTIMENT (All Expirations Combined)

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Aggregate Volume P/C Ratio | {agg_volume_ratio:.2f} | {agg_sentiment} |
| Aggregate OI P/C Ratio | {agg_oi_ratio:.2f} | {"Bullish" if agg_oi_ratio < 1 else "Bearish"} positioning |

**Total Open Interest:**
- Calls: {total_call_oi:,} contracts
- Puts: {total_put_oi:,} contracts

**Total Volume Today:**
- Calls: {total_call_volume:,} contracts
- Puts: {total_put_volume:,} contracts

---

## 2. EXPIRATION-BY-EXPIRATION BREAKDOWN

"""
        # Add detailed breakdown for each expiration
        for i, summary in enumerate(expiration_summaries):
            exp_date = summary['date']
            dte = summary['dte']
            pc = summary['pc_ratio']
            iv = summary['iv_metrics']
            mp = summary['max_pain']
            ua = summary['unusual']

            term_label = "Near-term" if dte <= 7 else "Short-term" if dte <= 30 else "Medium-term" if dte <= 60 else "Longer-term"

            report += f"""### Expiration {i+1}: {exp_date} ({dte} DTE) - {term_label}

| Metric | Value |
|--------|-------|
| P/C Volume Ratio | {pc['volume_ratio']:.2f} ({pc['volume_sentiment']}) |
| P/C OI Ratio | {pc['oi_ratio']:.2f} |
| ATM IV | {iv.get('atm_iv', 0):.1f}% |
| Expected Move | ±{iv.get('expected_move_pct', 0):.1f}% (±${iv.get('expected_move_dollars', 0):.2f}) |
| Max Pain | ${mp.get('max_pain', 0):.2f} ({mp.get('distance_pct', 0):+.1f}% away) |
| IV Skew | {iv.get('iv_skew', 0):+.2f}% ({iv.get('skew_interpretation', 'N/A')}) |

"""
            # Note unusual activity if present
            if ua.get('has_unusual_activity'):
                report += f"**⚠️ Unusual Activity:** {ua.get('activity_bias', 'Detected')}\n\n"

        report += """---

## 3. MAX PAIN TERM STRUCTURE

Understanding where price may gravitate at each expiration:

| Expiration | DTE | Max Pain | Distance from Current |
|------------|-----|----------|----------------------|
"""
        for mp in all_max_pains:
            report += f"| {mp['date']} | {mp['dte']} | ${mp['max_pain']:.2f} | {mp['distance_pct']:+.1f}% |\n"

        # Analyze max pain trend
        if len(all_max_pains) >= 2:
            near_term_mp = all_max_pains[0]['max_pain']
            far_term_mp = all_max_pains[-1]['max_pain']
            if far_term_mp > near_term_mp * 1.02:
                mp_trend = "**Trend:** Max pain rises over time - suggests upward price drift expected"
            elif far_term_mp < near_term_mp * 0.98:
                mp_trend = "**Trend:** Max pain falls over time - suggests downward price drift expected"
            else:
                mp_trend = "**Trend:** Max pain stable across expirations - range-bound expectations"
            report += f"\n{mp_trend}\n"

        report += """
---

## 4. KEY PRICE LEVELS ACROSS ALL EXPIRATIONS

### Highest Call OI (Resistance Levels)
| Strike | OI | Expiration | DTE | Distance |
|--------|-------|------------|-----|----------|
"""
        for level in all_key_levels['calls'][:5]:
            report += f"| ${level['strike']:.2f} | {level['oi']:,} | {level['expiration']} | {level['dte']} | {level['pct_away']:+.1f}% |\n"

        report += """
### Highest Put OI (Support Levels)
| Strike | OI | Expiration | DTE | Distance |
|--------|-------|------------|-----|----------|
"""
        for level in all_key_levels['puts'][:5]:
            report += f"| ${level['strike']:.2f} | {level['oi']:,} | {level['expiration']} | {level['dte']} | {level['pct_away']:+.1f}% |\n"

        report += """
---

## 5. TERM STRUCTURE INSIGHTS

"""
        # Compare near-term vs longer-term positioning
        if len(expiration_summaries) >= 2:
            near = expiration_summaries[0]
            far = expiration_summaries[-1]

            near_sentiment = near['pc_ratio']['volume_sentiment']
            far_sentiment = far['pc_ratio']['volume_sentiment']

            report += f"**Near-term ({near['date']}):** {near_sentiment} (P/C: {near['pc_ratio']['volume_ratio']:.2f})\n"
            report += f"**Longer-term ({far['date']}):** {far_sentiment} (P/C: {far['pc_ratio']['volume_ratio']:.2f})\n\n"

            # IV term structure
            near_iv = near['iv_metrics'].get('atm_iv', 0)
            far_iv = far['iv_metrics'].get('atm_iv', 0)

            if near_iv > far_iv * 1.1:
                report += "**IV Term Structure:** Backwardation (near-term IV higher) - event/catalyst expected soon\n"
            elif far_iv > near_iv * 1.1:
                report += "**IV Term Structure:** Contango (longer-term IV higher) - uncertainty increases over time\n"
            else:
                report += "**IV Term Structure:** Flat - no significant term structure signal\n"

            # Positioning divergence
            near_oi_ratio = near['pc_ratio']['oi_ratio']
            far_oi_ratio = far['pc_ratio']['oi_ratio']

            if near_oi_ratio < 0.9 and far_oi_ratio > 1.1:
                report += "**Positioning Divergence:** Near-term bullish but longer-term hedged - possible short-term rally then pullback\n"
            elif near_oi_ratio > 1.1 and far_oi_ratio < 0.9:
                report += "**Positioning Divergence:** Near-term bearish but longer-term bullish - possible dip then recovery\n"

        report += """
---

## 6. TRADING IMPLICATIONS

"""
        # Generate comprehensive implications
        implications = []

        # Aggregate sentiment
        if agg_volume_ratio < 0.8:
            implications.append("- **Strong Bullish Positioning:** Aggregate P/C ratio across all expirations is very low")
        elif agg_volume_ratio > 1.2:
            implications.append("- **Strong Bearish/Hedging:** Aggregate P/C ratio across all expirations is elevated")

        # Near-term max pain
        if all_max_pains and abs(all_max_pains[0]['distance_pct']) > 2:
            direction = "up" if all_max_pains[0]['distance_pct'] > 0 else "down"
            implications.append(f"- **Near-term Max Pain:** Price may drift {direction} toward ${all_max_pains[0]['max_pain']:.2f} by {all_max_pains[0]['date']}")

        # Key resistance/support
        if all_key_levels['calls']:
            top_resistance = all_key_levels['calls'][0]
            implications.append(f"- **Key Resistance:** Highest call OI at ${top_resistance['strike']:.2f} ({top_resistance['oi']:,} contracts)")
        if all_key_levels['puts']:
            top_support = all_key_levels['puts'][0]
            implications.append(f"- **Key Support:** Highest put OI at ${top_support['strike']:.2f} ({top_support['oi']:,} contracts)")

        # Unusual activity across expirations
        unusual_exps = [s for s in expiration_summaries if s['unusual'].get('has_unusual_activity')]
        if unusual_exps:
            exp_list = ', '.join([f"{s['date']}" for s in unusual_exps])
            implications.append(f"- **Unusual Activity Alert:** Detected in expirations: {exp_list}")

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
