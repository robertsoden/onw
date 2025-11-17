"""
Ingest Community Well-Being (CWB) data for First Nations and other communities.

Data sources:
- Indigenous Services Canada - Community Well-Being Index
- Statistics Canada - Census Subdivision Boundaries

Dataset: CWB scores including education, labour force, income, and housing components

This script processes CWB CSV data and joins it with census boundaries.
Ported from: https://github.com/robertsoden/williams-treaties
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

TABLE_NAME = "ontario_community_wellbeing"
CACHE_DIR = Path("data/ontario/community_wellbeing")

# Statistics Canada Census Subdivision Boundaries
STATCAN_CSD_URL = "https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/files-fichiers/lcsd000b21a_e.zip"

# Williams Treaty First Nations
WILLIAMS_TREATY_NATIONS = [
    "Alderville First Nation",
    "Curve Lake First Nation",
    "Hiawatha First Nation",
    "Mississaugas of Scugog Island First Nation",
    "Chippewas of Beausoleil First Nation",
    "Chippewas of Georgina Island First Nation",
    "Chippewas of Rama First Nation",
]


def download_census_boundaries(dest_dir: Path = CACHE_DIR) -> Path:
    """
    Download Statistics Canada Census Subdivision boundaries.

    Returns:
        Path to the extracted shapefile directory
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / "csd_boundaries.zip"
    extract_dir = dest_dir / "csd_boundaries"

    if extract_dir.exists():
        print(f"✓ Using cached boundaries → {extract_dir}")
        return extract_dir

    print(f"⇣ Downloading Census Subdivision boundaries from Statistics Canada...")

    try:
        response = requests.get(STATCAN_CSD_URL, timeout=300)
        response.raise_for_status()

        with open(zip_path, "wb") as f:
            f.write(response.content)

        print(f"✓ Downloaded {zip_path.stat().st_size / 1e6:.1f} MB")

        # Extract zip file
        print("📦 Extracting...")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        print(f"✓ Extracted to {extract_dir}")
        return extract_dir

    except Exception as e:
        print(f"⚠️  Download failed: {e}")
        print("📝 Please manually download Census boundaries from:")
        print(f"   {STATCAN_CSD_URL}")
        print(f"   Extract to: {extract_dir}")
        raise


def process_community_wellbeing(
    cwb_csv_path: Path,
    csd_boundaries_path: Path,
    williams_treaty_boundary: gpd.GeoDataFrame = None,
) -> gpd.GeoDataFrame:
    """
    Process CWB data and join with census boundaries.

    Args:
        cwb_csv_path: Path to the CWB CSV file
        csd_boundaries_path: Path to Census Subdivision shapefile directory
        williams_treaty_boundary: Optional Williams Treaty boundary GeoDataFrame

    Returns:
        Processed GeoDataFrame with CWB scores and geometries
    """
    # Load CWB data
    print(f"📖 Reading CWB data from {cwb_csv_path}...")
    try:
        cwb_df = pd.read_csv(cwb_csv_path, encoding="latin-1")  # Supports French chars
    except UnicodeDecodeError:
        cwb_df = pd.read_csv(cwb_csv_path, encoding="utf-8")

    print(f"✓ Loaded {len(cwb_df)} CWB records")
    print(f"Columns: {list(cwb_df.columns)}")

    # Load Census Subdivision boundaries
    print(f"\n📖 Reading Census boundaries from {csd_boundaries_path}...")
    # Find the shapefile
    shp_files = list(csd_boundaries_path.glob("*.shp"))
    if not shp_files:
        raise FileNotFoundError(f"No .shp file found in {csd_boundaries_path}")

    csd_gdf = gpd.read_file(shp_files[0])
    print(f"✓ Loaded {len(csd_gdf)} census subdivisions")

    # Filter for Ontario only (CSD codes starting with 35)
    csd_gdf = csd_gdf[csd_gdf["CSDUID"].str.startswith("35")].copy()
    print(f"✓ Filtered to {len(csd_gdf)} Ontario CSDs")

    # Standardize column names in CWB data
    column_mapping = {
        "CSD Code": "csd_code",
        "CSDUID": "csd_code",
        "Community Name": "community_name",
        "CSDNAME": "community_name",
        "Community Type": "community_type",
        "Census Year": "census_year",
        "Year": "census_year",
        "Population": "population",
        "POP": "population",
        "CWB Score": "cwb_score",
        "CWB": "cwb_score",
        "Education Score": "education_score",
        "EDUC": "education_score",
        "Labour Force Score": "labour_force_score",
        "LF": "labour_force_score",
        "Income Score": "income_score",
        "INC": "income_score",
        "Housing Score": "housing_score",
        "HOUSE": "housing_score",
    }

    # Rename CWB columns
    rename_dict = {old: new for old, new in column_mapping.items() if old in cwb_df.columns}
    cwb_df = cwb_df.rename(columns=rename_dict)

    # Ensure csd_code is string with no decimal
    if "csd_code" in cwb_df.columns:
        cwb_df["csd_code"] = cwb_df["csd_code"].astype(str).str.replace(".0", "", regex=False)

    # Join CWB data with geometries
    print("\n🔗 Joining CWB data with census boundaries...")
    merged_gdf = csd_gdf.merge(
        cwb_df,
        left_on="CSDUID",
        right_on="csd_code",
        how="inner"
    )

    print(f"✓ Joined {len(merged_gdf)} communities with both CWB data and geometries")

    # Use CSDNAME if community_name not in CWB data
    if "community_name" not in merged_gdf.columns and "CSDNAME" in merged_gdf.columns:
        merged_gdf["community_name"] = merged_gdf["CSDNAME"]

    # Determine community type if not present
    if "community_type" not in merged_gdf.columns:
        # Simple heuristic: if name contains "First Nation" or similar
        merged_gdf["community_type"] = merged_gdf["community_name"].apply(
            lambda x: "First Nation" if any(
                term in str(x).lower() for term in ["first nation", "reserve", "indian"]
            ) else "Non-Indigenous"
        )

    # Check if communities are within Williams Treaty territories
    if williams_treaty_boundary is not None:
        print("🗺️  Checking Williams Treaty territorial boundaries...")
        merged_gdf["within_williams_treaty"] = merged_gdf.geometry.intersects(
            williams_treaty_boundary.unary_union
        )
        williams_count = merged_gdf["within_williams_treaty"].sum()
        print(f"✓ {williams_count} communities within Williams Treaty territories")
    else:
        # Fallback: check if name matches Williams Treaty nations
        merged_gdf["within_williams_treaty"] = merged_gdf["community_name"].isin(
            WILLIAMS_TREATY_NATIONS
        )

    # Add metadata
    merged_gdf["data_source"] = "ISC/StatCan"
    merged_gdf["province"] = "Ontario"

    # Ensure CRS is WGS84
    if merged_gdf.crs != "EPSG:4326":
        merged_gdf = merged_gdf.to_crs("EPSG:4326")

    # Select and order final columns
    final_columns = [
        "csd_code",
        "community_name",
        "community_type",
        "census_year",
        "population",
        "cwb_score",
        "education_score",
        "labour_force_score",
        "income_score",
        "housing_score",
        "province",
        "within_williams_treaty",
        "data_source",
        "geometry",
    ]

    # Keep only columns that exist
    available_columns = [col for col in final_columns if col in merged_gdf.columns]
    merged_gdf = merged_gdf[available_columns]

    print(f"✓ Processed {len(merged_gdf)} communities for ingestion")

    # Print summary statistics
    if "cwb_score" in merged_gdf.columns:
        print(f"\nCWB Score Statistics:")
        print(f"  - Mean: {merged_gdf['cwb_score'].mean():.1f}")
        print(f"  - Min:  {merged_gdf['cwb_score'].min():.1f}")
        print(f"  - Max:  {merged_gdf['cwb_score'].max():.1f}")

    # Statistics for First Nations
    fn_df = merged_gdf[merged_gdf["community_type"].str.contains("First Nation", na=False)]
    if len(fn_df) > 0 and "cwb_score" in fn_df.columns:
        print(f"\nFirst Nations CWB Score Statistics ({len(fn_df)} communities):")
        print(f"  - Mean: {fn_df['cwb_score'].mean():.1f}")
        print(f"  - Min:  {fn_df['cwb_score'].min():.1f}")
        print(f"  - Max:  {fn_df['cwb_score'].max():.1f}")

    return merged_gdf


