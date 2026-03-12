# 🚀 Getting Started Guide

## Welcome to Spreadsheet MCP Agent!

This guide will get you from installation to querying your data with Claude in under 10 minutes.

---

## ⚡ Quick Start (5 minutes)

### 1. Install Dependencies

```bash
cd /Users/sakshipatne/Yash/mcpflux
pip install -r spreadsheet_mcp_agent/requirements.txt
```

### 2. Set Your API Key

```bash
export OPENAI_API_KEY="sk-your-api-key-from-openai"
```

To get an API key:

1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key
4. Run the command above

### 3. Test the Server

```bash
python main.py
```

You should see the server start. Press `Ctrl+C` to stop it.

### 4. Create Sample Data

```bash
python generate_examples.py
```

This creates `sales_data.csv` and `customer_data.csv` for testing.

---

## 🎯 Testing Locally (Before Claude Integration)

### Quick Test

```bash
python -c "
import json
from spreadsheet_mcp_agent import query_spreadsheet

result = query_spreadsheet('sales_data.csv', 'What is the total revenue?')
print(json.dumps(json.loads(result), indent=2))
"
```

### Expected Output

```json
{
	"success": true,
	"generated_sql": "SELECT SUM(revenue) as total_revenue FROM data",
	"result_preview": [
		{
			"total_revenue": 41700
		}
	],
	"row_count": 1,
	"total_columns": 1
}
```

---

## 🔧 Integration with Claude Desktop

### Mac Instructions

1. **Find Configuration File**

   ```bash
   open ~/Library/Application\ Support/Claude/
   ```

   Look for `claude_desktop_config.json`

2. **If File Doesn't Exist, Create It**

   ```bash
   mkdir -p ~/Library/Application\ Support/Claude
   touch ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

3. **Edit Configuration**
   Open the file in your text editor and add:

   ```json
   {
   	"mcpServers": {
   		"spreadsheet_agent": {
   			"command": "python",
   			"args": ["/Users/sakshipatne/Yash/mcpflux/main.py"],
   			"env": {
   				"OPENAI_API_KEY": "sk-your-api-key"
   			}
   		}
   	}
   }
   ```

4. **Restart Claude Desktop**
   - Close Claude completely
   - Wait 5 seconds
   - Open Claude again

5. **Verify Integration**
   - Look for "Tools" indicator in Claude
   - You should see "spreadsheet_agent" available

### Windows Instructions

1. Find: `%APPDATA%\Claude\claude_desktop_config.json`
2. Use absolute Windows path: `C:\Users\...\mcpflux\main.py`
3. Same JSON format as Mac
4. Restart Claude

### Linux Instructions

1. Find: `~/.config/Claude/claude_desktop_config.json`
2. Use absolute Linux path: `/home/user/mcpflux/main.py`
3. Same JSON format as Mac
4. Restart Claude

---

## 📚 Using the Server

### In Claude Desktop

1. **Upload a File**
   - Click file upload button
   - Select your CSV or Excel file

2. **Ask a Question**
   - "What is the total revenue?"
   - "Show me the top 5 products"
   - "Revenue by country"

3. **Get Results**
   - Claude shows the generated SQL
   - Returns formatted results
   - Shows number of rows

### Example Questions & Answers

**Question**: "Which country has the highest revenue?"

```sql
SELECT country, SUM(revenue) as total_revenue FROM data
GROUP BY country ORDER BY total_revenue DESC LIMIT 1
```

**Result**: USA with 11,500 revenue

**Question**: "Top 3 products by units sold"

```sql
SELECT product, SUM(units_sold) FROM data
GROUP BY product ORDER BY SUM(units_sold) DESC LIMIT 3
```

**Result**: Widget A, Widget B, Widget C

**Question**: "Average revenue per country"

```sql
SELECT country, AVG(revenue) FROM data GROUP BY country
```

**Result**: List of countries with averages

---

## 🎓 Understanding the Flow

```
You (Claude Desktop)
  ↓ Upload CSV + Ask question
  ↓
