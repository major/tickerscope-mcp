"""Shared test fixtures for TickerScope MCP server."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Client
from tickerscope import (
    AsyncTickerScopeClient,
    ChartData,
    FundamentalData,
    OwnershipData,
    Screen,
    ScreenResult,
    StockData,
    WatchlistSummary,
)

from tickerscope_mcp import mcp


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mocked AsyncTickerScopeClient with pre-configured return values.

    Returns:
        AsyncMock: Mocked client with spec=AsyncTickerScopeClient and all 6 tool
                   methods configured with minimal but valid dataclass instances.
    """
    client = AsyncMock(spec=AsyncTickerScopeClient)

    # Configure return values for all 6 tool paths
    client.get_stock.return_value = StockData(
        symbol="AAPL",
        ratings=None,
        company=None,
        pricing=None,
        financials=None,
        corporate_actions=None,
        industry=None,
        ownership=None,
        fundamentals=None,
        patterns=[],
    )

    client.get_fundamentals.return_value = FundamentalData(
        symbol="AAPL",
        company_name=None,
        reported_earnings=[],
        reported_sales=[],
        eps_estimates=[],
        sales_estimates=[],
    )

    client.get_ownership.return_value = OwnershipData(
        symbol="AAPL",
        funds_float_pct=None,
        quarterly_funds=[],
    )

    client.get_chart_data.return_value = ChartData(
        symbol="AAPL",
        time_series=None,
        quote=None,
        premarket_quote=None,
        postmarket_quote=None,
        current_market_state=None,
        exchange=None,
    )

    client.get_watchlist_names.return_value = [
        WatchlistSummary(
            id="123",
            name="My Watchlist",
            last_modified=None,
            description=None,
        )
    ]

    client.get_watchlist.return_value = []

    client.get_screens.return_value = [
        Screen(
            id="ibd50",
            name="IBD 50",
            type="PREDEFINED",
            source=None,
            description=None,
            filter_criteria=None,
            created_at=None,
            updated_at=None,
        )
    ]

    client.run_screen.return_value = ScreenResult(
        screen_name="IBD 50",
        elapsed_time=None,
        num_instruments=0,
        rows=[],
    )

    return client


@pytest.fixture
def mcp_server() -> object:
    """Return the FastMCP server instance.

    Returns:
        FastMCP: The mcp server instance from tickerscope_mcp module.
    """
    return mcp


@pytest.fixture
async def mcp_client(mock_client: AsyncMock, mcp_server: object) -> Client:
    """Create an MCP client with mocked AsyncTickerScopeClient.

    Injects the mock_client via patch.object so that when the server's
    lifespan calls AsyncTickerScopeClient.create(), it returns the mock.

    Args:
        mock_client: Mocked AsyncTickerScopeClient fixture.
        mcp_server: FastMCP server instance fixture.

    Yields:
        Client: Connected MCP client for testing.
    """
    with patch.object(
        AsyncTickerScopeClient,
        "create",
        new=AsyncMock(return_value=mock_client),
    ):
        async with Client(mcp_server) as client:
            yield client
