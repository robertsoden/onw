# Williams Treaty Data Ingestion Scripts

This directory contains ingestion scripts for Williams Treaty data sources ported from the [williams-treaties](https://github.com/robertsoden/williams-treaties) repository.

## Overview

These scripts process CSV and geospatial data files and load them into PostGIS for spatial queries by the Ontario Nature Watch agent.

## Available Scripts

### 1. Water Advisories (`ingest_water_advisories.py`)

Processes First Nations drinking water advisories data.

**Data Source:** Indigenous Services Canada
**URL:** https://www.sac-isc.gc.ca/eng/1506514143353/1533317130660

**Usage:**
```bash
python -m src.ingest.ingest_water_advisories <path-to-csv>
```

**Expected CSV Format:**
- Province: ON (Ontario filter)
- Community: Community name
- First Nation: First Nation name (optional)
- Latitude, Longitude: Location coordinates
- Advisory Type: Type of advisory (Boil Water, Do Not Consume, etc.)
- Advisory Date: When advisory was issued
- Lift Date: When advisory was lifted (optional, NULL = active)
- Water System: Name of affected water system (optional)
- Population: Population affected (optional)

**Features:**
- Filters for Ontario communities only
- Calculates advisory duration automatically
- Marks active vs. lifted advisories
- Creates spatial and text search indexes

---

### 2. Indigenous Infrastructure (`ingest_indigenous_infrastructure.py`)

Processes infrastructure project data for First Nations communities.

**Data Source:** Indigenous Community Infrastructure Management (ICIM)
**Provider:** Indigenous Services Canada

**Usage:**
```bash
python -m src.ingest.ingest_indigenous_infrastructure <path-to-csv> \
    [--williams-boundary <path-to-geojson>]
```

**Expected CSV Format:**
- Province: ON (optional filter)
- Community Name: Community name
- First Nation: First Nation name (optional)
- Latitude, Longitude: Location coordinates
- Project Name: Name of infrastructure project
- Infrastructure Category: Category (Education, Health, Housing, etc.)
- Infrastructure Type: Specific type of infrastructure
- Project Status: Status (Completed, In Progress, etc.)
- Funding Amount: Project funding ($)
- Funding Source: Source of funding
- Asset Condition: Condition (Good, Fair, Poor)

**Features:**
- Handles UTF-16 encoding (ICIM format)
- Parses funding amounts (removes $ and commas)
- Identifies projects within Williams Treaty territories
- Can use spatial boundary or First Nation name list

**Williams Boundary:**
If provided, uses spatial intersection to determine which projects are within Williams Treaty territories. Otherwise, matches by First Nation name.

---

### 3. Community Well-Being (`ingest_community_wellbeing.py`)

Processes Community Well-Being (CWB) scores and joins with census boundaries.

**Data Sources:**
- **CWB Scores:** Indigenous Services Canada
- **Boundaries:** Statistics Canada Census Subdivisions

**URLs:**
- CWB: https://www.sac-isc.gc.ca/eng/1345816651029/1557323327644
- Boundaries: https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/

**Usage:**
```bash
python -m src.ingest.ingest_community_wellbeing <cwb-csv> \
    [--csd-boundaries <path-to-boundaries>] \
    [--williams-boundary <path-to-geojson>]
```

**Expected CWB CSV Format:**
- CSD Code: Census Subdivision code
- Community Name: Name of community
- Census Year: Year of census data
- Population: Community population
- CWB Score: Overall well-being score (0-100)
- Education Score: Education component (0-100)
- Labour Force Score: Labour force component (0-100)
- Income Score: Income component (0-100)
- Housing Score: Housing component (0-100)

**Features:**
- Automatically downloads Census boundaries if not provided
- Joins CWB scores with geographic boundaries
- Filters for Ontario (CSD codes starting with 35)
- Identifies First Nations communities
- Calculates Williams Treaty territory membership
- Computes summary statistics

---

## Database Schema

All scripts load data into tables defined in `db/migrations/002_williams_treaty_data.sql`.

**Tables Created:**
- `ontario_water_advisories`
- `ontario_indigenous_infrastructure`
- `ontario_community_wellbeing`
- `ontario_fire_incidents` (requires separate ingestion - not yet implemented)
- `ontario_fire_danger` (requires separate ingestion - not yet implemented)

## Prerequisites

### Python Dependencies

```bash
pip install geopandas pandas shapely sqlalchemy requests
```

### Database Setup

1. Ensure PostgreSQL with PostGIS is running
2. Set `DATABASE_URL` environment variable in `.env`
3. Run database migration:

```bash
psql $DATABASE_URL -f db/migrations/002_williams_treaty_data.sql
```

### Data Files

Download data files from their respective sources:

1. **Water Advisories:** https://www.sac-isc.gc.ca/eng/1506514143353/1533317130660
2. **Infrastructure:** Contact Indigenous Services Canada for ICIM access
3. **Community Well-Being:** https://www.sac-isc.gc.ca/eng/1345816651029/1557323327644

Optional Williams Treaty boundary file can be created from the original repository or downloaded from Indigenous Affairs.

## Common Options

All scripts support these common arguments:

- `--if-exists`: How to handle existing data
  - `replace` (default): Drop and recreate table
  - `append`: Add to existing data
  - `fail`: Error if table exists

## Examples

### Full Workflow

```bash
# 1. Run database migration
psql $DATABASE_URL -f db/migrations/002_williams_treaty_data.sql

# 2. Ingest water advisories
python -m src.ingest.ingest_water_advisories \
    data/ontario/water_advisories.csv

# 3. Ingest infrastructure (with boundary)
python -m src.ingest.ingest_indigenous_infrastructure \
    data/ontario/icim_projects.csv \
    --williams-boundary data/boundaries/williams_treaty.geojson

# 4. Ingest community well-being
python -m src.ingest.ingest_community_wellbeing \
    data/ontario/cwb_2021.csv \
    --williams-boundary data/boundaries/williams_treaty.geojson
```

### Updating Existing Data

```bash
# Replace water advisories with new data
python -m src.ingest.ingest_water_advisories \
    data/water_advisories_2024.csv \
    --if-exists replace

# Append new infrastructure projects
python -m src.ingest.ingest_indigenous_infrastructure \
    data/new_projects.csv \
    --if-exists append
```

## Troubleshooting

### Encoding Issues

If you encounter encoding errors:

1. Try UTF-8 encoding first (default)
2. Script will fall back to Latin-1 (for French characters)
3. ICIM files often use UTF-16 with tab delimiters

### Missing Coordinates

Scripts automatically filter out records without valid latitude/longitude. Check source data if many records are dropped.

### Database Connection

Ensure `DATABASE_URL` is set correctly:

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/ontario_nature_watch"
```

Or add to `.env` file:

```
DATABASE_URL=postgresql://user:password@localhost:5432/ontario_nature_watch
```

### Williams Treaty Boundary

The Williams Treaty boundary file should be a GeoJSON or Shapefile containing the treaty territories. If not available:

1. Scripts will fall back to First Nation name matching
2. Less accurate but still functional
3. Consider creating boundary from the original repository

## Data Quality

### Water Advisories
- **Freshness:** Update weekly/monthly from ISC
- **Completeness:** Government-maintained, generally complete
- **Accuracy:** Coordinates may be approximate (community centroid)

### Infrastructure
- **Access:** Requires ICIM data access from ISC
- **Coverage:** Comprehensive for registered infrastructure
- **Updates:** Project data updated as projects complete

### Community Well-Being
- **Frequency:** Updated every 5 years with census
- **Coverage:** All Census Subdivisions in Ontario
- **Calculation:** Standardized ISC/StatCan methodology

## Output Validation

After ingestion, verify data was loaded correctly:

```sql
-- Check water advisories count
SELECT COUNT(*), COUNT(*) FILTER (WHERE is_active) as active
FROM ontario_water_advisories;

-- Check infrastructure by category
SELECT infrastructure_category, COUNT(*)
FROM ontario_indigenous_infrastructure
GROUP BY infrastructure_category;

-- Check CWB statistics
SELECT
    COUNT(*) as communities,
    AVG(cwb_score) as avg_score,
    COUNT(*) FILTER (WHERE community_type LIKE '%First Nation%') as first_nations
FROM ontario_community_wellbeing;
```

## See Also

- **Main Documentation:** `docs/WILLIAMS_TREATY_DATA_PORT.md`
- **Database Schema:** `db/migrations/002_williams_treaty_data.sql`
- **Data Handler:** `src/tools/data_handlers/williams_treaty_handler.py`
- **Original Repository:** https://github.com/robertsoden/williams-treaties

## Credits

Scripts ported from the [williams-treaties](https://github.com/robertsoden/williams-treaties) repository by Robert Soden.

Adapted for Ontario Nature Watch database architecture and LLM agent integration.
