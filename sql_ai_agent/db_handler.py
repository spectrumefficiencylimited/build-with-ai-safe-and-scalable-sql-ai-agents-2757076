import pandas as pd
import duckdb
import ibis
from dataclasses import dataclass


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
        DataFrame with query results (SELECT queries)
        DataFrame with execution info (DELETE/UPDATE/INSERT queries)

    Raises:
        TypeError: If connection type is unsupported
    """
    try:
        # Detect if this is a write operation (DELETE, UPDATE, INSERT)
        query_upper = query.strip().upper()
        is_write_operation = any(
            query_upper.startswith(keyword)
            for keyword in ['DELETE', 'UPDATE', 'INSERT', 'CREATE', 'DROP', 'ALTER', 'TRUNCATE']
        )

        # Detect Ibis Postgres backend
        if getattr(con, "name", None) == "postgres":
            if is_write_operation:
                # Use raw_sql for write operations
                con.raw_sql(query)
                # Return a DataFrame indicating success
                return pd.DataFrame({
                    'status': ['success'],
                    'message': ['Query executed successfully'],
                    'query_type': ['write_operation']
                })
            else:
                # Use sql() for SELECT queries
                df = con.sql(query).execute()
            db_type = "postgres"

        # Detect DuckDB backend (Ibis backend name is 'duckdb')
        elif getattr(con, "name", None) == "duckdb":
            if is_write_operation:
                # Use raw execute for write operations
                con.con.execute(query)
                # Return a DataFrame indicating success
                return pd.DataFrame({
                    'status': ['success'],
                    'message': ['Query executed successfully'],
                    'query_type': ['write_operation']
                })
            else:
                # Use sql() for SELECT queries
                df = con.con.sql(query).df()
            db_type = "duckdb"

        else:
            raise TypeError(
                f"Unsupported connection type: {type(con)}. "
                "Expected Ibis Postgres backend or Ibis DuckDB backend."
            )

        # Return the dataframe for SELECT queries
        if not is_write_operation:
            return df

    except Exception as e:
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
