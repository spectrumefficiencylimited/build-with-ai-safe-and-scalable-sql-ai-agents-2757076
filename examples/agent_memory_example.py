"""
Example: Using Agent Memory for Interactive Data Exploration

This example demonstrates how to use the conversation memory feature
to build interactive, multi-turn data exploration sessions.
"""

import ibis
import pandas as pd
from sql_ai_agent.SqlAgent import SqlAgent
from sql_ai_agent.llm_config_loader import load_config

# Load configuration
config = load_config()
memory_config = config.get_memory_config()

# Get LLM provider settings (using OpenAI as example)
provider = 'openai'
api_key = config.get_api_key(provider)
base_url = config.get_base_url(provider)
model = config.get_default_model(provider)
fallback_model = config.get_fallback_model(provider)

# Setup database connection
con = ibis.duckdb.connect()

# Load sample data
df = pd.read_csv("data/air_traffic.csv")
con.create_table("air_traffic", df, overwrite=True)

print("=" * 60)
print("Example 1: Agent WITH Memory (Interactive Exploration)")
print("=" * 60)

# Create agent with memory enabled
agent_with_memory = SqlAgent(
    api_key=api_key,
    base_url=base_url,
    model=model,
    con=con,
    tbl_name="air_traffic",
    fallback=True,
    fallback_model=fallback_model,
    # Enable memory for conversational interaction
    memory=True,
    memory_size=10,  # Keep last 10 Q&A pairs
    # Security
    read_only=True,
)

# Check initial memory state
print(f"\nInitial memory state: {agent_with_memory.get_memory_info()}")

# Interactive conversation - each question builds on previous context
print("\nQ1: What's the total passenger count?")
result1 = agent_with_memory.ask_question(
    "What's the total passenger count?",
    verbose=False
)
print(f"SQL: {result1.query}")
print(f"Result: {result1.data}")

print("\nQ2: Break that down by year")
result2 = agent_with_memory.ask_question(
    "Break that down by year",  # "that" references Q1
    verbose=False
)
print(f"SQL: {result2.query}")
print(f"Result:\n{result2.data}")

print("\nQ3: Show only years with over 5 million passengers")
result3 = agent_with_memory.ask_question(
    "Show only years with over 5 million passengers",
    verbose=False
)
print(f"SQL: {result3.query}")
print(f"Result:\n{result3.data}")

print("\nQ4: Sort that by passenger count descending")
result4 = agent_with_memory.ask_question(
    "Sort that by passenger count descending",  # References Q3 result
    verbose=False
)
print(f"SQL: {result4.query}")
print(f"Result:\n{result4.data}")

# Check memory state after conversation
print(f"\nFinal memory state: {agent_with_memory.get_memory_info()}")

print("\n" + "=" * 60)
print("Example 2: Agent WITHOUT Memory (Independent Queries)")
print("=" * 60)

# Create agent without memory
agent_no_memory = SqlAgent(
    api_key=api_key,
    base_url=base_url,
    model=model,
    con=con,
    tbl_name="air_traffic",
    fallback=True,
    fallback_model=fallback_model,
    # Disable memory
    memory=False,
    read_only=True,
)

print("\nQ1: What's the total passenger count?")
result1 = agent_no_memory.ask_question(
    "What's the total passenger count?",
    verbose=False
)
print(f"SQL: {result1.query}")

print("\nQ2: Break that down by year")
result2 = agent_no_memory.ask_question(
    "Break that down by year",  # "that" has NO context - may fail or be generic
    verbose=False
)
print(f"SQL: {result2.query}")
# This might generate a generic query without passenger count context

print("\n" + "=" * 60)
print("Example 3: Managing Memory Manually")
print("=" * 60)

agent = SqlAgent(
    api_key=api_key,
    base_url=base_url,
    model=model,
    con=con,
    tbl_name="air_traffic",
    fallback=True,
    fallback_model=fallback_model,
    memory=True,
    memory_size=5,  # Small memory for demonstration
)

# Topic 1: Passenger analysis
print("\n--- Topic 1: Passenger Analysis ---")
agent.ask_question("Show passenger counts by year")
agent.ask_question("Which year had the highest count?")
agent.ask_question("Show the percentage growth year over year")

print(f"Memory state: {agent.get_memory_info()}")

# Clear memory before changing topics
print("\n--- Clearing memory before topic change ---")
agent.clear_memory()
print(f"Memory state after clear: {agent.get_memory_info()}")

# Topic 2: Airport analysis
print("\n--- Topic 2: Airport Analysis ---")
agent.ask_question("How many unique airports are there?")
agent.ask_question("Which airport had the most passengers?")

print(f"Memory state: {agent.get_memory_info()}")

print("\n" + "=" * 60)
print("Example 4: Loading Memory Config from YAML")
print("=" * 60)

# Load memory settings from llm_config.yaml
memory_config = config.get_memory_config()
print(f"\nMemory config from YAML: {memory_config}")

agent_from_config = SqlAgent(
    api_key=api_key,
    base_url=base_url,
    model=model,
    con=con,
    tbl_name="air_traffic",
    fallback=True,
    fallback_model=fallback_model,
    # Use config values
    memory=memory_config['memory'],
    memory_size=memory_config['memory_size'],
)

print(f"Agent memory enabled: {agent_from_config.memory_enabled}")
print(f"Agent memory size: {agent_from_config.memory_size}")

print("\n" + "=" * 60)
print("Example 5: Monitoring Memory Usage")
print("=" * 60)

agent = SqlAgent(
    api_key=api_key,
    base_url=base_url,
    model=model,
    con=con,
    tbl_name="air_traffic",
    fallback=True,
    fallback_model=fallback_model,
    memory=True,
    memory_size=3,  # Very small to demonstrate trimming
)

# Ask several questions to exceed memory limit
for i in range(5):
    question = f"Query {i+1}: Show sample data with limit {i+1}"
    agent.ask_question(question, verbose=False)

    info = agent.get_memory_info()
    print(f"\nAfter Q{i+1}:")
    print(f"  Current pairs: {info['current_pairs']}/{info['memory_size_limit']}")
    print(f"  Memory full: {info['memory_full']}")

    if info['memory_full']:
        print("  ⚠️  Memory at capacity - oldest messages will be dropped")

print("\n" + "=" * 60)
print("All examples completed!")
print("=" * 60)

# Cleanup
print("\nFor more information, see:")
print("- docs/agent-memory-best-practices.md")
print("- docs/sql-validation-guide.md")
