"""Ontario Data Handler - Production Implementation

Integrates multiple Ontario environmental data sources including:
- iNaturalist (biodiversity observations)
- eBird (bird observations)
- GBIF (global biodiversity)
- PWQMN (water quality monitoring)
- DataStream (standardized water quality)

Includes fallback to global datasets (GFW Analytics) when Ontario-specific
data is not available or insufficient.

This handler uses the ontario-environmental-data library for:
- API clients (iNaturalist, eBird)
- Configuration management
- Geometry utilities (bounds extraction, filtering)
"""

import os
from typing import Any, Dict, List, Optional

# Import from ontario-environmental-data library
from ontario_data import OntarioConfig, filter_by_bounds, get_bounds_from_aoi
from ontario_data.sources import EBirdClient, INaturalistClient

from src.tools.data_handlers.base import DataPullResult, DataSourceHandler
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class OntarioDataHandler(DataSourceHandler):
    """
    Unified data handler for Ontario-specific environmental data sources.

    Supports fallback to global datasets (GFW Analytics) when Ontario-specific
    data is not available or returns insufficient results.
    """

    def __init__(self, config: OntarioConfig = None):
        # Get API keys from environment if not provided in config
        ebird_key = os.getenv("EBIRD_API_KEY")
        datastream_key = os.getenv("DATASTREAM_API_KEY")

        if config:
            self.config = config
            # Override with env vars if available
            if ebird_key:
                self.config.ebird_api_key = ebird_key
            if datastream_key:
                self.config.datastream_api_key = datastream_key
        else:
            self.config = OntarioConfig(
                ebird_api_key=ebird_key, datastream_api_key=datastream_key
            )

        self.inat_client = INaturalistClient(rate_limit=self.config.inat_rate_limit)
        self.ebird_client = (
            EBirdClient(self.config.ebird_api_key)
            if self.config.ebird_api_key
            else None
        )

        # Fallback handler for global datasets
        self.fallback_handler = None  # Initialized lazily to avoid circular imports

    def can_handle(self, dataset: Any) -> bool:
        """Check if dataset is Ontario-specific."""
        ontario_sources = [
            "iNaturalist",
            "eBird",
            "GBIF",
            "PWQMN",
            "DataStream",
            "ConservationOntario",
            "OntarioFRI",
            "OntarioParks",
        ]

        if not isinstance(dataset, dict):
            return False

        return dataset.get("source") in ontario_sources

    def _get_fallback_handler(self):
        """Get or initialize the fallback handler for global datasets."""
        if self.fallback_handler is None:
            # Import here to avoid circular imports
            from src.tools.data_handlers.analytics_handler import AnalyticsHandler

            self.fallback_handler = AnalyticsHandler()
        return self.fallback_handler

    async def pull_data(
        self,
        query: str,
        aoi: Dict,
        subregion_aois: List[Dict],
        subregion: str,
        subtype: str,
        dataset: Dict,
        start_date: str,
        end_date: str,
    ) -> DataPullResult:
        """
        Pull data from Ontario sources based on dataset type.

        Falls back to global datasets (GFW Analytics) when:
        - Ontario-specific source is not available
        - Ontario source returns no data
        - Query is for data types not in Ontario sources (e.g., forest cover, tree loss)

        Args:
            query: User's query string
            aoi: Area of interest dictionary
            subregion_aois: List of subregion AOIs
            subregion: Subregion identifier
            subtype: Subtype of area
            dataset: Dataset specification with 'source' and 'type'
            start_date: ISO format date string
            end_date: ISO format date string

        Returns:
            DataPullResult with observations (from Ontario or global sources)
        """
        source = dataset.get("source")

        logger.info(
            f"Ontario handler attempting {source} data for query: {query[:100]}..."
        )

        # Try Ontario-specific sources first
        try:
            if source == "iNaturalist":
                result = await self._pull_inat_data(aoi, start_date, end_date)
                if result.success and result.data_points_count > 0:
                    return result
                logger.info(f"iNaturalist returned no data, trying fallback...")

            elif source == "eBird":
                if not self.ebird_client:
                    logger.info("eBird API key not configured, trying fallback...")
                else:
                    result = await self._pull_ebird_data(aoi, start_date, end_date)
                    if result.success and result.data_points_count > 0:
                        return result
                    logger.info(f"eBird returned no data, trying fallback...")

            else:
                # Source not implemented in Ontario handler
                logger.info(
                    f"Ontario source '{source}' not yet implemented, trying fallback..."
                )

        except Exception as e:
            logger.warning(f"Error in Ontario handler: {e}, trying fallback...")

        # Try fallback to global datasets
        fallback_handler = self._get_fallback_handler()

        if fallback_handler.can_handle(dataset):
            logger.info(
                f"Falling back to global datasets (GFW Analytics) for {dataset.get('dataset_name', source)}"
            )
            try:
                fallback_result = await fallback_handler.pull_data(
                    query=query,
                    aoi=aoi,
                    subregion_aois=subregion_aois,
                    subregion=subregion,
                    subtype=subtype,
                    dataset=dataset,
                    start_date=start_date,
                    end_date=end_date,
                )

                # Add note to message that this came from fallback
                if fallback_result.success:
                    fallback_result.message = (
                        f"[Using global dataset] {fallback_result.message}"
                    )

                return fallback_result

            except Exception as e:
                logger.error(f"Fallback handler also failed: {e}", exc_info=True)

        # No data available from any source
        return DataPullResult(
            success=False,
            data=[],
            message=f"No data available for {source}. Ontario-specific data not found and no global dataset fallback available.",
            data_points_count=0,
        )

    async def _pull_inat_data(
        self, aoi: dict, start_date: str, end_date: str
    ) -> DataPullResult:
        """Pull iNaturalist observations for AOI."""
        # Extract bounding box from AOI geometry
        try:
            bounds = get_bounds_from_aoi(aoi)
        except Exception as e:
            return DataPullResult(
                success=False,
                data=[],
                message=f"Error extracting bounds from AOI: {str(e)}",
                data_points_count=0,
            )

        try:
            observations = await self.inat_client.get_observations(
                bounds=bounds,
                start_date=start_date,
                end_date=end_date,
                quality_grade="research",
            )

            # Transform observations
            transformed = [
                self.inat_client.transform_observation(obs) for obs in observations
            ]

            logger.info(
                f"Successfully fetched {len(transformed)} iNaturalist observations"
            )

            return DataPullResult(
                success=True,
                data=transformed,
                message=f"Successfully retrieved {len(transformed)} research-grade observations from iNaturalist",
                data_points_count=len(transformed),
            )

        except Exception as e:
            logger.error(f"iNaturalist error: {e}", exc_info=True)
            return DataPullResult(
                success=False,
                data=[],
                message=f"iNaturalist API error: {str(e)}",
                data_points_count=0,
            )

    async def _pull_ebird_data(
        self, aoi: dict, start_date: str, end_date: str
    ) -> DataPullResult:
        """Pull eBird observations for AOI."""
        # Calculate days back from date range
        try:
            end = datetime.fromisoformat(end_date)
            start = datetime.fromisoformat(start_date)
            days_back = min((end - start).days, 30)
        except Exception as e:
            return DataPullResult(
                success=False,
                data=[],
                message=f"Error parsing dates: {str(e)}",
                data_points_count=0,
            )

        try:
            observations = await self.ebird_client.get_recent_observations(
                back_days=days_back, max_results=1000
            )

            # Filter by AOI bounds
            bounds = get_bounds_from_aoi(aoi)
            filtered = filter_by_bounds(observations, bounds)

            # Transform observations
            transformed = [
                self.ebird_client.transform_observation(obs) for obs in filtered
            ]

            logger.info(f"Successfully fetched {len(transformed)} eBird observations")

            return DataPullResult(
                success=True,
                data=transformed,
                message=f"Successfully retrieved {len(transformed)} bird observations from eBird",
                data_points_count=len(transformed),
            )

        except Exception as e:
            logger.error(f"eBird error: {e}", exc_info=True)
            return DataPullResult(
                success=False,
                data=[],
                message=f"eBird API error: {str(e)}",
                data_points_count=0,
            )
