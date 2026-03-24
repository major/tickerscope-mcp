"""TickerScope MCP server with FastMCP integration."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from tickerscope import (
    APIError,
    AsyncTickerScopeClient,
    CookieExtractionError,
    HTTPError,
    SymbolNotFoundError,
    TokenExpiredError,
)


@asynccontextmanager
async def lifespan(app: FastMCP):
    """Manage AsyncTickerScopeClient lifecycle.

    Creates a client via AsyncTickerScopeClient.create() and ensures
    proper cleanup with aclose().
    """
    client = await AsyncTickerScopeClient.create()
    try:
        yield {"client": client}
    finally:
        await client.aclose()


mcp = FastMCP(
    name="tickerscope",
    lifespan=lifespan,
    instructions=(
        "You are a financial data assistant powered by MarketSurge. "
        "You can fetch stock quotes, market data, and financial information. "
        "Always provide accurate ticker symbols and handle errors gracefully."
    ),
)

from . import tools  # noqa: F401, E402


def handle_tickerscope_error(exc: Exception) -> None:
    """Map tickerscope exceptions to ToolError.

    Args:
        exc: Exception from tickerscope library.

    Raises:
        ToolError: Mapped error with actionable message.
    """
    if isinstance(exc, SymbolNotFoundError):
        symbol = getattr(exc, "symbol", "UNKNOWN")
        raise ToolError(f"Symbol '{symbol}' not found. Check the ticker spelling.")
    if isinstance(exc, TokenExpiredError):
        raise ToolError(
            "MarketSurge authentication expired. "
            "Restart the tickerscope-mcp server to re-authenticate."
        )
    if isinstance(exc, CookieExtractionError):
        raise ToolError(
            "No browser cookies found. "
            "Log into MarketSurge at marketsurge.investors.com in Firefox or Chrome first."
        )
    if isinstance(exc, HTTPError):
        raise ToolError(f"MarketSurge HTTP {exc.status_code} error: {exc.message}")
    if isinstance(exc, APIError):
        raise ToolError(f"MarketSurge API error: {exc}")
    raise ToolError(f"Unexpected error: {exc}")


def main() -> None:
    """Run the TickerScope MCP server."""
    mcp.run(transport="stdio")
