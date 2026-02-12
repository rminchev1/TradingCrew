# alpaca_utils.py

import os
import re
import time
import random
import pandas as pd
from datetime import datetime, timedelta
from typing import Annotated, Union, Optional, List
from alpaca.data.historical import StockHistoricalDataClient, CryptoHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, CryptoBarsRequest, StockLatestQuoteRequest, CryptoLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.data.enums import DataFeed
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    GetAssetsRequest,
    GetOrdersRequest,
    MarketOrderRequest,
    ClosePositionRequest,
    LimitOrderRequest,
    StopOrderRequest,
    TakeProfitRequest,
    StopLossRequest,
)
from alpaca.trading.enums import AssetClass, OrderSide, TimeInForce, OrderClass
from .config import get_api_key
from .external_data_logger import log_external_error, ExternalSystem


# Fallback dictionary for company names
ticker_to_company_fallback = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "GOOGL": "Google",
    "AMZN": "Amazon",
    "TSLA": "Tesla",
    "NVDA": "Nvidia",
    "TSM": "Taiwan Semiconductor Manufacturing Company OR TSMC",
    "JPM": "JPMorgan Chase OR JP Morgan",
    "JNJ": "Johnson & Johnson OR JNJ",
    "V": "Visa",
    "WMT": "Walmart",
    "META": "Meta OR Facebook",
    "AMD": "AMD",
    "INTC": "Intel",
    "QCOM": "Qualcomm",
    "BABA": "Alibaba",
    "ADBE": "Adobe",
    "NFLX": "Netflix",
    "CRM": "Salesforce",
    "PYPL": "PayPal",
    "PLTR": "Palantir",
    "MU": "Micron",
    "SQ": "Block OR Square",
    "ZM": "Zoom",
    "CSCO": "Cisco",
    "SHOP": "Shopify",
    "ORCL": "Oracle",
    "X": "Twitter OR X",
    "SPOT": "Spotify",
    "AVGO": "Broadcom",
    "ASML": "ASML ",
    "TWLO": "Twilio",
    "SNAP": "Snap Inc.",
    "TEAM": "Atlassian",
    "SQSP": "Squarespace",
    "UBER": "Uber",
    "ROKU": "Roku",
    "PINS": "Pinterest",
}


def get_alpaca_stock_client() -> StockHistoricalDataClient:
    api_key = get_api_key("alpaca_api_key", "ALPACA_API_KEY")
    api_secret = get_api_key("alpaca_secret_key", "ALPACA_SECRET_KEY")
    if not api_key or not api_secret:
        print(f"Warning: Missing Alpaca API credentials. API key: {'present' if api_key else 'missing'}, Secret: {'present' if api_secret else 'missing'}")
        raise ValueError("Alpaca API key or secret not found. Please set ALPACA_API_KEY and ALPACA_SECRET_KEY.")
    try:
        return StockHistoricalDataClient(api_key, api_secret)
    except Exception as e:
        print(f"Error creating Alpaca stock client: {e}")
        raise


def get_alpaca_crypto_client() -> CryptoHistoricalDataClient:
    api_key = get_api_key("alpaca_api_key", "ALPACA_API_KEY")
    api_secret = get_api_key("alpaca_secret_key", "ALPACA_SECRET_KEY")
    # Crypto calls work without keys, but keys raise rate limits
    if api_key and api_secret:
        return CryptoHistoricalDataClient(api_key, api_secret)
    else:
        return CryptoHistoricalDataClient()


def get_alpaca_trading_client() -> TradingClient:
    api_key = get_api_key("alpaca_api_key", "ALPACA_API_KEY")
    api_secret = get_api_key("alpaca_secret_key", "ALPACA_SECRET_KEY")
    if not api_key or not api_secret:
        raise ValueError("Alpaca API key or secret not found. Please set ALPACA_API_KEY and ALPACA_SECRET_KEY.")
    return TradingClient(api_key, api_secret, paper=True)


def is_options_symbol(symbol: str) -> bool:
    """
    Check if a symbol is an options contract (OCC format).

    OCC format: SYMBOL (1-6 chars) + YYMMDD (6) + C/P (1) + Strike*1000 (8)
    Example: AAPL240315C00200000
    Total length: 15-21 characters

    Args:
        symbol: The symbol to check

    Returns:
        True if the symbol matches OCC options format
    """
    import re
    if not symbol or len(symbol) < 15:
        return False

    # OCC pattern: 1-6 letter underlying + 6 digit date + C or P + 8 digit strike
    occ_pattern = r'^[A-Z]{1,6}\d{6}[CP]\d{8}$'
    return bool(re.match(occ_pattern, symbol.upper()))


def _parse_timeframe(tf: Union[str, TimeFrame]) -> TimeFrame:
    """Convert a string like '5Min' or a TimeFrame instance into a TimeFrame."""
    if isinstance(tf, TimeFrame):
        return tf

    tf = tf.strip()
    
    # mapping common strings
    if tf.lower() == "1min":
        result = TimeFrame.Minute
    elif tf.lower().endswith("min"):
        # e.g. "5Min", "15min"
        amount = int(tf[:-3])
        result = TimeFrame(amount, TimeFrameUnit.Minute)
    elif tf.lower() == "1hour":
        result = TimeFrame.Hour
    elif tf.lower().endswith("hour"):
        amount = int(tf[:-4])
        result = TimeFrame(amount, TimeFrameUnit.Hour)
    elif tf.lower() == "1day":
        result = TimeFrame.Day
    elif tf.lower().endswith("day"):
        amount = int(tf[:-3])
        result = TimeFrame(amount, TimeFrameUnit.Day)
    else:
        # fallback
        result = TimeFrame.Day
    
    return result


