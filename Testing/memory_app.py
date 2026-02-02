import ibis
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Add project root to path
# Get the directory of this file, then go up one level to project root
import sys
import os
from pathlib import Path

# Path to this file
current_file = Path(__file__).resolve()

# /workspace
project_root = current_file.parents[1]

sys.path.insert(0, str(project_root))

from sql_ai_agent.db_handler import get_tbl_attr
from sql_ai_agent.db_handler import get_character_distinct_values
from sql_ai_agent.prompt_handler import format_distinct_values_for_prompt

con = ibis.postgres.connect(
    user="postgres",
    password="password",
    host="postgres",
    port=5432,
    database="my_db",
)
tbl_name = "air_traffic"

tbl_attr = get_tbl_attr(con=con, tbl_name=tbl_name)
schema = tbl_attr.schema


base_url = "https://api.openai.com/v1"
api_key = os.getenv("OPENAI_API_KEY")
model = "gpt-4o"
llm = ChatOpenAI(base_url=base_url, api_key=api_key, temperature=0, model=model)


system_template = """
Given the following SQL table, your job is to write queries given a user’s request.
Return just the SQL query as plain text, without additional text, and don't use markdown format.
Please ensure that the field names in the query are enclosed in double quotes.

{additional_context}

CREATE TABLE {tbl_name} ({schema})

""".strip()


user_template = "Write a SQL query that returns: {question}"

messages = [("system", system_template), ("user", user_template)]

prompt_template = ChatPromptTemplate.from_messages(messages)

chain = prompt_template | llm


def basic_sql_agent(chain, question, tbl_name, schema, con, additional_context=""):
    distinct_values = get_character_distinct_values(
        con=con, tbl_schema=tbl_attr, tbl_name=tbl_name
    )
    distinct_values_formatted = format_distinct_values_for_prompt(distinct_values)
    additional_context = additional_context + "\n" + distinct_values_formatted

    llm_output = chain.invoke(
        {
            "question": question,
            "tbl_name": tbl_name,
            "schema": schema,
            "additional_context": additional_context,
        }
    )
    query = llm_output.content

    return query


def format_memory_for_prompt(memory):
    if not memory:
        return ""

    lines = ["Previous conversation:"]
    for msg in memory:
        role = msg["role"].capitalize()
        content = msg["content"]
        lines.append(f"{role}: {content}")

    return "\n".join(lines)


memory = []


while True:
    question = input("Question: ")
    if question == "quit":
        break
    memory_context = format_memory_for_prompt(memory)

    query = basic_sql_agent(
        chain,
        question=question,
        tbl_name=tbl_name,
        schema=schema,
        additional_context=memory_context,
        con=con,
    )
    memory.append({"role": "user", "content": question})
    memory.append({"role": "assistant", "content": query})
    output = con.sql(query).execute()

    print(f"AI: \n Query: \n {query} \n Output: \n {output} ")
