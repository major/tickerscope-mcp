"""TickerScope MCP server with FastMCP integration."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastmcp import FastMCP
from tickerscope import AsyncTickerScopeClient


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
from tickerscope_mcp.errors import handle_tickerscope_error  # noqa: F401


def main() -> None:
    """Run the TickerScope MCP server."""
    mcp.run(transport="stdio")
