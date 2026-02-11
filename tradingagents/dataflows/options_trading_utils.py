"""
Options Trading Utilities for TradingAgents

Provides Alpaca Options API integration for:
- Fetching option contracts
- Placing options orders
- Managing options positions
- OCC symbol formatting/parsing

Alpaca Options API:
- Tiers: 0 (disabled), 1 (covered calls/puts), 2 (buy calls/puts), 3 (spreads)
- Paper trading: Options enabled by default
- Endpoint: /v2/options/contracts for contract lookup
- Orders: Standard Orders API with OCC symbol format
- Constraints: qty=whole numbers, time_in_force="day", no extended hours
"""

import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    GetOptionContractsRequest,
    ClosePositionRequest,
)
from alpaca.trading.enums import (
    OrderSide,
    TimeInForce,
    OrderType,
    AssetClass,
    ContractType,
)

from .config import get_api_key
from .external_data_logger import log_external_error


def get_options_trading_client() -> TradingClient:
    """Get Alpaca Trading Client for options trading."""
    api_key = get_api_key("alpaca_api_key", "ALPACA_API_KEY")
    api_secret = get_api_key("alpaca_secret_key", "ALPACA_SECRET_KEY")
    if not api_key or not api_secret:
        raise ValueError("Alpaca API key or secret not found. Please set ALPACA_API_KEY and ALPACA_SECRET_KEY.")
    return TradingClient(api_key, api_secret, paper=True)


def format_occ_symbol(
    underlying: str,
    expiration: Union[str, datetime],
    contract_type: str,
    strike: float
) -> str:
    """
    Format an OCC option symbol.

    OCC format: SYMBOL + YYMMDD + C/P + strike*1000 (8 digits, zero-padded)
    Example: AAPL240315C00200000 = AAPL $200 Call expiring March 15, 2024

    Args:
        underlying: Stock ticker symbol (e.g., "AAPL")
        expiration: Expiration date as string (YYYY-MM-DD) or datetime
        contract_type: "call" or "put" (case-insensitive)
        strike: Strike price (e.g., 200.00)

    Returns:
        OCC formatted symbol string
    """
    # Normalize underlying to uppercase, max 6 chars
    underlying = underlying.upper()[:6]

    # Parse expiration date
    if isinstance(expiration, str):
        exp_date = datetime.strptime(expiration, "%Y-%m-%d")
    else:
        exp_date = expiration

    # Format date as YYMMDD
    date_str = exp_date.strftime("%y%m%d")

    # Contract type indicator
    type_char = "C" if contract_type.lower() == "call" else "P"

    # Strike price: multiply by 1000 and format as 8-digit integer
    strike_int = int(strike * 1000)
    strike_str = f"{strike_int:08d}"

    return f"{underlying}{date_str}{type_char}{strike_str}"


def parse_occ_symbol(occ_symbol: str) -> Dict[str, any]:
    """
    Parse an OCC option symbol into its components.

    Args:
        occ_symbol: OCC formatted symbol (e.g., "AAPL240315C00200000")

    Returns:
        Dict with keys: underlying, expiration, contract_type, strike
    """
    # OCC format: SYMBOL (1-6 chars) + YYMMDD (6) + C/P (1) + Strike*1000 (8)
    # Total: 15-21 characters

    pattern = r'^([A-Z]{1,6})(\d{6})([CP])(\d{8})$'
    match = re.match(pattern, occ_symbol.upper())

    if not match:
        raise ValueError(f"Invalid OCC symbol format: {occ_symbol}")

    underlying, date_str, type_char, strike_str = match.groups()

    # Parse expiration date (YYMMDD)
    exp_date = datetime.strptime(date_str, "%y%m%d")

    # Parse strike (divide by 1000)
    strike = int(strike_str) / 1000

    return {
        "underlying": underlying,
        "expiration": exp_date.strftime("%Y-%m-%d"),
        "contract_type": "call" if type_char == "C" else "put",
        "strike": strike,
        "occ_symbol": occ_symbol.upper()
    }


