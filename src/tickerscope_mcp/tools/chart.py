"""TickerScope MCP tools for price history and chart data."""

from __future__ import annotations

from typing import Annotated

from fastmcp import Context
from fastmcp.exceptions import ToolError

from tickerscope_mcp import mcp


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
    lookback: Annotated[
        str | None,
        "Relative lookback period: 1W, 1M, 3M, 6M, 1Y, or YTD. Cannot be used with start_date/end_date.",
    ] = None,
    max_points: Annotated[int, "Maximum number of data points to return."] = 500,
) -> dict:
    """Fetch OHLCV price history for a stock from MarketSurge.

    Provide either (start_date + end_date) or lookback, not both.
    """
    client = ctx.lifespan_context["client"]
    try:
        chart_data = await client.get_chart_data(
            symbol,
            start_date=start_date,
            end_date=end_date,
            lookback=lookback,
            max_points=max_points,
        )
    except ValueError as exc:
        raise ToolError(str(exc))
    except Exception as exc:
        from tickerscope_mcp import handle_tickerscope_error

        handle_tickerscope_error(exc)
        raise  # unreachable: handle_tickerscope_error always raises ToolError

    return {
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "lookback": lookback,
        "max_points": max_points,
        **chart_data.to_dict(),
    }
