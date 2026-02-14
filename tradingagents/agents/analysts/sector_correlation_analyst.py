"""
Sector/Correlation Analyst - Analyzes relative strength, peer comparison, and sector rotation.

This analyst evaluates:
- Relative strength vs sector peers (leading or lagging?)
- Correlation with SPY/QQQ (moving with or against market?)
- Sector rotation signals (money flowing in or out?)
- Divergences signaling overnight positioning opportunities
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


def create_sector_correlation_analyst(llm, toolkit):
    """
    Create a sector/correlation analyst node for the trading graph.

    This analyst evaluates a stock's relative performance within its sector,
    correlation with major indices, and sector rotation dynamics to provide
    EOD trading insights.

    Args:
        llm: The language model to use for analysis
        toolkit: The toolkit containing sector analysis tools

    Returns:
        A function that performs sector/correlation analysis
    """

    def sector_correlation_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # Check if this is a cryptocurrency - skip sector analysis for crypto
        is_crypto = "/" in ticker or "USD" in ticker.upper() or "USDT" in ticker.upper()

        if is_crypto:
            # Crypto doesn't have traditional sector analysis
            crypto_report = f"""# SECTOR/CORRELATION ANALYSIS: {ticker}

**Note:** Sector analysis is not available for cryptocurrency assets.

Cryptocurrencies do not belong to traditional market sectors and cannot be compared
to sector ETFs or equity peers. For crypto correlation analysis, consider:
- BTC correlation (if not BTC itself)
- Overall crypto market cap trends
- Risk-on/risk-off sentiment in traditional markets

FINAL TRANSACTION PROPOSAL: **HOLD** - Unable to provide sector-based recommendation for cryptocurrency.
"""
            return {
                "messages": [AIMessage(content=crypto_report)],
                "sector_correlation_report": crypto_report,
            }

        # Select tools for sector analysis
        tools = [
            toolkit.get_sector_peers,
            toolkit.get_peer_comparison,
            toolkit.get_relative_strength,
            toolkit.get_sector_rotation,
        ]

        system_message = """You are an EOD TRADING sector/correlation analyst specializing in relative strength analysis and sector rotation dynamics. Your role is to evaluate where a stock stands relative to its peers and the broader market, identifying opportunities for overnight positioning.

**CRITICAL FIRST STEP - SECTOR VALIDATION:**
After calling get_sector_peers, you MUST validate the sector classification:

1. Read the business summary carefully - what does this company ACTUALLY do?
2. Does the data provider's sector classification make sense?
3. Are the listed peers actually comparable companies?

**COMMON MISCLASSIFICATIONS TO CORRECT:**
- **Bitcoin/Crypto miners** (MARA, RIOT, CLSK, IREN, HUT, BITF) are often labeled "Financial Services"
  → Correct sector: Crypto Mining. Use peers: MARA, RIOT, CLSK, HUT, BITF, CIFR. Benchmark: Consider using BTC price or SPY.
- **SPACs** may retain old sector data → Check what the actual merged company does
- **Conglomerates/Holdings** → Look at primary business line

**IF SECTOR IS MISCLASSIFIED:**
- State the CORRECT sector based on the business summary
- List ACTUAL peer companies from your knowledge (not the provided list)
- Use a more appropriate benchmark ETF
- Note this correction prominently in your analysis

**EOD TRADING FOCUS:**
- Target holding periods: Overnight with daily reassessment
- Entry signals: Relative strength divergences, sector rotation, peer outperformance
- Exit signals: Loss of relative strength, sector weakness, correlation breakdown
- Risk assessment: Correlation with market, sector concentration risk

**ANALYSIS FRAMEWORK:**

1. **SECTOR IDENTIFICATION & VALIDATION** (Use get_sector_peers first)
   - Read the business summary to understand what the company does
   - VALIDATE or CORRECT the sector classification
   - Identify the correct sector ETF benchmark
   - List appropriate peer stocks (override if data is wrong)

2. **PEER RANKING** (Use get_peer_comparison)
   - Compare 1D, 5D, 10D, 30D performance vs peers
   - Determine if stock is a LEADER (top 25%) or LAGGARD (bottom 25%)
   - Identify momentum divergences from peers
   - NOTE: If peers are wrong, state this and provide qualitative peer comparison

3. **RELATIVE STRENGTH** (Use get_relative_strength)
   - Calculate RS ratio vs the CORRECT sector ETF (not necessarily what tool suggests)
   - Identify RS trend (rising = strengthening, falling = weakening)
   - Detect bullish/bearish divergences between price and RS
   - Note correlation coefficient

