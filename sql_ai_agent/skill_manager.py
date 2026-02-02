"""
SQL AI Agent Skills System

This module provides functionality to load and manage domain-specific skills
that provide additional context to the SQL AI agent.

Skills are markdown files that contain:
- Dataset domain knowledge
- Column definitions
- Query patterns
- Business context
- Best practices

Skills can be dynamically loaded and injected into the agent's prompt template
to improve query generation quality.
"""

import os
from pathlib import Path
from typing import Optional, Dict, List


class SkillManager:
    """Manages loading and retrieval of SQL AI agent skills."""

    def __init__(self, skills_dir: Optional[str] = None):
        """
        Initialize the SkillManager.

        Args:
            skills_dir: Path to directory containing skill markdown files.
                       Defaults to <project_root>/skills
        """
        if skills_dir is None:
            # Default to skills directory at project root
            # Navigate from sql_ai_agent/ to project root, then to skills/
            module_dir = Path(__file__).parent  # sql_ai_agent/
            project_root = module_dir.parent     # project root
            skills_dir = project_root / "skills"

        self.skills_dir = Path(skills_dir)
        self._skills_cache: Dict[str, str] = {}

    def load_skill(self, skill_name: str) -> str:
        """
        Load a skill from a markdown file.

        Args:
            skill_name: Name of the skill file (with or without .md extension)

        Returns:
            Contents of the skill markdown file

        Raises:
            FileNotFoundError: If skill file doesn't exist
        """
        # Add .md extension if not present
        if not skill_name.endswith('.md'):
            skill_name = f"{skill_name}.md"

        # Check cache first
        if skill_name in self._skills_cache:
            return self._skills_cache[skill_name]

        # Load from file
        skill_path = self.skills_dir / skill_name
        if not skill_path.exists():
            raise FileNotFoundError(f"Skill not found: {skill_path}")

        with open(skill_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Cache it
        self._skills_cache[skill_name] = content
        return content

    def list_skills(self) -> List[str]:
        """
        List all available skills.

        Returns:
            List of skill names (without .md extension)
        """
        if not self.skills_dir.exists():
            return []

        skills = []
        for file_path in self.skills_dir.glob("*.md"):
            skills.append(file_path.stem)

        return sorted(skills)

    def get_skill_summary(self, skill_name: str) -> str:
        """
        Get a brief summary of a skill (first paragraph or heading).

        Args:
            skill_name: Name of the skill

        Returns:
            Brief summary of the skill
        """
        content = self.load_skill(skill_name)
        lines = content.split('\n')

        # Find first substantial line (not just #, not empty)
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                return line[:200] + "..." if len(line) > 200 else line

        return "No summary available"

    def clear_cache(self):
        """Clear the skills cache, forcing reload on next access."""
        self._skills_cache.clear()


def format_skill_for_prompt(skill_content: str, prefix: str = "Domain Knowledge") -> str:
    """
    Format skill content for injection into a prompt template.

    Args:
        skill_content: Raw markdown content of the skill
        prefix: Header prefix to add before the skill content

    Returns:
        Formatted skill content ready for prompt injection
    """
    formatted = f"\n\n## {prefix}\n\n{skill_content.strip()}\n\n"
    return formatted


# Example usage
if __name__ == "__main__":
    manager = SkillManager()

    print("Available skills:")
    for skill in manager.list_skills():
        summary = manager.get_skill_summary(skill)
        print(f"\n- {skill}")
        print(f"  {summary}")

    # Load a specific skill
    if manager.list_skills():
        skill_name = manager.list_skills()[0]
        print(f"\n\nLoading skill: {skill_name}")
        content = manager.load_skill(skill_name)
        print(f"Content length: {len(content)} characters")
        print(f"\nFormatted for prompt:\n{format_skill_for_prompt(content)[:500]}...")
