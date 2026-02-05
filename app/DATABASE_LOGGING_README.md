# Streamlit App - Database Logging Guide

**Location:** `app/agent_app.py`
**Last Updated:** 2026-02-05

## Overview

The SQL AI Agent Streamlit app now supports **database logging** in addition to file-based logging. You can store all agent logs directly in PostgreSQL or DuckDB for easy querying and analysis.

## New Features

### 1. Database Logging Support

- **File Logging**: Traditional JSON log files (existing feature)
- **Database Logging**: NEW - Store logs in PostgreSQL or DuckDB
- **Automatic Schema Initialization**: One-click setup for log tables
- **Live Log Viewer**: Query and view logs directly from database
- **Log Statistics**: Real-time metrics and analytics

### 2. Flexible Configuration

- Choose logging destination (File or Database)
- Select log database (PostgreSQL or DuckDB)
- Initialize schema with single button click
- View log statistics in sidebar

## Quick Start

### Step 1: Launch the App

```bash
cd app/
streamlit run agent_app.py
```

### Step 2: Enable Database Logging

1. In the sidebar, navigate to **"Logging Settings"**
2. Check **"Enable Logging"**
3. Select **"Database"** as the log destination
4. Choose log database: **PostgreSQL** or **DuckDB**

### Step 3: Initialize Log Schema

Click the **"🔧 Initialize Log Schema"** button

This will:
- Create the `sql_agent_logs` table
- Set up indexes (PostgreSQL: 6 indexes)
- Verify table creation
- Show current log count

### Step 4: Start Using the Agent

Ask questions and all activity will be logged to the database!

## Database Logging Options

### Option 1: PostgreSQL Logging

**When to use:**
- Production environment
- Shared logging across multiple sessions
- Need concurrent write access
- Integration with existing PostgreSQL infrastructure

**Configuration:**
- Database: PostgreSQL (same server as data)
- Table: `public.sql_agent_logs`
- Indexes: 6 optimized indexes
- Schema: Auto-created with `init_postgres_log_schema()`

**Connection:**
```python
# App automatically connects to:
host: postgres
port: 5432
database: my_db
user: postgres
```

### Option 2: DuckDB Logging

**When to use:**
- Development and testing
- Single-user sessions
- Portable log storage
- Fast analytical queries on logs

**Configuration:**
- Database: DuckDB (persistent file)
- File location: `logs/sql_agent_logs.duckdb`
- Schema: Auto-created with `init_duckdb_log_schema()`

## Log Schema

Both PostgreSQL and DuckDB use the same schema:

```sql
CREATE TABLE sql_agent_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    level VARCHAR(10) NOT NULL,
    logger VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    session_id VARCHAR(36),
    operation_type VARCHAR(50),
    extra_fields JSONB/JSON,  -- JSONB for PostgreSQL, JSON for DuckDB
    exception TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Logged Fields

| Field | Description | Example |
|-------|-------------|---------|
| `timestamp` | When log was created | 2024-02-05 14:30:45 |
| `level` | Log level | INFO, DEBUG, WARNING, ERROR |
| `logger` | Logger name | sql_ai_agent |
| `message` | Log message | "Query executed successfully" |
| `session_id` | Unique session ID | abc-123-def-456 |
| `operation_type` | Operation category | query_result, llm_invocation |
| `extra_fields` | Additional metadata (JSON) | {"model": "gpt-4o", "tokens": 1250} |
| `exception` | Exception details if error | Full stack trace |

### Extra Fields (JSON)

The `extra_fields` column contains rich metadata:

**For LLM Invocations:**
```json
{
  "model_name": "gpt-4o",
  "estimated_prompt_tokens": 1245,
  "total_prompt_chars": 4980,
  "agent_config": {
    "model": "gpt-4o",
    "read_only": true,
    "memory_enabled": true,
    "memory_size": 10
  }
}
```

**For Query Results:**
```json
{
  "query": "SELECT COUNT(*) FROM employees",
  "success": true,
  "rows_returned": 1,
  "validation": true
}
```

## Viewing Logs in the App

### In-App Log Viewer

The app includes a built-in log viewer:

1. Enable logging (File or Database)
2. Expand **"📊 View Agent Logs"** section
3. Adjust number of entries to display
4. Click **"🔄 Refresh Logs"** to update

**File Logging Features:**
- View JSON-formatted logs
- Show full details toggle
- Download logs as JSON

**Database Logging Features:**
- Real-time query from database
- Formatted display with colors by log level
- Download logs as CSV
- Log statistics dashboard

### Log Statistics (Database Only)

When using database logging, you'll see:
- **Total Logs**: Count of all log entries
- **Errors**: Number of ERROR level logs
- **Operations**: Count of unique operation types

## Querying Logs Directly

### PostgreSQL Queries

```sql
-- Recent logs
SELECT * FROM sql_agent_logs
ORDER BY timestamp DESC
LIMIT 10;

