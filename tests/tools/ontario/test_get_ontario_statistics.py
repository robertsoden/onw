"""Unit tests for get_ontario_statistics tool."""

import uuid

import pytest

from src.tools.ontario.get_ontario_statistics import get_ontario_statistics


class TestGetOntarioStatistics:
    """Test get_ontario_statistics tool."""

    @pytest.mark.asyncio
    async def test_statistics_not_implemented(self):
        """Test that tool returns not_implemented status."""
        result = await get_ontario_statistics.ainvoke(
            {
                "area_name": "Algonquin Park",
                "tool_call_id": str(uuid.uuid4()),
            }
        )

        assert result["status"] == "not_implemented"
        assert "in progress" in result["message"]
        assert result["area_name"] == "Algonquin Park"

    @pytest.mark.asyncio
    async def test_statistics_with_metric(self):
        """Test requesting specific metric."""
        result = await get_ontario_statistics.ainvoke(
            {
                "area_name": "Killarney Park",
                "metric": "biodiversity",
                "tool_call_id": str(uuid.uuid4()),
            }
        )

        assert result["status"] == "not_implemented"
        assert result["requested_metric"] == "biodiversity"

    @pytest.mark.asyncio
    async def test_statistics_includes_next_steps(self):
        """Test that response includes integration next steps."""
        result = await get_ontario_statistics.ainvoke(
            {
                "area_name": "Test Park",
                "tool_call_id": str(uuid.uuid4()),
            }
        )

        assert "next_steps" in result
        assert len(result["next_steps"]) > 0
        # Should mention data integration
        assert any(
            "data" in step.lower() for step in result["next_steps"]
        )
