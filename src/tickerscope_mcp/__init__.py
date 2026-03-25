"""TickerScope MCP server with FastMCP integration."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

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


class _ToolManagerCompat:
    def __init__(self, app: FastMCP) -> None:
        self._app = app

    @property
    def tools(self) -> dict[str, Any]:
        tool_list = asyncio.run(self._app.list_tools())  # pyright: ignore[reportAttributeAccessIssue]
        return {tool.name: tool for tool in tool_list}


mcp._tool_manager = _ToolManagerCompat(mcp)  # type: ignore[attr-defined]


def main() -> None:
    """Run the TickerScope MCP server."""
    mcp.run(transport="stdio")
