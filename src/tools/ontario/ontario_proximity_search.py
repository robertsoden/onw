"""Ontario proximity search tool - find areas near a location."""

from typing import Annotated, Dict, List, Optional

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


async def search_nearby_areas(
    latitude: float,
    longitude: float,
    radius_km: float = 50,
    area_types: Optional[List[str]] = None,
    limit: int = 10,
) -> pd.DataFrame:
    """
    Search for Ontario areas within a radius of a point.

    Args:
        latitude: Latitude of the center point
        longitude: Longitude of the center point
        radius_km: Search radius in kilometers
        area_types: Optional list of area types to include ['park', 'conservation', 'treaty']
        limit: Maximum number of results

    Returns:
        DataFrame with nearby areas and distances
    """
    async with get_connection_from_pool() as conn:
        # Default to all area types if not specified
        if not area_types:
            area_types = ['park', 'conservation', 'treaty']

        # Build queries for each requested area type
        union_queries = []

        if 'park' in area_types:
            union_queries.append(f"""
                SELECT
                    name,
                    official_name,
                    'Provincial Park' as area_type,
                    designation,
                    managing_authority,
                    hectares,
                    ST_AsGeoJSON(geometry) as geometry,
                    ST_Distance(
                        ST_Transform(geometry::geometry, 3347),
                        ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geometry, 3347)
                    ) / 1000 as distance_km
                FROM {ONTARIO_PARKS_TABLE}
                WHERE ST_DWithin(
                    ST_Transform(geometry::geometry, 3347),
                    ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geometry, 3347),
                    :radius_m
                )
            """)

        if 'conservation' in area_types:
            union_queries.append(f"""
                SELECT
                    name,
                    official_name,
                    'Conservation Area' as area_type,
                    designation,
                    managing_authority,
                    hectares,
                    ST_AsGeoJSON(geometry) as geometry,
                    ST_Distance(
                        ST_Transform(geometry::geometry, 3347),
                        ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geometry, 3347)
                    ) / 1000 as distance_km
                FROM {ONTARIO_CONSERVATION_AREAS_TABLE}
                WHERE ST_DWithin(
                    ST_Transform(geometry::geometry, 3347),
                    ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geometry, 3347),
                    :radius_m
                )
            """)

        if 'treaty' in area_types:
            union_queries.append(f"""
                SELECT
                    first_nation_name as name,
                    first_nation_name as official_name,
                    'Williams Treaty Territory' as area_type,
                    'First Nations Territory' as designation,
                    first_nation_name as managing_authority,
                    NULL as hectares,
                    ST_AsGeoJSON(geometry) as geometry,
                    ST_Distance(
                        ST_Transform(geometry::geometry, 3347),
                        ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geometry, 3347)
                    ) / 1000 as distance_km
                FROM {WILLIAMS_TREATY_TERRITORIES_TABLE}
                WHERE ST_DWithin(
                    ST_Transform(geometry::geometry, 3347),
                    ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geometry, 3347),
                    :radius_m
                )
            """)

        if not union_queries:
            return pd.DataFrame()

        # Combine queries
        full_query = " UNION ALL ".join(union_queries)
        full_query += " ORDER BY distance_km LIMIT :limit"

        # Execute
        result = await conn.execute(
            text(full_query),
            {
                "lat": latitude,
                "lon": longitude,
                "radius_m": radius_km * 1000,  # Convert km to meters
                "limit": limit,
            },
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
                "geometry",
                "distance_km",
            ],
        )

        return df


class OntarioProximitySearchInput(BaseModel):
    """Input for Ontario proximity search."""

    latitude: float = Field(description="Latitude of the search center point")
    longitude: float = Field(description="Longitude of the search center point")
    radius_km: float = Field(
        default=50,
        description="Search radius in kilometers (default: 50km)",
    )
    area_types: Optional[List[str]] = Field(
        default=None,
        description="Types of areas to search: 'park', 'conservation', 'treaty'. Leave empty for all types.",
    )


@tool(args_schema=OntarioProximitySearchInput)
async def ontario_proximity_search(
    latitude: Annotated[float, Field(description="Latitude")],
    longitude: Annotated[float, Field(description="Longitude")],
    radius_km: Annotated[
        float, Field(description="Search radius in kilometers")
    ] = 50,
    area_types: Annotated[
        Optional[List[str]],
        Field(description="Area types: 'park', 'conservation', 'treaty'"),
    ] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = None,
) -> Dict:
    """
    Find Ontario protected areas and First Nations territories near a location.

    Searches within a specified radius for:
    - Provincial Parks
    - Conservation Areas
    - Williams Treaty First Nations Territories

    Args:
        latitude: Latitude of the center point
        longitude: Longitude of the center point
        radius_km: Search radius in kilometers (default: 50km)
        area_types: Optional list of area types to include

    Returns:
        Dictionary with nearby areas sorted by distance
    """
    logger.info(
        f"Proximity search: ({latitude}, {longitude}), radius: {radius_km}km"
    )

    try:
        df = await search_nearby_areas(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            area_types=area_types,
            limit=10,
        )

        if df.empty:
            return {
                "status": "not_found",
                "message": f"No Ontario areas found within {radius_km}km of ({latitude}, {longitude})",
                "suggestion": "Try increasing the search radius or checking the coordinates.",
            }

        # Format results
        results = []
        for _, row in df.iterrows():
            results.append(
                {
                    "name": row["name"],
                    "official_name": row["official_name"],
                    "area_type": row["area_type"],
                    "designation": row["designation"],
                    "managing_authority": row["managing_authority"],
                    "hectares": row.get("hectares"),
                    "distance_km": round(row["distance_km"], 2),
                }
            )

        return {
            "status": "found",
            "count": len(results),
            "search_center": {"latitude": latitude, "longitude": longitude},
            "radius_km": radius_km,
            "areas": results,
        }

    except Exception as e:
        logger.error(f"Error in proximity search: {e}")
        return {
            "status": "error",
            "message": f"Error searching nearby areas: {str(e)}",
        }
