"""Get environmental statistics for Ontario protected areas.

This tool integrates with the Ontario data handler to provide biodiversity and
environmental data for Ontario parks, conservation areas, and First Nations territories.
"""

from typing import Annotated, Dict, List, Optional

import structlog
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from pydantic import BaseModel, Field

from src.tools.data_handlers.ontario_handler import OntarioDataHandler, OntarioConfig
from src.utils.env_loader import load_environment_variables
from src.utils.logging_config import get_logger

load_environment_variables()
logger = get_logger(__name__)


class GetOntarioStatisticsInput(BaseModel):
    """Input for Ontario statistics."""

    area_name: str = Field(
        description="Name of the Ontario area (park, conservation area, or territory)"
    )
    metric: Optional[str] = Field(
        default=None,
        description="Optional specific metric: 'biodiversity', 'birds', 'water_quality', 'species_count'",
    )
    start_date: Optional[str] = Field(
        default=None, description="Start date for observations (YYYY-MM-DD)"
    )
    end_date: Optional[str] = Field(
        default=None, description="End date for observations (YYYY-MM-DD)"
    )


@tool(args_schema=GetOntarioStatisticsInput)
async def get_ontario_statistics(
    area_name: Annotated[str, Field(description="Ontario area name")],
    metric: Annotated[
        Optional[str],
        Field(description="Specific metric to retrieve"),
    ] = None,
    start_date: Annotated[
        Optional[str], Field(description="Start date (YYYY-MM-DD)")
    ] = None,
    end_date: Annotated[Optional[str], Field(description="End date (YYYY-MM-DD)")] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = None,
) -> Dict:
    """
    Get environmental statistics for an Ontario protected area.

    Provides data on:
    - Biodiversity observations (iNaturalist, eBird)
    - Bird observations (eBird)
    - Species counts and diversity
    - Recent wildlife sightings

    Args:
        area_name: Name of the Ontario area
        metric: Optional specific metric to retrieve ('biodiversity', 'birds', etc.)
        start_date: Start date for observations (defaults to last 30 days)
        end_date: End date for observations (defaults to today)

    Returns:
        Dictionary with environmental statistics
    """
    logger.info(
        f"Getting Ontario statistics for: {area_name}, metric: {metric}, dates: {start_date} to {end_date}"
    )

    try:
        # Import database access
        from src.db import get_db
        from sqlalchemy import text

        # Set default dates if not provided
        if not start_date or not end_date:
            from datetime import datetime, timedelta

            end = datetime.now()
            start = end - timedelta(days=30)
            if not end_date:
                end_date = end.strftime("%Y-%m-%d")
            if not start_date:
                start_date = start.strftime("%Y-%m-%d")

        # Look up the area in the database to get geometry
        async with get_db() as db:
            # Try to find the area in various tables
            area_query = """
                SELECT geometry, park_name as name, 'park' as type
                FROM ontario_provincial_parks
                WHERE LOWER(park_name) LIKE LOWER(:area_name)

                UNION ALL

                SELECT geometry, authority_name as name, 'conservation_authority' as type
                FROM ontario_conservation_authorities
                WHERE LOWER(authority_name) LIKE LOWER(:area_name)

                UNION ALL

                SELECT geometry, community_name as name, 'first_nation' as type
                FROM ontario_first_nations
                WHERE LOWER(community_name) LIKE LOWER(:area_name)

                LIMIT 1;
            """

            result = await db.execute(
                text(area_query), {"area_name": f"%{area_name}%"}
            )
            area_row = result.fetchone()

            if not area_row:
                return {
                    "status": "not_found",
                    "message": f"Area '{area_name}' not found in Ontario database. Try using pick_ontario_area first.",
                    "area_name": area_name,
                    "suggestion": "Use pick_ontario_area tool to search for the area",
                }

            # Get the geometry as GeoJSON
            geom_result = await db.execute(
                text("SELECT ST_AsGeoJSON(:geom) as geojson"),
                {"geom": area_row.geometry},
            )
            geom_json = geom_result.scalar()

            import json

            geometry = json.loads(geom_json)

            # Create AOI structure for the handler
            aoi = {
                "name": area_row.name,
                "type": area_row.type,
                "subtype": area_row.type,
                "geometry": geometry,
            }

        # Initialize Ontario data handler
        handler = OntarioDataHandler()

        # Determine which data source to query based on metric
        if metric == "birds" or metric == "bird_observations":
            # Use eBird if API key is configured
            dataset = {"source": "eBird", "type": "observations"}
        else:
            # Default to iNaturalist for general biodiversity
            dataset = {"source": "iNaturalist", "type": "observations"}

        # Pull data using the handler
        result = await handler.pull_data(
            query=f"Get {metric or 'biodiversity'} data for {area_name}",
            aoi=aoi,
            subregion_aois=[],
            subregion="",
            subtype=area_row.type,
            dataset=dataset,
            start_date=start_date,
            end_date=end_date,
        )

        if not result.success:
            return {
                "status": "error",
                "message": result.message,
                "area_name": area_name,
                "metric": metric,
            }

        # Process and summarize the data
        observations = result.data
        species_counts = {}
        for obs in observations:
            species = obs.get("scientific_name") or obs.get("common_name")
            if species:
                species_counts[species] = species_counts.get(species, 0) + 1

        # Sort species by observation count
        top_species = sorted(
            species_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]

        return {
            "status": "success",
            "area_name": area_row.name,
            "area_type": area_row.type,
            "metric": metric or "biodiversity",
            "date_range": {"start": start_date, "end": end_date},
            "data_source": dataset["source"],
            "total_observations": len(observations),
            "unique_species": len(species_counts),
            "top_species": [
                {"species": species, "observation_count": count}
                for species, count in top_species
            ],
            "recent_observations": [
                {
                    "species": obs.get("common_name") or obs.get("scientific_name"),
                    "scientific_name": obs.get("scientific_name"),
                    "date": obs.get("observation_date") or obs.get("observation_datetime"),
                    "source": obs.get("source"),
                }
                for obs in observations[:5]
            ],
            "message": f"Found {len(observations)} observations of {len(species_counts)} species in {area_row.name}",
        }

    except Exception as e:
        logger.error(f"Error getting Ontario statistics: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Error retrieving statistics: {str(e)}",
            "area_name": area_name,
            "metric": metric,
            "note": "Ensure the Ontario database schema is set up and API keys are configured",
        }
