"""
SQL AI Agent - Database Logging Module

Provides database-backed logging storage for PostgreSQL and DuckDB.
Enables structured log storage with efficient querying and analysis capabilities.

Features:
- Automatic schema creation and initialization
- JSONB storage for flexible metadata (PostgreSQL)
- JSON storage for flexible metadata (DuckDB)
- Optimized indexes for common query patterns
- Session and operation tracking
- Automatic timestamp handling
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
import json
import traceback


def init_postgres_log_schema(con, table_name: str = "sql_agent_logs", schema: str = "public") -> None:
    """
    Initialize PostgreSQL schema for storing SQL AI Agent logs.

    Creates a table with optimized structure for log storage and querying.
    Includes JSONB field for flexible metadata storage and indexes for
    common query patterns.

    Args:
        con: Ibis PostgreSQL connection
        table_name: Name of the log table (default: "sql_agent_logs")
        schema: PostgreSQL schema name (default: "public")

    Schema Design:
        - id: Auto-incrementing primary key
        - timestamp: Log entry timestamp (indexed)
        - level: Log level (INFO, WARNING, ERROR, DEBUG) (indexed)
        - logger: Logger name (sql_ai_agent.*)
        - message: Log message text
        - session_id: Unique session identifier (indexed)
        - operation_type: Type of operation (query_result, llm_invocation, etc.) (indexed)
        - extra_fields: JSONB field for flexible metadata
        - exception: Exception traceback if present

    Indexes:
        - timestamp (for time-range queries)
        - level (for filtering by severity)
        - session_id (for session tracking)
        - operation_type (for operation filtering)
        - GIN index on extra_fields (for JSONB queries)

    Example:
        >>> import ibis
        >>> con = ibis.postgres.connect(
        ...     host="localhost",
        ...     database="my_db",
        ...     user="postgres",
        ...     password="password"
        ... )
        >>> init_postgres_log_schema(con)
        >>> # Table created: sql_agent_logs

    Raises:
        Exception: If table creation fails
    """

    # Full table name with schema
    full_table_name = f'"{schema}"."{table_name}"'

    # SQL to create the logs table
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {full_table_name} (
        id BIGSERIAL PRIMARY KEY,
        timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        level VARCHAR(10) NOT NULL,
        logger VARCHAR(255) NOT NULL,
        message TEXT NOT NULL,
        session_id VARCHAR(36),
        operation_type VARCHAR(50),
        extra_fields JSONB,
        exception TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """

    # Create indexes for common query patterns
    create_indexes_sql = f"""
    -- Index for timestamp range queries
    CREATE INDEX IF NOT EXISTS idx_{table_name}_timestamp
        ON {full_table_name} (timestamp DESC);

    -- Index for filtering by log level
    CREATE INDEX IF NOT EXISTS idx_{table_name}_level
        ON {full_table_name} (level);

    -- Index for session tracking
    CREATE INDEX IF NOT EXISTS idx_{table_name}_session_id
        ON {full_table_name} (session_id)
        WHERE session_id IS NOT NULL;

    -- Index for operation type filtering
    CREATE INDEX IF NOT EXISTS idx_{table_name}_operation_type
        ON {full_table_name} (operation_type)
        WHERE operation_type IS NOT NULL;

    -- GIN index for JSONB field queries
    CREATE INDEX IF NOT EXISTS idx_{table_name}_extra_fields
        ON {full_table_name} USING GIN (extra_fields);

    -- Composite index for session + timestamp (common pattern)
    CREATE INDEX IF NOT EXISTS idx_{table_name}_session_timestamp
        ON {full_table_name} (session_id, timestamp DESC)
        WHERE session_id IS NOT NULL;
    """

    # Add comment to table for documentation
    comment_sql = f"""
    COMMENT ON TABLE {full_table_name} IS
        'SQL AI Agent structured logs with JSONB metadata storage';

    COMMENT ON COLUMN {full_table_name}.id IS
        'Auto-incrementing primary key';

    COMMENT ON COLUMN {full_table_name}.timestamp IS
        'Log entry timestamp (when the event occurred)';

    COMMENT ON COLUMN {full_table_name}.level IS
        'Log level: DEBUG, INFO, WARNING, ERROR';

    COMMENT ON COLUMN {full_table_name}.logger IS
        'Logger name (e.g., sql_ai_agent.SqlAgent)';

    COMMENT ON COLUMN {full_table_name}.message IS
        'Human-readable log message';

    COMMENT ON COLUMN {full_table_name}.session_id IS
        'Unique session identifier for tracking agent instances';

    COMMENT ON COLUMN {full_table_name}.operation_type IS
        'Operation category: query_result, llm_invocation, validation, etc.';

    COMMENT ON COLUMN {full_table_name}.extra_fields IS
        'JSONB field containing operation-specific metadata';

    COMMENT ON COLUMN {full_table_name}.exception IS
        'Exception traceback if an error occurred';

    COMMENT ON COLUMN {full_table_name}.created_at IS
        'Database record creation timestamp';
    """

    try:
        # Execute table creation
        con.raw_sql(create_table_sql)

        # Execute index creation
        con.raw_sql(create_indexes_sql)

        # Add comments
        con.raw_sql(comment_sql)

        print(f"✅ PostgreSQL log table '{full_table_name}' initialized successfully")
        print(f"   - Table created with optimized schema")
        print(f"   - 6 indexes created for query performance")
        print(f"   - Ready to receive log entries")

    except Exception as e:
        print(f"❌ Failed to initialize PostgreSQL log table: {e}")
        raise


