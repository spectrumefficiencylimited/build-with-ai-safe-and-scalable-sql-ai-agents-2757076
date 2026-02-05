"""
Visual comparison: Before and After SQL Formatting

This shows what the SQL output looks like with SqlGlot formatting.
"""

import sqlglot

# Example queries (as they might come from the LLM)
queries = [
    # Simple query
    'SELECT COUNT(*) FROM "air_traffic" LIMIT 10000',

    # Query with WHERE
    'SELECT SUM("Passenger Count") FROM "air_traffic" WHERE EXTRACT(YEAR FROM "Date") = 2024',

    # Query with GROUP BY
    'SELECT "Operating Airline", SUM("Passenger Count") as total_passengers FROM "air_traffic" GROUP BY "Operating Airline" ORDER BY total_passengers DESC LIMIT 5',

    # Complex query with multiple clauses
    'SELECT "Terminal", "Activity Type Code", COUNT(*) as flight_count, SUM("Passenger Count") as total_passengers, AVG("Passenger Count") as avg_passengers FROM "air_traffic" WHERE "Terminal" IS NOT NULL GROUP BY "Terminal", "Activity Type Code" ORDER BY total_passengers DESC LIMIT 10',
]

print("=" * 80)
print("SQL FORMATTING COMPARISON")
print("=" * 80)

for i, query in enumerate(queries, 1):
    print(f"\n{'=' * 80}")
    print(f"EXAMPLE {i}")
    print(f"{'=' * 80}")

    print("\n📝 BEFORE (Raw LLM Output):")
    print("-" * 80)
    print(query)

    print("\n✨ AFTER (SqlGlot Formatted):")
    print("-" * 80)
    formatted = sqlglot.prettify(query)
    print(formatted)
    print()

print("=" * 80)
print("KEY IMPROVEMENTS")
print("=" * 80)
print("""
1. Keywords on separate lines (SELECT, FROM, WHERE, etc.)
2. Proper indentation for readability
3. Consistent spacing and alignment
4. Column lists are easier to read
5. Complex conditions are more visible
6. Overall structure is clearer

This formatting is automatically applied when you use:
  - agent.ask_question(..., verbose=True)
  - result.display()
""")
