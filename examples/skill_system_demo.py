"""
Example: Using Skills with SQL AI Agent

This example demonstrates how to load and use domain-specific skills
to provide better context to the SQL AI agent.
"""

import sys
import os

# Add project root to path
current_dir = os.getcwd()
project_root = os.path.dirname(current_dir) if 'examples' in current_dir else current_dir
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sql_ai_agent.skill_manager import SkillManager, format_skill_for_prompt

# Initialize the skill manager
skill_manager = SkillManager()

print("=" * 80)
print("SQL AI AGENT - SKILLS SYSTEM DEMO")
print("=" * 80)

# List available skills
print("\n📚 Available Skills:")
print("-" * 80)
skills = skill_manager.list_skills()
for skill in skills:
    summary = skill_manager.get_skill_summary(skill)
    print(f"\n✓ {skill}")
    print(f"  {summary[:100]}...")

# Load the SFO Air Traffic skill
print("\n\n" + "=" * 80)
print("LOADING SKILL: SFO Air Traffic Context")
print("=" * 80)

sfo_skill = skill_manager.load_skill("sfo_air_traffic_context")
print(f"\n✓ Skill loaded successfully")
print(f"  Content size: {len(sfo_skill):,} characters")
print(f"  Content lines: {len(sfo_skill.splitlines())} lines")

# Preview the skill content
print("\n" + "-" * 80)
print("SKILL PREVIEW (first 1000 characters):")
print("-" * 80)
print(sfo_skill[:1000])
print("...\n")

# Show how it would be formatted for prompt injection
print("\n" + "=" * 80)
print("FORMATTED FOR PROMPT INJECTION")
print("=" * 80)

formatted_skill = format_skill_for_prompt(
    sfo_skill,
    prefix="Domain Knowledge: SFO Air Traffic Dataset"
)

print(f"\n✓ Formatted skill ready for injection")
print(f"  Total size: {len(formatted_skill):,} characters")
print("\nPreview of formatted content:")
print("-" * 80)
print(formatted_skill[:500])
print("...\n")

# Example: How to use with additional context parameter
print("\n" + "=" * 80)
print("USAGE EXAMPLE WITH SQL AI AGENT")
print("=" * 80)

example_code = """
# Load the skill
skill_manager = SkillManager()
sfo_skill = skill_manager.load_skill("sfo_air_traffic_context")

# Option 1: Add to additional_context parameter
result = agent.ask_question(
    question="What are the top 5 airlines by passenger count in 2024?",
    additional_context=sfo_skill,
    verbose=True
)

# Option 2: Use formatted version
formatted_skill = format_skill_for_prompt(sfo_skill)
result = agent.ask_question(
    question="Show me international traffic trends by region",
    additional_context=formatted_skill,
    verbose=True
)

# Option 3: Combine with other context
custom_context = \"\"\"
Focus on:
- International flights only
- Last 12 months
- Exclude transit passengers
\"\"\"

result = agent.ask_question(
    question="Which regions had the most growth?",
    additional_context=f"{sfo_skill}\\n\\n{custom_context}",
    verbose=True
)
"""

print(example_code)

# Show expected benefits
print("\n" + "=" * 80)
print("EXPECTED BENEFITS OF USING SKILLS")
print("=" * 80)
print("""
✓ Better understanding of column meanings and relationships
✓ Awareness of data quirks (e.g., codeshare flights, NULL values)
✓ More accurate query patterns (e.g., proper activity type filtering)
✓ Correct handling of aggregations (avoiding double-counting)
✓ Use of best practices (e.g., quoting column names with spaces)
✓ Knowledge of common business questions and their SQL patterns
✓ Understanding of data grain and aggregation level
✓ Awareness of temporal aspects (monthly granularity, date format)
""")

# Demonstrate skill cache efficiency
print("\n" + "=" * 80)
print("SKILL CACHING DEMONSTRATION")
print("=" * 80)

import time

# First load (from file)
start = time.time()
skill1 = skill_manager.load_skill("sfo_air_traffic_context")
time1 = (time.time() - start) * 1000

# Second load (from cache)
start = time.time()
skill2 = skill_manager.load_skill("sfo_air_traffic_context")
time2 = (time.time() - start) * 1000

print(f"\n✓ First load (from file):  {time1:.3f}ms")
print(f"✓ Second load (from cache): {time2:.3f}ms")
print(f"✓ Speedup: {time1/time2:.1f}x faster")

# Clear cache example
print("\n✓ Cache can be cleared with: skill_manager.clear_cache()")

print("\n" + "=" * 80)
print("NEXT STEPS")
print("=" * 80)
print("""
1. Test the skill with actual queries to the SQL AI agent
2. Measure improvement in query quality and accuracy
3. Create additional skills for other datasets
4. Consider selective skill loading based on query context
5. Integrate skill selection into the agent initialization
6. Add skill versioning for tracking changes
""")
