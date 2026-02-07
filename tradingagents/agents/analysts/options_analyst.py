"""
Options Market Positioning Analyst for TradingAgents

Analyzes options market data to understand institutional positioning,
expected price movements, and market sentiment for stock trading decisions.

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


def create_options_analyst(llm, toolkit):
    """
    Create an Options Market Positioning Analyst node.

    This analyst examines options chain data to provide insights on:
    - Institutional positioning (where smart money is betting)
    - Expected price movements (implied volatility analysis)
    - Key support/resistance levels from options open interest
    - Market sentiment (put/call ratios, IV skew)
    - Unusual options activity that may signal upcoming moves

    Args:
        llm: The language model to use
        toolkit: The toolkit containing data access tools

    Returns:
        A function that can be used as a graph node
    """

    def options_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # Check if this is crypto - options not available for crypto
        is_crypto = "/" in ticker or "USD" in ticker.upper() or "USDT" in ticker.upper()

        if is_crypto:
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

        system_message = """You are an OPTIONS MARKET POSITIONING analyst specializing in understanding institutional positioning and market expectations through options data analysis. Your role is to analyze options market data to provide insights for **STOCK TRADING** decisions (not options trading).

**YOUR MISSION:**
Analyze options data to understand:
1. Where are institutions positioned? (Large open interest at key strikes)
2. What move is the market pricing in? (Implied volatility and expected move)
3. Where are key support/resistance levels? (High OI strikes act as magnets)
4. Is sentiment bullish or bearish? (Put/call ratios, IV skew)
5. Any unusual activity signaling smart money moves? (Volume spikes vs OI)

**KEY METRICS TO ANALYZE:**

**Sentiment Indicators:**
- Put/Call Volume Ratio: <0.7 = Very Bullish, 0.7-0.9 = Bullish, 0.9-1.1 = Neutral, 1.1-1.3 = Bearish, >1.3 = Very Bearish
- Put/Call OI Ratio: Shows longer-term positioning bias
- IV Skew: Positive = puts expensive (fear), Negative = calls expensive (greed)

**Expected Move & Volatility:**
- ATM Implied Volatility: High IV = big move expected, Low IV = quiet period
- IV Rank/Percentile: Compares current IV to historical range
- Expected Move: Derived from ATM straddle price, shows anticipated range

**Key Price Levels:**
- Max Pain: Strike where option holders lose most - acts as price magnet near expiration
- High Call OI Strikes: Act as resistance levels (dealers short calls = sell stock to hedge)
- High Put OI Strikes: Act as support levels (dealers short puts = buy stock to hedge)

**Unusual Activity:**
- Volume/OI Ratio > 2x: Indicates new positions being opened
- Large call sweeps: Bullish institutional bets
- Large put sweeps: Bearish institutional bets or hedging

**EOD TRADING IMPLICATIONS:**
- Use max pain to anticipate expiration week price magnets
- High OI levels often act as intraday support/resistance
- Unusual options activity often precedes stock moves by 1-3 days
- IV expansion signals anticipated catalyst (earnings, news)

**ANALYSIS WORKFLOW:**
1. Call `get_options_positioning` to retrieve comprehensive options data
2. Analyze the put/call ratios for sentiment
3. Identify key OI levels for support/resistance
4. Check for unusual activity signals
5. Assess IV environment for expected move
6. Synthesize findings into stock trading recommendations

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

        # Ensure final proposal is included
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

        return {
            "messages": [result],
            "options_report": result.content,
        }

    return options_analyst_node
