[← Back to Contents](../README.md#documentation)

# Architecture & Design

## High-Level Overview

```
┌───────────────────────────────────────────────────────────────┐
│                      Claude Desktop                           │
└────────────────────────┬──────────────────────────────────────┘
                         │  file_path + question (MCP stdio)
                         ▼
┌───────────────────────────────────────────────────────────────┐
│              MCP Server  (server.py / FastMCP)                │
│         query_spreadsheet(file_path, question) → JSON         │
└────────────────────────┬──────────────────────────────────────┘
                         │
                         ▼
┌───────────────────────────────────────────────────────────────┐
│           SpreadsheetQueryFacade  (facade.py)                 │
│   Facade pattern — single execute() entry point               │
│   Generates run_id, tracks timing, notifies observers         │
│                                                               │
│  ┌──────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │FileLoader    │  │ SchemaExtractor  │  │  SqlGenerator   │  │
│  │Context       │  │ (schema_extrac- │  │  (sql_genera-   │  │
│  │(loaders.py)  │  │  tor.py)        │  │   tor.py)       │  │
│  │Strategy      │  └─────────────────┘  │  uses Provider  │  │
│  └──────┬───────┘                       └────────┬────────┘  │
│         │                                        │            │
│  ┌──────▼───────────────────────────────────────▼──────────┐  │
│  │         retry_with_recovery()  (handlers.py)            │  │
│  │         Chain of Responsibility:                        │  │
│  │         ExecuteHandler → DecompositionHandler →         │  │
│  │                          ExhaustedHandler               │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
                         │  PipelineEvent at each stage
                         ▼
┌───────────────────────────────────────────────────────────────┐
│                     Observers  (events.py)                    │
│  LoggingObserver  │  JsonlObserver  │  SqliteObserver         │
│  (Python logger)  │  (~/.mcpflux/  │  (~/.mcpflux/           │
│                   │  events.jsonl) │   metrics.db)            │
└───────────────────────────────────────────────────────────────┘
                         │  (optional)
                         ▼
┌───────────────────────────────────────────────────────────────┐
│               LangSmith  (via env vars)                       │
│   Auto-traces every LangChain call: tokens, latency, retries  │
└───────────────────────────────────────────────────────────────┘
```

---

## Design Patterns

### Facade (`facade.py`)
`SpreadsheetQueryFacade.execute()` is the single entry point that hides the 5-step pipeline from callers. Each step is a private method. The facade also:
- Generates a `run_id` (UUID4) for each run
- Tracks wall-clock timing
- Injects `run_id` and `latency_ms` into all emitted events
- Emits an `ERROR` stage event on any unhandled exception

### Observer (`events.py`)
`PipelineObserver` (ABC) with `on_event(PipelineEvent)`. Concrete implementations:
- `LoggingObserver` — logs to Python logger
- `JsonlObserver` — appends one JSON line per event to a `.jsonl` file, immediately flushed
- `SqliteObserver` — accumulates events per run_id, writes one row to SQLite on COMPLETE/ERROR
- `MetricsObserver` — placeholder for push-based sinks (Prometheus, Datadog)

### Strategy — File Loading (`loaders.py`)
`FileLoaderContext` selects `CsvLoaderStrategy` or `ExcelLoaderStrategy` based on file extension. Add new formats by implementing `FileLoaderStrategy`.

### Strategy — LLM Providers (`providers.py`)
`LLMProvider` (ABC) with `generate()` and `get_runnable()`. Concrete implementations:
- `AnthropicProvider` (default) — Claude via `langchain-anthropic`
- `OpenAIProvider` — GPT via `langchain-openai`
- `GoogleProvider` — Gemini via `langchain-google-genai` (placeholder)

Selected by `LLM_PROVIDER` env var via `get_provider()` factory.

### Chain of Responsibility (`handlers.py`)
SQL execution uses a proactive try-first-then-decompose strategy through a handler chain carried by `SqlContext`:
1. `ExecuteHandler` — tries the direct SQL query; marks `ctx.success = True` if OK
2. `DecompositionHandler` — on any failure, calls the LLM to decompose the question into sequential SQL steps (`query_decomposer.py`); executes each step, materialising intermediate results as named tables; sets `ctx.was_decomposed = True` on success
3. `ExhaustedHandler` — terminal handler, raises after both direct and decomposed execution fail

---

## Module Dependencies

```
server.py
  └── facade.py
        ├── events.py         (PipelineStage, PipelineEvent, all observers)
        ├── loaders.py        (FileLoaderContext, strategies)
        ├── schema_extractor.py
        ├── sql_generator.py
        │     └── providers.py  (LLMProvider, get_provider)
        │           └── langchain-anthropic / langchain-openai
        ├── handlers.py       (retry_with_recovery, handler chain)
        │     └── sql_executor.py  (DuckDB)
        └── config.py

config.py  (imported by most modules)
```

---

## Data Flow

```
Input: file_path, question
  │
  ├─ [START event] run_id, file, question, provider, model
  │
  ├─ FileLoaderContext ──────────────────► pandas.DataFrame
  │   [FILE_LOADED event] shape
  │
  ├─ SchemaExtractor ────────────────────► Schema String
  │   [SCHEMA_EXTRACTED event] schema_length   (columns, types, samples)
  │
  ├─ SqlGenerator ───────────────────────► SQL String
  │   [SQL_GENERATED event] sql (truncated)
  │
  ├─ retry_with_recovery()
  │   ├─ ExecuteHandler: try direct SQL query
  │   │   ├─ Success ──────────────────► result DataFrame
  │   │   │   [SQL_EXECUTED event] row_count, sql_was_decomposed=False
  │   │   └─ Failure (any error)
  │   │         ▼
  │   │       DecompositionHandler (LLM breaks question into steps)
  │   │         [SQL_DECOMPOSED event] original_sql, final_sql
  │   │         ├─ Execute step 1 → intermediate DataFrame (added to context)
  │   │         ├─ Execute step 2 → intermediate DataFrame (added to context)
  │   │         └─ ... → final result DataFrame
  │   │             [SQL_EXECUTED event] row_count, sql_was_decomposed=True
  │   └─ ExhaustedHandler → raises
  │
  ├─ [COMPLETE event] row_count, latency_ms
  │   OR [ERROR event] error, error_type, latency_ms
  │
Output: {"success", "generated_sql", "result_preview", "row_count", "total_columns"}
```

---

## Observability Layer

The MCP server process is killed when Claude Desktop exits — all in-memory state is lost. Observability is therefore written to **persistent storage with immediate flush**.

### Event Stages

| Stage | Emitted When | Key Data |
|---|---|---|
| `start` | `execute()` begins | run_id, file, question, provider, model |
| `file_loaded` | File parsed into DataFrame | run_id, shape |
| `schema_extracted` | Schema string built | run_id, schema_length |
| `sql_generated` | LLM produced SQL | run_id, sql (truncated) |
| `sql_corrected` | SQL changed (legacy path) | run_id, original_sql, corrected_sql |
| `sql_decomposed` | DecompositionHandler ran | run_id, original_sql, final_sql |
| `sql_executed` | SQL ran successfully | run_id, row_count, attempt, sql_was_decomposed |
| `complete` | Pipeline finished | run_id, row_count, latency_ms |
| `error` | Unhandled exception | run_id, error, error_type, latency_ms |

### JSONL Log (`~/.mcpflux/events.jsonl`)
Line format:
```json
{"ts": "2026-03-14T01:20:00Z", "stage": "sql_corrected", "data": {"run_id": "...", "attempt": 2, "error": "...", "corrected_sql": "SELECT ..."}}
```
Query examples:
```bash
# All events for one run
cat ~/.mcpflux/events.jsonl | jq 'select(.data.run_id == "abc-123")'
# All correction events
cat ~/.mcpflux/events.jsonl | jq 'select(.stage == "sql_corrected")'
```

### SQLite Metrics (`~/.mcpflux/metrics.db`)
Schema:
```sql
CREATE TABLE pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT, ts TEXT, file_path TEXT, question TEXT,
    provider TEXT, model TEXT,
    success INTEGER,     -- 1 or 0
    attempts INTEGER,    -- which attempt succeeded
    corrections INTEGER, -- how many LLM SQL corrections
    latency_ms INTEGER,
    error TEXT           -- NULL on success
);
```
Query examples:
```sql
-- Success rate by provider
SELECT provider, AVG(success)*100 FROM pipeline_runs GROUP BY provider;
-- Average SQL corrections for successful runs
SELECT AVG(corrections) FROM pipeline_runs WHERE success=1;
-- Slowest queries
SELECT question, latency_ms FROM pipeline_runs ORDER BY latency_ms DESC LIMIT 10;
```

---

## Configuration Hierarchy

```
Defaults in config.py
    │
    └─ Environment Variables (override, loaded from .env via dotenv)
        ├─ ANTHROPIC_API_KEY      (required)
        ├─ LLM_PROVIDER           (default: "anthropic")
        ├─ MODEL_NAME             (default: "claude-haiku-4-5")
        ├─ OPENAI_API_KEY         (if using OpenAI provider)
        ├─ EVENTS_LOG_PATH        (default: ~/.mcpflux/events.jsonl)
        ├─ METRICS_DB_PATH        (default: ~/.mcpflux/metrics.db)
        ├─ LANGCHAIN_TRACING_V2   (optional LangSmith)
        ├─ LANGCHAIN_API_KEY      (optional LangSmith)
        ├─ LANGSMITH_PROJECT      (optional LangSmith)
        ├─ MAX_SQL_RETRIES        (default: 3)
        ├─ MAX_SAMPLE_ROWS        (default: 5)
        └─ MAX_RESULT_ROWS        (default: 100)
```

---

## State Management

Each `execute()` call is stateless from the caller's perspective:
- `run_id` is local to the call; observers use it for correlation
- No DataFrames cached between calls
- DuckDB connections are in-memory per execution
- `SqliteObserver` accumulates in-memory state within a run but flushes to disk on completion

---

## Error Handling

```
execute() try/except:
    ├─ File not found → FileNotFoundError → ERROR event + re-raise
    ├─ Unsupported format → ValueError → ERROR event + re-raise
    ├─ SQL generation failure → RuntimeError → ERROR event + re-raise
    └─ SQL exhausted → RuntimeError → ERROR event + re-raise

Each ERROR event includes: run_id, error message, error_type, latency_ms
The server.py handler catches all exceptions and returns JSON {"success": false, ...}
```

---

## LLM Integration Points

### 1. SQL Generation (`sql_generator.py` + `providers.py`)
```
Input:  schema + question
LLM:    Prompted to return only a SQL SELECT statement
Output: SQL string (markdown fences stripped)
```

### 2. Query Decomposition (`query_decomposer.py` — DecompositionHandler)
```
Input:  schema + question (when direct SQL failed)
LLM:    Prompted to return a JSON array of sequential SQL steps
Output: List of QueryStep(step_name, sql, description)
```
Each step is executed in order; its result DataFrame is added to the working DataContext under `step_name`, making it available as a table for subsequent steps.
Both use LangChain `PromptTemplate | LLM | StrOutputParser` chains, which are auto-traced by LangSmith when enabled.

---

## Extensibility Points

### Add a new file format
Implement `FileLoaderStrategy` in `loaders.py` and register in `FileLoaderContext`:
```python
class ParquetLoaderStrategy(FileLoaderStrategy):
    def load(self, path: str) -> pd.DataFrame:
        return pd.read_parquet(path)
```

### Add a new LLM provider
Implement `LLMProvider` in `providers.py` and add a case to `get_provider()`:
```python
class MistralProvider(LLMProvider):
    def get_runnable(self): ...
```

### Add a new observer
Implement `PipelineObserver` in `events.py` and register in `server.py`:
```python
class SlackAlertObserver(PipelineObserver):
    def on_event(self, event):
        if event.stage == PipelineStage.ERROR:
            send_slack(event.data["error"])
```

---

## Security

- Local processing only — data does not leave the machine except:
  - Schema info + question sent to LLM API for SQL generation
  - Events/metrics sent to LangSmith if tracing is enabled
- SQL execution is isolated in DuckDB in-memory session
- API keys stored in environment variables / `.env` (never logged)
- No persistence between queries (stateless DuckDB)

---

## Performance

| Stage | Typical Latency |
|---|---|
| File loading | < 1s (CSV), < 2s (Excel) |
| Schema extraction | < 100ms |
| LLM SQL generation | 0.5–2s |
| SQL execution (DuckDB) | < 100ms |
| LLM SQL correction (if needed) | +0.5–2s per attempt |
| Observer writes (JSONL + SQLite) | < 5ms per event |

---

## Future Enhancements

- [ ] Async LLM calls for lower latency
- [ ] Multi-sheet Excel support
- [ ] Query result caching
- [ ] Streaming result support
- [ ] Health check endpoint (HTTP mode)
- [ ] PostgreSQL / MySQL connector support
- [ ] Dashboard for SQLite metrics
