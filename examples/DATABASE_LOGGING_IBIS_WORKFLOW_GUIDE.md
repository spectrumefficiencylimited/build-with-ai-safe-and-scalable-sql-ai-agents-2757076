# Database Logging with Ibis Workflow - Jupyter Notebook Guide

**Location:** `examples/database_logging_ibis_workflow.ipynb`

## Overview

A Jupyter notebook demonstrating database logging setup using the `get_ibis_connection()` utility from `sql_ai_agent/data.py`. This notebook shows a unified workflow for both PostgreSQL and DuckDB, following the same pattern as `chapter_1/01_02.ipynb`.

## What's Different from database_logging_setup.ipynb?

| Feature | database_logging_setup.ipynb | database_logging_ibis_workflow.ipynb (this) |
|---------|------------------------------|---------------------------------------------|
| **Connection Method** | Direct `ibis.postgres.connect()` / `ibis.duckdb.connect()` | Uses `get_ibis_connection()` for DuckDB |
| **DuckDB Data Source** | In-memory table creation | CSV file loaded via `get_ibis_connection()` |
| **Workflow** | Independent PostgreSQL and DuckDB examples | PostgreSQL → CSV export → DuckDB import |
| **Helper Functions** | None | `json_logs_to_csv()` for JSON-to-CSV conversion |
| **Flow Pattern** | Tutorial style | Follows `chapter_1/01_02.ipynb` pattern |

## What's Included

### Helper Function
- **`json_logs_to_csv()`** - Convert JSON log files to CSV format for DuckDB ingestion

### PostgreSQL Workflow (7 Steps)

1. **Configure Connection** - Set PostgreSQL connection parameters
2. **Connect to PostgreSQL** - Establish database connection
3. **Initialize Schema** - Create log table with 6 indexes
4. **Verify Table** - Check table creation and statistics
5. **Set Up Logging Handler** - Configure database logging
6. **Generate Sample Logs** - Write test logs to database
7. **Query Logs** - View and export logs using SQL

### DuckDB Workflow (6 Steps)

1. **Load Logs via get_ibis_connection()** - Import CSV into DuckDB
2. **Verify Table** - Check schema and row count
3. **Query Logs** - View logs using SQL
4. **Query by Operation Type** - Analyze log distribution
5. **Extract JSON Fields** - Query extra_fields data
6. **Set Up Live Logging** (Optional) - Configure persistent DuckDB logging

## Key Features

### 1. JSON to CSV Conversion

```python
def json_logs_to_csv(json_file_path: str, csv_file_path: str) -> pd.DataFrame:
    """
    Convert JSON log file to CSV format for DuckDB ingestion.

    - Reads newline-delimited JSON log files
    - Converts to DataFrame with database schema
    - Handles extra_fields as JSON string
    - Saves to CSV for DuckDB loading
    """
```

**Usage:**
```python
logs_df = json_logs_to_csv(
    json_file_path='logs/agent.log',
    csv_file_path='logs/agent_logs.csv'
)
```

### 2. PostgreSQL to CSV Export

```python
# Export logs from PostgreSQL to CSV
export_query = """
SELECT
    timestamp,
    level,
    logger,
    message,
    session_id,
    operation_type,
    extra_fields::text as extra_fields,
    exception
FROM sql_agent_logs
ORDER BY timestamp DESC;
"""

logs_df = con_postgres.raw_sql(export_query).to_pandas()
logs_df.to_csv('logs/agent_logs.csv', index=False)
```

### 3. DuckDB Loading via get_ibis_connection()

```python
# Load CSV into DuckDB
con_duckdb = get_ibis_connection(
    backend="duckdb",
    tbl_name="sql_agent_logs",
    duckdb_csv_path="logs/agent_logs.csv"
)
```

### 4. Persistent DuckDB Logging

```python
# Create persistent DuckDB database
con_duckdb_persistent = ibis.duckdb.connect('logs/agent_logs.duckdb')

# Initialize schema
init_duckdb_log_schema(
    con=con_duckdb_persistent,
    table_name="sql_agent_logs"
)

# Set up live logging
db_handler = DatabaseLogHandler(
    con=con_duckdb_persistent,
    table_name="sql_agent_logs",
    db_type="duckdb"
)
```

## Workflow Pattern (Following chapter_1/01_02.ipynb)

### 1. Introduction Markdown
- Clear explanation of what will be demonstrated
- List of steps

### 2. Setup and Imports
- Import required libraries
- Add project to path

### 3. Helper Functions
- Define utility functions needed

### 4. PostgreSQL Workflow
- Step-by-step PostgreSQL setup
- Similar to original air traffic data workflow
- Export data to CSV at the end

### 5. DuckDB Workflow
- Load CSV using `get_ibis_connection()`
- Query and analyze data
- Optional: Set up persistent logging

### 6. Summary
- Recap what was covered
- Next steps

## Use Cases

### Use Case 1: Development with DuckDB, Production with PostgreSQL