class AlpacaUtils:

    @staticmethod
    def get_stock_data(
        symbol: str,
        start_date: Union[str, datetime],
        end_date: Optional[Union[str, datetime]] = None,
        timeframe: Union[str, TimeFrame] = "1Day",
        save_path: Optional[str] = None,
        feed: DataFeed = DataFeed.IEX
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data for a stock or crypto symbol.

        Args:
            symbol: The ticker symbol (e.g. "SPY" or "BTC/USD")
            start_date: 'YYYY-MM-DD' string or datetime
            end_date: optional 'YYYY-MM-DD' string or datetime
            timeframe: e.g. "1Min","5Min","15Min","1Hour","1Day" or a TimeFrame instance
            save_path: if provided, path to write a CSV
            feed: DataFeed enum (default IEX)

        Returns:
            pandas DataFrame with columns ['timestamp','open','high','low','close','volume']
        """
        # normalize dates
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date) + timedelta(days=1) if end_date else None

        tf = _parse_timeframe(timeframe)

        # choose client
        is_crypto = "/" in symbol
        client = get_alpaca_crypto_client() if is_crypto else get_alpaca_stock_client()

        # build request params; always use a list for symbol_or_symbols
        params = (
            CryptoBarsRequest(
                symbol_or_symbols=[symbol],
                timeframe=tf,
                start=start,
                end=end,
                feed=feed
            ) if is_crypto else
            StockBarsRequest(
                symbol_or_symbols=[symbol],
                timeframe=tf,
                start=start,
                end=end,
                feed=feed
            )
        )

        # Retry logic for transient connection errors (SSL, network issues)
        max_retries = 3
        base_delay = 1.0  # seconds

        for attempt in range(max_retries):
            try:
                bars = client.get_crypto_bars(params) if is_crypto else client.get_stock_bars(params)
                # convert to DataFrame via the .df property
                df = bars.df.reset_index()  # multi-index ['symbol','timestamp']

                # filter for our symbol (in case of list) - only if symbol column exists
                if "symbol" in df.columns:
                    df = df[df["symbol"] == symbol].drop(columns="symbol")
                else:
                    # If no symbol column, assume all data is for the requested symbol
                    pass

                if save_path:
                    df.to_csv(save_path, index=False)
                return df

            except Exception as e:
                error_str = str(e)
                # Retry on SSL/connection errors
                is_retryable = any(err in error_str for err in [
                    "SSLError", "SSL:", "ConnectionError", "Max retries exceeded",
                    "EOF occurred", "Connection reset", "Connection refused"
                ])

                if is_retryable and attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"[ALPACA] Retry {attempt + 1}/{max_retries} for {symbol} after {delay:.1f}s: {e}")
                    time.sleep(delay)
                else:
                    log_external_error(
                        system="alpaca",
                        operation="get_stock_data",
                        error=e,
                        symbol=symbol,
                        params={"start_date": str(start), "timeframe": str(tf)}
                    )
                    return pd.DataFrame()

    @staticmethod
    def get_latest_quote(symbol: str) -> dict:
        """
        Get the latest bid/ask quote for a symbol.
        """
        is_crypto = "/" in symbol
        client = get_alpaca_crypto_client() if is_crypto else get_alpaca_stock_client()
        req = CryptoLatestQuoteRequest(symbol_or_symbols=[symbol]) if is_crypto else StockLatestQuoteRequest(symbol_or_symbols=[symbol])
        try:
            resp = client.get_crypto_latest_quote(req) if is_crypto else client.get_stock_latest_quote(req)
            quote = resp[symbol]
            return {
                "symbol": symbol,
                "bid_price": quote.bid_price,
                "bid_size": quote.bid_size,
                "ask_price": quote.ask_price,
                "ask_size": quote.ask_size,
                "timestamp": quote.timestamp
            }
        except Exception as e:
            log_external_error(
                system="alpaca",
                operation="get_latest_quote",
                error=e,
                symbol=symbol
            )
            return {}

    
    @staticmethod
    def get_stock_data_window(
        symbol: Annotated[str, "ticker symbol"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"] = None,
        look_back_days: Annotated[int, "Number of days to look back"] = 30,
        timeframe: Annotated[str, "Timeframe for data: 1Min, 5Min, 15Min, 1Hour, 1Day"] = "1Day",
    ) -> pd.DataFrame:
        """
        Fetches historical stock data from Alpaca for the specified symbol and a window of days.
        
        Args:
            symbol: The stock ticker symbol
            curr_date: Current date in yyyy-mm-dd format (optional - if not provided, will use today's date)
            look_back_days: Number of days to look back
            timeframe: Timeframe for data (1Min, 5Min, 15Min, 1Hour, 1Day)
            
        Returns:
            DataFrame containing the historical stock data
        """
        # Calculate start date based on look_back_days
        if curr_date:
            curr_dt = pd.to_datetime(curr_date)
        else:
            curr_dt = pd.to_datetime(datetime.now().strftime("%Y-%m-%d"))
            
        start_dt = curr_dt - pd.Timedelta(days=look_back_days)
        
        # Don't pass end_date to avoid subscription limitations
        return AlpacaUtils.get_stock_data(
            symbol=symbol,
            start_date=start_dt.strftime("%Y-%m-%d"),
            timeframe=timeframe
        ) 

    @staticmethod
    def get_company_name(symbol: str) -> str:
        """
        Get company name for a ticker symbol using Alpaca API.
        
        Args:
            symbol: The ticker symbol (e.g. "AAPL")
            
        Returns:
            Company name as string or original symbol if not found
        """
        try:
            # Skip crypto or symbols with special characters
            if "/" in symbol:
                return symbol
                
            client = get_alpaca_trading_client()
            asset = client.get_asset(symbol)
            
            if asset and hasattr(asset, 'name') and asset.name:
                return asset.name
            else:
                # Use fallback if name is not available
                print(f"No company name found for {symbol} via API, using fallback.")
                return ticker_to_company_fallback.get(symbol, symbol)
                
        except Exception as e:
            log_external_error(
                system="alpaca",
                operation="get_company_name",
                error=e,
                symbol=symbol
            )
            return ticker_to_company_fallback.get(symbol, symbol) 

    @staticmethod
    def get_positions_data():
        """Get current stock positions from Alpaca account (excludes options)"""
        try:
            client = get_alpaca_trading_client()
            positions = client.get_all_positions()

            # Convert positions to a list of dictionaries (filter out options)
            positions_data = []
            for position in positions:
                # Skip options contracts
                if is_options_symbol(position.symbol):
                    continue
                current_price = float(position.current_price)
                avg_entry_price = float(position.avg_entry_price)
                qty = float(position.qty)
                market_value = float(position.market_value)
                cost_basis = avg_entry_price * qty
                
                # Calculate P/L values
                today_pl_dollars = float(position.unrealized_intraday_pl)
                total_pl_dollars = float(position.unrealized_pl)
                today_pl_percent = (today_pl_dollars / cost_basis) * 100 if cost_basis != 0 else 0
                total_pl_percent = (total_pl_dollars / cost_basis) * 100 if cost_basis != 0 else 0
                
                positions_data.append({
                    "Symbol": position.symbol,
                    "Qty": qty,
                    "Market Value": f"${market_value:.2f}",
                    "Avg Entry": f"${avg_entry_price:.2f}",
                    "Cost Basis": f"${cost_basis:.2f}",
                    "Today's P/L (%)": f"{today_pl_percent:.2f}%",
                    "Today's P/L ($)": f"${today_pl_dollars:.2f}",
                    "Total P/L (%)": f"{total_pl_percent:.2f}%",
                    "Total P/L ($)": f"${total_pl_dollars:.2f}"
                })
            
            return positions_data
        except Exception as e:
            log_external_error(
                system="alpaca",
                operation="get_positions_data",
                error=e
            )
            return []

    @staticmethod
    def get_recent_orders(page=1, page_size=7, return_total=False):
        """Get recent orders from Alpaca account, with simple pagination.

        Args:
            page: Page number (1-indexed)
            page_size: Number of orders per page
            return_total: If True, returns (orders, total_count) tuple
        """
        try:
            client = get_alpaca_trading_client()
            # Fetch enough orders to know total (max 100 for reasonable performance)
            max_fetch = 100
            req = GetOrdersRequest(status="all", limit=max_fetch, nested=False)
            orders_page = client.get_orders(req)
            # Filter out options orders
            orders = [o for o in orders_page if o.symbol and not is_options_symbol(o.symbol)]
            total_count = len(orders)

            # Convert orders to a list of dictionaries
            orders_data = []
            for order in orders:
                qty = float(order.qty) if order.qty is not None else 0.0
                filled_qty = float(order.filled_qty) if order.filled_qty is not None else 0.0
                filled_avg_price = float(order.filled_avg_price) if order.filled_avg_price is not None else 0.0

                # Format order date/time
                order_date = ""
                if order.created_at:
                    order_date = order.created_at.strftime("%m/%d %H:%M")

                # Get order ID (short version for display)
                order_id = str(order.id) if order.id else "-"
                order_id_short = order_id[:8] if len(order_id) > 8 else order_id

                orders_data.append({
                    "Asset": order.symbol,
                    "Order Type": order.type,
                    "Side": order.side,
                    "Qty": qty,
                    "Filled Qty": filled_qty,
                    "Avg. Fill Price": f"${filled_avg_price:.2f}" if filled_avg_price > 0 else "-",
                    "Status": order.status,
                    "Source": order.client_order_id,
                    "Date": order_date,
                    "Order ID": order_id,
                    "Order ID Short": order_id_short
                })

            # Slice out the exact page we want (newest first)
            start = (page - 1) * page_size
            page_data = orders_data[start : start + page_size]

            if return_total:
                return page_data, total_count
            return page_data

        except Exception as e:
            log_external_error(
                system="alpaca",
                operation="get_recent_orders",
                error=e,
                params={"page": page, "page_size": page_size}
            )
            if return_total:
                return [], 0
            return []

    @staticmethod
    def get_options_positions_data():
        """Get current options positions from Alpaca account"""
        try:
            client = get_alpaca_trading_client()
            positions = client.get_all_positions()

            # Convert options positions to a list of dictionaries
            positions_data = []
            for position in positions:
                # Only include options contracts
                if not is_options_symbol(position.symbol):
                    continue

                current_price = float(position.current_price)
                avg_entry_price = float(position.avg_entry_price)
                qty = float(position.qty)
                market_value = float(position.market_value)
                cost_basis = avg_entry_price * abs(qty)

                # Calculate P/L values
                today_pl_dollars = float(position.unrealized_intraday_pl)
                total_pl_dollars = float(position.unrealized_pl)
                today_pl_percent = (today_pl_dollars / cost_basis) * 100 if cost_basis != 0 else 0
                total_pl_percent = (total_pl_dollars / cost_basis) * 100 if cost_basis != 0 else 0

                # Parse OCC symbol for display
                from .options_trading_utils import parse_occ_symbol
                try:
                    parsed = parse_occ_symbol(position.symbol)
                    underlying = parsed.get("underlying", position.symbol[:4])
                    contract_type = parsed.get("contract_type", "unknown").upper()
                    strike = parsed.get("strike", 0)
                    expiration = parsed.get("expiration", "")
                except:
                    underlying = position.symbol[:4]
                    contract_type = "OPT"
                    strike = 0
                    expiration = ""

                positions_data.append({
                    "Symbol": position.symbol,
                    "Underlying": underlying,
                    "Type": contract_type,
                    "Strike": f"${strike:.2f}" if strike else "-",
                    "Expiration": expiration,
                    "Qty": int(qty),
                    "Market Value": f"${market_value:.2f}",
                    "Avg Entry": f"${avg_entry_price:.2f}",
                    "Current Price": f"${current_price:.2f}",
                    "Today's P/L (%)": f"{today_pl_percent:.2f}%",
                    "Today's P/L ($)": f"${today_pl_dollars:.2f}",
                    "Total P/L (%)": f"{total_pl_percent:.2f}%",
                    "Total P/L ($)": f"${total_pl_dollars:.2f}"
                })

            return positions_data
        except Exception as e:
            log_external_error(
                system="alpaca",
                operation="get_options_positions_data",
                error=e
            )
            return []

    @staticmethod
    def get_options_orders(page=1, page_size=7, return_total=False):
        """Get recent options orders from Alpaca account, with simple pagination.

        Args:
            page: Page number (1-indexed)
            page_size: Number of orders per page
            return_total: If True, returns (orders, total_count) tuple
        """
        try:
            client = get_alpaca_trading_client()
            max_fetch = 100
            req = GetOrdersRequest(status="all", limit=max_fetch, nested=False)
            orders_page = client.get_orders(req)
            # Filter to only options orders
            orders = [o for o in orders_page if o.symbol and is_options_symbol(o.symbol)]
            total_count = len(orders)

            # Convert orders to a list of dictionaries
            orders_data = []
            for order in orders:
                qty = float(order.qty) if order.qty is not None else 0.0
                filled_qty = float(order.filled_qty) if order.filled_qty is not None else 0.0
                filled_avg_price = float(order.filled_avg_price) if order.filled_avg_price is not None else 0.0

                # Format order date/time
                order_date = ""
                if order.created_at:
                    order_date = order.created_at.strftime("%m/%d %H:%M")

                # Get order ID (short version for display)
                order_id = str(order.id) if order.id else "-"
                order_id_short = order_id[:8] if len(order_id) > 8 else order_id

                # Parse OCC symbol for display
                from .options_trading_utils import parse_occ_symbol
                try:
                    parsed = parse_occ_symbol(order.symbol)
                    underlying = parsed.get("underlying", order.symbol[:4])
                    contract_type = parsed.get("contract_type", "unknown").upper()
                    strike = parsed.get("strike", 0)
                    expiration = parsed.get("expiration", "")
                except:
                    underlying = order.symbol[:4]
                    contract_type = "OPT"
                    strike = 0
                    expiration = ""

                orders_data.append({
                    "Symbol": order.symbol,
                    "Underlying": underlying,
                    "Type": contract_type,
                    "Strike": f"${strike:.2f}" if strike else "-",
                    "Expiration": expiration,
                    "Order Type": order.type,
                    "Side": order.side,
                    "Qty": int(qty),
                    "Filled Qty": int(filled_qty),
                    "Avg. Fill Price": f"${filled_avg_price:.2f}" if filled_avg_price > 0 else "-",
                    "Status": order.status,
                    "Date": order_date,
                    "Order ID": order_id,
                    "Order ID Short": order_id_short
                })

            # Slice out the exact page we want (newest first)
            start = (page - 1) * page_size
            page_data = orders_data[start : start + page_size]

            if return_total:
                return page_data, total_count
            return page_data

        except Exception as e:
            log_external_error(
                system="alpaca",
                operation="get_options_orders",
                error=e,
                params={"page": page, "page_size": page_size}
            )
            if return_total:
                return [], 0
            return []

    @staticmethod
    def get_account_info():
        """Get account information from Alpaca"""
        try:
            client = get_alpaca_trading_client()
            account = client.get_account()
            
            # Extract the required values
            buying_power = float(account.buying_power)
            cash = float(account.cash)
            
            # Calculate daily change
            equity = float(account.equity)
            last_equity = float(account.last_equity)
            daily_change_dollars = equity - last_equity
            daily_change_percent = (daily_change_dollars / last_equity) * 100 if last_equity != 0 else 0
            
            return {
                "buying_power": buying_power,
                "cash": cash,
                "daily_change_dollars": daily_change_dollars,
                "daily_change_percent": daily_change_percent
            }
        except Exception as e:
            log_external_error(
                system="alpaca",
                operation="get_account_info",
                error=e
            )
            return {
                "buying_power": 0,
                "cash": 0,
                "daily_change_dollars": 0,
                "daily_change_percent": 0
            } 

    @staticmethod
    def get_current_position_state(symbol: str) -> str:
        """Return current position state for a symbol in the Alpaca account.

        Args:
            symbol: Ticker symbol (e.g. "AAPL" or "BTC/USD").  Crypto symbols will
                    be treated the same way as equities – a positive quantity is
                    considered a *LONG* position while a negative quantity (should
                    Alpaca ever allow it) is considered *SHORT*.

        Returns:
            One of "LONG", "SHORT", or "NEUTRAL" if no open position exists or we
            encounter an error.
        """
        try:
            # Skip if credentials are missing – the helper will raise inside but we
            # want to fail gracefully and just assume no position.
            client = get_alpaca_trading_client()

            # `get_all_positions()` is more broadly supported across Alpaca
            # versions than `get_position(symbol)` and avoids raising when the
            # asset is not found.
            positions = client.get_all_positions()

            # Normalise the requested symbol for comparisons – Alpaca symbols
            # for crypto may use different formats, so we normalize for position comparison only.
            requested_symbol_key = symbol.upper().replace("/", "")

            for pos in positions:
                if pos.symbol.upper() == requested_symbol_key:
                    try:
                        qty = float(pos.qty)
                    except (ValueError, AttributeError):
                        qty = 0.0

                    if qty > 0:
                        return "LONG"
                    elif qty < 0:
                        return "SHORT"
                    else:
                        # Zero quantity technically shouldn't appear but treat as
                        # neutral just in case.
                        return "NEUTRAL"
            # If we fall through the loop there is no open position for symbol.
            return "NEUTRAL"
        except Exception as e:
            # Log and default to neutral so agent prompts still work.
            log_external_error(
                system="alpaca",
                operation="get_current_position_state",
                error=e,
                symbol=symbol
            )
            return "NEUTRAL"

    @staticmethod
    def place_market_order(symbol: str, side: str, notional: float = None, qty: float = None) -> dict:
        """
        Place a market order with Alpaca
        
        Args:
            symbol: Stock symbol (e.g., "AAPL")
            side: "buy" or "sell"
            notional: Dollar amount to buy/sell (for fractional shares)
            qty: Number of shares (if not using notional)
            
        Returns:
            Dictionary with order result information
        """
        try:
            client = get_alpaca_trading_client()
            
            # Normalize symbol for Alpaca (remove "/" for crypto)
            alpaca_symbol = symbol.upper().replace("/", "")
            
            # Determine order side
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            
            # Determine proper time-in-force: crypto orders only allow GTC
            is_crypto = "/" in symbol.upper()
            tif = TimeInForce.GTC if is_crypto else TimeInForce.DAY

            # Create market order request
            if notional and notional > 0:
                # Use notional (dollar amount) for fractional shares
                order_request = MarketOrderRequest(
                    symbol=alpaca_symbol,
                    side=order_side,
                    time_in_force=tif,
                    notional=notional
                )
            elif qty and qty > 0:
                # Use quantity (number of shares)
                order_request = MarketOrderRequest(
                    symbol=alpaca_symbol,
                    side=order_side,
                    time_in_force=tif,
                    qty=qty
                )
            else:
                return {"success": False, "error": "Must specify either notional or qty"}
            
            # Submit the order
            order = client.submit_order(order_request)
            
            return {
                "success": True,
                "order_id": order.id,
                "symbol": order.symbol,
                "side": order.side,
                "qty": float(order.qty) if order.qty else None,
                "notional": float(order.notional) if order.notional else None,
                "status": order.status,
                "message": f"Successfully placed {side} order for {symbol}"
            }
            
        except Exception as e:
            error_msg = f"Error placing {side} order for {symbol}: {e}"
            log_external_error(
                system="alpaca",
                operation="place_market_order",
                error=e,
                symbol=symbol,
                params={"side": side, "notional": notional, "qty": qty}
            )
            return {"success": False, "error": error_msg}

    @staticmethod
    def extract_sl_tp_from_analysis(analysis_text: str, entry_price: float, is_short: bool = False) -> dict:
        """
        Extract stop-loss and take-profit levels from trader agent's analysis text.

        The trader agent outputs a markdown table with format:
        | Aspect | Details |
        |--------|---------|
        | Entry Price | $X.XX |
        | Stop Loss | $X.XX |
        | Target 1 | $X.XX |
        | Target 2 | $X.XX |

        Args:
            analysis_text: The trader's analysis text containing the decision table
            entry_price: The current entry price (for validation)
            is_short: Whether this is a SHORT position (inverts SL/TP logic)

        Returns:
            Dictionary with 'stop_loss' and 'take_profit' prices, or None if not found
        """
        result = {
            "stop_loss": None,
            "take_profit": None,
            "entry_price_from_ai": None,
        }

        if not analysis_text:
            return result

        # Extract Stop Loss price from markdown table
        sl_patterns = [
            r'\|\s*Stop Loss\s*\|\s*\$?([\d,]+\.?\d*)',
            r'Stop Loss[:\s]+\$?([\d,]+\.?\d*)',
            r'stop[- ]?loss[:\s]+\$?([\d,]+\.?\d*)',
        ]

        for pattern in sl_patterns:
            match = re.search(pattern, analysis_text, re.IGNORECASE)
            if match:
                try:
                    result["stop_loss"] = float(match.group(1).replace(",", ""))
                    break
                except ValueError:
                    continue

        # Extract Take Profit / Target 1 price from markdown table
        tp_patterns = [
            r'\|\s*Target\s*1?\s*\|\s*\$?([\d,]+\.?\d*)',
            r'Target\s*1?[:\s]+\$?([\d,]+\.?\d*)',
            r'take[- ]?profit[:\s]+\$?([\d,]+\.?\d*)',
            r'profit[- ]?target[:\s]+\$?([\d,]+\.?\d*)',
        ]

        for pattern in tp_patterns:
            match = re.search(pattern, analysis_text, re.IGNORECASE)
            if match:
                try:
                    result["take_profit"] = float(match.group(1).replace(",", ""))
                    break
                except ValueError:
                    continue

        # Extract AI's entry price for reference
        entry_patterns = [
            r'\|\s*Entry Price\s*\|\s*\$?([\d,]+\.?\d*)',
            r'Entry Price[:\s]+\$?([\d,]+\.?\d*)',
        ]

        for pattern in entry_patterns:
            match = re.search(pattern, analysis_text, re.IGNORECASE)
            if match:
                try:
                    result["entry_price_from_ai"] = float(match.group(1).replace(",", ""))
                    break
                except ValueError:
                    continue

        # Validate extracted prices make sense
        sl = result["stop_loss"]
        tp = result["take_profit"]

        if is_short:
            # For SHORT: SL should be ABOVE entry, TP should be BELOW entry
            if sl is not None and sl <= entry_price:
                print(f"[SL/TP] Invalid SHORT stop-loss {sl} <= entry {entry_price}, ignoring")
                result["stop_loss"] = None
            if tp is not None and tp >= entry_price:
                print(f"[SL/TP] Invalid SHORT take-profit {tp} >= entry {entry_price}, ignoring")
                result["take_profit"] = None
        else:
            # For BUY/LONG: SL should be BELOW entry, TP should be ABOVE entry
            if sl is not None and sl >= entry_price:
                print(f"[SL/TP] Invalid LONG stop-loss {sl} >= entry {entry_price}, ignoring")
                result["stop_loss"] = None
            if tp is not None and tp <= entry_price:
                print(f"[SL/TP] Invalid LONG take-profit {tp} <= entry {entry_price}, ignoring")
                result["take_profit"] = None

        return result

    @staticmethod
    def place_bracket_order(
        symbol: str,
        side: str,
        qty: int,
        stop_loss_price: float,
        take_profit_price: float = None
    ) -> dict:
        """
        Place a bracket order (entry + stop-loss + optional take-profit) with Alpaca.

        Bracket orders are atomic - all legs are created together.
        Only works for stocks; crypto doesn't support bracket orders.

        Args:
            symbol: Stock symbol (e.g., "AAPL")
            side: "buy" or "sell"
            qty: Number of shares (must be integer for bracket orders)
            stop_loss_price: Stop-loss trigger price
            take_profit_price: Take-profit limit price (optional)

        Returns:
            Dictionary with order result information
        """
        try:
            # Crypto doesn't support bracket orders
            is_crypto = "/" in symbol.upper()
            if is_crypto:
                return {
                    "success": False,
                    "error": f"Bracket orders not supported for crypto ({symbol}). Use separate orders."
                }

            client = get_alpaca_trading_client()

            # Normalize symbol
            alpaca_symbol = symbol.upper().replace("/", "")

            # Determine order side
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

            # Build bracket order request
            order_params = {
                "symbol": alpaca_symbol,
                "qty": qty,
                "side": order_side,
                "time_in_force": TimeInForce.DAY,
                "order_class": OrderClass.BRACKET,
                "stop_loss": StopLossRequest(stop_price=round(stop_loss_price, 2)),
            }

            # Add take-profit if specified
            if take_profit_price is not None:
                order_params["take_profit"] = TakeProfitRequest(limit_price=round(take_profit_price, 2))

            order_request = MarketOrderRequest(**order_params)

            # Submit the bracket order
            order = client.submit_order(order_request)

            return {
                "success": True,
                "order_id": order.id,
                "symbol": order.symbol,
                "side": str(order.side),
                "qty": float(order.qty) if order.qty else None,
                "order_class": "bracket",
                "stop_loss_price": stop_loss_price,
                "take_profit_price": take_profit_price,
                "status": str(order.status),
                "message": f"Successfully placed bracket order for {symbol} with SL=${stop_loss_price}"
                          + (f" and TP=${take_profit_price}" if take_profit_price else "")
            }

        except Exception as e:
            error_msg = f"Error placing bracket order for {symbol}: {e}"
            log_external_error(
                system="alpaca",
                operation="place_bracket_order",
                error=e,
                symbol=symbol,
                params={"side": side, "qty": qty, "stop_loss": stop_loss_price, "take_profit": take_profit_price}
            )
            return {"success": False, "error": error_msg}

    @staticmethod
    def place_stop_order(symbol: str, side: str, qty: int, stop_price: float) -> dict:
        """
        Place a standalone stop order (for crypto or as fallback).

        Args:
            symbol: Symbol (e.g., "AAPL" or "BTC/USD")
            side: "buy" or "sell"
            qty: Number of shares/units
            stop_price: Stop trigger price

        Returns:
            Dictionary with order result information
        """
        try:
            client = get_alpaca_trading_client()

            # Normalize symbol
            alpaca_symbol = symbol.upper().replace("/", "")

            # Determine order side
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

            # Crypto uses GTC, stocks use DAY
            is_crypto = "/" in symbol.upper()
            tif = TimeInForce.GTC if is_crypto else TimeInForce.DAY

            order_request = StopOrderRequest(
                symbol=alpaca_symbol,
                qty=qty,
                side=order_side,
                time_in_force=tif,
                stop_price=round(stop_price, 2)
            )

            order = client.submit_order(order_request)

            return {
                "success": True,
                "order_id": order.id,
                "symbol": order.symbol,
                "side": str(order.side),
                "qty": float(order.qty) if order.qty else None,
                "stop_price": stop_price,
                "status": str(order.status),
                "message": f"Successfully placed stop order for {symbol} at ${stop_price}"
            }

        except Exception as e:
            error_msg = f"Error placing stop order for {symbol}: {e}"
            log_external_error(
                system="alpaca",
                operation="place_stop_order",
                error=e,
                symbol=symbol,
                params={"side": side, "qty": qty, "stop_price": stop_price}
            )
            return {"success": False, "error": error_msg}

    @staticmethod
    def place_limit_order(symbol: str, side: str, qty: int, limit_price: float) -> dict:
        """
        Place a standalone limit order (for take-profit on crypto or as fallback).

        Args:
            symbol: Symbol (e.g., "AAPL" or "BTC/USD")
            side: "buy" or "sell"
            qty: Number of shares/units
            limit_price: Limit price

        Returns:
            Dictionary with order result information
        """
        try:
            client = get_alpaca_trading_client()

            # Normalize symbol
            alpaca_symbol = symbol.upper().replace("/", "")

            # Determine order side
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

            # Crypto uses GTC, stocks use DAY
            is_crypto = "/" in symbol.upper()
            tif = TimeInForce.GTC if is_crypto else TimeInForce.DAY

            order_request = LimitOrderRequest(
                symbol=alpaca_symbol,
                qty=qty,
                side=order_side,
                time_in_force=tif,
                limit_price=round(limit_price, 2)
            )

            order = client.submit_order(order_request)

            return {
                "success": True,
                "order_id": order.id,
                "symbol": order.symbol,
                "side": str(order.side),
                "qty": float(order.qty) if order.qty else None,
                "limit_price": limit_price,
                "status": str(order.status),
                "message": f"Successfully placed limit order for {symbol} at ${limit_price}"
            }

        except Exception as e:
            error_msg = f"Error placing limit order for {symbol}: {e}"
            log_external_error(
                system="alpaca",
                operation="place_limit_order",
                error=e,
                symbol=symbol,
                params={"side": side, "qty": qty, "limit_price": limit_price}
            )
            return {"success": False, "error": error_msg}

    @staticmethod
    def close_position(symbol: str, percentage: float = 100.0) -> dict:
        """
        Close a position (partially or completely)
        
        Args:
            symbol: Stock symbol
            percentage: Percentage of position to close (default 100% = full close)
            
        Returns:
            Dictionary with close result information
        """
        try:
            client = get_alpaca_trading_client()
            
            # Normalize symbol for Alpaca
            alpaca_symbol = symbol.upper().replace("/", "")
            
            # For full position close (100%), don't specify percentage - let Alpaca close entire position
            if percentage >= 100.0:
                # Close the entire position without specifying percentage
                order = client.close_position(alpaca_symbol)
            else:
                # Create close position request for partial close
                close_request = ClosePositionRequest(
                    percentage=str(percentage / 100.0)  # Convert percentage to decimal string
                )
                order = client.close_position(alpaca_symbol, close_request)
            
            return {
                "success": True,
                "order_id": order.id,
                "symbol": order.symbol,
                "side": order.side,
                "qty": float(order.qty) if order.qty else None,
                "status": order.status,
                "message": f"Successfully closed {percentage}% of {symbol} position"
            }
            
        except Exception as e:
            error_msg = f"Error closing position for {symbol}: {e}"
            log_external_error(
                system="alpaca",
                operation="close_position",
                error=e,
                symbol=symbol,
                params={"percentage": percentage}
            )
            return {"success": False, "error": error_msg}

    @staticmethod
    def execute_trading_action(
        symbol: str,
        current_position: str,
        signal: str,
        dollar_amount: float,
        allow_shorts: bool = False,
        sl_tp_config: dict = None,
        analysis_text: str = None
    ) -> dict:
        """
        Execute trading action based on current position and signal.

        Supports optional stop-loss and take-profit orders via bracket orders (stocks)
        or separate orders (crypto).

        Args:
            symbol: Stock symbol
            current_position: Current position state ("LONG", "SHORT", "NEUTRAL")
            signal: Trading signal from analysis
            dollar_amount: Dollar amount for trades
            allow_shorts: Whether short selling is allowed
            sl_tp_config: Optional dict with SL/TP configuration:
                - enable_stop_loss: bool
                - stop_loss_percentage: float (default %)
                - stop_loss_use_ai: bool (use AI-extracted levels)
                - enable_take_profit: bool
                - take_profit_percentage: float (default %)
                - take_profit_use_ai: bool (use AI-extracted levels)
            analysis_text: Optional trader analysis text for AI SL/TP extraction

        Returns:
            Dictionary with execution results
        """
        try:
            results = []

            # Helper to calculate integer quantity for any orders (used by both trading modes)
            def _calc_qty(sym: str, amount: float) -> tuple:
                """Return (integer share qty, price) based on latest quote price."""
                try:
                    quote = AlpacaUtils.get_latest_quote(sym)
                    price = quote.get("bid_price") or quote.get("ask_price")
                    if not price or price <= 0:
                        # Fallback: assume $1 to avoid div-by-zero; will raise later if Alpaca rejects
                        price = 1
                    qty = int(amount / price)
                    return max(qty, 1), price
                except Exception:
                    # Fallback: at least 1 share, unknown price
                    return 1, None

            def _calculate_sl_tp_prices(entry_price: float, is_short: bool, config: dict, analysis: str):
                """Calculate stop-loss and take-profit prices based on config and AI extraction."""
                sl_price = None
                tp_price = None

                if not config:
                    return sl_price, tp_price

                enable_sl = config.get("enable_stop_loss", False)
                enable_tp = config.get("enable_take_profit", False)

                if not enable_sl and not enable_tp:
                    return sl_price, tp_price

                use_ai_sl = config.get("stop_loss_use_ai", True)
                use_ai_tp = config.get("take_profit_use_ai", True)
                sl_pct = config.get("stop_loss_percentage", 5.0)
                tp_pct = config.get("take_profit_percentage", 10.0)

                # Try AI extraction first if enabled
                ai_levels = {}
                if analysis and (use_ai_sl or use_ai_tp):
                    ai_levels = AlpacaUtils.extract_sl_tp_from_analysis(analysis, entry_price, is_short)
                    print(f"[SL/TP] AI extraction: SL=${ai_levels.get('stop_loss')}, TP=${ai_levels.get('take_profit')}")

                # Calculate stop-loss
                if enable_sl:
                    if use_ai_sl and ai_levels.get("stop_loss"):
                        sl_price = ai_levels["stop_loss"]
                        print(f"[SL/TP] Using AI stop-loss: ${sl_price}")
                    else:
                        # Use percentage-based default
                        if is_short:
                            sl_price = entry_price * (1 + sl_pct / 100)  # SL above entry for SHORT
                        else:
                            sl_price = entry_price * (1 - sl_pct / 100)  # SL below entry for BUY/LONG
                        print(f"[SL/TP] Using default {sl_pct}% stop-loss: ${sl_price:.2f}")

                # Calculate take-profit
                if enable_tp:
                    if use_ai_tp and ai_levels.get("take_profit"):
                        tp_price = ai_levels["take_profit"]
                        print(f"[SL/TP] Using AI take-profit: ${tp_price}")
                    else:
                        # Use percentage-based default
                        if is_short:
                            tp_price = entry_price * (1 - tp_pct / 100)  # TP below entry for SHORT
                        else:
                            tp_price = entry_price * (1 + tp_pct / 100)  # TP above entry for BUY/LONG
                        print(f"[SL/TP] Using default {tp_pct}% take-profit: ${tp_price:.2f}")

                return sl_price, tp_price

            def _place_entry_with_sl_tp(sym: str, side: str, qty: int, entry_price: float, is_short: bool):
                """Place entry order with SL/TP using bracket orders (stocks) or separate orders (crypto)."""
                is_crypto = "/" in sym.upper()

                # Calculate SL/TP prices
                sl_price, tp_price = _calculate_sl_tp_prices(
                    entry_price, is_short, sl_tp_config, analysis_text
                )

                # If no SL/TP configured, just place market order
                if sl_price is None and tp_price is None:
                    if is_crypto:
                        return AlpacaUtils.place_market_order(sym, side, notional=dollar_amount)
                    else:
                        return AlpacaUtils.place_market_order(sym, side, qty=qty)

                # Try bracket order for stocks
                if not is_crypto and sl_price is not None:
                    bracket_result = AlpacaUtils.place_bracket_order(
                        sym, side, qty, sl_price, tp_price
                    )
                    if bracket_result.get("success"):
                        return bracket_result
                    else:
                        # Bracket failed, fall back to market order
                        print(f"[SL/TP] Bracket order failed, falling back to market order: {bracket_result.get('error')}")
                        market_result = AlpacaUtils.place_market_order(sym, side, qty=qty)
                        market_result["sl_tp_note"] = "Bracket order failed, placed market order without SL/TP"
                        return market_result

                # For crypto or if only TP is set, use market order + separate SL/TP orders
                if is_crypto:
                    entry_result = AlpacaUtils.place_market_order(sym, side, notional=dollar_amount)
                else:
                    entry_result = AlpacaUtils.place_market_order(sym, side, qty=qty)

                if not entry_result.get("success"):
                    return entry_result

                # Place separate SL/TP orders for crypto
                # Note: For crypto, qty is estimated from entry price. Actual fill qty may differ
                # slightly in volatile markets. The SL/TP orders use this estimated qty.
                sl_tp_results = []
                exit_side = "sell" if side.lower() == "buy" else "buy"

                if sl_price is not None:
                    sl_result = AlpacaUtils.place_stop_order(sym, exit_side, qty, sl_price)
                    sl_tp_results.append({"type": "stop_loss", "result": sl_result})

                if tp_price is not None:
                    tp_result = AlpacaUtils.place_limit_order(sym, exit_side, qty, tp_price)
                    sl_tp_results.append({"type": "take_profit", "result": tp_result})

                entry_result["sl_tp_orders"] = sl_tp_results
                return entry_result
            
            if allow_shorts:
                # Trading mode: LONG/NEUTRAL/SHORT signals
                signal = signal.upper()

                if current_position == "LONG":
                    if signal == "LONG":
                        results.append({"action": "hold", "message": f"Keeping LONG position in {symbol}"})
                    elif signal == "NEUTRAL":
                        # Close LONG position
                        close_result = AlpacaUtils.close_position(symbol)
                        results.append({"action": "close_long", "result": close_result})
                    elif signal == "SHORT":
                        # Close LONG and open SHORT
                        close_result = AlpacaUtils.close_position(symbol)
                        results.append({"action": "close_long", "result": close_result})
                        if close_result.get("success"):
                            # Check if this is crypto - Alpaca doesn't support crypto short selling directly
                            is_crypto = "/" in symbol.upper()
                            if is_crypto:
                                error_msg = f"Direct short selling not supported for crypto assets like {symbol}. Position closed but short not opened."
                                results.append({"action": "open_short", "result": {"success": False, "error": error_msg}})
                            else:
                                # Calculate integer quantity for short (fractional shares cannot be shorted)
                                qty_int, entry_price = _calc_qty(symbol, dollar_amount)
                                # Use SL/TP helper for entry with protective orders
                                short_result = _place_entry_with_sl_tp(symbol, "sell", qty_int, entry_price, is_short=True)
                                results.append({"action": "open_short", "result": short_result})

                elif current_position == "SHORT":
                    if signal == "SHORT":
                        results.append({"action": "hold", "message": f"Keeping SHORT position in {symbol}"})
                    elif signal == "NEUTRAL":
                        # Close SHORT position
                        close_result = AlpacaUtils.close_position(symbol)
                        results.append({"action": "close_short", "result": close_result})
                    elif signal == "LONG":
                        # Close SHORT and open LONG
                        close_result = AlpacaUtils.close_position(symbol)
                        results.append({"action": "close_short", "result": close_result})
                        if close_result.get("success"):
                            # Open LONG position with SL/TP
                            qty_int, entry_price = _calc_qty(symbol, dollar_amount)
                            long_result = _place_entry_with_sl_tp(symbol, "buy", qty_int, entry_price, is_short=False)
                            results.append({"action": "open_long", "result": long_result})

                elif current_position == "NEUTRAL":
                    if signal == "LONG":
                        # Open LONG position with SL/TP
                        qty_int, entry_price = _calc_qty(symbol, dollar_amount)
                        long_result = _place_entry_with_sl_tp(symbol, "buy", qty_int, entry_price, is_short=False)
                        results.append({"action": "open_long", "result": long_result})
                    elif signal == "SHORT":
                        # Check if this is crypto - Alpaca doesn't support crypto short selling directly
                        is_crypto = "/" in symbol.upper()
                        if is_crypto:
                            error_msg = f"Direct short selling not supported for crypto assets like {symbol}. Consider using derivatives or margin trading platforms."
                            results.append({"action": "open_short", "result": {"success": False, "error": error_msg}})
                        else:
                            # For stocks, attempt short selling with SL/TP
                            qty_int, entry_price = _calc_qty(symbol, dollar_amount)
                            short_result = _place_entry_with_sl_tp(symbol, "sell", qty_int, entry_price, is_short=True)
                            results.append({"action": "open_short", "result": short_result})
                    elif signal == "NEUTRAL":
                        results.append({"action": "hold", "message": f"No position needed for {symbol}"})
            
            else:
                # Investment mode: BUY/HOLD/SELL signals
                signal = signal.upper()
                has_position = current_position == "LONG"

                if signal == "BUY":
                    if has_position:
                        results.append({"action": "hold", "message": f"Already have position in {symbol}"})
                    else:
                        # Buy position with SL/TP
                        qty_int, entry_price = _calc_qty(symbol, dollar_amount)
                        buy_result = _place_entry_with_sl_tp(symbol, "buy", qty_int, entry_price, is_short=False)
                        results.append({"action": "buy", "result": buy_result})

                elif signal == "SELL":
                    if has_position:
                        # Sell position
                        sell_result = AlpacaUtils.close_position(symbol)
                        results.append({"action": "sell", "result": sell_result})
                    else:
                        results.append({"action": "hold", "message": f"No position to sell in {symbol}"})

                elif signal == "HOLD":
                    results.append({"action": "hold", "message": f"Holding current position in {symbol}"})
            
            # Check if any critical actions failed
            has_failures = False
            for action in results:
                if "result" in action and not action["result"].get("success", True):
                    has_failures = True
                    break
                    
            return {
                "success": not has_failures,
                "symbol": symbol,
                "current_position": current_position,
                "signal": signal,
                "actions": results
            }
            
        except Exception as e:
            error_msg = f"Error executing trading action for {symbol}: {e}"
            log_external_error(
                system="alpaca",
                operation="execute_trading_action",
                error=e,
                symbol=symbol,
                params={"signal": signal, "dollar_amount": dollar_amount, "allow_shorts": allow_shorts}
            )
            return {"success": False, "error": error_msg} 