"""
agent_trading_modes.py - Centralized trading mode utilities for all agents

This module provides consistent trading mode handling across all agent types:
- Analysts, Researchers, Risk Management, Managers, and Traders

Two trading modes supported:
1. Investment Mode (allow_shorts=False): BUY/HOLD/SELL actions
2. Trading Mode (allow_shorts=True): LONG/NEUTRAL/SHORT actions with position logic
"""

from typing import Dict, Any, Optional, Tuple, List


class TradingModeConfig:
    """Configuration class for trading modes"""

    # Investment mode actions
    INVESTMENT_ACTIONS = ["BUY", "HOLD", "SELL"]

    # Trading mode actions
    TRADING_ACTIONS = ["LONG", "NEUTRAL", "SHORT"]

    # Options trading actions
    OPTIONS_ACTIONS = [
        "BUY_CALL",      # Buy to open call
        "BUY_PUT",       # Buy to open put
        "SELL_CALL",     # Sell to close call
        "SELL_PUT",      # Sell to close put
        "WRITE_CALL",    # Sell to open (covered call)
        "WRITE_PUT",     # Sell to open (cash-secured put)
        "HOLD_OPTIONS",  # Hold existing options position
        "NO_OPTIONS",    # No options trade
    ]

    # Position states
    POSITION_LONG = "LONG"
    POSITION_SHORT = "SHORT"
    POSITION_NEUTRAL = "NEUTRAL"


def get_trading_mode_context(config: Optional[Dict[str, Any]] = None, 
                           current_position: str = "NEUTRAL") -> Dict[str, str]:
    """
    Get trading mode context information for agent prompts
    
    Args:
        config: Configuration dictionary containing 'allow_shorts' flag
        current_position: Current position state (LONG/SHORT/NEUTRAL)
        
    Returns:
        Dict containing trading mode context information
    """
    allow_shorts = config.get("allow_shorts", False) if config else False
    
    if allow_shorts:
        return _get_trading_context(current_position)
    else:
        return _get_investment_context()


def _get_investment_context() -> Dict[str, str]:
    """Get context for investment mode (BUY/HOLD/SELL) optimized for EOD trading"""
    return {
        "mode": "investment",
        "mode_name": "EOD TRADING INVESTMENT MODE",
        "actions": "BUY, HOLD, or SELL",
        "action_list": TradingModeConfig.INVESTMENT_ACTIONS,
        "allow_shorts": False,
        "instructions": """
You are operating in EOD TRADING INVESTMENT MODE with daily decision-making at market close.

Available actions for EOD trading:
- BUY: Enter position based on EOD analysis for next trading day
- HOLD: Maintain current position overnight after daily reassessment
- SELL: Exit position at market close or prepare for next day exit

**EOD TRADING FOCUS:**
- **Decision Timing:** Make trading decisions at end of each trading day
- **Holding Period:** Overnight positions with daily review and reassessment
- **Entry Strategy:** Based on daily closing prices, EOD momentum, and overnight setups
- **Exit Strategy:** Daily evaluation of profit targets, stop losses, and risk levels
- **Risk Management:** 1-3% risk per trade, 2:1 minimum risk/reward ratio
- **Position Sizing:** Based on daily volatility and overnight gap risk

**EOD TRADING CRITERIA:**
- Analysis based on daily closing prices and end-of-day momentum
- Volume confirmation from daily trading session
- Defined stop loss and profit target before overnight hold
- Consideration of overnight news risk and pre-market catalysts
- Daily market environment assessment and position adjustment

Focus on daily trading decisions with overnight position management, not intraday or long-term investing.
""",
        "decision_format": "BUY/HOLD/SELL",
        "final_format": "FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**"
    }