**Development:**
```python
# Use DuckDB for local development
con = get_ibis_connection(
    backend="duckdb",
    tbl_name="sql_agent_logs",
    duckdb_csv_path="logs/dev_logs.csv"
)
```

**Production:**
```python
# Use PostgreSQL for production
con = ibis.postgres.connect(**postgres_config)
init_postgres_log_schema(con, "sql_agent_logs")
```

### Use Case 2: Log Analysis Pipeline

```python
# Step 1: Export from PostgreSQL
logs_df = con_postgres.raw_sql("SELECT * FROM sql_agent_logs").to_pandas()
logs_df.to_csv('logs/analysis_export.csv')

# Step 2: Analyze in DuckDB (faster analytical queries)
con_analysis = get_ibis_connection(
    backend="duckdb",
    tbl_name="sql_agent_logs",
    duckdb_csv_path="logs/analysis_export.csv"
)

# Step 3: Run complex analytical queries
results = con_analysis.con.execute("""
    SELECT
        DATE_TRUNC('hour', timestamp) as hour,
        operation_type,
        COUNT(*) as count,
        AVG(CAST(json_extract(extra_fields, '$.estimated_prompt_tokens') AS INTEGER)) as avg_tokens
    FROM sql_agent_logs
    GROUP BY hour, operation_type
    ORDER BY hour DESC
""").df()
```

### Use Case 3: Portable Log Archive

```python
# Create portable DuckDB archive
con_archive = ibis.duckdb.connect('logs/archive_2024_q1.duckdb')
init_duckdb_log_schema(con_archive, "sql_agent_logs")

# Import historical logs
con_archive.con.execute("""
    COPY sql_agent_logs FROM 'logs/historical_logs.csv' (HEADER, DELIMITER ',')
""")
```

## Prerequisites

```bash
# Install required packages
pip install ibis-framework[postgres,duckdb] pandas

# For PostgreSQL: Ensure server is running
# For DuckDB: No server needed
```

## Configuration

### PostgreSQL Settings

```python
postgres_config = {
    'user': 'postgres',
    'password': 'password',
    'host': 'localhost',
    'port': 5432,
    'database': 'my_db',
}
```

### File Paths

```python
# Log files location
log_dir = '../logs'
csv_path = '../logs/agent_logs.csv'
duckdb_file = '../logs/agent_logs.duckdb'
```

## Sample Queries

### Query 1: Recent Logs (Both Databases)

**PostgreSQL:**
```sql
SELECT
    timestamp,
    level,
    message,
    operation_type
FROM sql_agent_logs
ORDER BY timestamp DESC
LIMIT 10;
```

**DuckDB:**
```sql
-- Same query works in DuckDB!
SELECT
    timestamp,
    level,
    message,
    operation_type
FROM sql_agent_logs
ORDER BY timestamp DESC
LIMIT 10;
```

### Query 2: Operation Type Distribution

```sql
SELECT
    operation_type,
    COUNT(*) as count
FROM sql_agent_logs
WHERE operation_type IS NOT NULL
GROUP BY operation_type
ORDER BY count DESC;
```

### Query 3: Extract JSON Fields (DuckDB)

```sql
SELECT
    timestamp,
    message,
    json_extract(extra_fields, '$.model_name') as model,
    json_extract(extra_fields, '$.estimated_prompt_tokens') as tokens
FROM sql_agent_logs
WHERE extra_fields IS NOT NULL
ORDER BY timestamp DESC;
```

### Query 4: Extract JSON Fields (PostgreSQL)

```sql
SELECT
    timestamp,
    message,
    extra_fields->>'model_name' as model,
    (extra_fields->>'estimated_prompt_tokens')::int as tokens
FROM sql_agent_logs
WHERE extra_fields IS NOT NULL
ORDER BY timestamp DESC;
```

## Troubleshooting

### Issue: CSV file not found

**Solution:**
```python
# Ensure log directory exists
os.makedirs('logs', exist_ok=True)

# Check file path
import os
if not os.path.exists(csv_path):
    print(f"File not found: {csv_path}")
    # Create sample CSV or export from PostgreSQL
```

### Issue: get_ibis_connection() error

**Solution:**
```python
# Verify function signature
from sql_ai_agent.data import get_ibis_connection

# For DuckDB, must provide both parameters
con = get_ibis_connection(
    backend="duckdb",
    tbl_name="sql_agent_logs",  # Required
    duckdb_csv_path="logs/agent_logs.csv"  # Required
)
```

### Issue: JSON fields showing as strings in DuckDB

**Solution:**
```sql
-- DuckDB requires explicit JSON parsing
SELECT
    json_extract(extra_fields, '$.field_name')
FROM sql_agent_logs;

-- PostgreSQL uses JSONB operators
SELECT
    extra_fields->>'field_name'
FROM sql_agent_logs;
```

### Issue: Empty CSV or no logs

**Solution:**
```python
# Generate sample logs first
from sql_ai_agent.logger import SQLAgentLogger

logger = setup_logging(log_file='logs/agent.log')
agent_logger = SQLAgentLogger(logger, extra={'session_id': 'test'})
agent_logger.info("Test log", extra={'operation_type': 'test'})

# Then convert to CSV
logs_df = json_logs_to_csv('logs/agent.log', 'logs/agent_logs.csv')
```

