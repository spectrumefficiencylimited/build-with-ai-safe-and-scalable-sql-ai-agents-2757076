# Database Logging Setup - Jupyter Notebook Guide

**Location:** `examples/database_logging_setup.ipynb`

## Overview

A comprehensive Jupyter notebook demonstrating how to set up database logging for the SQL AI Agent with both **PostgreSQL** and **DuckDB**.

## What's Included

### Part 1: PostgreSQL Database Logging (9 Steps)

1. **Connect to PostgreSQL** - Configure and connect to PostgreSQL server
2. **Initialize Schema** - Create log table with 6 optimized indexes
3. **Verify Table** - Check table creation and statistics
4. **Configure Handler** - Set up database logging handler
5. **Test Logging** - Write test logs to database
6. **Query Logs** - View logs using SQL
7. **Create Sample Data** - Set up demo employees table
8. **SqlAgent Demo** (Optional) - Use SqlAgent with database logging
9. **Analyze Logs** - Run analytical queries

### Part 2: DuckDB Database Logging (9 Steps)

1. **Connect to DuckDB** - In-memory or persistent file
2. **Initialize Schema** - Create log table
3. **Verify Table** - Check table creation
4. **Configure Handler** - Set up database logging
5. **Test Logging** - Write test logs
6. **Query Logs** - View logs with SQL
7. **Create Sample Data** - Set up demo data
8. **Analyze Logs** - Basic analytics
9. **Advanced Queries** - JSON field extraction

### Part 3: Best Practices

- Comparison table: PostgreSQL vs DuckDB
- When to use each database
- Log level configuration
- Table maintenance tips
- Query performance optimization

## Quick Start

### Prerequisites

```bash
# Install required packages
pip install ibis-framework[postgres,duckdb] pandas

# For PostgreSQL: Ensure server is running
# For DuckDB: No server needed
```

### Run the Notebook

```bash
# Start Jupyter
jupyter notebook examples/database_logging_setup.ipynb

# Or use JupyterLab
jupyter lab examples/database_logging_setup.ipynb
```

### Configuration

**PostgreSQL Settings** (Cell 4):
```python
POSTGRES_CONFIG = {
    'host': 'localhost',      # Your PostgreSQL host
    'port': 5432,             # Your PostgreSQL port
    'database': 'my_db',      # Your database name
    'user': 'postgres',       # Your username
    'password': 'password'    # Your password
}
```

**DuckDB Settings** (Cell - Part 2):
```python
# In-memory (default)
duckdb_con = ibis.duckdb.connect()

# OR persistent file
duckdb_con = ibis.duckdb.connect("logs/agent_logs.db")
```

## Notebook Structure

### Interactive Learning

The notebook is designed for **hands-on learning**:

- ✅ Clear step-by-step instructions
- ✅ Runnable code cells
- ✅ Expected output examples
- ✅ Detailed explanations
- ✅ Best practices highlighted

### Self-Contained

Each part is **independent**:

- Part 1 (PostgreSQL) can be run alone
- Part 2 (DuckDB) can be run alone
- No dependencies between parts

### Production-Ready Code

All code examples are **production-ready**:

- Error handling included
- Best practices applied
- Security considerations
- Performance optimized

## Key Features Demonstrated

### 1. Schema Initialization

**PostgreSQL:**
```python
init_postgres_log_schema(
    con=postgres_con,
    table_name="sql_agent_logs",
    schema="public"
)
# Creates table with 6 indexes
```

**DuckDB:**
```python
init_duckdb_log_schema(
    con=duckdb_con,
    table_name="sql_agent_logs"
)
# Creates table with auto-increment
```

### 2. Database Handler Setup

```python
db_handler = DatabaseLogHandler(
    con=postgres_con,
    table_name="sql_agent_logs",
    db_type="postgres",  # or "duckdb"
    schema="public",     # PostgreSQL only
    level=logging.INFO
)

logger.addHandler(db_handler)
```

### 3. Structured Logging

```python
agent_logger = SQLAgentLogger(
    logger,
    extra={'session_id': 'demo-session'}
)

agent_logger.info(
    "Query executed",
    extra={
        'operation_type': 'query_result',
        'success': True,
        'rows_returned': 100
    }
)
```

### 4. Log Querying

**PostgreSQL:**
```sql
SELECT
    timestamp,
    level,
    message,
    extra_fields->>'operation_type' as operation
FROM sql_agent_logs
WHERE level = 'ERROR'
ORDER BY timestamp DESC;
```

**DuckDB:**
```sql
SELECT
    timestamp,
    level,
    json_extract(extra_fields, '$.operation_type') as operation
FROM sql_agent_logs
ORDER BY timestamp DESC;
```

## Example Queries Included

