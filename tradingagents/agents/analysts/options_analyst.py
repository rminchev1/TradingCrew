"""
Options Market Positioning Analyst for TradingAgents

Analyzes options market data to understand institutional positioning,
expected price movements, and market sentiment for stock trading decisions.

When options trading is enabled, this analyst also recommends specific
option contracts (strike, expiration, quantity) for trading.

Note: This analyst is for stocks only - options data is not available for crypto.
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, ToolMessage
import json

# Import prompt capture utility
try:
    from webui.utils.prompt_capture import capture_agent_prompt
except ImportError:
    # Fallback for when webui is not available
    def capture_agent_prompt(report_type, prompt_content, symbol=None):
        pass


def create_options_analyst(llm, toolkit, config=None):
    """
    Create an Options Market Positioning Analyst node.

    This analyst examines options chain data to provide insights on:
    - Institutional positioning (where smart money is betting)
    - Expected price movements (implied volatility analysis)
    - Key support/resistance levels from options open interest
    - Market sentiment (put/call ratios, IV skew)
    - Unusual options activity that may signal upcoming moves

    When options trading is enabled (config["enable_options_trading"]=True),
    this analyst also recommends specific option contracts for trading.

    Args:
        llm: The language model to use
        toolkit: The toolkit containing data access tools
        config: Optional configuration dict with options trading settings

    Returns:
        A function that can be used as a graph node
    """
    # Check if options trading is enabled
    enable_options_trading = config.get("enable_options_trading", False) if config else False

    def options_analyst_node(state):
        try:
            current_date = state["trade_date"]
            ticker = state["company_of_interest"]

            print(f"[OPTIONS] Options Analyst starting for {ticker} on {current_date}")

            # Check if this is crypto - options not available for crypto
            is_crypto = "/" in ticker or "USD" in ticker.upper() or "USDT" in ticker.upper()

            if is_crypto:
                print(f"[OPTIONS] Skipping options analysis for crypto asset: {ticker}")
                return {
                    "messages": [],
                    "options_report": f"""# OPTIONS ANALYSIS: {ticker}

**Note:** Options market analysis is not available for cryptocurrency assets.

Cryptocurrencies like {ticker} do not have traditional listed options markets on regulated exchanges.
For crypto sentiment analysis, please refer to the Social Sentiment Analyst and News Analyst reports.

FINAL TRANSACTION PROPOSAL: **HOLD** - Unable to provide options-based recommendation for crypto assets.
""",
                }

            # Tools for options analysis
            tools = [
                toolkit.get_options_positioning,
            ]

            # Add options contract tools if options trading is enabled
            if enable_options_trading:
                if hasattr(toolkit, 'get_alpaca_option_contracts'):
                    tools.append(toolkit.get_alpaca_option_contracts)
                if hasattr(toolkit, 'get_recommended_option_contracts'):
                    tools.append(toolkit.get_recommended_option_contracts)

            # Build system message based on trading mode
            if enable_options_trading:
                system_message = """You are an OPTIONS TRADING analyst specializing in identifying profitable options trades based on market positioning, technical analysis, and risk/reward optimization.

**YOUR MISSION:**
Analyze options data and recommend SPECIFIC OPTION CONTRACTS for trading:
1. Identify optimal strikes and expirations based on analysis
2. Calculate risk/reward ratios for recommended trades
3. Consider liquidity (open interest, bid-ask spread)
4. Factor in time decay and volatility expectations
5. Provide actionable trade recommendations

**OPTIONS TRADING ANALYSIS:**

**1. DIRECTIONAL ANALYSIS:**
- Determine bullish/bearish/neutral bias from technical and fundamental factors
- Assess conviction level (high/medium/low) for directional trades
- Identify potential catalysts (earnings, news, technical breakouts)

**2. CONTRACT SELECTION CRITERIA:**
- **Strike Selection:**
  - ATM (at-the-money): Higher delta, lower cost basis risk
  - OTM (out-of-the-money): Higher leverage, higher risk of total loss
  - ITM (in-the-money): Higher premium, lower time decay risk
