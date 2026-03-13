[← Back to Contents](../README.md#documentation)

# Getting Started

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Anthropic API key — get one at [console.anthropic.com](https://console.anthropic.com)

---

## 1. Install Dependencies

```bash
cd /path/to/mcpflux

# With uv (recommended)
uv sync

# OR with pip
pip install -e .
```

---

## 2. Set Your API Key

```bash
cp .env.example .env
```

Edit `.env` and set your key:

```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

To use OpenAI instead:

```bash
LLM_PROVIDER=openai
MODEL_NAME=gpt-4o-mini
OPENAI_API_KEY=sk-your-openai-key
```

---

## 3. Test the Server

```bash
uv run python main.py
```

You should see:
```
JsonlObserver writing to /Users/yourname/.mcpflux/events.jsonl
SqliteObserver writing to /Users/yourname/.mcpflux/metrics.db
Starting MCP server — provider=anthropic, model=claude-haiku-4-5
```

Press `Ctrl+C` to stop.

---

## 4. Create Sample Data

```bash
uv run python generate_examples.py
```

This creates `sales_data.csv` and `customer_data.csv` for testing.

---

## 5. Run a Quick Local Test

```python
from spreadsheet_mcp_agent.facade import SpreadsheetQueryFacade
import json

facade = SpreadsheetQueryFacade()
result = facade.execute("sales_data.csv", "What is the total revenue?")
print(json.dumps(result, indent=2))
```

Expected output:
```json
{
  "success": true,
  "generated_sql": "SELECT SUM(revenue) as total_revenue FROM data",
  "result_preview": [{"total_revenue": 41700}],
  "row_count": 1,
  "total_columns": 1
}
```

---

## 6. Integrate with Claude Desktop

### Mac

1. Open (or create) the config file:
   ```bash
   open ~/Library/Application\ Support/Claude/
   # Edit: claude_desktop_config.json
   ```

2. Add the server entry:
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

3. Restart Claude Desktop completely (Cmd+Q, then reopen).

4. Verify: look for the hammer/tools icon in Claude — you should see `query_spreadsheet` available.

### Windows

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

Config location: `%APPDATA%\Claude\claude_desktop_config.json`

### Linux

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

Config location: `~/.config/Claude/claude_desktop_config.json`

---

## 7. Query Your Data

In Claude Desktop:

1. Tell Claude the path to your file:
   > "Query `/Users/me/data/sales.csv` — which country has the highest revenue?"

2. Claude will call `query_spreadsheet` automatically and return results.

Example questions:
- "What are the top 5 products by revenue in `sales_data.csv`?"
- "Show the average order value per month from `/path/to/orders.xlsx`"
- "How many unique customers are in `/path/to/customers.csv`?"

---

## 8. View Observability Data

After running queries, check the persistent logs:

```bash
# Recent events
tail -20 ~/.mcpflux/events.jsonl | jq '.'

# All SQL corrections (shows where the LLM had to fix SQL)
cat ~/.mcpflux/events.jsonl | jq 'select(.stage == "sql_corrected")'

# Run history
sqlite3 ~/.mcpflux/metrics.db \
  "SELECT ts, question, success, corrections, latency_ms FROM pipeline_runs ORDER BY ts DESC LIMIT 10;"
```

---

## Next Steps

- [Setup Guide](setup.md) — detailed installation and advanced configuration
- [Quick Reference](quick-reference.md) — all config vars, commands, and query examples
- [Architecture](architecture.md) — how the pipeline works internally
- [Claude Desktop Integration](claude-integration.md) — troubleshooting the integration
