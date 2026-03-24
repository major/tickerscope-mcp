"""TickerScope MCP tools for financial data queries."""

from __future__ import annotations

import asyncio
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
    Partial failures in fundamentals or ownership are returned as error messages
    rather than failing the entire request.

    Args:
        symbol: Stock ticker symbol, e.g. AAPL, NVDA, TSLA
    """
    client = ctx.lifespan_context["client"]

    stock_result, fundamentals_result, ownership_result = await asyncio.gather(
        client.get_stock(symbol),
        client.get_fundamentals(symbol),
        client.get_ownership(symbol),
        return_exceptions=True,
    )

    if isinstance(stock_result, Exception):
        from tickerscope_mcp import handle_tickerscope_error

        handle_tickerscope_error(stock_result)

    return {
        "symbol": symbol,
        "stock": stock_result.to_dict(),
        "fundamentals": (
            fundamentals_result.to_dict()
            if not isinstance(fundamentals_result, Exception)
            else {"error": str(fundamentals_result)}
        ),
        "ownership": (
            ownership_result.to_dict()
            if not isinstance(ownership_result, Exception)
            else {"error": str(ownership_result)}
        ),
    }
