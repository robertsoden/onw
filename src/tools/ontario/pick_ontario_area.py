"""Ontario-specific area lookup tool for parks, conservation areas, and First Nations territories."""

from typing import Annotated, Dict, Literal, Optional

import pandas as pd
import structlog
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from pydantic import BaseModel, Field
from sqlalchemy import text

from src.utils.database import get_connection_from_pool
from src.utils.env_loader import load_environment_variables
from src.utils.logging_config import get_logger

# Ontario-specific table names
ONTARIO_PARKS_TABLE = "ontario_parks"
ONTARIO_CONSERVATION_AREAS_TABLE = "ontario_conservation_areas"
WILLIAMS_TREATY_TERRITORIES_TABLE = "williams_treaty_first_nations"

# Source IDs for Ontario areas
ONTARIO_SOURCE_MAPPING = {
    "ontario_parks": 1,
    "conservation_areas": 2,
    "williams_treaty": 3,
}

RESULT_LIMIT = 10

load_environment_variables()
logger = get_logger(__name__)


async def query_ontario_database(
    place_name: str,
    area_type: Optional[str] = None,
    result_limit: int = 10,
):
    """Query the PostGIS database for Ontario location information.

    Args:
        place_name: Name of the place to search for
        area_type: Optional filter for specific area types ('park', 'conservation', 'treaty')
        result_limit: Maximum number of results to return

    Returns:
        DataFrame containing Ontario location information
    """
    async with get_connection_from_pool() as conn:
        # Enable pg_trgm extension for similarity function
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
            await conn.execute(text("SET pg_trgm.similarity_threshold = 0.2;"))
            await conn.commit()
        except Exception as e:
            logger.warning(f"Could not set up pg_trgm: {e}")
            await conn.rollback()

        # Check which tables exist
        existing_tables = []

        # Check Ontario Parks table
        if not area_type or area_type == "park":
            try:
                await conn.execute(
                    text(f"SELECT 1 FROM {ONTARIO_PARKS_TABLE} LIMIT 1")
                )
                existing_tables.append("ontario_parks")
            except Exception:
                logger.warning(f"Table {ONTARIO_PARKS_TABLE} does not exist")
                await conn.rollback()

        # Check Conservation Areas table
        if not area_type or area_type == "conservation":
            try:
                await conn.execute(
                    text(
                        f"SELECT 1 FROM {ONTARIO_CONSERVATION_AREAS_TABLE} LIMIT 1"
                    )
                )
                existing_tables.append("conservation_areas")
            except Exception:
                logger.warning(
                    f"Table {ONTARIO_CONSERVATION_AREAS_TABLE} does not exist"
                )
                await conn.rollback()

        # Check Williams Treaty Territories table
        if not area_type or area_type == "treaty":
            try:
                await conn.execute(
                    text(
                        f"SELECT 1 FROM {WILLIAMS_TREATY_TERRITORIES_TABLE} LIMIT 1"
                    )
                )
                existing_tables.append("williams_treaty")
            except Exception:
                logger.warning(
                    f"Table {WILLIAMS_TREATY_TERRITORIES_TABLE} does not exist"
                )
                await conn.rollback()

        if not existing_tables:
            logger.error("No Ontario area tables available")
            return pd.DataFrame()

        # Build UNION query for existing tables
        union_queries = []

        if "ontario_parks" in existing_tables:
            union_queries.append(f"""
                SELECT
                    name,
                    official_name,
                    'Provincial Park' as area_type,
                    designation,
                    managing_authority,
                    hectares,
                    ST_AsGeoJSON(geometry) as geometry,
                    {ONTARIO_SOURCE_MAPPING['ontario_parks']} as source_id
                FROM {ONTARIO_PARKS_TABLE}
                WHERE name ILIKE :search_pattern
                    OR official_name ILIKE :search_pattern
            """)

        if "conservation_areas" in existing_tables:
            union_queries.append(f"""
                SELECT
                    name,
                    official_name,
                    'Conservation Area' as area_type,
                    designation,
                    managing_authority,
                    hectares,
                    ST_AsGeoJSON(geometry) as geometry,
                    {ONTARIO_SOURCE_MAPPING['conservation_areas']} as source_id
                FROM {ONTARIO_CONSERVATION_AREAS_TABLE}
                WHERE name ILIKE :search_pattern
                    OR official_name ILIKE :search_pattern
            """)

        if "williams_treaty" in existing_tables:
            union_queries.append(f"""
                SELECT
                    first_nation_name as name,
                    first_nation_name as official_name,
                    'Williams Treaty Territory' as area_type,
                    'First Nations Territory' as designation,
                    first_nation_name as managing_authority,
                    NULL as hectares,
                    ST_AsGeoJSON(geometry) as geometry,
                    {ONTARIO_SOURCE_MAPPING['williams_treaty']} as source_id
                FROM {WILLIAMS_TREATY_TERRITORIES_TABLE}
                WHERE first_nation_name ILIKE :search_pattern
            """)

        if not union_queries:
            return pd.DataFrame()

        # Combine with UNION ALL
        full_query = " UNION ALL ".join(union_queries)
        full_query += f" ORDER BY name LIMIT :limit"

        # Execute query
        search_pattern = f"%{place_name}%"
        result = await conn.execute(
            text(full_query),
            {
                "search_pattern": search_pattern,
                "limit": result_limit,
            },
        )

        # Convert to DataFrame
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
                "source_id",
            ],
        )

        return df


