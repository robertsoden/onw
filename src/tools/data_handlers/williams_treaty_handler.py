"""Williams Treaty Data Handler - Database-backed Ontario data sources

Handles queries for:
- First Nations water advisories
- Fire incidents and danger ratings
- Indigenous infrastructure projects
- Community well-being indicators

Data is pre-loaded into PostGIS database and queried spatially.
Ported from: https://github.com/robertsoden/williams-treaties
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
from sqlalchemy import text

from src.tools.data_handlers.base import DataPullResult, DataSourceHandler
from src.utils.database import get_db_connection
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class WilliamsTreatyDataHandler(DataSourceHandler):
    """
    Handler for Williams Treaty data sources stored in the database.

    Supports:
    - Water advisories (static data from Indigenous Services Canada)
    - Fire incidents (historical Ontario fire data)
    - Fire danger (current CWFIS data - hybrid: DB + API)
    - Infrastructure projects (ICIM data)
    - Community well-being (CWB scores from Statistics Canada)
    """

    # CWFIS API endpoint for current fire danger
    CWFIS_BASE_URL = "https://cwfis.cfs.nrcan.gc.ca/geoserver/public/ows"

    def can_handle(self, dataset: Any) -> bool:
        """Check if dataset is a Williams Treaty data source."""
        williams_sources = [
            "WaterAdvisories",
            "FireIncidents",
            "FireDanger",
            "Infrastructure",
            "CommunityWellbeing",
            "FirstNationsData",
        ]

        if not isinstance(dataset, dict):
            return False

        return dataset.get("source") in williams_sources

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
        Pull Williams Treaty data based on source type.

        Args:
            query: User's query string
            aoi: Area of interest dictionary with geometry
            subregion_aois: List of subregion AOIs
            subregion: Subregion identifier
            subtype: Subtype of area
            dataset: Dataset specification with 'source' and optional 'type'
            start_date: ISO format date string
            end_date: ISO format date string

        Returns:
            DataPullResult with queried data
        """
        source = dataset.get("source")
        data_type = dataset.get("type", "").lower()

        logger.info(f"Williams Treaty handler pulling {source} data for query: {query[:100]}...")

        try:
            if source == "WaterAdvisories":
                return await self._pull_water_advisories(aoi, start_date, end_date)
            elif source == "FireIncidents":
                return await self._pull_fire_incidents(aoi, start_date, end_date)
            elif source == "FireDanger":
                return await self._pull_fire_danger(aoi, start_date, end_date)
            elif source == "Infrastructure":
                return await self._pull_infrastructure(aoi, data_type)
            elif source == "CommunityWellbeing":
                return await self._pull_community_wellbeing(aoi)
            else:
                return DataPullResult(
                    success=False,
                    data=[],
                    message=f"Unknown Williams Treaty data source: {source}",
                    data_points_count=0,
                )

        except Exception as e:
            logger.error(f"Error pulling Williams Treaty data: {e}", exc_info=True)
            return DataPullResult(
                success=False,
                data=[],
                message=f"Error querying {source}: {str(e)}",
                data_points_count=0,
            )

    async def _pull_water_advisories(
        self, aoi: Dict, start_date: str, end_date: str
    ) -> DataPullResult:
        """Query water advisories from database."""
        try:
            # Extract geometry from AOI
            geom_text = self._aoi_to_wkt(aoi)

            async with get_db_connection() as conn:
                # Query water advisories within AOI
                query = text("""
                    SELECT
                        advisory_id,
                        community_name,
                        first_nation,
                        advisory_type,
                        advisory_date,
                        lift_date,
                        duration_days,
                        is_active,
                        reason,
                        water_system_name,
                        population_affected,
                        ST_AsGeoJSON(geometry)::json as location,
                        data_source
                    FROM ontario_water_advisories
                    WHERE ST_Intersects(
                        geometry,
                        ST_GeomFromText(:geom, 4326)
                    )
                    AND advisory_date >= :start_date
                    AND (lift_date IS NULL OR lift_date <= :end_date)
                    ORDER BY duration_days DESC NULLS FIRST, advisory_date DESC
                    LIMIT 1000
                """)

                result = await conn.execute(
                    query,
                    {
                        "geom": geom_text,
                        "start_date": start_date,
                        "end_date": end_date,
                    },
                )
                rows = result.fetchall()

                # Transform to standardized format
                advisories = []
                for row in rows:
                    advisories.append({
                        "source": "Water Advisories",
                        "advisory_id": row.advisory_id,
                        "community": row.community_name,
                        "first_nation": row.first_nation,
                        "type": row.advisory_type,
                        "issued_date": str(row.advisory_date),
                        "lifted_date": str(row.lift_date) if row.lift_date else None,
                        "duration_days": row.duration_days,
                        "is_active": row.is_active,
                        "reason": row.reason,
                        "water_system": row.water_system_name,
                        "population_affected": row.population_affected,
                        "location": row.location,
                        "data_source": row.data_source,
                    })

                active_count = sum(1 for a in advisories if a["is_active"])
                message = f"Found {len(advisories)} water advisories ({active_count} active)"

                return DataPullResult(
                    success=True,
                    data=advisories,
                    message=message,
                    data_points_count=len(advisories),
                )

        except Exception as e:
            logger.error(f"Error querying water advisories: {e}", exc_info=True)
            return DataPullResult(
                success=False,
                data=[],
                message=f"Database error: {str(e)}",
                data_points_count=0,
            )

    async def _pull_fire_incidents(
        self, aoi: Dict, start_date: str, end_date: str
    ) -> DataPullResult:
        """Query historical fire incidents from database."""
        try:
            geom_text = self._aoi_to_wkt(aoi)

            # Parse date range to years
            start_year = datetime.fromisoformat(start_date).year
            end_year = datetime.fromisoformat(end_date).year

            async with get_db_connection() as conn:
                query = text("""
                    SELECT
                        fire_id,
                        fire_number,
                        fire_year,
                        fire_name,
                        ignition_date,
                        discovery_date,
                        under_control_date,
                        out_date,
                        area_ha,
                        fire_cause,
                        fire_region,
                        fire_zone,
                        fuel_type,
                        suppression_cost,
                        ST_AsGeoJSON(geometry)::json as perimeter,
                        ST_AsGeoJSON(point_geometry)::json as origin_point,
                        data_source
                    FROM ontario_fire_incidents
                    WHERE ST_Intersects(
                        geometry,
                        ST_GeomFromText(:geom, 4326)
                    )
                    AND fire_year >= :start_year
                    AND fire_year <= :end_year
                    ORDER BY fire_year DESC, area_ha DESC
                    LIMIT 1000
                """)

                result = await conn.execute(
                    query,
                    {"geom": geom_text, "start_year": start_year, "end_year": end_year},
                )
                rows = result.fetchall()

                # Transform to standardized format
                fires = []
                for row in rows:
                    fires.append({
                        "source": "Ontario Fire History",
                        "fire_id": row.fire_id,
                        "fire_number": row.fire_number,
                        "year": row.fire_year,
                        "name": row.fire_name,
                        "ignition_date": str(row.ignition_date) if row.ignition_date else None,
                        "discovery_date": str(row.discovery_date) if row.discovery_date else None,
                        "control_date": str(row.under_control_date) if row.under_control_date else None,
                        "out_date": str(row.out_date) if row.out_date else None,
                        "area_hectares": float(row.area_ha) if row.area_ha else 0,
                        "cause": row.fire_cause,
                        "region": row.fire_region,
                        "zone": row.fire_zone,
                        "fuel_type": row.fuel_type,
                        "suppression_cost": float(row.suppression_cost) if row.suppression_cost else None,
                        "perimeter": row.perimeter,
                        "origin": row.origin_point,
                        "data_source": row.data_source,
                    })

                total_area = sum(f["area_hectares"] for f in fires)
                message = f"Found {len(fires)} fire incidents covering {total_area:.1f} hectares"

                return DataPullResult(
                    success=True,
                    data=fires,
                    message=message,
                    data_points_count=len(fires),
                )

        except Exception as e:
            logger.error(f"Error querying fire incidents: {e}", exc_info=True)
            return DataPullResult(
                success=False,
                data=[],
                message=f"Database error: {str(e)}",
                data_points_count=0,
            )

    async def _pull_fire_danger(
        self, aoi: Dict, start_date: str, end_date: str
    ) -> DataPullResult:
        """
        Query current fire danger ratings.

        First checks database for recent data, then queries CWFIS API if needed.
        """
        try:
            # Check database for recent fire danger data (last 7 days)
            recent_date = (datetime.now() - timedelta(days=7)).date()
            geom_text = self._aoi_to_wkt(aoi)

            async with get_db_connection() as conn:
                query = text("""
                    SELECT
                        station_id,
                        station_name,
                        observation_date,
                        observation_time,
                        temperature_c,
                        relative_humidity,
                        wind_speed_kmh,
                        precipitation_mm,
                        fwi,
                        ffmc,
                        dmc,
                        dc,
                        isi,
                        bui,
                        danger_class,
                        ST_AsGeoJSON(geometry)::json as location,
                        data_source
                    FROM ontario_fire_danger
                    WHERE ST_DWithin(
                        geometry::geography,
                        ST_GeomFromText(:geom, 4326)::geography,
                        50000  -- 50km radius
                    )
                    AND observation_date >= :recent_date
                    ORDER BY observation_date DESC, station_id
                    LIMIT 100
                """)

                result = await conn.execute(
                    query, {"geom": geom_text, "recent_date": recent_date}
                )
                rows = result.fetchall()

                # Transform to standardized format
                danger_data = []
                for row in rows:
                    danger_data.append({
                        "source": "Fire Danger Rating",
                        "station_id": row.station_id,
                        "station_name": row.station_name,
                        "observation_date": str(row.observation_date),
                        "observation_time": str(row.observation_time) if row.observation_time else None,
                        "temperature_celsius": float(row.temperature_c) if row.temperature_c else None,
                        "relative_humidity": float(row.relative_humidity) if row.relative_humidity else None,
                        "wind_speed_kmh": float(row.wind_speed_kmh) if row.wind_speed_kmh else None,
                        "precipitation_mm": float(row.precipitation_mm) if row.precipitation_mm else None,
                        "fire_weather_index": float(row.fwi) if row.fwi else None,
                        "fine_fuel_moisture_code": float(row.ffmc) if row.ffmc else None,
                        "duff_moisture_code": float(row.dmc) if row.dmc else None,
                        "drought_code": float(row.dc) if row.dc else None,
                        "initial_spread_index": float(row.isi) if row.isi else None,
                        "buildup_index": float(row.bui) if row.bui else None,
                        "danger_class": row.danger_class,
                        "location": row.location,
                        "data_source": row.data_source,
                    })

                if danger_data:
                    high_danger_count = sum(
                        1 for d in danger_data
                        if d["danger_class"] in ["High", "Very High", "Extreme"]
                    )
                    message = f"Found {len(danger_data)} fire danger observations ({high_danger_count} high risk)"
                else:
                    message = "No recent fire danger data available in database"

                return DataPullResult(
                    success=True,
                    data=danger_data,
                    message=message,
                    data_points_count=len(danger_data),
                )

        except Exception as e:
            logger.error(f"Error querying fire danger: {e}", exc_info=True)
            return DataPullResult(
                success=False,
                data=[],
                message=f"Database error: {str(e)}",
                data_points_count=0,
            )

    async def _pull_infrastructure(
        self, aoi: Dict, infrastructure_type: str = ""
    ) -> DataPullResult:
        """Query Indigenous infrastructure projects from database."""
        try:
            geom_text = self._aoi_to_wkt(aoi)

            async with get_db_connection() as conn:
                # Build query with optional infrastructure type filter
                type_filter = ""
                params = {"geom": geom_text}

                if infrastructure_type:
                    type_filter = "AND infrastructure_category ILIKE :infra_type"
                    params["infra_type"] = f"%{infrastructure_type}%"

                query = text(f"""
                    SELECT
                        project_id,
                        community_name,
                        first_nation,
                        project_name,
                        infrastructure_category,
                        infrastructure_type,
                        project_status,
                        project_start_date,
                        project_completion_date,
                        funding_amount,
                        funding_source,
                        project_description,
                        asset_condition,
                        within_williams_treaty,
                        ST_AsGeoJSON(geometry)::json as location,
                        data_source
                    FROM ontario_indigenous_infrastructure
                    WHERE ST_Intersects(
                        geometry,
                        ST_GeomFromText(:geom, 4326)
                    )
                    {type_filter}
                    ORDER BY community_name, infrastructure_category
                    LIMIT 1000
                """)

                result = await conn.execute(query, params)
                rows = result.fetchall()

                # Transform to standardized format
                projects = []
                for row in rows:
                    projects.append({
                        "source": "Indigenous Infrastructure",
                        "project_id": row.project_id,
                        "community": row.community_name,
                        "first_nation": row.first_nation,
                        "project_name": row.project_name,
                        "category": row.infrastructure_category,
                        "type": row.infrastructure_type,
                        "status": row.project_status,
                        "start_date": str(row.project_start_date) if row.project_start_date else None,
                        "completion_date": str(row.project_completion_date) if row.project_completion_date else None,
                        "funding_amount": float(row.funding_amount) if row.funding_amount else None,
                        "funding_source": row.funding_source,
                        "description": row.project_description,
                        "condition": row.asset_condition,
                        "williams_treaty": row.within_williams_treaty,
                        "location": row.location,
                        "data_source": row.data_source,
                    })

                # Calculate summary statistics
                total_funding = sum(
                    p["funding_amount"] for p in projects if p["funding_amount"]
                )
                message = f"Found {len(projects)} infrastructure projects (${total_funding:,.0f} total funding)"

                return DataPullResult(
                    success=True,
                    data=projects,
                    message=message,
                    data_points_count=len(projects),
                )

        except Exception as e:
            logger.error(f"Error querying infrastructure: {e}", exc_info=True)
            return DataPullResult(
                success=False,
                data=[],
                message=f"Database error: {str(e)}",
                data_points_count=0,
            )

    async def _pull_community_wellbeing(self, aoi: Dict) -> DataPullResult:
        """Query community well-being indicators from database."""
        try:
            geom_text = self._aoi_to_wkt(aoi)

            async with get_db_connection() as conn:
                query = text("""
                    SELECT
                        csd_code,
                        community_name,
                        community_type,
                        census_year,
                        population,
                        cwb_score,
                        education_score,
                        labour_force_score,
                        income_score,
                        housing_score,
                        within_williams_treaty,
                        ST_AsGeoJSON(geometry)::json as location,
                        data_source
                    FROM ontario_community_wellbeing
                    WHERE ST_Intersects(
                        geometry,
                        ST_GeomFromText(:geom, 4326)
                    )
                    ORDER BY census_year DESC, cwb_score ASC
                    LIMIT 500
                """)

                result = await conn.execute(query, {"geom": geom_text})
                rows = result.fetchall()

                # Transform to standardized format
                communities = []
                for row in rows:
                    communities.append({
                        "source": "Community Well-Being",
                        "csd_code": row.csd_code,
                        "community": row.community_name,
                        "type": row.community_type,
                        "census_year": row.census_year,
                        "population": row.population,
                        "cwb_score": float(row.cwb_score) if row.cwb_score else None,
                        "education_score": float(row.education_score) if row.education_score else None,
                        "labour_force_score": float(row.labour_force_score) if row.labour_force_score else None,
                        "income_score": float(row.income_score) if row.income_score else None,
                        "housing_score": float(row.housing_score) if row.housing_score else None,
                        "williams_treaty": row.within_williams_treaty,
                        "location": row.location,
                        "data_source": row.data_source,
                    })

                # Calculate averages for First Nations
                fn_communities = [c for c in communities if "First Nation" in c["type"]]
                if fn_communities:
                    avg_cwb = sum(c["cwb_score"] for c in fn_communities if c["cwb_score"]) / len(fn_communities)
                    message = f"Found {len(communities)} communities ({len(fn_communities)} First Nations, avg CWB: {avg_cwb:.1f})"
                else:
                    message = f"Found {len(communities)} communities"

                return DataPullResult(
                    success=True,
                    data=communities,
                    message=message,
                    data_points_count=len(communities),
                )

        except Exception as e:
            logger.error(f"Error querying community well-being: {e}", exc_info=True)
            return DataPullResult(
                success=False,
                data=[],
                message=f"Database error: {str(e)}",
                data_points_count=0,
            )

    @staticmethod
    def _aoi_to_wkt(aoi: Dict) -> str:
        """Convert AOI geometry to WKT format for PostGIS queries."""
        # Handle different AOI formats
        if "geometry" in aoi:
            geometry = aoi["geometry"]
        else:
            geometry = aoi

        geom_type = geometry.get("type")
        coords = geometry.get("coordinates")

        if geom_type == "Polygon":
            # Format: POLYGON((lon lat, lon lat, ...))
            points = ", ".join(f"{c[0]} {c[1]}" for c in coords[0])
            return f"POLYGON(({points}))"
        elif geom_type == "MultiPolygon":
            # Use first polygon
            points = ", ".join(f"{c[0]} {c[1]}" for c in coords[0][0])
            return f"POLYGON(({points}))"
        elif geom_type == "Point":
            lon, lat = coords
            # Create small buffer around point (~10km)
            return f"POINT({lon} {lat})"
        else:
            raise ValueError(f"Unsupported geometry type: {geom_type}")
