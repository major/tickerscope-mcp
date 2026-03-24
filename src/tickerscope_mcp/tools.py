"""TickerScope MCP tools for financial data queries."""

from __future__ import annotations

from typing import Annotated

from fastmcp import Context
from fastmcp.exceptions import ToolError

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


@mcp.tool
async def list_watchlists(ctx: Context) -> list[dict]:
    """List all MarketSurge watchlists.

    Returns watchlist names and IDs. Use get_watchlist to fetch the contents
    of a specific watchlist.
    """
    client = ctx.lifespan_context["client"]
    watchlists = await client.get_watchlist_names()
    return [
        {"id": w.id, "name": w.name, "description": w.description} for w in watchlists
    ]


@mcp.tool
async def get_watchlist(
    name: Annotated[
        str,
        "Watchlist name, e.g. 'Growth Stocks'. Use list_watchlists to see available names.",
    ],
    ctx: Context,
) -> list[dict]:
    """Fetch enriched stock data for all symbols in a MarketSurge watchlist.

    Looks up the watchlist by name, then fetches enriched data including
    ratings, prices, and industry information for each symbol.

    Args:
        name: Watchlist name. Use list_watchlists to see available names.
    """
    client = ctx.lifespan_context["client"]
    try:
        entries = await client.screen_watchlist_by_name(name)
    except Exception as exc:
        from tickerscope_mcp import handle_tickerscope_error

        handle_tickerscope_error(exc)
        raise  # unreachable: handle_tickerscope_error always raises ToolError

    return [entry.to_dict() for entry in entries]


@mcp.tool
async def list_screens(ctx: Context) -> list[dict]:
    """List saved MarketSurge screens.

    These are user-created screens with filter criteria. Note: to run a
    predefined MarketSurge screen (like 'IBD 50'), use the run_screen tool instead.
    """
    client = ctx.lifespan_context["client"]
    screens = await client.get_screens()
    return [
        {"id": s.id, "name": s.name, "description": s.description, "type": s.type}
        for s in screens
    ]


@mcp.tool
async def run_screen(
    screen_name: Annotated[
        str,
        "Name of the predefined MarketSurge screen to run, e.g. 'IBD 50', 'Sector Leaders', 'IBD Big Cap 20'",
    ],
    ctx: Context,
    parameters: Annotated[
        list[dict[str, str]] | None,
        "Optional screen parameters as a list of {name, value} dicts",
    ] = None,
) -> dict:
    """Run a predefined MarketSurge screen and return matching stocks.

    Examples of predefined screens: 'IBD 50', 'Sector Leaders', 'IBD Big Cap 20'.
    Some screens accept parameters as a list of {name, value} dicts.

    Note: this runs predefined MarketSurge screens, not user-saved screens.
    Use list_screens to view user-saved screens.
    """
    client = ctx.lifespan_context["client"]
    try:
        result = await client.run_screen(screen_name, parameters or [])
    except Exception as exc:
        from tickerscope_mcp import handle_tickerscope_error

        handle_tickerscope_error(exc)
        raise  # unreachable: handle_tickerscope_error always raises ToolError
    return {
        "screen_name": result.screen_name,
        "num_instruments": result.num_instruments,
        "elapsed_time": result.elapsed_time,
        "rows": result.rows,
    }
