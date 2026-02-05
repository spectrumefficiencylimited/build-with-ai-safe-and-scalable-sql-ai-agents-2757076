"""
Quick test to verify SkillManager works with skills at root level
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sql_ai_agent.skill_manager import SkillManager

print("=" * 80)
print("SKILL MANAGER - PATH VERIFICATION TEST")
print("=" * 80)

# Initialize SkillManager (should auto-detect skills at root/skills/)
manager = SkillManager()

print(f"\n✓ SkillManager initialized")
print(f"  Skills directory: {manager.skills_dir}")
print(f"  Skills directory exists: {manager.skills_dir.exists()}")

# List skills
print(f"\n✓ Available skills:")
skills = manager.list_skills()
if skills:
    for skill in skills:
        print(f"  - {skill}")
else:
    print("  (No skills found)")

# Try loading a skill
if "sfo_air_traffic_context" in skills:
    print(f"\n✓ Loading sfo_air_traffic_context...")
    skill_content = manager.load_skill("sfo_air_traffic_context")
    print(f"  Size: {len(skill_content):,} characters")
    print(f"  First 100 chars: {skill_content[:100]}...")
    print(f"\n✓ Skill loaded successfully from root/skills/ directory!")
else:
    print("\n✗ sfo_air_traffic_context skill not found")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