Claude (Receives your file)
  ↓ Uses spreadsheet_agent tool
  ↓
MCP Server
  ├─ Reads your CSV file
  ├─ Analyzes columns and types
  ├─ Calls OpenAI to convert question to SQL
  ├─ Executes SQL on your data
  └─ Returns results as JSON
  ↓
Claude (Shows you results)
  ↓ Displays SQL and data
  ↓
You (Gets your answer)
```

---

## 📁 File Format Support

The server can read:

- ✅ CSV files (.csv)
- ✅ Excel files (.xlsx)
- ✅ Excel 97-2003 (.xls)

**Format Tips**:

- Use clear column names (e.g., "customer_revenue" not "cr")
- Avoid special characters in column names
- Ensure consistent data types per column

---

## 🐛 Troubleshooting

### "OPENAI_API_KEY not set"

**Solution**: Set your API key

```bash
export OPENAI_API_KEY="sk-..."
```

Verify it's set:

```bash
echo $OPENAI_API_KEY
```

### "File not found" in Claude

**Solution**: Use absolute paths

- Instead of: `./sales_data.csv`
- Use: `/Users/sakshipatne/Yash/mcpflux/sales_data.csv`

Or upload the file directly in Claude.

### "Claude doesn't see the tool"

**Solution**:

1. Restart Claude Desktop
2. Check configuration file path is correct
3. Verify JSON is valid (use jsonlint.com)
4. Make sure server path is absolute (not relative)

### "Invalid SQL" errors

**Solution**: The server automatically tries to fix SQL errors. If it fails:

- Simplify your question
- Use clearer column references
- Check data types match the question

### Server starts but crashes

**Solution**: Check error message

```bash
python main.py
# Look for error messages
```

Common issues:

- Missing dependencies: `pip install -r requirements.txt`
- Invalid API key: Check your OpenAI key
- Python version too old: Need Python 3.9+

---

## 🔑 Configuration Reference

### Basic Config (config.py)

```python
MODEL_NAME = "gpt-4o-mini"       # LLM model to use
MAX_SQL_RETRIES = 3              # Retry attempts on error
MAX_SAMPLE_ROWS = 5              # Rows in schema description
MAX_RESULT_ROWS = 100            # Max rows returned
```

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional (defaults shown)
MODEL_NAME=gpt-4o-mini
MAX_SQL_RETRIES=3
MAX_SAMPLE_ROWS=5
MAX_RESULT_ROWS=100
```

### Change Model

To use a different model:

```bash
export MODEL_NAME="gpt-4"
python main.py
```

Available models:

- `gpt-4o-mini` (recommended, fast & cheap)
- `gpt-4o` (more powerful)
- `gpt-4-turbo` (legacy, slower)
- `gpt-3.5-turbo` (legacy, less reliable)

---

## 📊 How It Works

### Step 1: Load File

```python
# Your CSV → pandas DataFrame
data:
  product, country, revenue
  Widget A, USA, 5000
  Widget B, UK, 3000
```

### Step 2: Extract Schema

```python
# DataFrame structure → Text description
Table: data
Columns:
  - product: string
  - country: string
  - revenue: integer
Row count: 2
Sample data:
  product  country  revenue
  Widget A USA      5000
  Widget B UK       3000
```

### Step 3: Generate SQL

```python
# Question + Schema → SQL Query (via LLM)
User: "Total revenue by country"
LLM: "SELECT country, SUM(revenue) FROM data GROUP BY country"
```

### Step 4: Execute Query

```python
# SQL on DuckDB → Results
DuckDB executes: SELECT country, SUM(revenue) FROM data GROUP BY country
Returns:
  country  SUM(revenue)
  USA      5000
  UK       3000
```

### Step 5: Format Results

