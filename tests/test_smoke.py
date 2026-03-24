"""Smoke test for TickerScope MCP server initialization and connection."""

from __future__ import annotations

from fastmcp import Client


class TestSmoke:
    """Smoke tests for server boot and connection."""

    async def test_server_boots_and_connects(self, mcp_client: Client) -> None:
        """Test that the server boots and connects via in-memory Client.

        Args:
            mcp_client: MCP client fixture with mocked TickerScope client.
        """
        assert mcp_client is not None
