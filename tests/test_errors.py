"""Tests for TickerScope MCP error handling utilities."""

from __future__ import annotations

import pytest
from fastmcp.exceptions import ToolError
from tickerscope import (
    HTTPError,
    SymbolNotFoundError,
)

from tickerscope_mcp.errors import handle_tool_errors


class TestHandleToolErrors:
    """Test the handle_tool_errors decorator."""

    @pytest.mark.asyncio
    async def test_catches_symbol_not_found_error(self) -> None:
        """Test SymbolNotFoundError is caught and re-raised as ToolError."""

        @handle_tool_errors
        async def my_tool():
            """Raise SymbolNotFoundError."""
            raise SymbolNotFoundError("not found", symbol="FAKE")

        with pytest.raises(ToolError, match="not found"):
            await my_tool()

    @pytest.mark.asyncio
    async def test_catches_value_error(self) -> None:
        """Test ValueError is caught and re-raised as ToolError."""

        @handle_tool_errors
        async def my_tool():
            """Raise ValueError."""
            raise ValueError("invalid date")

        with pytest.raises(ToolError, match="invalid date"):
            await my_tool()

    @pytest.mark.asyncio
    async def test_passes_through_tool_error(self) -> None:
        """Test ToolError propagates unchanged through the decorator."""

        @handle_tool_errors
        async def my_tool():
            """Raise ToolError directly."""
            raise ToolError("explicit error")

        with pytest.raises(ToolError, match="explicit error"):
            await my_tool()

    @pytest.mark.asyncio
    async def test_catches_http_error(self) -> None:
        """Test HTTPError is caught and re-raised as ToolError with status code."""

        @handle_tool_errors
        async def my_tool():
            """Raise HTTPError."""
            raise HTTPError(
                status_code=429,
                response_body="rate limited",
                message="Too many requests",
            )

        with pytest.raises(ToolError, match="429"):
            await my_tool()

    @pytest.mark.asyncio
    async def test_catches_unknown_exception(self) -> None:
        """Test unknown exceptions are caught and re-raised as ToolError with 'Unexpected error'."""

        @handle_tool_errors
        async def my_tool():
            """Raise RuntimeError."""
            raise RuntimeError("crash")

        with pytest.raises(ToolError, match="Unexpected error"):
            await my_tool()

    def test_preserves_function_metadata(self) -> None:
        """Test functools.wraps preserves function name and docstring."""

        @handle_tool_errors
        async def my_tool():
            """My tool docstring."""

        assert my_tool.__name__ == "my_tool"
        assert my_tool.__doc__ is not None
