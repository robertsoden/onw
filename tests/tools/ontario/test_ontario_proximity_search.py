"""Unit tests for ontario_proximity_search tool."""

import uuid
from unittest.mock import patch

import pandas as pd
import pytest

from src.tools.ontario.ontario_proximity_search import (
    ontario_proximity_search,
)


class TestOntarioProximitySearch:
    """Test ontario_proximity_search tool."""

    @pytest.mark.asyncio
    async def test_proximity_search_no_results(self):
        """Test handling when no areas are found in range."""
        with patch(
            "src.tools.ontario.ontario_proximity_search.search_nearby_areas"
        ) as mock_search:
            mock_search.return_value = pd.DataFrame()

            result = await ontario_proximity_search.ainvoke(
                {
                    "latitude": 45.0,
                    "longitude": -78.0,
                    "radius_km": 10,
                    "tool_call_id": str(uuid.uuid4()),
                }
            )

            assert result["status"] == "not_found"
            assert "No Ontario areas found" in result["message"]
            assert "10km" in result["message"]

    @pytest.mark.asyncio
    async def test_proximity_search_finds_areas(self):
        """Test successful proximity search."""
        mock_df = pd.DataFrame(
            [
                {
                    "name": "Algonquin Park",
                    "official_name": "Algonquin Provincial Park",
                    "area_type": "Provincial Park",
                    "designation": "Wilderness Park",
                    "managing_authority": "Ontario Parks",
                    "hectares": 769500,
                    "geometry": '{"type":"Point"}',
                    "distance_km": 25.5,
                },
                {
                    "name": "Silent Lake Park",
                    "official_name": "Silent Lake Provincial Park",
                    "area_type": "Provincial Park",
                    "designation": "Natural Environment Park",
                    "managing_authority": "Ontario Parks",
                    "hectares": 1431,
                    "geometry": '{"type":"Point"}',
                    "distance_km": 35.2,
                },
            ]
        )

        with patch(
            "src.tools.ontario.ontario_proximity_search.search_nearby_areas"
        ) as mock_search:
            mock_search.return_value = mock_df

            result = await ontario_proximity_search.ainvoke(
                {
                    "latitude": 45.0,
                    "longitude": -78.5,
                    "radius_km": 50,
                    "tool_call_id": str(uuid.uuid4()),
                }
            )

            assert result["status"] == "found"
            assert result["count"] == 2
            assert result["radius_km"] == 50
            assert result["search_center"]["latitude"] == 45.0
            assert len(result["areas"]) == 2
            assert result["areas"][0]["distance_km"] == 25.5

    @pytest.mark.asyncio
    async def test_proximity_search_with_type_filter(self):
        """Test proximity search with area type filter."""
        mock_df = pd.DataFrame(
            [
                {
                    "name": "Warsaw Caves",
                    "official_name": "Warsaw Caves Conservation Area",
                    "area_type": "Conservation Area",
                    "designation": "Conservation Area",
                    "managing_authority": "Otonabee Conservation",
                    "hectares": 162,
                    "geometry": '{"type":"Point"}',
                    "distance_km": 15.0,
                }
            ]
        )

        with patch(
            "src.tools.ontario.ontario_proximity_search.search_nearby_areas"
        ) as mock_search:
            mock_search.return_value = mock_df

            result = await ontario_proximity_search.ainvoke(
                {
                    "latitude": 44.3,
                    "longitude": -78.1,
                    "radius_km": 25,
                    "area_types": ["conservation"],
                    "tool_call_id": str(uuid.uuid4()),
                }
            )

            assert result["status"] == "found"
            assert result["areas"][0]["area_type"] == "Conservation Area"

    @pytest.mark.asyncio
    async def test_proximity_search_default_radius(self):
        """Test that default radius is used when not specified."""
        mock_df = pd.DataFrame(
            [
                {
                    "name": "Test Park",
                    "official_name": "Test Provincial Park",
                    "area_type": "Provincial Park",
                    "designation": "Park",
                    "managing_authority": "Ontario Parks",
                    "hectares": 1000,
                    "geometry": '{"type":"Point"}',
                    "distance_km": 40.0,
                }
            ]
        )

        with patch(
            "src.tools.ontario.ontario_proximity_search.search_nearby_areas"
        ) as mock_search:
            mock_search.return_value = mock_df

            result = await ontario_proximity_search.ainvoke(
                {
                    "latitude": 44.0,
                    "longitude": -79.0,
                    "tool_call_id": str(uuid.uuid4()),
                }
            )

            assert result["status"] == "found"
            # Default radius should be 50km
            assert result["radius_km"] == 50

    @pytest.mark.asyncio
    async def test_proximity_search_distance_rounding(self):
        """Test that distances are properly rounded to 2 decimals."""
        mock_df = pd.DataFrame(
            [
                {
                    "name": "Test Area",
                    "official_name": "Test Area",
                    "area_type": "Provincial Park",
                    "designation": "Park",
                    "managing_authority": "Ontario Parks",
                    "hectares": 500,
                    "geometry": '{"type":"Point"}',
                    "distance_km": 12.3456789,  # Many decimals
                }
            ]
        )

        with patch(
            "src.tools.ontario.ontario_proximity_search.search_nearby_areas"
        ) as mock_search:
            mock_search.return_value = mock_df

            result = await ontario_proximity_search.ainvoke(
                {
                    "latitude": 44.0,
                    "longitude": -79.0,
                    "tool_call_id": str(uuid.uuid4()),
                }
            )

            # Distance should be rounded to 2 decimals
            assert result["areas"][0]["distance_km"] == 12.35

    @pytest.mark.asyncio
    async def test_proximity_search_error_handling(self):
        """Test error handling when search fails."""
        with patch(
            "src.tools.ontario.ontario_proximity_search.search_nearby_areas"
        ) as mock_search:
            mock_search.side_effect = Exception("PostGIS error")

            result = await ontario_proximity_search.ainvoke(
                {
                    "latitude": 44.0,
                    "longitude": -79.0,
                    "tool_call_id": str(uuid.uuid4()),
                }
            )

            assert result["status"] == "error"
            assert "Error" in result["message"]