def init_duckdb_log_schema(con, table_name: str = "sql_agent_logs") -> None:
    """
    Initialize DuckDB schema for storing SQL AI Agent logs.

    Creates a table with optimized structure for log storage and querying.
    Uses JSON field for flexible metadata storage (DuckDB doesn't have JSONB).

    Args:
        con: Ibis DuckDB connection
        table_name: Name of the log table (default: "sql_agent_logs")

    Schema Design:
        - id: Auto-incrementing primary key
        - timestamp: Log entry timestamp
        - level: Log level (INFO, WARNING, ERROR, DEBUG)
        - logger: Logger name (sql_ai_agent.*)
        - message: Log message text
        - session_id: Unique session identifier
        - operation_type: Type of operation
        - extra_fields: JSON field for flexible metadata
        - exception: Exception traceback if present

    Example:
        >>> import ibis
        >>> con = ibis.duckdb.connect()
        >>> init_duckdb_log_schema(con)
        >>> # Table created: sql_agent_logs

    Raises:
        Exception: If table creation fails
    """

    # SQL to create the logs table for DuckDB
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id INTEGER PRIMARY KEY,
        timestamp TIMESTAMP NOT NULL,
        level VARCHAR(10) NOT NULL,
        logger VARCHAR(255) NOT NULL,
        message TEXT NOT NULL,
        session_id VARCHAR(36),
        operation_type VARCHAR(50),
        extra_fields JSON,
        exception TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """

    # Create sequence for auto-incrementing ID
    create_sequence_sql = f"""
    CREATE SEQUENCE IF NOT EXISTS {table_name}_id_seq START 1;
    """

    try:
        # Execute sequence creation (DuckDB uses sequences for auto-increment)
        con.con.execute(create_sequence_sql)

        # Execute table creation
        con.con.execute(create_table_sql)

        print(f"✅ DuckDB log table '{table_name}' initialized successfully")
        print(f"   - Table created with optimized schema")
        print(f"   - Auto-increment sequence created")
        print(f"   - Ready to receive log entries")

    except Exception as e:
        print(f"❌ Failed to initialize DuckDB log table: {e}")
        raise


def verify_log_table(con, table_name: str = "sql_agent_logs", db_type: str = "postgres") -> Dict[str, Any]:
    """
    Verify that the log table exists and return its statistics.

    Args:
        con: Database connection (Ibis)
        table_name: Name of the log table
        db_type: Database type ("postgres" or "duckdb")

    Returns:
        Dictionary with table statistics:
        - exists: Boolean indicating if table exists
        - row_count: Number of log entries
        - earliest_log: Timestamp of earliest log
        - latest_log: Timestamp of latest log
        - log_levels: Count of logs by level

    Example:
        >>> stats = verify_log_table(con, "sql_agent_logs", "postgres")
        >>> print(f"Total logs: {stats['row_count']}")
    """

    try:
        if db_type == "postgres":
            # Check if table exists in PostgreSQL using a simpler query
            exists_query = f"""
            SELECT COUNT(*) as count
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = '{table_name}';
            """
            result = con.sql(exists_query).to_pandas()
            exists = result.iloc[0, 0] > 0

        elif db_type == "duckdb":
            # Check if table exists in DuckDB
            exists_query = f"""
            SELECT COUNT(*) as count
            FROM information_schema.tables
            WHERE table_name = '{table_name}';
            """
            result = con.con.execute(exists_query).df()
            exists = result.iloc[0, 0] > 0
        else:
            raise ValueError(f"Unsupported db_type: {db_type}")

        if not exists:
            return {
                "exists": False,
                "row_count": 0,
                "earliest_log": None,
                "latest_log": None,
                "log_levels": {}
            }

        # Get statistics
        stats_query = f"""
        SELECT
            COUNT(*) as total_logs,
            MIN(timestamp) as earliest_log,
            MAX(timestamp) as latest_log
        FROM {table_name};
        """

        levels_query = f"""
        SELECT
            level,
            COUNT(*) as count
        FROM {table_name}
        GROUP BY level
        ORDER BY count DESC;
        """

        if db_type == "postgres":
            stats = con.sql(stats_query).to_pandas()
            levels = con.sql(levels_query).to_pandas()
        else:  # duckdb
            stats = con.con.execute(stats_query).df()
            levels = con.con.execute(levels_query).df()

        return {
            "exists": True,
            "row_count": int(stats.iloc[0]['total_logs']),
            "earliest_log": stats.iloc[0]['earliest_log'],
            "latest_log": stats.iloc[0]['latest_log'],
            "log_levels": dict(zip(levels['level'], levels['count']))
        }

    except Exception as e:
        # Return exists=False on any error, but include error details
        return {
            "exists": False,
            "error": str(e)
        }


def drop_log_table(con, table_name: str = "sql_agent_logs", db_type: str = "postgres",
                   schema: str = "public", confirm: bool = False) -> None:
    """
    Drop the log table (DANGEROUS - for testing/cleanup only).

    Args:
        con: Database connection (Ibis)
        table_name: Name of the log table to drop
        db_type: Database type ("postgres" or "duckdb")
        schema: PostgreSQL schema name (default: "public")
        confirm: Must be True to actually drop the table (safety check)

    Example:
        >>> # BE CAREFUL - This deletes all logs!
        >>> drop_log_table(con, "sql_agent_logs", "postgres", confirm=True)

    Raises:
        ValueError: If confirm is not True
        Exception: If drop fails
    """

    if not confirm:
        raise ValueError(
            "Must set confirm=True to drop log table. "
            "This will DELETE ALL LOGS permanently!"
        )

    try:
        if db_type == "postgres":
            full_table_name = f'"{schema}"."{table_name}"'
            drop_sql = f"DROP TABLE IF EXISTS {full_table_name} CASCADE;"
            con.raw_sql(drop_sql)
        elif db_type == "duckdb":
            drop_sql = f"DROP TABLE IF EXISTS {table_name};"
            drop_seq_sql = f"DROP SEQUENCE IF EXISTS {table_name}_id_seq;"
            con.con.execute(drop_sql)
            con.con.execute(drop_seq_sql)
        else:
            raise ValueError(f"Unsupported db_type: {db_type}")

        print(f"⚠️  Log table '{table_name}' has been dropped")

    except Exception as e:
        print(f"❌ Failed to drop log table: {e}")
        raise


class DatabaseLogHandler(logging.Handler):
    """
    Custom logging handler that writes log records to a database table.

    Integrates with Python's logging system to automatically store structured
    logs in PostgreSQL or DuckDB. Handles all standard log record fields plus
    custom extra fields.

    Attributes:
        con: Database connection (Ibis)
        table_name: Name of the log table
        db_type: Database type ("postgres" or "duckdb")
        schema: PostgreSQL schema name (only for PostgreSQL)
        batch_size: Number of logs to batch before writing (future enhancement)

    Example:
        >>> import logging
        >>> from sql_ai_agent.log_database import DatabaseLogHandler
        >>> from sql_ai_agent.logger import SQLAgentLogger
        >>>
        >>> # Create database handler
        >>> db_handler = DatabaseLogHandler(
        ...     con=postgres_con,
        ...     table_name="sql_agent_logs",
        ...     db_type="postgres"
        ... )
        >>>
        >>> # Add to logger
        >>> logger = logging.getLogger('sql_ai_agent')
        >>> logger.addHandler(db_handler)
        >>>
        >>> # Now all logs are written to database
        >>> logger.info("Test message", extra={'operation_type': 'test'})
    """

    def __init__(
        self,
        con,
        table_name: str = "sql_agent_logs",
        db_type: str = "postgres",
        schema: str = "public",
        level: int = logging.INFO
    ):
        """
        Initialize database log handler.

        Args:
            con: Database connection (Ibis)
            table_name: Name of the log table
            db_type: Database type ("postgres" or "duckdb")
            schema: PostgreSQL schema name (only for PostgreSQL, default: "public")
            level: Minimum log level to write (default: INFO)
        """
        super().__init__(level)
        self.con = con
        self.table_name = table_name
        self.db_type = db_type.lower()
        self.schema = schema

        # Build full table name
        if self.db_type == "postgres":
            self.full_table_name = f'"{schema}"."{table_name}"'
        else:
            self.full_table_name = table_name

        # Validate db_type
        if self.db_type not in ["postgres", "duckdb"]:
            raise ValueError(f"Unsupported db_type: {db_type}. Must be 'postgres' or 'duckdb'")

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record to the database.

        Called automatically by Python's logging system when a log is generated.
        Extracts all fields from the log record and inserts into the database.

        Args:
            record: LogRecord instance from Python logging system
        """
        try:
            # Extract standard fields
            timestamp = datetime.fromtimestamp(record.created).isoformat()
            level = record.levelname
            logger_name = record.name
            message = record.getMessage()

            # Extract extra fields if present
            session_id = None
            operation_type = None
            extra_fields = {}

            if hasattr(record, 'extra_fields'):
                extra_data = record.extra_fields
                session_id = extra_data.get('session_id')
                operation_type = extra_data.get('operation_type')

                # Store all extra fields as JSON
                extra_fields = extra_data

            # Extract exception info if present
            exception_text = None
            if record.exc_info:
                exception_text = ''.join(traceback.format_exception(*record.exc_info))

            # Build INSERT query
            if self.db_type == "postgres":
                self._insert_postgres(
                    timestamp, level, logger_name, message,
                    session_id, operation_type, extra_fields, exception_text
                )
            else:  # duckdb
                self._insert_duckdb(
                    timestamp, level, logger_name, message,
                    session_id, operation_type, extra_fields, exception_text
                )

        except Exception as e:
            # Don't let logging failures break the application
            # Use handleError to report the problem
            self.handleError(record)

    def _insert_postgres(
        self,
        timestamp: str,
        level: str,
        logger_name: str,
        message: str,
        session_id: Optional[str],
        operation_type: Optional[str],
        extra_fields: Dict[str, Any],
        exception_text: Optional[str]
    ) -> None:
        """Insert log record into PostgreSQL."""

        # Convert extra_fields dict to JSON string for JSONB
        extra_json = json.dumps(extra_fields) if extra_fields else None

        # Escape single quotes in string values for SQL
        def escape_sql(value):
            if value is None:
                return 'NULL'
            # Escape single quotes by doubling them
            escaped = str(value).replace("'", "''")
            return f"'{escaped}'"

        # Build INSERT query with escaped values
        insert_sql = f"""
        INSERT INTO {self.full_table_name}
            (timestamp, level, logger, message, session_id, operation_type, extra_fields, exception)
        VALUES
            (
                '{timestamp}'::TIMESTAMPTZ,
                {escape_sql(level)},
                {escape_sql(logger_name)},
                {escape_sql(message)},
                {escape_sql(session_id)},
                {escape_sql(operation_type)},
                {escape_sql(extra_json)}::JSONB,
                {escape_sql(exception_text)}
            )
        """

        # Execute using Ibis raw_sql (no psycopg2 import needed)
        self.con.raw_sql(insert_sql)

    def _insert_duckdb(
        self,
        timestamp: str,
        level: str,
        logger_name: str,
        message: str,
        session_id: Optional[str],
        operation_type: Optional[str],
        extra_fields: Dict[str, Any],
        exception_text: Optional[str]
    ) -> None:
        """Insert log record into DuckDB."""

        # Convert extra_fields dict to JSON string
        extra_json = json.dumps(extra_fields) if extra_fields else None

        # Escape single quotes in string values
        def escape_sql(value):
            if value is None:
                return 'NULL'
            return "'" + str(value).replace("'", "''") + "'"

        # Get next ID from sequence
        next_id_sql = f"SELECT nextval('{self.table_name}_id_seq')"
        next_id = self.con.con.execute(next_id_sql).fetchone()[0]

        # Build INSERT query
        insert_sql = f"""
        INSERT INTO {self.full_table_name}
            (id, timestamp, level, logger, message, session_id, operation_type, extra_fields, exception)
        VALUES
            (
                {next_id},
                '{timestamp}'::TIMESTAMP,
                {escape_sql(level)},
                {escape_sql(logger_name)},
                {escape_sql(message)},
                {escape_sql(session_id)},
                {escape_sql(operation_type)},
                {escape_sql(extra_json)}::JSON,
                {escape_sql(exception_text)}
            )
        """

        self.con.con.execute(insert_sql)

    def close(self) -> None:
        """
        Close the handler and clean up resources.

        Called when the logger is shut down.
        """
        super().close()
        # Connection cleanup handled by caller


