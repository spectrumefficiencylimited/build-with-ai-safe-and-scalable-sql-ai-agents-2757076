import sys
import os

current_dir = os.getcwd()
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import ibis
from sql_ai_agent.log_database import (
    init_postgres_log_schema,
    init_duckdb_log_schema,
    DatabaseLogHandler,
    verify_log_table
)
from sql_ai_agent.logger import setup_logging
from sql_ai_agent.SqlAgent import SqlAgent
import logging


def example_1_postgres_basic():
    """
    Example 1: Basic PostgreSQL database logging setup.
    """
    print("\n" + "=" * 80)
    print("Example 1: Basic PostgreSQL Database Logging")
    print("=" * 80)

    # Step 1: Connect to PostgreSQL
    print("\n📌 Step 1: Connect to PostgreSQL")
    con = ibis.postgres.connect(
        host="localhost",
        port=5432,
        database="my_db",
        user="postgres",
        password="password"
    )
    print("✅ Connected to PostgreSQL")

    # Step 2: Initialize log table schema
    print("\n📌 Step 2: Initialize log table")
    init_postgres_log_schema(
        con,
        table_name="sql_agent_logs",
        schema="public"
    )

    # Step 3: Verify table was created
    print("\n📌 Step 3: Verify table")
    stats = verify_log_table(con, "sql_agent_logs", "postgres")
    print(f"Table exists: {stats['exists']}")
    print(f"Total logs: {stats['row_count']}")

    # Step 4: Set up logging with database handler
    print("\n📌 Step 4: Configure logging with database handler")

    # Create base logger
    logger = logging.getLogger('sql_ai_agent')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    # Add database handler
    db_handler = DatabaseLogHandler(
        con=con,
        table_name="sql_agent_logs",
        db_type="postgres",
        schema="public",
        level=logging.INFO
    )
    logger.addHandler(db_handler)

    # Also add console handler for visibility
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(console_handler)

    print("✅ Database logging configured")

    # Step 5: Test logging
    print("\n📌 Step 5: Test logging")

    # Create SQLAgentLogger adapter for structured logging
    from sql_ai_agent.logger import SQLAgentLogger
    agent_logger = SQLAgentLogger(logger, extra={'session_id': 'example-session-1'})

    # Log some test messages
    agent_logger.info("Agent initialized", extra={
        'operation_type': 'initialization',
        'model': 'gpt-4o',
        'database_type': 'postgres'
    })

    agent_logger.info("Query executed successfully", extra={
        'operation_type': 'query_result',
        'question': 'How many rows in the table?',
        'success': True,
        'rows_returned': 100
    })

    agent_logger.error("Query failed", extra={
        'operation_type': 'query_result',
        'question': 'Invalid query',
        'success': False,
        'error': 'Syntax error in SQL'
    })

    print("✅ Test logs written to database")

    # Step 6: Verify logs were written
    print("\n📌 Step 6: Verify logs in database")
    stats = verify_log_table(con, "sql_agent_logs", "postgres")
    print(f"Total logs: {stats['row_count']}")
    print(f"Log levels: {stats['log_levels']}")

    # Query recent logs
    recent_logs_query = """
    SELECT id, timestamp, level, message, operation_type
    FROM sql_agent_logs
    ORDER BY timestamp DESC
    LIMIT 5;
    """
    recent_logs = con.raw_sql(recent_logs_query).to_pandas()
    print("\nRecent logs:")
    print(recent_logs.to_string(index=False))

    print("\n✅ Example 1 complete!")