- **Expiration Selection:**
  - Short-term (< 14 DTE): High theta decay, use for quick moves
  - Medium-term (14-45 DTE): Balance of decay and time for move
  - Longer-term (> 45 DTE): Lower decay, higher premium
- **Liquidity Requirements:**
  - Minimum open interest: 100 contracts
  - Bid-ask spread: < 10% of option price preferred

**3. RISK MANAGEMENT:**
- Maximum loss = premium paid (for long options)
- Define profit target (typically 50-100% of premium)
- Set stop loss level (typically 50% of premium)
- Consider position sizing based on account risk

**4. RECOMMENDATION FORMAT:**
When recommending an options trade, include:
- Action: BUY_CALL, BUY_PUT, WRITE_CALL, WRITE_PUT, etc.
- Contract: Symbol, Strike, Expiration
- Quantity: Number of contracts
- Entry Price: Target entry price or market
- Profit Target: Expected profit level
- Stop Loss: Maximum acceptable loss
- Rationale: Why this specific contract

**FINAL RECOMMENDATION:**
Conclude with: FINAL OPTIONS PROPOSAL: **ACTION** - [Symbol] $[Strike] [Call/Put], [X] DTE, [Y] contracts @ $[Price]
Example: FINAL OPTIONS PROPOSAL: **BUY_CALL** - AAPL $200 Call, 30 DTE, 2 contracts @ $5.50
"""
            else:
                system_message = """You are an OPTIONS MARKET POSITIONING analyst specializing in understanding institutional positioning and market expectations through options data analysis. Your role is to analyze options market data to provide insights for **STOCK TRADING** decisions (not options trading).

**YOUR MISSION:**
Analyze options data across **MULTIPLE EXPIRATIONS** (next 4) to understand:
1. Where are institutions positioned across time horizons? (Large OI at key strikes)
2. What move is the market pricing in? (IV and expected move by expiration)
3. Where are key support/resistance levels? (Highest OI strikes across all expirations)
4. Is sentiment bullish or bearish? (Put/call ratios - aggregate and by expiration)
5. How does positioning change across time? (Term structure analysis)
6. Any unusual activity signaling smart money moves? (Volume spikes vs OI)

**MULTI-EXPIRATION ANALYSIS FRAMEWORK:**

The tool provides data for the **next 4 expirations**, giving you insight into:
- **Near-term** (< 7 DTE): Immediate positioning, gamma exposure, weekly expirations
- **Short-term** (7-30 DTE): Monthly cycles, earnings positioning
- **Medium-term** (30-60 DTE): Swing trade positioning
- **Longer-term** (60+ DTE): Institutional hedges, LEAPS activity

**TERM STRUCTURE INSIGHTS:**
- **Max Pain Trend:** If max pain rises across expirations → bullish drift expected
- **Max Pain Trend:** If max pain falls across expirations → bearish drift expected
- **IV Backwardation** (near-term IV > longer-term IV): Event/catalyst expected soon
- **IV Contango** (longer-term IV > near-term IV): Uncertainty increases over time
- **Positioning Divergence:** If near-term bullish but longer-term bearish → short-term rally then pullback

**AGGREGATE VS INDIVIDUAL EXPIRATION:**
- **Aggregate P/C Ratio:** Overall market sentiment across all expirations
- **Individual P/C Ratios:** How sentiment changes by time horizon
- **Key Levels:** Highest OI strikes across ALL expirations (most significant walls)

**KEY METRICS TO ANALYZE:**

**Sentiment Indicators:**
- Put/Call Volume Ratio: <0.7 = Very Bullish, 0.7-0.9 = Bullish, 0.9-1.1 = Neutral, 1.1-1.3 = Bearish, >1.3 = Very Bearish
- Put/Call OI Ratio: Shows longer-term positioning bias
- IV Skew: Positive = puts expensive (fear), Negative = calls expensive (greed)

**Expected Move & Volatility:**
- ATM Implied Volatility: High IV = big move expected, Low IV = quiet period
- Expected Move: Derived from ATM straddle price, shows anticipated range per expiration

