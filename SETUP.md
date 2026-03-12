# Setup Guide

## Prerequisites

- Python 3.9 or higher
- OpenAI API key (get one at https://platform.openai.com/api-keys)
- pip or uv package manager

## Installation Steps

### 1. Clone or Download the Project

```bash
cd /path/to/mcpflux
```

### 2. Create a Virtual Environment (Recommended)

Using venv:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Using uv:

```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Using pip
pip install -r spreadsheet_mcp_agent/requirements.txt

# OR using uv
uv pip install -r spreadsheet_mcp_agent/requirements.txt
```

### 4. Set Up Environment Variables

Copy the example file:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```bash
OPENAI_API_KEY=sk-your-api-key-here
```

You can also set it in your shell:

```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

### 5. Verify Installation

Test that everything is working:

```bash
python main.py
```

You should see:

```
Starting Spreadsheet MCP Agent...
```

Press Ctrl+C to stop the server.

## Integration with Claude Desktop

### Mac

1. Open Claude Desktop settings
2. Look for "Developer" settings
3. Add or edit the MCP servers configuration
4. Add this entry:

```json
{
	"mcpServers": {
		"spreadsheet_agent": {
			"command": "python",
			"args": ["/absolute/path/to/mcpflux/main.py"],
			"env": {
				"OPENAI_API_KEY": "sk-your-api-key"
			}
		}
	}
}
```

### Windows

Similar to Mac, but use the Windows path format and ensure Python is in PATH:

```json
{
	"mcpServers": {
		"spreadsheet_agent": {
			"command": "python",
			"args": ["C:\\path\\to\\mcpflux\\main.py"],
			"env": {
				"OPENAI_API_KEY": "sk-your-api-key"
			}
		}
	}
}
```

### Linux

```json
{
	"mcpServers": {
		"spreadsheet_agent": {
			"command": "python",
			"args": ["/home/user/path/to/mcpflux/main.py"],
			"env": {
				"OPENAI_API_KEY": "sk-your-api-key"
			}
		}
	}
}
```

## Testing the Installation

### Generate Example Data

```bash
python generate_examples.py
```

This creates sample CSV files for testing.

### Run a Quick Test

```bash
python -c "
import json
from spreadsheet_mcp_agent import query_spreadsheet

# Create or use existing CSV file
result = query_spreadsheet('sales_data.csv', 'What is the total revenue?')
print(json.dumps(json.loads(result), indent=2))
"
```

## Using the Server

### Command Line Testing

```bash
# Start the server
python main.py

# In another terminal, you can send requests via Claude Desktop
```

### With Claude Desktop

1. Open Claude Desktop
2. Upload a CSV or Excel file
3. Ask a question like:
   - "What's the total revenue by country?"
   - "Show me the top 5 products"
   - "Average revenue per product"

4. Claude will automatically use the MCP server to query your data

## Troubleshooting

### "OPENAI_API_KEY not set" Error

**Solution**: Make sure you've set the API key:

```bash
export OPENAI_API_KEY="sk-your-key"
python main.py
```

### "Module not found" Error

**Solution**: Reinstall dependencies:

```bash
pip install --upgrade -r spreadsheet_mcp_agent/requirements.txt
```

### "File not found" Error

**Solution**: Use absolute file paths:

```bash
python -c "
from spreadsheet_mcp_agent import query_spreadsheet
result = query_spreadsheet('/absolute/path/to/file.csv', 'Your question')
"
```

### "Invalid SQL" Errors

The server automatically attempts to fix SQL errors using the LLM. If this fails after 3 retries, check:

1. File format is correct (CSV/XLSX)
2. Column names don't have special characters
3. Data types are valid (use pandas to inspect: `pd.read_csv('file.csv').dtypes`)

### Claude Desktop Not Detecting Server

1. Restart Claude Desktop
2. Check that the server path is absolute (not relative)
3. Verify Python is accessible: `which python` or `python --version`
4. Check Claude Desktop logs for error messages

## Configuration

### Model Selection

By default, the server uses `gpt-4o-mini`. To use a different model:

```bash
export MODEL_NAME="gpt-4-turbo"
python main.py
```

Or edit `spreadsheet_mcp_agent/config.py`:

```python
MODEL_NAME = "gpt-4-turbo"  # Change this
```

### Adjust Retry Attempts

Edit `spreadsheet_mcp_agent/config.py`:

```python
MAX_SQL_RETRIES = 5  # Increase from 3 to 5
```

### Result Limit

Change how many rows are returned:

```python
MAX_RESULT_ROWS = 500  # Increase from 100 to 500
```

## Advanced Usage

### Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from spreadsheet_mcp_agent import query_spreadsheet
result = query_spreadsheet('file.csv', 'question')
```

### Custom LLM Prompts

Edit `spreadsheet_mcp_agent/sql_generator.py` to customize how questions are converted to SQL.

### Schema Customization

Modify `spreadsheet_mcp_agent/schema_extractor.py` to change what schema information is sent to the LLM.

## Performance Tips

1. **Large Files**: DuckDB can handle millions of rows, but may slow down with >10GB datasets
2. **Complex Queries**: The LLM works better with natural language descriptions
3. **Column Names**: Use clear, descriptive column names (e.g., "customer_revenue" not "cr")

## Support

For detailed documentation, see:

- [Main README](README.md)
- [Module Documentation](spreadsheet_mcp_agent/README.md)
- [OpenAI Documentation](https://platform.openai.com/docs)
- [DuckDB Documentation](https://duckdb.org)
