"""
Test script to validate logging functionality with and without console output.

This script demonstrates:
1. Logging to file only (no console output)
2. Logging to both file and console
3. How verbose parameter works as fallback when logging is disabled
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
temperature = 0
max_token = 10000

print("=" * 80)
print("TEST 1: Logging to file only (no console output)")
print("=" * 80)

# Create agent with logging enabled but console output disabled
agent_file_only = SqlAgent(
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
    log_file="logs/agent_file_only.log",
    log_to_console=False,  # ← KEY: Disable console output
)

print("\n✓ Agent initialized with log_to_console=False")
print("  Logs will be written to: logs/agent_file_only.log")
print("  No logs should appear in console below this line:\n")

# Ask a simple question (logs should NOT appear in console)
result = agent_file_only.ask_question(
    question="How many flights are in the dataset?",
    verbose=False,  # Also disable verbose output
)

print(f"\n✓ Query executed successfully")
print(f"  Result shape: {result.data.shape if result.success else 'Failed'}")

print("\n" + "=" * 80)
print("TEST 2: Logging to both file and console")
print("=" * 80)

# Create agent with logging to both console and file
agent_both = SqlAgent(
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
    log_file="logs/agent_both.log",
    log_to_console=True,  # ← Enable console output
)

print("\n✓ Agent initialized with log_to_console=True")
print("  Logs will appear in console AND be written to: logs/agent_both.log\n")

# Ask a question (logs SHOULD appear in console)
result = agent_both.ask_question(
    question="What are the top 5 destination airports?",
    verbose=False,
)

print(f"\n✓ Query executed")

print("\n" + "=" * 80)
print("TEST 3: Verbose mode (fallback when logging disabled)")
print("=" * 80)

# Create agent without logging but with verbose mode
agent_verbose = SqlAgent(
    api_key=api_key,
    base_url=base_url,
    model=model,
    con=con,
    fallback=True,
    fallback_model=fallback_model,
    tbl_name=tbl_name,
    memory=False,
    enable_logging=False,  # ← Logging disabled
)

print("\n✓ Agent initialized with enable_logging=False")
print("  Using verbose=True as fallback for status messages\n")

# Ask a question with verbose mode
result = agent_verbose.ask_question(
    question="Show me 5 flights",
    verbose=True,  # ← This will print status messages
)

print(f"\n✓ Query completed")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("""
The verbose parameter controls console output as follows:

1. When enable_logging=True:
   - log_to_console=False → Logs go to file only, no console output
   - log_to_console=True  → Logs go to both file and console
   - verbose parameter is ignored (logger takes precedence)

2. When enable_logging=False:
   - verbose=True  → Print status messages to console
   - verbose=False → Silent operation

Check the log files:
  - logs/agent_file_only.log
  - logs/agent_both.log
""")
