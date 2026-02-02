"""
Skills System A/B Test - Complex Question Comparison

This script tests the same complex question with and without skill context
to demonstrate the value of domain knowledge injection.
"""

import sys
import os

# Setup paths
current_dir = os.getcwd()
project_root = os.path.dirname(current_dir) if 'chapter_2' in current_dir else os.getcwd()
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sql_ai_agent.SqlAgent import SqlAgent
from sql_ai_agent.skill_manager import SkillManager
from sql_ai_agent.data import get_ibis_connection

# ===========================================================================
# COMPLEX QUESTION - Tests 5 Key Concepts
# ===========================================================================

complex_question = """
Show me the top 10 low-fare carriers for international flights in 2024,
ranked by total passenger volume. For each airline, also show which
international region they serve the most.

Important: Only count actual passengers (exclude those just connecting
through SFO), and make sure not to double-count passengers from
codeshare flights.
"""

print("=" * 100)
print("SKILLS SYSTEM A/B TEST")
print("=" * 100)
print("\n📋 COMPLEX QUESTION:")
print("-" * 100)
print(complex_question)
print("-" * 100)

# ===========================================================================
# WHAT THIS TESTS (5 Concepts)
# ===========================================================================

print("\n🧩 COMPLEXITY BREAKDOWN:")
print("-" * 100)
print("""
This question tests 5 critical concepts:

1. ✓ ACTIVITY TYPE FILTERING
   - Must exclude 'Thru / Transit' passengers
   - Should filter: "Activity Type Code" IN ('Deplaned', 'Enplaned')
   - Without skill: May include all activity types (wrong totals)

2. ✓ PRICE CATEGORY FILTERING
   - Must filter for 'Low Fare' carriers only
   - Should filter: "Price Category Code" = 'Low Fare'
   - Without skill: May not know this column exists

3. ✓ GEOGRAPHIC FILTERING
   - Must filter for International flights only
   - Should filter: "GEO Summary" = 'International'
   - Need to group by "GEO Region" to find top region per airline
   - Without skill: May not understand GEO Summary vs GEO Region

4. ✓ CODESHARE AWARENESS
   - Must avoid double-counting codeshare flights
   - Should use "Operating Airline" (not "Published Airline")
   - Without skill: May double-count same passengers

5. ✓ COLUMN NAME QUOTING
   - All columns with spaces must be quoted
   - Without skill: Likely syntax errors
""")
print("-" * 100)

# ===========================================================================
# EXPECTED OUTCOMES
# ===========================================================================

print("\n📊 EXPECTED OUTCOMES:")
print("-" * 100)
print("""
WITHOUT SKILL - Likely Issues:
  ❌ May include transit passengers (inflated numbers)
  ❌ May not filter by Price Category (wrong airlines)
  ❌ May not filter by GEO Summary (includes domestic)
  ❌ May use Published Airline (double-counts codeshares)
  ❌ Syntax errors from unquoted column names
  ❌ May not understand how to find "top region per airline"

WITH SKILL - Expected Query:
  ✅ Filters: "Activity Type Code" IN ('Deplaned', 'Enplaned')
  ✅ Filters: "Price Category Code" = 'Low Fare'
  ✅ Filters: "GEO Summary" = 'International'
  ✅ Groups by: "Operating Airline" (avoids codeshare double-counting)
  ✅ Uses window function or subquery to find top "GEO Region" per airline
  ✅ All column names properly quoted
  ✅ Returns accurate top 10 low-fare international carriers
""")
print("-" * 100)

# ===========================================================================
# DATABASE CONNECTION
# ===========================================================================

print("\n🔌 Setting up database connection...")
print("-" * 100)

postgres_config = {
    "user": "postgres",
    "password": "password",
    "host": "postgres",
    "port": 5432,
    "database": "my_db",
}

con = get_ibis_connection(
    backend="postgres",
    postgres_config=postgres_config,
)

print("✓ Connected to database")
print("-" * 100)

# ===========================================================================
# TEST 1: WITHOUT SKILL
# ===========================================================================

print("\n\n" + "=" * 100)
print("TEST 1: WITHOUT SKILL CONTEXT")
print("=" * 100)

agent_no_skill = SqlAgent(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://api.openai.com/v1",
    model="gpt-4o",
    con=con,
    fallback=True,
    fallback_model="gpt-4o-mini",
    tbl_name="air_traffic",
    skill=False,  # ❌ No skill context
    enable_logging=True,
    log_level="INFO",
    log_file="test_no_skill.log",
    log_to_console=False,
)

print("\n🤖 Executing query WITHOUT skill context...")
print("-" * 100)

result_no_skill = agent_no_skill.ask_question(
    question=complex_question,
    verbose=True,
)

# ===========================================================================
# TEST 2: WITH SKILL
# ===========================================================================

print("\n\n" + "=" * 100)
print("TEST 2: WITH SKILL CONTEXT")
print("=" * 100)

