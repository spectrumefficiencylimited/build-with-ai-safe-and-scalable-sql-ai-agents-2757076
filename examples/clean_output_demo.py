"""
Demo: Clean output display with verbose mode and detailed logging

This demonstrates the improved output formatting:
1. Clean console output when using verbose=True
2. Detailed information stored in logs
3. Different display options for QueryOutput
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
print("EXAMPLE 1: Verbose mode with clean output (no logging)")
print("=" * 80)

# Create agent without logging
agent = SqlAgent(
    api_key=api_key,
    base_url=base_url,
    model=model,
    con=con,
    fallback=True,
    fallback_model=fallback_model,
    tbl_name=tbl_name,
    memory=False,
    enable_logging=False,  # No logging
)

# Ask question with verbose=True - will display clean output automatically
result = agent.ask_question(
    question="How many passengers landed during 2024?",
    verbose=True,  # Clean output will be printed automatically
)

# If you still want to access the result programmatically:
if result.success:
    print(f"✓ Retrieved {len(result.data)} rows")

print("\n" + "=" * 80)
print("EXAMPLE 2: With logging enabled (detailed info in logs)")
print("=" * 80)

# Create agent with logging to file only
agent_logged = SqlAgent(
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
    log_file="logs/detailed_logs.log",
    log_to_console=False,  # Logs to file, not console
    log_level="DEBUG",  # Capture detailed LLM responses
)

# Ask question - detailed info goes to log file
result = agent_logged.ask_question(
    question="What are the top 5 destination airports by passenger count?",
    verbose=False,  # No console output (logger takes precedence)
)

print("\n✓ Query executed (check logs/detailed_logs.log for details)")
print("  The log file contains:")
print("  - Full LLM request and response")
print("  - Query execution details")
print("  - Timing information")
print("  - All debug attempts (if any)")

# You can still manually display the result
print("\nManually displaying result:")
result.display(max_rows=5)

print("\n" + "=" * 80)
print("EXAMPLE 3: Custom display options")
print("=" * 80)

result = agent.ask_question(
    question="Count flights by airline, show top 10",
    verbose=False,  # Don't auto-display
)

# Custom display options
print("\n1. Show only the query:")
result.display(show_query=True, show_data=False)

print("\n2. Show only the data (first 3 rows):")
result.display(show_query=False, show_data=True, max_rows=3)

print("\n3. Show everything (default):")
result.display()

print("\n" + "=" * 80)
print("EXAMPLE 4: Clean __repr__ for interactive shells")
print("=" * 80)

result = agent.ask_question(
    question="How many flights in total?",
    verbose=False,
)

# In Jupyter or Python REPL, this will show clean output instead of ugly dataclass dump
print("\nClean representation (what you see in REPL):")
print(repr(result))

print("\nDetailed display:")
result.display()

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("""
New features:

1. Clean console output with verbose=True
   - Query and results displayed in a readable format
   - Automatically shown when verbose=True and logging is disabled

2. Detailed logging
   - LLM requests/responses logged at DEBUG level
   - Query execution details logged at INFO level
   - All information stored in log file

3. Clean __repr__ for interactive shells
   - Shows "QueryOutput(success=True, rows=X, cols=Y)" instead of full dataclass dump
   - Much cleaner in Jupyter notebooks and Python REPL

4. Flexible display options
   - result.display() for manual control
   - Customize what to show and how many rows

Usage:
  - verbose=True (no logging) → Clean output to console
  - enable_logging=True + log_to_console=False → Details to file only
  - Both combined → Clean output + detailed logs
""")
