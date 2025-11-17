"""
Ingest Indigenous Community Infrastructure Management (ICIM) data.

Data source: Indigenous Services Canada
Dataset: Indigenous Community Infrastructure Management
Projects: Infrastructure projects in First Nations communities

This script processes infrastructure project CSV data and loads it into PostGIS.
Ported from: https://github.com/robertsoden/williams-treaties
"""

import os
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

TABLE_NAME = "ontario_indigenous_infrastructure"
CACHE_DIR = Path("data/ontario/infrastructure")

# Williams Treaty First Nations for filtering
WILLIAMS_TREATY_NATIONS = [
    "Alderville First Nation",
    "Curve Lake First Nation",
    "Hiawatha First Nation",
    "Mississaugas of Scugog Island First Nation",
    "Chippewas of Beausoleil First Nation",
    "Chippewas of Georgina Island First Nation",
    "Chippewas of Rama First Nation",
]


def process_infrastructure_projects(
    csv_path: Path, williams_treaty_boundary: gpd.GeoDataFrame = None
) -> gpd.GeoDataFrame:
    """
    Process infrastructure projects CSV into standardized GeoDataFrame.

    Expected CSV columns (from ICIM):
    - Community Name
    - First Nation
    - Latitude, Longitude
    - Project Name
    - Infrastructure Category
    - Project Status
    - Funding information
    - Asset Condition

    Args:
        csv_path: Path to the CSV file
        williams_treaty_boundary: Optional GeoDataFrame with Williams Treaty boundary

    Returns:
        Processed GeoDataFrame
    """
    print(f"📖 Reading {csv_path}...")

    # Read CSV - ICIM files are often UTF-16 with tab delimiters
    try:
        df = pd.read_csv(csv_path, encoding="utf-16", sep="\t", on_bad_lines="skip")
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(csv_path, encoding="utf-8", on_bad_lines="skip")
        except Exception:
            df = pd.read_csv(csv_path, encoding="latin-1", on_bad_lines="skip")

    print(f"✓ Loaded {len(df)} infrastructure project records")
    print(f"Columns: {list(df.columns)[:10]}...")  # Show first 10 columns

    # Filter for Ontario only (if Province column exists)
    if "Province" in df.columns:
        ontario_df = df[df["Province"].str.upper() == "ON"].copy()
        print(f"✓ Filtered to {len(ontario_df)} Ontario records")
    else:
        ontario_df = df.copy()

    # Remove records without valid coordinates
    lat_col = next((c for c in ontario_df.columns if "latitude" in c.lower()), None)
    lon_col = next((c for c in ontario_df.columns if "longitude" in c.lower()), None)

    if not lat_col or not lon_col:
        raise ValueError("Could not find latitude/longitude columns in CSV")

    ontario_df = ontario_df.dropna(subset=[lat_col, lon_col])

    # Convert coordinates to numeric
    ontario_df[lat_col] = pd.to_numeric(ontario_df[lat_col], errors="coerce")
    ontario_df[lon_col] = pd.to_numeric(ontario_df[lon_col], errors="coerce")
    ontario_df = ontario_df.dropna(subset=[lat_col, lon_col])

    print(f"✓ {len(ontario_df)} records with valid coordinates")

    # Standardize column names to match database schema
    # Note: ICIM CSV has typo "Infrastucture" instead of "Infrastructure"
    column_mapping = {
        "Project ID": "project_id",
        "Community Name": "community_name",
        "First Nation": "first_nation",
        "Project Name": "project_name",
        "Infrastructure Category": "infrastructure_category",
        "Infrastucture Category": "infrastructure_category",  # Handle typo
        "Infrastructure Type": "infrastructure_type",
        "Infrastucture Type": "infrastructure_type",  # Handle typo
        "Project Status": "project_status",
        "Project Start Date": "project_start_date",
        "Project Completion Date": "project_completion_date",
        "Funding Amount": "funding_amount",
        "Funding Source": "funding_source",
        "Project Description": "project_description",
        "Asset Condition": "asset_condition",
        lat_col: "lat",
        lon_col: "lon",
    }

    # Rename columns that exist
    rename_dict = {
        old: new for old, new in column_mapping.items() if old in ontario_df.columns
    }
    ontario_df = ontario_df.rename(columns=rename_dict)

    # Parse dates if they exist
    for date_col in ["project_start_date", "project_completion_date"]:
        if date_col in ontario_df.columns:
            ontario_df[date_col] = pd.to_datetime(ontario_df[date_col], errors="coerce")

    # Parse funding amount if it exists
    if "funding_amount" in ontario_df.columns:
        # Remove currency symbols and commas, convert to numeric
        ontario_df["funding_amount"] = (
            ontario_df["funding_amount"]
            .astype(str)
            .str.replace(r"[$,]", "", regex=True)
            .str.strip()
        )
        ontario_df["funding_amount"] = pd.to_numeric(
            ontario_df["funding_amount"], errors="coerce"
        )

    # Create Point geometries
    geometry = [
        Point(lon, lat) for lon, lat in zip(ontario_df["lon"], ontario_df["lat"])
    ]
    gdf = gpd.GeoDataFrame(ontario_df, geometry=geometry, crs="EPSG:4326")

    # Determine if projects are within Williams Treaty territories
    if williams_treaty_boundary is not None:
        print("🗺️  Checking Williams Treaty territorial boundaries...")
        gdf["within_williams_treaty"] = gdf.geometry.within(
            williams_treaty_boundary.unary_union
        )
        williams_count = gdf["within_williams_treaty"].sum()
        print(f"✓ {williams_count} projects within Williams Treaty territories")
    else:
        # Fallback: check if First Nation is in Williams Treaty list
        if "first_nation" in gdf.columns:
            gdf["within_williams_treaty"] = gdf["first_nation"].isin(
                WILLIAMS_TREATY_NATIONS
            )
        else:
            gdf["within_williams_treaty"] = False

    # Add data source metadata
    gdf["data_source"] = "ICIM"

    # Generate project_id if not present
    if "project_id" not in gdf.columns:
        gdf["project_id"] = [f"ICIM_{i:06d}" for i in range(1, len(gdf) + 1)]

    # Select and order columns for database
    final_columns = [
        "project_id",
        "community_name",
        "first_nation",
        "project_name",
        "infrastructure_category",
        "infrastructure_type",
        "project_status",
        "project_start_date",
        "project_completion_date",
        "funding_amount",
        "funding_source",
        "project_description",
        "asset_condition",
        "within_williams_treaty",
        "data_source",
        "geometry",
    ]

    # Keep only columns that exist
    available_columns = [col for col in final_columns if col in gdf.columns]
    gdf = gdf[available_columns]

    print(f"✓ Processed {len(gdf)} infrastructure projects for ingestion")

    # Print summary statistics
    if "infrastructure_category" in gdf.columns:
        print("\nProjects by category:")
        category_counts = gdf["infrastructure_category"].value_counts()
        for category, count in category_counts.head(10).items():
            print(f"  - {category}: {count}")

    return gdf


