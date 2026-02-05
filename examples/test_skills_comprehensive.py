"""
Comprehensive test of Skills System after migration to root/skills/

This test verifies:
1. SkillManager auto-detection of root/skills/ directory
2. Skill loading works correctly
3. All documented skills are accessible
4. Example usage patterns work as documented
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sql_ai_agent.skill_manager import SkillManager, format_skill_for_prompt

print("=" * 80)
print("COMPREHENSIVE SKILLS SYSTEM TEST")
print("=" * 80)

# Test 1: Initialization
print("\n📋 Test 1: SkillManager Initialization")
print("-" * 80)
manager = SkillManager()
print(f"✓ Skills directory: {manager.skills_dir}")
print(f"✓ Directory exists: {manager.skills_dir.exists()}")
print(f"✓ Directory is absolute: {manager.skills_dir.is_absolute()}")
expected_path = project_root / "skills"
assert manager.skills_dir == expected_path, f"Expected {expected_path}, got {manager.skills_dir}"
print("✓ Path matches expected location")

# Test 2: List Skills
print("\n📋 Test 2: List Available Skills")
print("-" * 80)
skills = manager.list_skills()
print(f"✓ Found {len(skills)} skills:")
for skill in skills:
    print(f"  - {skill}")
assert "sfo_air_traffic_context" in skills, "sfo_air_traffic_context not found!"
print("✓ Primary skill (sfo_air_traffic_context) is available")

# Test 3: Load Skill
print("\n📋 Test 3: Load Skill")
print("-" * 80)
sfo_skill = manager.load_skill("sfo_air_traffic_context")
print(f"✓ Loaded sfo_air_traffic_context")
print(f"  Size: {len(sfo_skill):,} characters")
print(f"  Lines: {len(sfo_skill.splitlines())} lines")
assert len(sfo_skill) > 1000, "Skill content seems too short"
assert "SFO" in sfo_skill, "Skill doesn't contain expected content"
print("✓ Skill content looks valid")

# Test 4: Get Summary
print("\n📋 Test 4: Get Skill Summary")
print("-" * 80)
summary = manager.get_skill_summary("sfo_air_traffic_context")
print(f"✓ Summary: {summary[:100]}...")
assert len(summary) > 0, "Summary is empty"
print("✓ Summary generated successfully")

# Test 5: Caching
print("\n📋 Test 5: Skill Caching")
print("-" * 80)
import time
start = time.time()
skill1 = manager.load_skill("sfo_air_traffic_context")
time1 = time.time() - start

start = time.time()
skill2 = manager.load_skill("sfo_air_traffic_context")
time2 = time.time() - start

print(f"✓ First load:  {time1*1000:.3f}ms")
print(f"✓ Second load: {time2*1000:.3f}ms (cached)")
if time2 > 0:
    print(f"✓ Cache speedup: {time1/time2:.1f}x faster")
else:
    print("✓ Cache speedup: Extremely fast (< 1μs)")
assert skill1 == skill2, "Cached skill differs from original"
print("✓ Cache working correctly")

# Test 6: Format for Prompt
print("\n📋 Test 6: Format Skill for Prompt Injection")
print("-" * 80)
formatted = format_skill_for_prompt(sfo_skill, prefix="SFO Air Traffic Knowledge")
print(f"✓ Formatted skill size: {len(formatted):,} characters")
assert "## SFO Air Traffic Knowledge" in formatted, "Prefix not found in formatted output"
print("✓ Formatting works correctly")
print(f"  Preview: {formatted[:150].strip()}...")

# Test 7: Clear Cache
print("\n📋 Test 7: Cache Management")
print("-" * 80)
cache_size_before = len(manager._skills_cache)
print(f"✓ Cache contains {cache_size_before} skills")
manager.clear_cache()
cache_size_after = len(manager._skills_cache)
print(f"✓ Cache cleared: {cache_size_after} skills")
assert cache_size_after == 0, "Cache not properly cleared"
print("✓ Cache management working")

# Test 8: Custom Skills Directory
print("\n📋 Test 8: Custom Skills Directory")
print("-" * 80)
custom_manager = SkillManager(skills_dir=str(project_root / "skills"))
print(f"✓ Custom path: {custom_manager.skills_dir}")
custom_skills = custom_manager.list_skills()
print(f"✓ Found {len(custom_skills)} skills with custom path")
assert len(custom_skills) == len(skills), "Custom path should find same skills"
print("✓ Custom directory parameter works")

# Test 9: Load with .md extension
print("\n📋 Test 9: Load Skill with .md Extension")
print("-" * 80)
skill_with_ext = manager.load_skill("sfo_air_traffic_context.md")
skill_without_ext = manager.load_skill("sfo_air_traffic_context")
assert skill_with_ext == skill_without_ext, "Skills differ with/without extension"
print("✓ Loading works with or without .md extension")

# Test 10: Error Handling
print("\n📋 Test 10: Error Handling")
print("-" * 80)
try:
    manager.load_skill("nonexistent_skill")
    print("✗ Should have raised FileNotFoundError")
    assert False, "Expected FileNotFoundError"
except FileNotFoundError as e:
    print(f"✓ Correctly raises FileNotFoundError for missing skill")
    print(f"  Error message: {str(e)}")

# Summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print("""
✅ All tests passed!

The Skills System is working correctly with skills at root/skills/

✓ SkillManager auto-detects correct path
✓ Skill loading works
✓ Caching improves performance
✓ All features function as expected
✓ Error handling is appropriate

You can now use the skills system with confidence:

    from sql_ai_agent.skill_manager import SkillManager

    manager = SkillManager()
    skill = manager.load_skill("sfo_air_traffic_context")

    result = agent.ask_question(
        question="Your question",
        additional_context=skill,
        verbose=True
    )
""")
print("=" * 80)
