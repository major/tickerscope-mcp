"""TickerScope MCP tools for price history and chart data."""

from __future__ import annotations

from typing import Annotated, Any, Callable, cast

from fastmcp import Context
from fastmcp.tools import tool as _tool
from mcp.types import ToolAnnotations

from tickerscope_mcp.errors import handle_tool_errors

tool = cast(Callable[..., Any], _tool)

_CHART_ANNOTATIONS = ToolAnnotations(readOnlyHint=True, idempotentHint=True)


@handle_tool_errors
@tool(annotations=_CHART_ANNOTATIONS, tags={"charts"}, timeout=60.0)
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
    benchmark: Annotated[
        str | None,
        "Benchmark symbol for relative strength computation (e.g. '0S&P5' for S&P 500). "
        "When provided, the response includes a benchmark_time_series for computing RS line ratios.",
    ] = None,
) -> dict:
    """Fetch OHLCV price history for a stock from MarketSurge.

    Provide either (start_date + end_date) or lookback, not both.
    """
    client = ctx.lifespan_context["client"]  # pyright: ignore[reportAttributeAccessIssue]
    chart_data = await client.get_chart_data(
        symbol,
        start_date=start_date,
        end_date=end_date,
        lookback=lookback,
        benchmark=benchmark,
    )

    return {
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "lookback": lookback,
        **chart_data.to_dict(),
    }