def _get_trading_context(current_position: str = "NEUTRAL") -> Dict[str, str]:
    """Get context for trading mode (LONG/NEUTRAL/SHORT) optimized for EOD trading"""
    
    position_logic = f"""
Current Position: {current_position}

EOD Trading Position Transition Logic:
- If Current Position: LONG
  • Signal: LONG → Hold position overnight, daily reassessment at market close
  • Signal: NEUTRAL → Close LONG position at market close or prepare exit for next day
  • Signal: SHORT → Close LONG position and prepare SHORT entry for next trading day

- If Current Position: SHORT  
  • Signal: SHORT → Hold position overnight, daily reassessment at market close
  • Signal: NEUTRAL → Close SHORT position at market close or prepare exit for next day
  • Signal: LONG → Close SHORT position and prepare LONG entry for next trading day

- If Current Position: NEUTRAL (no open position)
  • Signal: LONG → Prepare LONG position entry based on EOD analysis
  • Signal: SHORT → Prepare SHORT position entry based on EOD analysis
  • Signal: NEUTRAL → Stay in cash, wait for clear EOD setup
"""
    
    return {
        "mode": "trading",
        "mode_name": "EOD TRADING MODE", 
        "actions": "LONG, NEUTRAL, or SHORT",
        "action_list": TradingModeConfig.TRADING_ACTIONS,
        "allow_shorts": True,
        "current_position": current_position,
        "position_logic": position_logic,
        "instructions": f"""
You are operating in EOD TRADING MODE with daily decision-making at market close.

{position_logic}

Available EOD trading actions:
- LONG: Take long position based on EOD analysis (profit from overnight and next-day moves)
- SHORT: Take short position based on EOD analysis (profit from overnight and next-day declines) 
- NEUTRAL: Close all positions or stay in cash based on daily assessment

**EOD TRADING METHODOLOGY:**
- **Decision Timing:** All trading decisions made at market close (3:50-4:00 PM ET)
- **Entry Signals:** Based on daily closing prices, EOD momentum, and overnight catalysts
- **Exit Signals:** Daily reassessment at market close, gap management at open
- **Risk Management:** 1-3% risk per trade, 2:1 minimum R/R ratio
- **Position Management:** Daily stop adjustments, overnight risk assessment

**EOD POSITION CRITERIA:**
- Analysis based on daily charts and end-of-day technical setup
- Volume confirmation from full trading session
- Risk/reward ratio of at least 2:1 based on daily ranges
- Consideration of overnight news events and pre-market catalysts
- Appropriate position sizing based on daily volatility (ATR)

Focus on daily decision-making with overnight position management, emphasizing end-of-day analysis and next-day preparation.
""",
        "decision_format": "LONG/NEUTRAL/SHORT",
        "final_format": "FINAL TRANSACTION PROPOSAL: **LONG/NEUTRAL/SHORT**"
    }


def get_agent_specific_context(agent_type: str, trading_context: Dict[str, str]) -> str:
    """
    Get agent-specific trading mode instructions
    
    Args:
        agent_type: Type of agent (analyst, researcher, trader, risk_mgmt, manager)
        trading_context: Trading context from get_trading_mode_context()
        
    Returns:
        Agent-specific instruction string
    """
    
    base_context = trading_context["instructions"]
    mode_name = trading_context["mode_name"]
    actions = trading_context["actions"]
    
    agent_contexts = {
        "analyst": f"""
As an Analyst in {mode_name}, your analysis should consider {actions} perspectives.

Your analysis should:
- Evaluate market conditions suitable for each action type
- Provide data-driven insights supporting potential decisions
- Consider risk factors relevant to {actions} recommendations
- Present balanced analysis while highlighting key opportunities

{base_context}
""",
        
        "researcher": f"""
As a Researcher in {mode_name}, develop arguments supporting {actions} strategies.

Your research should:
- Build evidence-based cases for different action scenarios
- Address counterarguments from opposing perspectives
- Use historical data and market patterns to support positions
- Engage in debate using {actions} terminology

{base_context}
""",
        
        "trader": f"""
As a Trader in {mode_name}, make decisive {actions} recommendations.

Your decisions should:
- Be based on comprehensive analysis from the team
- Consider current market conditions and timing
- Include clear rationale for the chosen action
- Account for risk management and position sizing

{base_context}
""",
        
        "risk_mgmt": f"""
As a Risk Management Analyst in {mode_name}, evaluate {actions} decisions.

Your risk assessment should:
- Analyze potential losses and gains for each action type
- Consider portfolio impact and correlation risks
- Evaluate market volatility and timing risks
- Provide risk-adjusted recommendations using {actions} terminology

{base_context}
""",
        
        "manager": f"""
As a Manager in {mode_name}, synthesize team input for final {actions} decisions.

Your management approach should:
- Weigh different analyst perspectives and debates
- Make decisive final recommendations from {actions} options
- Consider overall strategy and risk management
- Provide clear reasoning for the chosen course of action

{base_context}
"""
    }
    
    return agent_contexts.get(agent_type, base_context)