agent_with_skill = SqlAgent(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://api.openai.com/v1",
    model="gpt-4o",
    con=con,
    fallback=True,
    fallback_model="gpt-4o-mini",
    tbl_name="air_traffic",
    skill=True,  # ✅ Skill context enabled
    enable_logging=True,
    log_level="INFO",
    log_file="test_with_skill.log",
    log_to_console=False,
)

print("\n🧠 Executing query WITH skill context...")
print("Skill provides: Activity types, Price categories, Geographic fields,")
print("                Codeshare handling, Column quoting, Best practices")
print("-" * 100)

result_with_skill = agent_with_skill.ask_question(
    question=complex_question,
    verbose=True,
)

# ===========================================================================
# COMPARISON ANALYSIS
# ===========================================================================

print("\n\n" + "=" * 100)
print("COMPARISON ANALYSIS")
print("=" * 100)

# Success comparison
print("\n📊 EXECUTION RESULTS:")
print("-" * 100)
print(f"WITHOUT Skill - Success: {result_no_skill.success}")
print(f"WITH Skill    - Success: {result_with_skill.success}")

if not result_no_skill.success:
    print(f"\n❌ No-skill query failed: {result_no_skill.error}")

if not result_with_skill.success:
    print(f"\n❌ Skill query failed: {result_with_skill.error}")

# Query comparison
if result_no_skill.success and result_with_skill.success:
    print("\n✅ Both queries succeeded")

    print(f"\n📏 QUERY LENGTH:")
    print(f"  Without skill: {len(result_no_skill.query)} characters")
    print(f"  With skill:    {len(result_with_skill.query)} characters")

    print(f"\n📊 RESULT SIZE:")
    no_skill_rows = len(result_no_skill.data) if result_no_skill.data is not None else 0
    with_skill_rows = len(result_with_skill.data) if result_with_skill.data is not None else 0
    print(f"  Without skill: {no_skill_rows} rows")
    print(f"  With skill:    {with_skill_rows} rows")

    # Query content analysis
    print(f"\n🔍 QUERY ANALYSIS:")
    print("-" * 100)

    checks = [
        ("Activity Type Filter", "Activity Type Code", "IN ('Deplaned', 'Enplaned')"),
        ("Price Category Filter", "Price Category Code", "Low Fare"),
        ("Geographic Filter", "GEO Summary", "International"),
        ("Operating Airline", "Operating Airline", "GROUP BY"),
        ("Regional Grouping", "GEO Region", None),
    ]

    print("\n{:<30} {:<20} {:<20}".format("Check", "Without Skill", "With Skill"))
    print("-" * 100)

    for check_name, keyword1, keyword2 in checks:
        no_skill_has = keyword1 in result_no_skill.query
        with_skill_has = keyword1 in result_with_skill.query

        if keyword2:
            no_skill_has = no_skill_has and keyword2 in result_no_skill.query
            with_skill_has = with_skill_has and keyword2 in result_with_skill.query

        no_skill_symbol = "✅" if no_skill_has else "❌"
        with_skill_symbol = "✅" if with_skill_has else "❌"

        print("{:<30} {:<20} {:<20}".format(
            check_name,
            f"{no_skill_symbol} {'Present' if no_skill_has else 'Missing'}",
            f"{with_skill_symbol} {'Present' if with_skill_has else 'Missing'}"
        ))

    print("-" * 100)

# ===========================================================================
# DETAILED QUERIES
# ===========================================================================

print("\n\n" + "=" * 100)
print("DETAILED QUERY COMPARISON")
print("=" * 100)

print("\n📝 QUERY WITHOUT SKILL:")
print("-" * 100)
print(result_no_skill.query)
print("-" * 100)

print("\n📝 QUERY WITH SKILL:")
print("-" * 100)
print(result_with_skill.query)
print("-" * 100)

# ===========================================================================
# RESULTS PREVIEW
# ===========================================================================

if result_no_skill.success and result_no_skill.data is not None:
    print("\n\n📊 RESULTS WITHOUT SKILL (Top 5):")
    print("-" * 100)
    print(result_no_skill.data.head())
    print("-" * 100)

if result_with_skill.success and result_with_skill.data is not None:
    print("\n\n📊 RESULTS WITH SKILL (Top 5):")
    print("-" * 100)
    print(result_with_skill.data.head())
    print("-" * 100)

# ===========================================================================
# SUMMARY
# ===========================================================================

print("\n\n" + "=" * 100)
print("SUMMARY")
print("=" * 100)

print("""
The skill provides critical domain knowledge:
  1. Activity Type values and when to exclude transit passengers
  2. Price Category values (Low Fare vs Other)
  3. Geographic fields (GEO Summary for international filtering)
  4. Codeshare explanation (use Operating vs Published Airline)
  5. Column quoting requirements

This enables the LLM to:
  ✓ Generate syntactically correct queries (proper column quoting)
  ✓ Apply correct business logic (exclude transit, avoid double-counting)
  ✓ Use appropriate filters (Low Fare, International)
  ✓ Produce accurate results

Check the detailed logs:
  - test_no_skill.log    (without skill context)
  - test_with_skill.log  (with skill context)
""")

print("=" * 100)