def ingest_community_wellbeing(
    cwb_csv_path: Path,
    csd_boundaries_path: Path = None,
    williams_treaty_boundary_path: Path = None,
    if_exists: str = "replace",
) -> None:
    """
    Ingest community well-being data into PostGIS.

    Args:
        cwb_csv_path: Path to the CWB CSV file
        csd_boundaries_path: Path to Census Subdivision boundaries (will download if None)
        williams_treaty_boundary_path: Optional path to Williams Treaty boundary GeoJSON
        if_exists: How to behave if table exists ('fail', 'replace', 'append')
    """
    # Download or use cached census boundaries
    if csd_boundaries_path is None:
        csd_boundaries_path = download_census_boundaries()

    # Load Williams Treaty boundary if provided
    williams_boundary = None
    if williams_treaty_boundary_path and williams_treaty_boundary_path.exists():
        print(f"📖 Loading Williams Treaty boundary from {williams_treaty_boundary_path}")
        williams_boundary = gpd.read_file(williams_treaty_boundary_path)
        print(f"✓ Loaded boundary with {len(williams_boundary)} features")

    # Process the data
    gdf = process_community_wellbeing(cwb_csv_path, csd_boundaries_path, williams_boundary)

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
            # Index on community type
            conn.execute(
                text(
                    f"""
                CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_type
                ON {TABLE_NAME}(community_type)
            """
                )
            )
            # Index on census year
            conn.execute(
                text(
                    f"""
                CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_year
                ON {TABLE_NAME}(census_year)
            """
                )
            )
            # Index on CWB score
            conn.execute(
                text(
                    f"""
                CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_score
                ON {TABLE_NAME}(cwb_score)
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

    print(f"\n✅ Successfully ingested {len(gdf)} community well-being records")


def main():
    """Main entry point for script execution."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Ingest Community Well-Being (CWB) data"
    )
    parser.add_argument(
        "cwb_csv",
        type=Path,
        help="Path to CWB CSV file",
    )
    parser.add_argument(
        "--csd-boundaries",
        type=Path,
        help="Path to Census Subdivision boundaries directory (will download if not provided)",
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

    if not args.cwb_csv.exists():
        print(f"❌ File not found: {args.cwb_csv}")
        print("\n📝 To obtain CWB data:")
        print("   Visit: https://www.sac-isc.gc.ca/eng/1345816651029/1557323327644")
        print("   Download the Community Well-Being Index CSV")
        return

    ingest_community_wellbeing(
        args.cwb_csv,
        csd_boundaries_path=args.csd_boundaries,
        williams_treaty_boundary_path=args.williams_boundary,
        if_exists=args.if_exists,
    )


if __name__ == "__main__":
    main()