class PickOntarioAreaInput(BaseModel):
    """Input for picking an Ontario area of interest."""

    place_name: str = Field(
        description="Name of the Ontario location (park, conservation area, or First Nations territory)"
    )
    area_type: Optional[Literal["park", "conservation", "treaty"]] = Field(
        default=None,
        description="Optional: Type of area to search for. Use 'park' for provincial parks, 'conservation' for conservation areas, 'treaty' for Williams Treaty territories. Leave empty to search all types.",
    )


@tool(args_schema=PickOntarioAreaInput)
async def pick_ontario_area(
    place_name: Annotated[str, Field(description="Name of the Ontario location")],
    area_type: Annotated[
        Optional[Literal["park", "conservation", "treaty"]],
        Field(
            description="Type of area: 'park', 'conservation', or 'treaty'. Leave empty for all types."
        ),
    ] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = None,
) -> Dict:
    """Search for Ontario protected areas including provincial parks, conservation areas, and First Nations territories.

    This tool searches Ontario-specific areas of interest including:
    - Provincial Parks (e.g., Algonquin Park, Killarney Provincial Park)
    - Conservation Areas (managed by Conservation Authorities)
    - Williams Treaty First Nations Territories

    Args:
        place_name: Name or partial name of the location to search for
        area_type: Optional filter - 'park', 'conservation', or 'treaty'

    Returns:
        Dictionary with location information and geometry
    """
    logger.info(
        f"Searching Ontario areas for: {place_name}, type: {area_type or 'all'}"
    )

    try:
        df = await query_ontario_database(
            place_name=place_name,
            area_type=area_type,
            result_limit=RESULT_LIMIT,
        )

        if df.empty:
            return {
                "status": "not_found",
                "message": f"No Ontario areas found matching '{place_name}'",
                "suggestion": "Try searching for a provincial park (e.g., 'Algonquin'), conservation area, or First Nations territory name.",
            }

        # If single result, return it directly
        if len(df) == 1:
            result = df.iloc[0].to_dict()
            return {
                "status": "found",
                "name": result["name"],
                "official_name": result["official_name"],
                "area_type": result["area_type"],
                "designation": result["designation"],
                "managing_authority": result["managing_authority"],
                "hectares": result.get("hectares"),
                "geometry": result["geometry"],
                "source_id": int(result["source_id"]),
            }

        # Multiple results - return list for user to choose
        results = df[
            [
                "name",
                "official_name",
                "area_type",
                "designation",
                "managing_authority",
                "hectares",
            ]
        ].to_dict(orient="records")

        return {
            "status": "multiple_found",
            "message": f"Found {len(results)} Ontario areas matching '{place_name}'. Please specify which one:",
            "results": results,
            "suggestion": "Choose one from the list or refine your search.",
        }

    except Exception as e:
        logger.error(f"Error searching Ontario areas: {e}")
        return {
            "status": "error",
            "message": f"Error searching Ontario areas: {str(e)}",
        }
