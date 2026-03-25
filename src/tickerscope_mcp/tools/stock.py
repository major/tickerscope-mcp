"""TickerScope MCP tools for stock analysis."""

from __future__ import annotations

from typing import Annotated

from fastmcp import Context

from tickerscope_mcp import mcp


@mcp.tool
async def analyze_stock(
    symbol: Annotated[str, "Stock ticker symbol, e.g. AAPL, NVDA, TSLA"],
    ctx: Context,
) -> dict:
    """Analyze a stock with comprehensive data from MarketSurge.

    Fetches stock ratings, fundamentals, and ownership data concurrently.
    Partial failures in fundamentals or ownership are returned in the errors
    list rather than failing the entire request.

    Args:
        symbol: Stock ticker symbol, e.g. AAPL, NVDA, TSLA
    """
    client = ctx.lifespan_context["client"]
    try:
        analysis = await client.get_stock_analysis(symbol)
    except Exception as exc:
        from tickerscope_mcp import handle_tickerscope_error

        handle_tickerscope_error(exc)
        raise  # unreachable: handle_tickerscope_error always raises ToolError

    return analysis.to_dict()


@mcp.tool
async def get_stock(
    symbol: Annotated[str, "Stock ticker symbol, e.g. AAPL, NVDA, TSLA"],
    ctx: Context,
) -> dict:
    """Fetch stock data including ratings, pricing, financials, patterns, and company info from MarketSurge.

    Use this for targeted stock data without fundamentals or ownership.
    For comprehensive analysis, use analyze_stock instead.

    Args:
        symbol: Stock ticker symbol, e.g. AAPL, NVDA, TSLA
    """
    client = ctx.lifespan_context["client"]
    try:
        result = await client.get_stock(symbol)
    except Exception as exc:
        from tickerscope_mcp import handle_tickerscope_error

        handle_tickerscope_error(exc)
        raise  # unreachable: handle_tickerscope_error always raises ToolError

    return result.to_dict()


@mcp.tool
async def get_fundamentals(
    symbol: Annotated[str, "Stock ticker symbol, e.g. AAPL, NVDA, TSLA"],
    ctx: Context,
) -> dict:
    """Fetch reported and estimated earnings and sales data from MarketSurge.

    Returns historical EPS/sales with YoY changes and future estimates.
    For comprehensive analysis, use analyze_stock instead.

    Args:
        symbol: Stock ticker symbol, e.g. AAPL, NVDA, TSLA
    """
    client = ctx.lifespan_context["client"]
    try:
        result = await client.get_fundamentals(symbol)
    except Exception as exc:
        from tickerscope_mcp import handle_tickerscope_error

        handle_tickerscope_error(exc)
        raise  # unreachable: handle_tickerscope_error always raises ToolError

    return result.to_dict()


@mcp.tool
async def get_ownership(
    symbol: Annotated[str, "Stock ticker symbol, e.g. AAPL, NVDA, TSLA"],
    ctx: Context,
) -> dict:
    """Fetch institutional fund ownership data from MarketSurge.

    Returns quarterly fund ownership counts and funds as percentage of float.
    For comprehensive analysis, use analyze_stock instead.

    Args:
        symbol: Stock ticker symbol, e.g. AAPL, NVDA, TSLA
    """
    client = ctx.lifespan_context["client"]
    try:
        result = await client.get_ownership(symbol)
    except Exception as exc:
        from tickerscope_mcp import handle_tickerscope_error

        handle_tickerscope_error(exc)
        raise  # unreachable: handle_tickerscope_error always raises ToolError

    return result.to_dict()
