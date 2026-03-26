# PROJECT KNOWLEDGE BASE

**Generated:** 2026-03-26
**Commit:** a2c4581
**Branch:** main

## OVERVIEW

MCP server exposing MarketSurge financial data (stocks, charts, screens, watchlists) via 11 tools. Built on FastMCP + tickerscope client library. Read-only, async-first, stdio transport.

## STRUCTURE

```text
src/tickerscope_mcp/
  __init__.py        # Entry point: FastMCP server, lifespan, main()
  errors.py          # Exception mapping: tickerscope errors -> ToolError
  tools/
    stock.py         # 4 tools: analyze_stock, get_stock, get_fundamentals, get_ownership
    chart.py         # 1 tool: get_price_history (OHLCV + optional benchmark RS line)
    lists.py         # 6 tools: watchlists, screens, reports
tests/
  conftest.py        # 3 fixtures: mock_client, mcp_server, mcp_client
  test_smoke.py      # Server boot test
  test_errors.py     # Decorator + error mapping tests
  test_server.py     # Lifespan, metadata, annotations
  test_tools.py      # All tool happy-path + error cases
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add a new tool | `src/tickerscope_mcp/tools/` | New file auto-discovered via FileSystemProvider |
| Fix error messages | `src/tickerscope_mcp/errors.py` | Maps tickerscope exceptions to ToolError |
| Change server config | `src/tickerscope_mcp/__init__.py` | FastMCP instance, lifespan, instructions |
| Add test fixtures | `tests/conftest.py` | mock_client has pre-configured return values |
| Dev server config | `opencode.json` | Hot-reload via `fastmcp run --reload` |
| Upstream client API | `tickerscope` (git dep) | github.com/major/tickerscope |

## CONVENTIONS

Every tool function follows this exact pattern:

```python
@handle_tool_errors                              # MUST be outermost decorator
@tool(annotations=_ANNOTATIONS, tags={"domain"}, timeout=60.0)
async def tool_name(
    param: Annotated[str, "Description"],        # Annotated for MCP schema
    ctx: Context,                                # Always present
    optional: Annotated[str | None, "Desc"] = None,
) -> dict:
    """Docstring becomes tool description in MCP."""
    client = ctx.lifespan_context["client"]      # pyright: ignore[reportAttributeAccessIssue]
    result = await client.some_method(param)
    return result.to_dict()
```

- `from __future__ import annotations` in every module
- Absolute imports only, grouped: stdlib / third-party / local
- `tool` is cast at module top: `tool = cast(Callable[..., Any], _tool)` (works around FastMCP typing)
- Annotations constant per module: `_STOCK_ANNOTATIONS`, `_CHART_ANNOTATIONS`, `_LIST_ANNOTATIONS`
- All tools: `readOnlyHint=True`, `idempotentHint=True`, `timeout=60.0`
- Tags by domain: `stocks`, `charts`, `lists`
- PEP 257 docstrings on everything including test methods and closures

## ANTI-PATTERNS (THIS PROJECT)

- **Never suppress type errors** except the established `pyright: ignore` on `ctx.lifespan_context` access (FastMCP typing gap)
- **Never exceed cyclomatic complexity B** - `make radon` fails on C or higher
- **No logging** - errors propagate to MCP clients via ToolError, not logs
- **No .env files or env vars** - auth is implicit via browser cookies
- **Never mix screen types** - `list_screens()` = user-saved, `run_screen()` = predefined (IBD 50 etc.)

## TESTING

```python
# Integration test pattern (uses in-memory MCP client):
async def test_tool_happy_path(self, mcp_client: Client, mock_client) -> None:
    """Docstring required."""
    result = await mcp_client.call_tool("tool_name", {"param": "value"})
    data = json.loads(cast(Any, result.content[0]).text)
    assert data["key"] == "expected"
    mock_client.method.assert_called_once_with("value")

# Error test pattern:
async def test_tool_error(self, mcp_client: Client, mock_client) -> None:
    """Docstring required."""
    mock_client.method.side_effect = SymbolNotFoundError("not found", symbol="FAKE")
    with pytest.raises(ToolError, match="not found"):
        await mcp_client.call_tool("tool_name", {"symbol": "FAKE"})
```

- `asyncio_mode = "auto"` - no `@pytest.mark.asyncio` needed
- `pytest-randomly` shuffles test order - tests must be independent
- `AsyncMock(spec=AsyncTickerScopeClient)` - always use spec for type safety
- Test classes: `Test<Feature>`, methods: `test_<scenario>`

## COMMANDS

```bash
make lint        # ruff check src/ tests/
make format      # ruff format src/ tests/
make typecheck   # ty check src/
make radon       # Fail if any function rated C+
make test        # pytest -v --cov=tickerscope_mcp --cov-report=term-missing
make ci          # lint -> typecheck -> radon -> test (run before PR)
```

## NOTES

- **Auth requires browser login**: Users must log into marketsurge.investors.com in Firefox/Chrome first. Server extracts cookies at startup. Token expiration requires full server restart.
- **tickerscope is a git dependency** (not PyPI): `uv.lock` pins it. Check github.com/major/tickerscope for upstream changes.
- **Partial failures**: `analyze_stock()` returns an `errors` list instead of failing when fundamentals/ownership endpoints are down.
- **Price history param conflict**: `lookback` and `start_date/end_date` are mutually exclusive. Client raises `ValueError`.
- **FileSystemProvider**: Tools in `src/tickerscope_mcp/tools/` are auto-discovered. No manual registration needed. Just add a new `.py` file with `@tool` decorated functions.
- **run_report return types differ**: `run_report(id)` returns `list[WatchlistEntry]`, `run_report_by_name(name)` returns `AdhocScreenResult`. The tool normalizes both to `{"entries": [...], "error_values": ...}`.
