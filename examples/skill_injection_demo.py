"""
Demonstration of skill injection feature in SqlAgent

This example shows how to use the skill parameter to automatically
inject domain knowledge into the SQL AI agent's context.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sql_ai_agent.SqlAgent import SqlAgent
import ibis

print("=" * 80)
print("SKILL INJECTION DEMO")
print("=" * 80)

# Note: This is a demonstration of the skill parameter
# For actual execution, you'll need to configure your database connection
# and provide valid API credentials

print("\n1. Initialize SqlAgent WITHOUT skill")
print("-" * 80)

# Example without skill
try:
    agent_no_skill = SqlAgent(
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key"),
        base_url="https://api.openai.com/v1",
        model="gpt-4o",
        fallback=True,
        fallback_model="gpt-4o-mini",
        con=None,  # Replace with actual ibis connection
        tbl_name="air_traffic",
        skill=False,  # Skill disabled
        enable_logging=True,
        log_level="INFO",
    )
    print("✓ Agent initialized without skill")
except Exception as e:
    print(f"Note: This is a demo - actual execution requires database connection")
    print(f"Configuration shown: skill=False")

print("\n2. Initialize SqlAgent WITH skill")
print("-" * 80)

# Example with skill
try:
    agent_with_skill = SqlAgent(
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key"),
        base_url="https://api.openai.com/v1",
        model="gpt-4o",
        fallback=True,
        fallback_model="gpt-4o-mini",
        con=None,  # Replace with actual ibis connection
        tbl_name="air_traffic",
        skill=True,  # Skill enabled - will auto-load skill for table
        enable_logging=True,
        log_level="INFO",
    )
    print("✓ Agent initialized with skill")
except Exception as e:
    print(f"Note: This is a demo - actual execution requires database connection")
    print(f"Configuration shown: skill=True")

print("\n3. Initialize SqlAgent with custom skills directory")
print("-" * 80)

# Example with custom skills directory
try:
    agent_custom_dir = SqlAgent(
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key"),
        base_url="https://api.openai.com/v1",
        model="gpt-4o",
        fallback=True,
        fallback_model="gpt-4o-mini",
        con=None,  # Replace with actual ibis connection
        tbl_name="air_traffic",
        skill=True,  # Skill enabled
        skills_dir="/path/to/custom/skills",  # Custom skills directory
        enable_logging=True,
        log_level="INFO",
    )
    print("✓ Agent initialized with custom skills directory")
except Exception as e:
    print(f"Note: This is a demo - actual execution requires database connection")
    print(f"Configuration shown: skill=True, skills_dir='/path/to/custom/skills'")

print("\n" + "=" * 80)
print("HOW IT WORKS")
print("=" * 80)

print("""
When skill=True, SqlAgent automatically:

1. Initializes a SkillManager with the specified skills_dir (or default location)

2. Tries to load a skill file matching the table name using these patterns:
   - {table_name}.md
   - {table_name}_context.md
   - sfo_{table_name}_context.md

3. For table "air_traffic", it will try:
   - air_traffic.md
   - air_traffic_context.md
   - sfo_air_traffic_context.md  ✓ (This exists!)

4. If a skill is found, it's automatically injected into every query's
   additional_context, just like distinct_char_values

5. The skill provides domain-specific knowledge about:
   - Dataset structure and column definitions
   - Data characteristics and quirks
   - Common query patterns and best practices
   - Business context and sample queries

USAGE EXAMPLE:
""")

print("""
from sql_ai_agent.SqlAgent import SqlAgent
import ibis

# Connect to database
con = ibis.postgres.connect(
    user="postgres",
    password="password",
    host="postgres",
    port=5432,
    database="my_db",
)

# Initialize agent WITH skill
agent = SqlAgent(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://api.openai.com/v1",
    model="gpt-4o",
    con=con,
    fallback=True,
    fallback_model="gpt-4o-mini",
    tbl_name="air_traffic",
    skill=True,  # 🔑 Enable skill injection
)

# Ask question - skill context is automatically included!
result = agent.ask_question(
    question="What are the top 5 airlines by passenger count in 2024?",
    verbose=True
)

# The LLM receives both the schema AND the domain knowledge from the skill
# This results in more accurate queries that:
# - Use proper column names
# - Apply correct filters (e.g., excluding transit passengers)
# - Handle data quirks (e.g., codeshare flights)
# - Follow best practices for the dataset
""")

print("=" * 80)
print("\nSee skills/README.md for more information on creating and using skills")
print("=" * 80)
