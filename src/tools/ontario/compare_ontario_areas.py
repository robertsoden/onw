"""Compare multiple Ontario protected areas."""

from typing import Annotated, Dict, List

import pandas as pd
import structlog
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from pydantic import BaseModel, Field
from sqlalchemy import text

from src.tools.ontario.constants import (
    ONTARIO_CONSERVATION_AREAS_TABLE,
    ONTARIO_PARKS_TABLE,
    WILLIAMS_TREATY_TERRITORIES_TABLE,
)
from src.utils.database import get_connection_from_pool
from src.utils.env_loader import load_environment_variables
from src.utils.logging_config import get_logger

load_environment_variables()
logger = get_logger(__name__)


async def fetch_area_details(area_names: List[str]) -> pd.DataFrame:
    """
    Fetch details for multiple Ontario areas by name.

    Args:
        area_names: List of area names to fetch

    Returns:
        DataFrame with area details
    """
    async with get_connection_from_pool() as conn:
        # Search across all Ontario area types
        union_queries = []

        # Ontario Parks
        union_queries.append(f"""
            SELECT
                name,
                official_name,
                'Provincial Park' as area_type,
                designation,
                managing_authority,
                hectares,
                ST_AsGeoJSON(ST_Centroid(geometry)) as centroid,
                ST_Area(ST_Transform(geometry::geometry, 3347)) / 10000 as calculated_hectares
            FROM {ONTARIO_PARKS_TABLE}
            WHERE name = ANY(:names) OR official_name = ANY(:names)
        """)

        # Conservation Areas
        union_queries.append(f"""
            SELECT
                name,
                official_name,
                'Conservation Area' as area_type,
                designation,
                managing_authority,
                hectares,
                ST_AsGeoJSON(ST_Centroid(geometry)) as centroid,
                ST_Area(ST_Transform(geometry::geometry, 3347)) / 10000 as calculated_hectares
            FROM {ONTARIO_CONSERVATION_AREAS_TABLE}
            WHERE name = ANY(:names) OR official_name = ANY(:names)
        """)

        # Williams Treaty Territories
        union_queries.append(f"""
            SELECT
                first_nation_name as name,
                first_nation_name as official_name,
                'Williams Treaty Territory' as area_type,
                'First Nations Territory' as designation,
                first_nation_name as managing_authority,
                NULL as hectares,
                ST_AsGeoJSON(ST_Centroid(geometry)) as centroid,
                ST_Area(ST_Transform(geometry::geometry, 3347)) / 10000 as calculated_hectares
            FROM {WILLIAMS_TREATY_TERRITORIES_TABLE}
            WHERE first_nation_name = ANY(:names)
        """)

        full_query = " UNION ALL ".join(union_queries)

        result = await conn.execute(
            text(full_query),
            {"names": area_names},
        )

        rows = result.fetchall()
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(
            [dict(row._mapping) for row in rows],
            columns=[
                "name",
                "official_name",
                "area_type",
                "designation",
                "managing_authority",
                "hectares",
                "centroid",
                "calculated_hectares",
            ],
        )

        return df


class CompareOntarioAreasInput(BaseModel):
    """Input for comparing Ontario areas."""

    area_names: List[str] = Field(
        description="List of 2-5 Ontario area names to compare"
    )


@tool(args_schema=CompareOntarioAreasInput)
async def compare_ontario_areas(
    area_names: Annotated[
        List[str], Field(description="List of area names to compare")
    ],
    tool_call_id: Annotated[str, InjectedToolCallId] = None,
) -> Dict:
    """
    Compare multiple Ontario protected areas side-by-side.

    Compares key attributes including:
    - Size (hectares)
    - Type and designation
    - Managing authority
    - Location

    Args:
        area_names: List of 2-5 Ontario area names

    Returns:
        Dictionary with comparison data
    """
    logger.info(f"Comparing Ontario areas: {area_names}")

    if len(area_names) < 2:
        return {
            "status": "error",
            "message": "Please provide at least 2 areas to compare",
        }

    if len(area_names) > 5:
        return {
            "status": "error",
            "message": "Please limit comparison to 5 areas or fewer",
        }

    try:
        df = await fetch_area_details(area_names)

        if df.empty:
            return {
                "status": "not_found",
                "message": f"No Ontario areas found matching: {', '.join(area_names)}",
                "suggestion": "Check area names and try again",
            }

        # Check if we found all requested areas
        found_names = set(df["name"].tolist() + df["official_name"].tolist())
        missing = [name for name in area_names if name not in found_names]

        # Build comparison results
        comparison = []
        for _, row in df.iterrows():
            comparison.append(
                {
                    "name": row["name"],
                    "official_name": row["official_name"],
                    "area_type": row["area_type"],
                    "designation": row["designation"],
                    "managing_authority": row["managing_authority"],
                    "hectares": (
                        row["hectares"]
                        if row["hectares"]
                        else round(row["calculated_hectares"], 2)
                    ),
                }
            )

        # Calculate summary statistics
        areas_by_size = sorted(
            comparison, key=lambda x: x["hectares"] or 0, reverse=True
        )
        total_hectares = sum(
            [a["hectares"] for a in comparison if a["hectares"]]
        )

        result = {
            "status": "found",
            "count": len(comparison),
            "areas": comparison,
            "summary": {
                "total_hectares": round(total_hectares, 2),
                "largest": areas_by_size[0]["name"] if areas_by_size else None,
                "smallest": (
                    areas_by_size[-1]["name"] if areas_by_size else None
                ),
            },
        }

        if missing:
            result["warning"] = f"Could not find: {', '.join(missing)}"

        return result

    except Exception as e:
        logger.error(f"Error comparing areas: {e}")
        return {
            "status": "error",
            "message": f"Error comparing areas: {str(e)}",
        }
