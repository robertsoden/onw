"""Ontario Data Handler - Production Implementation

Integrates multiple Ontario environmental data sources including:
- iNaturalist (biodiversity observations)
- eBird (bird observations)
- GBIF (global biodiversity)
- PWQMN (water quality monitoring)
- DataStream (standardized water quality)
"""

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
from pydantic import BaseModel

from src.tools.data_handlers.base import DataPullResult, DataSourceHandler
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class OntarioConfig:
    """Configuration for Ontario data sources."""

    ebird_api_key: Optional[str] = None
    datastream_api_key: Optional[str] = None
    inat_rate_limit: int = 60  # requests per minute
    cache_ttl_hours: int = 24


class INaturalistClient:
    """Client for iNaturalist API v1."""

    BASE_URL = "https://api.inaturalist.org/v1"
    ONTARIO_PLACE_ID = 6942

    def __init__(self, rate_limit: int = 60):
        self.rate_limit = rate_limit
        self.last_request = datetime.now()

    async def _rate_limit_wait(self):
        """Implement rate limiting."""
        now = datetime.now()
        time_since_last = (now - self.last_request).total_seconds()
        min_interval = 60.0 / self.rate_limit

        if time_since_last < min_interval:
            await asyncio.sleep(min_interval - time_since_last)

        self.last_request = datetime.now()

    async def get_observations(
        self,
        bounds: tuple[float, float, float, float],  # swlat, swlng, nelat, nelng
        start_date: str = None,
        end_date: str = None,
        quality_grade: str = "research",
        per_page: int = 200,
        max_results: int = 1000,
    ) -> List[Dict]:
        """
        Get iNaturalist observations within bounds.

        Args:
            bounds: (swlat, swlng, nelat, nelng)
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
            quality_grade: research, needs_id, or casual
            per_page: Results per page (max 200)
            max_results: Maximum total results to fetch

        Returns:
            List of observation dictionaries
        """
        all_observations = []
        page = 1

        params = {
            "swlat": bounds[0],
            "swlng": bounds[1],
            "nelat": bounds[2],
            "nelng": bounds[3],
            "quality_grade": quality_grade,
            "geo": "true",
            "photos": "true",
            "per_page": per_page,
            "page": page,
        }

        if start_date:
            params["d1"] = start_date
        if end_date:
            params["d2"] = end_date

        async with aiohttp.ClientSession() as session:
            while len(all_observations) < max_results:
                await self._rate_limit_wait()

                params["page"] = page
                url = f"{self.BASE_URL}/observations"

                try:
                    async with session.get(url, params=params) as response:
                        if response.status != 200:
                            logger.warning(
                                f"iNaturalist API returned status {response.status}"
                            )
                            break

                        data = await response.json()
                        results = data.get("results", [])

                        if not results:
                            break

                        all_observations.extend(results)

                        # Check if we've reached the end
                        if len(results) < per_page:
                            break

                        page += 1
                except Exception as e:
                    logger.error(f"Error fetching iNaturalist data: {e}")
                    break

        return all_observations[:max_results]

    @staticmethod
    def transform_observation(obs: dict) -> dict:
        """Transform iNaturalist observation to standardized format."""
        location_parts = obs.get("location", ",").split(",")

        return {
            "source": "iNaturalist",
            "observation_id": str(obs["id"]),
            "species_name": obs["taxon"]["name"],
            "common_name": obs["taxon"].get("preferred_common_name", ""),
            "scientific_name": obs["taxon"]["name"],
            "taxonomy": {
                "rank": obs["taxon"]["rank"],
                "iconic_taxon": obs["taxon"].get("iconic_taxon_name"),
                "taxon_id": obs["taxon"]["id"],
            },
            "observation_date": obs["observed_on"],
            "observation_datetime": obs.get("time_observed_at"),
            "location": {
                "type": "Point",
                "coordinates": [
                    float(location_parts[1]),  # longitude
                    float(location_parts[0]),  # latitude
                ],
            },
            "accuracy_meters": obs.get("positional_accuracy"),
            "place_name": obs.get("place_guess"),
            "quality_grade": obs["quality_grade"],
            "license": obs.get("license"),
            "observer": obs["user"]["login"],
            "photos": [photo["url"] for photo in obs.get("photos", [])],
            "identifications_count": obs.get("identifications_count", 0),
            "url": f"https://www.inaturalist.org/observations/{obs['id']}",
        }


