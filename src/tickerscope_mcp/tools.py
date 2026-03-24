"""TickerScope MCP tools for financial data queries."""

from __future__ import annotations

import asyncio
import sys
import threading
import time
from typing import Annotated, Any, Callable, cast

from fastmcp import Context


def _register_on_package_mcp(func: Callable[..., Any]) -> None:
    """Register tool on package mcp after circular import completes."""

    def _register() -> None:
        for _ in range(100):
            package_module = sys.modules.get("tickerscope_mcp")
            if package_module is None:
                time.sleep(0.01)
                continue
            package_mcp = getattr(package_module, "mcp", None)
            if package_mcp is None:
                time.sleep(0.01)
                continue
            package_mcp.tool(func)
            return

    threading.Thread(target=_register, daemon=True).start()


class _MCPProxy:
    """Proxy decorator to defer registration until mcp exists."""

    def tool(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Register function as mcp tool once package initialization completes."""
        _register_on_package_mcp(func)
        return func


mcp = _MCPProxy()


@mcp.tool
async def analyze_stock(
    symbol: Annotated[str, "Stock ticker symbol, for example AAPL or NVDA"],
    ctx: Context,
) -> dict:
    """Fetch stock, fundamentals, and ownership data concurrently."""
    ctx_any = cast(Any, ctx)
    lifespan_context = cast(dict[str, Any], ctx_any.lifespan_context)
    client = lifespan_context["client"]

    stock_task = client.get_stock(symbol)
    fundamentals_task = client.get_fundamentals(symbol)
    ownership_task = client.get_ownership(symbol)

    stock_result, fundamentals_result, ownership_result = await asyncio.gather(
        stock_task,
        fundamentals_task,
        ownership_task,
        return_exceptions=True,
    )

    if isinstance(stock_result, Exception):
        from tickerscope_mcp import handle_tickerscope_error

        handle_tickerscope_error(stock_result)
    assert not isinstance(stock_result, Exception)

    stock_data = stock_result.to_dict()

    fundamentals = (
        fundamentals_result.to_dict()
        if not isinstance(fundamentals_result, Exception)
        else {"error": str(fundamentals_result)}
    )
    ownership = (
        ownership_result.to_dict()
        if not isinstance(ownership_result, Exception)
        else {"error": str(ownership_result)}
    )

    return {
        "symbol": symbol,
        "stock": stock_data,
        "fundamentals": fundamentals,
        "ownership": ownership,
    }
