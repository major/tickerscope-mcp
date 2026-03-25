"""TickerScope MCP tools for watchlists and screens."""

from __future__ import annotations

from typing import Annotated

from fastmcp import Context

from tickerscope_mcp import mcp


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
