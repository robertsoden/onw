# ontario_handler.py
"""
Ontario Data Handler - Production Template
Integrates multiple Ontario environmental data sources.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
import aiohttp
from dataclasses import dataclass

from tools.data_handlers.base import DataSourceHandler, DataPullResult


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
        max_results: int = 1000
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
            "page": page
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
                
                async with session.get(url, params=params) as response:
                    if response.status != 200:
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
        
        return all_observations[:max_results]
    
    @staticmethod
    def transform_observation(obs: dict) -> dict:
        """Transform iNaturalist observation to standardized format."""
        location_parts = obs.get('location', ',').split(',')
        
        return {
            "source": "iNaturalist",
            "observation_id": str(obs['id']),
            "species_name": obs['taxon']['name'],
            "common_name": obs['taxon'].get('preferred_common_name', ''),
            "scientific_name": obs['taxon']['name'],
            "taxonomy": {
                "rank": obs['taxon']['rank'],
                "iconic_taxon": obs['taxon'].get('iconic_taxon_name'),
                "taxon_id": obs['taxon']['id']
            },
            "observation_date": obs['observed_on'],
            "observation_datetime": obs.get('time_observed_at'),
            "location": {
                "type": "Point",
                "coordinates": [
                    float(location_parts[1]),  # longitude
                    float(location_parts[0])   # latitude
                ]
            },
            "accuracy_meters": obs.get('positional_accuracy'),
            "place_name": obs.get('place_guess'),
            "quality_grade": obs['quality_grade'],
            "license": obs.get('license'),
            "observer": obs['user']['login'],
            "photos": [photo['url'] for photo in obs.get('photos', [])],
            "identifications_count": obs.get('identifications_count', 0),
            "url": f"https://www.inaturalist.org/observations/{obs['id']}"
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
        max_results: int = 1000
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
        params = {
            "back": min(back_days, 30),
            "maxResults": min(max_results, 10000)
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status != 200:
                    return []
                
                return await response.json()
    
    async def get_hotspots(self, region_code: str = None) -> List[Dict]:
        """Get eBird hotspots in region."""
        if region_code is None:
            region_code = self.ONTARIO_REGION
        
        url = f"{self.BASE_URL}/ref/hotspot/{region_code}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    return []
                
                return await response.json()
    
    @staticmethod
    def transform_observation(obs: dict) -> dict:
        """Transform eBird observation to standardized format."""
        return {
            "source": "eBird",
            "observation_id": obs['subId'],
            "species_code": obs['speciesCode'],
            "common_name": obs['comName'],
            "scientific_name": obs['sciName'],
            "observation_datetime": obs['obsDt'],
            "location": {
                "type": "Point",
                "coordinates": [obs['lng'], obs['lat']]
            },
            "location_name": obs['locName'],
            "location_id": obs['locId'],
            "count": obs.get('howMany'),
            "valid": obs.get('obsValid', True),
            "reviewed": obs.get('obsReviewed', False),
            "url": f"https://ebird.org/checklist/{obs['subId']}"
        }


class PWQMNClient:
    """Client for Provincial Water Quality Monitoring Network data."""
    
    STATIONS_URL = "https://files.ontario.ca/moe_mapping/downloads/2Water/PWQMN/PWQMN_Stations.csv"
    DATA_URL_2019_2021 = "https://files.ontario.ca/moe_mapping/downloads/2Water/PWQMN/PWQMN-2019_2021Mar.csv"
    
    async def get_stations(self) -> List[Dict]:
        """Download and parse PWQMN stations."""
        import pandas as pd
        
        # Note: In production, implement caching
        stations_df = pd.read_csv(self.STATIONS_URL)
        
        return stations_df.to_dict('records')
    
    async def get_measurements(
        self,
        start_date: str = None,
        end_date: str = None
    ) -> List[Dict]:
        """Download and parse PWQMN measurements."""
        import pandas as pd
        
        # Note: In production, implement caching and incremental updates
        measurements_df = pd.read_csv(self.DATA_URL_2019_2021)
        
        if start_date:
            measurements_df = measurements_df[
                pd.to_datetime(measurements_df['SAMPLE_DATE']) >= start_date
            ]
        
        if end_date:
            measurements_df = measurements_df[
                pd.to_datetime(measurements_df['SAMPLE_DATE']) <= end_date
            ]
        
        return measurements_df.to_dict('records')


class DataStreamClient:
    """Client for DataStream OData v4 API."""
    
    BASE_URL = "https://api.datastream.org/v1/odata/v4"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"x-api-key": api_key}
    
    async def get_observations(
        self,
        doi: str,
        characteristic: str = None,
        location_id: int = None,
        start_date: str = None,
        end_date: str = None
    ) -> List[Dict]:
        """
        Get water quality observations from DataStream.
        
        Args:
            doi: Dataset DOI (e.g., "10.25976/tnw0-3x43" for PWQMN)
            characteristic: Parameter name (e.g., "Total Phosphorus")
            location_id: Specific location ID
            start_date: ISO format date
            end_date: ISO format date
        
        Returns:
            List of observation dictionaries
        """
        all_observations = []
        url = f"{self.BASE_URL}/Observations"
        
        # Build filter
        filters = [f"DOI eq '{doi}'"]
        
        if characteristic:
            filters.append(f"CharacteristicName eq '{characteristic}'")
        
        if location_id:
            filters.append(f"LocationId eq {location_id}")
        
        if start_date:
            filters.append(f"ActivityStartDate ge {start_date}")
        
        if end_date:
            filters.append(f"ActivityStartDate le {end_date}")
        
        filter_string = " and ".join(filters)
        
        params = {
            "$filter": filter_string,
            "$top": 1000
        }
        
        async with aiohttp.ClientSession() as session:
            while url:
                async with session.get(url, headers=self.headers, params=params if params else None) as response:
                    if response.status != 200:
                        break
                    
                    data = await response.json()
                    all_observations.extend(data.get('value', []))
                    
                    # Get next page
                    url = data.get('@odata.nextLink')
                    params = None  # nextLink includes all params
                    
                    # Rate limiting
                    await asyncio.sleep(0.5)
        
        return all_observations


class OntarioDataHandler(DataSourceHandler):
    """
    Unified data handler for Ontario-specific environmental data sources.
    """
    
    def __init__(self, config: OntarioConfig = None):
        self.config = config or OntarioConfig()
        self.inat_client = INaturalistClient(rate_limit=self.config.inat_rate_limit)
        self.ebird_client = EBirdClient(self.config.ebird_api_key) if self.config.ebird_api_key else None
        self.pwqmn_client = PWQMNClient()
        self.datastream_client = DataStreamClient(self.config.datastream_api_key) if self.config.datastream_api_key else None
    
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
            "OntarioParks"
        ]
        
        if not isinstance(dataset, dict):
            return False
        
        return dataset.get("source") in ontario_sources
    
    async def pull_data(
        self,
        aoi: dict,
        dataset: dict,
        start_date: str,
        end_date: str
    ) -> DataPullResult:
        """
        Pull data from Ontario sources based on dataset type.
        
        Args:
            aoi: Area of interest (GeoJSON geometry)
            dataset: Dataset specification with 'source' and 'type'
            start_date: ISO format date string
            end_date: ISO format date string
        
        Returns:
            DataPullResult with observations
        """
        source = dataset.get("source")
        
        try:
            if source == "iNaturalist":
                return await self._pull_inat_data(aoi, start_date, end_date)
            elif source == "eBird":
                if not self.ebird_client:
                    return DataPullResult(
                        success=False,
                        data=[],
                        error="eBird API key not configured"
                    )
                return await self._pull_ebird_data(aoi, start_date, end_date)
            elif source == "PWQMN":
                return await self._pull_pwqmn_data(aoi, start_date, end_date)
            elif source == "DataStream":
                if not self.datastream_client:
                    return DataPullResult(
                        success=False,
                        data=[],
                        error="DataStream API key not configured"
                    )
                return await self._pull_datastream_data(aoi, start_date, end_date, dataset)
            else:
                return DataPullResult(
                    success=False,
                    data=[],
                    error=f"Unsupported Ontario data source: {source}"
                )
        
        except Exception as e:
            return DataPullResult(
                success=False,
                data=[],
                error=str(e)
            )
    
    async def _pull_inat_data(
        self, aoi: dict, start_date: str, end_date: str
    ) -> DataPullResult:
        """Pull iNaturalist observations for AOI."""
        # Extract bounding box from AOI
        bounds = self._get_bounds_from_aoi(aoi)
        
        try:
            observations = await self.inat_client.get_observations(
                bounds=bounds,
                start_date=start_date,
                end_date=end_date,
                quality_grade="research"
            )
            
            # Transform observations
            transformed = [
                self.inat_client.transform_observation(obs)
                for obs in observations
            ]
            
            return DataPullResult(
                success=True,
                data=transformed,
                metadata={
                    "source": "iNaturalist",
                    "count": len(transformed),
                    "date_range": f"{start_date} to {end_date}"
                }
            )
        
        except Exception as e:
            return DataPullResult(
                success=False,
                data=[],
                error=f"iNaturalist error: {str(e)}"
            )
    
    async def _pull_ebird_data(
        self, aoi: dict, start_date: str, end_date: str
    ) -> DataPullResult:
        """Pull eBird observations for AOI."""
        # Calculate days back from date range
        from datetime import datetime
        
        end = datetime.fromisoformat(end_date)
        start = datetime.fromisoformat(start_date)
        days_back = min((end - start).days, 30)
        
        try:
            observations = await self.ebird_client.get_recent_observations(
                back_days=days_back,
                max_results=1000
            )
            
            # Filter by AOI bounds
            bounds = self._get_bounds_from_aoi(aoi)
            filtered = self._filter_by_bounds(observations, bounds)
            
            # Transform observations
            transformed = [
                self.ebird_client.transform_observation(obs)
                for obs in filtered
            ]
            
            return DataPullResult(
                success=True,
                data=transformed,
                metadata={
                    "source": "eBird",
                    "count": len(transformed),
                    "date_range": f"{start_date} to {end_date}"
                }
            )
        
        except Exception as e:
            return DataPullResult(
                success=False,
                data=[],
                error=f"eBird error: {str(e)}"
            )
    
    async def _pull_pwqmn_data(
        self, aoi: dict, start_date: str, end_date: str
    ) -> DataPullResult:
        """Pull PWQMN water quality data for AOI."""
        try:
            # Get stations within AOI
            stations = await self.pwqmn_client.get_stations()
            bounds = self._get_bounds_from_aoi(aoi)
            
            # Filter stations by bounds
            stations_in_aoi = [
                s for s in stations
                if self._point_in_bounds(
                    (s['LATITUDE'], s['LONGITUDE']),
                    bounds
                )
            ]
            
            if not stations_in_aoi:
                return DataPullResult(
                    success=True,
                    data=[],
                    metadata={"message": "No PWQMN stations in AOI"}
                )
            
            # Get measurements for these stations
            measurements = await self.pwqmn_client.get_measurements(
                start_date=start_date,
                end_date=end_date
            )
            
            station_ids = {s['STN'] for s in stations_in_aoi}
            relevant_measurements = [
                m for m in measurements
                if m['STN'] in station_ids
            ]
            
            return DataPullResult(
                success=True,
                data=relevant_measurements,
                metadata={
                    "source": "PWQMN",
                    "stations": len(stations_in_aoi),
                    "measurements": len(relevant_measurements)
                }
            )
        
        except Exception as e:
            return DataPullResult(
                success=False,
                data=[],
                error=f"PWQMN error: {str(e)}"
            )
    
    async def _pull_datastream_data(
        self, aoi: dict, start_date: str, end_date: str, dataset: dict
    ) -> DataPullResult:
        """Pull water quality data from DataStream."""
        doi = dataset.get("doi", "10.25976/tnw0-3x43")  # Default to PWQMN
        characteristic = dataset.get("parameter")
        
        try:
            observations = await self.datastream_client.get_observations(
                doi=doi,
                characteristic=characteristic,
                start_date=start_date,
                end_date=end_date
            )
            
            return DataPullResult(
                success=True,
                data=observations,
                metadata={
                    "source": "DataStream",
                    "doi": doi,
                    "count": len(observations)
                }
            )
        
        except Exception as e:
            return DataPullResult(
                success=False,
                data=[],
                error=f"DataStream error: {str(e)}"
            )
    
    @staticmethod
    def _get_bounds_from_aoi(aoi: dict) -> tuple[float, float, float, float]:
        """Extract bounding box from GeoJSON AOI."""
        # Simple implementation - assumes Polygon
        coords = aoi['coordinates'][0]
        
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        
        return (
            min(lats),  # swlat
            min(lons),  # swlng
            max(lats),  # nelat
            max(lons)   # nelng
        )
    
    @staticmethod
    def _point_in_bounds(
        point: tuple[float, float],
        bounds: tuple[float, float, float, float]
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
            lat = obs.get('lat')
            lon = obs.get('lng')
            
            if lat is not None and lon is not None:
                if OntarioDataHandler._point_in_bounds((lat, lon), bounds):
                    filtered.append(obs)
        
        return filtered


# Example usage
async def main():
    """Example usage of Ontario Data Handler."""
    
    # Configure with API keys
    config = OntarioConfig(
        ebird_api_key="your_ebird_key_here",
        datastream_api_key="your_datastream_key_here"
    )
    
    handler = OntarioDataHandler(config)
    
    # Define Algonquin Park AOI
    algonquin_aoi = {
        "type": "Polygon",
        "coordinates": [[
            [-78.5, 45.5],
            [-78.5, 46.0],
            [-77.5, 46.0],
            [-77.5, 45.5],
            [-78.5, 45.5]
        ]]
    }
    
    # Pull iNaturalist data
    inat_dataset = {"source": "iNaturalist", "type": "observations"}
    result = await handler.pull_data(
        aoi=algonquin_aoi,
        dataset=inat_dataset,
        start_date="2024-06-01",
        end_date="2024-06-30"
    )
    
    if result.success:
        print(f"Found {len(result.data)} observations")
        for obs in result.data[:5]:
            print(f"- {obs['common_name']} on {obs['observation_date']}")
    else:
        print(f"Error: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