def extract_recommendation(response_content: str, trading_mode: str) -> Optional[str]:
    """
    Extract trading recommendation from agent response
    
    Args:
        response_content: The agent's response content
        trading_mode: 'investment' or 'trading'
        
    Returns:
        Extracted recommendation or None if not found
    """
    content = response_content.upper()
    
    if trading_mode == "investment":
        # Look for BUY/HOLD/SELL patterns
        patterns = [
            "FINAL TRANSACTION PROPOSAL: **BUY**",
            "FINAL TRANSACTION PROPOSAL: **HOLD**", 
            "FINAL TRANSACTION PROPOSAL: **SELL**",
            "FINAL INVESTMENT DECISION: **BUY**",
            "FINAL INVESTMENT DECISION: **HOLD**",
            "FINAL INVESTMENT DECISION: **SELL**",
            "FINAL DECISION: **BUY**",
            "FINAL DECISION: **HOLD**",
            "FINAL DECISION: **SELL**"
        ]
        
        for pattern in patterns:
            if pattern in content:
                return pattern.split("**")[1]
                
        # Fallback - look for standalone actions at end
        for action in TradingModeConfig.INVESTMENT_ACTIONS:
            if f"**{action}**" in content[-100:]:  # Check last 100 chars
                return action
                
    else:  # trading mode
        # Look for LONG/NEUTRAL/SHORT patterns
        patterns = [
            "FINAL TRANSACTION PROPOSAL: **LONG**",
            "FINAL TRANSACTION PROPOSAL: **NEUTRAL**",
            "FINAL TRANSACTION PROPOSAL: **SHORT**",
            "FINAL TRADING DECISION: **LONG**", 
            "FINAL TRADING DECISION: **NEUTRAL**",
            "FINAL TRADING DECISION: **SHORT**",
            "FINAL RISK MANAGEMENT DECISION: **LONG**",
            "FINAL RISK MANAGEMENT DECISION: **NEUTRAL**", 
            "FINAL RISK MANAGEMENT DECISION: **SHORT**",
            "FINAL DECISION: **LONG**",
            "FINAL DECISION: **NEUTRAL**",
            "FINAL DECISION: **SHORT**"
        ]
        
        for pattern in patterns:
            if pattern in content:
                return pattern.split("**")[1]
                
        # Fallback - look for standalone actions at end
        for action in TradingModeConfig.TRADING_ACTIONS:
            if f"**{action}**" in content[-100:]:  # Check last 100 chars
                return action
    
    return None


def validate_recommendation(recommendation: str, trading_mode: str) -> bool:
    """
    Validate if recommendation is valid for the trading mode
    
    Args:
        recommendation: The recommendation to validate
        trading_mode: 'investment' or 'trading'
        
    Returns:
        True if valid, False otherwise
    """
    if not recommendation:
        return False
        
    recommendation = recommendation.upper()
    
    if trading_mode == "investment":
        return recommendation in TradingModeConfig.INVESTMENT_ACTIONS
    else:  # trading mode
        return recommendation in TradingModeConfig.TRADING_ACTIONS


def get_position_transition(current_position: str, new_signal: str) -> Dict[str, str]:
    """
    Get position transition information for trading mode
    
    Args:
        current_position: Current position (LONG/SHORT/NEUTRAL)
        new_signal: New signal (LONG/SHORT/NEUTRAL)
        
    Returns:
        Dict with transition information
    """
    current = current_position.upper()
    signal = new_signal.upper()
    
    transitions = {
        ("LONG", "LONG"): {
            "action": "HOLD",
            "description": "Keep existing LONG position",
            "new_position": "LONG"
        },
        ("LONG", "NEUTRAL"): {
            "action": "CLOSE_LONG", 
            "description": "Close LONG position, exit to neutral",
            "new_position": "NEUTRAL"
        },
        ("LONG", "SHORT"): {
            "action": "REVERSE_TO_SHORT",
            "description": "Close LONG position and open SHORT position", 
            "new_position": "SHORT"
        },
        ("SHORT", "SHORT"): {
            "action": "HOLD",
            "description": "Keep existing SHORT position",
            "new_position": "SHORT"
        },
        ("SHORT", "NEUTRAL"): {
            "action": "CLOSE_SHORT",
            "description": "Close SHORT position, exit to neutral",
            "new_position": "NEUTRAL"
        },
        ("SHORT", "LONG"): {
            "action": "REVERSE_TO_LONG", 
            "description": "Close SHORT position and open LONG position",
            "new_position": "LONG"
        },
        ("NEUTRAL", "LONG"): {
            "action": "OPEN_LONG",
            "description": "Open LONG position",
            "new_position": "LONG"
        },
        ("NEUTRAL", "SHORT"): {
            "action": "OPEN_SHORT",
            "description": "Open SHORT position", 
            "new_position": "SHORT"
        },
        ("NEUTRAL", "NEUTRAL"): {
            "action": "STAY_NEUTRAL",
            "description": "Stay in neutral position",
            "new_position": "NEUTRAL"
        }
    }
    
    return transitions.get((current, signal), {
        "action": "UNKNOWN",
        "description": f"Unknown transition from {current} to {signal}",
        "new_position": signal
    })


