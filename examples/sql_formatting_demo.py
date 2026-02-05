"""
Demo: SQL Query Formatting with SqlGlot

This demonstrates how SqlGlot is used to format and indent SQL queries
for better readability in the console output.
"""

import ibis
import sys
import os

# Add project root to path
current_dir = os.getcwd()
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sql_ai_agent.SqlAgent import SqlAgent

# Database connection
con = ibis.postgres.connect(
    user="postgres",
    password="password",
    host="postgres",
    port=5432,
    database="my_db",
)

tbl_name = "air_traffic"

base_url = "https://api.openai.com/v1"
api_key = os.getenv("OPENAI_API_KEY")
model = "gpt-4o"
fallback_model = "gpt-4o-mini"

# Create agent with logging to file only
agent = SqlAgent(
    api_key=api_key,
    base_url=base_url,
    model=model,
    con=con,
    fallback=True,
    fallback_model=fallback_model,
    tbl_name=tbl_name,
    memory=True,
    memory_size=3,
    enable_logging=True,
    log_file="logs/formatted_queries.log",
    log_to_console=False,
    log_level="INFO",
)

print("=" * 80)
print("SQL QUERY FORMATTING DEMO")
print("=" * 80)
print("\nSqlGlot automatically formats SQL queries for better readability.\n")

# Example 1: Simple aggregation
print("\n" + "=" * 80)
print("EXAMPLE 1: Simple Aggregation")
print("=" * 80)

result = agent.ask_question(
    question="How many passengers traveled in total?",
    verbose=True,
)

# Example 2: Complex query with joins and grouping
print("\n" + "=" * 80)
print("EXAMPLE 2: Group By Query")
print("=" * 80)

result = agent.ask_question(
    question="Show me the top 5 airlines by total passenger count",
    verbose=True,
)

# Example 3: Filtering with WHERE clause
print("\n" + "=" * 80)
print("EXAMPLE 3: Filtered Query")
print("=" * 80)

result = agent.ask_question(
    question="How many passengers departed from Terminal 1 in 2024?",
    verbose=True,
)

# Example 4: Multiple aggregations
print("\n" + "=" * 80)
print("EXAMPLE 4: Multiple Aggregations")
print("=" * 80)

result = agent.ask_question(
    question="Show the total and average passenger count by terminal",
    verbose=True,
)

print("\n" + "=" * 80)
print("BENEFITS OF SQL FORMATTING")
print("=" * 80)
print("""
SqlGlot formatting provides:

1. Consistent indentation
   - Clauses are properly aligned
   - Nested queries are indented

2. Better readability
   - Keywords are on separate lines when appropriate
   - Complex queries are easier to understand

3. Debugging friendly
   - Errors are easier to spot
   - Query structure is clear at a glance

4. Professional output
   - Clean, well-formatted SQL
   - Suitable for documentation or sharing

The formatting happens automatically whenever verbose=True or when
you manually call result.display().

If SqlGlot cannot parse a query (rare edge cases), it falls back to
displaying the original unformatted query.
""")

print("\n✓ All detailed information is logged to: logs/formatted_queries.log")
