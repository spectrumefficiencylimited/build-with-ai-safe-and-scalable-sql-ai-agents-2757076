"""
Updated Example: Clean output with verbose=True (works with or without logging)

This demonstrates that verbose=True now displays clean output regardless of logging status.
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

print("=" * 80)
print("EXAMPLE 1: verbose=True WITHOUT logging (clean output only)")
print("=" * 80)

agent1 = SqlAgent(
    api_key=api_key,
    base_url=base_url,
    model=model,
    con=con,
    fallback=True,
    fallback_model=fallback_model,
    tbl_name=tbl_name,
    enable_logging=False,  # No logging
)

# Clean output displayed automatically
result = agent1.ask_question(
    question="How many passengers landed during 2024?",
    verbose=True,  # ← Display clean output
)

print("\n" + "=" * 80)
print("EXAMPLE 2: verbose=True WITH logging (clean output + detailed logs)")
print("=" * 80)

agent2 = SqlAgent(
    api_key=api_key,
    base_url=base_url,
    model=model,
    con=con,
    fallback=True,
    fallback_model=fallback_model,
    tbl_name=tbl_name,
    memory=True,
    memory_size=3,
    enable_logging=True,           # ← Logging enabled
    log_file="logs/agent.log",     # ← Detailed logs go here
    log_to_console=False,          # ← Don't print log messages to console
    log_level="DEBUG",             # ← Capture LLM requests/responses
)

# Clean output displayed to console, detailed info logged to file
result = agent2.ask_question(
    question="What are the top 5 destination airports?",
    verbose=True,  # ← Display clean output (works even with logging enabled!)
)

print("\n✓ Check logs/agent.log for detailed information:")
print("  - Full LLM request and response")
print("  - Query execution timing")
print("  - Validation details")

print("\n" + "=" * 80)
print("EXAMPLE 3: verbose=False (silent operation, can still access result)")
print("=" * 80)

# No output displayed, but detailed logs are still written
result = agent2.ask_question(
    question="How many flights in total?",
    verbose=False,  # ← No console output
)

# Process result programmatically
if result.success:
    print(f"✓ Query executed silently")
    print(f"  Result: {result.data.iloc[0, 0]} total flights")
    print(f"  (check logs/agent.log for details)")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("""
New behavior:

verbose=True  → ALWAYS displays clean, formatted output to console
              (regardless of logging configuration)

verbose=False → Silent operation, no console output
              (but logs are still written if logging is enabled)

This gives you the best of both worlds:
- Clean, readable output on console (when you want it)
- Detailed information in log files (for debugging/auditing)

Configuration:
  enable_logging=True + log_to_console=False + verbose=True

  Result:
  - Clean formatted output on console (via verbose)
  - Detailed logs in file (via enable_logging)
  - No log messages cluttering console (via log_to_console=False)
""")
