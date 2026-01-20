# from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from sql_ai_agent.db_handler import get_tbl_attr


def set_prompt_template():
    """
    Build a LangChain ChatPromptTemplate for SQL generation.

    Parameters
    ----------
    question : str
        Natural language question describing the SQL request.
    tbl_name : str
        Name of the SQL table.
    schema : str
        Table schema (column definitions).
    additional_context : str, optional
        Extra system context. Defaults to empty string.

    Returns
    -------
    ChatPromptTemplate
        A LangChain prompt template ready to be invoked.
    """

    system_template = """
Given the following SQL table, your job is to write queries given a user’s request.
Return just the SQL query as plain text, without additional text, and don't use markdown format.
I am querying the data against a {database} database, please make sure you are using the {database} SQL dialects. 
Please ensure that the field names in the query are enclosed in double quotes.
{additional_context}
CREATE TABLE {tbl_name} ({schema})
""".strip()

    user_template = "Write a SQL query that returns: {question}"

    messages = [
        ("system", system_template),
        MessagesPlaceholder(variable_name="chat_history"),
        ("user", user_template),
    ]

    prompt_template = ChatPromptTemplate.from_messages(messages)

    return prompt_template


def format_distinct_values_for_prompt(
    distinct_values: dict[str, list], max_values: int = 10
) -> str:
    """
    Format distinct column values into a prompt-friendly context block.
    """

    if not distinct_values:
        return ""

    lines = ["The following columns have known categorical values:"]

    for col, values in distinct_values.items():
        if not values:
            continue

        shown = values[:max_values]
        suffix = " ..." if len(values) > max_values else ""

        formatted_vals = ", ".join(repr(v) for v in shown)
        lines.append(f'- "{col}": {formatted_vals}{suffix}')

    return "\n".join(lines)


def debug_prompt_template():
    system_template = """
You are a senior data engineer debugging SQL queries.

Your task:
- Fix the SQL query so it executes successfully.
- Do NOT repeat mistakes from previous attempts.
- Use the debug history to identify patterns or incorrect assumptions.

Rules:
- Return ONLY the corrected SQL query.
- No explanations, no markdown.

Database: {database}
Table:
CREATE TABLE {tbl_name} ({schema})
"""

    user_template = """
User question:
{question}

Previous debug attempts:
{debug_memory}

Latest failed query:
{query}

Error message:
{error}

Based on the history above, fix the query.
"""

    messages = [("system", system_template), ("user", user_template)]

    return ChatPromptTemplate.from_messages(messages)
