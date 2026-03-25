"""LLM Agent logic for the AI Copilot (M18).

Provides tool definitions, provider abstraction (Anthropic / Ollama),
and the agentic tool-use loop.
"""

import json
import os
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta

from utils.logger import logger

# ═════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ═════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are an AI assistant embedded in a Bloomberg-style terminal for Indian stock markets (NSE/BSE).

You help users analyze stocks, understand their portfolio, track market trends, and answer questions about Indian equities, derivatives, and macro-economic data.

## Conventions
- All monetary values are in Indian Rupees (₹). Use Crores (1 Cr = 10M) for large numbers.
- Use Indian number grouping: 12,34,567.
- Stock symbols are NSE tickers (e.g., RELIANCE, TCS, HDFCBANK, INFY).
- Available stock universe: Nifty 50, Nifty 100, Nifty 200.
- Key indices: NIFTY 50, NIFTY BANK, NIFTY IT, NIFTY NEXT 50, NIFTY MIDCAP 50, INDIA VIX, NIFTY FINANCIAL SERVICES, NIFTY AUTO, NIFTY PHARMA, NIFTY FMCG, NIFTY METAL, NIFTY REALTY, NIFTY ENERGY, NIFTY INFRA, NIFTY PSE, NIFTY MEDIA.

## Guidelines
- Be concise and data-driven. Use tables or bullet points for numeric data.
- When comparing stocks, present side-by-side metrics.
- Always use the available tools to fetch real-time data — never guess prices or metrics.
- If a tool returns an error, explain what happened and suggest alternatives.
- End financial analysis with: "This is for informational purposes only, not financial advice."
"""

# ═════════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS (Anthropic tool-use format)
# ═════════════════════════════════════════════════════════════════════

TOOL_DEFINITIONS = [
    {
        "name": "get_stock_quote",
        "description": "Get live NSE quote for a stock symbol. Returns last price, change, % change, open, high, low, previous close, volume, 52-week high/low.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "NSE stock symbol, e.g. RELIANCE, TCS, HDFCBANK",
                },
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_index_quote",
        "description": "Get live quote for an NSE index. Returns last value, change, % change, advances, declines. Valid indices: NIFTY 50, NIFTY BANK, NIFTY IT, INDIA VIX, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "index_name": {
                    "type": "string",
                    "description": "Index name, e.g. 'NIFTY 50', 'NIFTY BANK', 'INDIA VIX'",
                },
            },
            "required": ["index_name"],
        },
    },
    {
        "name": "get_market_overview",
        "description": "Get a comprehensive market summary: top 5 gainers/losers, market breadth (advances/declines), and all sectoral index performance sorted by % change.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_company_info",
        "description": "Get fundamental data for a company: sector, market cap, P/E, P/B, ROE, dividend yield, 52-week range, revenue, profit margins, debt/equity, and more.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "NSE stock symbol, e.g. RELIANCE, TCS",
                },
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_stock_history",
        "description": "Get historical OHLCV data for a stock. Returns up to 30 data points plus summary statistics (min, max, avg close, total return %).",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "NSE stock symbol",
                },
                "period_days": {
                    "type": "integer",
                    "description": "Number of days of history to fetch (default 30, max 365)",
                },
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_income_statement",
        "description": "Get income statement (revenue, expenses, profit) for a company. Returns last 4 annual and quarterly periods.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "NSE stock symbol",
                },
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_option_analysis",
        "description": "Get options analysis for an index or stock: Put-Call Ratio (PCR), max pain strike, top 5 strikes by OI for calls and puts, and underlying value.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Symbol for option chain. For indices use: NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY. For stocks use NSE symbol.",
                },
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_portfolio_holdings",
        "description": "Get the user's portfolio holdings with live prices and P&L. Returns each holding's symbol, quantity, average price, current price, and unrealized gain/loss.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_watchlist",
        "description": "Get the user's watchlist with live prices and daily change for each symbol.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_paper_trading_status",
        "description": "Get paper trading account status: current balance, order history, open positions, and realized P&L.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_economic_indicators",
        "description": "Get Indian economic indicators: RBI policy rates (repo, CRR, SLR, etc.) and upcoming economic events (RBI MPC meetings, FOMC meetings).",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "compare_stocks",
        "description": "Compare 2-5 stocks side by side on key metrics: price, market cap, P/E, P/B, ROE, dividend yield, debt/equity, revenue growth, 52-week range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of 2-5 NSE stock symbols to compare, e.g. ['TCS', 'INFY', 'WIPRO']",
                },
            },
            "required": ["symbols"],
        },
    },
]


# ═════════════════════════════════════════════════════════════════════
# TOOL EXECUTION
# ═════════════════════════════════════════════════════════════════════

# Key fields to extract from company info (avoid sending 100+ fields to LLM)
_COMPANY_KEY_FIELDS = [
    "longName", "sector", "industry", "website", "marketCap",
    "currentPrice", "previousClose", "dayHigh", "dayLow",
    "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
    "trailingPE", "forwardPE", "priceToBook", "priceToSalesTrailing12Months",
    "returnOnEquity", "returnOnAssets", "profitMargins", "operatingMargins",
    "revenueGrowth", "earningsGrowth", "debtToEquity",
    "dividendYield", "trailingAnnualDividendYield",
    "totalRevenue", "totalDebt", "totalCash",
    "enterpriseValue", "beta", "bookValue", "earningsPerShare",
]


def _execute_tool(name, args):
    """Execute a tool by name with given arguments. Returns JSON string."""
    try:
        if name == "get_stock_quote":
            return _tool_stock_quote(args["symbol"])
        elif name == "get_index_quote":
            return _tool_index_quote(args["index_name"])
        elif name == "get_market_overview":
            return _tool_market_overview()
        elif name == "get_company_info":
            return _tool_company_info(args["symbol"])
        elif name == "get_stock_history":
            period = args.get("period_days", 30)
            return _tool_stock_history(args["symbol"], min(period, 365))
        elif name == "get_income_statement":
            return _tool_income_statement(args["symbol"])
        elif name == "get_option_analysis":
            return _tool_option_analysis(args["symbol"])
        elif name == "get_portfolio_holdings":
            return _tool_portfolio_holdings()
        elif name == "get_watchlist":
            return _tool_watchlist()
        elif name == "get_paper_trading_status":
            return _tool_paper_trading()
        elif name == "get_economic_indicators":
            return _tool_economic_indicators()
        elif name == "compare_stocks":
            return _tool_compare_stocks(args["symbols"][:5])
        else:
            return json.dumps({"error": f"Unknown tool: {name}"})
    except Exception as e:
        logger.error(f"llm_agent | tool={name} | {type(e).__name__}: {e}")
        return json.dumps({"error": f"Failed to fetch data: {type(e).__name__}: {e}"})


def _tool_stock_quote(symbol):
    from data.nse_live import get_stock_quote
    quote = get_stock_quote(symbol.upper())
    if quote is None:
        return json.dumps({"error": f"No data found for {symbol}"})
    return json.dumps(quote)


def _tool_index_quote(index_name):
    from data.nse_live import get_index_quote
    quote = get_index_quote(index_name)
    if quote is None:
        return json.dumps({"error": f"No data found for index {index_name}"})
    return json.dumps(quote)


def _tool_market_overview():
    from data.nse_live import get_top_gainers_losers, get_market_breadth, get_sectoral_indices

    result = {}

    breadth = get_market_breadth()
    if breadth:
        result["market_breadth"] = breadth

    gainers_df, losers_df = get_top_gainers_losers("NIFTY 50", n=5)
    if gainers_df is not None and not gainers_df.empty:
        result["top_gainers"] = gainers_df.to_dict(orient="records")
    if losers_df is not None and not losers_df.empty:
        result["top_losers"] = losers_df.to_dict(orient="records")

    sectors_df = get_sectoral_indices()
    if sectors_df is not None and not sectors_df.empty:
        result["sectoral_indices"] = sectors_df.to_dict(orient="records")

    return json.dumps(result, default=str)


def _tool_company_info(symbol):
    from data.fundamentals import get_company_info
    info = get_company_info(symbol.upper())
    if info is None:
        return json.dumps({"error": f"No fundamental data for {symbol}"})
    filtered = {k: info.get(k) for k in _COMPANY_KEY_FIELDS if info.get(k) is not None}
    filtered["symbol"] = symbol.upper()
    return json.dumps(filtered, default=str)


def _tool_stock_history(symbol, period_days):
    from data.nse_historical import get_stock_history
    end = date.today()
    start = end - timedelta(days=period_days)
    df = get_stock_history(symbol.upper(), start.isoformat(), end.isoformat())
    if df is None or df.empty:
        return json.dumps({"error": f"No historical data for {symbol}"})

    # Summary stats
    summary = {
        "symbol": symbol.upper(),
        "period_days": period_days,
        "data_points": len(df),
        "close_min": round(float(df["Close"].min()), 2),
        "close_max": round(float(df["Close"].max()), 2),
        "close_avg": round(float(df["Close"].mean()), 2),
        "total_return_pct": round(
            (float(df["Close"].iloc[-1]) / float(df["Close"].iloc[0]) - 1) * 100, 2
        ),
        "latest_close": round(float(df["Close"].iloc[-1]), 2),
    }

    # Cap to last 30 rows
    sample = df.tail(30).copy()
    sample["Date"] = sample["Date"].astype(str) if "Date" in sample.columns else sample.index.astype(str)
    records = sample.round(2).to_dict(orient="records")

    return json.dumps({"summary": summary, "data": records}, default=str)


def _tool_income_statement(symbol):
    from data.fundamentals import get_income_statement
    data = get_income_statement(symbol.upper())
    if data is None:
        return json.dumps({"error": f"No income statement data for {symbol}"})

    result = {"symbol": symbol.upper()}
    for key in ("annual", "quarterly"):
        df = data.get(key)
        if df is not None and not df.empty:
            # Keep last 4 periods, transpose for readability
            df_trimmed = df.iloc[:, :4]
            result[key] = {
                "columns": [str(c) for c in df_trimmed.columns.tolist()],
                "data": {str(idx): [_safe_num(v) for v in row] for idx, row in df_trimmed.iterrows()},
            }
    return json.dumps(result, default=str)


def _tool_option_analysis(symbol):
    from data.nse_fno import get_option_chain, compute_pcr, compute_max_pain
    chain = get_option_chain(symbol.upper())
    if chain is None:
        return json.dumps({"error": f"No option chain data for {symbol}"})

    records = chain.get("records", [])
    result = {
        "symbol": symbol.upper(),
        "underlying_value": chain.get("underlying_value"),
        "selected_expiry": chain.get("selected_expiry"),
        "available_expiries": chain.get("expiry_dates", [])[:5],
    }

    if records:
        pcr = compute_pcr(records)
        if pcr:
            result["pcr"] = pcr
        max_pain = compute_max_pain(records)
        if max_pain:
            result["max_pain_strike"] = max_pain

        # Top 5 strikes by CE OI and PE OI
        sorted_ce = sorted(records, key=lambda r: r.get("CE_OI", 0), reverse=True)[:5]
        sorted_pe = sorted(records, key=lambda r: r.get("PE_OI", 0), reverse=True)[:5]
        result["top_call_oi_strikes"] = [
            {"strike": r["strikePrice"], "CE_OI": r.get("CE_OI", 0), "CE_LTP": r.get("CE_LTP", 0)}
            for r in sorted_ce
        ]
        result["top_put_oi_strikes"] = [
            {"strike": r["strikePrice"], "PE_OI": r.get("PE_OI", 0), "PE_LTP": r.get("PE_LTP", 0)}
            for r in sorted_pe
        ]

    return json.dumps(result, default=str)


def _tool_portfolio_holdings():
    from data.database import load_holdings
    from data.nse_live import get_stock_quote

    holdings = load_holdings()
    if not holdings:
        return json.dumps({"message": "Portfolio is empty. Add holdings in the M10 PORTFOLIO tab."})

    enriched = []
    total_invested = 0
    total_current = 0
    for h in holdings:
        symbol = h["symbol"]
        qty = h["qty"]
        avg = h["avg_price"]
        invested = qty * avg
        total_invested += invested

        quote = get_stock_quote(symbol)
        ltp = quote["lastPrice"] if quote else None
        current_val = qty * ltp if ltp else None
        if current_val:
            total_current += current_val

        enriched.append({
            "symbol": symbol,
            "qty": qty,
            "avg_price": avg,
            "buy_date": h.get("buy_date", ""),
            "current_price": ltp,
            "invested": round(invested, 2),
            "current_value": round(current_val, 2) if current_val else None,
            "pnl": round(current_val - invested, 2) if current_val else None,
            "pnl_pct": round((current_val / invested - 1) * 100, 2) if current_val and invested else None,
        })

    summary = {
        "total_invested": round(total_invested, 2),
        "total_current_value": round(total_current, 2),
        "total_pnl": round(total_current - total_invested, 2),
        "total_pnl_pct": round((total_current / total_invested - 1) * 100, 2) if total_invested else 0,
        "num_holdings": len(holdings),
    }

    return json.dumps({"summary": summary, "holdings": enriched}, default=str)


def _tool_watchlist():
    from data.database import load_watchlist
    from data.nse_live import get_stock_quote

    symbols = load_watchlist()
    if not symbols:
        return json.dumps({"message": "Watchlist is empty. Add symbols in the M02 WATCHLIST tab."})

    items = []
    for sym in symbols:
        quote = get_stock_quote(sym)
        if quote:
            items.append({
                "symbol": sym,
                "lastPrice": quote["lastPrice"],
                "change": quote["change"],
                "pChange": quote["pChange"],
                "dayHigh": quote["dayHigh"],
                "dayLow": quote["dayLow"],
                "volume": quote.get("totalTradedVolume"),
            })
        else:
            items.append({"symbol": sym, "error": "No data"})

    return json.dumps({"count": len(items), "watchlist": items}, default=str)


def _tool_paper_trading():
    from data.database import load_paper_balance, load_paper_orders

    balance = load_paper_balance()
    orders = load_paper_orders()

    # Derive positions from orders
    positions = {}
    for o in reversed(orders):  # oldest first
        sym = o["symbol"]
        if sym not in positions:
            positions[sym] = {"qty": 0, "invested": 0}
        if o["side"] == "BUY":
            positions[sym]["qty"] += o["qty"]
            positions[sym]["invested"] += o["total"]
        else:
            positions[sym]["qty"] -= o["qty"]
            positions[sym]["invested"] -= o.get("total", 0)

    open_positions = [
        {"symbol": s, "qty": p["qty"], "avg_cost": round(p["invested"] / p["qty"], 2) if p["qty"] > 0 else 0}
        for s, p in positions.items() if p["qty"] > 0
    ]

    return json.dumps({
        "balance": balance,
        "total_orders": len(orders),
        "open_positions": open_positions,
        "recent_orders": orders[:10],
    }, default=str)


def _tool_economic_indicators():
    from data.economic import get_rbi_rates, get_economic_calendar

    result = {}
    rates = get_rbi_rates()
    if rates:
        result["rbi_rates"] = rates

    calendar = get_economic_calendar()
    if calendar:
        result["upcoming_events"] = calendar[:10]

    return json.dumps(result, default=str)


def _tool_compare_stocks(symbols):
    from data.fundamentals import get_company_info

    rows = []
    for sym in symbols:
        info = get_company_info(sym.upper())
        if info is None:
            rows.append({"symbol": sym.upper(), "error": "No data"})
            continue
        rows.append({
            "symbol": sym.upper(),
            "name": info.get("longName"),
            "sector": info.get("sector"),
            "marketCap": info.get("marketCap"),
            "currentPrice": info.get("currentPrice"),
            "trailingPE": info.get("trailingPE"),
            "priceToBook": info.get("priceToBook"),
            "returnOnEquity": info.get("returnOnEquity"),
            "debtToEquity": info.get("debtToEquity"),
            "dividendYield": info.get("dividendYield"),
            "revenueGrowth": info.get("revenueGrowth"),
            "profitMargins": info.get("profitMargins"),
            "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
            "beta": info.get("beta"),
        })

    return json.dumps({"comparison": rows}, default=str)


def _safe_num(val):
    """Convert a value to a JSON-safe number, handling NaN/Inf."""
    import math
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 2)
    except (TypeError, ValueError):
        return str(val)


# ═════════════════════════════════════════════════════════════════════
# LLM PROVIDERS
# ═════════════════════════════════════════════════════════════════════

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def chat(self, messages, system_prompt, tools):
        """Send messages to the LLM and return the response."""
        ...


class AnthropicProvider(LLMProvider):
    """Claude API provider via the anthropic SDK."""

    def __init__(self, api_key, model="claude-sonnet-4-20250514"):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = 4096

    def chat(self, messages, system_prompt, tools):
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_prompt,
            messages=messages,
            tools=tools,
        )
        return response


class OllamaProvider(LLMProvider):
    """Local Ollama provider via REST API."""

    def __init__(self, model="llama3.1", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def chat(self, messages, system_prompt, tools):
        import requests

        # Convert Anthropic message format to Ollama (OpenAI-compatible)
        ollama_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            if msg["role"] == "user":
                # Handle both string content and list content
                if isinstance(msg["content"], str):
                    ollama_messages.append({"role": "user", "content": msg["content"]})
                else:
                    # Extract text from content blocks
                    text_parts = [
                        b["content"] if b["type"] == "tool_result" else b.get("text", "")
                        for b in msg["content"]
                        if b.get("type") in ("text", "tool_result")
                    ]
                    ollama_messages.append({"role": "user", "content": "\n".join(text_parts)})
            elif msg["role"] == "assistant":
                if isinstance(msg["content"], str):
                    ollama_messages.append({"role": "assistant", "content": msg["content"]})
                else:
                    text_parts = [b.get("text", "") for b in msg["content"] if b.get("type") == "text"]
                    ollama_messages.append({"role": "assistant", "content": "\n".join(text_parts)})

        # Convert Anthropic tool format to OpenAI-compatible format
        ollama_tools = []
        for t in tools:
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"],
                },
            })

        resp = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": ollama_messages,
                "tools": ollama_tools,
                "stream": False,
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        # Convert Ollama response to a duck-typed object matching Anthropic's format
        return _OllamaResponse(data)


class _OllamaResponse:
    """Adapts Ollama response to match Anthropic response interface."""

    def __init__(self, data):
        self._data = data
        msg = data.get("message", {})
        self.content = []

        # Check for tool calls
        tool_calls = msg.get("tool_calls", [])
        if tool_calls:
            self.stop_reason = "tool_use"
            for tc in tool_calls:
                fn = tc.get("function", {})
                self.content.append(_OllamaBlock(
                    type="tool_use",
                    id=f"ollama_{id(tc)}",
                    name=fn.get("name", ""),
                    input=fn.get("arguments", {}),
                ))
        else:
            self.stop_reason = "end_turn"
            text = msg.get("content", "")
            if text:
                self.content.append(_OllamaBlock(type="text", text=text))


class _OllamaBlock:
    """Mimics an Anthropic content block."""

    def __init__(self, type, text=None, id=None, name=None, input=None):
        self.type = type
        self.text = text
        self.id = id
        self.name = name
        self.input = input or {}


# ═════════════════════════════════════════════════════════════════════
# AGENT LOOP
# ═════════════════════════════════════════════════════════════════════

MAX_TOOL_ITERATIONS = 5


def run_agent_turn(provider, messages, tools_called_log=None):
    """Run one turn of the agent loop.

    Args:
        provider: An LLMProvider instance.
        messages: Conversation history in Anthropic message format.
        tools_called_log: Optional list to append tool call info to.

    Returns:
        str: The final text response from the assistant.
    """
    if tools_called_log is None:
        tools_called_log = []

    working_messages = list(messages)

    for iteration in range(MAX_TOOL_ITERATIONS):
        response = provider.chat(
            working_messages,
            system_prompt=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
        )

        # Check if the response contains tool use
        if response.stop_reason == "tool_use":
            # Build assistant message content from response
            assistant_content = []
            tool_uses = []

            for block in response.content:
                if block.type == "text" and block.text:
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
                    tool_uses.append(block)

            # Append assistant message with tool use
            working_messages.append({"role": "assistant", "content": assistant_content})

            # Execute tools and build tool results
            tool_results = []
            for tu in tool_uses:
                logger.info(f"llm_agent | executing tool={tu.name} | args={tu.input}")
                tools_called_log.append({"name": tu.name, "input": tu.input})
                result_str = _execute_tool(tu.name, tu.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": result_str,
                })

            # Append tool results as user message
            working_messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            # Extract text from response
            for block in response.content:
                if block.type == "text" and block.text:
                    return block.text
            return "I wasn't able to generate a response. Please try again."

        else:
            # Unexpected stop reason
            for block in response.content:
                if block.type == "text" and block.text:
                    return block.text
            return "Processing complete."

    return "I reached the maximum number of data lookups for this question. Here's what I found so far — please ask a more specific question if you need additional details."


def get_provider(backend="anthropic", **kwargs):
    """Factory function to create an LLM provider.

    Args:
        backend: "anthropic" or "ollama"
        **kwargs: Provider-specific arguments (api_key, model, base_url)

    Returns:
        LLMProvider instance
    """
    if backend == "anthropic":
        api_key = kwargs.get("api_key")
        if not api_key:
            raise ValueError("Anthropic API key is required")
        model = kwargs.get("model", "claude-sonnet-4-20250514")
        return AnthropicProvider(api_key=api_key, model=model)
    elif backend == "ollama":
        model = kwargs.get("model", "llama3.1")
        base_url = kwargs.get("base_url", "http://localhost:11434")
        return OllamaProvider(model=model, base_url=base_url)
    else:
        raise ValueError(f"Unknown backend: {backend}")
