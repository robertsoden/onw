"""
Ingest Williams Treaty First Nations territories data.

Data sources:
- Indigenous Services Canada
- Ontario Ministry of Indigenous Affairs
- Treaties Recognition Office
- First Nations open data portals

The Williams Treaties were signed October 31, 1923 between the Crown and
seven First Nations covering ~20,000 km² in central Ontario.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import Point, Polygon

from src.ingest.utils import (
    create_geometry_index_if_not_exists,
    create_id_index_if_not_exists,
    create_text_search_index_if_not_exists,
    ingest_to_postgis,
)
from src.utils.env_loader import load_environment_variables

load_environment_variables()

# First Nations Reserve boundaries from Indigenous Services Canada
INDIGENOUS_LANDS_URL = "https://geo.statcan.gc.ca/geoserver/census-recensement/wfs"

# Williams Treaty First Nations
WILLIAMS_TREATY_FIRST_NATIONS = [
    "Alderville First Nation",
    "Curve Lake First Nation",
    "Hiawatha First Nation",
    "Mississaugas of Scugog Island First Nation",
    "Chippewas of Beausoleil First Nation",
    "Chippewas of Georgina Island First Nation",
    "Chippewas of Rama First Nation",
]

TABLE_NAME = "williams_treaty_first_nations"
CACHE_DIR = Path("data/ontario")


def create_williams_treaty_data() -> gpd.GeoDataFrame:
    """
    Create Williams Treaty First Nations territory data.

    This creates approximate territories based on treaty area and reserve locations.
    For production, source from official First Nations or government GIS data.
    """
    print("📝 Creating Williams Treaty First Nations territory data...")
    print("⚠️  Using approximate locations - source official data for production")

    # Williams Treaty First Nations with approximate central coordinates
    # In production, download actual reserve boundaries and treaty territories
    first_nations_data = [
        {
            "first_nation_name": "Alderville First Nation",
            "treaty": "Williams Treaties (1923)",
            "treaty_date": "1923-10-31",
            "traditional_territory": "Rice Lake, Northumberland County",
            "population_approx": 1100,
            "reserve_area_ha": 1200,
            "website": "https://www.aldervillefirstnation.ca",
            "lat": 44.1194,
            "lon": -78.0753,
        },
        {
            "first_nation_name": "Curve Lake First Nation",
            "treaty": "Williams Treaties (1923)",
            "treaty_date": "1923-10-31",
            "traditional_territory": "Kawartha Lakes region",
            "population_approx": 2200,
            "reserve_area_ha": 800,
            "website": "https://www.curvelakefirstnation.ca",
            "lat": 44.5319,
            "lon": -78.2289,
        },
        {
            "first_nation_name": "Hiawatha First Nation",
            "treaty": "Williams Treaties (1923)",
            "treaty_date": "1923-10-31",
            "traditional_territory": "Rice Lake, near Peterborough",
            "population_approx": 600,
            "reserve_area_ha": 400,
            "website": "https://www.hiawathafirstnation.com",
            "lat": 44.2486,
            "lon": -78.1581,
        },
        {
            "first_nation_name": "Mississaugas of Scugog Island First Nation",
            "treaty": "Williams Treaties (1923)",
            "treaty_date": "1923-10-31",
            "traditional_territory": "Scugog Island, Lake Scugog",
            "population_approx": 275,
            "reserve_area_ha": 324,
            "website": "https://www.scugogfirstnation.com",
            "lat": 44.1178,
            "lon": -78.9017,
        },
        {
            "first_nation_name": "Chippewas of Beausoleil First Nation",
            "treaty": "Williams Treaties (1923)",
            "treaty_date": "1923-10-31",
            "traditional_territory": "Christian Island, Georgian Bay",
            "population_approx": 1900,
            "reserve_area_ha": 1360,
            "website": "https://www.chimnissing.ca",
            "lat": 44.8194,
            "lon": -80.0092,
        },
        {
            "first_nation_name": "Chippewas of Georgina Island First Nation",
            "treaty": "Williams Treaties (1923)",
            "treaty_date": "1923-10-31",
            "traditional_territory": "Georgina Island, Lake Simcoe",
            "population_approx": 750,
            "reserve_area_ha": 505,
            "website": "https://www.georginaisland.com",
            "lat": 44.3392,
            "lon": -79.3483,
        },
        {
            "first_nation_name": "Chippewas of Rama First Nation",
            "treaty": "Williams Treaties (1923)",
            "treaty_date": "1923-10-31",
            "traditional_territory": "Lake Couchiching, Rama",
            "population_approx": 950,
            "reserve_area_ha": 932,
            "website": "https://www.ramafirstnation.ca",
            "lat": 44.6156,
            "lon": -79.3014,
        },
    ]

    df = pd.DataFrame(first_nations_data)

    # Create point geometries (representing reserve centers)
    # In production, use actual reserve polygon boundaries
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df.lon, df.lat),
        crs="EPSG:4326"
    )

    # Remove lat/lon columns
    gdf = gdf.drop(columns=['lat', 'lon'])

    # Add territory_id
    gdf['territory_id'] = range(1, len(gdf) + 1)

    # Add metadata
    gdf['data_source'] = 'Approximate locations - requires official verification'
    gdf['last_updated'] = pd.Timestamp.now().strftime('%Y-%m-%d')

    # Add cultural notes
    gdf['cultural_notes'] = 'Traditional territory extends beyond reserve boundaries. Consult with First Nation for accurate territorial boundaries and data sharing protocols.'

    print(f"✓ Created data for {len(gdf)} Williams Treaty First Nations")

    return gdf


def download_first_nations_boundaries() -> gpd.GeoDataFrame:
    """
    Download First Nations reserve boundaries from Statistics Canada.

    This is a fallback - ideally source from First Nations or Indigenous Services Canada.
    """
    print("📥 Attempting to download First Nations boundaries...")

    try:
        # Statistics Canada has Indigenous lands boundaries
        # This is simplified - actual implementation would use WFS query
        print("⚠️  StatsCan WFS integration not implemented")
        print("    Using sample data instead")
        return None

    except Exception as e:
        print(f"⚠️  Download failed: {e}")
        return None


def create_indices(table_name: str = TABLE_NAME):
    """Create spatial and text search indices."""
    print("📑 Creating indices...")

    create_geometry_index_if_not_exists(
        table_name, f"{table_name}_geom_idx", "geometry"
    )
    create_text_search_index_if_not_exists(
        table_name, f"{table_name}_name_idx", "first_nation_name"
    )
    create_id_index_if_not_exists(
        table_name, f"{table_name}_territory_id_idx", "territory_id"
    )


def main():
    """Main ingestion workflow."""
    print("=" * 60)
    print("Williams Treaty First Nations Territories Ingestion")
    print("=" * 60)
    print()
    print("⚠️  IMPORTANT - Cultural Sensitivity")
    print("   This data represents traditional territories of")
    print("   Williams Treaty First Nations signatories.")
    print("   Data should be used respectfully and with proper")
    print("   acknowledgment of Indigenous sovereignty.")
    print("=" * 60)
    print()

    # Try to download official data
    gdf = download_first_nations_boundaries()

    # If download fails, use created data
    if gdf is None:
        gdf = create_williams_treaty_data()

    # Ingest to PostGIS
    print(f"💾 Ingesting to PostGIS table '{TABLE_NAME}'...")
    ingest_to_postgis(TABLE_NAME, gdf, chunk_size=10, if_exists="replace")

    # Create indices
    create_indices()

    print()
    print("=" * 60)
    print("✅ Williams Treaty First Nations ingestion complete!")
    print(f"   Total First Nations: {len(gdf)}")
    print(f"   Table: {TABLE_NAME}")
    print("=" * 60)
    print()
    print("📝 Production Setup Requirements:")
    print("   1. Source official reserve boundary data from:")
    print("      - Indigenous Services Canada")
    print("      - Individual First Nations")
    print("      - Ontario Ministry of Indigenous Affairs")
    print("   2. Obtain proper permissions for data use")
    print("   3. Implement data sharing agreements")
    print("   4. Regular consultation with First Nations")
    print("   5. Update data based on First Nation input")
    print()
    print("🤝 Engagement:")
    print("   Contact each First Nation for:")
    print("   - Accurate territorial boundary data")
    print("   - Permission to use and share data")
    print("   - Cultural protocols and guidelines")
    print("   - Ongoing collaboration opportunities")


if __name__ == "__main__":
    main()
