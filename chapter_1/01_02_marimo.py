import marimo

__generated_with = "0.19.4"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Preparing the datasets

    Throughout the course, we will use the San Francisco International Airport report on monthly passenger traffic statistics by airline dataset. In this lesson we will:
    - Load and review the dataset
    - Prepare the dataset to work with AI agents
    - Review the DuckDB approach
    - Review the PostgreSQL approach

    This dataset is available at [here](https://data.sfgov.org/Transportation/Air-Traffic-Passenger-Statistics/rkru-6vcg/about_data)
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Loading the Air Passenger Traffic Dataset

    Let's start by import the required libraries:
    """)
    return


@app.cell
def _():
    import pandas as pd
    import duckdb as db
    import ibis
    import marimo as mo
    return db, ibis, mo, pd


@app.cell
def _(pd):
    df = pd.read_csv("./data/air_traffic.csv")
    df.head()
    return (df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Let's prep the dataset to work with AI agents:
    - Validate the column names
    - Rename the column names
    - Remove irrelevant columns
    - Reformat the columns
    """)
    return


@app.cell
def _(df, pd):
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
    air_traffic.dtypes
    return (air_traffic,)


@app.cell
def _(air_traffic):
    air_traffic
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## DuckDB Workflow

    In this section, we will review how to set up in-memory DuckDB database. Let's start by loading the `duckdb` library:
    """)
    return


@app.cell
def _(air_traffic, db):
    db.register("air_traffic", air_traffic)
    return


@app.cell
def _(db):
    db.sql("DESCRIBE TABLE air_traffic")
    return


@app.cell
def _(db):
    db.sql("SELECT * FROM air_traffic LIMIT 10")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## PostgreSQL Workflow
    """)
    return


@app.cell
def _(ibis):
    con = ibis.postgres.connect(
        user="postgres",
        password="password",
        host="postgres",
        port=5432,
        database="my_db",
    )
    return (con,)


@app.cell
def _(air_traffic, ibis):
    schema = ibis.memtable(air_traffic).schema()
    print(schema)
    return (schema,)


@app.cell
def _(air_traffic, con, schema):
    con.create_table("air_traffic", air_traffic, schema=schema, overwrite=True)

    print(f"Successfully loaded {len(air_traffic)} rows into air_traffic table")

    con.sql("SELECT * FROM air_traffic LIMIT 10").execute()
    return


@app.cell
def _(air_traffic, con, mo):
    _df = mo.sql(
        f"""
        SELECT
            *
        FROM
            air_traffic
        LIMIT
            10
        """,
        engine=con
    )
    return


if __name__ == "__main__":
    app.run()