def ingest_infrastructure_projects(
    csv_path: Path,
    williams_treaty_boundary_path: Path = None,
    if_exists: str = "replace",
) -> None:
    """
    Ingest infrastructure projects data into PostGIS.

    Args:
        csv_path: Path to the infrastructure projects CSV file
        williams_treaty_boundary_path: Optional path to Williams Treaty boundary GeoJSON
        if_exists: How to behave if table exists ('fail', 'replace', 'append')
    """
    # Load Williams Treaty boundary if provided
    williams_boundary = None
    if williams_treaty_boundary_path and williams_treaty_boundary_path.exists():
        print(f"📖 Loading Williams Treaty boundary from {williams_treaty_boundary_path}")
        williams_boundary = gpd.read_file(williams_treaty_boundary_path)
        print(f"✓ Loaded boundary with {len(williams_boundary)} features")

    # Process the data
    gdf = process_infrastructure_projects(csv_path, williams_boundary)

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
            # Index on infrastructure category
            conn.execute(
                text(
                    f"""
                CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_category
                ON {TABLE_NAME}(infrastructure_category)
            """
                )
            )
            # Index on project status
            conn.execute(
                text(
                    f"""
                CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_status
                ON {TABLE_NAME}(project_status)
            """
                )
            )
            # Index on Williams Treaty status
            conn.execute(
                text(
                    f"""
                CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_williams
                ON {TABLE_NAME}(within_williams_treaty)
                WHERE within_williams_treaty = TRUE
            """
                )
            )
            conn.commit()
            print("✓ Indexes created successfully")
        except Exception as e:
            print(f"⚠️  Index creation warning: {e}")

    print(f"\n✅ Successfully ingested {len(gdf)} infrastructure project records")


def main():
    """Main entry point for script execution."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Ingest Indigenous infrastructure projects data"
    )
    parser.add_argument(
        "csv_path",
        type=Path,
        help="Path to infrastructure projects CSV file",
    )
    parser.add_argument(
        "--williams-boundary",
        type=Path,
        help="Path to Williams Treaty boundary GeoJSON",
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
        print("\n📝 To obtain infrastructure project data:")
        print("   Contact Indigenous Services Canada for ICIM data access")
        return

    ingest_infrastructure_projects(
        args.csv_path,
        williams_treaty_boundary_path=args.williams_boundary,
        if_exists=args.if_exists,
    )


if __name__ == "__main__":
    main()
