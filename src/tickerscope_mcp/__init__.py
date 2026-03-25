"""TickerScope MCP server with FastMCP integration."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.providers import FileSystemProvider  # pyright: ignore[reportMissingImports]
from tickerscope import AsyncTickerScopeClient  # pyright: ignore[reportMissingImports]
from tickerscope_mcp.errors import handle_tickerscope_error  # noqa: F401


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


mcp = FastMCP(  # pyright: ignore[reportCallIssue]
    name="tickerscope",
    lifespan=lifespan,
    providers=[FileSystemProvider(Path(__file__).parent / "tools")],  # pyright: ignore[reportCallIssue]
    instructions=(
        "You are a financial data assistant powered by MarketSurge. "
        "You can fetch stock quotes, market data, and financial information. "
        "Always provide accurate ticker symbols and handle errors gracefully."
    ),
)


def main() -> None:
    """Run the TickerScope MCP server."""
    mcp.run(transport="stdio")
