"""Get environmental statistics for Ontario protected areas.

This tool will integrate with environmental datasets once configured.
For now, it provides placeholder functionality.
"""

from typing import Annotated, Dict, Optional

import structlog
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from pydantic import BaseModel, Field

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
        description="Optional specific metric: 'biodiversity', 'forest_cover', 'water_quality', 'species_count'",
    )


@tool(args_schema=GetOntarioStatisticsInput)
async def get_ontario_statistics(
    area_name: Annotated[str, Field(description="Ontario area name")],
    metric: Annotated[
        Optional[str],
        Field(description="Specific metric to retrieve"),
    ] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = None,
) -> Dict:
    """
    Get environmental statistics for an Ontario protected area.

    Provides data on:
    - Biodiversity metrics
    - Forest cover
    - Water quality (where available)
    - Species observations
    - Conservation status

    NOTE: This tool requires integration with environmental datasets.
    Currently returns placeholder data.

    Args:
        area_name: Name of the Ontario area
        metric: Optional specific metric to retrieve

    Returns:
        Dictionary with environmental statistics
    """
    logger.info(f"Getting Ontario statistics for: {area_name}, metric: {metric}")

    # Placeholder response until environmental datasets are integrated
    return {
        "status": "not_implemented",
        "message": "Environmental statistics integration is in progress.",
        "area_name": area_name,
        "requested_metric": metric,
        "next_steps": [
            "Integrate with Ontario Biodiversity Council data",
            "Connect to iNaturalist observations API",
            "Add forest cover change datasets",
            "Include water quality monitoring data",
        ],
        "note": "This tool will provide real environmental data once datasets are configured.",
    }


# Future implementation will include:
# - Integration with Ontario Biodiversity Council
# - iNaturalist species observations
# - Forest Resources Inventory (FRI) data
# - Conservation Authority monitoring data
# - eBird observations
# - Water quality monitoring from PWQMN (Provincial Water Quality Monitoring Network)
