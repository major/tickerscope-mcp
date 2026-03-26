"""TickerScope MCP tools for stock analysis."""

from __future__ import annotations

from typing import Annotated, Any, Callable, cast

from fastmcp import Context
from fastmcp.tools import tool as _tool
from mcp.types import ToolAnnotations

from tickerscope_mcp.errors import handle_tool_errors

tool = cast(Callable[..., Any], _tool)

_STOCK_ANNOTATIONS = ToolAnnotations(readOnlyHint=True, idempotentHint=True)


@handle_tool_errors
@tool(annotations=_STOCK_ANNOTATIONS, tags={"stocks"}, timeout=60.0)
async def analyze_stock(
    symbol: Annotated[str, "Stock ticker symbol, e.g. AAPL, NVDA, TSLA"],
    ctx: Context,
) -> dict:
    """Analyze a stock with comprehensive data from MarketSurge.

    Fetches stock ratings, fundamentals, and ownership data concurrently.
    Partial failures in fundamentals or ownership are returned in the errors
    list rather than failing the entire request.

    Stock data now includes valuation ratios (P/E, P/S, P/CF), risk metrics (alpha, beta), short interest data, and blue dot event flags.

    Args:
        symbol: Stock ticker symbol, e.g. AAPL, NVDA, TSLA
    """
    client = ctx.lifespan_context["client"]  # pyright: ignore[reportAttributeAccessIssue]
    analysis = await client.get_stock_analysis(symbol)
    return analysis.to_dict()


@handle_tool_errors
@tool(annotations=_STOCK_ANNOTATIONS, tags={"stocks"}, timeout=60.0)
async def get_stock(
    symbol: Annotated[str, "Stock ticker symbol, e.g. AAPL, NVDA, TSLA"],
    ctx: Context,
) -> dict:
    """Fetch stock data including ratings, pricing, financials, patterns, and company info from MarketSurge.

    Use this for targeted stock data without fundamentals or ownership.
    For comprehensive analysis, use analyze_stock instead.

    Stock data now includes valuation ratios (P/E, P/S, P/CF), risk metrics (alpha, beta), short interest data, and blue dot event flags.

    Args:
        symbol: Stock ticker symbol, e.g. AAPL, NVDA, TSLA
    """
    client = ctx.lifespan_context["client"]  # pyright: ignore[reportAttributeAccessIssue]
    result = await client.get_stock(symbol)
    return result.to_dict()


@handle_tool_errors
@tool(annotations=_STOCK_ANNOTATIONS, tags={"stocks"}, timeout=60.0)
async def get_fundamentals(
    symbol: Annotated[str, "Stock ticker symbol, e.g. AAPL, NVDA, TSLA"],
    ctx: Context,
) -> dict:
    """Fetch reported and estimated earnings and sales data from MarketSurge.

    Returns historical EPS/sales with YoY changes and future estimates.
    For comprehensive analysis, use analyze_stock instead.

    Quarterly breakdowns (earnings, sales, margins) and cash flow per share are now included.

    Args:
        symbol: Stock ticker symbol, e.g. AAPL, NVDA, TSLA
    """
    client = ctx.lifespan_context["client"]  # pyright: ignore[reportAttributeAccessIssue]
    result = await client.get_fundamentals(symbol)
    return result.to_dict()


@handle_tool_errors
@tool(annotations=_STOCK_ANNOTATIONS, tags={"stocks"}, timeout=60.0)
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
    client = ctx.lifespan_context["client"]  # pyright: ignore[reportAttributeAccessIssue]
    result = await client.get_ownership(symbol)
    return result.to_dict()


@handle_tool_errors
@tool(annotations=_STOCK_ANNOTATIONS, tags={"stocks"}, timeout=60.0)
async def get_rs_rating_history(
    symbol: Annotated[str, "Stock ticker symbol, e.g. AAPL, NVDA, TSLA"],
    ctx: Context,
) -> dict:
    """Fetch reported relative strength rating history for a stock from MarketSurge.

    Returns a time series of RS rating snapshots showing relative price performance
    vs the market over various periods. Includes the rs_line_new_high flag indicating
    when the RS line hits a new high ahead of price.
    For comprehensive analysis, use analyze_stock instead.
    """
    client = ctx.lifespan_context["client"]  # pyright: ignore[reportAttributeAccessIssue]
    result = await client.get_rs_rating_history(symbol)
    return result.to_dict()