class EBirdClient:
    """Client for eBird API 2.0."""

    BASE_URL = "https://api.ebird.org/v2"
    ONTARIO_REGION = "CA-ON"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"x-ebirdapitoken": api_key}

    async def get_recent_observations(
        self,
        region_code: str = None,
        back_days: int = 30,
        max_results: int = 1000,
    ) -> List[Dict]:
        """
        Get recent eBird observations for Ontario or specific region.

        Args:
            region_code: Regional code (default CA-ON for Ontario)
            back_days: Days back (1-30)
            max_results: Maximum results (1-10000)

        Returns:
            List of observation dictionaries
        """
        if region_code is None:
            region_code = self.ONTARIO_REGION

        url = f"{self.BASE_URL}/data/obs/{region_code}/recent"
        params = {"back": min(back_days, 30), "maxResults": min(max_results, 10000)}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=self.headers, params=params
                ) as response:
                    if response.status != 200:
                        logger.warning(f"eBird API returned status {response.status}")
                        return []

                    return await response.json()
        except Exception as e:
            logger.error(f"Error fetching eBird data: {e}")
            return []

    @staticmethod
    def transform_observation(obs: dict) -> dict:
        """Transform eBird observation to standardized format."""
        return {
            "source": "eBird",
            "observation_id": obs["subId"],
            "species_code": obs["speciesCode"],
            "common_name": obs["comName"],
            "scientific_name": obs["sciName"],
            "observation_datetime": obs["obsDt"],
            "location": {"type": "Point", "coordinates": [obs["lng"], obs["lat"]]},
            "location_name": obs["locName"],
            "location_id": obs["locId"],
            "count": obs.get("howMany"),
            "valid": obs.get("obsValid", True),
            "reviewed": obs.get("obsReviewed", False),
            "url": f"https://ebird.org/checklist/{obs['subId']}",
        }


class OntarioDataHandler(DataSourceHandler):
    """
    Unified data handler for Ontario-specific environmental data sources.
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
            DataPullResult with observations
        """
        source = dataset.get("source")

        logger.info(
            f"Ontario handler pulling {source} data for query: {query[:100]}..."
        )

        try:
            if source == "iNaturalist":
                return await self._pull_inat_data(aoi, start_date, end_date)
            elif source == "eBird":
                if not self.ebird_client:
                    return DataPullResult(
                        success=False,
                        data=[],
                        message="eBird API key not configured. Set EBIRD_API_KEY environment variable.",
                        data_points_count=0,
                    )
                return await self._pull_ebird_data(aoi, start_date, end_date)
            else:
                return DataPullResult(
                    success=False,
                    data=[],
                    message=f"Ontario data source '{source}' not yet implemented. Available: iNaturalist, eBird",
                    data_points_count=0,
                )

        except Exception as e:
            logger.error(f"Error in Ontario handler: {e}", exc_info=True)
            return DataPullResult(
                success=False,
                data=[],
                message=f"Error pulling {source} data: {str(e)}",
                data_points_count=0,
            )

    async def _pull_inat_data(
        self, aoi: dict, start_date: str, end_date: str
    ) -> DataPullResult:
        """Pull iNaturalist observations for AOI."""
        # Extract bounding box from AOI geometry
        try:
            bounds = self._get_bounds_from_aoi(aoi)
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
            bounds = self._get_bounds_from_aoi(aoi)
            filtered = self._filter_by_bounds(observations, bounds)

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

    @staticmethod
    def _get_bounds_from_aoi(aoi: dict) -> tuple[float, float, float, float]:
        """Extract bounding box from AOI geometry."""
        # Handle different AOI formats
        if "geometry" in aoi:
            geometry = aoi["geometry"]
        else:
            geometry = aoi

        # Extract coordinates
        if geometry.get("type") == "Polygon":
            coords = geometry["coordinates"][0]
        elif geometry.get("type") == "MultiPolygon":
            # Use first polygon
            coords = geometry["coordinates"][0][0]
        elif geometry.get("type") == "Point":
            # Create small bounds around point
            lon, lat = geometry["coordinates"]
            buffer = 0.1  # ~11km
            return (lat - buffer, lon - buffer, lat + buffer, lon + buffer)
        else:
            raise ValueError(f"Unsupported geometry type: {geometry.get('type')}")

        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]

        return (
            min(lats),  # swlat
            min(lons),  # swlng
            max(lats),  # nelat
            max(lons),  # nelng
        )

    @staticmethod
    def _point_in_bounds(
        point: tuple[float, float], bounds: tuple[float, float, float, float]
    ) -> bool:
        """Check if point (lat, lon) is within bounds."""
        lat, lon = point
        swlat, swlng, nelat, nelng = bounds

        return swlat <= lat <= nelat and swlng <= lon <= nelng

    @staticmethod
    def _filter_by_bounds(observations: List[Dict], bounds: tuple) -> List[Dict]:
        """Filter observations by bounding box."""
        filtered = []

        for obs in observations:
            lat = obs.get("lat")
            lon = obs.get("lng")

            if lat is not None and lon is not None:
                if OntarioDataHandler._point_in_bounds((lat, lon), bounds):
                    filtered.append(obs)

        return filtered
