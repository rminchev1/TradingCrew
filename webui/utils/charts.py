# -------------------------------- charts.py -----------------------

import random
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import pandas as pd
import traceback
import pytz
import yfinance as yf
from typing import Union, List, Optional


def get_yahoo_data(symbol: str, period: str = "1d") -> pd.DataFrame:
    """
    Fetch historical OHLCV data from Yahoo Finance.

    Args:
        symbol: Stock/crypto symbol (e.g., "AAPL", "BTC-USD")
        period: Timeframe period (5m, 15m, 30m, 1h, 4h, 1d, 1w, 1mo, 1y)

    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume
    """
    # Convert crypto symbols from Alpaca format to Yahoo format
    if "/" in symbol:
        symbol = symbol.replace("/", "-")  # BTC/USD -> BTC-USD

    # Map period to yfinance parameters
    # yfinance uses: period (how far back) and interval (bar size)
    period_map = {
        "5m": {"period": "1d", "interval": "1m"},
        "15m": {"period": "5d", "interval": "5m"},
        "30m": {"period": "5d", "interval": "15m"},
        "1h": {"period": "1y", "interval": "30m"},
        "4h": {"period": "2y", "interval": "1h"},
        "1d": {"days_back": 244, "interval": "1d"},  # ~8 months of daily bars
        "1w": {"period": "2y", "interval": "1d"},
        "1mo": {"period": "2y", "interval": "1d"},
        "1y": {"period": "2y", "interval": "1d"},
    }

    params = period_map.get(period.lower(), period_map["1d"])

    try:
        ticker = yf.Ticker(symbol)
        if "days_back" in params:
            from datetime import date
            end_dt = date.today()
            start_dt = end_dt - timedelta(days=params["days_back"])
            df = ticker.history(start=start_dt.isoformat(), end=end_dt.isoformat(), interval=params["interval"])
        else:
            df = ticker.history(period=params["period"], interval=params["interval"])

        if df.empty:
            print(f"[YAHOO] No data returned for {symbol}")
            return pd.DataFrame()

        # Reset index to get timestamp as a column
        df = df.reset_index()

        # The index column name varies: 'Date' for daily, 'Datetime' for intraday
        # Find the datetime column
        datetime_col = None
        for col in df.columns:
            if col in ['Date', 'Datetime', 'index']:
                datetime_col = col
                break

        if datetime_col:
            df = df.rename(columns={datetime_col: 'timestamp'})

        # Rename OHLCV columns (they are capitalized in yfinance)
        df = df.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })

        # Keep only required columns
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        available_cols = [col for col in required_cols if col in df.columns]
        df = df[available_cols]

        return df

    except Exception as e:
        print(f"[YAHOO] Error fetching data for {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate technical indicators and add them as columns to the DataFrame.

    Indicators added:
    - SMA_20, SMA_50: Simple Moving Averages
    - EMA_12, EMA_26: Exponential Moving Averages
    - BB_upper, BB_mid, BB_lower: Bollinger Bands (20-period, 2 std)
    - RSI: Relative Strength Index (14-period)
    - MACD, MACD_signal, MACD_hist: MACD (12/26/9)
    """
    if df.empty or 'close' not in df.columns:
        return df

    df = df.copy()

    # Moving Averages
    df['SMA_20'] = df['close'].rolling(window=20, min_periods=1).mean()
    df['SMA_50'] = df['close'].rolling(window=50, min_periods=1).mean()
    df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean()

    # Bollinger Bands (20-period, 2 standard deviations)
    df['BB_mid'] = df['close'].rolling(window=20, min_periods=1).mean()
    df['BB_std'] = df['close'].rolling(window=20, min_periods=1).std()
    df['BB_upper'] = df['BB_mid'] + 2 * df['BB_std']
    df['BB_lower'] = df['BB_mid'] - 2 * df['BB_std']

    # RSI (14-period)
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
    rs = gain / loss.replace(0, float('nan'))
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RSI'] = df['RSI'].fillna(50)  # Fill NaN with neutral value

    # MACD (12/26/9)
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']

    # OBV (On-Balance Volume)
    obv = [0]
    for i in range(1, len(df)):
        if df['close'].iloc[i] > df['close'].iloc[i - 1]:
            obv.append(obv[-1] + df['volume'].iloc[i])
        elif df['close'].iloc[i] < df['close'].iloc[i - 1]:
            obv.append(obv[-1] - df['volume'].iloc[i])
        else:
            obv.append(obv[-1])
    df['OBV'] = obv

    return df


def create_chart(
    ticker: str,
    period: str = "1y",
    end_date: Union[str, datetime] = None,
    indicators: Optional[List[str]] = None
):
    """
    Create a Plotly candlestick chart with technical indicators for a given ticker and period.
    Uses Yahoo Finance for data. Falls back to demo data if API fails.

    Args:
        ticker: Stock/crypto symbol
        period: Timeframe period (5m, 15m, 30m, 1h, 4h, 1d, 1w, 1mo, 1y)
        end_date: End date for the data (not used with Yahoo Finance, kept for compatibility)
        indicators: List of indicators to show ('sma', 'ema', 'bb', 'rsi', 'macd')
    """
    # Default indicators if none specified
    if indicators is None:
        indicators = ['sma', 'bb', 'rsi', 'macd']

    # Normalize indicator names
    indicators = [ind.lower() for ind in indicators]

    # Determine if we need RSI and/or MACD subplots
    show_rsi = 'rsi' in indicators
    show_macd = 'macd' in indicators

    # Fetch data from Yahoo Finance
    df = get_yahoo_data(ticker, period)

    # if we got no data, make a demo chart
    if df.empty:
        return create_demo_chart(ticker, period, end_date, error_msg="No data returned from Yahoo Finance.", indicators=indicators)

    # Add technical indicators
    df = add_indicators(df)

    # Build the chart with subplots
    return _build_chart_figure(df, ticker, period, end_date, indicators, show_rsi, show_macd)


def _build_chart_figure(
    df: pd.DataFrame,
    ticker: str,
    period: str,
    end_date,
    indicators: List[str],
    show_rsi: bool,
    show_macd: bool
):
    """Build the Plotly figure with subplots for price, volume, RSI, and MACD."""

    # Calculate number of rows needed
    num_rows = 1  # Main price chart (includes volume)
    if show_rsi:
        num_rows += 1
    if show_macd:
        num_rows += 1

    # Calculate row heights based on what's shown
    if num_rows == 1:
        row_heights = [1.0]
    elif num_rows == 2:
        row_heights = [0.7, 0.3]
    else:  # 3 rows
        row_heights = [0.55, 0.22, 0.23]

    # Create specs for each row
    specs = [[{"secondary_y": True}]]  # First row always has secondary y for volume
    for _ in range(num_rows - 1):
        specs.append([{"secondary_y": False}])

    fig = make_subplots(
        rows=num_rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
        specs=specs
    )

    # Row 1: Candlestick + Volume + Overlays
    # Add volume bars first with lower opacity
    colors = ['rgba(0,150,0,0.3)' if close >= open else 'rgba(255,0,0,0.3)'
              for close, open in zip(df['close'], df['open'])]
    fig.add_trace(
        go.Bar(
            x=df['timestamp'],
            y=df['volume'],
            name='Volume',
            marker_color=colors,
            showlegend=True
        ),
        row=1, col=1, secondary_y=True
    )

    # Add candlestick trace
    fig.add_trace(
        go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Price',
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350'
        ),
        row=1, col=1, secondary_y=False
    )

    # Add Moving Averages if selected
    if 'sma' in indicators:
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['SMA_20'],
                name='SMA(20)',
                line=dict(color='#2196f3', width=1),
                hovertemplate='SMA(20): %{y:.2f}<extra></extra>'
            ),
            row=1, col=1, secondary_y=False
        )
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['SMA_50'],
                name='SMA(50)',
                line=dict(color='#ff9800', width=1),
                hovertemplate='SMA(50): %{y:.2f}<extra></extra>'
            ),
            row=1, col=1, secondary_y=False
        )

    if 'ema' in indicators:
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['EMA_12'],
                name='EMA(12)',
                line=dict(color='#9c27b0', width=1, dash='dot'),
                hovertemplate='EMA(12): %{y:.2f}<extra></extra>'
            ),
            row=1, col=1, secondary_y=False
        )
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['EMA_26'],
                name='EMA(26)',
                line=dict(color='#e91e63', width=1, dash='dot'),
                hovertemplate='EMA(26): %{y:.2f}<extra></extra>'
            ),
            row=1, col=1, secondary_y=False
        )

    # Add Bollinger Bands if selected
    if 'bb' in indicators:
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['BB_upper'],
                name='BB Upper',
                line=dict(color='rgba(128,128,128,0.5)', width=1, dash='dash'),
                hovertemplate='BB Upper: %{y:.2f}<extra></extra>'
            ),
            row=1, col=1, secondary_y=False
        )
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['BB_lower'],
                name='BB Lower',
                line=dict(color='rgba(128,128,128,0.5)', width=1, dash='dash'),
                fill='tonexty',
                fillcolor='rgba(128,128,128,0.1)',
                hovertemplate='BB Lower: %{y:.2f}<extra></extra>'
            ),
            row=1, col=1, secondary_y=False
        )

    current_row = 2

    # Row 2 (or 2): RSI if selected
    if show_rsi:
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['RSI'],
                name='RSI(14)',
                line=dict(color='#7c4dff', width=1.5),
                hovertemplate='RSI: %{y:.1f}<extra></extra>'
            ),
            row=current_row, col=1
        )
        # Add overbought/oversold lines
        fig.add_hline(y=70, line_dash="dash", line_color="rgba(255,0,0,0.5)",
                      line_width=1, row=current_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="rgba(0,255,0,0.5)",
                      line_width=1, row=current_row, col=1)
        fig.add_hline(y=50, line_dash="dot", line_color="rgba(128,128,128,0.3)",
                      line_width=1, row=current_row, col=1)

        # Update RSI y-axis
        fig.update_yaxes(
            title_text="RSI",
            range=[0, 100],
            row=current_row, col=1,
            tickvals=[30, 50, 70],
            gridcolor='rgba(128,128,128,0.1)'
        )
        current_row += 1

    # Row 3 (or 2): MACD if selected
    if show_macd:
        # MACD histogram
        colors = ['#26a69a' if val >= 0 else '#ef5350' for val in df['MACD_hist']]
        fig.add_trace(
            go.Bar(
                x=df['timestamp'],
                y=df['MACD_hist'],
                name='MACD Hist',
                marker_color=colors,
                hovertemplate='Histogram: %{y:.4f}<extra></extra>'
            ),
            row=current_row, col=1
        )
        # MACD line
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['MACD'],
                name='MACD',
                line=dict(color='#2196f3', width=1.5),
                hovertemplate='MACD: %{y:.4f}<extra></extra>'
            ),
            row=current_row, col=1
        )
        # Signal line
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['MACD_signal'],
                name='Signal',
                line=dict(color='#ff9800', width=1.5),
                hovertemplate='Signal: %{y:.4f}<extra></extra>'
            ),
            row=current_row, col=1
        )
        # Zero line
        fig.add_hline(y=0, line_dash="dot", line_color="rgba(128,128,128,0.5)",
                      line_width=1, row=current_row, col=1)

        # Update MACD y-axis
        fig.update_yaxes(
            title_text="MACD",
            row=current_row, col=1,
            gridcolor='rgba(128,128,128,0.1)'
        )

    # Build title
    title = f"{ticker} - {period.upper()} Chart"
    if end_date:
        title += f" (as of {pd.to_datetime(end_date).date()})"

    # Configure rangebreaks for stocks (not crypto)
    rangebreaks = []
    if "/" not in ticker:  # Only apply to stocks, not crypto
        if period.lower() in ["5m", "15m", "30m", "1h"]:
            # For intraday charts, hide non-trading hours
            rangebreaks = [
                dict(bounds=["sat", "mon"]),  # Hide weekends
                dict(bounds=[20, 9.5], pattern="hour"),  # Hide non-trading hours
            ]
        elif period.lower() in ["4h", "1d"]:
            # For shorter daily charts, only hide weekends
            rangebreaks = [
                dict(bounds=["sat", "mon"]),  # Hide weekends
            ]
        # For 1w, 1mo, 1y charts, no rangebreaks to avoid issues with daily data

    # Calculate chart height based on number of rows
    chart_height = 400 + (num_rows - 1) * 120

    # Update layout
    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor='center'),
        template="plotly_white",
        height=chart_height,
        margin=dict(l=50, r=50, t=50, b=40),
        autosize=True,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10)
        ),
        hovermode='x unified',
        xaxis=dict(
            type='date',
            rangeslider_visible=True,
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1d", step="day", stepmode="backward"),
                    dict(count=7, label="1w", step="day", stepmode="backward"),
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=3, label="3m", step="month", stepmode="backward"),
                    dict(step="all", label="All")
                ]),
                x=0,
                y=1.15
            ),
            rangebreaks=rangebreaks
        ),
        xaxis_rangeslider=dict(
            visible=True,
            thickness=0.05
        )
    )

    # Update y-axes
    fig.update_yaxes(title_text="Price", row=1, col=1, secondary_y=False, gridcolor='rgba(128,128,128,0.1)')
    fig.update_yaxes(title_text="Volume", row=1, col=1, secondary_y=True, showgrid=False)

    # Update x-axis for all rows to hide them except the last one
    for i in range(1, num_rows):
        fig.update_xaxes(showticklabels=False, row=i, col=1)
    fig.update_xaxes(showticklabels=True, row=num_rows, col=1)

    return fig


def create_demo_chart(
    ticker,
    period="1y",
    end_date=None,
    error_msg=None,
    indicators: Optional[List[str]] = None
):
    """Create a demo chart with random walk data"""
    # Default indicators if none specified
    if indicators is None:
        indicators = ['sma', 'bb', 'rsi', 'macd']
    indicators = [ind.lower() for ind in indicators]

    show_rsi = 'rsi' in indicators
    show_macd = 'macd' in indicators

    # Updated points mapping to reflect new timeframes
    points_map = {
        "5m": 390,   # 1 trading day of 1-min bars
        "15m": 156,  # 2 days of 5-min bars
        "30m": 130,  # 5 days of 15-min bars
        "1h": 130,   # 10 days of 30-min bars
        "4h": 180,   # 30 days of 1-hour bars
        "1d": 252,   # 252 trading days (~12 months)
        "1w": 252,   # 252 trading days (~12 months)
        "1mo": 252,  # 252 trading days (~1 year)
        "1y": 504    # 504 trading days (~2 years)
    }
    points = points_map.get(period.lower(), 252)

    title_map = {
        "5m": "5 Minutes",
        "15m": "15 Minutes",
        "30m": "30 Minutes",
        "1h": "1 Hour",
        "4h": "4 Hours",
        "1d": "1 Day",
        "1w": "1 Week",
        "1mo": "1 Month",
        "1y": "1 Year"
    }
    title = f"{ticker} - {title_map.get(period.lower(), period)} Chart (Demo)"
    if end_date:
        title += f" (as of {end_date})"

    # Generate demo data
    end_dt = pd.to_datetime(end_date) if end_date else datetime.now()
    dates = pd.date_range(end=end_dt, periods=points)
    prices = [100 + random.uniform(-20, 20)]
    for _ in range(1, points):
        delta = random.uniform(-2, 2) + random.uniform(-0.5, 0.7)
        prices.append(max(5, prices[-1] + delta))

    opens, highs, lows, closes, vols = [], [], [], prices.copy(), []
    for i, close in enumerate(closes):
        opens.append(closes[i-1] if i > 0 else close)
        high = max(opens[i], close) + random.uniform(0.1, 1)
        low = min(opens[i], close) - random.uniform(0.1, 1)
        vols.append(random.randint(100000, 10000000))
        highs.append(high)
        lows.append(low)

    # Create DataFrame
    df = pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': vols
    })

    # Add indicators
    df = add_indicators(df)

    # Build chart figure
    fig = _build_chart_figure(df, ticker, period, end_date, indicators, show_rsi, show_macd)

    # Add demo data annotation
    if error_msg:
        fig.add_annotation(
            x=0.5, y=0.5, xref='paper', yref='paper',
            text=f"DEMO DATA: {error_msg}",
            showarrow=False,
            font=dict(color='red', size=12),
            bgcolor='rgba(255,255,255,0.7)',
            bordercolor='red',
            borderwidth=1
        )

    return fig


def create_welcome_chart():
    """Create a welcome chart when no symbol is selected."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0, 1, 2, 3], y=[1, 3, 2, 4], mode='lines', name='Welcome'))
    fig.update_layout(
        title="Welcome to TradingAgents",
        template="plotly_white",
        annotations=[
            dict(
                x=1.5, y=2.5, xref='x', yref='y',
                text="Enter a ticker symbol and click 'Start Analysis'",
                showarrow=True, arrowhead=1, ax=0, ay=-40
            )
        ],
        height=400,
        margin=dict(l=40, r=40, t=40, b=40),
        autosize=True
    )
    return fig
