[← Back to Contents](../README.md#documentation)

# Setup Guide

## Prerequisites

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Anthropic API key (default provider) — [console.anthropic.com](https://console.anthropic.com)
- Optional: OpenAI API key or Google API key for alternate providers

---

## Installation

### 1. Navigate to the project

```bash
cd /path/to/mcpflux
```

### 2. Install dependencies

Using uv (recommended — handles virtualenv automatically):

```bash
uv sync
```

Using pip:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

### 3. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional: choose a different LLM provider
# LLM_PROVIDER=openai
# MODEL_NAME=gpt-4o-mini
# OPENAI_API_KEY=sk-your-openai-key

# Optional: LangSmith tracing (free tier at smith.langchain.com)
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=ls__your-key
# LANGSMITH_PROJECT=mcpflux

# Optional: custom paths for observability data
# EVENTS_LOG_PATH=~/.mcpflux/events.jsonl
# METRICS_DB_PATH=~/.mcpflux/metrics.db
```

### 4. Verify installation

```bash
uv run python -c "from spreadsheet_mcp_agent import run_server; print('OK')"
```

Expected output:
```
JsonlObserver writing to /Users/yourname/.mcpflux/events.jsonl
SqliteObserver writing to /Users/yourname/.mcpflux/metrics.db
OK
```

---

## Claude Desktop Integration

### Mac

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "spreadsheet-query-agent": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/mcpflux", "run", "python", "main.py"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-your-key"
      }
    }
  }
}
```

### Windows

Config location: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "spreadsheet-query-agent": {
      "command": "uv",
      "args": ["--directory", "C:\\path\\to\\mcpflux", "run", "python", "main.py"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-your-key"
      }
    }
  }
}
```

### Linux

Config location: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "spreadsheet-query-agent": {
      "command": "uv",
      "args": ["--directory", "/home/user/mcpflux", "run", "python", "main.py"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-your-key"
      }
    }
  }
}
```

After editing, restart Claude Desktop completely.

---

## Testing the Installation

### Generate example data

```bash
uv run python generate_examples.py
```

### Run a query

```python
from spreadsheet_mcp_agent.facade import SpreadsheetQueryFacade
import json

facade = SpreadsheetQueryFacade()
result = facade.execute("sales_data.csv", "What is the total revenue?")
print(json.dumps(result, indent=2))
```

---

## Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | **Required**. Anthropic API key |
| `LLM_PROVIDER` | `anthropic` | LLM provider: `anthropic`, `openai`, `google` |
| `MODEL_NAME` | `claude-haiku-4-5` | Model name for chosen provider |
| `OPENAI_API_KEY` | — | Required if `LLM_PROVIDER=openai` |
| `EVENTS_LOG_PATH` | `~/.mcpflux/events.jsonl` | Path for JSONL event log |
| `METRICS_DB_PATH` | `~/.mcpflux/metrics.db` | Path for SQLite metrics DB |
| `LANGCHAIN_TRACING_V2` | — | Set `true` for LangSmith tracing |
| `LANGCHAIN_API_KEY` | — | LangSmith API key |
| `LANGSMITH_PROJECT` | — | LangSmith project name |
| `MAX_SQL_RETRIES` | `3` | Max LLM SQL correction attempts |
| `MAX_SAMPLE_ROWS` | `5` | Rows in schema sample sent to LLM |
| `MAX_RESULT_ROWS` | `100` | Max rows returned in result |

---

## Troubleshooting

### "ANTHROPIC_API_KEY not set"

Set it in `.env` or export it:
```bash
export ANTHROPIC_API_KEY="sk-ant-your-key"
```

### "Module not found"

```bash
uv sync
```

### "File not found" when querying

Use absolute file paths:
```python
facade.execute("/Users/me/data/sales.csv", "Your question")
```

### Claude Desktop not detecting the server

1. Restart Claude Desktop completely (Cmd+Q on Mac)
2. Verify the path in `claude_desktop_config.json` is absolute
3. Test that `uv` is in PATH: `which uv`
4. Check Claude Desktop logs for errors

### SQL errors

The server automatically retries with LLM correction (up to `MAX_SQL_RETRIES` times). If still failing:
- Inspect `~/.mcpflux/events.jsonl` for correction details
- Check column names don't contain special characters
- Increase `MAX_SQL_RETRIES` in `.env`

---

## Advanced Usage

### Use a different LLM provider

```bash
LLM_PROVIDER=openai
MODEL_NAME=gpt-4o
OPENAI_API_KEY=sk-...
```

### Enable LangSmith tracing

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...
LANGSMITH_PROJECT=mcpflux
```

Then view traces at [smith.langchain.com](https://smith.langchain.com).

### Register a custom observer

```python
from spreadsheet_mcp_agent.events import PipelineObserver, PipelineEvent, PipelineStage
from spreadsheet_mcp_agent.facade import SpreadsheetQueryFacade

class SlackObserver(PipelineObserver):
    def on_event(self, event: PipelineEvent) -> None:
        if event.stage == PipelineStage.ERROR:
            # send_slack(event.data["error"])
            pass

facade = SpreadsheetQueryFacade(observers=[SlackObserver()])
```

### Increase result rows

```bash
MAX_RESULT_ROWS=500
```

---

## Support

- [Getting Started](getting-started.md)
- [Quick Reference](quick-reference.md)
- [Architecture](architecture.md)
- [Claude Desktop Integration](claude-integration.md)
