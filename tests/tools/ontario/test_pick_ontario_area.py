"""Unit tests for pick_ontario_area tool."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.tools.ontario.pick_ontario_area import pick_ontario_area


class TestPickOntarioArea:
    """Test pick_ontario_area tool."""

    @pytest.mark.asyncio
    async def test_pick_area_not_found(self):
        """Test handling when no areas are found."""
        with patch(
            "src.tools.ontario.pick_ontario_area.query_ontario_database"
        ) as mock_query:
            mock_query.return_value = pd.DataFrame()

            result = await pick_ontario_area.ainvoke(
                {
                    "place_name": "Nonexistent Park",
                    "tool_call_id": str(uuid.uuid4()),
                }
            )

            assert result["status"] == "not_found"
            assert "No Ontario areas found" in result["message"]

    @pytest.mark.asyncio
    async def test_pick_area_single_result(self):
        """Test handling when a single area is found."""
        mock_df = pd.DataFrame(
            [
                {
                    "name": "Algonquin Park",
                    "official_name": "Algonquin Provincial Park",
                    "area_type": "Provincial Park",
                    "designation": "Wilderness Park",
                    "managing_authority": "Ontario Parks",
                    "hectares": 769500,
                    "geometry": '{"type":"Point","coordinates":[-78.5,45.5]}',
                    "source_id": 1,
                }
            ]
        )

        with patch(
            "src.tools.ontario.pick_ontario_area.query_ontario_database"
        ) as mock_query:
            mock_query.return_value = mock_df

            result = await pick_ontario_area.ainvoke(
                {
                    "place_name": "Algonquin",
                    "tool_call_id": str(uuid.uuid4()),
                }
            )

            assert result["status"] == "found"
            assert result["name"] == "Algonquin Park"
            assert result["area_type"] == "Provincial Park"
            assert result["hectares"] == 769500

    @pytest.mark.asyncio
    async def test_pick_area_multiple_results(self):
        """Test handling when multiple areas are found."""
        mock_df = pd.DataFrame(
            [
                {
                    "name": "Killarney Park",
                    "official_name": "Killarney Provincial Park",
                    "area_type": "Provincial Park",
                    "designation": "Wilderness Park",
                    "managing_authority": "Ontario Parks",
                    "hectares": 48500,
                    "geometry": '{"type":"Point","coordinates":[-81.4,46.0]}',
                    "source_id": 1,
                },
                {
                    "name": "Killarney Mountain Lodge",
                    "official_name": "Killarney Conservation Area",
                    "area_type": "Conservation Area",
                    "designation": "Conservation Area",
                    "managing_authority": "Georgian Bay Land Trust",
                    "hectares": 120,
                    "geometry": '{"type":"Point","coordinates":[-81.5,45.9]}',
                    "source_id": 2,
                },
            ]
        )

        with patch(
            "src.tools.ontario.pick_ontario_area.query_ontario_database"
        ) as mock_query:
            mock_query.return_value = mock_df

            result = await pick_ontario_area.ainvoke(
                {
                    "place_name": "Killarney",
                    "tool_call_id": str(uuid.uuid4()),
                }
            )

            assert result["status"] == "multiple_found"
            assert len(result["results"]) == 2
            assert "choose" in result["suggestion"].lower()

    @pytest.mark.asyncio
    async def test_pick_area_with_type_filter(self):
        """Test filtering by area type."""
        mock_df = pd.DataFrame(
            [
                {
                    "name": "Warsaw Caves",
                    "official_name": "Warsaw Caves Conservation Area",
                    "area_type": "Conservation Area",
                    "designation": "Conservation Area",
                    "managing_authority": "Otonabee Conservation",
                    "hectares": 162,
                    "geometry": '{"type":"Point","coordinates":[-78.1,44.3]}',
                    "source_id": 2,
                }
            ]
        )

        with patch(
            "src.tools.ontario.pick_ontario_area.query_ontario_database"
        ) as mock_query:
            mock_query.return_value = mock_df

            result = await pick_ontario_area.ainvoke(
                {
                    "place_name": "Warsaw",
                    "area_type": "conservation",
                    "tool_call_id": str(uuid.uuid4()),
                }
            )

            assert result["status"] == "found"
            assert result["area_type"] == "Conservation Area"

    @pytest.mark.asyncio
    async def test_pick_area_first_nations_territory(self):
        """Test finding First Nations territories."""
        mock_df = pd.DataFrame(
            [
                {
                    "name": "Curve Lake First Nation",
                    "official_name": "Curve Lake First Nation",
                    "area_type": "Williams Treaty Territory",
                    "designation": "First Nations Territory",
                    "managing_authority": "Curve Lake First Nation",
                    "hectares": None,
                    "geometry": '{"type":"Point","coordinates":[-78.2,44.5]}',
                    "source_id": 3,
                }
            ]
        )

        with patch(
            "src.tools.ontario.pick_ontario_area.query_ontario_database"
        ) as mock_query:
            mock_query.return_value = mock_df

            result = await pick_ontario_area.ainvoke(
                {
                    "place_name": "Curve Lake",
                    "area_type": "treaty",
                    "tool_call_id": str(uuid.uuid4()),
                }
            )

            assert result["status"] == "found"
            assert result["area_type"] == "Williams Treaty Territory"
            assert "First Nation" in result["managing_authority"]

    @pytest.mark.asyncio
    async def test_pick_area_error_handling(self):
        """Test error handling when database query fails."""
        with patch(
            "src.tools.ontario.pick_ontario_area.query_ontario_database"
        ) as mock_query:
            mock_query.side_effect = Exception("Database connection error")

            result = await pick_ontario_area.ainvoke(
                {
                    "place_name": "Test Park",
                    "tool_call_id": str(uuid.uuid4()),
                }
            )

            assert result["status"] == "error"
            assert "Error" in result["message"]