-- LLM invocations with token usage
SELECT
    timestamp,
    message,
    extra_fields->>'model_name' as model,
    (extra_fields->>'estimated_prompt_tokens')::int as tokens
FROM sql_agent_logs
WHERE operation_type = 'llm_invocation'
ORDER BY timestamp DESC;

-- Error summary
SELECT
    DATE(timestamp) as date,
    COUNT(*) as error_count
FROM sql_agent_logs
WHERE level = 'ERROR'
GROUP BY DATE(timestamp)
ORDER BY date DESC;

-- Average tokens by model
SELECT
    extra_fields->>'model_name' as model,
    AVG((extra_fields->>'estimated_prompt_tokens')::int) as avg_tokens,
    COUNT(*) as invocations
FROM sql_agent_logs
WHERE operation_type = 'llm_invocation'
GROUP BY extra_fields->>'model_name';
```

### DuckDB Queries

```sql
-- Recent logs
SELECT * FROM sql_agent_logs
ORDER BY timestamp DESC
LIMIT 10;

-- LLM invocations with token usage
SELECT
    timestamp,
    message,
    json_extract(extra_fields, '$.model_name') as model,
    json_extract(extra_fields, '$.estimated_prompt_tokens') as tokens
FROM sql_agent_logs
WHERE operation_type = 'llm_invocation'
ORDER BY timestamp DESC;

-- Operations by type
SELECT
    operation_type,
    COUNT(*) as count
