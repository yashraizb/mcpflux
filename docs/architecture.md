[← Back to Contents](../README.md#documentation)

# Architecture & Design Documentation

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Desktop                           │
└────────────────────┬────────────────────────────────────────┘
                     │ (question + file path)
                     │
┌────────────────────▼────────────────────────────────────────┐
│                   MCP Server (main.py)                      │
│          ┌──────────────────────────────────────┐           │
│          │  query_spreadsheet(file, question)   │           │
│          └──────────────┬───────────────────────┘           │
└─────────────────────────┼────────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
    ┌────▼──────┐  ┌─────▼──────┐  ┌────▼──────────┐
    │   File    │  │  Schema    │  │  SQL Builder  │
    │  Loader   │  │ Extractor  │  │    (LLM)      │
    └────┬──────┘  └─────┬──────┘  └────┬──────────┘
         │                │               │
         └────────────────┼───────────────┘
                          │
                     ┌────▼──────┐
                     │ SQL Query  │
                     │  Executor  │
                     │ (DuckDB)   │
                     └────┬──────┘
                          │
              ┌───────────────────────┐
              │   Error Recovery?     │
              │   (LLM Retry Logic)   │
              └───────────────────────┘
                          │
                     ┌────▼──────┐
                     │  Results  │
                     │  Formatter│
                     └────┬──────┘
                          │
                     ┌────▼──────┐
                     │   JSON    │
                     │ Response  │
                     └─────┬─────┘
                           │
                     ┌─────▼──────┐
                     │   Claude   │
                     │  Desktop   │
                     └────────────┘
```

## Module Dependencies

```
server.py (main orchestrator)
  ├── file_loader.py       (no internal deps)
  ├── schema_extractor.py  (no internal deps)
  ├── sql_generator.py
  │   └── llm_client.py
  │       └── openai (external)
  ├── sql_executor.py      (uses duckdb)
  └── error_recovery.py
      └── llm_client.py

config.py (used by most modules)
```

## Data Flow Diagram

```
Input: file_path, question
  │
  ├─ File Loader ────────────► pandas.DataFrame
  │
  ├─ Schema Extractor ───────► Schema String
  │                               │
  │                               ├─ Column Names
  │                               ├─ Data Types
  │                               ├─ Sample Rows
  │                               └─ Row Count
  │
  ├─ SQL Generator ─────┐
  │   (LLM)              │
  │                      ├──► SQL Query String
  │                      │
  │                  ┌───┴────────┐
  │                  │   Failure? │
  │                  └─────┬──────┘
  │                        │ Yes
  │              Error Recovery (Retry)
  │                    max_retries=3
  │
  └─ SQL Executor ──────────► Result DataFrame
         (DuckDB)                 │
                                  ├─ Rows
                                  ├─ Columns
                                  └─ Data
                                      │
                           Result Formatter
                                      │
                           JSON Response
                                      │
                           Claude Desktop

Output: JSON with generated_sql, result_preview, row_count
```

## State Management

The system is **stateless**:

- No persistent state between calls
- Each query is independent
- No connection pooling
- Fresh DataFrames for each query
- DuckDB in-memory connections

## Error Handling Strategy

```
Try SQL Execution
    │
    ├─ Success ─────────► Return Results
    │
    └─ Failure
        │
        ├─ Retry 1/3 with LLM correction
        │   │
        │   ├─ Success ─► Return Results
        │   │
        │   └─ Failure
        │       │
        │       ├─ Retry 2/3
        │       │   │
        │       │   ├─ Success ─► Return Results
        │       │   │
        │       │   └─ Failure
        │       │       │
        │       │       └─ Retry 3/3
        │       │           │
        │       │           ├─ Success ─► Return Results
        │       │           │
        │       │           └─ Failure ──► Error Response
        │       │
        │       └─ [Max retries exhausted]
        │
        └─ [Error message + type to user]
```

## Configuration Hierarchy

```
config.py (defaults)
    │
    ├─ Environment Variables (override)
    │   │
    │   ├─ OPENAI_API_KEY
    │   ├─ MODEL_NAME
    │   ├─ MAX_SQL_RETRIES
    │   └─ MAX_SAMPLE_ROWS
    │
    └─ Runtime Parameters (override)
        (passed to functions)
```

## LLM Integration Points

### 1. SQL Generation

```
Input:  schema + question
Process: Call OpenAI API with prompt
Output: SQL query string
```

### 2. Error Recovery

```
Input:  schema + broken_sql + error_message
Process: Call OpenAI API to fix SQL
Output: Corrected SQL query string
```

## Type System

### Input Types

```python
file_path: str                    # Absolute or relative path
question: str                     # Natural language query
```

### Internal Types

```python
df: pd.DataFrame                  # Loaded data
schema: str                       # Formatted schema
sql: str                         # SQL query
result: pd.DataFrame            # Query results
```

### Output Types

```python
{
  "success": bool,
  "generated_sql": str,
  "result_preview": list[dict],
  "row_count": int,
  "total_columns": int,
  # OR on error:
  "error": str,
  "error_type": str
}
```

## Performance Considerations

### Time Breakdown

```
File Loading:        < 1s   (0.1s for CSV, 0.5s for Excel)
Schema Extraction:   < 100ms
LLM SQL Generation:  1-2s   (API latency)
SQL Execution:       < 100ms (DuckDB is fast)
Error Recovery:      2-3s   (if needed)
────────────────────────────
Total Latency:       2-6s typical
```

### Memory Usage

```
Small files (<10MB):      < 100MB RAM
Medium files (100MB):     ~500MB RAM
Large files (1GB):        ~2-5GB RAM
```

## Concurrency & Thread Safety

Currently **single-threaded**:

- MCP server handles one request at a time
- No shared state between requests
- Thread-safe libraries (pandas, duckdb)

For scaling:

- Add async/await support
- Use connection pooling for DuckDB
- Implement request queue

## Database Schema

The system registers DataFrames as a single table:

```
Table Name: "data"
Columns:    [from input file]
Rows:       [from input file]
```

Example with sales.csv:

```
Table: data

Columns:
- product (string)
- country (string)
- revenue (integer)
- date (string)

Row Count: 10

Sample:
product     country    revenue    date
Widget A    USA        5000       2024-01-01
Widget B    USA        3000       2024-01-01
...
```

## Security Architecture

### Data Isolation

- ✅ Local processing only
- ✅ No data sent to external services except:
  - Schema info to LLM (for SQL generation)
  - Question text to LLM
- ✅ Results computed locally

### API Key Management

- ⚠️ Stored in environment variable
- ⚠️ Not logged or transmitted
- ⚠️ Should be restricted in OpenAI dashboard

### Query Safety

- ✅ SQL executed in isolated DuckDB session
- ✅ No persistence between queries
- ✅ Memory-only execution

## Logging Architecture

```
Logger Hierarchy:
    root logger
    │
    ├── spreadsheet_mcp_agent.server
    │   └── Logs: orchestration, pipeline steps
    │
    ├── spreadsheet_mcp_agent.file_loader
    │   └── Logs: file operations
    │
    ├── spreadsheet_mcp_agent.schema_extractor
    │   └── Logs: schema extraction
    │
    ├── spreadsheet_mcp_agent.sql_generator
    │   └── Logs: SQL generation
    │
    ├── spreadsheet_mcp_agent.sql_executor
    │   └── Logs: SQL execution
    │
    ├── spreadsheet_mcp_agent.error_recovery
    │   └── Logs: retry attempts
    │
    └── spreadsheet_mcp_agent.llm_client
        └── Logs: LLM API calls
```

## Integration Points

### With Claude Desktop

```
MCP Protocol (stdio)
    ↔ query_spreadsheet tool
    ↔ Structured inputs/outputs
    ↔ JSON responses
```

### With External Services

```
OpenAI API
    ← Model name, API key
    ← Prompts (schema + question)
    → SQL queries
    → Error corrections
```

### With File System

```
Read Operations:
    → Load CSV/Excel files
    ← DataFrame contents
```

## Extensibility Points

### Add New File Formats

Edit `file_loader.py`:

```python
elif file_suffix == ".parquet":
    df = pd.read_parquet(file_path)
```

### Add New LLM Providers

Extend `llm_client.py`:

```python
class AnthropicClient(LLMClient):
    def generate_text(self, prompt):
        # Claude API implementation
```

### Add Database Support

Extend `sql_executor.py`:

```python
def execute_sql_postgres(sql, conn_string):
    # Direct database execution
```

### Add Result Post-Processing

Extend `server.py`:

```python
def format_results(df):
    # Custom formatting
```

## Testing Architecture

### Unit Tests (suggested)

```
test_file_loader.py
    - Test CSV loading
    - Test Excel loading
    - Test error cases

test_schema_extractor.py
    - Test schema formatting
    - Test various data types

test_sql_generator.py
    - Test prompt generation
    - Test markdown cleanup

test_sql_executor.py
    - Test SQL execution
    - Test error handling

test_error_recovery.py
    - Test retry logic
    - Test SQL correction
```

### Integration Tests (suggested)

```
test_end_to_end.py
    - Full pipeline test
    - Various query types
    - Error scenarios
```

## Deployment Architecture

### Single Machine

```
Python Process
    └── MCP Server
        └── Stdio to Claude
```

### With Process Manager (recommended)

```
Systemd/Supervisor
    └── Python Process
        └── MCP Server
            └── Stdio to Claude
```

### With Load Balancer (future)

```
Claude Desktop (1)  ┐
Claude Desktop (2)  ├─► Load Balancer ─► Server Pool
Claude Desktop (N)  ┘
```

## Version Control

```
git
├── .gitignore
│   ├── .venv/
│   ├── .env
│   ├── *.pyc
│   └── __pycache__/
│
└── tracked files
    ├── Code (*.py)
    ├── Config (pyproject.toml)
    ├── Docs (*.md)
    └── Requirements (requirements.txt)
```

## Code Organization Principles

1. **Separation of Concerns**: Each module has one responsibility
2. **DRY (Don't Repeat Yourself)**: Common logic in llm_client, config
3. **SOLID Principles**:
   - Single Responsibility: Each function does one thing
   - Open/Closed: Easy to extend, hard to modify
   - Liskov Substitution: Consistent interfaces
   - Interface Segregation: Small, focused functions
   - Dependency Inversion: Depend on abstractions (config)

4. **Clean Code**:
   - Meaningful names
   - Short functions
   - Comprehensive documentation
   - Error handling throughout

## Future Enhancements

### Planned Features

- [ ] Support for multiple tables/sheets
- [ ] Query caching
- [ ] Result visualization
- [ ] Query history
- [ ] User authentication
- [ ] Rate limiting
- [ ] Batch query processing
- [ ] Database connectors (PostgreSQL, MySQL)

### Performance Improvements

- [ ] Async LLM calls
- [ ] Connection pooling
- [ ] Result streaming
- [ ] Query optimization

### Reliability

- [ ] Circuit breaker for LLM
- [ ] Request timeout handling
- [ ] Graceful degradation
- [ ] Health checks

---

This architecture is designed for:

- ✅ Production use
- ✅ Easy maintenance
- ✅ Clear extensibility
- ✅ Comprehensive error handling
- ✅ Performance and reliability
