# Spreadsheet MCP Agent

A production-quality MCP (Model Context Protocol) server that integrates with Claude Desktop to query CSV and Excel files using natural language.

## Features

- **Natural Language Queries**: Ask questions about your data in plain English
- **Multi-Format Support**: CSV, XLSX, XLS files
- **Multi-Provider LLM**: Anthropic (default), OpenAI, Google
- **DuckDB Execution**: Fast, reliable in-memory SQL execution
- **LLM-Powered SQL Correction**: Auto-corrects broken SQL with retry logic
- **Persistent Observability**: JSONL event log + SQLite metrics DB survive process death
- **LangSmith Tracing**: Optional LLM-level tracing via LangSmith (free tier)
- **Design Patterns**: Facade, Observer, Strategy, Chain of Responsibility

## Quick Start

### Installation

```bash
cd mcpflux

# Install dependencies (recommended: uv)
uv sync

# OR with pip
pip install -e .
```

### Set API Key

```bash
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=your-key
```

### Run the Server

```bash
uv run python main.py
```

### Integration with Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac):

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

## Usage Examples

Once integrated with Claude Desktop:

1. **Point Claude at a file** by providing its path
2. **Ask a question** about the data:
   - "Which country has the highest revenue?"
   - "What are the top 5 customers by spending?"
   - "Show me the average sales per month"

3. **Get instant results** with the generated SQL and data preview

## Architecture

```
Claude Desktop
    │ (file_path + question)
    ▼
MCP Server (server.py)          ← thin adapter
    │
    ▼
SpreadsheetQueryFacade          ← Facade pattern; orchestrates pipeline
    │                             emits PipelineEvents at each stage
    ├── FileLoaderContext        ← Strategy pattern (CSV / Excel)
    │
    ├── SchemaExtractor
    │
    ├── SqlGenerator             ← LLM provider via Strategy pattern
    │   └── LLMProvider          (Anthropic / OpenAI / Google)
    │
    └── retry_with_recovery()   ← Chain of Responsibility
            ExecuteHandler → CorrectionHandler → ExhaustedHandler

Observers (notified at every stage):
    ├── LoggingObserver          ← Python logger
    ├── JsonlObserver            ← ~/.mcpflux/events.jsonl  (immediate flush)
    └── SqliteObserver           ← ~/.mcpflux/metrics.db    (one row per run)

LangSmith (optional)            ← auto-traces all LangChain calls
```

## Project Structure

```
mcpflux/
├── main.py                          # Entry point
├── pyproject.toml                   # Project config & dependencies
├── .env.example                     # Environment variable template
├── README.md                        # This file
├── docs/                            # All documentation
│   ├── architecture.md
│   ├── getting-started.md
│   ├── setup.md
│   ├── quick-reference.md
│   ├── claude-integration.md
│   ├── files-index.md
│   └── ...
└── spreadsheet_mcp_agent/
    ├── __init__.py
    ├── server.py                    # MCP server & tool registration
    ├── facade.py                    # Pipeline orchestrator (Facade pattern)
    ├── events.py                    # Observer pattern + all observer classes
    ├── handlers.py                  # SQL retry chain (Chain of Responsibility)
    ├── providers.py                 # LLM provider abstraction (Strategy)
    ├── loaders.py                   # File format loaders (Strategy)
    ├── config.py                    # Configuration & env vars
    ├── schema_extractor.py          # DataFrame → LLM-friendly schema
    ├── sql_generator.py             # NLP question → SQL
    ├── sql_executor.py              # DuckDB execution
    ├── llm_client.py                # Low-level LLM wrapper
    ├── error_recovery.py            # Legacy recovery helpers
    └── example.py                   # Example usage
```

## Module Overview

| Module               | Pattern               | Purpose                                      |
|----------------------|-----------------------|----------------------------------------------|
| `server.py`          | MCP adapter           | Exposes `query_spreadsheet` tool via FastMCP |
| `facade.py`          | Facade                | Orchestrates the full pipeline; emits events |
| `events.py`          | Observer              | Event types + LoggingObserver, JsonlObserver, SqliteObserver |
| `handlers.py`        | Chain of Responsibility | SQL execution + LLM-powered SQL correction  |
| `providers.py`       | Strategy              | Anthropic / OpenAI / Google LLM providers    |
| `loaders.py`         | Strategy              | CSV and Excel file loading                   |
| `config.py`          | —                     | All env vars and defaults                    |
| `schema_extractor.py`| —                     | Extract schema string from DataFrame         |
| `sql_generator.py`   | —                     | NLP → SQL using LLM                         |
| `sql_executor.py`    | —                     | Execute SQL on DataFrame via DuckDB          |

