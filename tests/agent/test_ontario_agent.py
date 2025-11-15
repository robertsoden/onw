"""Unit tests for Ontario agent configuration."""

import pytest

from src.agents.ontario_agent import get_ontario_prompt


class TestOntarioAgentPrompt:
    """Test Ontario agent prompt generation."""

    def test_prompt_includes_ontario_context(self):
        """Test that prompt includes Ontario-specific context."""
        prompt = get_ontario_prompt()

        assert "Ontario" in prompt
        assert "provincial parks" in prompt.lower()
        assert "conservation" in prompt.lower()

    def test_prompt_includes_williams_treaty_context(self):
        """Test that prompt includes Williams Treaty information."""
        prompt = get_ontario_prompt()

        assert "Williams Treaty" in prompt
        assert "First Nations" in prompt
        assert "1923" in prompt

    def test_prompt_includes_cultural_sensitivity(self):
        """Test that prompt includes cultural sensitivity guidelines."""
        prompt = get_ontario_prompt()

        assert "cultural" in prompt.lower() or "Cultural" in prompt
        assert "respectful" in prompt.lower() or "Respectful" in prompt

    def test_prompt_includes_current_date(self):
        """Test that prompt includes current date."""
        prompt = get_ontario_prompt()

        assert "Current date" in prompt
        # Should have a date in YYYY-MM-DD format
        import re

        date_pattern = r"\d{4}-\d{2}-\d{2}"
        assert re.search(date_pattern, prompt)

    def test_prompt_includes_tool_instructions(self):
        """Test that prompt includes Ontario tool usage instructions."""
        prompt = get_ontario_prompt()

        # Should mention all Ontario tools
        assert "pick_ontario_area" in prompt
        assert "ontario_proximity_search" in prompt
        assert "compare_ontario_areas" in prompt
        assert "get_ontario_statistics" in prompt

    def test_prompt_includes_workflow(self):
        """Test that prompt includes workflow guidance."""
        prompt = get_ontario_prompt()

        assert "workflow" in prompt.lower() or "Workflow" in prompt

    def test_prompt_with_user_context(self):
        """Test prompt generation with user information."""
        user = {"name": "Test User", "email": "test@example.com"}

        prompt = get_ontario_prompt(user)

        # Prompt should still be generated (user context may not be used yet)
        assert len(prompt) > 0
        assert "Ontario" in prompt


class TestOntarioAgentFactories:
    """Test Ontario agent factory functions."""

    @pytest.mark.asyncio
    async def test_fetch_ontario_agent_anonymous_import(self):
        """Test that anonymous Ontario agent can be imported."""
        from src.agents import fetch_ontario_agent_anonymous

        assert callable(fetch_ontario_agent_anonymous)

    @pytest.mark.asyncio
    async def test_fetch_ontario_agent_import(self):
        """Test that Ontario agent with checkpointer can be imported."""
        from src.agents import fetch_ontario_agent

        assert callable(fetch_ontario_agent)

    @pytest.mark.asyncio
    async def test_ontario_tools_available(self):
        """Test that Ontario tools are properly imported."""
        from src.tools.ontario import (
            compare_ontario_areas,
            get_ontario_statistics,
            ontario_proximity_search,
            pick_ontario_area,
        )

        assert callable(pick_ontario_area)
        assert callable(ontario_proximity_search)
        assert callable(compare_ontario_areas)
        assert callable(get_ontario_statistics)
