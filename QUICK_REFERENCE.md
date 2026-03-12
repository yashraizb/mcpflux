# Quick Reference

## Quick Start

```bash
# 1. Install
pip install -r spreadsheet_mcp_agent/requirements.txt

# 2. Set API key
export OPENAI_API_KEY="sk-..."

# 3. Run server
python main.py
```

## File Structure

```
spreadsheet_mcp_agent/
├── server.py           # MCP server & main tool
├── file_loader.py      # Load CSV/Excel
├── schema_extractor.py # Extract schema
├── sql_generator.py    # Convert Q→SQL
├── sql_executor.py     # Execute SQL
├── error_recovery.py   # Retry logic
├── llm_client.py       # OpenAI API
├── config.py           # Configuration
└── requirements.txt    # Dependencies
```

## Key Functions

### Load File

```python
from spreadsheet_mcp_agent.file_loader import load_file
df = load_file("data.csv")
```

### Extract Schema

```python
from spreadsheet_mcp_agent.schema_extractor import extract_schema
schema = extract_schema(df)
```

### Generate SQL

```python
from spreadsheet_mcp_agent.sql_generator import generate_sql
sql = generate_sql(schema, "Total sales by country")
```

### Execute SQL

```python
from spreadsheet_mcp_agent.sql_executor import execute_sql
result = execute_sql(df, sql)
```

### Query Spreadsheet (All-in-one)

```python
from spreadsheet_mcp_agent import query_spreadsheet
result = query_spreadsheet("data.csv", "Your question")
```

## Configuration

Key settings in `config.py`:

```python
MODEL_NAME = "gpt-4o-mini"       # LLM model
MAX_SQL_RETRIES = 3              # Retry attempts
MAX_SAMPLE_ROWS = 5              # Schema sample size
MAX_RESULT_ROWS = 100            # Result limit
```

## Error Handling

Server automatically recovers from:

- ✓ Invalid SQL syntax
- ✓ Wrong column references
- ✓ Type mismatches
- ✓ LLM API failures (with retries)

## Common Queries

| Question    | Example                  |
| ----------- | ------------------------ |
| Aggregation | "Total revenue"          |
| Grouping    | "Sales by country"       |
| Ranking     | "Top 5 products"         |
| Filtering   | "Orders > 1000"          |
| Joining     | "Customers with revenue" |

## Logging

View detailed logs:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Log files show:

- File loading
- Schema extraction
- SQL generation
- Execution status
- Errors & retries

## Troubleshooting

| Issue              | Solution                             |
| ------------------ | ------------------------------------ |
| API key error      | `export OPENAI_API_KEY=sk-...`       |
| File not found     | Use absolute paths                   |
| Module not found   | `pip install -r requirements.txt`    |
| SQL errors         | Server auto-retries with LLM fixes   |
| Claude integration | Restart Claude, check absolute paths |

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

## Environment Variables

```bash
OPENAI_API_KEY=sk-...          # Required
MODEL_NAME=gpt-4o-mini         # Optional
MAX_SQL_RETRIES=3              # Optional
MAX_SAMPLE_ROWS=5              # Optional
MAX_RESULT_ROWS=100            # Optional
```

## Supported File Formats

- ✓ CSV (.csv)
- ✓ Excel (.xlsx, .xls)
- ✓ Gzip-compressed CSV (.csv.gz)

## Performance

- Handles millions of rows
- 1-5 second latency for most queries
- LLM calls take ~1-2 seconds
- SQL execution typically <100ms

## Integration Points

- **Claude Desktop**: Via MCP protocol
- **Custom Apps**: Import `query_spreadsheet` function
- **CLI**: Run `python main.py`
- **API**: FastMCP stdio interface

## Next Steps

1. Read [SETUP.md](SETUP.md) for detailed installation
2. Check [spreadsheet_mcp_agent/README.md](spreadsheet_mcp_agent/README.md) for docs
3. Run `generate_examples.py` to create sample data
4. Test with `python -c "..."`
5. Integrate with Claude Desktop

## Resources

- [OpenAI API Docs](https://platform.openai.com/docs)
- [DuckDB Docs](https://duckdb.org)
- [MCP Spec](https://modelcontextprotocol.io)
- [FastMCP Docs](https://github.com/jlowin/fastmcp)