## Comparison: This Notebook vs database_logging_setup.ipynb

### When to Use database_logging_setup.ipynb
- **Learning**: New to database logging
- **Complete setup**: Need full PostgreSQL + DuckDB setup from scratch
- **Independent databases**: Want separate examples
- **Tutorial style**: Prefer step-by-step explanations

### When to Use database_logging_ibis_workflow.ipynb (This Notebook)
- **Data transfer**: Need to move logs from PostgreSQL to DuckDB
- **Analysis workflow**: PostgreSQL for logging, DuckDB for analytics
- **CSV integration**: Working with CSV log exports
- **Production pattern**: Following established connection patterns
- **Consistent with course**: Following `chapter_1/01_02.ipynb` style

## Best Practices

### 1. PostgreSQL for Production Logging

```python
# Use PostgreSQL for live logging in production
con_postgres = ibis.postgres.connect(**postgres_config)
init_postgres_log_schema(con_postgres, "sql_agent_logs")

db_handler = DatabaseLogHandler(
    con=con_postgres,
    table_name="sql_agent_logs",
    db_type="postgres",
    level=logging.INFO  # INFO level for production
)
```

### 2. DuckDB for Log Analysis

```python
# Export logs to CSV periodically
logs_df = con_postgres.raw_sql("SELECT * FROM sql_agent_logs WHERE timestamp > NOW() - INTERVAL '7 days'").to_pandas()
logs_df.to_csv('logs/weekly_logs.csv')

# Analyze in DuckDB (faster for aggregations)
con_analysis = get_ibis_connection(
    backend="duckdb",
    tbl_name="sql_agent_logs",
    duckdb_csv_path="logs/weekly_logs.csv"
)
```

### 3. Incremental CSV Updates

```python
# Export only new logs
last_export = "2024-02-01 00:00:00"
query = f"""
SELECT * FROM sql_agent_logs
WHERE timestamp > '{last_export}'
ORDER BY timestamp
"""

new_logs = con_postgres.raw_sql(query).to_pandas()

# Append to existing CSV
new_logs.to_csv('logs/agent_logs.csv', mode='a', header=False, index=False)
```

### 4. Automated Log Archival

```python
# Monthly archival to DuckDB
import datetime

month = datetime.datetime.now().strftime('%Y_%m')
archive_file = f'logs/archive_{month}.duckdb'

con_archive = ibis.duckdb.connect(archive_file)
init_duckdb_log_schema(con_archive, "sql_agent_logs")

# Load current month's logs
# ... (export and load logic)
```

## Performance Tips

### PostgreSQL
- Use indexes for timestamp, level, session_id, operation_type
- Run `VACUUM ANALYZE sql_agent_logs` periodically
- Archive old logs to reduce table size

### DuckDB
- Load only necessary columns from CSV
- Use columnar storage advantage for analytical queries
- Partition large CSV files by date for faster loading

### CSV Export
- Export incrementally instead of full table
- Use date range filters
- Compress CSV files for storage

## Next Steps

1. **Run the Notebook**
   ```bash
   jupyter notebook examples/database_logging_ibis_workflow.ipynb
   ```

2. **Customize for Your Needs**
   - Modify PostgreSQL connection settings
   - Adjust CSV export paths
   - Add custom queries

3. **Integrate with SqlAgent**
   - Use logging setups in your agent
   - Monitor logs in production
   - Analyze performance metrics

4. **Build Analytics Pipeline**
   - Regular exports from PostgreSQL
   - Analytical queries in DuckDB
   - Visualization dashboards

## Related Documentation

- 📘 **Complete Guide:** `docs/DATABASE_LOGGING.md`
- 📄 **Python Examples:** `examples/database_logging_examples.py`
- 📓 **Alternative Notebook:** `examples/database_logging_setup.ipynb`
- 🔧 **Source Code:** `sql_ai_agent/log_database.py`
- 📚 **Reference Pattern:** `chapter_1/01_02.ipynb`

## File Structure

```
build-with-ai-safe-and-scalable-sql-ai-agents-2757076/
├── examples/
│   ├── database_logging_ibis_workflow.ipynb  ← This notebook
│   ├── DATABASE_LOGGING_IBIS_WORKFLOW_GUIDE.md  ← This guide
│   ├── database_logging_setup.ipynb  ← Alternative notebook
│   └── database_logging_examples.py  ← Python examples
├── sql_ai_agent/
│   ├── data.py  ← Contains get_ibis_connection()
│   └── log_database.py  ← Logging utilities
└── logs/  ← Created by notebook
    ├── agent_logs.csv
    └── agent_logs.duckdb
```

---

**Created:** 2026-02-05
**Last Updated:** 2026-02-05
**Status:** ✅ Ready to Use
**Pattern:** Follows `chapter_1/01_02.ipynb` workflow