def get_option_contracts(
    underlying: str,
    contract_type: Optional[str] = None,
    strike_price_gte: Optional[float] = None,
    strike_price_lte: Optional[float] = None,
    expiration_date_gte: Optional[str] = None,
    expiration_date_lte: Optional[str] = None,
    min_open_interest: Optional[int] = None,
    limit: int = 100
) -> List[Dict]:
    """
    Fetch available option contracts from Alpaca API.

    Args:
        underlying: Stock ticker symbol (e.g., "AAPL")
        contract_type: "call" or "put" (None for both)
        strike_price_gte: Minimum strike price
        strike_price_lte: Maximum strike price
        expiration_date_gte: Earliest expiration (YYYY-MM-DD)
        expiration_date_lte: Latest expiration (YYYY-MM-DD)
        min_open_interest: Minimum open interest filter
        limit: Maximum number of contracts to return

    Returns:
        List of contract dictionaries with details
    """
    try:
        client = get_options_trading_client()

        # Build request parameters
        request_params = {
            "underlying_symbols": [underlying.upper()],
        }

        if contract_type:
            request_params["type"] = ContractType.CALL if contract_type.lower() == "call" else ContractType.PUT

        if strike_price_gte:
            request_params["strike_price_gte"] = str(strike_price_gte)
        if strike_price_lte:
            request_params["strike_price_lte"] = str(strike_price_lte)

        if expiration_date_gte:
            request_params["expiration_date_gte"] = expiration_date_gte
        if expiration_date_lte:
            request_params["expiration_date_lte"] = expiration_date_lte

        request_params["limit"] = limit

        # Create request and fetch contracts
        request = GetOptionContractsRequest(**request_params)
        contracts_response = client.get_option_contracts(request)

        # Convert to list of dicts
        contracts = []
        for contract in contracts_response.option_contracts or []:
            contract_dict = {
                "symbol": contract.symbol,
                "underlying": contract.underlying_symbol,
                "strike": float(contract.strike_price),
                "expiration": str(contract.expiration_date),
                "contract_type": "call" if contract.type == ContractType.CALL else "put",
                "open_interest": getattr(contract, 'open_interest', 0),
                "close_price": float(getattr(contract, 'close_price', 0) or 0),
                "status": str(getattr(contract, 'status', 'unknown')),
            }

            # Apply open interest filter if specified
            if min_open_interest and contract_dict["open_interest"] < min_open_interest:
                continue

            contracts.append(contract_dict)

        return contracts

    except Exception as e:
        log_external_error(
            system="alpaca_options",
            operation="get_option_contracts",
            error=e,
            symbol=underlying,
            params={
                "contract_type": contract_type,
                "strike_range": f"{strike_price_gte}-{strike_price_lte}",
                "expiration_range": f"{expiration_date_gte} to {expiration_date_lte}"
            }
        )
        return []


def get_option_contract_by_symbol(occ_symbol: str) -> Optional[Dict]:
    """
    Get a specific option contract by its OCC symbol.

    Args:
        occ_symbol: OCC formatted symbol (e.g., "AAPL240315C00200000")

    Returns:
        Contract dictionary or None if not found
    """
    try:
        # Parse the OCC symbol to get underlying
        parsed = parse_occ_symbol(occ_symbol)

        client = get_options_trading_client()

        # Fetch contract directly
        # Note: Alpaca may require fetching by underlying and filtering
        contracts = get_option_contracts(
            underlying=parsed["underlying"],
            contract_type=parsed["contract_type"],
            strike_price_gte=parsed["strike"] - 0.01,
            strike_price_lte=parsed["strike"] + 0.01,
            expiration_date_gte=parsed["expiration"],
            expiration_date_lte=parsed["expiration"],
            limit=10
        )

        # Find exact match
        for contract in contracts:
            if contract["symbol"].upper() == occ_symbol.upper():
                return contract

        # If no exact match, return first matching contract
        if contracts:
            return contracts[0]

        return None

    except Exception as e:
        log_external_error(
            system="alpaca_options",
            operation="get_option_contract_by_symbol",
            error=e,
            symbol=occ_symbol
        )
        return None