**Key Price Levels (from ALL expirations):**
- Max Pain: Strike where option holders lose most - acts as price magnet near expiration
- High Call OI Strikes: Act as resistance levels (dealers short calls = sell stock to hedge)
- High Put OI Strikes: Act as support levels (dealers short puts = buy stock to hedge)

**Unusual Activity:**
- Volume/OI Ratio > 2x: Indicates new positions being opened
- Activity in specific expirations: May signal expected catalyst timing

**EOD TRADING IMPLICATIONS:**
- Use near-term max pain to anticipate weekly/monthly expiration magnets
- High OI levels from ALL expirations form the most significant support/resistance
- Compare sentiment across expirations to gauge conviction
- IV term structure signals when big moves are expected
- Unusual options activity often precedes stock moves by 1-3 days

**ANALYSIS WORKFLOW:**
1. Call `get_options_positioning` to retrieve multi-expiration options data
2. Review AGGREGATE sentiment (all expirations combined)
3. Compare positioning ACROSS EXPIRATIONS (term structure)
4. Identify highest OI levels across all expirations (key price walls)
5. Analyze max pain term structure (price drift expectations)
6. Check for unusual activity and which expirations are active
7. Synthesize findings into stock trading recommendations

**IMPORTANT:** You are analyzing options data to inform STOCK trading decisions, not to recommend options trades. Focus on what the options market reveals about likely stock price direction and key levels.
"""

            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        " You are a helpful AI assistant, collaborating with other assistants."
                        " Use the provided tools to progress towards answering the question."
                        " If you are unable to fully answer, that's OK; another assistant with different tools"
                        " will help where you left off. Execute what you can to make progress."
                        " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                        " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                        " You have access to the following tools: {tool_names}.\n{system_message}"
                        "For your reference, the current date is {current_date}. The stock we want to analyze is {ticker}",
                    ),
                    MessagesPlaceholder(variable_name="messages"),
                ]
            )

            prompt = prompt.partial(system_message=system_message)
            prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
            prompt = prompt.partial(current_date=current_date)
            prompt = prompt.partial(ticker=ticker)

            # Capture the complete resolved prompt
            try:
                messages_history = list(state["messages"])
                formatted_messages = prompt.format_messages(messages=messages_history)

                if formatted_messages and hasattr(formatted_messages[0], 'content'):
                    complete_prompt = formatted_messages[0].content
                else:
                    tool_names_str = ", ".join([tool.name for tool in tools])
                    complete_prompt = f""" You are a helpful AI assistant, collaborating with other assistants. Use the provided tools to progress towards answering the question. If you are unable to fully answer, that's OK; another assistant with different tools will help where you left off. Execute what you can to make progress. If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable, prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop. You have access to the following tools: {tool_names_str}.

{system_message}

For your reference, the current date is {current_date}. The stock we want to analyze is {ticker}"""

                capture_agent_prompt("options_report", complete_prompt, ticker)
            except Exception as e:
                print(f"[OPTIONS] Warning: Could not capture complete prompt: {e}")
                capture_agent_prompt("options_report", system_message, ticker)

            chain = prompt | llm.bind_tools(tools)

            # Copy the incoming conversation history
            messages_history = list(state["messages"])

            # First LLM response
            result = chain.invoke(messages_history)

            # Handle iterative tool calls
            while getattr(result, "additional_kwargs", {}).get("tool_calls"):
                for tool_call in result.additional_kwargs["tool_calls"]:
                    # Handle different tool call structures
                    if isinstance(tool_call, dict):
                        tool_name = tool_call.get("name") or tool_call.get("function", {}).get("name")
                        tool_args = tool_call.get("args", {}) or tool_call.get("function", {}).get("arguments", {})
                        if isinstance(tool_args, str):
                            try:
                                tool_args = json.loads(tool_args)
                            except json.JSONDecodeError:
                                tool_args = {}
                    else:
                        tool_name = getattr(tool_call, 'name', None)
                        tool_args = getattr(tool_call, 'args', {})

                    # Find the matching tool
                    tool_fn = next((t for t in tools if t.name == tool_name), None)

                    if tool_fn is None:
                        tool_result = f"Tool '{tool_name}' not found."
                        print(f"[OPTIONS] Tool '{tool_name}' not found.")
                    else:
                        try:
                            if hasattr(tool_fn, "invoke"):
                                tool_result = tool_fn.invoke(tool_args)
                            else:
                                tool_result = tool_fn.run(**tool_args)
                        except Exception as tool_err:
                            tool_result = f"Error running tool '{tool_name}': {str(tool_err)}"
                            print(f"[OPTIONS] Error running tool '{tool_name}': {tool_err}")

                    # Append messages
                    tool_call_id = tool_call.get("id") or tool_call.get("tool_call_id")
                    ai_tool_call_msg = AIMessage(
                        content="",
                        additional_kwargs={"tool_calls": [tool_call]},
                    )
                    tool_msg = ToolMessage(
                        content=str(tool_result),
                        tool_call_id=tool_call_id,
                    )

                    messages_history.append(ai_tool_call_msg)
                    messages_history.append(tool_msg)

                # Continue conversation
                result = chain.invoke(messages_history)

            # Ensure final proposal is included - handle both options trading and stock trading modes
            if enable_options_trading:
                # For options trading mode, look for OPTIONS PROPOSAL
                if "FINAL OPTIONS PROPOSAL:" not in result.content:
                    final_prompt = f"""Based on the following options analysis for {ticker}, please provide your final options trading recommendation.

