"""
Ingest Ontario Conservation Areas data.

Data sources:
- Conservation Ontario
- Ontario GeoHub
- Individual Conservation Authority open data

This script downloads and processes Conservation Areas spatial data into PostGIS.
"""

import os
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from sqlalchemy import create_engine, text

from src.ingest.utils import (
    create_geometry_index_if_not_exists,
    create_id_index_if_not_exists,
    create_text_search_index_if_not_exists,
    ingest_to_postgis,
)
from src.utils.env_loader import load_environment_variables

load_environment_variables()

# Conservation Authority boundaries from Ontario GeoHub
CONSERVATION_AUTHORITIES_URL = "https://ws.lioservices.lrc.gov.on.ca/arcgis1071a/rest/services/MOE/Conservation_Authorities/MapServer/0/query?where=1%3D1&outFields=*&f=geojson"

# Conservation Areas (lands managed by CAs)
# Note: This may need to be compiled from multiple sources
CONSERVATION_AREAS_SOURCES = {
    "kawartha": "https://data.kawarthaconservation.com/datasets/conservation-areas/",
    "trca": "https://data.trca.ca/",
    # Add more Conservation Authority data sources
}

TABLE_NAME = "ontario_conservation_areas"
CACHE_DIR = Path("data/ontario")


def download_conservation_authorities() -> Path:
    """
    Download Conservation Authority boundaries.

    Returns:
        Path to the downloaded GeoJSON file
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    dest_file = CACHE_DIR / "conservation_authorities.geojson"

    if dest_file.exists():
        print(f"✓ Using cached file → {dest_file}")
        return dest_file

    print(f"⇣ Downloading Conservation Authorities boundaries...")

    try:
        response = requests.get(CONSERVATION_AUTHORITIES_URL, timeout=300)
        response.raise_for_status()

        with open(dest_file, "wb") as f:
            f.write(response.content)

        print(f"✓ Downloaded {dest_file.stat().st_size / 1e6:.1f} MB")
        return dest_file

    except Exception as e:
        print(f"⚠️  Download failed: {e}")
        print("📝 Please manually download Conservation Authority data from:")
        print("   https://geohub.lio.gov.on.ca/")
        print(f"   Save as: {dest_file}")
        raise


def create_sample_conservation_areas() -> gpd.GeoDataFrame:
    """
    Create sample Conservation Areas data for major Conservation Authorities.

    This is a placeholder until proper data sources are configured.
    In production, this should download from Conservation Authority open data portals.
    """
    print("⚠️  Using sample data - configure proper data sources for production")

    # Sample major conservation areas
    # In production, download from actual Conservation Authority databases
    sample_data = [
        {
            "name": "Kawartha Highlands Signature Site",
            "official_name": "Kawartha Highlands Signature Site Park",
            "authority": "Kawartha Conservation",
            "designation": "Conservation Area",
            "hectares": 37595,
            "region": "Kawartha",
            "lat": 44.85,
            "lon": -78.2,
        },
        {
            "name": "Warsaw Caves Conservation Area",
            "official_name": "Warsaw Caves Conservation Area",
            "authority": "Otonabee Conservation",
            "designation": "Conservation Area",
            "hectares": 162,
            "region": "Peterborough",
            "lat": 44.3,
            "lon": -78.1,
        },
        {
            "name": "Mark S. Burnham Provincial Park",
            "official_name": "Mark S. Burnham Provincial Park",
            "authority": "Central Lake Ontario Conservation Authority",
            "designation": "Provincial Park / Conservation Area",
            "hectares": 120,
            "region": "Durham",
            "lat": 44.1,
            "lon": -78.4,
        },
    ]

    df = pd.DataFrame(sample_data)

    # Create point geometries (in production, use actual polygons)
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df.lon, df.lat),
        crs="EPSG:4326"
    )

    # Remove lat/lon columns
    gdf = gdf.drop(columns=['lat', 'lon'])

    # Add area_id
    gdf['area_id'] = range(1, len(gdf) + 1)

    # Rename managing_authority column to match schema
    gdf['managing_authority'] = gdf['authority']
    gdf = gdf.drop(columns=['authority'])

    print(f"✓ Created {len(gdf)} sample conservation areas")
    print("📝 NOTE: Configure Conservation Authority data sources for production data")

    return gdf


def process_conservation_areas(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Process Conservation Areas into standardized format.

    Args:
        gdf: Raw GeoDataFrame

    Returns:
        Processed GeoDataFrame
    """
    print(f"📖 Processing conservation areas...")

    # Ensure required columns
    required_columns = [
        'area_id', 'name', 'official_name', 'designation',
        'managing_authority', 'hectares', 'geometry'
    ]

    # Set defaults for missing columns
    if 'designation' not in gdf.columns:
        gdf['designation'] = 'Conservation Area'

    if 'official_name' not in gdf.columns and 'name' in gdf.columns:
        gdf['official_name'] = gdf['name']

    # Ensure CRS
    if gdf.crs != 'EPSG:4326':
        gdf = gdf.to_crs('EPSG:4326')

    # Clean data
    gdf = gdf.dropna(subset=['geometry'])
    gdf = gdf[gdf.geometry.is_valid]

    print(f"✓ Processed {len(gdf)} valid conservation areas")

    return gdf


def create_indices(table_name: str = TABLE_NAME):
    """Create spatial and text search indices."""
    print("📑 Creating indices...")

    create_geometry_index_if_not_exists(
        table_name, f"{table_name}_geom_idx", "geometry"
    )
    create_text_search_index_if_not_exists(
        table_name, f"{table_name}_name_idx", "name"
    )
    create_text_search_index_if_not_exists(
        table_name, f"{table_name}_official_name_idx", "official_name"
    )
    create_id_index_if_not_exists(
        table_name, f"{table_name}_area_id_idx", "area_id"
    )


def main():
    """Main ingestion workflow."""
    print("=" * 60)
    print("Ontario Conservation Areas Ingestion")
    print("=" * 60)

    # For now, use sample data
    # In production, download from Conservation Authority sources
    gdf = create_sample_conservation_areas()

    # Process data
    gdf = process_conservation_areas(gdf)

    # Ingest to PostGIS
    print(f"💾 Ingesting to PostGIS table '{TABLE_NAME}'...")
    ingest_to_postgis(TABLE_NAME, gdf, chunk_size=100, if_exists="replace")

    # Create indices
    create_indices()

    print("=" * 60)
    print("✅ Conservation Areas ingestion complete!")
    print(f"   Total areas: {len(gdf)}")
    print(f"   Table: {TABLE_NAME}")
    print("=" * 60)
    print()
    print("📝 Production Setup Notes:")
    print("   1. Configure Conservation Authority data sources")
    print("   2. Set up authentication if needed")
    print("   3. Download actual polygon data (not points)")
    print("   4. Add additional attributes (facilities, hours, etc.)")


if __name__ == "__main__":
    main()