def example_2_duckdb_basic():
    """
    Example 2: Basic DuckDB database logging setup.
    """
    print("\n" + "=" * 80)
    print("Example 2: Basic DuckDB Database Logging")
    print("=" * 80)

    # Step 1: Connect to DuckDB (in-memory)
    print("\n📌 Step 1: Connect to DuckDB")
    con = ibis.duckdb.connect()
    print("✅ Connected to DuckDB (in-memory)")

    # Step 2: Initialize log table schema
    print("\n📌 Step 2: Initialize log table")
    init_duckdb_log_schema(con, table_name="sql_agent_logs")

    # Step 3: Verify table was created
    print("\n📌 Step 3: Verify table")
    stats = verify_log_table(con, "sql_agent_logs", "duckdb")
    print(f"Table exists: {stats['exists']}")
    print(f"Total logs: {stats['row_count']}")

    # Step 4: Set up logging with database handler
    print("\n📌 Step 4: Configure logging with database handler")

    logger = logging.getLogger('sql_ai_agent_duckdb')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    # Add database handler
    db_handler = DatabaseLogHandler(
        con=con,
        table_name="sql_agent_logs",
        db_type="duckdb",
        level=logging.INFO
    )
    logger.addHandler(db_handler)

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(console_handler)

    print("✅ Database logging configured")

    # Step 5: Test logging
    print("\n📌 Step 5: Test logging")

    from sql_ai_agent.logger import SQLAgentLogger
    agent_logger = SQLAgentLogger(logger, extra={'session_id': 'duckdb-example-1'})

    # Log some test messages
    agent_logger.info("Agent started", extra={
        'operation_type': 'initialization',
        'model': 'gpt-4o-mini',
        'database_type': 'duckdb'
    })

    agent_logger.debug("Debug information", extra={
        'operation_type': 'debug',
        'trial_number': 1
    })

    agent_logger.warning("Validation warning", extra={
        'operation_type': 'validation',
        'warning': 'Query modified to add LIMIT'
    })

    print("✅ Test logs written to database")

    # Step 6: Verify logs were written
    print("\n📌 Step 6: Verify logs in database")
    stats = verify_log_table(con, "sql_agent_logs", "duckdb")
    print(f"Total logs: {stats['row_count']}")
    print(f"Log levels: {stats['log_levels']}")

    # Query recent logs
    recent_logs = con.con.execute("""
        SELECT id, timestamp, level, message, operation_type
        FROM sql_agent_logs
        ORDER BY timestamp DESC
        LIMIT 5;
    """).df()

    print("\nRecent logs:")
    print(recent_logs.to_string(index=False))

    print("\n✅ Example 2 complete!")