# Example usage and testing
if __name__ == "__main__":
    """
    Example usage of the database logging schema initialization.
    """

    print("=" * 80)
    print("SQL AI Agent - Database Logging Schema Initialization")
    print("=" * 80)

    # Example 1: PostgreSQL
    print("\n📘 Example 1: PostgreSQL Schema Initialization")
    print("-" * 80)
    print("""
    import ibis
    from sql_ai_agent.log_database import init_postgres_log_schema, verify_log_table

    # Connect to PostgreSQL
    con = ibis.postgres.connect(
        host="localhost",
        database="my_db",
        user="postgres",
        password="password",
        port=5432
    )

    # Initialize log table
    init_postgres_log_schema(con, table_name="sql_agent_logs", schema="public")

    # Verify table was created
    stats = verify_log_table(con, "sql_agent_logs", "postgres")
    print(f"Table exists: {stats['exists']}")
    print(f"Total logs: {stats['row_count']}")
    """)

    # Example 2: DuckDB
    print("\n📗 Example 2: DuckDB Schema Initialization")
    print("-" * 80)
    print("""
    import ibis
    from sql_ai_agent.log_database import init_duckdb_log_schema, verify_log_table

    # Connect to DuckDB (in-memory)
    con = ibis.duckdb.connect()

    # Initialize log table
    init_duckdb_log_schema(con, table_name="sql_agent_logs")

    # Verify table was created
    stats = verify_log_table(con, "sql_agent_logs", "duckdb")
    print(f"Table exists: {stats['exists']}")
    print(f"Total logs: {stats['row_count']}")
    """)

    # Example 3: Custom table name
    print("\n📙 Example 3: Custom Table Name and Schema")
    print("-" * 80)
    print("""
    # Use custom table name and schema
    init_postgres_log_schema(
        con,
        table_name="my_custom_logs",
        schema="analytics"
    )

    # This creates: analytics.my_custom_logs
    """)

    print("\n" + "=" * 80)
    print("✅ Examples complete. Ready to use database logging!")
    print("=" * 80)