## Configuration

All settings via environment variables (see `.env.example`):

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# LLM provider (default: anthropic)
LLM_PROVIDER=anthropic         # "anthropic" | "openai" | "google"
MODEL_NAME=claude-haiku-4-5    # model for chosen provider
OPENAI_API_KEY=sk-...          # if using OpenAI

# Observability (paths default to ~/.mcpflux/)
EVENTS_LOG_PATH=~/.mcpflux/events.jsonl
METRICS_DB_PATH=~/.mcpflux/metrics.db

# LangSmith tracing (optional, free tier)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGSMITH_PROJECT=mcpflux

# Tuning
MAX_SQL_RETRIES=3
MAX_SAMPLE_ROWS=5
MAX_RESULT_ROWS=100
```

## Observability

Every pipeline run is tracked across two persistent stores that survive MCP server process death:

### JSONL Event Log (`~/.mcpflux/events.jsonl`)
One JSON line per event, immediately flushed:
```bash
cat ~/.mcpflux/events.jsonl | jq 'select(.stage == "sql_corrected")'
```

### SQLite Metrics DB (`~/.mcpflux/metrics.db`)
One row per completed run, queryable with SQL:
```bash
sqlite3 ~/.mcpflux/metrics.db \
  "SELECT provider, AVG(success)*100, AVG(corrections), AVG(latency_ms)
   FROM pipeline_runs GROUP BY provider;"
```

### LangSmith (optional)
Set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` to get full LLM-level traces (token usage, per-call latency, retries) in the LangSmith dashboard.

## API Format

### Tool Input
```json
{
  "file_path": "/path/to/data.csv",
  "question": "Which country has the highest revenue?"
}
```

### Tool Output (success)
```json
{
  "success": true,
  "generated_sql": "SELECT country, SUM(revenue) as total FROM data GROUP BY country ORDER BY total DESC LIMIT 1",
  "result_preview": [{"country": "USA", "total": 50000}],
  "row_count": 1,
  "total_columns": 2
}
```

### Tool Output (error)
```json
{
  "success": false,
  "error": "Failed to generate SQL after 3 attempts",
  "error_type": "RuntimeError"
}
```

## Error Handling

SQL errors trigger the Chain of Responsibility:
1. `ExecuteHandler` attempts SQL execution
2. On failure → `CorrectionHandler` sends SQL + error to LLM for correction
3. Retries from step 1 (up to `MAX_SQL_RETRIES` times)
4. `ExhaustedHandler` raises a descriptive error if all retries fail

## Development

```bash
# Run examples
uv run python spreadsheet_mcp_agent/example.py

# Generate sample data
uv run python generate_examples.py

# Code quality
uv run black spreadsheet_mcp_agent/
uv run ruff check spreadsheet_mcp_agent/
uv run mypy spreadsheet_mcp_agent/
```

## Requirements

- Python 3.10+
- Anthropic API key (or OpenAI/Google key for alternate providers)

## Documentation

| Document | Description |
|---|---|
| [Getting Started](docs/getting-started.md) | 5-minute install, config, and first query |
| [Setup Guide](docs/setup.md) | Detailed installation and environment setup |
| [Claude Desktop Integration](docs/claude-integration.md) | Connect to Claude Desktop on Mac/Windows/Linux |
| [Quick Reference](docs/quick-reference.md) | Commands, config, and common queries at a glance |
| [Architecture](docs/architecture.md) | System design, patterns, data flow, and module breakdown |
| [Files Index](docs/files-index.md) | Complete codebase file descriptions |
| [Implementation Summary](docs/implementation-summary.md) | What was built and how it works |
| [Documentation Index](docs/documentation-index.md) | Learning paths by use case |
| [Deployment Checklist](docs/deployment-checklist.md) | Pre-deployment verification steps |

## License

MIT