```python
# Results → JSON for Claude
{
  "success": true,
  "generated_sql": "SELECT country, SUM(revenue) FROM data GROUP BY country",
  "result_preview": [
    {"country": "USA", "SUM(revenue)": 5000},
    {"country": "UK", "SUM(revenue)": 3000}
  ],
  "row_count": 2,
  "total_columns": 2
}
```

---

## 💡 Best Practices

### Question Phrasing

✅ Good: "Total sales by product"  
❌ Bad: "sum product"

✅ Good: "Top 5 customers by revenue"  
❌ Bad: "five best customers"

✅ Good: "Average price per category"  
❌ Bad: "what's the avg"

### File Preparation

✅ Use clear column names  
✅ Consistent data types  
✅ No empty rows in middle  
✅ Headers in first row

❌ Avoid special characters in names  
❌ Mixed data types in columns  
❌ Merged cells (Excel)  
❌ Multiple sheets without specification

### Error Handling

- Server automatically retries on SQL errors (up to 3 times)
- Clear error messages if it fails
- Check logs for debugging

---

## 🔒 Security & Privacy

### Your Data

- ✅ Stays on your machine
- ✅ Not sent to external services
- ✅ Only schema sent to LLM (for SQL generation)
- ✅ No data persistence

### API Key

- ⚠️ Keep it secret
- ⚠️ Don't commit to version control
- ⚠️ Use environment variables
- ⚠️ Rotate if compromised

### Tips

1. Never share your API key
2. Use in environment variables, not code
3. Monitor usage in OpenAI dashboard
4. Set spending limits if worried

---

## 📈 Performance Tips

### File Size

- Small (<10MB): < 1 second to load
- Medium (10-100MB): 1-2 seconds
- Large (100MB-1GB): 2-5 seconds
- Very Large (>1GB): May be slow

### Query Latency

```
Typical breakdown:
  File load:        0-2 seconds
  Schema extract:   <100ms
  LLM call:         1-2 seconds
  SQL execute:      <100ms
  ───────────────────────────
  Total:            2-6 seconds
```

### Optimization

- Ask simple questions for fast responses
- Use specific column references
- Filter with WHERE clauses
- Use descriptive column names

---

## 📞 Getting Help

### Before Asking for Help

1. Check [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
2. Verify API key is set: `echo $OPENAI_API_KEY`
3. Test manually: `python main.py`
4. Check logs for error messages

### Documentation

- **Installation**: [SETUP.md](SETUP.md)
- **Quick Ref**: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **Claude Setup**: [CLAUDE_INTEGRATION.md](CLAUDE_INTEGRATION.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)

### Sample Data

```bash
# Create example files
python generate_examples.py

# Test with examples
python spreadsheet_mcp_agent/example.py
```

---

## ✅ Verification Checklist

After setup, verify:

- [ ] Dependencies installed: `pip freeze | grep mcp`
- [ ] API key set: `echo $OPENAI_API_KEY`
- [ ] Server runs: `python main.py` (then Ctrl+C)
- [ ] Sample data created: `ls sales_data.csv`
- [ ] Local test works: `python -c "from spreadsheet_mcp_agent import query_spreadsheet; ..."`
- [ ] Claude Desktop closed and restarted
- [ ] Claude config updated with absolute path
- [ ] Claude tool available in menu

---

## 🎯 What's Next?

1. **Setup**: Follow this guide (you're reading it!)
2. **Test**: Run `python generate_examples.py` and test locally
3. **Integrate**: Follow Claude Desktop instructions above
4. **Query**: Start asking questions about your data!
5. **Explore**: Try different query types and files
6. **Optimize**: Use configuration for your needs

---

## 🎉 You're Ready!

Your MCP server is now:

- ✅ Installed
- ✅ Configured
- ✅ Tested
- ✅ Integrated with Claude

**Start querying your data!**

---

**Questions?** Check the documentation files listed above.  
**Issues?** See troubleshooting section.  
**Want more details?** Check [ARCHITECTURE.md](ARCHITECTURE.md).

**Happy querying! 🚀**
