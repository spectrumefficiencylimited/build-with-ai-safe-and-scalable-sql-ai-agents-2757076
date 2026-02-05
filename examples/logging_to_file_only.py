"""
Example: Logging to file only (no console output)

This is the solution for storing logs without printing them to console.
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

# Create agent with logging to file only (no console output)
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
    enable_logging=True,              # ← Enable logging
    log_file="logs/agent.log",        # ← Specify log file path
    log_to_console=False,             # ← Disable console output (KEY CHANGE)
)

print("✓ Agent initialized successfully")
print("  Logs are being written to: logs/agent.log")
print("  No logs will appear in console\n")

# Use the agent - logs will be stored in file but not printed
result = agent.ask_question(
    question="How many flights are in the dataset?",
    verbose=False,  # Also disable verbose output
)

if result.success:
    print(f"✓ Query executed successfully")
    print(f"  Result: {result.data.iloc[0, 0]} flights")
else:
    print(f"✗ Query failed: {result.error}")

# Check the log file to see all logged operations
print(f"\nTo view the logs, run:")
print(f"  cat logs/agent.log")
print(f"  # or")
print(f"  tail -f logs/agent.log  # for real-time monitoring")
