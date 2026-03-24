"""TickerScope MCP tools for financial data queries."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Annotated

from fastmcp import Context
from fastmcp.exceptions import ToolError

from tickerscope_mcp import mcp

PERIOD_DAYS = {"1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365}


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


@mcp.tool
async def get_price_history(
    symbol: Annotated[str, "Stock ticker symbol, e.g. AAPL, NVDA, TSLA"],
    ctx: Context,
    start_date: Annotated[
        str | None,
        "Start date in ISO format (YYYY-MM-DD). Use with end_date.",
    ] = None,
    end_date: Annotated[
        str | None,
        "End date in ISO format (YYYY-MM-DD). Use with start_date.",
    ] = None,
    period: Annotated[
        str | None,
        "Relative period: 1W, 1M, 3M, 6M, or 1Y. Cannot be used with start_date/end_date.",
    ] = None,
    max_points: Annotated[int, "Maximum number of data points to return."] = 500,
) -> dict:
    """Fetch OHLCV price history for a stock from MarketSurge.

    Provide either (start_date + end_date) or period, not both.
    """
    if period and (start_date or end_date):
        raise ToolError("Provide either period OR start_date/end_date, not both.")
    if not period and not (start_date and end_date):
        raise ToolError(
            "Provide either period (e.g. '6M') or both start_date and end_date."
        )

    if period:
        if period not in PERIOD_DAYS:
            raise ToolError(
                f"Invalid period '{period}'. Use one of: {', '.join(PERIOD_DAYS)}"
            )
        today = date.today()
        end_date = today.isoformat()
        start_date = (today - timedelta(days=PERIOD_DAYS[period])).isoformat()

    client = ctx.lifespan_context["client"]  # type: ignore[attr-defined]
    try:
        chart_data = await client.get_chart_data(
            symbol,
            start_date=start_date,
            end_date=end_date,
            max_points=max_points,
        )
    except Exception as exc:
        from tickerscope_mcp import handle_tickerscope_error

        handle_tickerscope_error(exc)
        raise  # unreachable: handle_tickerscope_error always raises ToolError

    return {
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "max_points": max_points,
        **chart_data.to_dict(),
    }