Analysis:
{result.content}

Consider:
1. Overall directional bias from put/call ratios and technical analysis
2. Optimal strike price based on delta and risk tolerance
3. Appropriate expiration based on expected move timeframe
4. Liquidity (open interest) for the selected contract
5. Risk/reward ratio for the trade

You must conclude with: FINAL OPTIONS PROPOSAL: **ACTION** - [Symbol] $[Strike] [Call/Put], [X] DTE, [Y] contracts @ $[Price]
Example: FINAL OPTIONS PROPOSAL: **BUY_CALL** - {ticker} $200 Call, 30 DTE, 2 contracts @ $5.50

If no options trade is recommended, use: FINAL OPTIONS PROPOSAL: **NO_OPTIONS** - [Reason]"""

                    final_chain = llm
                    final_result = final_chain.invoke(final_prompt)

                    combined_content = result.content + "\n\n" + final_result.content
                    result = AIMessage(content=combined_content)
            else:
                # For stock trading mode, look for TRANSACTION PROPOSAL
                if "FINAL TRANSACTION PROPOSAL:" not in result.content:
                    final_prompt = f"""Based on the following options market positioning analysis for {ticker}, please provide your final trading recommendation.

Analysis:
{result.content}

Consider:
1. Overall sentiment from put/call ratios
2. Expected move from IV analysis
3. Key support/resistance from OI levels
4. Any unusual activity signals

You must conclude with: FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** followed by a brief justification based on the options market positioning."""

                    final_chain = llm
                    final_result = final_chain.invoke(final_prompt)

                    combined_content = result.content + "\n\n" + final_result.content
                    result = AIMessage(content=combined_content)

            print(f"[OPTIONS] Options Analyst completed for {ticker}")

            # Build return dict with options recommendation if in options trading mode
            return_dict = {
                "messages": [result],
                "options_report": result.content,
            }

            # Extract options recommendation if in options trading mode
            if enable_options_trading:
                from ..utils.agent_trading_modes import extract_options_recommendation
                options_rec = extract_options_recommendation(result.content)
                if options_rec:
                    return_dict["options_recommendation"] = options_rec
                    return_dict["options_action"] = options_rec.get("action", "NO_OPTIONS")

            return return_dict

        except Exception as e:
            print(f"[OPTIONS] ERROR in Options Analyst: {e}")
            import traceback
            traceback.print_exc()
            # Return an error report so analysis can continue
            ticker = state.get('company_of_interest', 'Unknown')
            error_report = f"""# OPTIONS ANALYSIS: {ticker}

**Error:** Options analysis encountered an error: {str(e)}

Unable to complete options market analysis. Please check the logs for details.

FINAL TRANSACTION PROPOSAL: **HOLD** - Unable to provide options-based recommendation due to error.
"""
            return {
                "messages": [],
                "options_report": error_report,
            }

    return options_analyst_node
