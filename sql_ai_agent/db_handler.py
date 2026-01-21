import pandas as pd
import duckdb
import ibis
import logging
import time
from dataclasses import dataclass

# Create module-level logger
logger = logging.getLogger('sql_ai_agent.db_handler')


@dataclass
class TableSchema:
    schema: str  # "col1 type1, col2 type2"
    db_type: str  # "postgres" or "duckdb"
    table: pd.DataFrame  # Schema as DataFrame


def _format_schema(df: pd.DataFrame) -> str:
    """Format a schema DataFrame as 'col1 type1, col2 type2'."""
    return ", ".join(f"{row.column_name} {row.column_type}" for row in df.itertuples())


def get_postgres_schema(con, tbl_name: str) -> pd.DataFrame:
    """
    Retrieve a PostgreSQL table schema safely using parameterized SQL.
    """

    query = f"""
        SELECT 
            column_name,
            data_type AS column_type
        FROM information_schema.columns
        WHERE table_name = '{tbl_name}'
        ORDER BY ordinal_position
    """
    df = con.sql(query).execute()
    return df


def get_duckdb_schema(con, tbl_name: str) -> pd.DataFrame:
    """Retrieve DuckDB table schema using Ibis introspection."""

    query = f"DESCRIBE SELECT * FROM {tbl_name};"
    df = con.con.execute(query).df()
    df = df[["column_name", "column_type"]]
    return df


def get_tbl_attr(con, tbl_name: str) -> TableSchema:
    """
    Detect backend and return schema information as a structured object.
    """

    # Detect Ibis Postgres backend
    if getattr(con, "name", None) == "postgres":
        df = get_postgres_schema(con, tbl_name)
        db_type = "postgres"

    # Detect DuckDB backend (Ibis backend name is 'duckdb')
    elif getattr(con, "name", None) == "duckdb":
        df = get_duckdb_schema(con, tbl_name)
        db_type = "duckdb"

    else:
        raise TypeError(
            f"Unsupported connection type: {type(con)}. "
            "Expected Ibis Postgres backend or Ibis DuckDB backend."
        )

    formatted = _format_schema(df)

    return TableSchema(schema=formatted, db_type=db_type, table=df)


def query_execute(con, query: str) -> pd.DataFrame:
    """Execute SQL query and return results as DataFrame.

    Args:
        con: Database connection (Ibis connection)
        query: SQL query string to execute

    Returns:
        DataFrame with query results

    Raises:
        TypeError: If connection type is unsupported
    """
    start_time = time.perf_counter()

    try:
        # Detect Ibis Postgres backend
        if getattr(con, "name", None) == "postgres":
            df = con.sql(query).execute()
            db_type = "postgres"

        # Detect DuckDB backend (Ibis backend name is 'duckdb')
        elif getattr(con, "name", None) == "duckdb":
            df = con.con.sql(query).df()
            db_type = "duckdb"

        else:
            raise TypeError(
                f"Unsupported connection type: {type(con)}. "
                "Expected Ibis Postgres backend or Ibis DuckDB backend."
            )

        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "Query executed successfully",
            extra={
                'operation_type': 'query_execution',
                'duration_ms': round(duration_ms, 2),
                'rows_returned': len(df),
                'query_length': len(query),
                'database_type': db_type
            }
        )

        return df

    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.error(
            f"Query execution failed: {str(e)}",
            extra={
                'operation_type': 'query_execution',
                'duration_ms': round(duration_ms, 2),
                'error_type': type(e).__name__,
                'query': query[:200]  # Log first 200 chars to avoid huge logs
            },
            exc_info=True
        )

        raise

def _quote_ident(name: str) -> str:
    """
    Safely quote SQL identifiers (column / table names).

    Uses ANSI double quotes, compatible with Postgres and DuckDB.
    """
    escaped = name.replace('"', '""')
    return f'"{escaped}"'



def _is_character_type(dtype: str, db_type: str) -> bool:
    dtype = dtype.lower()

    if db_type == "postgres":
        return dtype in {"character varying", "varchar", "character", "char", "text"}

    elif db_type == "duckdb":
        return dtype in {"varchar", "text", "string"}

    return False


def get_character_distinct_values(
    con, tbl_schema: TableSchema, tbl_name: str, max_values: int = 50
) -> dict[str, list]:
    char_cols = [
        row.column_name
        for row in tbl_schema.table.itertuples()
        if _is_character_type(row.column_type, tbl_schema.db_type)
    ]

    quoted_table = _quote_ident(tbl_name)

    results: dict[str, list] = {}

    for col in char_cols:
        qcol = _quote_ident(col)

        query = f"""
            SELECT DISTINCT {qcol}
            FROM {quoted_table}
            WHERE {qcol} IS NOT NULL
            ORDER BY {qcol}
            LIMIT {max_values}
        """

        df = query_execute(con, query)

        # Pandas column name is unquoted
        results[col] = df[col].tolist()

    return results