def example_3_sqlagent_with_db_logging():
    """
    Example 3: Use SqlAgent with database logging.
    """
    print("\n" + "=" * 80)
    print("Example 3: SqlAgent with Database Logging")
    print("=" * 80)

    # Connect to DuckDB and load sample data
    print("\n📌 Step 1: Set up database and sample data")
    con = ibis.duckdb.connect()

    # Create sample table
    import pandas as pd
    sample_data = pd.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
        'age': [25, 30, 35, 40, 45],
        'department': ['Engineering', 'Sales', 'Engineering', 'HR', 'Sales']
    })
    con.create_table('employees', sample_data, overwrite=True)
    print("✅ Sample table 'employees' created")

    # Initialize log table
    print("\n📌 Step 2: Initialize log table")
    init_duckdb_log_schema(con, table_name="agent_logs")

    # Step 3: Create SqlAgent with custom logging setup
    print("\n📌 Step 3: Create SqlAgent with database logging")

    # Set up logger with both database and console handlers
    logger = logging.getLogger('sql_ai_agent')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    # Database handler
    db_handler = DatabaseLogHandler(
        con=con,
        table_name="agent_logs",
        db_type="duckdb",
        level=logging.INFO
    )
    logger.addHandler(db_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(console_handler)

    # Create SqlAgent
    # Note: You'll need to provide your API key
    agent = SqlAgent(
        api_key="your-api-key-here",
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
        con=con,
        tbl_name="employees",
        fallback=False,
        fallback_model="gpt-4o-mini",
        enable_logging=True,
        log_level="INFO",
        log_file=None,  # Only database logging, no file
        log_to_console=False,  # We have our own console handler
        memory=True,
        memory_size=5
    )

    print("✅ SqlAgent created with database logging")

    # Step 4: Execute some queries
    print("\n📌 Step 4: Execute queries (all activity logged to database)")

    # Query 1
    result1 = agent.ask_question(
        "How many employees are there?",
        verbose=True
    )

    # Query 2
    result2 = agent.ask_question(
        "What's the average age of employees in Engineering?",
        verbose=True
    )

    # Step 5: Check logs in database
    print("\n📌 Step 5: Review logs in database")

    stats = verify_log_table(con, "agent_logs", "duckdb")
    print(f"\nTotal logs: {stats['row_count']}")
    print(f"Log levels: {stats['log_levels']}")

    # Query logs by operation type
    operation_logs = con.con.execute("""
        SELECT
            operation_type,
            COUNT(*) as count
        FROM agent_logs
        WHERE operation_type IS NOT NULL
        GROUP BY operation_type
        ORDER BY count DESC;
    """).df()

    print("\nLogs by operation type:")
    print(operation_logs.to_string(index=False))

    # Show recent query results
    query_results = con.con.execute("""
        SELECT
            timestamp,
            level,
            message,
            extra_fields->>'success' as success,
            extra_fields->>'rows_returned' as rows
        FROM agent_logs
        WHERE operation_type = 'query_result'
        ORDER BY timestamp DESC;
    """).df()

    print("\nQuery execution logs:")
    print(query_results.to_string(index=False))

    print("\n✅ Example 3 complete!")


def example_4_query_logs():
    """
    Example 4: Querying and analyzing logs from database.
    """
    print("\n" + "=" * 80)
    print("Example 4: Querying and Analyzing Database Logs")
    print("=" * 80)

    # Assuming logs already exist from previous examples
    # Connect to PostgreSQL
    con = ibis.postgres.connect(
        host="localhost",
        database="my_db",
        user="postgres",
        password="password"
    )

    print("\n📊 Log Analysis Queries\n")

    # Query 1: Count logs by level
    print("1️⃣ Logs by severity level:")
    query1 = """
    SELECT level, COUNT(*) as count
    FROM sql_agent_logs
    GROUP BY level
    ORDER BY
        CASE level
            WHEN 'ERROR' THEN 1
            WHEN 'WARNING' THEN 2
            WHEN 'INFO' THEN 3
            WHEN 'DEBUG' THEN 4
        END;
    """
    result1 = con.raw_sql(query1).to_pandas()
    print(result1.to_string(index=False))

    # Query 2: Recent errors
    print("\n2️⃣ Recent errors:")
    query2 = """
    SELECT
        timestamp,
        message,
        extra_fields->>'error' as error_detail
    FROM sql_agent_logs
    WHERE level = 'ERROR'
    ORDER BY timestamp DESC
    LIMIT 5;
    """
    result2 = con.raw_sql(query2).to_pandas()
    print(result2.to_string(index=False))

    # Query 3: Query success rate
    print("\n3️⃣ Query success rate:")
    query3 = """
    SELECT
        COUNT(*) as total_queries,
        SUM(CASE WHEN (extra_fields->>'success')::boolean THEN 1 ELSE 0 END) as successful,
        ROUND(
            100.0 * SUM(CASE WHEN (extra_fields->>'success')::boolean THEN 1 ELSE 0 END) / COUNT(*),
            2
        ) as success_rate_percent
    FROM sql_agent_logs
    WHERE operation_type = 'query_result';
    """
    result3 = con.raw_sql(query3).to_pandas()
    print(result3.to_string(index=False))

    # Query 4: LLM token usage
    print("\n4️⃣ LLM token usage by session:")
    query4 = """
    SELECT
        session_id,
        SUM((extra_fields->>'total_tokens')::int) as total_tokens,
        AVG((extra_fields->>'total_tokens')::int) as avg_tokens_per_call,
        COUNT(*) as llm_calls
    FROM sql_agent_logs
    WHERE operation_type = 'llm_invocation'
        AND extra_fields->>'total_tokens' IS NOT NULL
    GROUP BY session_id
    ORDER BY total_tokens DESC;
    """
    result4 = con.raw_sql(query4).to_pandas()
    print(result4.to_string(index=False))

    # Query 5: Slow queries (queries that took debug attempts)
    print("\n5️⃣ Queries that needed debugging:")
    query5 = """
    SELECT
        extra_fields->>'question' as question,
        COUNT(*) as debug_attempts
    FROM sql_agent_logs
    WHERE operation_type = 'debug'
    GROUP BY extra_fields->>'question'
    ORDER BY debug_attempts DESC
    LIMIT 5;
    """
    result5 = con.raw_sql(query5).to_pandas()
    print(result5.to_string(index=False))

    print("\n✅ Example 4 complete!")


if __name__ == "__main__":
    print("=" * 80)
    print("SQL AI Agent - Database Logging Examples")
    print("=" * 80)
    print("\nChoose an example to run:")
    print("1. PostgreSQL basic setup")
    print("2. DuckDB basic setup")
    print("3. SqlAgent with database logging")
    print("4. Query and analyze logs")
    print("\nOr edit this file to run examples programmatically")
    print("=" * 80)

    # Uncomment to run examples:
    # example_1_postgres_basic()
    # example_2_duckdb_basic()
    # example_3_sqlagent_with_db_logging()
    # example_4_query_logs()
