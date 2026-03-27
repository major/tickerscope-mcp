"""TickerScope MCP tools for the unified stock list catalog."""

from __future__ import annotations

from typing import Annotated, Any, Callable, cast

from fastmcp import Context
from fastmcp.tools import tool as _tool
from mcp.types import ToolAnnotations
from tickerscope import CatalogEntry, CatalogKind

from tickerscope_mcp.errors import handle_tool_errors

tool = cast(Callable[..., Any], _tool)

_LIST_ANNOTATIONS = ToolAnnotations(readOnlyHint=True, idempotentHint=True)


@handle_tool_errors
@tool(annotations=_LIST_ANNOTATIONS, tags={"lists"}, timeout=60.0)
async def get_catalog(
    ctx: Context,
    kind: Annotated[
        CatalogKind | None,
        "Filter entries by kind: 'watchlist', 'screen', 'report', or 'coach_screen'. "
        "Omit to return all entries.",
    ] = None,
) -> dict:
    """List all available stock lists from all sources.

    Aggregates user screens, predefined reports, coach screens, and
    watchlists into a single catalog. Tolerates partial failures: if one
    source errors, entries from other sources are still returned with the
    error message collected.

    Use run_catalog_entry to fetch the stocks in a specific entry.
    """
    client = ctx.lifespan_context["client"]  # pyright: ignore[reportAttributeAccessIssue]
    catalog = await client.get_catalog()
    result = catalog.to_dict()
    if kind is not None:
        result["entries"] = [e for e in result["entries"] if e["kind"] == kind]
    return result


@handle_tool_errors
@tool(annotations=_LIST_ANNOTATIONS, tags={"lists"}, timeout=60.0)
async def run_catalog_entry(
    kind: Annotated[
        CatalogKind,
        "Entry kind: 'watchlist', 'report', or 'coach_screen'. "
        "Screen entries cannot be dispatched.",
    ],
    ctx: Context,
    name: Annotated[str | None, "Entry name (for display purposes)."] = None,
    report_id: Annotated[
        int | None,
        "Report ID (required when kind='report').",
    ] = None,
    coach_screen_id: Annotated[
        str | None,
        "Coach screen ID (required when kind='coach_screen').",
    ] = None,
    watchlist_id: Annotated[
        int | None,
        "Watchlist ID (required when kind='watchlist').",
    ] = None,
) -> dict:
    """Run a catalog entry and return its results.

    Dispatches to the appropriate run method based on the entry's kind.
    Pass the identifying fields from a get_catalog entry directly.

    Screen entries cannot be dispatched (raises an error).
    """
    client = ctx.lifespan_context["client"]  # pyright: ignore[reportAttributeAccessIssue]
    entry = CatalogEntry(
        name=name or "",
        kind=kind,
        report_id=report_id,
        coach_screen_id=coach_screen_id,
        watchlist_id=watchlist_id,
    )
    result = await client.run_catalog_entry(entry)
    return result.to_dict()
