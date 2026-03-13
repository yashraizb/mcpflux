[← Back to Contents](../README.md#documentation)

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
%APPDATA%\Claude