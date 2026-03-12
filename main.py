#!/usr/bin/env python3
"""Main entry point for the Spreadsheet MCP Agent."""

import sys
from spreadsheet_mcp_agent import run_server

if __name__ == "__main__":
    try:
        print("Starting Spreadsheet MCP Agent...", file=sys.stderr)
        run_server()
    except KeyboardInterrupt:
        print("\nServer stopped by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)