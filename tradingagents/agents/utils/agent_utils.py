from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage
from typing import List
from typing import Annotated
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import RemoveMessage
from langchain_core.tools import tool
from datetime import date, timedelta, datetime
import functools
import pandas as pd
import os
from dateutil.relativedelta import relativedelta
from langchain_openai import ChatOpenAI
import tradingagents.dataflows.interface as interface
from tradingagents.default_config import DEFAULT_CONFIG
import json
import time
from functools import wraps


def _get_current_symbol():
    """Get the current symbol from thread-local storage (preferred) or global state (fallback)."""
    try:
        from webui.utils.state import get_thread_symbol, app_state
        # Prefer thread-local symbol for parallel execution safety
        symbol = get_thread_symbol()
        if symbol:
            return symbol
        # Fallback to global state - this path should only be hit in CLI mode
        # or single-ticker analysis. Log if this happens during parallel execution.
        fallback = getattr(app_state, 'analyzing_symbol', None) or getattr(app_state, 'current_symbol', None)
        if fallback and len(getattr(app_state, 'analyzing_symbols', set())) > 1:
            print(f"[WARNING] Thread-local symbol not set during parallel execution, using fallback: {fallback}")
        return fallback
    except Exception:
        return None


def timing_wrapper(analyst_type, timeout_seconds=120):
    """
    Decorator to time function calls and track them for UI display with timeout protection
    
    Args:
        analyst_type: Type of analyst (MARKET, SOCIAL, etc.)
        timeout_seconds: Maximum execution time allowed (default 120s)
    """
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Start timing
            start_time = time.time()
            
            # Get the function (tool) name
            tool_name = func.__name__
            
            # Timeout handling using ThreadPoolExecutor (cross-platform)
            import concurrent.futures
            
            def run_function():
                return func(*args, **kwargs)
            
            # Format tool inputs for display
            input_summary = {}
            
            # Get function signature to map args to parameter names
            import inspect
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())
            
            # Map positional args to parameter names
            for i, arg in enumerate(args):
                if i < len(param_names):
                    param_name = param_names[i]
                    # Truncate long string arguments for display
                    if isinstance(arg, str) and len(arg) > 100:
                        input_summary[param_name] = arg[:97] + "..."
                    else:
                        input_summary[param_name] = arg
            
            # Add keyword arguments
            for key, value in kwargs.items():
                if isinstance(value, str) and len(value) > 100:
                    input_summary[key] = value[:97] + "..."
                else:
                    input_summary[key] = value

            print(f"[{analyst_type}] 🔧 Starting tool '{tool_name}' with inputs: {input_summary}")

            # Notify the state management system of tool call execution
            try:
                from webui.utils.state import app_state
                import datetime
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")

                # Pipeline pause/stop checkpoint before each tool call
                try:
                    interrupt_status = app_state.check_pipeline_interrupt(symbol=_get_current_symbol())
                    if interrupt_status == "stopped":
                        print(f"[{analyst_type}] Pipeline stopped before tool '{tool_name}' could execute")
                        return f"Error: Pipeline stopped. Tool '{tool_name}' was not executed."
                except Exception:
                    pass  # If check fails (e.g. CLI mode), continue normally

                # Execute the function with timeout protection
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_function)
                    try:
                        # Wait for the function to complete with timeout
                        result = future.result(timeout=timeout_seconds)
                        
                        # Check for very slow execution (warn if > 30s)
                        partial_elapsed = time.time() - start_time
                        if partial_elapsed > 120:
                            print(f"[{analyst_type}] ⚠️ Slow execution warning: {tool_name} took {partial_elapsed:.1f}s")
                            
                    except concurrent.futures.TimeoutError:
                        elapsed = time.time() - start_time
                        timeout_msg = f"TIMEOUT: Tool '{tool_name}' exceeded {timeout_seconds}s limit (stopped at {elapsed:.1f}s)"
                        print(f"[{analyst_type}] ⏰ {timeout_msg}")
                        
                        # Store timeout info
                        tool_call_info = {
                            "timestamp": timestamp,
                            "tool_name": tool_name,
                            "inputs": input_summary,
                            "output": f"TIMEOUT ERROR: {timeout_msg}",
                            "execution_time": f"{elapsed:.2f}s",
                            "status": "timeout",
                            "agent_type": analyst_type,
                            "symbol": _get_current_symbol(),  # Use thread-safe symbol lookup
                            "error_details": {
                                "error_type": "TimeoutError",
                                "timeout_seconds": timeout_seconds,
                                "actual_time": elapsed
                            }
                        }
                        
                        app_state.tool_calls_log.append(tool_call_info)
                        app_state.tool_calls_count = len(app_state.tool_calls_log)
                        app_state.needs_ui_update = True
                        
                        # Return a timeout error message
                        return f"Error: Tool '{tool_name}' timed out after {timeout_seconds}s. This may indicate network issues, API problems, or insufficient data."
                
                # Calculate execution time
                elapsed = time.time() - start_time
                print(f"[{analyst_type}] ✅ Tool '{tool_name}' completed in {elapsed:.2f}s")
                
                # Format the result for display (truncate if too long)
                result_summary = result
                
                # Store the complete tool call information including the output
                # Get current symbol from thread-local storage (thread-safe for parallel execution)
                current_symbol = _get_current_symbol()

                tool_call_info = {
                    "timestamp": timestamp,
                    "tool_name": tool_name,
                    "inputs": input_summary,
                    "output": result_summary,
                    "execution_time": f"{elapsed:.2f}s",
                    "status": "success",
                    "agent_type": analyst_type,  # Add agent type for filtering
                    "symbol": current_symbol  # Add symbol for filtering (thread-safe)
                }
                
                app_state.tool_calls_log.append(tool_call_info)
                app_state.tool_calls_count = len(app_state.tool_calls_log)
                app_state.needs_ui_update = True
                print(f"[TOOL TRACKER] Registered tool call: {tool_name} for {analyst_type} (Total: {app_state.tool_calls_count})")
                
                return result
                
            except Exception as e:
                elapsed = time.time() - start_time
                
                # Enhanced error logging with detailed debugging info
                error_details = {
                    "tool_name": tool_name,
                    "inputs": input_summary,
                    "execution_time": f"{elapsed:.2f}s",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
                
                # Add specific error handling for common issues
                detailed_error = str(e)
                if "api key" in str(e).lower():
                    detailed_error = f"API KEY ERROR: {str(e)}\n💡 SOLUTION: Check your API key configuration in the .env file"
                elif "organization" in str(e).lower() and "verification" in str(e).lower():
                    detailed_error = f"OPENAI ORG ERROR: {str(e)}\n💡 SOLUTION: Your OpenAI organization may need verification or you may have billing issues"
                elif "timeout" in str(e).lower() or "timed out" in str(e).lower():
                    detailed_error = f"TIMEOUT ERROR: {str(e)}\n💡 SOLUTION: Network or API service may be slow. Try again in a few minutes"
                elif "rate limit" in str(e).lower():
                    detailed_error = f"RATE LIMIT ERROR: {str(e)}\n💡 SOLUTION: You've hit API rate limits. Wait before retrying"
                elif "connection" in str(e).lower():
                    detailed_error = f"CONNECTION ERROR: {str(e)}\n💡 SOLUTION: Check your internet connection and API service status"
                elif "insufficient data" in str(e).lower():
                    detailed_error = f"DATA ERROR: {str(e)}\n💡 SOLUTION: Try a different date range or check if the symbol is correct"
                
                print(f"[{analyst_type}] ❌ Tool '{tool_name}' failed after {elapsed:.2f}s")
                print(f"[{analyst_type}] 🔍 ERROR DETAILS:")
                print(f"   Error Type: {error_details['error_type']}")
                print(f"   Error Message: {detailed_error}")
                print(f"   Tool Inputs: {input_summary}")
                
                # Store the failed tool call information with enhanced details
                try:
                    from webui.utils.state import app_state
                    import datetime
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")

                    # Get current symbol from thread-local storage (thread-safe for parallel execution)
                    current_symbol = _get_current_symbol()

                    tool_call_info = {
                        "timestamp": timestamp,
                        "tool_name": tool_name,
                        "inputs": input_summary,
                        "output": f"ERROR ({error_details['error_type']}): {detailed_error}",
                        "execution_time": f"{elapsed:.2f}s",
                        "status": "error",
                        "agent_type": analyst_type,  # Add agent type for filtering
                        "symbol": current_symbol,  # Add symbol for filtering (thread-safe)
                        "error_details": error_details  # Add structured error details
                    }
                    
                    app_state.tool_calls_log.append(tool_call_info)
                    app_state.tool_calls_count = len(app_state.tool_calls_log)
                    app_state.needs_ui_update = True
                    print(f"[TOOL TRACKER] Registered failed tool call: {tool_name} for {analyst_type} (Total: {app_state.tool_calls_count})")
                except Exception as track_error:
                    print(f"[TOOL TRACKER] Failed to track failed tool call: {track_error}")
                
                raise  # Re-raise the exception
                
        return wrapper
    return decorator


def create_msg_delete():
    def delete_messages(state):
        """To prevent message history from overflowing, regularly clear message history after a stage of the pipeline is done"""
        messages = state["messages"]
        return {"messages": [RemoveMessage(id=m.id) for m in messages]}

    return delete_messages


class Toolkit:
    _config = DEFAULT_CONFIG.copy()

    @classmethod
    def update_config(cls, config):
        """Update the class-level configuration."""
        cls._config.update(config)

    @property
    def config(self):
        """Access the configuration."""
        return self._config

    def __init__(self, config=None):
        if config:
            self.update_config(config)

    @staticmethod
    @tool
    @timing_wrapper("NEWS")
    def get_reddit_news(
        curr_date: Annotated[str, "Date you want to get news for in yyyy-mm-dd format"],
    ) -> str:
        """
        Retrieve global news from Reddit within a specified time frame.
        Args:
            curr_date (str): Date you want to get news for in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing the latest global news from Reddit in the specified time frame.
        """
        
        global_news_result = interface.get_reddit_global_news(curr_date, 7, 5)

        return global_news_result

    @staticmethod
    @tool
    @timing_wrapper("NEWS")
    def get_finnhub_news(
        ticker: Annotated[
            str,
            "Search query of a company, e.g. 'AAPL, TSM, etc.",
        ],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest news about a given stock from Finnhub within a date range
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            start_date (str): Start date in yyyy-mm-dd format
            end_date (str): End date in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing news about the company within the date range from start_date to end_date
        """

        end_date_str = end_date

        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        look_back_days = (end_date - start_date).days

        finnhub_news_result = interface.get_finnhub_news(
            ticker, end_date_str, look_back_days
        )

        return finnhub_news_result

    @staticmethod
    @tool
    @timing_wrapper("NEWS")
    def get_finnhub_news_online(
        ticker: Annotated[str, "Stock ticker symbol, e.g. 'AAPL', 'TSLA'"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
        look_back_days: Annotated[int, "Number of days to look back for news"] = 7,
    ):
        """
        Retrieve LIVE news about a company from Finnhub API.
        This is the preferred tool for getting real-time stock news.

        Args:
            ticker (str): Stock ticker symbol (e.g., 'AAPL', 'NVDA')
            curr_date (str): Current date in yyyy-mm-dd format
            look_back_days (int): Number of days to look back (default: 7)

        Returns:
            str: Formatted news articles with headlines, summaries, sources, and dates
        """

        finnhub_news_result = interface.get_finnhub_news_online(
            ticker, curr_date, look_back_days
        )

        return finnhub_news_result

    @staticmethod
    @tool
    @timing_wrapper("SOCIAL")
    def get_reddit_stock_info(
        ticker: Annotated[
            str,
            "Ticker of a company. e.g. AAPL, TSM",
        ],
        curr_date: Annotated[str, "Current date you want to get news for"],
    ) -> str:
        """
        Retrieve the latest news about a given stock from Reddit, given the current date.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): current date in yyyy-mm-dd format to get news for
        Returns:
            str: A formatted dataframe containing the latest news about the company on the given date
        """

        stock_news_results = interface.get_reddit_company_news(ticker, curr_date, 7, 5)

        return stock_news_results

    @staticmethod
    @tool
    @timing_wrapper("MARKET")
    def get_alpaca_data(
        symbol: Annotated[str, "ticker symbol (stocks: AAPL, TSM; crypto: ETH/USD, BTC/USD)"],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
        timeframe: Annotated[str, "Timeframe for data: 1Hour, 4Hour, 1Day"] = "1Day",
    ) -> str:
        """
        Retrieve stock and cryptocurrency price data from Alpaca.
        For crypto symbols, use format with slash: ETH/USD, BTC/USD, SOL/USD
        For stock symbols, use standard format: AAPL, TSM, NVDA
        Args:
            symbol (str): Ticker symbol - stocks: AAPL, TSM; crypto: ETH/USD, BTC/USD
            start_date (str): Start date in yyyy-mm-dd format
            end_date (str): End date in yyyy-mm-dd format
            timeframe (str): Timeframe for data (1Hour, 4Hour, 1Day)
        Returns:
            str: A formatted dataframe containing the price data for the specified ticker symbol in the specified date range.
        """

        result_data = interface.get_alpaca_data(symbol, start_date, end_date, timeframe)

        return result_data

    @staticmethod
    @tool
    @timing_wrapper("MARKET")
    def get_stockstats_indicators_report(
        symbol: Annotated[str, "ticker symbol of the company"],
        indicator: Annotated[
            str, "technical indicator to get the analysis and report of"
        ],
        curr_date: Annotated[
            str, "The current trading date you are trading on, YYYY-mm-dd"
        ],
        look_back_days: Annotated[int, "how many days to look back"] = 30,
    ) -> str:
        """
        Retrieve stock stats indicators for a given ticker symbol and indicator.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            indicator (str): Technical indicator to get the analysis and report of
            curr_date (str): The current trading date you are trading on, YYYY-mm-dd
            look_back_days (int): How many days to look back, default is 30
        Returns:
            str: A formatted dataframe containing the stock stats indicators for the specified ticker symbol and indicator.
        """

        result_stockstats = interface.get_stock_stats_indicators_window(
            symbol, indicator, curr_date, look_back_days, False
        )

        return result_stockstats

    @staticmethod
    @tool
    @timing_wrapper("MARKET")
    def get_stockstats_indicators_report_online(
        symbol: Annotated[str, "ticker symbol (stocks: AAPL, TSM; crypto: ETH/USD, BTC/USD)"],
        indicator: Annotated[
            str, "technical indicator to get the analysis and report of"
        ],
        curr_date: Annotated[
            str, "The current trading date you are trading on, YYYY-mm-dd"
        ],
        look_back_days: Annotated[int, "how many days to look back"] = 30,
    ) -> str:
        """
        Retrieve technical indicators for stocks and crypto symbols.
        For crypto symbols, use format with slash: ETH/USD, BTC/USD, SOL/USD
        For stock symbols, use standard format: AAPL, TSM, NVDA
        Args:
            symbol (str): Ticker symbol - stocks: AAPL, TSM; crypto: ETH/USD, BTC/USD
            indicator (str): Technical indicator to get the analysis and report of, or 'all' for comprehensive report
            curr_date (str): The current trading date you are trading on, YYYY-mm-dd
            look_back_days (int): How many days to look back, default is 30
        Returns:
            str: A formatted report containing the stock stats indicators for the specified ticker symbol and indicator.
        """

        if indicator.lower() == 'all':
            # Handle comprehensive indicator report
            key_indicators = [
                'close_10_ema',     # 10-day Exponential Moving Average
                'close_20_sma',     # 20-day Simple Moving Average  
                'close_50_sma',     # 50-day Simple Moving Average
                'rsi_14',           # 14-day Relative Strength Index
                'macd',             # Moving Average Convergence Divergence
                'boll_ub',          # Bollinger Bands Upper Band
                'boll_lb',          # Bollinger Bands Lower Band
                'volume_delta'      # Volume Delta
            ]
            
            results = []
            results.append(f"# Comprehensive Technical Indicators Report for {symbol} on {curr_date}")
            results.append("")
            
            for ind in key_indicators:
                try:
                    result = interface.get_stockstats_indicator(symbol, ind, curr_date, True)
                    # Clean up the result format
                    if result.startswith(f"## {ind} for"):
                        # Extract just the value part
                        value_part = result.split(": ")[-1]
                        indicator_name = ind.replace('_', ' ').title()
                        results.append(f"**{indicator_name}:** {value_part}")
                    else:
                        results.append(f"**{ind}:** {result}")
                except Exception as e:
                    results.append(f"**{ind}:** Error - {str(e)}")
            
            results.append("")
            results.append("## EOD Trading Analysis")
            results.append("These indicators provide key signals for end-of-day trading decisions:")
            results.append("- **EMAs/SMAs:** Trend direction and support/resistance levels")
            results.append("- **RSI:** Overbought (>70) or oversold (<30) conditions")  
            results.append("- **MACD:** Momentum and trend change signals")
            results.append("- **Bollinger Bands:** Volatility and price extremes")
            
            return "\n".join(results)
        else:
            # For single indicator, use the existing method
            result_stockstats = interface.get_stockstats_indicator(
                symbol, indicator, curr_date, True
            )
            return result_stockstats

    @staticmethod
    @tool
    @timing_wrapper("FUNDAMENTALS")
    def get_finnhub_company_insider_sentiment(
        ticker: Annotated[str, "ticker symbol for the company"],
        curr_date: Annotated[
            str,
            "current date of you are trading at, yyyy-mm-dd",
        ],
    ):
        """
        Retrieve insider sentiment information about a company (retrieved from public SEC information) for the past 30 days
        Args:
            ticker (str): ticker symbol of the company
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
            str: a report of the sentiment in the past 30 days starting at curr_date
        """

        data_sentiment = interface.get_finnhub_company_insider_sentiment(
            ticker, curr_date, 30
        )

        return data_sentiment

    @staticmethod
    @tool
    @timing_wrapper("FUNDAMENTALS")
    def get_finnhub_company_insider_transactions(
        ticker: Annotated[str, "ticker symbol"],
        curr_date: Annotated[
            str,
            "current date you are trading at, yyyy-mm-dd",
        ],
    ):
        """
        Retrieve insider transaction information about a company (retrieved from public SEC information) for the past 30 days
        Args:
            ticker (str): ticker symbol of the company
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
            str: a report of the company's insider transactions/trading information in the past 30 days
        """

        data_trans = interface.get_finnhub_company_insider_transactions(
            ticker, curr_date, 30
        )

        return data_trans

    @staticmethod
    @tool
    @timing_wrapper("FUNDAMENTALS")
    def get_simfin_balance_sheet(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[
            str,
            "reporting frequency of the company's financial history: annual/quarterly",
        ],
        curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    ):
        """
        Retrieve the most recent balance sheet of a company
        Args:
            ticker (str): ticker symbol of the company
            freq (str): reporting frequency of the company's financial history: annual / quarterly
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
            str: a report of the company's most recent balance sheet
        """

        data_balance_sheet = interface.get_simfin_balance_sheet(ticker, freq, curr_date)

        return data_balance_sheet

    @staticmethod
    @tool
    @timing_wrapper("FUNDAMENTALS")
    def get_simfin_cashflow(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[
            str,
            "reporting frequency of the company's financial history: annual/quarterly",
        ],
        curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    ):
        """
        Retrieve the most recent cash flow statement of a company
        Args:
            ticker (str): ticker symbol of the company
            freq (str): reporting frequency of the company's financial history: annual / quarterly
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
                str: a report of the company's most recent cash flow statement
        """

        data_cashflow = interface.get_simfin_cashflow(ticker, freq, curr_date)

        return data_cashflow

    @staticmethod
    @tool
    def get_coindesk_news(
        ticker: Annotated[str, "Ticker symbol, e.g. 'BTC/USD', 'ETH/USD', 'ETH', etc."],
        num_sentences: Annotated[int, "Number of sentences to include from news body."] = 5,
    ):
        """
        Retrieve news for a cryptocurrency.
        This function checks if the ticker is a crypto pair (like BTC/USD) and extracts the base currency.
        Then it fetches news for that cryptocurrency from CryptoCompare.

        Args:
            ticker (str): Ticker symbol for the cryptocurrency.
            num_sentences (int): Number of sentences to extract from the body of each news article.

        Returns:
            str: Formatted string containing news.
        """
        return interface.get_coindesk_news(ticker, num_sentences)

    @staticmethod
    @tool
    @timing_wrapper("FUNDAMENTALS")
    def get_simfin_income_stmt(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[
            str,
            "reporting frequency of the company's financial history: annual/quarterly",
        ],
        curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    ):
        """
        Retrieve the most recent income statement of a company
        Args:
            ticker (str): ticker symbol of the company
            freq (str): reporting frequency of the company's financial history: annual / quarterly
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
                str: a report of the company's most recent income statement
        """

        data_income_stmt = interface.get_simfin_income_statements(
            ticker, freq, curr_date
        )

        return data_income_stmt

    @staticmethod
    @tool
    @timing_wrapper("SOCIAL", timeout_seconds=300)  # Extended timeout for web search + reasoning
    def get_stock_news_openai(
        ticker: Annotated[str, "the company's ticker"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest news about a given stock by using OpenAI's news API.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted string containing the latest news about the company on the given date.
        """

        openai_news_results = interface.get_stock_news_openai(ticker, curr_date)

        return openai_news_results

    @staticmethod
    @tool
    @timing_wrapper("FUNDAMENTALS", timeout_seconds=300)  # Extended timeout for web search + reasoning
    def get_fundamentals_openai(
        ticker: Annotated[str, "the company's ticker"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest fundamental information about a given stock on a given date by using OpenAI's news API.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted string containing the latest fundamental information about the company on the given date.
        """

        openai_fundamentals_results = interface.get_fundamentals_openai(
            ticker, curr_date
        )

        return openai_fundamentals_results

    @staticmethod
    @tool
    @timing_wrapper("FUNDAMENTALS")
    def get_fundamentals_yfinance(
        ticker: Annotated[str, "the company's ticker symbol"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """
        Retrieve comprehensive fundamental data for a stock using Yahoo Finance.
        Includes valuation metrics (P/E, P/B, EV/EBITDA), profitability (margins, ROE, ROA),
        growth rates, financial health (debt, cash flow), dividends, and analyst estimates.

        Args:
            ticker (str): Ticker of a company. e.g. AAPL, NVDA, MSFT
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted fundamental analysis report with key metrics and assessments.
        """
        return interface.get_fundamentals_yfinance(ticker, curr_date)

    @staticmethod
    @tool
    @timing_wrapper("FUNDAMENTALS")
    def get_earnings_calendar(
        ticker: Annotated[str, "Stock or crypto ticker symbol"],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ) -> str:
        """
        Retrieve earnings calendar data for stocks or major events for crypto.
        For stocks: Shows earnings dates, EPS estimates vs actuals, revenue estimates vs actuals, and surprise analysis.
        For crypto: Shows major protocol events, upgrades, and announcements that could impact price.
        
        Args:
            ticker (str): Stock ticker (e.g. AAPL, TSLA) or crypto ticker (e.g. BTC/USD, ETH/USD, SOL/USD)
            start_date (str): Start date in yyyy-mm-dd format
            end_date (str): End date in yyyy-mm-dd format
            
        Returns:
            str: Formatted earnings calendar data with estimates, actuals, and surprise analysis
        """
        
        earnings_calendar_results = interface.get_earnings_calendar(
            ticker, start_date, end_date
        )
        
        return earnings_calendar_results

    @staticmethod
    @tool
    @timing_wrapper("FUNDAMENTALS")
    def get_earnings_surprise_analysis(
        ticker: Annotated[str, "Stock ticker symbol"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
        lookback_quarters: Annotated[int, "Number of quarters to analyze"] = 8,
    ) -> str:
        """
        Analyze historical earnings surprises to identify patterns and trading implications.
        Shows consistency of beats/misses, magnitude of surprises, and seasonal patterns.
        
        Args:
            ticker (str): Stock ticker symbol, e.g. AAPL, TSLA
            curr_date (str): Current date in yyyy-mm-dd format
            lookback_quarters (int): Number of quarters to analyze (default 8 = ~2 years)
            
        Returns:
            str: Analysis of earnings surprise patterns with trading implications
        """
        
        earnings_surprise_results = interface.get_earnings_surprise_analysis(
            ticker, curr_date, lookback_quarters
        )
        
        return earnings_surprise_results

    @staticmethod
    @tool
    @timing_wrapper("MACRO")
    def get_macro_analysis(
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
        lookback_days: Annotated[int, "Number of days to look back for data"] = 365,
    ) -> str:
        """
        Retrieve comprehensive macro economic analysis including Fed funds, CPI, PPI, NFP, GDP, PMI, Treasury curve, VIX.
        Provides economic indicators, yield curve analysis, and Fed policy updates with trading implications.

        Args:
            curr_date (str): Current date in yyyy-mm-dd format
            lookback_days (int): Number of days to look back for data (default 365 = 12 months)
            
        Returns:
            str: Comprehensive macro economic analysis with trading implications
        """
        
        macro_analysis_results = interface.get_macro_analysis(
            curr_date, lookback_days
        )
        
        return macro_analysis_results

    @staticmethod
    @tool
    def get_economic_indicators(
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
        lookback_days: Annotated[int, "Number of days to look back for data"] = 365,
    ) -> str:
        """
        Retrieve key economic indicators report including Fed funds, CPI, PPI, unemployment, NFP, GDP, PMI, VIX.

        Args:
            curr_date (str): Current date in yyyy-mm-dd format
            lookback_days (int): Number of days to look back for data (default 365 = 12 months)
            
        Returns:
            str: Economic indicators report with analysis and interpretations
        """
        
        economic_indicators_results = interface.get_economic_indicators(
            curr_date, lookback_days
        )
        
        return economic_indicators_results

    @staticmethod
    @tool
    def get_yield_curve_analysis(
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ) -> str:
        """
        Retrieve Treasury yield curve analysis including inversion signals and recession indicators.
        
        Args:
            curr_date (str): Current date in yyyy-mm-dd format
            
        Returns:
            str: Treasury yield curve data with inversion analysis
        """
        
        yield_curve_results = interface.get_yield_curve_analysis(curr_date)

        return yield_curve_results

    @staticmethod
    @tool
    @timing_wrapper("OPTIONS")
    def get_options_positioning(
        ticker: Annotated[str, "Stock ticker symbol (e.g., AAPL, TSLA)"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ) -> str:
        """
        Retrieve comprehensive options market positioning analysis for a stock.

        Includes:
        - Put/Call ratios (volume and open interest) for sentiment
        - Max pain calculation (price magnet at expiration)
        - Key OI levels (support/resistance from options positioning)
        - Implied volatility metrics and expected move
        - Unusual options activity detection

        Use this to understand institutional positioning and market expectations.
        Only available for stocks with listed options - not available for crypto.

        Args:
            ticker (str): Stock ticker symbol
            curr_date (str): Current date in yyyy-mm-dd format

        Returns:
            str: Comprehensive options market positioning analysis
        """

        options_results = interface.get_options_positioning(ticker, curr_date)

        return options_results

    @staticmethod
    @tool
    @timing_wrapper("FUNDAMENTALS")
    def get_defillama_fundamentals(
        ticker: Annotated[str, "Crypto ticker symbol (without USD/USDT suffix)"],
        lookback_days: Annotated[int, "Number of days to look back for data"] = 30,
    ):
        """
        Retrieve fundamental data for a cryptocurrency from DeFi Llama.
        This includes TVL (Total Value Locked), TVL change over lookback period,
        fees collected, and revenue data.
        
        Args:
            ticker (str): Crypto ticker symbol (e.g., BTC, ETH, UNI)
            lookback_days (int): Number of days to look back for data
            
        Returns:
            str: A markdown-formatted report of crypto fundamentals from DeFi Llama
        """
        
        defillama_results = interface.get_defillama_fundamentals(
            ticker, lookback_days
        )
        
        return defillama_results

    @staticmethod
    @tool
    def get_alpaca_data_report(
        symbol: Annotated[str, "ticker symbol of the company"],
        curr_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        look_back_days: Annotated[int, "how many days to look back"],
        timeframe: Annotated[str, "Timeframe for data: 1Hour, 4Hour, 1Day"] = "1Day",
    ) -> str:
        """
        Retrieve Alpaca data for a given ticker symbol.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            curr_date (str): The current trading date in YYYY-mm-dd format
            look_back_days (int): How many days to look back
            timeframe (str): Timeframe for data (1Hour, 4Hour, 1Day)
        Returns:
            str: A formatted dataframe containing the Alpaca data for the specified ticker symbol.
        """

        result_alpaca = interface.get_alpaca_data_window(
            symbol, curr_date, look_back_days, timeframe
        )

        return result_alpaca

    @staticmethod
    @tool
    @timing_wrapper("MARKET")
    def get_stock_data_table(
        symbol: Annotated[str, "ticker symbol of the company"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
        look_back_days: Annotated[int, "how many days to look back"] = 365,
        timeframe: Annotated[str, "Timeframe for data: 1Hour, 4Hour, 1Day"] = "1Day",
    ) -> str:
        """
        Retrieve comprehensive stock data table for a given ticker symbol over a lookback period.
        Returns a clean table with Date, Open, High, Low, Close, Volume, VWAP columns for EOD trading analysis.

        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, NVDA
            curr_date (str): The current trading date in YYYY-mm-dd format
            look_back_days (int): How many days to look back (default 365 = 12 months)
            timeframe (str): Timeframe for data (1Hour, 4Hour, 1Day)
            
        Returns:
            str: A comprehensive table containing Date, OHLCV, VWAP data for the lookback period
        """

        # Get the raw data from the interface
        raw_result = interface.get_alpaca_data_window(
            symbol, curr_date, look_back_days, timeframe
        )
        
        # Parse and reformat the timestamp column to be more readable
        import re
        
        try:
            # Use regex to replace complex timestamps with simple dates
            # Pattern: 2025-07-08 04:00:00+00:00 -> 2025-07-08
            timestamp_pattern = r'(\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}:\d{2}[+\-]\d{2}:\d{2}'
            
            # Replace the header line
            result = raw_result.replace('timestamp', 'Date')
            
            # Replace all timestamp values with just the date
            result = re.sub(timestamp_pattern, r'\1', result)
            
            # Also clean up any remaining timezone info
            result = re.sub(r'\s+\d{2}:\d{2}:\d{2}[+\-]\d{2}:\d{2}', '', result)
            
            # Update the title
            result = result.replace('Stock data for', 'Stock Data Table for')
            result = result.replace('from 2025-', f'({look_back_days}-day lookback)\nFrom 2025-')
            
            return result
                
        except Exception as e:
            # Fallback to original if any processing fails
            return raw_result

    @staticmethod
    @tool
    @timing_wrapper("MARKET")
    def get_indicators_table(
        symbol: Annotated[str, "ticker symbol (stocks: AAPL, NVDA; crypto: ETH/USD, BTC/USD)"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
        look_back_days: Annotated[int, "how many days to look back"] = 365,
    ) -> str:
        """
        Retrieve comprehensive technical indicators table for stocks and crypto over a lookback period.
        Returns a full table with Date and all key technical indicators calculated over the specified time window.
        Includes: EMAs, SMAs, RSI, MACD, Bollinger Bands, Stochastic, Williams %R, OBV, MFI, ATR.

        For crypto symbols, use format with slash: ETH/USD, BTC/USD, SOL/USD
        For stock symbols, use standard format: AAPL, NVDA, TSLA

        Args:
            symbol (str): Ticker symbol - stocks: AAPL, NVDA; crypto: ETH/USD, BTC/USD
            curr_date (str): The current trading date in YYYY-mm-dd format
            look_back_days (int): How many days to look back (default 365 = 12 months)
            
        Returns:
            str: A comprehensive table containing Date and all technical indicators for the lookback period
        """
        
        # Define the key indicators optimized for EOD trading
        key_indicators = [
            'close_8_ema',      # 8-day EMA (faster trend detection for EOD)
            'close_21_ema',     # 21-day EMA (key swing level)
            'close_50_sma',     # 50-day SMA (major trend)
            'rsi_14',           # 14-day RSI (optimal for daily signals)
            'macd',             # MACD Line (12,26,9 default)
            'macds',            # MACD Signal Line
            'macdh',            # MACD Histogram
            'boll_ub',          # Bollinger Upper (20,2 default)
            'boll_lb',          # Bollinger Lower (20,2 default)
            'kdjk_9',           # Stochastic %K (9-period for EOD)
            'kdjd_9',           # Stochastic %D (9-period for EOD)
            'wr_14',            # Williams %R (14-period)
            'atr_14',           # ATR (14-period for position sizing)
            'obv'               # On-Balance Volume (volume confirmation)
        ]
        
        # Get indicator data for each indicator across the time window
        import pandas as pd
        from datetime import datetime, timedelta
        
        # Calculate date range
        curr_dt = pd.to_datetime(curr_date)
        start_dt = curr_dt - pd.Timedelta(days=look_back_days)
        
        results = []
        results.append(f"# Technical Indicators Table for {symbol}")
        results.append(f"**Period:** {start_dt.strftime('%Y-%m-%d')} to {curr_date} ({look_back_days} days lookback)")
        results.append(f"**Showing:** Last 25 trading days for EOD analysis")
        results.append("")
        
        # Create table header
        header_row = "| Date | " + " | ".join([ind.replace('_', ' ').title() for ind in key_indicators]) + " |"
        separator_row = "|------|" + "|".join(["------" for _ in key_indicators]) + "|"
        
        results.append(header_row)
        results.append(separator_row)
        
        # Generate dates for the lookback period - only trading days
        dates = []
        trading_days_found = 0
        days_back = 0
        
        # Get the last 45 trading days (roughly 9 weeks of trading data)
        while trading_days_found < 45 and days_back <= look_back_days:
            date = curr_dt - pd.Timedelta(days=days_back)
            # Skip weekends (Saturday=5, Sunday=6)
            if date.weekday() < 5:  # Monday=0, Friday=4
                dates.append(date.strftime("%Y-%m-%d"))
                trading_days_found += 1
            days_back += 1
        
        # Reverse to get chronological order, then take the most recent portion
        dates = dates[::-1]
        recent_dates = dates[-25:] if len(dates) > 25 else dates  # Show last 25 trading days
        
        # OPTIMIZED: Use batch processing instead of 350+ individual calls
        print(f"[INDICATORS] Getting batch indicator data for {symbol} over {len(recent_dates)} dates...")
        
        # Get raw stock data first to calculate all indicators at once
        try:
            from tradingagents.dataflows.alpaca_utils import AlpacaUtils
            import pandas as pd
            
            # Get extended data for proper indicator calculation (need more history)
            start_date_extended = curr_dt - pd.Timedelta(days=200)  # More history for proper indicators
            
            # Get stock data
            stock_data = AlpacaUtils.get_stock_data(
                symbol=symbol,
                start_date=start_date_extended.strftime('%Y-%m-%d'),
                end_date=curr_date,
                timeframe="1Day"
            )
            
            if stock_data.empty:
                results.append("| ERROR | No stock data available for indicator calculations |")
                return "\n".join(results)
            
            # Clean data and ensure proper indexing
            stock_data = stock_data.dropna()
            stock_data = stock_data.reset_index(drop=True)
            
            # Ensure we have enough data for indicators
            if len(stock_data) < 50:
                results.append(f"| WARNING | Only {len(stock_data)} days of data available, indicators may be incomplete |")
            
            print(f"[INDICATORS] Processing {len(stock_data)} days of data for {symbol}")
            
            # Calculate all indicators using stockstats
            import stockstats
            stock_stats = stockstats.StockDataFrame.retype(stock_data.copy())
            
            # Calculate all indicators efficiently
            indicator_data = {}
            for indicator in key_indicators:
                try:
                    if indicator == 'close_8_ema':
                        indicator_data[indicator] = stock_stats['close_8_ema']
                    elif indicator == 'close_21_ema':
                        indicator_data[indicator] = stock_stats['close_21_ema']  
                    elif indicator == 'close_50_sma':
                        indicator_data[indicator] = stock_stats['close_50_sma']
                    elif indicator == 'rsi_14':
                        indicator_data[indicator] = stock_stats['rsi_14']
                    elif indicator == 'macd':
                        indicator_data[indicator] = stock_stats['macd']
                    elif indicator == 'macds':
                        indicator_data[indicator] = stock_stats['macds']
                    elif indicator == 'macdh':
                        indicator_data[indicator] = stock_stats['macdh']
                    elif indicator == 'boll_ub':
                        indicator_data[indicator] = stock_stats['boll_ub']
                    elif indicator == 'boll_lb':
                        indicator_data[indicator] = stock_stats['boll_lb']
                    elif indicator == 'kdjk_9':
                        indicator_data[indicator] = stock_stats['kdjk_9']
                    elif indicator == 'kdjd_9':
                        indicator_data[indicator] = stock_stats['kdjd_9']
                    elif indicator == 'wr_14':
                        indicator_data[indicator] = stock_stats['wr_14']
                    elif indicator == 'atr_14':
                        indicator_data[indicator] = stock_stats['atr_14']
                    elif indicator == 'obv':
                        # Manual OBV calculation (stockstats has parsing issues with 'obv')
                        obv_values = []
                        obv = 0
                        for i in range(len(stock_data)):
                            if i == 0:
                                obv_values.append(stock_data['volume'].iloc[i])
                            else:
                                if stock_data['close'].iloc[i] > stock_data['close'].iloc[i-1]:
                                    obv += stock_data['volume'].iloc[i]
                                elif stock_data['close'].iloc[i] < stock_data['close'].iloc[i-1]:
                                    obv -= stock_data['volume'].iloc[i]
                                obv_values.append(obv)
                        indicator_data[indicator] = pd.Series(obv_values, index=stock_data.index)
                    else:
                        indicator_data[indicator] = None
                except Exception as e:
                    print(f"[INDICATORS] Warning: Failed to calculate {indicator}: {e}")
                    indicator_data[indicator] = None
            
            # Convert date strings to datetime for matching
            recent_dates_dt = [pd.to_datetime(d) for d in recent_dates]
            
            # Build table rows efficiently
            for date_str in recent_dates:
                row_values = [date_str]
                date_dt = pd.to_datetime(date_str)
                
                for indicator in key_indicators:
                    try:
                        # Find matching date in indicator data
                        indicator_series = indicator_data.get(indicator)
                        if indicator_series is not None and len(indicator_series) > 0:
                            try:
                                # Convert recent_dates to match stock_data index
                                # Find the closest date index in our data
                                target_date = pd.to_datetime(date_str)
                                
                                # If stock_data has a date column, use it for matching
                                if 'date' in stock_data.columns:
                                    date_matches = stock_data[stock_data['date'] == target_date.strftime('%Y-%m-%d')]
                                    if not date_matches.empty:
                                        idx = date_matches.index[0]
                                        if idx < len(indicator_series):
                                            value = indicator_series.iloc[idx]
                                        else:
                                            value = indicator_series.iloc[-1]  # Use last available
                                    else:
                                        # Use the most recent available data
                                        value = indicator_series.iloc[-1] if len(indicator_series) > 0 else None
                                else:
                                    # Use index-based matching (most recent data)
                                    days_from_end = (pd.to_datetime(recent_dates[-1]) - target_date).days
                                    idx = max(0, len(indicator_series) - 1 - days_from_end)
                                    idx = min(idx, len(indicator_series) - 1)
                                    value = indicator_series.iloc[idx]
                                
                                if pd.isna(value) or value is None:
                                    row_values.append("N/A")
                                else:
                                    # Format value appropriately
                                    if indicator in ['rsi_14', 'kdjk_9', 'kdjd_9', 'wr_14']:
                                        row_values.append(f"{float(value):.1f}")
                                    elif 'macd' in indicator:
                                        row_values.append(f"{float(value):.3f}")
                                    else:
                                        row_values.append(f"{float(value):.2f}")
                            except Exception as match_error:
                                print(f"[INDICATORS] Date matching error for {indicator}: {match_error}")
                                row_values.append("N/A")
                        else:
                            row_values.append("N/A")
                    except Exception as e:
                        row_values.append("N/A")
                
                # Format the table row
                table_row = "| " + " | ".join(row_values) + " |"
                results.append(table_row)
                
        except Exception as e:
            print(f"[INDICATORS] ERROR: Batch indicator calculation failed: {e}")
            # Fallback to individual calls (original slow method) with timeout
            import time
            timeout_per_call = 2.0  # 2 second timeout per call
            
            for date in recent_dates:
                row_values = [date]
                
                for indicator in key_indicators:
                    start_time = time.time()
                    try:
                        # Get indicator value with timeout protection
                        value = interface.get_stock_stats_indicators_window(
                            symbol, indicator, date, 1, True
                        )
                        
                        # Check if call took too long
                        elapsed = time.time() - start_time
                        if elapsed > timeout_per_call:
                            print(f"[INDICATORS] Warning: {indicator} took {elapsed:.1f}s (slow)")
                        
                        # Extract numeric value
                        if ":" in value:
                            numeric_part = value.split(":")[-1].strip().split("(")[0].strip()
                            try:
                                float_val = float(numeric_part)
                                if indicator in ['rsi_14', 'kdjk_9', 'kdjd_9', 'wr_14']:
                                    row_values.append(f"{float_val:.1f}")
                                elif 'macd' in indicator:
                                    row_values.append(f"{float_val:.3f}")
                                else:
                                    row_values.append(f"{float_val:.2f}")
                            except:
                                row_values.append("N/A")
                        else:
                            row_values.append("N/A")
                    except Exception as ind_e:
                        print(f"[INDICATORS] Error getting {indicator} for {date}: {ind_e}")
                        row_values.append("N/A")
                
                # Format the table row
                table_row = "| " + " | ".join(row_values) + " |"
                results.append(table_row)
        
        results.append("")
        results.append("## Key EOD Trading Signals Analysis:")
        results.append("- **Trend Structure:** 8-EMA > 21-EMA > 50-SMA = Strong uptrend | Price above all EMAs = Bullish")
        results.append("- **Momentum:** RSI 30-50 = Accumulation zone | RSI 50-70 = Trending | RSI >70 = Overbought")
        results.append("- **MACD Signals:** MACD > Signal = Bullish momentum | Histogram growing = Acceleration")
        results.append("- **Bollinger Bands:** Price at Upper Band = Breakout potential | Price at Lower Band = Support test")
        results.append("- **Stochastic:** %K crossing above %D in oversold (<20) = Buy signal | In overbought (>80) = Sell signal")
        results.append("- **Williams %R:** Values -20 to -80 = Normal range | Below -80 = Oversold (buy) | Above -20 = Overbought (sell)")
        results.append("- **ATR:** Use for position sizing (1-2x ATR for stop loss) | Higher ATR = More volatile")
        results.append("")
        results.append("**EOD Strategy:** Look for trend + momentum + volume confirmation for overnight positions")

        return "\n".join(results)

    # =========================================================================
    # Options Trading Tools (for options trading mode)
    # =========================================================================

    @staticmethod
    @tool
    @timing_wrapper("OPTIONS_TRADING")
    def get_alpaca_option_contracts(
        ticker: Annotated[str, "Stock ticker symbol (e.g., AAPL, TSLA)"],
        contract_type: Annotated[str, "Contract type: 'call' or 'put'"],
        min_strike: Annotated[float, "Minimum strike price"],
        max_strike: Annotated[float, "Maximum strike price"],
        expiration_gte: Annotated[str, "Earliest expiration date (YYYY-MM-DD)"],
        expiration_lte: Annotated[str, "Latest expiration date (YYYY-MM-DD)"],
    ) -> str:
        """
        Fetch available option contracts from Alpaca API.

        Use this tool to find specific option contracts for trading.
        Returns contracts with strike, expiration, open interest, and pricing info.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL", "TSLA")
            contract_type: "call" or "put"
            min_strike: Minimum strike price to filter
            max_strike: Maximum strike price to filter
            expiration_gte: Earliest expiration date (YYYY-MM-DD)
            expiration_lte: Latest expiration date (YYYY-MM-DD)

        Returns:
            str: Formatted list of available option contracts
        """
        from tradingagents.dataflows.options_trading_utils import get_option_contracts

        contracts = get_option_contracts(
            underlying=ticker,
            contract_type=contract_type,
            strike_price_gte=min_strike,
            strike_price_lte=max_strike,
            expiration_date_gte=expiration_gte,
            expiration_date_lte=expiration_lte,
            min_open_interest=100,
            limit=50
        )

        if not contracts:
            return f"No option contracts found for {ticker} matching the specified criteria."

        # Format as markdown table
        result = f"# Option Contracts for {ticker}\n\n"
        result += f"**Filter:** {contract_type.upper()}S, Strike ${min_strike}-${max_strike}, Exp {expiration_gte} to {expiration_lte}\n\n"
        result += "| Symbol | Strike | Expiration | Type | OI | Last Price |\n"
        result += "|--------|--------|------------|------|-----|------------|\n"

        for c in contracts[:20]:  # Limit to 20 results
            price_str = f"${c['close_price']:.2f}" if c['close_price'] > 0 else "N/A"
            result += f"| {c['symbol']} | ${c['strike']:.2f} | {c['expiration']} | {c['contract_type'].upper()} | {c['open_interest']:,} | {price_str} |\n"

        result += f"\n**Total contracts found:** {len(contracts)}"

        return result

    @staticmethod
    @tool
    @timing_wrapper("OPTIONS_TRADING")
    def get_recommended_option_contracts(
        ticker: Annotated[str, "Stock ticker symbol (e.g., AAPL)"],
        direction: Annotated[str, "Trading direction: 'bullish' or 'bearish'"],
        risk_profile: Annotated[str, "Risk profile: 'conservative', 'moderate', or 'aggressive'"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ) -> str:
        """
        Get AI-recommended option contracts based on market analysis.

        This tool analyzes the underlying stock and recommends specific option
        contracts based on the trading direction and risk profile.

        Args:
            ticker: Stock ticker symbol
            direction: "bullish" for calls, "bearish" for puts
            risk_profile: "conservative" (ATM, longer DTE), "moderate" (OTM, medium DTE),
                         "aggressive" (deep OTM, short DTE)
            curr_date: Current date for DTE calculation

        Returns:
            str: Recommended contracts with rationale
        """
        from tradingagents.dataflows.options_trading_utils import get_recommended_contracts

        recommendations = get_recommended_contracts(
            ticker=ticker,
            direction=direction,
            risk_profile=risk_profile,
            curr_date=curr_date
        )

        return recommendations

    @staticmethod
    @tool
    @timing_wrapper("OPTIONS_TRADING")
    def get_current_options_positions() -> str:
        """
        Get current options positions from Alpaca account.

        Returns a summary of all open options positions including:
        - Contract details (symbol, strike, expiration)
        - Position size and P/L
        - Current market value

        Returns:
            str: Formatted summary of options positions
        """
        from tradingagents.dataflows.options_trading_utils import get_options_positions

        positions = get_options_positions()

        if not positions:
            return "No open options positions."

        result = "# Current Options Positions\n\n"
        result += "| Symbol | Type | Strike | Exp | Qty | Entry | Current | P/L ($) | P/L (%) |\n"
        result += "|--------|------|--------|-----|-----|-------|---------|---------|--------|\n"

        total_pl = 0
        for p in positions:
            result += f"| {p['symbol'][:16]} | {p['contract_type'].upper()} | ${p['strike']:.2f} | "
            result += f"{p['expiration']} | {p['qty']} | ${p['avg_entry_price']:.2f} | "
            result += f"${p['current_price']:.2f} | ${p['unrealized_pl']:.2f} | {p['unrealized_pl_pct']:.1f}% |\n"
            total_pl += p['unrealized_pl']

        result += f"\n**Total Options P/L:** ${total_pl:.2f}"

        return result

    # =========================================================================
    # Sector/Correlation Analysis Tools
    # =========================================================================

    @staticmethod
    @tool
    @timing_wrapper("SECTOR")
    def get_sector_peers(
        ticker: Annotated[str, "Stock ticker symbol (e.g., AAPL, NVDA)"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ) -> str:
        """
        Identify the sector, sector ETF, and peer stocks for a given ticker.

        Use this tool to understand where a stock fits in the market ecosystem.
        Returns the stock's sector classification, corresponding sector ETF for
        benchmarking, and a list of peer stocks in the same sector.

        Args:
            ticker: Stock ticker symbol
            curr_date: Current date (used for context)

        Returns:
            str: Sector information including sector name, ETF, and list of peers
        """
        from tradingagents.dataflows.sector_utils import identify_sector, get_sector_classification

        info = identify_sector(ticker)

        sector = info["sector"]
        industry = info.get("industry", "Unknown")
        sector_etf = info["sector_etf"]
        peers = info["peers"]
        all_sectors = info["all_sectors"]
        business_summary = info.get("business_summary", "")
        company_name = info.get("company_name", ticker)

        if sector == "Unknown":
            return f"""# Sector Analysis: {ticker} ({company_name})

**Sector:** Unknown (not in data provider)
**Benchmark:** SPY (S&P 500)
**Peers:** Unable to identify - sector data unavailable

**Business Summary:** {business_summary if business_summary else 'Not available'}

**Note:** For stocks without sector data, use SPY as the benchmark. Based on the business summary above,
you should determine what sector this company actually belongs to and identify appropriate peers manually.
"""

        # Get sector classification
        sector_class = get_sector_classification(sector_etf)

        result = f"""# Sector Analysis: {ticker} ({company_name})

## Sector Classification (from data provider)
| Attribute | Value |
|-----------|-------|
| **Primary Sector** | {sector} |
| **Industry** | {industry} |
| **Sector ETF** | {sector_etf} |
| **Sector Type** | {sector_class.title()} |

## Business Summary
{business_summary if business_summary else 'Not available'}

## Peer Stocks ({len(peers)} peers from curated list)
{', '.join(peers[:15]) if peers else 'No curated peers available for this sector'}

## IMPORTANT: Sector Validation Required
**You must validate if the sector classification above makes sense for this company.**

Based on the business summary:
1. Does "{sector}" accurately describe what this company does?
2. Are the listed peers actually comparable companies?
3. Is {sector_etf} an appropriate benchmark?

**Common misclassifications to watch for:**
- Bitcoin/crypto miners often classified as "Financial Services" - should use crypto peers (MARA, RIOT, CLSK)
- SPACs may have wrong legacy sector - look at actual business
- Holding companies may be misclassified - check what they actually own

**If the sector is WRONG:** State the correct sector, identify appropriate peers from your knowledge,
and use a more appropriate benchmark ETF in your analysis.

## Default Analysis Notes (if sector is correct)
- Use **{sector_etf}** as the primary benchmark for relative strength calculations
- Compare performance against peers to determine if {ticker} is a sector leader or laggard
- Sector type "{sector_class}" indicates {'risk-on behavior in bull markets' if sector_class == 'offensive' else 'safe-haven during market stress' if sector_class == 'defensive' else 'sensitivity to economic cycles'}
"""

        return result

    @staticmethod
    @tool
    @timing_wrapper("SECTOR")
    def get_peer_comparison(
        ticker: Annotated[str, "Stock ticker symbol (e.g., AAPL, NVDA)"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
        look_back_days: Annotated[int, "Number of days to look back for comparison"] = 365,
    ) -> str:
        """
        Compare a stock's performance against its sector peers.

        Calculates and ranks performance (1D, 5D, 10D, 30D returns) for the ticker
        and all its sector peers. Helps identify if the stock is leading or lagging
        its sector.

        Args:
            ticker: Stock ticker symbol
            curr_date: Current date in yyyy-mm-dd format
            look_back_days: Number of days to analyze (default 365 = 12 months)

        Returns:
            str: Performance comparison table with peer rankings
        """
        from tradingagents.dataflows.sector_utils import identify_sector
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils
        import pandas as pd
        from datetime import datetime, timedelta

        info = identify_sector(ticker)
        sector = info["sector"]
        peers = info["peers"]

        if sector == "unknown":
            return f"""# Peer Comparison: {ticker}

**Error:** Unable to identify sector peers for {ticker}.
Stock not found in sector mapping. Consider using relative strength vs SPY instead.
"""

        # Include the ticker itself in the comparison
        all_symbols = [ticker] + peers[:14]  # Limit to 15 total for performance

        # Calculate date range
        end_date = datetime.strptime(curr_date, "%Y-%m-%d")
        start_date = end_date - timedelta(days=look_back_days + 10)  # Buffer for weekends

        # Fetch data for all symbols
        performance_data = []

        for symbol in all_symbols:
            try:
                df = AlpacaUtils.get_stock_data(
                    symbol=symbol,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=curr_date,
                    timeframe="1Day"
                )

                if df.empty or len(df) < 5:
                    continue

                # Calculate returns
                close_col = 'close' if 'close' in df.columns else 'Close'
                closes = df[close_col].values

                current_price = closes[-1]

                # Calculate various period returns
                ret_1d = ((closes[-1] / closes[-2]) - 1) * 100 if len(closes) >= 2 else 0
                ret_5d = ((closes[-1] / closes[-6]) - 1) * 100 if len(closes) >= 6 else 0
                ret_10d = ((closes[-1] / closes[-11]) - 1) * 100 if len(closes) >= 11 else 0
                ret_30d = ((closes[-1] / closes[0]) - 1) * 100 if len(closes) >= 2 else 0

                performance_data.append({
                    "symbol": symbol,
                    "price": current_price,
                    "1d_return": ret_1d,
                    "5d_return": ret_5d,
                    "10d_return": ret_10d,
                    "30d_return": ret_30d,
                    "is_target": symbol == ticker,
                })

            except Exception as e:
                print(f"[SECTOR] Error fetching {symbol}: {e}")
                continue

        if not performance_data:
            return f"""# Peer Comparison: {ticker}

**Error:** Unable to fetch performance data for {ticker} or its peers.
"""

        # Sort by 30-day return and assign ranks
        performance_data.sort(key=lambda x: x["30d_return"], reverse=True)
        for i, item in enumerate(performance_data):
            item["rank"] = i + 1

        # Find target stock's data
        target_data = next((p for p in performance_data if p["is_target"]), None)

        # Build result
        result = f"""# Peer Comparison: {ticker}

## Sector: {sector.replace('_', ' ').title()}
**Analysis Date:** {curr_date}
**Peers Analyzed:** {len(performance_data)}

## Performance Rankings (by 30D Return)

| Rank | Symbol | Price | 1D | 5D | 10D | 30D |
|------|--------|-------|-----|-----|------|------|
"""

        for item in performance_data:
            marker = " **" if item["is_target"] else ""
            end_marker = "**" if item["is_target"] else ""
            result += f"| {item['rank']} | {marker}{item['symbol']}{end_marker} | ${item['price']:.2f} | {item['1d_return']:+.1f}% | {item['5d_return']:+.1f}% | {item['10d_return']:+.1f}% | {item['30d_return']:+.1f}% |\n"

        # Add summary for target stock
        if target_data:
            total_peers = len(performance_data)
            rank = target_data["rank"]
            percentile = ((total_peers - rank + 1) / total_peers) * 100

            if rank <= total_peers * 0.25:
                position = "SECTOR LEADER"
                signal = "Bullish"
            elif rank <= total_peers * 0.5:
                position = "ABOVE AVERAGE"
                signal = "Mildly Bullish"
            elif rank <= total_peers * 0.75:
                position = "BELOW AVERAGE"
                signal = "Mildly Bearish"
            else:
                position = "SECTOR LAGGARD"
                signal = "Bearish"

            result += f"""
## {ticker} Summary

| Metric | Value | Interpretation |
|--------|-------|----------------|
| **Sector Rank** | #{rank} of {total_peers} | {position} |
| **Percentile** | {percentile:.0f}th | {'Outperforming' if percentile >= 50 else 'Underperforming'} most peers |
| **30D Return** | {target_data['30d_return']:+.1f}% | {'Positive' if target_data['30d_return'] > 0 else 'Negative'} momentum |
| **EOD Signal** | {signal} | {'Consider long' if 'Bullish' in signal else 'Consider caution'} |
"""

        return result

    @staticmethod
    @tool
    @timing_wrapper("SECTOR")
    def get_relative_strength(
        ticker: Annotated[str, "Stock ticker symbol (e.g., AAPL, NVDA)"],
        benchmark: Annotated[str, "Benchmark symbol (sector ETF or SPY)"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
        look_back_days: Annotated[int, "Number of days to look back"] = 365,
    ) -> str:
        """
        Calculate relative strength of a stock vs a benchmark (sector ETF or SPY).

        Computes the RS ratio (stock cumulative return / benchmark cumulative return),
        identifies the RS trend (rising/falling), calculates correlation, and
        detects divergences that may signal trading opportunities.

        Args:
            ticker: Stock ticker symbol
            benchmark: Benchmark symbol (e.g., XLK, SPY)
            curr_date: Current date in yyyy-mm-dd format
            look_back_days: Number of days for analysis (default 365 = 12 months)

        Returns:
            str: Relative strength analysis with trend and divergence signals
        """
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta

        # Calculate date range
        end_date = datetime.strptime(curr_date, "%Y-%m-%d")
        start_date = end_date - timedelta(days=look_back_days + 10)

        try:
            # Fetch data for both ticker and benchmark
            ticker_df = AlpacaUtils.get_stock_data(
                symbol=ticker,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=curr_date,
                timeframe="1Day"
            )

            benchmark_df = AlpacaUtils.get_stock_data(
                symbol=benchmark,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=curr_date,
                timeframe="1Day"
            )

            if ticker_df.empty or benchmark_df.empty:
                return f"""# Relative Strength: {ticker} vs {benchmark}

**Error:** Unable to fetch data for {ticker} or {benchmark}.
"""

            # Get close prices
            close_col = 'close' if 'close' in ticker_df.columns else 'Close'

            ticker_closes = ticker_df[close_col].values
            benchmark_closes = benchmark_df[close_col].values

            # Align lengths
            min_len = min(len(ticker_closes), len(benchmark_closes))
            ticker_closes = ticker_closes[-min_len:]
            benchmark_closes = benchmark_closes[-min_len:]

            if min_len < 5:
                return f"""# Relative Strength: {ticker} vs {benchmark}

**Error:** Insufficient data points for analysis (need at least 5 days).
"""

            # Calculate cumulative returns
            ticker_cum_ret = (ticker_closes / ticker_closes[0] - 1) * 100
            benchmark_cum_ret = (benchmark_closes / benchmark_closes[0] - 1) * 100

            # Calculate RS ratio series
            # RS = (1 + ticker_return) / (1 + benchmark_return)
            rs_ratio = (ticker_closes / ticker_closes[0]) / (benchmark_closes / benchmark_closes[0])

            # Current values
            current_ticker_ret = ticker_cum_ret[-1]
            current_benchmark_ret = benchmark_cum_ret[-1]
            current_rs = rs_ratio[-1]

            # RS trend (compare current RS to RS from 10 days ago)
            rs_10d_ago = rs_ratio[-11] if len(rs_ratio) >= 11 else rs_ratio[0]
            rs_change = ((current_rs / rs_10d_ago) - 1) * 100
            rs_trend = "Rising" if rs_change > 1 else "Falling" if rs_change < -1 else "Flat"

            # Calculate correlation
            correlation = np.corrcoef(ticker_closes, benchmark_closes)[0, 1]

            # Detect divergences
            # Bullish divergence: Price down, RS up
            # Bearish divergence: Price up, RS down
            price_direction = "up" if ticker_closes[-1] > ticker_closes[-11] else "down"
            rs_direction = "up" if current_rs > rs_10d_ago else "down"

            divergence = "None"
            divergence_signal = "Neutral"
            if price_direction == "down" and rs_direction == "up":
                divergence = "Bullish Divergence"
                divergence_signal = "Potential reversal - consider long"
            elif price_direction == "up" and rs_direction == "down":
                divergence = "Bearish Divergence"
                divergence_signal = "Potential reversal - consider caution"

            # Determine overall signal
            if current_rs > 1.0 and rs_trend == "Rising":
                overall_signal = "Strong Outperformance"
                overnight_bias = "Bullish"
            elif current_rs > 1.0 and rs_trend == "Falling":
                overall_signal = "Weakening Leader"
                overnight_bias = "Neutral"
            elif current_rs < 1.0 and rs_trend == "Rising":
                overall_signal = "Improving Laggard"
                overnight_bias = "Mildly Bullish"
            else:
                overall_signal = "Underperforming"
                overnight_bias = "Bearish"

            # Build result
            result = f"""# Relative Strength Analysis: {ticker} vs {benchmark}

## Performance Comparison
| Metric | {ticker} | {benchmark} | Difference |
|--------|----------|-------------|------------|
| **{look_back_days}D Return** | {current_ticker_ret:+.2f}% | {current_benchmark_ret:+.2f}% | {current_ticker_ret - current_benchmark_ret:+.2f}% |
| **Current Price** | ${ticker_closes[-1]:.2f} | ${benchmark_closes[-1]:.2f} | - |

## Relative Strength Metrics
| Metric | Value | Interpretation |
|--------|-------|----------------|
| **RS Ratio** | {current_rs:.3f} | {'Outperforming' if current_rs > 1 else 'Underperforming'} benchmark |
| **RS Trend (10D)** | {rs_trend} ({rs_change:+.1f}%) | {'Strengthening' if rs_trend == 'Rising' else 'Weakening' if rs_trend == 'Falling' else 'Stable'} |
| **Correlation** | {correlation:.2f} | {'High' if abs(correlation) > 0.8 else 'Moderate' if abs(correlation) > 0.5 else 'Low'} correlation |
| **Divergence** | {divergence} | {divergence_signal} |

## Trading Signal
| Signal Type | Value | Overnight Bias |
|-------------|-------|----------------|
| **Overall Signal** | {overall_signal} | {overnight_bias} |
| **RS > 1.0** | {'Yes' if current_rs > 1 else 'No'} | {'Positive' if current_rs > 1 else 'Negative'} |
| **RS Trending Up** | {'Yes' if rs_trend == 'Rising' else 'No'} | {'Momentum' if rs_trend == 'Rising' else 'Caution'} |

## EOD Trading Implications
- **RS Ratio {current_rs:.3f}**: {ticker} is {'outperforming' if current_rs > 1 else 'underperforming'} {benchmark} by {abs(current_rs - 1) * 100:.1f}%
- **Trend**: RS is {rs_trend.lower()}, suggesting {'continued strength' if rs_trend == 'Rising' else 'potential weakness' if rs_trend == 'Falling' else 'consolidation'}
- **Correlation {correlation:.2f}**: {'Moves closely with' if correlation > 0.7 else 'Partially independent from'} the benchmark
{f'- **DIVERGENCE ALERT**: {divergence} detected - {divergence_signal}' if divergence != 'None' else ''}
"""

            return result

        except Exception as e:
            return f"""# Relative Strength: {ticker} vs {benchmark}

**Error:** Failed to calculate relative strength: {str(e)}
"""

    @staticmethod
    @tool
    @timing_wrapper("SECTOR")
    def get_sector_rotation(
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
        look_back_days: Annotated[int, "Number of days to look back"] = 365,
    ) -> str:
        """
        Analyze sector rotation by ranking all 11 sector ETFs by momentum.

        Calculates performance rankings for all major sector ETFs and identifies
        whether money is flowing into offensive (risk-on) or defensive (risk-off)
        sectors. Helps determine market regime and optimal sector positioning.

        Args:
            curr_date: Current date in yyyy-mm-dd format
            look_back_days: Number of days for momentum calculation (default 365 = 12 months)

        Returns:
            str: Sector rotation analysis with rankings and flow signals
        """
        from tradingagents.dataflows.sector_utils import get_all_sector_etfs, get_sector_classification
        from tradingagents.dataflows.alpaca_utils import AlpacaUtils
        from datetime import datetime, timedelta

        sector_etfs = get_all_sector_etfs()

        # Calculate date range
        end_date = datetime.strptime(curr_date, "%Y-%m-%d")
        start_date = end_date - timedelta(days=look_back_days + 10)

        sector_data = []

        for etf in sector_etfs:
            try:
                df = AlpacaUtils.get_stock_data(
                    symbol=etf,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=curr_date,
                    timeframe="1Day"
                )

                if df.empty or len(df) < 5:
                    continue

                close_col = 'close' if 'close' in df.columns else 'Close'
                closes = df[close_col].values

                # Calculate returns
                ret_5d = ((closes[-1] / closes[-6]) - 1) * 100 if len(closes) >= 6 else 0
                ret_10d = ((closes[-1] / closes[-11]) - 1) * 100 if len(closes) >= 11 else 0
                ret_30d = ((closes[-1] / closes[0]) - 1) * 100 if len(closes) >= 2 else 0

                classification = get_sector_classification(etf)

                sector_data.append({
                    "etf": etf,
                    "classification": classification,
                    "5d_return": ret_5d,
                    "10d_return": ret_10d,
                    "30d_return": ret_30d,
                    "price": closes[-1],
                })

            except Exception as e:
                print(f"[SECTOR] Error fetching {etf}: {e}")
                continue

        if not sector_data:
            return f"""# Sector Rotation Analysis

**Error:** Unable to fetch sector ETF data.
"""

        # Sort by 30-day return
        sector_data.sort(key=lambda x: x["30d_return"], reverse=True)

        # Assign ranks
        for i, item in enumerate(sector_data):
            item["rank"] = i + 1

        # Calculate offensive vs defensive performance
        offensive_returns = [s["30d_return"] for s in sector_data if s["classification"] == "offensive"]
        defensive_returns = [s["30d_return"] for s in sector_data if s["classification"] == "defensive"]

        avg_offensive = sum(offensive_returns) / len(offensive_returns) if offensive_returns else 0
        avg_defensive = sum(defensive_returns) / len(defensive_returns) if defensive_returns else 0

        # Determine market regime
        if avg_offensive > avg_defensive + 2:
            market_regime = "RISK-ON"
            regime_signal = "Offensive sectors outperforming - favor growth/cyclicals"
        elif avg_defensive > avg_offensive + 2:
            market_regime = "RISK-OFF"
            regime_signal = "Defensive sectors outperforming - favor safety/yield"
        else:
            market_regime = "NEUTRAL"
            regime_signal = "Mixed sector performance - no clear direction"

        # Build result
        result = f"""# Sector Rotation Analysis

**Analysis Date:** {curr_date}
**Lookback Period:** {look_back_days} days

## Sector Performance Rankings

| Rank | Sector ETF | Type | 5D | 10D | 30D |
|------|------------|------|-----|------|------|
"""

        for item in sector_data:
            type_emoji = "⚡" if item["classification"] == "offensive" else "🛡️" if item["classification"] == "defensive" else "🔄"
            result += f"| {item['rank']} | {item['etf']} | {type_emoji} {item['classification'].title()} | {item['5d_return']:+.1f}% | {item['10d_return']:+.1f}% | {item['30d_return']:+.1f}% |\n"

        result += f"""
## Market Regime Analysis

| Metric | Value | Signal |
|--------|-------|--------|
| **Market Regime** | {market_regime} | {regime_signal} |
| **Avg Offensive Return** | {avg_offensive:+.1f}% | {'Positive' if avg_offensive > 0 else 'Negative'} momentum |
| **Avg Defensive Return** | {avg_defensive:+.1f}% | {'Positive' if avg_defensive > 0 else 'Negative'} momentum |
| **Risk Appetite Spread** | {avg_offensive - avg_defensive:+.1f}% | {'Risk-on' if avg_offensive > avg_defensive else 'Risk-off'} bias |

## Top & Bottom Sectors

**Leading Sectors (Money Inflow):**
"""
        for item in sector_data[:3]:
            result += f"- **{item['etf']}** ({item['classification'].title()}): {item['30d_return']:+.1f}%\n"

        result += """
**Lagging Sectors (Money Outflow):**
"""
        for item in sector_data[-3:]:
            result += f"- **{item['etf']}** ({item['classification'].title()}): {item['30d_return']:+.1f}%\n"

        result += f"""
## EOD Trading Implications
- **Regime**: {market_regime} environment suggests {'aggressive positioning in growth stocks' if market_regime == 'RISK-ON' else 'defensive positioning in stable names' if market_regime == 'RISK-OFF' else 'balanced approach'}
- **Sector Flow**: Money flowing {'into' if sector_data[0]['30d_return'] > 0 else 'out of'} {sector_data[0]['etf']} ({sector_data[0]['30d_return']:+.1f}%)
- **Avoid**: {sector_data[-1]['etf']} showing weakness ({sector_data[-1]['30d_return']:+.1f}%)
"""

        return result