def place_option_order(
    contract_symbol: str,
    side: str,
    qty: int,
    order_type: str = "market",
    limit_price: Optional[float] = None,
    client_order_id: Optional[str] = None
) -> Dict:
    """
    Place an options order via Alpaca.

    Args:
        contract_symbol: OCC formatted symbol (e.g., "AAPL240315C00200000")
        side: "buy" or "sell"
        qty: Number of contracts (whole numbers only)
        order_type: "market" or "limit"
        limit_price: Required for limit orders
        client_order_id: Optional client-specified order ID

    Returns:
        Dict with order result information

    Note:
        - Options orders must use whole number quantities
        - time_in_force must be "day" for options
        - No extended hours trading for options
    """
    try:
        client = get_options_trading_client()

        # Validate qty is whole number
        qty = int(qty)
        if qty <= 0:
            return {"success": False, "error": "Quantity must be a positive integer"}

        # Determine order side
        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

        # Build order request - options must use time_in_force="day"
        if order_type.lower() == "limit":
            if limit_price is None:
                return {"success": False, "error": "Limit price required for limit orders"}

            order_request = LimitOrderRequest(
                symbol=contract_symbol.upper(),
                qty=qty,
                side=order_side,
                time_in_force=TimeInForce.DAY,
                limit_price=limit_price,
                client_order_id=client_order_id
            )
        else:
            order_request = MarketOrderRequest(
                symbol=contract_symbol.upper(),
                qty=qty,
                side=order_side,
                time_in_force=TimeInForce.DAY,
                client_order_id=client_order_id
            )

        # Submit order
        order = client.submit_order(order_request)

        return {
            "success": True,
            "order_id": str(order.id),
            "symbol": order.symbol,
            "side": str(order.side),
            "qty": int(order.qty) if order.qty else qty,
            "order_type": str(order.type),
            "status": str(order.status),
            "filled_qty": int(order.filled_qty) if order.filled_qty else 0,
            "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
            "message": f"Successfully placed {side} order for {qty} contracts of {contract_symbol}"
        }

    except Exception as e:
        error_msg = f"Error placing options order for {contract_symbol}: {e}"
        log_external_error(
            system="alpaca_options",
            operation="place_option_order",
            error=e,
            symbol=contract_symbol,
            params={"side": side, "qty": qty, "order_type": order_type}
        )
        return {"success": False, "error": error_msg}


def get_options_positions() -> List[Dict]:
    """
    Get current options positions from Alpaca account.

    Returns:
        List of options position dictionaries
    """
    try:
        client = get_options_trading_client()
        positions = client.get_all_positions()

        options_positions = []
        for position in positions:
            # Check if this is an options position (symbol length > 6 typically)
            symbol = position.symbol

            # Try to parse as OCC symbol to confirm it's an option
            try:
                parsed = parse_occ_symbol(symbol)

                qty = float(position.qty)
                avg_entry = float(position.avg_entry_price)
                current_price = float(position.current_price)
                market_value = float(position.market_value)
                cost_basis = avg_entry * abs(qty) * 100  # Options are 100 shares per contract

                # Calculate P/L
                unrealized_pl = float(position.unrealized_pl)
                unrealized_pl_pct = (unrealized_pl / cost_basis) * 100 if cost_basis != 0 else 0

                options_positions.append({
                    "symbol": symbol,
                    "underlying": parsed["underlying"],
                    "contract_type": parsed["contract_type"],
                    "strike": parsed["strike"],
                    "expiration": parsed["expiration"],
                    "qty": int(qty),
                    "avg_entry_price": avg_entry,
                    "current_price": current_price,
                    "market_value": market_value,
                    "cost_basis": cost_basis,
                    "unrealized_pl": unrealized_pl,
                    "unrealized_pl_pct": unrealized_pl_pct,
                    "side": "long" if qty > 0 else "short"
                })
            except ValueError:
                # Not an options symbol, skip
                continue

        return options_positions

    except Exception as e:
        log_external_error(
            system="alpaca_options",
            operation="get_options_positions",
            error=e
        )
        return []


def close_option_position(contract_symbol: str, qty: Optional[int] = None) -> Dict:
    """
    Close an options position (partially or completely).

    Args:
        contract_symbol: OCC formatted symbol
        qty: Number of contracts to close (None = close all)

    Returns:
        Dict with close result information
    """
    try:
        client = get_options_trading_client()

        # Get current position
        positions = get_options_positions()
        position = next((p for p in positions if p["symbol"].upper() == contract_symbol.upper()), None)

        if not position:
            return {"success": False, "error": f"No open position found for {contract_symbol}"}

        # Determine quantity to close
        position_qty = abs(position["qty"])
        close_qty = qty if qty and qty < position_qty else position_qty

        # Determine side (opposite of current position)
        if position["side"] == "long":
            order_side = "sell"
        else:
            order_side = "buy"

        # Place closing order
        result = place_option_order(
            contract_symbol=contract_symbol,
            side=order_side,
            qty=close_qty,
            order_type="market"
        )

        if result["success"]:
            result["message"] = f"Successfully closed {close_qty} contracts of {contract_symbol}"

        return result

    except Exception as e:
        error_msg = f"Error closing options position {contract_symbol}: {e}"
        log_external_error(
            system="alpaca_options",
            operation="close_option_position",
            error=e,
            symbol=contract_symbol,
            params={"qty": qty}
        )
        return {"success": False, "error": error_msg}


