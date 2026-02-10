"""
Chart data transformation utilities for TradingView lightweight-charts.

Converts pandas DataFrames to the JSON format required by lightweight-charts.
"""

import pandas as pd
from typing import List, Optional, Dict, Any


def transform_candlestick_data(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Convert DataFrame to lightweight-charts candlestick format.

    Args:
        df: DataFrame with columns: timestamp, open, high, low, close

    Returns:
        List of dicts: [{time: unix_ts, open, high, low, close}, ...]
    """
    if df.empty or 'timestamp' not in df.columns:
        return []

    data = []
    for _, row in df.iterrows():
        ts = row['timestamp']
        # Convert to Unix timestamp in seconds
        if isinstance(ts, pd.Timestamp):
            time_val = int(ts.timestamp())
        else:
            time_val = int(pd.to_datetime(ts).timestamp())

        data.append({
            'time': time_val,
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close'])
        })

    return data


def transform_volume_data(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Convert DataFrame to lightweight-charts volume histogram format.

    Args:
        df: DataFrame with columns: timestamp, open, close, volume

    Returns:
        List of dicts: [{time: unix_ts, value, color}, ...]
    """
    if df.empty or 'timestamp' not in df.columns or 'volume' not in df.columns:
        return []

    data = []
    for _, row in df.iterrows():
        ts = row['timestamp']
        if isinstance(ts, pd.Timestamp):
            time_val = int(ts.timestamp())
        else:
            time_val = int(pd.to_datetime(ts).timestamp())

        # Green for up candles, red for down candles
        is_up = row['close'] >= row['open']
        color = 'rgba(38, 166, 154, 0.5)' if is_up else 'rgba(239, 83, 80, 0.5)'

        data.append({
            'time': time_val,
            'value': float(row['volume']),
            'color': color
        })

    return data


def transform_line_series(df: pd.DataFrame, column: str) -> List[Dict[str, Any]]:
    """
    Convert a DataFrame column to lightweight-charts line series format.

    Args:
        df: DataFrame with timestamp column and the specified data column
        column: Name of the column to extract

    Returns:
        List of dicts: [{time: unix_ts, value}, ...]
    """
    if df.empty or 'timestamp' not in df.columns or column not in df.columns:
        return []

    data = []
    for _, row in df.iterrows():
        value = row[column]
        # Skip NaN values
        if pd.isna(value):
            continue

        ts = row['timestamp']
        if isinstance(ts, pd.Timestamp):
            time_val = int(ts.timestamp())
        else:
            time_val = int(pd.to_datetime(ts).timestamp())

        data.append({
            'time': time_val,
            'value': float(value)
        })

    return data


def prepare_chart_data(
    df: pd.DataFrame,
    indicators: Optional[List[str]] = None,
    symbol: str = "",
    period: str = ""
) -> Dict[str, Any]:
    """
    Main function to prepare all chart data for lightweight-charts.

    Args:
        df: DataFrame with OHLCV data and calculated indicators
        indicators: List of indicator names to include ('sma', 'ema', 'bb', 'rsi', 'macd')
        symbol: The ticker symbol
        period: The timeframe period

    Returns:
        Dict containing all series data in JSON-serializable format:
        {
            'symbol': str,
            'period': str,
            'candlestick': [...],
            'volume': [...],
            'sma20': [...],
            'sma50': [...],
            'ema12': [...],
            'ema26': [...],
            'bbUpper': [...],
            'bbLower': [...],
            'rsi': [...],
            'macd': [...],
            'macdSignal': [...],
            'macdHist': [...]
        }
    """
    if indicators is None:
        indicators = ['sma', 'bb']

    # Normalize indicator names
    indicators = [ind.lower() for ind in indicators]

    result = {
        'symbol': symbol,
        'period': period,
        'candlestick': transform_candlestick_data(df),
        'volume': transform_volume_data(df),
    }

    # Add SMA lines if requested
    if 'sma' in indicators:
        result['sma20'] = transform_line_series(df, 'SMA_20')
        result['sma50'] = transform_line_series(df, 'SMA_50')

    # Add EMA lines if requested
    if 'ema' in indicators:
        result['ema12'] = transform_line_series(df, 'EMA_12')
        result['ema26'] = transform_line_series(df, 'EMA_26')

    # Add Bollinger Bands if requested
    if 'bb' in indicators:
        result['bbUpper'] = transform_line_series(df, 'BB_upper')
        result['bbLower'] = transform_line_series(df, 'BB_lower')

    # Add RSI if requested (for future Phase 2)
    if 'rsi' in indicators:
        result['rsi'] = transform_line_series(df, 'RSI')

    # Add MACD if requested
    if 'macd' in indicators:
        result['macd'] = transform_line_series(df, 'MACD')
        result['macdSignal'] = transform_line_series(df, 'MACD_signal')
        # MACD histogram needs special handling for colors
        if 'MACD_hist' in df.columns:
            macd_hist_data = []
            for _, row in df.iterrows():
                value = row['MACD_hist']
                if pd.isna(value):
                    continue
                ts = row['timestamp']
                if isinstance(ts, pd.Timestamp):
                    time_val = int(ts.timestamp())
                else:
                    time_val = int(pd.to_datetime(ts).timestamp())

                color = '#26a69a' if value >= 0 else '#ef5350'
                macd_hist_data.append({
                    'time': time_val,
                    'value': float(value),
                    'color': color
                })
            result['macdHist'] = macd_hist_data

    # Add OBV if requested
    if 'obv' in indicators:
        result['obv'] = transform_line_series(df, 'OBV')

    return result
