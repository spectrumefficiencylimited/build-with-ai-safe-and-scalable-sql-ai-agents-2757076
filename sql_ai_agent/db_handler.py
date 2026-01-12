import pandas as pd
import duckdb
import ibis
from dataclasses import dataclass

@dataclass
class TableSchema:
    schema: str      # "col1 type1, col2 type2"
    db_type: str        # "postgres" or "duckdb"
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
    df =con.con.execute(query).df()
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

    return TableSchema(
        schema=formatted,
        db_type=db_type,
        table=df
    )


def query_execute(con, query: str) -> pd.DataFrame:
    # Detect Ibis Postgres backend
    if getattr(con, "name", None) == "postgres":
        df = con.sql(query).execute()
        

    # Detect DuckDB backend (Ibis backend name is 'duckdb')
    elif getattr(con, "name", None) == "duckdb":
        df = con.con.sql(query).df()
        

    else:
        raise TypeError(
            f"Unsupported connection type: {type(con)}. "
            "Expected Ibis Postgres backend or Ibis DuckDB backend."
        )
    return df