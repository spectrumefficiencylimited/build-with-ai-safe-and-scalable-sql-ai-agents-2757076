import marimo

__generated_with = "0.19.4"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    mo.md(
        r"""
        # SQL AI Agent Testing

        Interactive notebook for testing SQL AI agents with different configurations.

        Use the dropdowns below to select your database and LLM provider.
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
    return SqlAgent, ibis, load_config, pd


@app.cell
def _(mo):
    mo.md(r"""
    ## Configuration
    """)
    return


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
def _(mo):
    # LLM Provider dropdown

    provider_dropdown = mo.ui.dropdown(
        options=["Anthropic", "Docker Model Runner","Google", "OpenAI"],
        value="OpenAI",
        label="Select LLM Provider:"
    )

    provider_dropdown
    return (provider_dropdown,)


@app.cell
def _(config, mo, provider_name):
    models = config.get_model_names(provider_name= provider_name)
    print(models[0])
    print(type(models))
    provider_models_dropdown = mo.ui.dropdown(
        options = models,
        value = models[0],
        label = "Select Model"
    )

    provider_models_dropdown

    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Custom Query
    """)
    return


@app.cell
def _(mo):
    # Text input for custom questions
    custom_question_input = mo.ui.text_area(
        placeholder="Enter your question here...",
        label="Ask a custom question:",
        full_width=True
    )

    custom_question_input
    return (custom_question_input,)


@app.cell
def _(agent, custom_question_input, mo):
    if custom_question_input.value:
        custom_result = agent.ask_question(
            question=custom_question_input.value,
            verbose=False
        )

        mo.md(f"""
        **Question:** {custom_question_input.value}

        **Generated SQL:**
        ```sql
        {custom_result.query}
        ```

        **Result:**
        """)
    else:
        mo.md("*Enter a question above to see results*")
    return (custom_result,)


@app.cell
def _(custom_question_input, custom_result):
    custom_result.data if custom_question_input.value else None
    return


@app.cell
def _(database_dropdown, mo):
    mo.md(f"""
    **Selected Database:** {database_dropdown.value}
    """)
    return


@app.cell
def _(mo, provider_dropdown):
    mo.md(f"""
    **Selected LLM Provider:** {provider_dropdown.value}
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Database Connection
    """)
    return


@app.cell
def _(database_dropdown, ibis, mo, pd):
    # Map dropdown values to provider names
    provider_map = {
        "Docker Model Runner": "docker_model_runner",
        "OpenAI": "openai",
        "Anthropic": "anthropic",
        "Google": "google"
    }
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
    return con, provider_map, tbl_name


@app.cell
def _(mo):
    mo.md(r"""
    ## LLM Configuration
    """)
    return


@app.cell
def _(load_config, mo, provider_dropdown, provider_map):
    # Load LLM configuration
    config = load_config()

    # Get provider name
    provider_name = provider_map[provider_dropdown.value]


    # Get provider settings
    base_url = config.get_base_url(provider_name)
    api_key = config.get_api_key(provider_name)
    model = config.get_default_model(provider_name)
    fallback_model = config.get_fallback_model(provider_name)
    temperature = config.get_temperature(provider_name)
    max_tokens = config.get_max_tokens(provider_name)

    mo.md(f"""
    **LLM Provider:** {provider_dropdown.value}

    - **Model:** {model}
    - **Fallback Model:** {fallback_model}
    - **Base URL:** {base_url}
    - **Temperature:** {temperature}
    - **Max Tokens:** {max_tokens}
    """)
    return api_key, base_url, config, fallback_model, model, provider_name


@app.cell
def _(mo):
    mo.md(r"""
    ## SQL Agent Setup
    """)
    return


@app.cell
def _(SqlAgent, api_key, base_url, con, fallback_model, mo, model, tbl_name):
    # Create SQL Agent with selected configuration
    agent = SqlAgent(
        api_key=api_key,
        base_url=base_url,
        model=model,
        con=con,
        fallback=True,
        fallback_model=fallback_model,
        tbl_name=tbl_name,
    )

    mo.md("✓ SQL Agent initialized successfully")
    return (agent,)


@app.cell
def _(mo):
    mo.md(r"""
    ## Test Queries
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### Query 1: Row Count
    """)
    return


@app.cell
def _(agent, mo):
    question_1 = "How many rows are in the dataset?"
    result_1 = agent.ask_question(question=question_1, verbose=False)

    mo.md(f"""
    **Question:** {question_1}

    **Generated SQL:**
    ```sql
    {result_1.query}
    ```

    **Result:**
    """)
    return (result_1,)


@app.cell
def _(result_1):
    result_1.data
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### Query 2: Unique Values
    """)
    return


@app.cell
def _(agent, mo):
    question_2 = "What are the unique values of the Activity Type Code field?"
    result_2 = agent.ask_question(question=question_2, verbose=False)

    mo.md(f"""
    **Question:** {question_2}

    **Generated SQL:**
    ```sql
    {result_2.query}
    ```

    **Result:**
    """)
    return (result_2,)


@app.cell
def _(result_2):
    result_2.data
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### Query 3: Aggregation with Filter
    """)
    return


@app.cell
def _(agent, mo):
    additional_context = "The Activity Type Code field defines if a passenger departures (e.g., Enplaned) or landed (e.g., Deplaned)"
    question_3 = "How many passengers landed at the airport in 2019?"
    result_3 = agent.ask_question(
        question=question_3,
        additional_context=additional_context,
        trials=3,
        verbose=False
    )

    mo.md(f"""
    **Question:** {question_3}

    **Context:** {additional_context}

    **Generated SQL:**
    ```sql
    {result_3.query}
    ```

    **Result:**
    """)
    return (result_3,)


@app.cell
def _(result_3):
    result_3.data
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Configuration Summary
    """)
    return


@app.cell
def _(database_dropdown, mo, provider_dropdown):
    mo.md(f"""
    ### Current Configuration

    | Setting | Value |
    |---------|-------|
    | Database | {database_dropdown.value} |
    | LLM Provider | {provider_dropdown.value} |

    **Note:** Change the dropdown selections above to test different configurations.
    All cells will automatically update due to marimo's reactive execution!
    """)
    return


if __name__ == "__main__":
    app.run()
