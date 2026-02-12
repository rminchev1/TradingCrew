"""
Options Trader Agent for TradingAgents

Specializes in executing options trading recommendations from the Options Analyst.
Makes final decisions on options trades considering:
- Options analyst recommendations
- Current options positions
- Account constraints
- Risk parameters

This agent is only active when options trading is enabled.
"""

import functools
from typing import Dict, Any, Optional

from ..utils.agent_trading_modes import (
    get_options_trading_context,
    extract_options_recommendation,
    validate_options_recommendation,
    format_final_decision,
    TradingModeConfig,
)
from tradingagents.dataflows.options_trading_utils import (
    get_options_positions,
    get_recommended_contracts,
    execute_options_trading_action,
)
from tradingagents.dataflows.alpaca_utils import AlpacaUtils

# Import prompt capture utility
try:
    from webui.utils.prompt_capture import capture_agent_prompt
except ImportError:
    def capture_agent_prompt(report_type, prompt_content, symbol=None):
        pass


def create_options_trader(llm, memory, config=None):
    """
    Create an Options Trader agent node.

    This agent:
    1. Reviews options analyst recommendations
    2. Validates against account constraints
    3. Makes final execution decisions
    4. Generates options trade plan

    Args:
        llm: The language model to use
        memory: Memory system for learning from past trades
        config: Configuration dict with options trading settings

    Returns:
        A function that can be used as a graph node
    """
    config = config or {}

    def options_trader_node(state, name):
        company_name = state["company_of_interest"]
        current_date = state.get("trade_date", "")

        print(f"[OPTIONS_TRADER] Starting options trading decision for {company_name}")

        # Get analyst reports
        options_report = state.get("options_report", "")
        market_report = state.get("market_report", "")
        trader_plan = state.get("trader_investment_plan", "")

        # Get options recommendation from options analyst
        options_recommendation = state.get("options_recommendation", {})
        options_action = state.get("options_action", "NO_OPTIONS")

        # Get current options positions
        current_options = get_options_positions()

        # Get current stock position
        current_stock_position = AlpacaUtils.get_current_position_state(company_name)

        # Get account info
        account_info = AlpacaUtils.get_account_info()
        buying_power = account_info.get("buying_power", 0)

        # Build options context
        options_context = get_options_trading_context(config, current_options)

        # Filter options positions for this symbol
        symbol_options = [
            p for p in current_options
            if p.get("underlying", "").upper() == company_name.upper().replace("/", "")
        ]

        # Build positions summary
        if symbol_options:
            positions_desc = f"\n**Current Options Positions for {company_name}:**\n"
            for pos in symbol_options:
                positions_desc += (
                    f"- {pos['symbol']}: {pos['qty']} {pos['contract_type']}s "
                    f"@ ${pos['strike']:.2f}, exp {pos['expiration']}\n"
                    f"  Entry: ${pos['avg_entry_price']:.2f}, "
                    f"Current: ${pos['current_price']:.2f}, "
                    f"P/L: ${pos['unrealized_pl']:.2f} ({pos['unrealized_pl_pct']:.1f}%)\n"
                )
        else:
            positions_desc = f"\n**No current options positions for {company_name}.**"

        # Build recommendation summary
        if options_recommendation and options_action not in ["NO_OPTIONS", "HOLD_OPTIONS"]:
            rec_desc = f"""
**Options Analyst Recommendation:**
- Action: {options_action}
- Details: {options_recommendation.get('details', 'See options report')}
"""
            if options_recommendation.get('strike'):
                rec_desc += f"- Strike: ${options_recommendation['strike']:.2f}\n"
            if options_recommendation.get('dte'):
                rec_desc += f"- DTE: {options_recommendation['dte']} days\n"
            if options_recommendation.get('qty'):
                rec_desc += f"- Quantity: {options_recommendation['qty']} contracts\n"
            if options_recommendation.get('price'):
                rec_desc += f"- Target Price: ${options_recommendation['price']:.2f}\n"
        else:
            rec_desc = "\n**No specific options trade recommended by analyst.**"

        # Get past memories for similar situations
        curr_situation = f"{options_report}\n\n{market_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)
        past_memory_str = ""
        for rec in past_memories:
            past_memory_str += rec.get("recommendation", "") + "\n\n"

        # Build system prompt
        system_prompt = f"""You are an OPTIONS TRADER specializing in executing options trades at end-of-day.

{options_context['instructions']}

**ACCOUNT STATUS:**
- Buying Power: ${buying_power:,.2f}
- Stock Position: {current_stock_position}
{positions_desc}

**OPTIONS ANALYST REPORT:**
{options_report[:2000] if options_report else 'No options analysis available.'}

{rec_desc}

**STOCK TRADER ANALYSIS:**
{trader_plan[:1000] if trader_plan else 'No stock trader analysis available.'}

**YOUR DECISION CRITERIA:**

1. **Validate Recommendation:**
   - Check if recommended contract meets liquidity requirements
   - Verify strike/expiration are within acceptable parameters
   - Ensure position size fits account risk limits

2. **Risk Assessment:**
   - Maximum loss = premium paid (for long options)
   - Consider existing positions and portfolio delta
   - Account for overnight/weekend risk

3. **Execution Decision:**
   - Confirm or modify the analyst's recommendation
   - Specify exact contract, quantity, and order type
   - Set clear profit target and stop loss

4. **Position Management:**
   - If holding existing positions, decide: hold, add, reduce, or close
   - Consider rolling positions if near expiration
   - Factor in upcoming events (earnings, dividends, etc.)

**PREVIOUS TRADES & LESSONS:**
{past_memory_str if past_memory_str else 'No relevant past trades.'}

**FINAL DECISION:**
Provide your options trading decision with:
1. Detailed rationale for the trade (or no-trade)
2. Risk/reward analysis
3. Specific execution instructions

Conclude with: FINAL OPTIONS PROPOSAL: **ACTION** - [Details]
Example: FINAL OPTIONS PROPOSAL: **BUY_CALL** - {company_name} $150 Call, 30 DTE, 2 contracts @ $3.50

If no options trade is warranted, use:
FINAL OPTIONS PROPOSAL: **NO_OPTIONS** - [Reason for not trading]
"""

        # Capture prompt
        capture_agent_prompt("options_trade_plan", system_prompt, company_name)

        # Call LLM for decision
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Based on the options analysis for {company_name}, make your final options trading decision for end-of-day execution."}
        ]

        result = llm.invoke(messages)
        response_content = result.content if hasattr(result, 'content') else str(result)

        # Ensure we have a final proposal
        if "FINAL OPTIONS PROPOSAL:" not in response_content:
            # Generate final proposal if missing
            final_prompt = f"""Based on your analysis, provide your final options trading decision.

You must conclude with one of:
- FINAL OPTIONS PROPOSAL: **BUY_CALL** - [Details]
- FINAL OPTIONS PROPOSAL: **BUY_PUT** - [Details]
- FINAL OPTIONS PROPOSAL: **SELL_CALL** - [Details]
- FINAL OPTIONS PROPOSAL: **SELL_PUT** - [Details]
- FINAL OPTIONS PROPOSAL: **WRITE_CALL** - [Details]
- FINAL OPTIONS PROPOSAL: **WRITE_PUT** - [Details]
- FINAL OPTIONS PROPOSAL: **HOLD_OPTIONS** - [Reason]
- FINAL OPTIONS PROPOSAL: **NO_OPTIONS** - [Reason]
"""
            final_result = llm.invoke(final_prompt)
            final_content = final_result.content if hasattr(final_result, 'content') else str(final_result)
            response_content = response_content + "\n\n---\n\n## Final Options Decision\n\n" + final_content

        # Extract final recommendation
        final_recommendation = extract_options_recommendation(response_content)

        # Validate recommendation against config
        if final_recommendation:
            is_valid, error_msg = validate_options_recommendation(final_recommendation, config)
            if not is_valid:
                print(f"[OPTIONS_TRADER] Recommendation validation failed: {error_msg}")
                # Add warning to response
                response_content += f"\n\n**Warning:** Recommendation validation: {error_msg}"

        # Determine final action
        final_action = "NO_OPTIONS"
        if final_recommendation:
            final_action = final_recommendation.get("action", "NO_OPTIONS")

        print(f"[OPTIONS_TRADER] Final options decision for {company_name}: {final_action}")

        return {
            "messages": [result],
            "options_trade_plan": response_content,
            "options_action": final_action,
            "options_recommendation": final_recommendation or {},
            "sender": name,
        }

    return functools.partial(options_trader_node, name="Options Trader")