def exercise_option(contract_symbol: str) -> Dict:
    """
    Exercise an options contract.

    Args:
        contract_symbol: OCC formatted symbol

    Returns:
        Dict with exercise result information

    Note:
        Only available for in-the-money options before expiration.
    """
    try:
        client = get_options_trading_client()

        # Alpaca exercise endpoint: POST /v2/positions/{symbol}/exercise
        # This may not be available in all alpaca-py versions
        response = client.exercise_option(contract_symbol.upper())

        return {
            "success": True,
            "symbol": contract_symbol,
            "message": f"Successfully exercised option {contract_symbol}"
        }

    except AttributeError:
        # Exercise may not be available in current alpaca-py version
        return {
            "success": False,
            "error": "Exercise functionality not available. Please exercise through Alpaca dashboard."
        }
    except Exception as e:
        error_msg = f"Error exercising option {contract_symbol}: {e}"
        log_external_error(
            system="alpaca_options",
            operation="exercise_option",
            error=e,
            symbol=contract_symbol
        )
        return {"success": False, "error": error_msg}


def get_recommended_contracts(
    ticker: str,
    direction: str,
    risk_profile: str = "moderate",
    curr_date: Optional[str] = None,
    current_price: Optional[float] = None
) -> str:
    """
    Get AI-recommended option contracts based on analysis parameters.

    Args:
        ticker: Underlying stock symbol
        direction: "bullish" or "bearish"
        risk_profile: "conservative", "moderate", or "aggressive"
        curr_date: Current date (YYYY-MM-DD)
        current_price: Current stock price (optional, will be fetched if not provided)

    Returns:
        Formatted string with recommended contracts and rationale
    """
    try:
        from .alpaca_utils import AlpacaUtils

        # Get current price if not provided
        if current_price is None:
            quote = AlpacaUtils.get_latest_quote(ticker)
            if quote and quote.get("ask_price"):
                current_price = (quote["bid_price"] + quote["ask_price"]) / 2
            else:
                return f"Error: Could not fetch current price for {ticker}"

        # Parse current date
        if curr_date:
            today = datetime.strptime(curr_date, "%Y-%m-%d")
        else:
            today = datetime.now()

        # Set parameters based on risk profile
        if risk_profile == "conservative":
            min_dte = 30
            max_dte = 60
            min_delta = 0.50  # ATM or slightly ITM
            max_delta = 0.70
            strike_range_pct = 0.05  # 5% from current price
        elif risk_profile == "aggressive":
            min_dte = 7
            max_dte = 30
            min_delta = 0.20  # OTM
            max_delta = 0.40
            strike_range_pct = 0.15  # 15% from current price
        else:  # moderate
            min_dte = 14
            max_dte = 45
            min_delta = 0.30
            max_delta = 0.55
            strike_range_pct = 0.10  # 10% from current price

        # Calculate strike range based on direction
        contract_type = "call" if direction.lower() == "bullish" else "put"

        if contract_type == "call":
            # For calls: look at strikes at and above current price
            strike_min = current_price * (1 - strike_range_pct * 0.3)
            strike_max = current_price * (1 + strike_range_pct)
        else:
            # For puts: look at strikes at and below current price
            strike_min = current_price * (1 - strike_range_pct)
            strike_max = current_price * (1 + strike_range_pct * 0.3)

        # Calculate expiration range
        exp_min = (today + timedelta(days=min_dte)).strftime("%Y-%m-%d")
        exp_max = (today + timedelta(days=max_dte)).strftime("%Y-%m-%d")

        # Fetch contracts
        contracts = get_option_contracts(
            underlying=ticker,
            contract_type=contract_type,
            strike_price_gte=strike_min,
            strike_price_lte=strike_max,
            expiration_date_gte=exp_min,
            expiration_date_lte=exp_max,
            min_open_interest=100,  # Liquidity filter
            limit=50
        )

        if not contracts:
            return f"""# RECOMMENDED OPTIONS CONTRACTS: {ticker}

**Direction:** {direction.upper()}
**Risk Profile:** {risk_profile.title()}

No suitable contracts found matching criteria:
- Strike range: ${strike_min:.2f} - ${strike_max:.2f}
- Expiration range: {exp_min} to {exp_max}
- Minimum open interest: 100

Consider adjusting parameters or checking if options are available for this symbol.
"""

        # Sort by open interest (liquidity)
        contracts.sort(key=lambda x: x.get("open_interest", 0), reverse=True)

        # Select top 5 recommendations
        top_contracts = contracts[:5]

        # Build recommendation report
        report = f"""# RECOMMENDED OPTIONS CONTRACTS: {ticker}

**Current Price:** ${current_price:.2f}
**Direction:** {direction.upper()}
**Risk Profile:** {risk_profile.title()}
**Contract Type:** {contract_type.upper()}S
**Expiration Range:** {min_dte}-{max_dte} DTE

---

## TOP RECOMMENDATIONS

| # | Symbol | Strike | Exp | DTE | OI | Last Price |
|---|--------|--------|-----|-----|-----|------------|
"""

        for i, c in enumerate(top_contracts, 1):
            exp_date = datetime.strptime(c["expiration"], "%Y-%m-%d")
            dte = (exp_date - today).days
            price_str = f"${c['close_price']:.2f}" if c['close_price'] > 0 else "N/A"

            report += f"| {i} | {c['symbol']} | ${c['strike']:.2f} | {c['expiration']} | {dte} | {c['open_interest']:,} | {price_str} |\n"

        # Add best recommendation
        best = top_contracts[0]
        best_exp = datetime.strptime(best["expiration"], "%Y-%m-%d")
        best_dte = (best_exp - today).days

        report += f"""
---

## PRIMARY RECOMMENDATION

**Contract:** {best['symbol']}
- **Strike:** ${best['strike']:.2f}
- **Expiration:** {best['expiration']} ({best_dte} DTE)
- **Type:** {best['contract_type'].upper()}
- **Open Interest:** {best['open_interest']:,}
- **Last Price:** ${best['close_price']:.2f}

**Rationale:**
- {"Above" if contract_type == "call" else "Below"} current price of ${current_price:.2f}
- Strong liquidity with {best['open_interest']:,} open interest
- {best_dte} days to expiration fits {risk_profile} risk profile
"""

        # Calculate estimated cost and max loss
        if best['close_price'] > 0:
            contract_cost = best['close_price'] * 100  # 100 shares per contract
            report += f"""
**Cost Analysis:**
- Cost per contract: ${contract_cost:.2f}
- Max loss (if expires worthless): ${contract_cost:.2f}
"""

        return report

    except Exception as e:
        log_external_error(
            system="alpaca_options",
            operation="get_recommended_contracts",
            error=e,
            symbol=ticker,
            params={"direction": direction, "risk_profile": risk_profile}
        )
        return f"Error generating contract recommendations for {ticker}: {str(e)}"


