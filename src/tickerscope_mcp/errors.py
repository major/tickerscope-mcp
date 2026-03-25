"""TickerScope MCP error handling utilities."""

from __future__ import annotations

import functools
from collections.abc import Callable

from fastmcp.exceptions import ToolError
from tickerscope import (
    CookieExtractionError,
    HTTPError,
    TickerScopeError,
    TokenExpiredError,
)


def handle_tickerscope_error(exc: Exception) -> None:
    """Map tickerscope exceptions to ToolError.

    Args:
        exc: Exception from tickerscope library.

    Raises:
        ToolError: Mapped error with actionable message.
    """
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
    if isinstance(exc, TickerScopeError):
        raise ToolError(exc.user_message)
    raise ToolError(f"Unexpected error: {exc}")


def handle_tool_errors(fn: Callable) -> Callable:
    """Decorator that maps tool errors to ToolError for MCP clients.

    Catches ToolError (pass-through), ValueError (converts to ToolError),
    and all other exceptions (maps via handle_tickerscope_error).

    Args:
        fn: Async tool function to wrap.
    """

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        """Wrap async tool function with error handling."""
        try:
            return await fn(*args, **kwargs)
        except ToolError:
            raise
        except ValueError as exc:
            raise ToolError(str(exc))
        except Exception as exc:
            handle_tickerscope_error(exc)
            raise  # unreachable

    return wrapper