def format_final_decision(recommendation: str, trading_mode: str) -> str:
    """
    Format the final decision string consistently

    Args:
        recommendation: The recommendation (BUY/HOLD/SELL or LONG/NEUTRAL/SHORT)
        trading_mode: 'investment', 'trading', or 'options'

    Returns:
        Formatted final decision string
    """
    if not recommendation:
        return "FINAL DECISION: **NO_RECOMMENDATION**"

    recommendation = recommendation.upper()

    if trading_mode == "options":
        return f"FINAL OPTIONS PROPOSAL: **{recommendation}**"
    elif trading_mode == "investment":
        return f"FINAL TRANSACTION PROPOSAL: **{recommendation}**"
    else:  # trading mode
        return f"FINAL TRANSACTION PROPOSAL: **{recommendation}**"


def get_options_trading_context(config: Optional[Dict[str, Any]] = None,
                                current_options_positions: Optional[List] = None) -> Dict[str, str]:
    """
    Get options trading mode context information for agent prompts.

    Args:
        config: Configuration dictionary containing options trading settings
        current_options_positions: List of current options positions

    Returns:
        Dict containing options trading mode context information
    """
    if config is None:
        config = {}

    max_contracts = config.get("options_max_contracts", 10)
    max_position_value = config.get("options_max_position_value", 5000)
    min_dte = config.get("options_min_dte", 7)
    max_dte = config.get("options_max_dte", 45)
    min_delta = config.get("options_min_delta", 0.20)
    max_delta = config.get("options_max_delta", 0.70)
    min_open_interest = config.get("options_min_open_interest", 100)

    positions_summary = ""
    if current_options_positions:
        positions_summary = "\nCurrent Options Positions:\n"
        for pos in current_options_positions:
            positions_summary += f"- {pos['symbol']}: {pos['qty']} contracts @ ${pos['avg_entry_price']:.2f} (P/L: ${pos['unrealized_pl']:.2f})\n"
    else:
        positions_summary = "\nNo current options positions."

    return {
        "mode": "options",
        "mode_name": "OPTIONS TRADING MODE",
        "actions": ", ".join(TradingModeConfig.OPTIONS_ACTIONS),
        "action_list": TradingModeConfig.OPTIONS_ACTIONS,
        "positions_summary": positions_summary,
        "instructions": f"""
You are operating in OPTIONS TRADING MODE for end-of-day decision making.

**AVAILABLE OPTIONS ACTIONS:**
- **BUY_CALL**: Buy to open a call option (bullish bet)
- **BUY_PUT**: Buy to open a put option (bearish bet)
- **SELL_CALL**: Sell to close an existing call position
- **SELL_PUT**: Sell to close an existing put position
- **WRITE_CALL**: Sell to open a covered call (income strategy)
- **WRITE_PUT**: Sell to open a cash-secured put (income/entry strategy)
- **HOLD_OPTIONS**: Maintain existing options position
- **NO_OPTIONS**: Do not take any options trade

**OPTIONS TRADING PARAMETERS:**
- Maximum contracts per trade: {max_contracts}
- Maximum position value: ${max_position_value}
- Days to expiration range: {min_dte}-{max_dte} DTE
- Delta range: {min_delta}-{max_delta}
- Minimum open interest: {min_open_interest}

**CONTRACT SELECTION CRITERIA:**
1. **Strike Selection**: Choose strikes based on directional conviction and risk tolerance
2. **Expiration Selection**: Balance time decay vs. movement probability
3. **Liquidity**: Ensure adequate open interest and tight bid-ask spreads
4. **Risk/Reward**: Define max loss (premium paid) and profit targets

**OPTIONS-SPECIFIC CONSIDERATIONS:**
- **Theta Decay**: Time decay accelerates as expiration approaches
- **IV Rank**: Consider implied volatility relative to historical range
- **Earnings/Events**: Be aware of upcoming catalysts affecting IV
- **Delta/Gamma**: Understand sensitivity to underlying price movement
- **Bid-Ask Spread**: Wide spreads reduce profit potential

{positions_summary}

**DECISION FORMAT:**
When recommending an options trade, specify:
- Action (BUY_CALL, BUY_PUT, etc.)
- Underlying symbol
- Strike price with rationale
- Expiration date (DTE)
- Number of contracts
- Entry price (limit or market)
- Profit target and stop loss

Always conclude with: FINAL OPTIONS PROPOSAL: **ACTION** - [Details]
Example: FINAL OPTIONS PROPOSAL: **BUY_CALL** - AAPL $200 Call, 30 DTE, 2 contracts @ $5.50
""",
        "decision_format": "ACTION - [Symbol] $[Strike] [Call/Put] [Exp] [Qty] @ $[Price]",
        "final_format": "FINAL OPTIONS PROPOSAL: **ACTION** - [Symbol] $[Strike] [Call/Put] [Exp] [Qty] @ $[Price]"
    }


