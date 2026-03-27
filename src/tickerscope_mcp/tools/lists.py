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


def _build_filters(
    min_composite: int | None,
    min_rs: int | None,
    exclude_spacs: bool,
) -> dict[str, Any] | None:
    """Build a filters dict from individual filter parameters.

    Returns ``None`` when no filters are active so the library skips
    filtering entirely.
    """
    filters: dict[str, Any] = {}
    if min_composite is not None:
        filters["min_composite"] = min_composite
    if min_rs is not None:
        filters["min_rs"] = min_rs
    if exclude_spacs:
        filters["exclude_spacs"] = exclude_spacs
    return filters or None


def _parse_fields(fields: str | None) -> set[str] | None:
    """Parse a comma-separated fields string into a set.

    Returns ``None`` when *fields* is ``None`` or contains only
    whitespace, so the library returns all fields.
    """
    if fields is None:
        return None
    return {f.strip() for f in fields.split(",") if f.strip()} or None


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
    limit: Annotated[
        int | None,
        "Maximum number of results to return. Defaults to all.",
    ] = None,
    offset: Annotated[
        int | None,
        "Starting index for pagination (0-based). Use with limit.",
    ] = None,
    fields: Annotated[
        str | None,
        "Comma-separated list of fields to include per entry "
        "(e.g., 'symbol,composite_rating,rs_rating,price,industry_name'). "
        "Omit for all fields.",
    ] = None,
    min_composite: Annotated[
        int | None,
        "Minimum Composite Rating filter (0-99).",
    ] = None,
    min_rs: Annotated[
        int | None,
        "Minimum RS Rating filter (0-99).",
    ] = None,
    exclude_spacs: Annotated[
        bool,
        "Exclude SPAC/blank-check entries.",
    ] = False,
) -> dict:
    """Run a catalog entry and return its results.

    Dispatches to the appropriate run method based on the entry's kind.
    Pass the identifying fields from a get_catalog entry directly.

    Screen entries cannot be dispatched (raises an error).

    Reports and coach screens can return hundreds of stocks. Use ``limit``
    and ``offset`` for manageable pages, ``fields`` to select only the
    columns you need, and the filter parameters to narrow results
    server-side before they reach you.
    """
    client = ctx.lifespan_context["client"]  # pyright: ignore[reportAttributeAccessIssue]
    entry = CatalogEntry(
        name=name or "",
        kind=kind,
        report_id=report_id,
        coach_screen_id=coach_screen_id,
        watchlist_id=watchlist_id,
    )

    result = await client.run_catalog_entry(
        entry,
        limit=limit,
        offset=offset,
        filters=_build_filters(min_composite, min_rs, exclude_spacs),
    )

    output = result.to_dict(fields=_parse_fields(fields))
    output["total"] = result.total
    output["limit"] = limit
    output["offset"] = offset or 0
    return output