def execute_options_trading_action(
    contract_symbol: str,
    action: str,
    qty: int = 1,
    limit_price: Optional[float] = None
) -> Dict:
    """
    Execute an options trading action based on the action type.

    Args:
        contract_symbol: OCC formatted symbol
        action: One of: BUY_CALL, BUY_PUT, SELL_CALL, SELL_PUT,
                WRITE_CALL, WRITE_PUT, HOLD_OPTIONS, NO_OPTIONS
        qty: Number of contracts
        limit_price: Optional limit price for the order

    Returns:
        Dict with execution result
    """
    action = action.upper()

    # Handle no-action cases
    if action in ["HOLD_OPTIONS", "NO_OPTIONS"]:
        return {
            "success": True,
            "action": action,
            "message": f"No options trade executed ({action})"
        }

    # Map actions to order parameters
    action_map = {
        "BUY_CALL": ("buy", "call"),
        "BUY_PUT": ("buy", "put"),
        "SELL_CALL": ("sell", "call"),
        "SELL_PUT": ("sell", "put"),
        "WRITE_CALL": ("sell", "call"),  # Sell to open
        "WRITE_PUT": ("sell", "put"),    # Sell to open
    }

    if action not in action_map:
        return {
            "success": False,
            "error": f"Unknown options action: {action}"
        }

    side, expected_type = action_map[action]

    # Validate contract type matches action
    try:
        parsed = parse_occ_symbol(contract_symbol)
        if parsed["contract_type"] != expected_type:
            return {
                "success": False,
                "error": f"Contract type mismatch: {action} expects {expected_type}, got {parsed['contract_type']}"
            }
    except ValueError as e:
        return {
            "success": False,
            "error": f"Invalid contract symbol: {e}"
        }

    # Execute the order
    order_type = "limit" if limit_price else "market"
    result = place_option_order(
        contract_symbol=contract_symbol,
        side=side,
        qty=qty,
        order_type=order_type,
        limit_price=limit_price
    )

    if result["success"]:
        result["action"] = action

    return result