def extract_options_recommendation(response_content: str) -> Optional[Dict]:
    """
    Extract options trading recommendation from agent response.

    Args:
        response_content: The agent's response content

    Returns:
        Dict with extracted options recommendation or None if not found
    """
    import re

    content = response_content.upper()

    # Look for FINAL OPTIONS PROPOSAL pattern
    patterns = [
        r"FINAL OPTIONS PROPOSAL:\s*\*\*(\w+)\*\*\s*[-:]\s*(.+)",
        r"FINAL OPTIONS DECISION:\s*\*\*(\w+)\*\*\s*[-:]\s*(.+)",
        r"OPTIONS RECOMMENDATION:\s*\*\*(\w+)\*\*\s*[-:]\s*(.+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            action = match.group(1)
            details = match.group(2).strip()

            if action in TradingModeConfig.OPTIONS_ACTIONS:
                # Try to parse details
                recommendation = {
                    "action": action,
                    "details": details,
                    "raw_match": match.group(0)
                }

                # Extract components from details
                # Pattern: [Symbol] $[Strike] [Call/Put] [Exp] [Qty] @ $[Price]
                detail_pattern = r"(\w+)\s+\$?([\d.]+)\s+(CALL|PUT)[,\s]+(\d+)\s*DTE[,\s]+(\d+)\s+CONTRACTS?\s*@\s*\$?([\d.]+)"
                detail_match = re.search(detail_pattern, details)

                if detail_match:
                    recommendation.update({
                        "underlying": detail_match.group(1),
                        "strike": float(detail_match.group(2)),
                        "contract_type": detail_match.group(3).lower(),
                        "dte": int(detail_match.group(4)),
                        "qty": int(detail_match.group(5)),
                        "price": float(detail_match.group(6))
                    })

                return recommendation

    # Fallback - look for action keywords
    for action in TradingModeConfig.OPTIONS_ACTIONS:
        if f"**{action}**" in content[-500:]:  # Check last 500 chars
            return {"action": action, "details": None}

    return None


def validate_options_recommendation(recommendation: Dict, config: Optional[Dict] = None) -> Tuple[bool, str]:
    """
    Validate if options recommendation meets configured constraints.

    Args:
        recommendation: Options recommendation dict
        config: Configuration with options constraints

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not recommendation:
        return False, "No recommendation provided"

    action = recommendation.get("action", "").upper()

    # Validate action is known
    if action not in TradingModeConfig.OPTIONS_ACTIONS:
        return False, f"Unknown options action: {action}"

    # No-trade actions are always valid
    if action in ["HOLD_OPTIONS", "NO_OPTIONS"]:
        return True, ""

    # For trade actions, validate parameters if available
    if config:
        qty = recommendation.get("qty", 1)
        max_contracts = config.get("options_max_contracts", 10)
        if qty > max_contracts:
            return False, f"Quantity {qty} exceeds maximum {max_contracts} contracts"

        dte = recommendation.get("dte")
        if dte:
            min_dte = config.get("options_min_dte", 7)
            max_dte = config.get("options_max_dte", 45)
            if dte < min_dte:
                return False, f"DTE {dte} below minimum {min_dte}"
            if dte > max_dte:
                return False, f"DTE {dte} above maximum {max_dte}"

    return True, ""