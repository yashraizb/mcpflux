# Claude Desktop Integration Guide

## Overview

This guide explains how to integrate the Spreadsheet MCP Agent with Claude Desktop so you can query CSV and Excel files directly from Claude.

## Step 1: Get Your Absolute Path

First, find the absolute path to your mcpflux directory:

```bash
cd /Users/sakshipatne/Yash/mcpflux
pwd
```

This should output something like: `/Users/sakshipatne/Yash/mcpflux`

## Step 2: Locate Claude Desktop Config

The Claude Desktop configuration file location depends on your OS:

### macOS

```
~/Library/Application Support/Claude/claude_desktop_config.json
```

### Windows

```
%APPDATA%\Claude\claude_desktop_config.json
```

### Linux

```
~/.config/Claude/claude_desktop_config.json
```

## Step 3: Edit Configuration

If the file doesn't exist, create it. Add or merge this configuration:

```json
{
	"mcpServers": {
		"spreadsheet_agent": {
			"command": "python",
			"args": ["/absolute/path/to/mcpflux/main.py"],
			"env": {
				"OPENAI_API_KEY": "sk-your-api-key-here"
			}
		}
	}
}
```

### Full Example Configuration

```json
{
	"mcpServers": {
		"spreadsheet_agent": {
			"command": "python",
			"args": ["/Users/sakshipatne/Yash/mcpflux/main.py"],
			"env": {
				"OPENAI_API_KEY": "sk-proj-abc123...",
				"MODEL_NAME": "gpt-4o-mini"
			}
		}
	}
}
```

## Step 4: Set Up OpenAI API Key

You have two options:

### Option A: Add to Configuration (Easy)

Include the API key in the `env` section of the config (as shown above).

### Option B: Set System Environment Variable

```bash
# Add to ~/.zshrc or ~/.bash_profile
export OPENAI_API_KEY="sk-your-api-key"

# Reload shell
source ~/.zshrc
```

## Step 5: Restart Claude Desktop

1. Fully close Claude Desktop
2. Reopen Claude Desktop
3. Wait for the server to initialize (usually takes a few seconds)

## Step 6: Verify Integration

You should see a "Tools" indicator in Claude with the spreadsheet agent available.

## Testing

1. Create a test CSV file with sample data
2. Upload it to Claude
3. Ask a question like:
   - "What's the total in this spreadsheet?"
   - "Show me the top rows"
   - "Calculate the average of the revenue column"

Claude should use the spreadsheet agent automatically.

## Troubleshooting

### Server Not Appearing in Claude

1. **Check Configuration Syntax**
   - Make sure the JSON is valid (use a JSON validator)
   - Verify the file path is absolute (not relative)
   - Check that `command` is `python`

2. **Verify Python Path**

   ```bash
   which python
   python --version  # Should be 3.9+
   ```

3. **Test Server Manually**

   ```bash
   python /Users/sakshipatne/Yash/mcpflux/main.py
   ```

   Should start without errors.

4. **Restart Claude Desktop**
   - Fully close all Claude windows
   - Wait 10 seconds
   - Reopen Claude

### API Key Not Working

1. Verify the API key is correct

   ```bash
   # Test API key
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer sk-your-api-key"
   ```

2. Try setting as environment variable instead
3. Check that you have API credits

### File Not Found Errors

- Use absolute file paths
- Copy/paste files into Claude or upload them properly
- Check file exists before querying

### "Invalid SQL" Errors

- Make sure column names don't have special characters
- Try simplifying the question
- Check that the file isn't corrupted

### Server Crashes

1. Check logs in Claude Desktop
2. Run the server manually to see errors
3. Ensure all dependencies are installed
4. Check Python version is 3.9+

## Advanced Configuration

### Using Different Python Version

```json
{
	"mcpServers": {
		"spreadsheet_agent": {
			"command": "/usr/local/bin/python3.11",
			"args": ["/Users/sakshipatne/Yash/mcpflux/main.py"],
			"env": {
				"OPENAI_API_KEY": "sk-..."
			}
		}
	}
}
```

### Using Virtual Environment

```json
{
	"mcpServers": {
		"spreadsheet_agent": {
			"command": "/Users/sakshipatne/Yash/mcpflux/venv/bin/python",
			"args": ["/Users/sakshipatne/Yash/mcpflux/main.py"],
			"env": {
				"OPENAI_API_KEY": "sk-..."
			}
		}
	}
}
```

### Multiple Servers

You can have multiple MCP servers in Claude:

```json
{
	"mcpServers": {
		"spreadsheet_agent": {
			"command": "python",
			"args": ["/path/to/mcpflux/main.py"],
			"env": {
				"OPENAI_API_KEY": "sk-..."
			}
		},
		"other_server": {
			"command": "python",
			"args": ["/path/to/other/server.py"],
			"env": {}
		}
	}
}
```

## Security Notes

⚠️ **Important**: The API key is stored in plaintext in the configuration file. Consider:

1. **File Permissions**: Make sure the config file has restricted permissions

   ```bash
   chmod 600 ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

2. **Use Environment Variables**: Prefer setting `OPENAI_API_KEY` as a system environment variable instead of in the config file

3. **Limit API Key Permissions**: In OpenAI settings, you can:
   - Set usage limits
   - Restrict to specific IP addresses
   - Rotate keys regularly

## Uninstalling

To remove the server from Claude:

1. Edit the config file
2. Remove the `spreadsheet_agent` section
3. Restart Claude Desktop

```json
{
	"mcpServers": {
		// Remove spreadsheet_agent entry entirely
	}
}
```

## FAQ

**Q: Can I use multiple file types?**  
A: Yes! The server supports CSV, XLSX, and XLS files.

**Q: What's the file size limit?**  
A: DuckDB can handle millions of rows. Large files (>1GB) may be slower.

**Q: Can I use a different LLM?**  
A: Yes, edit `config.py` or set `MODEL_NAME` environment variable.

**Q: Is my data secure?**  
A: Data is processed locally. Queries are sent to OpenAI to generate SQL, but you can review the SQL before it runs.

**Q: Can I use this offline?**  
A: No, the LLM requires an internet connection to generate SQL.

**Q: Can I use other OpenAI models?**  
A: Yes, set `MODEL_NAME` to `gpt-4`, `gpt-3.5-turbo`, etc.

## Next Steps

1. Follow the [SETUP.md](SETUP.md) guide to install
2. Test the server manually
3. Integrate with Claude Desktop (this guide)
4. Start querying your spreadsheets!

## Support

- Check [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for common commands
- See [spreadsheet_mcp_agent/README.md](spreadsheet_mcp_agent/README.md) for detailed docs
- Review logs for debugging issues
