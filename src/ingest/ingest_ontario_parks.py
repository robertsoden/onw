"""
Ingest Ontario Provincial Parks data from Ontario GeoHub.

Data source: Ontario GeoHub / Land Information Ontario
URL: https://geohub.lio.gov.on.ca/
Dataset: Ontario Parks (Provincial Parks and Conservation Reserves)

This script downloads and processes Ontario Parks spatial data into PostGIS.
"""

import os
import zipfile
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

# Ontario Parks data sources
# Note: The actual URL may need to be updated from Ontario GeoHub
ONTARIO_PARKS_URL = "https://ws.lioservices.lrc.gov.on.ca/arcgis1071a/rest/services/LIO_Cartographic/LIO_Topographic/MapServer/9/query?where=1%3D1&outFields=*&f=geojson"

# Alternate source: Ontario Parks open data portal
ONTARIO_PARKS_ALT_URL = "https://data.ontario.ca/api/3/action/datastore_search_sql"

TABLE_NAME = "ontario_parks"
CACHE_DIR = Path("data/ontario")


def download_ontario_parks(dest_dir: Path = CACHE_DIR) -> Path:
    """
    Download Ontario Parks GeoJSON data.

    Returns:
        Path to the downloaded GeoJSON file
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / "ontario_parks.geojson"

    if dest_file.exists():
        print(f"✓ Using cached file → {dest_file}")
        return dest_file

    print(f"⇣ Downloading Ontario Parks data from Ontario GeoHub...")

    try:
        # Try primary source (Ontario GeoHub REST API)
        response = requests.get(ONTARIO_PARKS_URL, timeout=300)
        response.raise_for_status()

        with open(dest_file, "wb") as f:
            f.write(response.content)

        print(f"✓ Downloaded {dest_file.stat().st_size / 1e6:.1f} MB")
        return dest_file

    except Exception as e:
        print(f"⚠️  Primary source failed: {e}")
        print("📝 Please manually download Ontario Parks data from:")
        print("   https://geohub.lio.gov.on.ca/")
        print(f"   Save as: {dest_file}")
        raise


def process_ontario_parks(geojson_path: Path) -> gpd.GeoDataFrame:
    """
    Process Ontario Parks GeoJSON into standardized format.

    Args:
        geojson_path: Path to the GeoJSON file

    Returns:
        Processed GeoDataFrame
    """
    print(f"📖 Reading {geojson_path}...")
    gdf = gpd.read_file(geojson_path)

    print(f"✓ Loaded {len(gdf)} parks")
    print(f"Columns: {list(gdf.columns)}")

    # Standardize column names (adjust based on actual column names in the data)
    # Common column mappings from Ontario data
    column_mapping = {
        'PARK_NAME': 'name',
        'OFFICIAL_NAME': 'official_name',
        'ONT_PARK_ID': 'park_id',
        'REGULATION': 'designation',
        'AREA_HA': 'hectares',
        'MANAGEMENT_UNIT': 'managing_authority',
        'PARK_CLASS': 'park_class',
        'ZONE_CLASS': 'zone_class',
    }

    # Rename columns if they exist
    rename_dict = {old: new for old, new in column_mapping.items() if old in gdf.columns}
    gdf = gdf.rename(columns=rename_dict)

    # Ensure required columns exist
    if 'name' not in gdf.columns:
        # Try to find a suitable name column
        name_candidates = [c for c in gdf.columns if 'name' in c.lower()]
        if name_candidates:
            gdf = gdf.rename(columns={name_candidates[0]: 'name'})
        else:
            raise ValueError("No name column found in data")

    # Set official_name to name if not present
    if 'official_name' not in gdf.columns:
        gdf['official_name'] = gdf['name']

    # Add default values for missing columns
    if 'designation' not in gdf.columns:
        gdf['designation'] = 'Provincial Park'

    if 'managing_authority' not in gdf.columns:
        gdf['managing_authority'] = 'Ontario Parks'

    if 'hectares' not in gdf.columns and 'geometry' in gdf.columns:
        # Calculate area from geometry (convert to hectares)
        gdf = gdf.to_crs('EPSG:3347')  # Statistics Canada Lambert
        gdf['hectares'] = gdf.geometry.area / 10000  # m² to hectares
        gdf = gdf.to_crs('EPSG:4326')  # Back to WGS84

    # Add park_id if missing
    if 'park_id' not in gdf.columns:
        gdf['park_id'] = range(1, len(gdf) + 1)

    # Ensure CRS is WGS84
    if gdf.crs != 'EPSG:4326':
        gdf = gdf.to_crs('EPSG:4326')

    # Select final columns
    final_columns = [
        'park_id', 'name', 'official_name', 'designation',
        'managing_authority', 'hectares', 'geometry'
    ]

    # Add optional columns if they exist
    optional_columns = ['park_class', 'zone_class']
    for col in optional_columns:
        if col in gdf.columns:
            final_columns.insert(-1, col)  # Before geometry

    gdf = gdf[final_columns]

    # Clean data
    gdf = gdf.dropna(subset=['geometry'])
    gdf = gdf[gdf.geometry.is_valid]

    print(f"✓ Processed {len(gdf)} valid parks")

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
        table_name, f"{table_name}_park_id_idx", "park_id"
    )


def main():
    """Main ingestion workflow."""
    print("=" * 60)
    print("Ontario Provincial Parks Ingestion")
    print("=" * 60)

    # Download data
    geojson_path = download_ontario_parks()

    # Process data
    gdf = process_ontario_parks(geojson_path)

    # Ingest to PostGIS
    print(f"💾 Ingesting to PostGIS table '{TABLE_NAME}'...")
    ingest_to_postgis(TABLE_NAME, gdf, chunk_size=100, if_exists="replace")

    # Create indices
    create_indices()

    print("=" * 60)
    print("✅ Ontario Parks ingestion complete!")
    print(f"   Total parks: {len(gdf)}")
    print(f"   Table: {TABLE_NAME}")
    print("=" * 60)


if __name__ == "__main__":
    main()
