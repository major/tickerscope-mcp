"""Tests for TickerScope MCP server core functionality."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from tickerscope import (
    APIError,
    AsyncTickerScopeClient,
    CookieExtractionError,
    HTTPError,
    SymbolNotFoundError,
    TickerScopeError,
    TokenExpiredError,
)

from fastmcp.decorators import get_fastmcp_meta
from fastmcp.tools.function_tool import FunctionTool

from tickerscope_mcp import handle_tickerscope_error, mcp

STOCK_TOOLS = {"analyze_stock", "get_stock", "get_fundamentals", "get_ownership"}
LIST_TOOLS = {"list_watchlists", "get_watchlist", "list_screens", "run_screen"}
CHART_TOOLS = {"get_price_history"}


class TestErrorMapping:
    """Test error mapping from tickerscope to ToolError."""

    async def test_symbol_not_found_error(self) -> None:
        """Test SymbolNotFoundError maps to ToolError with symbol."""
        exc = SymbolNotFoundError("not found", symbol="FAKE")
        with pytest.raises(ToolError, match="not found"):
            handle_tickerscope_error(exc)

    async def test_token_expired_error(self) -> None:
        """Test TokenExpiredError maps to ToolError with restart message."""
        exc = TokenExpiredError("expired", status_code=401)
        with pytest.raises(ToolError, match="[Rr]estart"):
            handle_tickerscope_error(exc)

    async def test_cookie_extraction_error(self) -> None:
        """Test CookieExtractionError maps to ToolError with login message."""
        exc = CookieExtractionError("no cookies", browser="firefox")
        with pytest.raises(ToolError, match="Log into MarketSurge"):
            handle_tickerscope_error(exc)

    async def test_api_error(self) -> None:
        """Test APIError maps to ToolError with error message."""
        exc = APIError("api failed", errors=[{"message": "invalid query"}])
        with pytest.raises(ToolError, match="api failed"):
            handle_tickerscope_error(exc)

    async def test_http_error(self) -> None:
        """Test HTTPError maps to ToolError with status code and message."""
        exc = HTTPError(
            status_code=429,
            response_body="rate limited",
            message="Too many requests",
        )
        with pytest.raises(ToolError, match="429"):
            handle_tickerscope_error(exc)

    async def test_unknown_tickerscope_error_uses_user_message(self) -> None:
        """Test unhandled TickerScopeError subclass delegates to user_message."""
        exc = TickerScopeError("something broke")
        with pytest.raises(ToolError, match="An unexpected error occurred"):
            handle_tickerscope_error(exc)


class TestLifespan:
    """Test server lifespan management."""

    async def test_lifespan_creates_and_closes_client(self) -> None:
        """Test lifespan creates client via .create() and closes via .aclose()."""
        mock_client = AsyncMock(spec=AsyncTickerScopeClient)
        with patch.object(
            AsyncTickerScopeClient,
            "create",
            new=AsyncMock(return_value=mock_client),
        ):
            async with Client(mcp):
                # Lifespan ran, client was created
                pass
        mock_client.aclose.assert_called_once()


class TestServerSetup:
    """Test server configuration."""

    def test_mcp_name(self) -> None:
        """Test MCP server has correct name."""
        assert mcp.name == "tickerscope"

    def test_mcp_instructions(self) -> None:
        """Test MCP server has instructions."""
        assert mcp.instructions is not None
        assert len(mcp.instructions) > 0


class TestToolMetadata:
    """Test tool annotations, tags, and timeouts on all 9 tools."""

    async def test_all_nine_tools_registered(self) -> None:
        """Test all 9 expected tools are registered."""
        tools = await mcp.list_tools()
        names = {t.name for t in tools}
        expected = STOCK_TOOLS | LIST_TOOLS | CHART_TOOLS
        assert expected.issubset(names)

    async def test_stock_tools_have_stocks_tag(self) -> None:
        """Test stock tools have the 'stocks' domain tag."""
        tools = await mcp.list_tools()
        tool_map = {t.name: t for t in tools}
        for name in STOCK_TOOLS:
            assert "stocks" in tool_map[name].tags, f"{name} missing 'stocks' tag"

    async def test_list_tools_have_lists_tag(self) -> None:
        """Test list tools have the 'lists' domain tag."""
        tools = await mcp.list_tools()
        tool_map = {t.name: t for t in tools}
        for name in LIST_TOOLS:
            assert "lists" in tool_map[name].tags, f"{name} missing 'lists' tag"

    async def test_chart_tools_have_charts_tag(self) -> None:
        """Test chart tools have the 'charts' domain tag."""
        tools = await mcp.list_tools()
        tool_map = {t.name: t for t in tools}
        for name in CHART_TOOLS:
            assert "charts" in tool_map[name].tags, f"{name} missing 'charts' tag"

    async def test_all_tools_have_timeout(self) -> None:
        """Test all 9 tools have a 60-second timeout in their __fastmcp__ metadata."""
        tools = await mcp.list_tools()
        tool_map = {t.name: t for t in tools}
        all_tools = STOCK_TOOLS | LIST_TOOLS | CHART_TOOLS
        for name in all_tools:
            tool = tool_map[name]
            assert isinstance(tool, FunctionTool), f"{name} is not a FunctionTool"
            meta = get_fastmcp_meta(tool.fn)
            assert meta is not None, f"{name} has no __fastmcp__ metadata"
            assert meta.timeout == 60.0, f"{name} timeout != 60.0"

    async def test_all_tools_have_read_only_annotation(self) -> None:
        """Test all 9 tools have readOnlyHint=True annotation."""
        tools = await mcp.list_tools()
        tool_map = {t.name: t for t in tools}
        all_tools = STOCK_TOOLS | LIST_TOOLS | CHART_TOOLS
        for name in all_tools:
            ann = tool_map[name].annotations
            assert ann is not None, f"{name} has no annotations"
            assert ann.readOnlyHint is True, f"{name} readOnlyHint != True"

    async def test_all_tools_have_idempotent_annotation(self) -> None:
        """Test all 9 tools have idempotentHint=True annotation."""
        tools = await mcp.list_tools()
        tool_map = {t.name: t for t in tools}
        all_tools = STOCK_TOOLS | LIST_TOOLS | CHART_TOOLS
        for name in all_tools:
            ann = tool_map[name].annotations
            assert ann is not None, f"{name} has no annotations"
            assert ann.idempotentHint is True, f"{name} idempotentHint != True"
