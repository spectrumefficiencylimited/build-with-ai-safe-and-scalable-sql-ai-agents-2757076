import marimo

__generated_with = "0.19.4"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    mo.md(
        r"""
        # SQL Validation

        In this notebook, we will focus on methods for validate SQL queries before executing them.
        """
    )
    return (mo,)


@app.cell
def _():
    import sys
    import os

    # Add project root to path
    # Get the directory of this file, then go up one level to project root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    import pandas as pd
    import ibis
    import duckdb as db
    from sql_ai_agent.SqlAgent import SqlAgent
    from sql_ai_agent.llm_config_loader import load_config
    return ibis, pd


@app.cell
def _(database_dropdown, ibis, mo, pd):

    tbl_name = "air_traffic"
    # Database connection based on selection
    if database_dropdown.value == "PostgreSQL":
        con = ibis.postgres.connect(
            user="postgres",
            password="password",
            host="postgres",
            port=5432,
            database="my_db",
        )
        mo.md(f"✓ Connected to PostgreSQL database")
    else:  # DuckDB
        # Prepare the dataset

        df = pd.read_csv("data/air_traffic.csv")
        df["Date"] = pd.to_datetime(
            df["Activity Period Start Date"], format="%Y/%m/%d"
        )
        df["Year"] = df["Activity Period"].astype(str).str[:4].astype(int)

        columns = [
            "Year",
            "Date",
            "Operating Airline",
            "Operating Airline IATA Code",
            "Published Airline",
            "Published Airline IATA Code",
            "GEO Summary",
            "GEO Region",
            "Activity Type Code",
            "Price Category Code",
            "Terminal",
            "Boarding Area",
            "Passenger Count"
        ]

        air_traffic = df[columns].copy()
        con = ibis.duckdb.connect()
        # Use create_table instead of register in ibis 11.x
        con.create_table("air_traffic", df, overwrite=True)

        mo.md(f"✓ Connected to DuckDB in-memory database ({len(air_traffic)} rows loaded)")
    return air_traffic, con


@app.cell
def _(mo):
    # Database dropdown
    database_dropdown = mo.ui.dropdown(
        options=["DuckDB", "PostgreSQL"],
        value="DuckDB",
        label="Select Database:"
    )

    database_dropdown
    return (database_dropdown,)


@app.cell
def _(air_traffic, con, mo):
    _df = mo.sql(
        f"""
        SELECT * FROM air_traffic
        """,
        engine=con
    )
    return


@app.cell
def _(air_traffic, con, mo):
    _df = mo.sql(
        f"""
        DROP TABLE air_traffic
        """,
        engine=con
    )
    return


if __name__ == "__main__":
    app.run()
