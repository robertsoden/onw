"""
Ingest First Nations Water Advisories data.

Data source: Indigenous Services Canada
URL: https://www.sac-isc.gc.ca/eng/1506514143353/1533317130660
Dataset: Drinking Water Advisories for First Nations

This script processes water advisory CSV data and loads it into PostGIS.
Ported from: https://github.com/robertsoden/williams-treaties
"""

import os
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from sqlalchemy import create_engine, text

from src.ingest.utils import (
    create_geometry_index_if_not_exists,
    create_id_index_if_not_exists,
    create_text_search_index_if_not_exists,
    ingest_to_postgis,
)
from src.utils.env_loader import load_environment_variables

load_environment_variables()

TABLE_NAME = "ontario_water_advisories"
CACHE_DIR = Path("data/ontario/water_advisories")


def process_water_advisories(csv_path: Path) -> gpd.GeoDataFrame:
    """
    Process water advisories CSV into standardized GeoDataFrame.

    Expected CSV columns (from Indigenous Services Canada):
    - Community/First Nation name
    - Region/Province
    - Latitude, Longitude
    - Advisory Type
    - Advisory Date
    - Lift Date (optional)
    - Water System Name (optional)
    - Population (optional)

    Args:
        csv_path: Path to the CSV file

    Returns:
        Processed GeoDataFrame
    """
    print(f"📖 Reading {csv_path}...")

    # Read CSV - try different encodings
    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, encoding="latin-1")

    print(f"✓ Loaded {len(df)} water advisory records")
    print(f"Columns: {list(df.columns)}")

    # Filter for Ontario only
    ontario_df = df[df["Province"].str.upper() == "ONTARIO"].copy()
    print(f"✓ Filtered to {len(ontario_df)} Ontario records")

    # Remove records without valid coordinates
    ontario_df = ontario_df.dropna(subset=["Latitude", "Longitude"])

    # Convert coordinates to numeric
    ontario_df["Latitude"] = pd.to_numeric(ontario_df["Latitude"], errors="coerce")
    ontario_df["Longitude"] = pd.to_numeric(ontario_df["Longitude"], errors="coerce")
    ontario_df = ontario_df.dropna(subset=["Latitude", "Longitude"])

    print(f"✓ {len(ontario_df)} records with valid coordinates")

    # Standardize column names to match database schema
    column_mapping = {
        "Advisory ID": "advisory_id",
        "Community": "community_name",
        "First Nation": "first_nation",
        "Region": "region",
        "Advisory Type": "advisory_type",
        "Advisory Date": "advisory_date",
        "Lift Date": "lift_date",
        "Reason": "reason",
        "Water System": "water_system_name",
        "Population": "population_affected",
        "Latitude": "lat",
        "Longitude": "lon",
    }

    # Rename columns that exist
    rename_dict = {old: new for old, new in column_mapping.items() if old in ontario_df.columns}
    ontario_df = ontario_df.rename(columns=rename_dict)

    # Parse dates
    if "advisory_date" in ontario_df.columns:
        ontario_df["advisory_date"] = pd.to_datetime(
            ontario_df["advisory_date"], errors="coerce"
        )

    if "lift_date" in ontario_df.columns:
        ontario_df["lift_date"] = pd.to_datetime(
            ontario_df["lift_date"], errors="coerce"
        )
        # Mark active advisories (no lift date)
        ontario_df["is_active"] = ontario_df["lift_date"].isna()
    else:
        ontario_df["is_active"] = True

    # Calculate duration
    ontario_df["duration_days"] = ontario_df.apply(
        lambda row: (
            (row["lift_date"] - row["advisory_date"]).days
            if pd.notna(row["lift_date"])
            else (datetime.now() - row["advisory_date"]).days
        )
        if pd.notna(row["advisory_date"])
        else None,
        axis=1,
    )

    # Create Point geometries
    geometry = [
        Point(lon, lat) for lon, lat in zip(ontario_df["lon"], ontario_df["lat"])
    ]
    gdf = gpd.GeoDataFrame(ontario_df, geometry=geometry, crs="EPSG:4326")

    # Add data source metadata
    gdf["data_source"] = "Indigenous Services Canada"
    gdf["source_url"] = "https://www.sac-isc.gc.ca/eng/1506514143353/1533317130660"

    # Select and order columns for database
    final_columns = [
        "advisory_id",
        "community_name",
        "first_nation",
        "region",
        "advisory_type",
        "advisory_date",
        "lift_date",
        "duration_days",
        "is_active",
        "reason",
        "water_system_name",
        "population_affected",
        "data_source",
        "source_url",
        "geometry",
    ]

    # Keep only columns that exist
    available_columns = [col for col in final_columns if col in gdf.columns]
    gdf = gdf[available_columns]

    print(f"✓ Processed {len(gdf)} records for ingestion")
    print(
        f"   - Active advisories: {gdf['is_active'].sum() if 'is_active' in gdf.columns else 'N/A'}"
    )

    return gdf


def ingest_water_advisories(csv_path: Path, if_exists: str = "replace") -> None:
    """
    Ingest water advisories data into PostGIS.

    Args:
        csv_path: Path to the water advisories CSV file
        if_exists: How to behave if table exists ('fail', 'replace', 'append')
    """
    # Process the data
    gdf = process_water_advisories(csv_path)

    # Ingest to PostGIS
    print(f"\n📥 Ingesting to PostGIS table: {TABLE_NAME}")
    ingest_to_postgis(gdf, TABLE_NAME, if_exists=if_exists)

    # Create indexes
    print("\n🔧 Creating spatial and text indexes...")
    engine = create_engine(os.getenv("DATABASE_URL"))

    create_geometry_index_if_not_exists(engine, TABLE_NAME, "geometry")
    create_text_search_index_if_not_exists(engine, TABLE_NAME, "community_name")

    # Create additional useful indexes
    with engine.connect() as conn:
        try:
            # Index on active status
            conn.execute(
                text(
                    f"""
                CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_active
                ON {TABLE_NAME}(is_active) WHERE is_active = TRUE
            """
                )
            )
            # Index on advisory type
            conn.execute(
                text(
                    f"""
                CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_type
                ON {TABLE_NAME}(advisory_type)
            """
                )
            )
            # Index on advisory date
            conn.execute(
                text(
                    f"""
                CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_date
                ON {TABLE_NAME}(advisory_date)
            """
                )
            )
            conn.commit()
            print("✓ Indexes created successfully")
        except Exception as e:
            print(f"⚠️  Index creation warning: {e}")

    print(f"\n✅ Successfully ingested {len(gdf)} water advisory records")


def main():
    """Main entry point for script execution."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Ingest First Nations water advisories data"
    )
    parser.add_argument(
        "csv_path",
        type=Path,
        help="Path to water advisories CSV file",
    )
    parser.add_argument(
        "--if-exists",
        choices=["fail", "replace", "append"],
        default="replace",
        help="How to behave if table exists (default: replace)",
    )

    args = parser.parse_args()

    if not args.csv_path.exists():
        print(f"❌ File not found: {args.csv_path}")
        print("\n📝 To obtain water advisory data:")
        print("   1. Visit: https://www.sac-isc.gc.ca/eng/1506514143353/1533317130660")
        print("   2. Download the 'Drinking Water Advisories' CSV")
        print(f"   3. Run: python -m src.ingest.ingest_water_advisories <path-to-csv>")
        return

    ingest_water_advisories(args.csv_path, if_exists=args.if_exists)


if __name__ == "__main__":
    main()
