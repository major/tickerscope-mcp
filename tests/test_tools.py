"""Tests for TickerScope MCP tools."""

from __future__ import annotations

import json
from typing import Any, cast

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from tickerscope import APIError, SymbolNotFoundError, WatchlistEntry


class TestAnalyzeStock:
    """Tests for analyze_stock tool behavior and error handling."""

    async def test_analyze_stock_happy_path(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Return stock analysis data for a valid symbol."""
        result = await mcp_client.call_tool("analyze_stock", {"symbol": "AAPL"})

        response_text = cast(Any, result.content[0]).text
        data = json.loads(response_text)
        assert data["symbol"] == "AAPL"
        assert "stock" in data
        assert "fundamentals" in data
        assert "ownership" in data
        assert data["errors"] == []

        mock_client.get_stock_analysis.assert_called_once_with("AAPL")

    async def test_analyze_stock_symbol_not_found(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Raise ToolError when stock analysis fails with unknown symbol."""
        mock_client.get_stock_analysis.side_effect = SymbolNotFoundError(
            "not found", symbol="FAKE"
        )

        with pytest.raises(ToolError, match="not found"):
            await mcp_client.call_tool("analyze_stock", {"symbol": "FAKE"})

    async def test_analyze_stock_partial_failure(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Return analysis with errors list when optional sections fail."""
        from tickerscope import StockAnalysis, StockData

        mock_client.get_stock_analysis.return_value = StockAnalysis(
            symbol="AAPL",
            stock=StockData(
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
            ),
            fundamentals=None,
            ownership=None,
            errors=["ownership endpoint down"],
        )

        result = await mcp_client.call_tool("analyze_stock", {"symbol": "AAPL"})

        response_text = cast(Any, result.content[0]).text
        data = json.loads(response_text)
        assert data["symbol"] == "AAPL"
        assert "stock" in data
        assert "fundamentals" not in data  # omitted when None (omit_none=True)
        assert "ownership" not in data  # omitted when None (omit_none=True)
        assert data["errors"] == ["ownership endpoint down"]


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

    async def test_price_history_lookback(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Call with lookback='6M', verify it is passed through to the client."""
        result = await mcp_client.call_tool(
            "get_price_history",
            {"symbol": "AAPL", "lookback": "6M"},
        )

        data = json.loads(cast(Any, result.content[0]).text)
        assert data["symbol"] == "AAPL"
        assert data["lookback"] == "6M"

        call_kwargs = mock_client.get_chart_data.call_args.kwargs
        assert call_kwargs["lookback"] == "6M"

    @pytest.mark.parametrize("lookback", ["1W", "1M", "3M", "6M", "1Y", "YTD"])
    async def test_price_history_all_lookbacks(
        self,
        mcp_client: Client,
        mock_client,
        lookback: str,
    ) -> None:
        """All supported lookback values are passed through to the client."""
        await mcp_client.call_tool(
            "get_price_history",
            {"symbol": "AAPL", "lookback": lookback},
        )

        call_kwargs = mock_client.get_chart_data.call_args.kwargs
        assert call_kwargs["lookback"] == lookback

    async def test_price_history_validation_conflict(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Raise ToolError when both lookback and dates are provided."""
        mock_client.get_chart_data.side_effect = ValueError(
            "lookback cannot be combined with start_date"
        )

        with pytest.raises(ToolError, match="lookback cannot be combined"):
            await mcp_client.call_tool(
                "get_price_history",
                {
                    "symbol": "AAPL",
                    "start_date": "2025-01-01",
                    "end_date": "2025-03-01",
                    "lookback": "6M",
                },
            )

    async def test_price_history_validation_missing(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Raise ToolError when neither dates nor lookback are provided."""
        mock_client.get_chart_data.side_effect = ValueError(
            "either lookback or start_date and end_date must be provided"
        )

        with pytest.raises(ToolError, match="lookback or start_date"):
            await mcp_client.call_tool(
                "get_price_history",
                {"symbol": "AAPL"},
            )

    async def test_price_history_benchmark(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Pass benchmark symbol through to the client for RS line computation."""
        await mcp_client.call_tool(
            "get_price_history",
            {"symbol": "AAPL", "lookback": "1Y", "benchmark": "0S&P5"},
        )

        call_kwargs = mock_client.get_chart_data.call_args.kwargs
        assert call_kwargs["benchmark"] == "0S&P5"

    async def test_price_history_benchmark_defaults_none(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Omit benchmark from client call when not provided."""
        await mcp_client.call_tool(
            "get_price_history",
            {"symbol": "AAPL", "lookback": "1M"},
        )

        call_kwargs = mock_client.get_chart_data.call_args.kwargs
        assert call_kwargs["benchmark"] is None

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
                {"symbol": "FAKE", "lookback": "1M"},
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
        assert data[0]["id"] == 123
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
        mock_client.screen_watchlist_by_name.return_value = [
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

        mock_client.screen_watchlist_by_name.assert_called_once_with("My Watchlist")

    async def test_get_watchlist_not_found(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Raise ToolError when watchlist name does not match any known watchlist."""
        mock_client.screen_watchlist_by_name.side_effect = APIError(
            "No watchlist found with name 'Nonexistent'"
        )

        with pytest.raises(ToolError, match="API error"):
            await mcp_client.call_tool("get_watchlist", {"name": "Nonexistent"})


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


class TestGetStock:
    """Tests for get_stock tool behavior and error handling."""

    async def test_get_stock_happy_path(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Return stock data for a valid symbol."""
        result = await mcp_client.call_tool("get_stock", {"symbol": "AAPL"})

        response_text = cast(Any, result.content[0]).text
        data = json.loads(response_text)
        assert data["symbol"] == "AAPL"

        mock_client.get_stock.assert_called_once_with("AAPL")

    async def test_get_stock_symbol_not_found(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Raise ToolError when symbol is not found."""
        mock_client.get_stock.side_effect = SymbolNotFoundError(
            "not found", symbol="FAKE"
        )

        with pytest.raises(ToolError, match="not found"):
            await mcp_client.call_tool("get_stock", {"symbol": "FAKE"})


class TestGetFundamentals:
    """Tests for get_fundamentals tool behavior and error handling."""

    async def test_get_fundamentals_happy_path(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Return fundamentals data for a valid symbol."""
        result = await mcp_client.call_tool("get_fundamentals", {"symbol": "AAPL"})

        response_text = cast(Any, result.content[0]).text
        data = json.loads(response_text)
        assert data["symbol"] == "AAPL"

        mock_client.get_fundamentals.assert_called_once_with("AAPL")

    async def test_get_fundamentals_symbol_not_found(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Raise ToolError when symbol is not found."""
        mock_client.get_fundamentals.side_effect = SymbolNotFoundError(
            "not found", symbol="FAKE"
        )

        with pytest.raises(ToolError, match="not found"):
            await mcp_client.call_tool("get_fundamentals", {"symbol": "FAKE"})


class TestGetOwnership:
    """Tests for get_ownership tool behavior and error handling."""

    async def test_get_ownership_happy_path(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Return ownership data for a valid symbol."""
        result = await mcp_client.call_tool("get_ownership", {"symbol": "AAPL"})

        response_text = cast(Any, result.content[0]).text
        data = json.loads(response_text)
        assert data["symbol"] == "AAPL"

        mock_client.get_ownership.assert_called_once_with("AAPL")

    async def test_get_ownership_symbol_not_found(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Raise ToolError when symbol is not found."""
        mock_client.get_ownership.side_effect = SymbolNotFoundError(
            "not found", symbol="FAKE"
        )

        with pytest.raises(ToolError, match="not found"):
            await mcp_client.call_tool("get_ownership", {"symbol": "FAKE"})
