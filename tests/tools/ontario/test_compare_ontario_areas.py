"""Unit tests for compare_ontario_areas tool."""

import uuid
from unittest.mock import patch

import pandas as pd
import pytest

from src.tools.ontario.compare_ontario_areas import compare_ontario_areas


class TestCompareOntarioAreas:
    """Test compare_ontario_areas tool."""

    @pytest.mark.asyncio
    async def test_compare_too_few_areas(self):
        """Test error when fewer than 2 areas provided."""
        result = await compare_ontario_areas.ainvoke(
            {
                "area_names": ["Algonquin Park"],
                "tool_call_id": str(uuid.uuid4()),
            }
        )

        assert result["status"] == "error"
        assert "at least 2 areas" in result["message"]

    @pytest.mark.asyncio
    async def test_compare_too_many_areas(self):
        """Test error when more than 5 areas provided."""
        result = await compare_ontario_areas.ainvoke(
            {
                "area_names": [
                    "Park1",
                    "Park2",
                    "Park3",
                    "Park4",
                    "Park5",
                    "Park6",
                ],
                "tool_call_id": str(uuid.uuid4()),
            }
        )

        assert result["status"] == "error"
        assert "5 areas or fewer" in result["message"]

    @pytest.mark.asyncio
    async def test_compare_not_found(self):
        """Test handling when no areas are found."""
        with patch(
            "src.tools.ontario.compare_ontario_areas.fetch_area_details"
        ) as mock_fetch:
            mock_fetch.return_value = pd.DataFrame()

            result = await compare_ontario_areas.ainvoke(
                {
                    "area_names": ["Nonexistent Park 1", "Nonexistent Park 2"],
                    "tool_call_id": str(uuid.uuid4()),
                }
            )

            assert result["status"] == "not_found"
            assert "No Ontario areas found" in result["message"]

    @pytest.mark.asyncio
    async def test_compare_successful(self):
        """Test successful comparison of areas."""
        mock_df = pd.DataFrame(
            [
                {
                    "name": "Algonquin Park",
                    "official_name": "Algonquin Provincial Park",
                    "area_type": "Provincial Park",
                    "designation": "Wilderness Park",
                    "managing_authority": "Ontario Parks",
                    "hectares": 769500,
                    "centroid": '{"type":"Point"}',
                    "calculated_hectares": 769500,
                },
                {
                    "name": "Killarney Park",
                    "official_name": "Killarney Provincial Park",
                    "area_type": "Provincial Park",
                    "designation": "Wilderness Park",
                    "managing_authority": "Ontario Parks",
                    "hectares": 48500,
                    "centroid": '{"type":"Point"}',
                    "calculated_hectares": 48500,
                },
            ]
        )

        with patch(
            "src.tools.ontario.compare_ontario_areas.fetch_area_details"
        ) as mock_fetch:
            mock_fetch.return_value = mock_df

            result = await compare_ontario_areas.ainvoke(
                {
                    "area_names": ["Algonquin Park", "Killarney Park"],
                    "tool_call_id": str(uuid.uuid4()),
                }
            )

            assert result["status"] == "found"
            assert result["count"] == 2
            assert len(result["areas"]) == 2
            assert result["summary"]["largest"] == "Algonquin Park"
            assert result["summary"]["smallest"] == "Killarney Park"
            assert result["summary"]["total_hectares"] == 818000

    @pytest.mark.asyncio
    async def test_compare_with_missing_areas(self):
        """Test comparison when some requested areas are not found."""
        mock_df = pd.DataFrame(
            [
                {
                    "name": "Algonquin Park",
                    "official_name": "Algonquin Provincial Park",
                    "area_type": "Provincial Park",
                    "designation": "Wilderness Park",
                    "managing_authority": "Ontario Parks",
                    "hectares": 769500,
                    "centroid": '{"type":"Point"}',
                    "calculated_hectares": 769500,
                }
            ]
        )

        with patch(
            "src.tools.ontario.compare_ontario_areas.fetch_area_details"
        ) as mock_fetch:
            mock_fetch.return_value = mock_df

            result = await compare_ontario_areas.ainvoke(
                {
                    "area_names": ["Algonquin Park", "Nonexistent Park"],
                    "tool_call_id": str(uuid.uuid4()),
                }
            )

            assert result["status"] == "found"
            assert "warning" in result
            assert "Could not find" in result["warning"]

    @pytest.mark.asyncio
    async def test_compare_with_null_hectares(self):
        """Test comparison when some areas don't have hectare data."""
        mock_df = pd.DataFrame(
            [
                {
                    "name": "Test Park",
                    "official_name": "Test Provincial Park",
                    "area_type": "Provincial Park",
                    "designation": "Park",
                    "managing_authority": "Ontario Parks",
                    "hectares": None,
                    "centroid": '{"type":"Point"}',
                    "calculated_hectares": 1500.5,
                },
                {
                    "name": "Another Park",
                    "official_name": "Another Park",
                    "area_type": "Provincial Park",
                    "designation": "Park",
                    "managing_authority": "Ontario Parks",
                    "hectares": 2000,
                    "centroid": '{"type":"Point"}',
                    "calculated_hectares": 2000,
                },
            ]
        )

        with patch(
            "src.tools.ontario.compare_ontario_areas.fetch_area_details"
        ) as mock_fetch:
            mock_fetch.return_value = mock_df

            result = await compare_ontario_areas.ainvoke(
                {
                    "area_names": ["Test Park", "Another Park"],
                    "tool_call_id": str(uuid.uuid4()),
                }
            )

            assert result["status"] == "found"
            # Should use calculated hectares when hectares is None
            assert result["areas"][0]["hectares"] == 1500.5
            assert result["areas"][1]["hectares"] == 2000

    @pytest.mark.asyncio
    async def test_compare_error_handling(self):
        """Test error handling when comparison fails."""
        with patch(
            "src.tools.ontario.compare_ontario_areas.fetch_area_details"
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("Database error")

            result = await compare_ontario_areas.ainvoke(
                {
                    "area_names": ["Park1", "Park2"],
                    "tool_call_id": str(uuid.uuid4()),
                }
            )

            assert result["status"] == "error"
            assert "Error" in result["message"]
