# Spreadsheet MCP Agent

A production-quality MCP (Model Context Protocol) server that integrates with Claude Desktop to query CSV and Excel files using natural language.

## Features

✨ **Natural Language Queries**: Ask questions about your data in plain English  
📊 **Multi-Format Support**: CSV, XLSX, XLS files  
🤖 **LLM-Powered**: Converts questions to SQL automatically  
⚡ **DuckDB Execution**: Fast, reliable query execution  
🔄 **Error Recovery**: Automatic SQL correction and retries  
📝 **Type-Safe**: Full type hints throughout  
📋 **Production Ready**: Comprehensive logging and error handling

## Quick Start

### Installation

```bash
# Clone or navigate to project
cd mcpflux

# Install dependencies
pip install -r spreadsheet_mcp_agent/requirements.txt

# Set up API key
export OPENAI_API_KEY="your-api-key-here"
```

### Running the Server

```bash
python main.py
```

### Integration with Claude Desktop

Add to your Claude Desktop configuration:

```json
{
	"mcpServers": {
		"spreadsheet_agent": {
			"command": "python",
			"args": ["/path/to/mcpflux/main.py"],
			"env": {
				"OPENAI_API_KEY": "your-api-key"
			}
		}
	}
}
```

## Usage Examples

Once integrated with Claude Desktop:

1. **Upload a CSV or Excel file** to Claude
2. **Ask a question** about the data:
   - "Which country has the highest revenue?"
   - "What are the top 5 customers by spending?"
   - "Show me the average sales per month"

3. **Get instant results** with the generated SQL query and data

## Architecture

```
Claude Desktop
    ↓
MCP Server (query_spreadsheet tool)
    ↓
File Loader
    ↓
Schema Extractor
    ↓
LLM → SQL Generator
    ↓
DuckDB SQL Executor
    ↓
Error Recovery (if needed)
    ↓
JSON Results
```

## Project Structure

```
mcpflux/
├── main.py                          # Entry point
├── pyproject.toml                   # Project config
├── README.md                        # This file
└── spreadsheet_mcp_agent/
    ├── __init__.py                  # Package exports
    ├── server.py                    # MCP server & main tool
    ├── config.py                    # Configuration
    ├── file_loader.py               # CSV/Excel loading
    ├── schema_extractor.py          # Schema extraction
    ├── sql_generator.py             # Question → SQL
    ├── sql_executor.py              # DuckDB execution
    ├── error_recovery.py            # Retry & recovery
    ├── llm_client.py                # OpenAI wrapper
    ├── example.py                   # Example usage
    ├── requirements.txt             # Dependencies
    └── README.md                    # Detailed docs
```

## Module Overview

| Module                | Purpose                                  |
| --------------------- | ---------------------------------------- |
| `server.py`           | MCP server with `query_spreadsheet` tool |
| `file_loader.py`      | Load CSV/Excel to DataFrame              |
| `schema_extractor.py` | Extract & format schema for LLM          |
| `sql_generator.py`    | Convert NLP question to SQL              |
| `sql_executor.py`     | Execute SQL on DataFrame via DuckDB      |
| `error_recovery.py`   | Retry with LLM-powered correction        |
| `llm_client.py`       | OpenAI API integration                   |
| `config.py`           | Configuration & validation               |

## Configuration

Edit `spreadsheet_mcp_agent/config.py`:

```python
MODEL_NAME = "gpt-4o-mini"       # LLM model
MAX_SQL_RETRIES = 3              # Retry attempts
MAX_SAMPLE_ROWS = 5              # Schema sample size
MAX_RESULT_ROWS = 100            # Result limit
```

Or set environment variables:

```bash
export MODEL_NAME="gpt-4o-mini"
export OPENAI_API_KEY="sk-..."
```

## Example Data

Create `sample_data.csv`:

```csv
product,country,revenue,date
Widget A,USA,5000,2024-01-01
Widget B,USA,3000,2024-01-01
Widget A,UK,4000,2024-01-02
Widget C,Canada,2000,2024-01-02
```

## Development

### Run Examples

```bash
python spreadsheet_mcp_agent/example.py
```

### Testing

```bash
pytest spreadsheet_mcp_agent/
```

### Code Quality

```bash
black spreadsheet_mcp_agent/
ruff check spreadsheet_mcp_agent/
mypy spreadsheet_mcp_agent/
```

## Error Handling

The server gracefully handles:

- Invalid file formats
- Empty datasets
- Malformed SQL
- LLM API failures
- File not found errors

On SQL errors, the system:

1. Captures the error
2. Sends original SQL + error to LLM
3. Asks model to fix it
4. Retries (up to 3 times)

## Logging

Full structured logging to debug queries:

```
2024-01-15 10:23:45 - spreadsheet_mcp_agent.server - INFO - Processing query: Which country has the highest revenue?
2024-01-15 10:23:45 - spreadsheet_mcp_agent.file_loader - INFO - Loading CSV file: /path/to/data.csv
2024-01-15 10:23:46 - spreadsheet_mcp_agent.schema_extractor - INFO - Schema extracted: 2456 characters
2024-01-15 10:23:47 - spreadsheet_mcp_agent.llm_client - INFO - Calling gpt-4o-mini with prompt of length 1024
2024-01-15 10:23:48 - spreadsheet_mcp_agent.sql_generator - INFO - Generated SQL: SELECT country, SUM(revenue) as total_revenue ...
2024-01-15 10:23:48 - spreadsheet_mcp_agent.sql_executor - INFO - Query executed successfully. Result shape: (1, 2)
```

## API Format

### Request

```json
{
	"file_path": "/path/to/data.csv",
	"question": "Which country has the highest revenue?"
}
```

### Response

```json
{
	"success": true,
	"generated_sql": "SELECT country, SUM(revenue) as total_revenue FROM data GROUP BY country ORDER BY total_revenue DESC LIMIT 1",
	"result_preview": [
		{
			"country": "USA",
			"total_revenue": 50000
		}
	],
	"row_count": 1,
	"total_columns": 2
}
```

## Requirements

- Python 3.9+
- OpenAI API key
- Internet connection (for LLM calls)

## Documentation

| Document | Description |
|---|---|
| [Getting Started](docs/getting-started.md) | 5-minute install, config, and first query |
| [Setup Guide](docs/setup.md) | Detailed installation and environment setup |
| [Claude Desktop Integration](docs/claude-integration.md) | Connect to Claude Desktop on Mac/Windows/Linux |
| [Quick Reference](docs/quick-reference.md) | Commands, config, and common queries at a glance |
| [Architecture](docs/architecture.md) | System design, data flow, and module breakdown |
| [Implementation Summary](docs/implementation-summary.md) | What was built and how it works |
| [Files Index](docs/files-index.md) | Complete codebase file descriptions |
| [Documentation Index](docs/documentation-index.md) | Learning paths by use case |
| [Deployment Checklist](docs/deployment-checklist.md) | Pre-deployment verification steps |
| [Project Checklist](docs/project-checklist.md) | Deliverables and features checklist |
| [Project Complete](docs/project-complete.md) | Completion summary and production readiness |
| [Delivery Summary](docs/delivery-summary.md) | High-level overview of delivered components |

## License

MIT