The notebook demonstrates **10+ analytical queries**:

1. Count logs by level
2. Count logs by operation type
3. View recent logs
4. Filter by time range
5. Extract JSON fields
6. Session-based analysis
7. Error rate calculation
8. And more...

## Optional SqlAgent Demo

The notebook includes an **optional section** for using SqlAgent with database logging:

```python
# Requires API key
agent = SqlAgent(
    api_key="your-key",
    model="gpt-4o-mini",
    con=postgres_con,
    tbl_name="employees",
    enable_logging=True,
    log_file=None,  # Database only
    log_to_console=False
)

result = agent.ask_question("How many employees?")
# All activity logged to database!
```

**Note:** This section is commented out by default. Uncomment and add your API key to test.

## Comparison Table (in Notebook)

| Feature | PostgreSQL | DuckDB |
|---------|-----------|--------|
| **Use Case** | Production, shared | Development, portable |
| **Setup** | Requires server | In-memory or file |
| **Performance** | Concurrent writes | Analytical queries |
| **JSON** | JSONB + GIN indexes | JSON extraction |
| **Persistence** | Always | Optional |
| **Sharing** | Multi-user | Single process |

## Best Practices Covered

### 1. Database Selection
- When to use PostgreSQL
- When to use DuckDB
- Trade-offs and considerations

### 2. Configuration
- Log levels (INFO vs DEBUG)
- Handler setup
- Multiple handlers (console + database)

### 3. Performance
- Index usage
- Query optimization
- JSON field access

### 4. Maintenance
- Table vacuuming (PostgreSQL)
- Log archival
- Storage management

## Sample Output

When you run the notebook, you'll see:

```
✅ Connected to PostgreSQL: localhost:5432/my_db
✅ PostgreSQL log table initialized!
   Table: public.sql_agent_logs
   Indexes: 6 created for query performance

📊 Table Statistics:
   Table exists: True
   Total logs: 3

📋 Recent logs from PostgreSQL:
 id                   timestamp level                             message operation_type           session_id
  1 2024-01-15 14:30:45.123000  INFO PostgreSQL database logging... initialization notebook-postgres-demo
  2 2024-01-15 14:30:45.456000  INFO                   Test log entry           test notebook-postgres-demo
```

## Troubleshooting

### Issue: PostgreSQL connection failed

**Solution:**
1. Check PostgreSQL server is running
2. Verify credentials in `POSTGRES_CONFIG`
3. Ensure database exists
4. Check network/firewall settings

### Issue: Permission denied on PostgreSQL

**Solution:**
```sql
-- Grant necessary permissions
GRANT CREATE ON SCHEMA public TO postgres;
GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres;
```

### Issue: DuckDB table not found

**Solution:**
- Re-run the initialization cell
- Check if using in-memory (data lost on disconnect)
- For persistent storage, use: `ibis.duckdb.connect("file.db")`

## Next Steps After Running Notebook

1. **Integrate with Your Code**
   - Copy initialization code to your scripts
   - Configure for your environment
   - Set up production logging

2. **Build Analytics**
   - Create dashboards
   - Monitor error rates
   - Track token usage
   - Analyze performance

3. **Production Deployment**
   - Use PostgreSQL for production
   - Set up log rotation
   - Configure monitoring
   - Implement alerting

## Related Documentation

- 📘 **Complete Guide:** `docs/DATABASE_LOGGING.md`
- 📄 **Python Examples:** `examples/database_logging_examples.py`
- 🔧 **Source Code:** `sql_ai_agent/log_database.py`
- 📊 **Summary:** `docs/DATABASE_LOGGING_SUMMARY.md`

## Notebook Features

✅ **Self-Contained** - All code in one place
✅ **Runnable** - Execute cell by cell
✅ **Educational** - Clear explanations
✅ **Production-Ready** - Real-world code
✅ **Interactive** - Modify and experiment
✅ **Visual** - Tables and formatted output

## Tips for Use

### For Learning
- Run cells sequentially
- Read all markdown cells
- Experiment with queries
- Try different configurations

### For Development
- Use DuckDB in-memory
- Enable DEBUG level logging
- Test different scenarios
- Iterate quickly

### For Production
- Use PostgreSQL
- Set INFO level logging
- Configure proper credentials
- Set up monitoring

## File Location

```
build-with-ai-safe-and-scalable-sql-ai-agents-2757076/
└── examples/
    └── database_logging_setup.ipynb  ← This notebook
```

## Support

For questions or issues:
- Check inline comments in notebook
- See `docs/DATABASE_LOGGING.md`
- Review Python examples
- Check module docstrings

---

**Created:** 2026-02-05
**Last Updated:** 2026-02-05
**Status:** ✅ Ready to Use
