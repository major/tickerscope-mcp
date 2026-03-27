"""Tests for TickerScope MCP tools."""

from __future__ import annotations

import json
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from tickerscope import (
    APIError,
    Catalog,
    CatalogEntry,
    SymbolNotFoundError,
)


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
                quarterly_financials=None,
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


class TestGetCatalog:
    """Tests for get_catalog tool behavior and error handling."""

    async def test_get_catalog_happy_path(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Return all catalog entries from all sources."""
        result = await mcp_client.call_tool("get_catalog", {})

        data = json.loads(cast(Any, result.content[0]).text)
        assert "entries" in data
        assert "errors" in data
        assert len(data["entries"]) == 4
        assert data["errors"] == []

        kinds = {e["kind"] for e in data["entries"]}
        assert kinds == {"watchlist", "coach_screen", "report", "screen"}

        mock_client.get_catalog.assert_called_once()

    async def test_get_catalog_filter_by_kind(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Return only entries matching the requested kind."""
        result = await mcp_client.call_tool("get_catalog", {"kind": "watchlist"})

        data = json.loads(cast(Any, result.content[0]).text)
        assert len(data["entries"]) == 1
        assert data["entries"][0]["kind"] == "watchlist"
        assert data["entries"][0]["name"] == "My Watchlist"

    async def test_get_catalog_filter_no_matches(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Return empty entries list when kind filter has no matches."""
        mock_client.get_catalog.return_value = Catalog(entries=[], errors=[])

        result = await mcp_client.call_tool("get_catalog", {"kind": "watchlist"})

        data = json.loads(cast(Any, result.content[0]).text)
        assert data["entries"] == []

    async def test_get_catalog_partial_errors(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Return entries from successful sources with errors from failed ones."""
        mock_client.get_catalog.return_value = Catalog(
            entries=[
                CatalogEntry(name="Bases Forming", kind="report", report_id=124),
            ],
            errors=["screens endpoint down"],
        )

        result = await mcp_client.call_tool("get_catalog", {})

        data = json.loads(cast(Any, result.content[0]).text)
        assert len(data["entries"]) == 1
        assert data["errors"] == ["screens endpoint down"]

    async def test_get_catalog_api_error(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Raise ToolError when catalog fetch fails entirely."""
        mock_client.get_catalog.side_effect = APIError("catalog failed")

        with pytest.raises(ToolError, match="API error"):
            await mcp_client.call_tool("get_catalog", {})


class TestRunCatalogEntry:
    """Tests for run_catalog_entry tool behavior and error handling."""

    async def test_run_report_entry(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Dispatch a report entry and return CatalogResult."""
        result = await mcp_client.call_tool(
            "run_catalog_entry",
            {"kind": "report", "name": "Bases Forming", "report_id": 124},
        )

        data = json.loads(cast(Any, result.content[0]).text)
        assert data["kind"] == "report"
        mock_client.run_catalog_entry.assert_called_once()

        entry = mock_client.run_catalog_entry.call_args.args[0]
        assert entry.kind == "report"
        assert entry.report_id == 124

    async def test_run_coach_screen_entry(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Dispatch a coach screen entry and return CatalogResult."""
        result_mock = MagicMock()
        result_mock.total = 1
        result_mock.to_dict.return_value = {
            "kind": "coach_screen",
            "screen_result": {
                "screen_name": "IBD 50",
                "elapsed_time": None,
                "num_instruments": 0,
                "rows": [],
            },
        }
        mock_client.run_catalog_entry.return_value = result_mock

        result = await mcp_client.call_tool(
            "run_catalog_entry",
            {"kind": "coach_screen", "name": "IBD 50", "coach_screen_id": "ibd50"},
        )

        data = json.loads(cast(Any, result.content[0]).text)
        assert data["kind"] == "coach_screen"
        assert data["screen_result"]["screen_name"] == "IBD 50"

    async def test_run_watchlist_entry(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Dispatch a watchlist entry and return CatalogResult with entries."""
        result_mock = MagicMock()
        result_mock.total = 1
        result_mock.to_dict.return_value = {
            "kind": "watchlist",
            "watchlist_entries": [
                {
                    "symbol": "AAPL",
                    "company_name": "Apple Inc",
                    "composite_rating": 95,
                    "rs_rating": 88,
                },
            ],
        }
        mock_client.run_catalog_entry.return_value = result_mock

        result = await mcp_client.call_tool(
            "run_catalog_entry",
            {"kind": "watchlist", "name": "My Watchlist", "watchlist_id": 123},
        )

        data = json.loads(cast(Any, result.content[0]).text)
        assert data["kind"] == "watchlist"
        assert len(data["watchlist_entries"]) == 1
        assert data["watchlist_entries"][0]["symbol"] == "AAPL"

    async def test_run_screen_entry_raises(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Raise ToolError when dispatching a screen entry (not supported)."""
        mock_client.run_catalog_entry.side_effect = NotImplementedError(
            "Screen entries cannot be dispatched"
        )

        with pytest.raises(ToolError, match="Screen entries cannot be dispatched"):
            await mcp_client.call_tool(
                "run_catalog_entry",
                {"kind": "screen", "name": "My Filter"},
            )

    async def test_run_entry_api_error(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Raise ToolError when catalog dispatch fails."""
        mock_client.run_catalog_entry.side_effect = APIError("dispatch failed")

        with pytest.raises(ToolError, match="API error"):
            await mcp_client.call_tool(
                "run_catalog_entry",
                {"kind": "report", "name": "Bad Report", "report_id": 999},
            )

    async def test_run_entry_defaults_name_to_empty(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Use empty string for name when not provided."""
        await mcp_client.call_tool(
            "run_catalog_entry",
            {"kind": "report", "report_id": 124},
        )

        entry = mock_client.run_catalog_entry.call_args.args[0]
        assert entry.name == ""

    async def test_run_entry_passes_pagination(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Pass limit and offset through to the client."""
        await mcp_client.call_tool(
            "run_catalog_entry",
            {"kind": "report", "report_id": 124, "limit": 25, "offset": 50},
        )

        call_kwargs = mock_client.run_catalog_entry.call_args.kwargs
        assert call_kwargs["limit"] == 25
        assert call_kwargs["offset"] == 50

    async def test_run_entry_builds_filters(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Build filters dict from individual filter parameters."""
        await mcp_client.call_tool(
            "run_catalog_entry",
            {
                "kind": "report",
                "report_id": 124,
                "min_composite": 80,
                "min_rs": 70,
                "exclude_spacs": True,
            },
        )

        call_kwargs = mock_client.run_catalog_entry.call_args.kwargs
        assert call_kwargs["filters"] == {
            "min_composite": 80,
            "min_rs": 70,
            "exclude_spacs": True,
        }

    async def test_run_entry_no_filters_passes_none(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Pass filters=None when no filter parameters are set."""
        await mcp_client.call_tool(
            "run_catalog_entry",
            {"kind": "report", "report_id": 124},
        )

        call_kwargs = mock_client.run_catalog_entry.call_args.kwargs
        assert call_kwargs["filters"] is None

    async def test_run_entry_parses_fields(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Parse comma-separated fields string and pass as set to to_dict."""
        await mcp_client.call_tool(
            "run_catalog_entry",
            {
                "kind": "report",
                "report_id": 124,
                "fields": "symbol, composite_rating, rs_rating",
            },
        )

        result_mock = mock_client.run_catalog_entry.return_value
        result_mock.to_dict.assert_called_once_with(
            fields={"symbol", "composite_rating", "rs_rating"}
        )

    async def test_run_entry_response_metadata(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Include total, limit, and offset in response."""
        mock_client.run_catalog_entry.return_value.total = 875

        result = await mcp_client.call_tool(
            "run_catalog_entry",
            {"kind": "report", "report_id": 124, "limit": 25, "offset": 50},
        )

        data = json.loads(cast(Any, result.content[0]).text)
        assert data["total"] == 875
        assert data["limit"] == 25
        assert data["offset"] == 50

    async def test_run_entry_defaults_offset_to_zero(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Default offset to 0 when not provided."""
        result = await mcp_client.call_tool(
            "run_catalog_entry",
            {"kind": "report", "report_id": 124},
        )

        data = json.loads(cast(Any, result.content[0]).text)
        assert data["offset"] == 0


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


class TestGetRSRatingHistory:
    """Tests for get_rs_rating_history tool behavior and error handling."""

    async def test_get_rs_rating_history_happy_path(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Return RS rating history data for a valid symbol."""
        result = await mcp_client.call_tool("get_rs_rating_history", {"symbol": "AAPL"})

        response_text = cast(Any, result.content[0]).text
        data = json.loads(response_text)
        assert data["symbol"] == "AAPL"
        assert "ratings" in data
        assert "rs_line_new_high" in data

        mock_client.get_rs_rating_history.assert_called_once_with("AAPL")

    async def test_get_rs_rating_history_symbol_not_found(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Raise ToolError when symbol is not found."""
        mock_client.get_rs_rating_history.side_effect = SymbolNotFoundError(
            "not found", symbol="FAKE"
        )

        with pytest.raises(ToolError, match="not found"):
            await mcp_client.call_tool("get_rs_rating_history", {"symbol": "FAKE"})


class TestGetChartMarkups:
    """Tests for get_chart_markups tool behavior and error handling."""

    async def test_get_chart_markups_happy_path(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Return chart markups with default frequency and sort direction."""
        result = await mcp_client.call_tool("get_chart_markups", {"symbol": "AAPL"})

        response_text = cast(Any, result.content[0]).text
        data = json.loads(response_text)
        assert "cursor_id" in data
        assert "markups" in data

        call_kwargs = mock_client.get_chart_markups.call_args.kwargs
        assert call_kwargs["frequency"] == "DAILY"
        assert call_kwargs["sort_dir"] == "ASC"

    async def test_get_chart_markups_custom_params(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Pass custom frequency and sort_dir through to the client."""
        await mcp_client.call_tool(
            "get_chart_markups",
            {"symbol": "AAPL", "frequency": "WEEKLY", "sort_dir": "DESC"},
        )

        call_kwargs = mock_client.get_chart_markups.call_args.kwargs
        assert call_kwargs["frequency"] == "WEEKLY"
        assert call_kwargs["sort_dir"] == "DESC"

    async def test_get_chart_markups_error(
        self,
        mcp_client: Client,
        mock_client,
    ) -> None:
        """Raise ToolError when API returns an error for chart markups."""
        from tickerscope import APIError

        mock_client.get_chart_markups.side_effect = APIError(
            "chart markup fetch failed"
        )

        with pytest.raises(ToolError, match="API error"):
            await mcp_client.call_tool("get_chart_markups", {"symbol": "AAPL"})
