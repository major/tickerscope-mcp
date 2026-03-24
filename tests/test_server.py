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
    SymbolNotFoundError,
    TokenExpiredError,
)

from tickerscope_mcp import handle_tickerscope_error, mcp


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
        """Test APIError maps to ToolError with error details."""
        errors = [{"message": "invalid query"}]
        exc = APIError("api failed", errors=errors)
        with pytest.raises(ToolError, match="API error"):
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
