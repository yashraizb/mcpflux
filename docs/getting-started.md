[← Back to Contents](../README.md#documentation)

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

1. Find: `%APPDATA%\Claude