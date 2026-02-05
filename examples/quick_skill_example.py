"""
Quick Example: Using the Skill Parameter

This example shows the simplest way to use the new skill parameter.
"""

from sql_ai_agent.SqlAgent import SqlAgent
import ibis
import os

# 1. Connect to database
con = ibis.postgres.connect(
    user="postgres",
    password="password",
    host="postgres",
    port=5432,
    database="my_db",
)

# 2. Initialize agent WITH skill (NEW FEATURE!)
agent = SqlAgent(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://api.openai.com/v1",
    model="gpt-4o",
    con=con,
    fallback=True,
    fallback_model="gpt-4o-mini",
    tbl_name="air_traffic",

    # 🆕 NEW PARAMETERS
    skill=True,              # Enable automatic skill loading
    skills_dir=None,         # Use default location (optional)

    # Optional: Enable logging to see skill loading
    enable_logging=True,
    log_level="INFO",
)

# 3. Ask question - skill is automatically injected!
result = agent.ask_question(
    question="What are the top 5 airlines by passenger count in 2024?",
    verbose=True
)

# That's it! The skill is automatically loaded and injected into the prompt.
# The LLM now has domain knowledge about:
# - Column definitions and meanings
# - Data characteristics (codeshares, NULL values, etc.)
# - Best practices for querying this dataset
# - Common pitfalls to avoid

print(result)
