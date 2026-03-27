"""Shared test fixtures for TickerScope MCP server."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Client, FastMCP
from tickerscope import (
    AsyncTickerScopeClient,
    Catalog,
    CatalogEntry,
    CatalogResult,
    ChartData,
    ChartMarkup,
    ChartMarkupList,
    FundamentalData,
    OwnershipData,
    RSRatingHistory,
    RSRatingSnapshot,
    StockAnalysis,
    StockData,
)

from tickerscope_mcp import mcp


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mocked AsyncTickerScopeClient with pre-configured return values.

    Returns:
        AsyncMock: Mocked client with spec=AsyncTickerScopeClient and tool
                   methods configured with minimal but valid dataclass instances.
    """
    client = AsyncMock(spec=AsyncTickerScopeClient)

    stock = StockData(
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
        tight_areas=[],
        quarterly_financials=None,
    )

    fundamentals = FundamentalData(
        symbol="AAPL",
        company_name=None,
        reported_earnings=[],
        reported_sales=[],
        eps_estimates=[],
        sales_estimates=[],
    )

    ownership = OwnershipData(
        symbol="AAPL",
        funds_float_pct=None,
        quarterly_funds=[],
    )

    client.get_stock_analysis.return_value = StockAnalysis(
        symbol="AAPL",
        stock=stock,
        fundamentals=fundamentals,
        ownership=ownership,
        errors=[],
    )

    client.get_stock.return_value = stock
    client.get_fundamentals.return_value = fundamentals
    client.get_ownership.return_value = ownership

    client.get_chart_data.return_value = ChartData(
        symbol="AAPL",
        time_series=None,
        benchmark_time_series=None,
        quote=None,
        premarket_quote=None,
        postmarket_quote=None,
        current_market_state=None,
        exchange=None,
    )

    client.get_rs_rating_history.return_value = RSRatingHistory(
        symbol="AAPL",
        ratings=[
            RSRatingSnapshot(
                letter_value="A",
                period="week",
                period_offset="0",
                value=92,
            ),
            RSRatingSnapshot(
                letter_value=None,
                period="month",
                period_offset="-1",
                value=None,
            ),
        ],
        rs_line_new_high=True,
    )

    client.get_chart_markups.return_value = ChartMarkupList(
        cursor_id="cursor_abc123",
        markups=[
            ChartMarkup(
                id="markup-001",
                name="Breakout pattern",
                data='{"shapes":[]}',
                frequency="DAILY",
                site="marketsurge",
                created_at="2025-01-15T10:00:00Z",
                updated_at="2025-01-20T14:30:00Z",
            )
        ],
    )

    client.get_catalog.return_value = Catalog(
        entries=[
            CatalogEntry(name="My Watchlist", kind="watchlist", watchlist_id=123),
            CatalogEntry(name="IBD 50", kind="coach_screen", coach_screen_id="ibd50"),
            CatalogEntry(name="Bases Forming", kind="report", report_id=124),
            CatalogEntry(name="My Filter", kind="screen"),
        ],
        errors=[],
    )

    client.run_catalog_entry.return_value = CatalogResult(
        kind="report",
        screen_result=None,
        adhoc_result=None,
        watchlist_entries=None,
    )

    return client


@pytest.fixture
def mcp_server() -> FastMCP:
    """Return the FastMCP server instance.

    Returns:
        FastMCP: The mcp server instance from tickerscope_mcp module.
    """
    return mcp


@pytest.fixture
async def mcp_client(mock_client: AsyncMock, mcp_server: FastMCP) -> Client:
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
