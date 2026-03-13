[← Back to Contents](../README.md#documentation)

# Quick Reference

## Quick Start

```bash
# Install
uv sync

# Copy and edit .env
cp .env.example .env   # set ANTHROPIC_API_KEY

# Run server
uv run python main.py
```

## File Structure

```
spreadsheet_mcp_agent/
├── server.py           # MCP adapter & tool registration
├── facade.py           # Pipeline orchestrator (Facade pattern)
├── events.py           # Observer pattern: event types + all observers
├── handlers.py         # SQL retry chain (Chain of Responsibility)
├── providers.py        # LLM provider abstraction (Strategy)
├── loaders.py          # File format loaders (Strategy)
├── config.py           # All configuration & env vars
├── schema_extractor.py # DataFrame → schema string
├── sql_generator.py    # NLP → SQL
├── sql_executor.py     # DuckDB SQL execution
└── llm_client.py       # Low-level LLM wrapper
```

## Key Usage

### Run a query via facade

```python
from spreadsheet_mcp_agent.facade import SpreadsheetQueryFacade

facade = SpreadsheetQueryFacade()
result = facade.execute("/path/to/data.csv", "Total sales by country")
print(result)
# {"success": True, "generated_sql": "...", "result_preview": [...], ...}
```

### Register custom observer

```python
from spreadsheet_mcp_agent.events import PipelineObserver, PipelineEvent, PipelineStage
from spreadsheet_mcp_agent.facade import SpreadsheetQueryFacade

class MyObserver(PipelineObserver):
    def on_event(self, event: PipelineEvent) -> None:
        print(f"[{event.stage.value}] run_id={event.data.get('run_id')}")

facade = SpreadsheetQueryFacade(observers=[MyObserver()])
```

### Direct module use

```python
from spreadsheet_mcp_agent.loaders import FileLoaderContext
from spreadsheet_mcp_agent.schema_extractor import extract_schema
from spreadsheet_mcp_agent.sql_generator import generate_sql
from spreadsheet_mcp_agent.sql_executor import execute_sql

df = FileLoaderContext().load("data.csv")
schema = extract_schema(df)
sql = generate_sql(schema, "Total revenue by country")
result = execute_sql(df, sql)
```

## Environment Variables

| Variable | Default | Required | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | — | Yes | Anthropic API key |
| `LLM_PROVIDER` | `anthropic` | No | `anthropic` / `openai` / `google` |
| `MODEL_NAME` | `claude-haiku-4-5` | No | Model for chosen provider |
| `OPENAI_API_KEY` | — | If OpenAI | OpenAI API key |
| `EVENTS_LOG_PATH` | `~/.mcpflux/events.jsonl` | No | JSONL event log path |
| `METRICS_DB_PATH` | `~/.mcpflux/metrics.db` | No | SQLite metrics DB path |
| `LANGCHAIN_TRACING_V2` | — | No | `true` to enable LangSmith |
| `LANGCHAIN_API_KEY` | — | If LangSmith | LangSmith API key |
| `LANGSMITH_PROJECT` | — | No | LangSmith project name |
| `MAX_SQL_RETRIES` | `3` | No | Max SQL correction retries |
| `MAX_SAMPLE_ROWS` | `5` | No | Schema sample rows |
| `MAX_RESULT_ROWS` | `100` | No | Max rows in response |

## Claude Desktop Config

Mac — edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "spreadsheet-query-agent": {
      "command": "uv",
      "args": ["--directory", "/path/to/mcpflux", "run", "python", "main.py"],
      "env": {
        "ANTHROPIC_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Observability Quick Queries

```bash
# Last 10 pipeline events
tail -10 ~/.mcpflux/events.jsonl | jq '.'

# All SQL corrections
cat ~/.mcpflux/events.jsonl | jq 'select(.stage == "sql_corrected")'

# Failed runs
sqlite3 ~/.mcpflux/metrics.db "SELECT ts, question, error FROM pipeline_runs WHERE success=0;"

# Success rate by provider
sqlite3 ~/.mcpflux/metrics.db \
  "SELECT provider, AVG(success)*100 as pct FROM pipeline_runs GROUP BY provider;"

# Average latency
sqlite3 ~/.mcpflux/metrics.db "SELECT AVG(latency_ms) FROM pipeline_runs WHERE success=1;"
```

## Response Format

```json
{
  "success": true,
  "generated_sql": "SELECT ...",
  "result_preview": [...],
  "row_count": 10,
  "total_columns": 5
}
```

Error response:
```json
{
  "success": false,
  "error": "Failed to generate SQL after 3 attempts",
  "error_type": "RuntimeError"
}
```

## Supported File Formats

- CSV (`.csv`)
- Excel (`.xlsx`, `.xls`)

## Error Handling

The server auto-recovers from SQL errors using the Chain of Responsibility:

| Attempt | What happens |
|---|---|
| 1 | Execute generated SQL |
| 2+ | LLM corrects SQL using the error message; retry |
| After MAX_SQL_RETRIES | Raise error, emit ERROR event, return error JSON |

## Troubleshooting

| Issue | Solution |
|---|---|
| `ANTHROPIC_API_KEY not set` | Set in `.env` or shell export |
| `File not found` | Use absolute paths |
| `Module not found` | Run `uv sync` |
| SQL errors not auto-fixed | Increase `MAX_SQL_RETRIES` in `.env` |
| Claude not detecting server | Restart Claude Desktop, verify absolute path in config |
| No observability data | Check `~/.mcpflux/` is writable |

## Development Commands

```bash
# Run example
uv run python spreadsheet_mcp_agent/example.py

# Generate sample data
uv run python generate_examples.py

# Format
uv run black spreadsheet_mcp_agent/

# Lint
uv run ruff check spreadsheet_mcp_agent/

# Type check
uv run mypy spreadsheet_mcp_agent/
```
