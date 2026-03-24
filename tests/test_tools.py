"""Tests for TickerScope MCP tools."""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any, cast

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from tickerscope import APIError, SymbolNotFoundError, WatchlistEntry  # type: ignore[reportMissingImports]


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


class TestGetPriceHistory:
    """Tests for get_price_history tool behavior and error handling."""

    async def test_price_history_dates(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Call with explicit start_date and end_date, verify mock receives them."""
        result = await mcp_client.call_tool(
            "get_price_history",
            {"symbol": "AAPL", "start_date": "2025-01-01", "end_date": "2025-03-01"},
        )

        data = json.loads(cast(Any, result.content[0]).text)
        assert data["symbol"] == "AAPL"
        assert data["start_date"] == "2025-01-01"
        assert data["end_date"] == "2025-03-01"

        call_kwargs = mock_client.get_chart_data.call_args.kwargs
        assert call_kwargs["start_date"] == "2025-01-01"
        assert call_kwargs["end_date"] == "2025-03-01"

    async def test_price_history_period(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Call with period='6M', verify computed start_date is ~180 days ago."""
        result = await mcp_client.call_tool(
            "get_price_history",
            {"symbol": "AAPL", "period": "6M"},
        )

        data = json.loads(cast(Any, result.content[0]).text)
        assert data["symbol"] == "AAPL"

        call_kwargs = mock_client.get_chart_data.call_args.kwargs
        expected_start = (date.today() - timedelta(days=180)).isoformat()
        assert call_kwargs["start_date"] == expected_start
        assert call_kwargs["end_date"] == date.today().isoformat()
        assert call_kwargs["max_points"] == 500

    @pytest.mark.parametrize(
        ("period", "expected_days"),
        [
            ("1W", 7),
            ("1M", 30),
            ("3M", 90),
            ("6M", 180),
            ("1Y", 365),
        ],
    )
    async def test_price_history_all_periods(
        self,
        mcp_client: Client,
        mock_client,
        period: str,
        expected_days: int,
    ) -> None:
        """All supported periods parse to the correct number of days."""
        await mcp_client.call_tool(
            "get_price_history",
            {"symbol": "AAPL", "period": period},
        )

        call_kwargs = mock_client.get_chart_data.call_args.kwargs
        expected_start = (date.today() - timedelta(days=expected_days)).isoformat()
        assert call_kwargs["start_date"] == expected_start
        assert call_kwargs["end_date"] == date.today().isoformat()

    async def test_price_history_max_points(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Custom max_points=100 is passed through to the client."""
        await mcp_client.call_tool(
            "get_price_history",
            {"symbol": "AAPL", "period": "1M", "max_points": 100},
        )

        call_kwargs = mock_client.get_chart_data.call_args.kwargs
        assert call_kwargs["max_points"] == 100

    async def test_price_history_default_max_points(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Default max_points=500 is used when not specified."""
        await mcp_client.call_tool(
            "get_price_history",
            {"symbol": "AAPL", "period": "1M"},
        )

        call_kwargs = mock_client.get_chart_data.call_args.kwargs
        assert call_kwargs["max_points"] == 500

    async def test_price_history_validation_both(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Raise ToolError when both dates and period are provided."""
        with pytest.raises(ToolError, match="not both"):
            await mcp_client.call_tool(
                "get_price_history",
                {
                    "symbol": "AAPL",
                    "start_date": "2025-01-01",
                    "end_date": "2025-03-01",
                    "period": "6M",
                },
            )

    async def test_price_history_validation_neither(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Raise ToolError when neither dates nor period are provided."""
        with pytest.raises(ToolError, match="start_date and end_date"):
            await mcp_client.call_tool(
                "get_price_history",
                {"symbol": "AAPL"},
            )

    async def test_price_history_symbol_not_found(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Raise ToolError when symbol is not found."""
        mock_client.get_chart_data.side_effect = SymbolNotFoundError(
            "not found", symbol="FAKE"
        )

        with pytest.raises(ToolError, match="not found"):
            await mcp_client.call_tool(
                "get_price_history",
                {"symbol": "FAKE", "period": "1M"},
            )


class TestListWatchlists:
    """Tests for list_watchlists tool behavior."""

    async def test_list_watchlists_happy_path(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Return list of watchlists with id, name, and description."""
        result = await mcp_client.call_tool("list_watchlists", {})

        data = json.loads(cast(Any, result.content[0]).text)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == "123"
        assert data[0]["name"] == "My Watchlist"
        assert "description" in data[0]
        assert "last_modified" not in data[0]

        mock_client.get_watchlist_names.assert_called_once()

    async def test_list_watchlists_empty(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Return empty list when no watchlists exist."""
        mock_client.get_watchlist_names.return_value = []

        result = await mcp_client.call_tool("list_watchlists", {})

        if result.content:
            data = json.loads(cast(Any, result.content[0]).text)
        else:
            data = cast(Any, result.structured_content).get("result", [])
        assert data == []


class TestGetWatchlist:
    """Tests for get_watchlist tool behavior and error handling."""

    async def test_get_watchlist_enriched(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Return enriched watchlist entries with to_dict() serialization."""
        mock_client.get_watchlist.return_value = [
            WatchlistEntry(
                symbol="AAPL",
                company_name="Apple Inc",
                list_rank=1,
                price=150.0,
                price_net_change=2.5,
                price_pct_change=1.7,
                price_pct_off_52w_high=-5.0,
                volume=1000000,
                volume_change=50000,
                volume_pct_change=5.0,
                composite_rating=95,
                eps_rating=90,
                rs_rating=88,
                acc_dis_rating="A",
                smr_rating="A",
                industry_group_rank=10,
                industry_name="Technology",
            )
        ]

        result = await mcp_client.call_tool("get_watchlist", {"name": "My Watchlist"})

        data = json.loads(cast(Any, result.content[0]).text)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["symbol"] == "AAPL"
        assert data[0]["company_name"] == "Apple Inc"
        assert data[0]["composite_rating"] == 95

        mock_client.get_watchlist_names.assert_called_once()
        mock_client.get_watchlist.assert_called_once_with(123)

    async def test_get_watchlist_not_found(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Raise ToolError when watchlist name does not match any known watchlist."""
        with pytest.raises(ToolError, match="not found"):
            await mcp_client.call_tool("get_watchlist", {"name": "Nonexistent"})

    async def test_get_watchlist_id_conversion(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Convert string ID '123' from WatchlistSummary to int 123 for get_watchlist call."""
        await mcp_client.call_tool("get_watchlist", {"name": "My Watchlist"})

        mock_client.get_watchlist.assert_called_once_with(123)


class TestListScreens:
    """Tests for list_screens tool behavior."""

    async def test_list_screens_happy_path(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Return list of screens with id, name, description, and type."""
        result = await mcp_client.call_tool("list_screens", {})

        data = json.loads(cast(Any, result.content[0]).text)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == "ibd50"
        assert data[0]["name"] == "IBD 50"
        assert data[0]["type"] == "PREDEFINED"
        assert "description" in data[0]
        assert "filter_criteria" not in data[0]

        mock_client.get_screens.assert_called_once()

    async def test_list_screens_empty(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Return empty list when no screens exist."""
        mock_client.get_screens.return_value = []

        result = await mcp_client.call_tool("list_screens", {})

        if result.content:
            data = json.loads(cast(Any, result.content[0]).text)
        else:
            data = cast(Any, result.structured_content).get("result", [])
        assert data == []


class TestRunScreen:
    """Tests for run_screen tool behavior and error handling."""

    async def test_run_screen_happy_path(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Return screen results with screen_name, num_instruments, and rows."""
        result = await mcp_client.call_tool("run_screen", {"screen_name": "IBD 50"})

        data = json.loads(cast(Any, result.content[0]).text)
        assert data["screen_name"] == "IBD 50"
        assert "num_instruments" in data
        assert "rows" in data
        mock_client.run_screen.assert_called_once_with("IBD 50", [])

    async def test_run_screen_with_params(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Pass screen parameters through to the client."""
        params = [{"name": "MinPrice", "value": "10"}]
        await mcp_client.call_tool(
            "run_screen", {"screen_name": "IBD 50", "parameters": params}
        )

        mock_client.run_screen.assert_called_once_with("IBD 50", params)

    async def test_run_screen_no_params_default(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Default to empty parameters list when none provided."""
        await mcp_client.call_tool("run_screen", {"screen_name": "IBD 50"})

        mock_client.run_screen.assert_called_once_with("IBD 50", [])

    async def test_run_screen_api_error(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Raise ToolError when API returns an error."""
        mock_client.run_screen.side_effect = APIError("screen failed")

        with pytest.raises(ToolError, match="API error"):
            await mcp_client.call_tool("run_screen", {"screen_name": "INVALID"})