FROM sql_agent_logs
WHERE operation_type IS NOT NULL
GROUP BY operation_type
ORDER BY count DESC;
```

## Resetting Logs

### Using the Reset Script

We've provided a utility script to clear logs:

```bash
# Run the reset script
python scripts/reset_logs.py
```

**Options:**
1. File logs only - Delete log files in `logs/` directory
2. PostgreSQL logs only - Truncate `sql_agent_logs` table
3. DuckDB logs only - Truncate table or delete database file
4. All logs - Clear everything

### Manual Reset

**PostgreSQL:**
```sql
TRUNCATE TABLE sql_agent_logs RESTART IDENTITY CASCADE;
```

**DuckDB:**
```sql
DELETE FROM sql_agent_logs;
```

Or delete the file:
```bash
rm logs/sql_agent_logs.duckdb
```

**File logs:**
```bash
rm logs/*.log logs/*.json
```

## Workflow Example

### Complete Workflow: Initialize and Use Database Logging

1. **Start the app:**
   ```bash
   streamlit run app/agent_app.py
   ```

2. **Configure logging:**
   - Sidebar → Logging Settings
   - Enable Logging: ✅
   - Log Destination: Database
   - Log Database: PostgreSQL

3. **Initialize schema:**
   - Click "🔧 Initialize Log Schema"
   - Wait for success message
   - Verify table exists (shows 0 logs initially)

4. **Use the agent:**
   - Ask: "How many rows are in the air traffic dataset?"
   - Agent processes query
   - Logs written to database automatically

5. **View logs:**
   - Expand "📊 View Agent Logs"
   - See logs with operation types
   - View statistics
   - Download as CSV

6. **Query logs externally:**
   ```bash
   psql -h postgres -U postgres -d my_db
   SELECT COUNT(*) FROM sql_agent_logs;
   ```

7. **Reset when needed:**
   ```bash
   python scripts/reset_logs.py
   # Select option 2 (PostgreSQL logs only)
   ```

## Troubleshooting

### Issue: "Log table not initialized"

**Solution:**
Click the "🔧 Initialize Log Schema" button in the Logging Settings

### Issue: "Failed to connect to log database"

**PostgreSQL Solution:**
- Ensure PostgreSQL container is running
- Check connection settings in app
- Verify database exists

**DuckDB Solution:**
- Check file permissions in `logs/` directory
- Ensure directory exists: `mkdir -p logs`

### Issue: No logs appearing in viewer

**Solution:**
1. Verify logging is enabled
2. Check log level (DEBUG shows all logs)
3. Click "🔄 Refresh Logs"
4. Ensure log table was initialized

### Issue: "Permission denied" on PostgreSQL

**Solution:**
```sql
-- Grant permissions
GRANT ALL ON TABLE sql_agent_logs TO postgres;
GRANT USAGE, SELECT ON SEQUENCE sql_agent_logs_id_seq TO postgres;
```

## Performance Considerations

### PostgreSQL
- **Indexes**: 6 indexes created automatically for fast queries
- **Maintenance**: Run `VACUUM ANALYZE sql_agent_logs` periodically
- **Archival**: Archive old logs monthly to reduce table size

### DuckDB
- **File growth**: Database file grows with logs
- **Compaction**: Periodically delete and recreate for smaller file size
- **Analytics**: Excellent for analytical queries on logs

## Migration from File Logging

### Converting Existing File Logs to Database

```bash
# 1. Initialize database schema
# (Use the app's "Initialize Log Schema" button)

# 2. Convert JSON logs to CSV
python examples/json_logs_to_csv.py \
    --input logs/sql_agent_streamlit.log \
    --output logs/converted_logs.csv

# 3. Load into database (PostgreSQL)
psql -h postgres -U postgres -d my_db -c "\COPY sql_agent_logs(timestamp, level, logger, message, session_id, operation_type, extra_fields, exception) FROM 'logs/converted_logs.csv' WITH CSV HEADER;"

# Or load into DuckDB
duckdb logs/sql_agent_logs.duckdb \
    "COPY sql_agent_logs FROM 'logs/converted_logs.csv' (HEADER);"
```

## Best Practices

### 1. Choose the Right Database

**Use PostgreSQL when:**
- Running in production
- Multiple users/sessions
- Need concurrent access
- Integration with existing PostgreSQL setup

**Use DuckDB when:**
- Development/testing
- Single user
- Need portability
- Analytical query focus

### 2. Log Level Configuration

**Production:**
- Use `INFO` level to reduce volume
- Focus on important operations

**Development:**
- Use `DEBUG` level for detailed insight
- See all LLM interactions

### 3. Regular Maintenance

**PostgreSQL:**
```sql
-- Weekly: Analyze table
VACUUM ANALYZE sql_agent_logs;

-- Monthly: Archive old logs
DELETE FROM sql_agent_logs
WHERE timestamp < NOW() - INTERVAL '30 days';
```

**DuckDB:**
```bash
# Monthly: Compact database
python scripts/compact_duckdb_logs.py
```

### 4. Monitoring

Set up alerts for:
- High error rates
- Unusual token usage
- Failed queries

## Related Documentation

- **Database Logging Guide**: `docs/DATABASE_LOGGING.md`
- **Enhanced LLM Logging**: `docs/ENHANCED_LLM_LOGGING.md`
- **Example Notebooks**: `examples/database_logging_setup.ipynb`
- **Reset Script**: `scripts/reset_logs.py`

---

**Enjoy powerful database logging with your SQL AI Agent! 🎉**
