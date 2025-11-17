# Williams Treaty Data Sources - Port Documentation

This document describes the Williams Treaty data sources ported from the [williams-treaties](https://github.com/robertsoden/williams-treaties) repository into Ontario Nature Watch.

## Overview

The Williams Treaty data sources add critical Indigenous-focused environmental and social data to Ontario Nature Watch, including:

1. **First Nations Water Advisories** - Drinking water safety alerts
2. **Fire Incidents & Danger Ratings** - Historical fires and current fire risk
3. **Indigenous Infrastructure Projects** - Community infrastructure data
4. **Community Well-Being Indicators** - Social health metrics

These data sources complement the existing Ontario environmental data (iNaturalist, eBird, Global Forest Watch) with Indigenous-specific datasets focused on the Williams Treaty Territories.

## Williams Treaty Context

The **Williams Treaties** were signed in 1923 between the Crown and seven First Nations in central Ontario:

- Alderville First Nation
- Curve Lake First Nation
- Hiawatha First Nation
- Mississaugas of Scugog Island First Nation
- Chippewas of Beausoleil First Nation
- Chippewas of Georgina Island First Nation
- Chippewas of Rama First Nation

The treaties cover approximately **20,000 square kilometers** in the Lake Simcoe, Kawartha Lakes, and Georgian Bay regions.

## Architecture

### Data Handler

**File:** `src/tools/data_handlers/williams_treaty_handler.py`

The `WilliamsTreatyDataHandler` class provides a unified interface for querying Williams Treaty data sources. Unlike the Ontario handler (which queries external APIs), this handler primarily queries data that has been pre-loaded into the PostGIS database.

**Supported Sources:**
- `WaterAdvisories` - Query drinking water advisories
- `FireIncidents` - Historical fire perimeter data
- `FireDanger` - Current/recent fire danger ratings
- `Infrastructure` - Indigenous infrastructure projects
- `CommunityWellbeing` - Community well-being scores

### Database Schema

**File:** `db/migrations/002_williams_treaty_data.sql`

**Tables Created:**

1. **ontario_water_advisories**
   - First Nations drinking water advisories (boil water, do not consume, etc.)
   - Tracks active vs. lifted advisories
   - Includes duration calculations and population affected

2. **ontario_fire_incidents**
   - Historical fire perimeter data from Ontario MNRF
   - Fire cause, area burned, suppression costs
   - Supports queries by year, region, and cause

3. **ontario_fire_danger**
   - Current fire weather and danger ratings from CWFIS
   - Fire Weather Index (FWI), Initial Spread Index (ISI), etc.
   - Danger classes: Low, Moderate, High, Very High, Extreme

4. **ontario_indigenous_infrastructure**
   - Infrastructure projects in First Nations communities
   - Categories: Education, Health, Housing, Water/Wastewater
   - Project status, funding amounts, asset condition

5. **ontario_community_wellbeing**
   - Community Well-Being (CWB) scores from Statistics Canada
   - Components: Education, Labour Force, Income, Housing
   - Includes First Nations and non-Indigenous communities for comparison

**Key Features:**
- Spatial indexes on all geometry columns (PostGIS GIST)
- Text search indexes using trigrams (fuzzy matching)
- Automatic timestamp triggers
- Helper views for common queries
- Advisory duration calculation triggers

### Ingestion Scripts

Data must be manually downloaded and ingested into the database using these scripts:

#### 1. Water Advisories

**File:** `src/ingest/ingest_water_advisories.py`

```bash
# Download CSV from Indigenous Services Canada
# https://www.sac-isc.gc.ca/eng/1506514143353/1533317130660

python -m src.ingest.ingest_water_advisories data/water_advisories.csv
```

**Expected CSV Columns:**
- Community, First Nation, Region
- Latitude, Longitude
- Advisory Type, Advisory Date, Lift Date
- Water System, Population

#### 2. Indigenous Infrastructure

**File:** `src/ingest/ingest_indigenous_infrastructure.py`

```bash
# Contact Indigenous Services Canada for ICIM data access

python -m src.ingest.ingest_indigenous_infrastructure data/icim_projects.csv \
    --williams-boundary data/boundaries/williams_treaty.geojson
```

**Expected CSV Columns:**
- Community Name, First Nation
- Latitude, Longitude
- Project Name, Infrastructure Category
- Project Status, Funding Amount

#### 3. Community Well-Being

**File:** `src/ingest/ingest_community_wellbeing.py`

```bash
# Download CWB data from ISC
# https://www.sac-isc.gc.ca/eng/1345816651029/1557323327644

python -m src.ingest.ingest_community_wellbeing data/cwb_2021.csv \
    --williams-boundary data/boundaries/williams_treaty.geojson
```

**Features:**
- Automatically downloads Census Subdivision boundaries from Statistics Canada
- Joins CWB scores with geographic boundaries
- Filters for Ontario communities
- Identifies Williams Treaty territories

## Data Sources & APIs

### 1. First Nations Water Advisories

**Source:** Indigenous Services Canada (ISC)
**URL:** https://www.sac-isc.gc.ca/eng/1506514143353/1533317130660
**Format:** CSV (updated regularly)
**Coverage:** All First Nations in Canada

**Data Quality:**
- Official government data
- Updated regularly (weekly/monthly)
- Includes historical advisory information

### 2. Fire Data

**Historical Fires:**
- **Source:** Ontario Ministry of Natural Resources and Forestry (MNRF)
- **URL:** https://geohub.lio.gov.on.ca/
- **Coverage:** Historical fire perimeters (decades of data)

**Current Fire Danger:**
- **Source:** Canadian Wildland Fire Information System (CWFIS)
- **URL:** https://cwfis.cfs.nrcan.gc.ca/
- **Format:** WMS/WFS services
- **Update Frequency:** Daily

### 3. Infrastructure Projects

**Source:** Indigenous Community Infrastructure Management (ICIM)
**Provider:** Indigenous Services Canada
**Access:** Requires permission/request
**Coverage:** All First Nations infrastructure assets

**Categories:**
- Education facilities (schools, training centers)
- Health facilities (nursing stations, health centers)
- Housing (residential units, multi-family dwellings)
- Water/Wastewater systems
- Transportation infrastructure
- Community buildings

### 4. Community Well-Being

**Source:** Indigenous Services Canada / Statistics Canada
**URL:** https://www.sac-isc.gc.ca/eng/1345816651029/1557323327644
**Format:** CSV
**Coverage:** All Canadian communities (Census Subdivisions)

**Components:**
- **Education:** High school completion, university degree attainment
- **Labour Force:** Employment rate, labour force participation
- **Income:** Median household income
- **Housing:** Condition and crowding metrics

**Score Range:** 0-100 (higher is better)

## Usage Examples

### Query Water Advisories

```python
from src.tools.data_handlers.williams_treaty_handler import WilliamsTreatyDataHandler

handler = WilliamsTreatyDataHandler()

result = await handler.pull_data(
    query="Show active water advisories near Curve Lake First Nation",
    aoi=curve_lake_aoi,
    subregion_aois=[],
    subregion="",
    subtype="",
    dataset={"source": "WaterAdvisories"},
    start_date="2020-01-01",
    end_date="2024-12-31"
)

# Result includes:
# - Active vs. lifted advisories
# - Duration of each advisory
# - Affected population
# - Advisory type (Boil Water, Do Not Consume, etc.)
```

### Query Fire Incidents

```python
result = await handler.pull_data(
    query="Show forest fires in the last 10 years",
    aoi=williams_treaty_aoi,
    subregion_aois=[],
    subregion="",
    subtype="",
    dataset={"source": "FireIncidents"},
    start_date="2014-01-01",
    end_date="2024-12-31"
)

# Result includes:
# - Fire perimeters (geometry)
# - Area burned (hectares)
# - Fire cause (Lightning, Human, Unknown)
# - Suppression costs
```

### Query Community Well-Being

```python
result = await handler.pull_data(
    query="Compare community well-being scores",
    aoi=williams_treaty_aoi,
    subregion_aois=[],
    subregion="",
    subtype="",
    dataset={"source": "CommunityWellbeing"},
    start_date="2021-01-01",
    end_date="2021-12-31"
)

# Result includes:
# - Overall CWB score
# - Component scores (education, labour, income, housing)
# - First Nations vs. non-Indigenous comparison
# - Census year
```

## Integration with Ontario Agent

The Williams Treaty data sources are automatically available to the Ontario Nature Watch agent through the data pull orchestrator.

**Example Queries:**

1. *"Are there any active water advisories in Williams Treaty territories?"*
   - Agent selects Williams Treaty AOI
   - Queries WaterAdvisories dataset
   - Returns active advisories with duration and details

2. *"Show me fire incidents near Curve Lake First Nation in the last 5 years"*
   - Agent selects Curve Lake area
   - Queries FireIncidents dataset
   - Returns fire perimeters, causes, and areas

3. *"Compare infrastructure funding across Williams Treaty First Nations"*
   - Agent selects Williams Treaty territories
   - Queries Infrastructure dataset
   - Returns projects by community with funding amounts

4. *"What is the community well-being score for Alderville First Nation?"*
   - Agent selects Alderville AOI
   - Queries CommunityWellbeing dataset
   - Returns CWB score with component breakdown

## Database Maintenance

### Updating Water Advisories

Water advisories should be updated regularly (weekly/monthly) as they change frequently:

```bash
# Download latest CSV from ISC
python -m src.ingest.ingest_water_advisories data/water_advisories_latest.csv \
    --if-exists replace
```

### Adding New Fire Data

Historical fire data can be appended as new years become available:

```bash
# Process new fire data
python -m src.ingest.ingest_fire_incidents data/fire_2024.geojson \
    --if-exists append
```

### Refreshing Community Well-Being

CWB data is released every 5 years with the census:

```bash
# Ingest new census year
python -m src.ingest.ingest_community_wellbeing data/cwb_2026.csv \
    --if-exists append
```

## Cultural Sensitivity Guidelines

When working with Williams Treaty data, follow these important guidelines:

### 1. Respect Indigenous Data Sovereignty

- First Nations communities have inherent rights to their data
- Data sharing should be done with community knowledge and consent
- Some data may be culturally sensitive and require restricted access

### 2. Proper Terminology

- Use full names: "Curve Lake First Nation" (not "Curve Lake")
- Avoid possessive language about land
- Acknowledge continuing relationship with territory

### 3. Context Awareness

- Williams Treaties were signed in 1923
- First Nations continue active stewardship of these lands
- Many communities are engaged in environmental monitoring and conservation

### 4. Data Interpretation

- Water advisories reflect infrastructure challenges, not community capacity
- CWB scores should be contextualized with historical and systemic factors
- Infrastructure data shows needs and investments, not deficits

## Comparison: Original vs. Ported

### Original williams-treaties Repository

**Purpose:** Static web-based mapping tool
**Architecture:** Python scripts → GeoJSON → HTML/JS map
**Data Flow:** Download → Process → Export → Visualize
**Use Case:** Exploring Williams Treaty environmental data

### Ontario Nature Watch Port

**Purpose:** LLM-powered natural language query system
**Architecture:** Database-backed handlers → Agent tools
**Data Flow:** Ingest → Database → Query → LLM response
**Use Case:** Interactive questions about Ontario environmental data

### What Was Preserved

✅ Data sources and processing logic
✅ Spatial analysis capabilities
✅ Williams Treaty territorial focus
✅ Cultural sensitivity considerations

### What Was Adapted

🔄 Static files → PostGIS database
🔄 Manual visualization → Natural language queries
🔄 Standalone tool → Integrated with Ontario Nature Watch
🔄 Script-based → Handler-based architecture

## Future Enhancements

### Phase 2 Additions

1. **Ontario Fire Risk Zones**
   - Real-time fire danger from CWFIS WFS service
   - Fuel type mapping
   - Elevation data integration

2. **Land Cover Change Detection**
   - NRCan land cover datasets (2010, 2015, 2020)
   - NDVI time series analysis
   - Deforestation tracking

3. **Water Quality Monitoring**
   - Provincial Water Quality Monitoring Network (PWQMN)
   - DataStream water quality data
   - Integration with existing water advisory data

### Potential Improvements

- **Automated Data Updates:** Scheduled ingestion from ISC APIs
- **Real-time Fire Danger:** Direct CWFIS API integration for current conditions
- **Temporal Analysis:** Time-series queries for trends (fire frequency, CWB changes)
- **Spatial Relationships:** Cross-dataset queries (fires near communities, advisories + infrastructure)

## References

### Original Repository
- **GitHub:** https://github.com/robertsoden/williams-treaties
- **Author:** Robert Soden
- **Purpose:** Williams Treaty Territories environmental mapping

### Data Sources
- **Indigenous Services Canada:** https://www.sac-isc.gc.ca/
- **Ontario GeoHub:** https://geohub.lio.gov.on.ca/
- **CWFIS:** https://cwfis.cfs.nrcan.gc.ca/
- **Statistics Canada:** https://www.statcan.gc.ca/

### Williams Treaties
- **Ontario Ministry of Indigenous Affairs:** https://www.ontario.ca/page/williams-treaties
- **Williams Treaties First Nations:** https://www.williamstreatiesfirstnations.ca/

## Contributing

To add new Williams Treaty data sources:

1. Add table schema to `db/migrations/002_williams_treaty_data.sql`
2. Create ingestion script in `src/ingest/`
3. Add data source case to `williams_treaty_handler.py`
4. Update this documentation
5. Test with sample queries

## Support

For issues or questions about Williams Treaty data integration:
- Review this documentation
- Check the original repository: https://github.com/robertsoden/williams-treaties
- Consult data source documentation (ISC, MNRF, etc.)

---

**Document Version:** 1.0
**Last Updated:** 2024
**Ported By:** Claude Code Agent
**Original Author:** Robert Soden
