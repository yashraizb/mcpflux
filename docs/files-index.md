[← Back to Contents](../README.md#documentation)

# Codebase File Index

## Project Structure

```
mcpflux/
│
├── README.md                        Main overview, quick start, API format
├── main.py                          Server entry point (imports run_server)
├── pyproject.toml                   Project metadata, dependencies, build config
├── .env.example                     Environment variable template
├── generate_examples.py             Creates sample CSV files for testing
│
├── docs/
│   ├── getting-started.md           5-minute install and first query
│   ├── setup.md                     Detailed installation and configuration
│   ├── quick-reference.md           Config vars, commands, common queries
│   ├── claude-integration.md        Claude Desktop setup on Mac/Windows/Linux
│   ├── architecture.md              System design, patterns, data flow
│   ├── files-index.md               This file
│   ├── implementation-summary.md    What was built and how it works
│   ├── documentation-index.md       Learning paths by use case
│   ├── deployment-checklist.md      Pre-deployment verification
│   ├── project-checklist.md         Deliverables and features checklist
│   ├── project-complete.md          Completion summary
│   └── delivery-summary.md          High-level overview
│
└── spreadsheet_mcp_agent/
    ├── __init__.py                  Package exports (run_server)
    │
    ├── server.py                    MCP server adapter
    ├── facade.py                    Pipeline orchestrator (Facade pattern)
    ├── events.py                    Observer pattern: events + all observers
    ├── handlers.py                  SQL retry chain (Chain of Responsibility)
    ├── providers.py                 LLM provider abstraction (Strategy)
    ├── loaders.py                   File format loaders (Strategy)
    ├── config.py                    Configuration dataclass + env vars
    ├── schema_extractor.py          DataFrame → LLM-friendly schema string
    ├── sql_generator.py             NLP question → SQL
    ├── sql_executor.py              DuckDB SQL execution
    ├── llm_client.py                Low-level LLM API wrapper
    ├── error_recovery.py            Legacy recovery helpers
    └── example.py                   Usage examples and local test
```

---

## File Descriptions

### Entry Points

#### `main.py`
- Calls `run_server()` from the package
- Usage: `uv run python main.py`

#### `spreadsheet_mcp_agent/__init__.py`
- Exports: `run_server`

---

### Core Pipeline Modules

#### `spreadsheet_mcp_agent/server.py`
- **Pattern**: MCP adapter
- **Responsibilities**: FastMCP setup, `@mcp.tool()` registration, observer wiring, `run_server()`
- Instantiates `SpreadsheetQueryFacade` with `LoggingObserver`, `JsonlObserver`, `SqliteObserver`
- Catches all exceptions and returns JSON error response

#### `spreadsheet_mcp_agent/facade.py`
- **Pattern**: Facade
- **Key class**: `SpreadsheetQueryFacade`
- **Key method**: `execute(file_path, question) -> dict`
- Generates `run_id` (UUID4) per execution; tracks wall-clock timing
- Calls private methods: `_load`, `_extract_schema`, `_generate_sql`, `_execute_sql`, `_format_result`
- Notifies all observers at each stage via `_notify(stage, data)`
- Emits `ERROR` event on unhandled exception

#### `spreadsheet_mcp_agent/events.py`
- **Pattern**: Observer
- **`PipelineStage`**: Enum — START, FILE_LOADED, SCHEMA_EXTRACTED, SQL_GENERATED, SQL_CORRECTED, SQL_EXECUTED, COMPLETE, ERROR
- **`PipelineEvent`**: Dataclass with `stage: PipelineStage` and `data: dict`
- **`PipelineObserver`**: ABC with abstract `on_event(event)`
- **`LoggingObserver`**: Logs to Python logger
- **`MetricsObserver`**: Placeholder for push-based sinks
- **`JsonlObserver`**: Appends JSON lines to `~/.mcpflux/events.jsonl`; immediate flush per write
- **`SqliteObserver`**: Writes one row per completed run to `~/.mcpflux/metrics.db`; accumulates state in `self._runs` keyed by `run_id`

#### `spreadsheet_mcp_agent/handlers.py`
- **Pattern**: Chain of Responsibility
- **`SqlContext`**: Dataclass — schema, sql, execute_func, max_retries, attempt, last_error, result, success
- **`SqlHandler`**: ABC with `handle(ctx)` and `set_next(handler)`
- **`ExecuteHandler`**: Calls `execute_func(ctx.sql)`, sets `ctx.success = True` on success
- **`CorrectionHandler`**: On failure, builds a LangChain correction prompt, calls LLM, updates `ctx.sql`, increments `ctx.attempt`, re-triggers chain
- **`ExhaustedHandler`**: Terminal handler — raises `RuntimeError` when retries exhausted
- **`build_handler_chain(schema, execute_func, max_retries)`**: Factory
- **`retry_with_recovery(schema, sql, execute_func, max_retries)`**: Public API

#### `spreadsheet_mcp_agent/providers.py`
- **Pattern**: Strategy
- **`LLMProvider`**: ABC with `generate(prompt) -> str` and `get_runnable() -> Runnable`
- **`AnthropicProvider`**: Claude via `langchain-anthropic`; default
- **`OpenAIProvider`**: GPT via `langchain-openai`
- **`GoogleProvider`**: Gemini via `langchain-google-genai` (placeholder)
- **`get_provider() -> LLMProvider`**: Factory; reads `LLM_PROVIDER` env var

#### `spreadsheet_mcp_agent/loaders.py`
- **Pattern**: Strategy
- **`FileLoaderStrategy`**: ABC with `load(path) -> pd.DataFrame`
- **`CsvLoaderStrategy`**: `pd.read_csv()`
- **`ExcelLoaderStrategy`**: `pd.read_excel()`
- **`FileLoaderContext`**: Selects strategy by file extension; validates format and existence

#### `spreadsheet_mcp_agent/config.py`
- **`Config`**: Dataclass with all settings loaded from env vars
- Settings: `LLM_PROVIDER`, `MODEL_NAME`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `EVENTS_LOG_PATH`, `METRICS_DB_PATH`, `MAX_SQL_RETRIES`, `MAX_SAMPLE_ROWS`, `MAX_RESULT_ROWS`, `ALLOWED_FILE_FORMATS`
- `validate()`: Raises `ValueError` if `ANTHROPIC_API_KEY` is empty
- Global instance: `config`

---

### Supporting Modules

#### `spreadsheet_mcp_agent/schema_extractor.py`
- **`extract_schema(df) -> str`**: Returns LLM-friendly string with column names, types, sample rows, row count

#### `spreadsheet_mcp_agent/sql_generator.py`
- **`generate_sql(schema, question) -> str`**: Builds a LangChain prompt with schema + question, calls the active provider, strips markdown fences from response

#### `spreadsheet_mcp_agent/sql_executor.py`
- **`execute_sql(df, sql) -> pd.DataFrame`**: Registers DataFrame as DuckDB `data` table; executes SQL; returns result DataFrame

#### `spreadsheet_mcp_agent/llm_client.py`
- Low-level LLM wrapper used by legacy code and `sql_generator.py`; handles retry on 529 (overloaded)

#### `spreadsheet_mcp_agent/error_recovery.py`
- Legacy error recovery helpers; superseded by `handlers.py` but retained for compatibility

#### `spreadsheet_mcp_agent/file_loader.py`
- Legacy file loader; superseded by `loaders.py` but retained for compatibility

#### `spreadsheet_mcp_agent/example.py`
- Standalone example: creates sample data, runs queries via facade, prints results

---

## Dependencies

### Runtime

| Package | Version | Purpose |
|---|---|---|
| `mcp` | ≥0.1.0 | Model Context Protocol |
| `fastmcp` | ≥0.0.10 | MCP server framework |
| `pandas` | ≥2.0.0 | Data manipulation |
| `duckdb` | ≥0.9.0 | In-memory SQL execution |
| `openpyxl` | ≥3.0.0 | Excel file support |
| `python-dotenv` | ≥1.0.0 | `.env` file loading |
| `anthropic` | ≥0.7.0 | Anthropic API client |
| `langchain` | ≥0.3.0 | LLM chain orchestration |
| `langchain-anthropic` | ≥0.3.0 | Claude via LangChain |
| `langsmith` | ≥0.1.0 | LLM tracing (optional) |

### Development

| Package | Purpose |
|---|---|
| `pytest` | Testing |
| `black` | Code formatting |
| `mypy` | Type checking |
| `ruff` | Linting |

---

## Observability Files (runtime, not in repo)

| Path | Format | Created By | Purpose |
|---|---|---|---|
| `~/.mcpflux/events.jsonl` | JSONL | `JsonlObserver` | One line per pipeline event |
| `~/.mcpflux/metrics.db` | SQLite | `SqliteObserver` | One row per completed run |
