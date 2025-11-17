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
        description="Optional specific metric: 'biodiversity', 'birds', 'forest_cover', 'tree_cover', 'tree_loss', 'deforestation', 'water_quality', 'species_count'",
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
    - Forest cover and tree loss (via Global Forest Watch fallback)

    Automatically falls back to global datasets when Ontario-specific data is not available.
    For example, forest metrics use Global Forest Watch data.

    Args:
        area_name: Name of the Ontario area
        metric: Optional specific metric to retrieve:
            - 'biodiversity': General species observations (iNaturalist)
            - 'birds': Bird-specific observations (eBird)
            - 'forest_cover' / 'tree_cover': Forest coverage (GFW)
            - 'tree_loss' / 'deforestation': Tree cover loss (GFW)
            - 'water_quality': Water quality data (Phase 2)
        start_date: Start date for observations (defaults to last 30 days)
        end_date: End date for observations (defaults to today)

    Returns:
        Dictionary with environmental statistics (source indicated in response)
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

        # Initialize Ontario data handler (with fallback support)
        handler = OntarioDataHandler()

        # Determine which data source to query based on metric
        if metric == "birds" or metric == "bird_observations":
            # Use eBird if API key is configured
            dataset = {"source": "eBird", "type": "observations"}
        elif metric in ["forest_cover", "tree_cover", "tree_loss", "deforestation"]:
            # For forest metrics, use GFW datasets (will trigger fallback)
            from src.tools.datasets_config import DATASETS

            # Find appropriate GFW dataset
            dataset_map = {
                "forest_cover": "Tree cover",
                "tree_cover": "Tree cover",
                "tree_loss": "Tree cover loss",
                "deforestation": "Tree cover loss",
            }
            dataset_name = dataset_map.get(metric, "Tree cover")

            # Get dataset from config
            matching_datasets = [
                ds for ds in DATASETS if ds["dataset_name"] == dataset_name
            ]
            if matching_datasets:
                dataset = matching_datasets[0]
            else:
                dataset = {"source": "iNaturalist", "type": "observations"}
        else:
            # Default to iNaturalist for general biodiversity
            dataset = {"source": "iNaturalist", "type": "observations"}

        # Pull data using the handler (with automatic fallback to global datasets)
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
                "note": "Tried both Ontario-specific and global datasets",
            }

        # Process and summarize the data
        # Check if this is biodiversity data (list of observations) or analytics data (dict)
        is_biodiversity_data = isinstance(result.data, list)

        if is_biodiversity_data:
            # Handle biodiversity observations (from iNaturalist/eBird)
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

            # Determine data source (check if message indicates fallback)
            data_source_note = ""
            if "[Using global dataset]" in result.message:
                data_source_note = " (via global dataset)"

            return {
                "status": "success",
                "area_name": area_row.name,
                "area_type": area_row.type,
                "metric": metric or "biodiversity",
                "date_range": {"start": start_date, "end": end_date},
                "data_source": dataset.get("source", "iNaturalist") + data_source_note,
                "total_observations": len(observations),
                "unique_species": len(species_counts),
                "top_species": [
                    {"species": species, "observation_count": count}
                    for species, count in top_species
                ],
                "recent_observations": [
                    {
                        "species": obs.get("common_name")
                        or obs.get("scientific_name"),
                        "scientific_name": obs.get("scientific_name"),
                        "date": obs.get("observation_date")
                        or obs.get("observation_datetime"),
                        "source": obs.get("source"),
                    }
                    for obs in observations[:5]
                ],
                "message": f"Found {len(observations)} observations of {len(species_counts)} species in {area_row.name}",
            }
        else:
            # Handle analytics data (from GFW - tree cover, forest data, etc.)
            analytics_data = result.data

            return {
                "status": "success",
                "area_name": area_row.name,
                "area_type": area_row.type,
                "metric": metric or "forest_cover",
                "date_range": {"start": start_date, "end": end_date},
                "data_source": dataset.get("dataset_name", "Global Forest Watch"),
                "data_type": "analytics",
                "analytics_data": analytics_data,
                "data_points_count": result.data_points_count,
                "message": result.message.replace("[Using global dataset] ", ""),
                "note": "Using global dataset (Ontario-specific data for this metric not yet available)",
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
