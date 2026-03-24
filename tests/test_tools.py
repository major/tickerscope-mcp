"""Tests for TickerScope MCP tools."""

from __future__ import annotations

import json
from typing import Any, cast

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from tickerscope import APIError, SymbolNotFoundError  # type: ignore[reportMissingImports]


class TestAnalyzeStock:
    """Tests for analyze_stock tool behavior and error handling."""

    async def test_analyze_stock_happy_path(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Return stock, fundamentals, and ownership data for a valid symbol."""
        result = await mcp_client.call_tool("analyze_stock", {"symbol": "AAPL"})

        response_text = cast(Any, result.content[0]).text
        data = json.loads(response_text)
        assert data["symbol"] == "AAPL"
        assert "stock" in data
        assert "fundamentals" in data
        assert "ownership" in data

        mock_client.get_stock.assert_called_once_with("AAPL")
        mock_client.get_fundamentals.assert_called_once_with("AAPL")
        mock_client.get_ownership.assert_called_once_with("AAPL")

    async def test_analyze_stock_symbol_not_found(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Raise ToolError when required stock lookup fails with unknown symbol."""
        mock_client.get_stock.side_effect = SymbolNotFoundError(
            "not found", symbol="FAKE"
        )

        with pytest.raises(ToolError, match="not found"):
            await mcp_client.call_tool("analyze_stock", {"symbol": "FAKE"})

    async def test_analyze_stock_partial_failure(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Return partial response with explicit error for failed optional section."""
        mock_client.get_ownership.side_effect = APIError(
            "ownership failed",
            errors=[{"message": "ownership endpoint down"}],
        )

        result = await mcp_client.call_tool("analyze_stock", {"symbol": "AAPL"})

        response_text = cast(Any, result.content[0]).text
        data = json.loads(response_text)
        assert data["symbol"] == "AAPL"
        assert "stock" in data
        assert "fundamentals" in data
        assert "ownership" in data
        assert "error" in data["ownership"]