4. **SECTOR ROTATION** (Use get_sector_rotation)
   - Rank all 11 sector ETFs by momentum
   - Determine market regime (risk-on vs risk-off)
   - Identify if money is flowing into or out of the stock's ACTUAL sector
   - Compare sector performance to market

**ANALYSIS REQUIREMENTS:**
1. Call get_sector_peers FIRST - then VALIDATE the sector classification
2. Call get_peer_comparison to rank the stock among peers
3. Call get_relative_strength using the CORRECT sector ETF
4. Call get_sector_rotation to understand the broader sector context
5. Synthesize findings into actionable EOD trading insights

**OUTPUT FORMAT:**
Start with sector validation, then include this summary table:

**Sector Validation:**
- Data Provider Sector: [what the tool returned]
- Actual Business: [what the company really does based on summary]
- Validated Sector: [correct sector - same or different]
- Benchmark Used: [ETF symbol and why]
- Peers Used: [list of actual comparable companies]

| Metric | Value | Signal | Overnight Bias |
|--------|-------|--------|----------------|
| Sector Rank | #X of Y | Leader/Laggard | Bullish/Bearish |
| RS vs Sector | X.XX | Rising/Falling | Bullish/Bearish |
| Sector Momentum | #X of 11 | Inflow/Outflow | Bullish/Bearish |
| SPY Correlation | 0.XX | High/Low | Market-dependent |

FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** - [Justification based on sector/correlation analysis]

Focus on relative performance, not absolute price levels. A stock can be down but still be a BUY if it's outperforming its sector during a correction.
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
                    "For your reference, the current date is {current_date}. The company we want to look at is {ticker}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)

        # Capture the COMPLETE resolved prompt that gets sent to the LLM
        try:
            messages_history = list(state["messages"])
            formatted_messages = prompt.format_messages(messages=messages_history)

            if formatted_messages and hasattr(formatted_messages[0], 'content'):
                complete_prompt = formatted_messages[0].content
            else:
                tool_names_str = ", ".join([tool.name for tool in tools])
                complete_prompt = f""" You are a helpful AI assistant, collaborating with other assistants. Use the provided tools to progress towards answering the question. If you are unable to fully answer, that's OK; another assistant with different tools will help where you left off. Execute what you can to make progress. If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable, prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop. You have access to the following tools: {tool_names_str}.

{system_message}

For your reference, the current date is {current_date}. The company we want to look at is {ticker}"""

            capture_agent_prompt("sector_correlation_report", complete_prompt, ticker)
        except Exception as e:
            print(f"[SECTOR] Warning: Could not capture complete prompt: {e}")
            capture_agent_prompt("sector_correlation_report", system_message, ticker)

        chain = prompt | llm.bind_tools(tools)

        # Copy the incoming conversation history so we can append to it when the model makes tool calls
        messages_history = list(state["messages"])

        # First LLM response
        result = chain.invoke(messages_history)

        # Handle iterative tool calls until the model stops requesting them
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
                    # Handle LangChain ToolCall objects
                    tool_name = getattr(tool_call, 'name', None)
                    tool_args = getattr(tool_call, 'args', {})

                # Find the matching tool by name
                tool_fn = next((t for t in tools if t.name == tool_name), None)

                if tool_fn is None:
                    tool_result = f"Tool '{tool_name}' not found."
                    print(f"[SECTOR] Tool '{tool_name}' not found.")
                else:
                    try:
                        # LangChain Tool objects expose `.run` (string IO) as well as `.invoke` (dict/kwarg IO)
                        if hasattr(tool_fn, "invoke"):
                            tool_result = tool_fn.invoke(tool_args)
                        else:
                            tool_result = tool_fn.run(**tool_args)

                    except Exception as tool_err:
                        tool_result = f"Error running tool '{tool_name}': {str(tool_err)}"

                # Append the assistant tool call and tool result messages so the LLM can continue the conversation
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

            # Ask the LLM to continue with the new context
            result = chain.invoke(messages_history)

        # Check if the result already contains FINAL TRANSACTION PROPOSAL
        if "FINAL TRANSACTION PROPOSAL:" not in result.content:
            # Create a simple prompt that includes the analysis content directly
            final_prompt = f"""Based on the following sector/correlation analysis for {ticker}, please provide your final trading recommendation.

Analysis:
{result.content}

You must conclude with: FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** followed by a brief justification based on sector relative strength and rotation analysis."""

            # Use a simple chain without tools for the final recommendation
            final_chain = llm
            final_result = final_chain.invoke(final_prompt)

            # Combine the analysis with the final proposal
            combined_content = result.content + "\n\n" + final_result.content
            result = AIMessage(content=combined_content)

        return {
            "messages": [result],
            "sector_correlation_report": result.content,
        }

    return sector_correlation_analyst_node
