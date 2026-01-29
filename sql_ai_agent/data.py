import os
import sys
import pandas as pd
import ibis


def get_ibis_connection(
    backend: str,
    *,
    tbl_name: str = "air_traffic",
    postgres_config: dict | None = None,
    duckdb_csv_path: str | None = None,
):
    """
    Create and return an Ibis connection.

    Parameters
    ----------
    backend : str
        Connection backend. Supported values: "postgres", "duckdb".
    tbl_name : str
        Table name to register (DuckDB only).
    postgres_config : dict
        Dictionary with Postgres connection arguments.
        Example:
        {
            "user": "postgres",
            "password": "password",
            "host": "postgres",
            "port": 5432,
            "database": "my_db",
        }
    duckdb_csv_path : str
        Path to the CSV file to load into DuckDB.

    Returns
    -------
    ibis.BaseBackend
        An Ibis connection object.
    """

    backend = backend.lower()

    if backend == "postgres":
        if postgres_config is None:
            raise ValueError("postgres_config must be provided for Postgres backend")

        con = ibis.postgres.connect(**postgres_config)
        return con

    elif backend == "duckdb":
        if duckdb_csv_path is None:
            raise ValueError("duckdb_csv_path must be provided for DuckDB backend")

        # Ensure project root is on PYTHONPATH (mirrors your logic)
        current_dir = os.getcwd()
        project_root = os.path.dirname(current_dir)
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        df = pd.read_csv(duckdb_csv_path)

        con = ibis.duckdb.connect()
        con.create_table(tbl_name, df, overwrite=True)
        return con

    else:
        raise ValueError(f"Unsupported backend: {backend}")
