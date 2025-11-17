# Ontario Data Research Agent Instructions

## Mission Statement

Your task is to identify, evaluate, and prepare production-ready environmental and biodiversity datasets for the Ontario Nature Watch agent. The output should be a comprehensive data integration plan with all necessary technical specifications, API documentation, data schemas, and ingestion scripts ready for implementation.

---

## Background Context

### Current State

The Ontario Nature Watch agent currently has:

**✅ Working Geographic Data**:
- Ontario Provincial Parks (ingested)
- Williams Treaty First Nations territories (manual geocoding, 7 communities)
- Conservation Areas (placeholder data - needs replacement)

**❌ Missing Environmental Data**:
- Biodiversity observations
- Species occurrence data
- Forest cover and health metrics
- Water quality indicators
- Climate and weather patterns
- Ecological monitoring data

**Current Implementation Files**:
- Tools: `/Users/robertsoden/www/onw/src/tools/ontario/`
- Ingestion: `/Users/robertsoden/www/onw/src/ingest/`
- Data handlers: `/Users/robertsoden/www/onw/src/tools/data_handlers/`

### Target Architecture

The Ontario agent needs a data handler implementing the `DataSourceHandler` interface:

```python
class OntarioDataHandler(DataSourceHandler):
    def can_handle(self, dataset: Any) -> bool:
        """Check if dataset is Ontario-specific"""

    async def pull_data(
        self,
        aoi: dict,
        dataset: dict,
        start_date: str,
        end_date: str
    ) -> DataPullResult:
        """Pull data from Ontario sources"""
```

This handler should integrate multiple Ontario data sources and return standardized results compatible with the existing `generate_insights` tool.

---

## Research Objectives

### Primary Deliverables

For each identified dataset, you must provide:

1. **Data Source Documentation**
   - Official name and maintaining organization
   - API/download documentation URL
   - Terms of use and licensing (must be open data or compatible)
   - Attribution requirements
   - Update frequency and data currency

2. **Technical Specifications**
   - API endpoints (REST, WFS, WMS, WCS, etc.)
   - Authentication requirements (API keys, OAuth, etc.)
   - Rate limits and usage quotas
   - Data format (GeoJSON, Shapefile, CSV, JSON, XML)
   - Coordinate reference system (CRS)
   - Temporal coverage (date ranges available)
   - Spatial resolution/granularity

3. **Data Schema Analysis**
   - Field names and data types
   - Required vs optional fields
   - Null value handling
   - Enumerated values (controlled vocabularies)
   - Relationships to other datasets

4. **Sample Data**
   - Working example API calls with responses
   - Sample records in native format
   - Data quality assessment
   - Known issues or quirks

5. **Integration Plan**
   - Mapping to `AgentState` schema
   - Transformation logic needed
   - Caching strategy
   - Error handling requirements

---

## Priority Dataset Categories

### Category 1: Biodiversity & Species Observations (CRITICAL)

**Objective**: Enable queries like "What species are found in Algonquin Park?" or "Show me recent bird observations near Peterborough"

**Required Data Points**:
- Species name (common and scientific)
- Observation date and time
- Location (coordinates or area)
- Observer information (if public)
- Observation quality/verification status
- Photos/media (URLs if available)

**Suggested Sources to Investigate**:

1. **iNaturalist API**
   - Endpoint: `https://api.inaturalist.org/v1/`
   - Documentation: https://api.inaturalist.org/v1/docs/
   - Filter by: Ontario bounding box, specific parks, date ranges
   - Quality grades: research, needs_id, casual
   - **Action**: Test API with sample queries for Ontario locations

2. **eBird API 2.0**
   - Endpoint: `https://api.ebird.org/v2/`
   - Documentation: https://documenter.getpostman.com/view/664302/S1ENwy59
   - Requires API key (free registration)
   - Regional data endpoint: `/data/obs/{regionCode}/recent`
   - **Action**: Register for API key, test Ontario region codes (CA-ON)

3. **GBIF (Global Biodiversity Information Facility)**
   - Endpoint: `https://api.gbif.org/v1/`
   - Documentation: https://www.gbif.org/developer/summary
   - Filter by: `country=CA`, `stateProvince=Ontario`
   - Occurrence data with coordinates
   - **Action**: Test occurrence search with Ontario filters

4. **Ontario Breeding Bird Atlas**
   - Website: https://www.birdsontario.org/atlas/
   - Data availability: Check if API exists or data downloads
   - **Action**: Investigate data access methods, contact if necessary

5. **Ontario Butterfly Atlas**
   - Website: https://www.ontarioinsects.org/atlas/
   - **Action**: Determine if programmatic access available

**Deliverable for Category 1**:
- Comparison matrix of all sources (coverage, freshness, API quality)
- Recommended primary and fallback sources
- Complete API integration guide with code examples
- Data transformation pipeline design

---

### Category 2: Forest Cover & Vegetation (CRITICAL)

**Objective**: Enable queries like "What's the forest health in Kawartha region?" or "Show deforestation trends near conservation areas"

**Required Data Points**:
- Forest cover percentage
- Tree species composition
- Forest health indicators
- Disturbance events (fire, insects, harvest)
- Canopy height and density
- Temporal change detection

**Suggested Sources to Investigate**:

1. **Ontario Forest Resources Inventory (FRI)**
   - Authority: Ontario Ministry of Natural Resources and Forestry
   - Website: https://data.ontario.ca/
   - Search for: "Forest Resources Inventory"
   - **Action**: Check data catalog for latest FRI data, determine if WFS/WMS available

2. **Global Forest Watch - Canada**
   - Already integrated globally via `analytics_handler.py`
   - **Action**: Verify Ontario-specific coverage and resolution
   - Check tree cover loss/gain datasets for Ontario validity

3. **Ontario Land Cover Compilation (OLCC)**
   - Source: Ontario GeoHub
   - **Action**: Find latest version, assess temporal coverage
   - Determine classification scheme and accuracy

4. **Canadian Forest Service - National Forest Inventory**
   - Website: https://nfi.nfis.org/
   - **Action**: Check Ontario-specific datasets
   - Evaluate data format and access methods

5. **Sentinel-2 / Landsat Derived Vegetation Indices**
   - Platform: Google Earth Engine or direct STAC access
   - **Action**: Investigate pre-computed NDVI, EVI for Ontario
   - Check if eoAPI integration can serve this data

**Deliverable for Category 2**:
- Assessment of spatial and temporal resolution for each source
- Recommended approach for forest queries
- Integration with existing GFW analytics handler vs new handler
- Sample queries and expected response formats

---

### Category 3: Water Quality & Aquatic Ecosystems (HIGH PRIORITY)

**Objective**: Enable queries like "What's the water quality in Rice Lake?" or "Show phosphorus levels in Kawartha Lakes"

**Required Data Points**:
- Water quality parameters (pH, dissolved oxygen, turbidity, nutrients)
- Sampling locations and dates
- Lake/river identification
- Trend analysis (improving/declining)
- Trophic status classifications

**Suggested Sources to Investigate**:

1. **Provincial Water Quality Monitoring Network (PWQMN)**
   - Authority: Ontario Ministry of the Environment
   - Website: https://data.ontario.ca/
   - Search for: "Provincial Water Quality Monitoring"
   - **Action**: Find API or bulk download options
   - Map station IDs to lake/river names

2. **Great Lakes Water Quality Data**
   - Source: Environment and Climate Change Canada
   - Portal: https://open.canada.ca/
   - **Action**: Filter for Ontario portion of Great Lakes
   - Check data format and access methods

3. **Conservation Authority Water Monitoring**
   - Example: Kawartha Conservation, TRCA, GRCA
   - **Action**: Survey major conservation authorities for open data
   - Determine if standardized format exists
   - Check coverage and sampling frequency

4. **DataStream - The Water Data Platform**
   - Website: https://datastream.org/
   - Open water data platform for Canada
   - **Action**: Check Ontario coverage and API availability
   - Evaluate data standardization

**Deliverable for Category 3**:
- Inventory of available monitoring stations in Ontario
- Spatial coverage map (which lakes/rivers have data)
- Data quality and completeness assessment
- API integration specifications
- Gap analysis (areas without coverage)

---

### Category 4: Conservation Areas & Protected Lands (CRITICAL)

**Objective**: Replace placeholder data with authoritative conservation area boundaries

**Required Data Points**:
- Conservation area name and designation
- Managing authority (which Conservation Authority)
- Boundaries (accurate geometries)
- Area size, establishment date
- Management classification
- Public access information

**Suggested Sources to Investigate**:

1. **Conservation Ontario**
   - Website: https://conservationontario.ca/
   - **Action**: Look for WFS/WMS services for all 36 Conservation Authorities
   - Check if centralized data portal exists
   - Alternative: Individual CA websites

2. **Ontario GeoHub - Conservation Areas Layer**
   - Website: https://geohub.lio.gov.on.ca/
   - Search for: Conservation lands, conservation reserves
   - **Action**: Identify all relevant layers
   - Download metadata and test WFS access

3. **Protected Planet (WDPA) - Ontario Filter**
   - Already have global WDPA ingested
   - **Action**: Extract Ontario-specific protected areas
   - Cross-reference with provincial data for gaps

4. **Ontario Parks - Conservation Reserves**
   - Different from Provincial Parks
   - **Action**: Check if separate dataset exists
   - Determine overlap with conservation areas

**Current Status**:
- File exists: `src/ingest/ingest_conservation_areas.py` (line 83: placeholder)
- **Action**: Replace placeholder with real data sources identified above

**Deliverable for Category 4**:
- Complete inventory of conservation authorities and their areas
- WFS endpoint list or data download URLs
- Updated ingestion script with real data
- Data validation rules
- Deduplication strategy (avoid overlap with parks/WDPA)

---

### Category 5: Climate & Weather (MEDIUM PRIORITY)

**Objective**: Enable queries about climate patterns, temperature, precipitation trends

**Required Data Points**:
- Temperature (min, max, mean)
- Precipitation
- Growing degree days
- Climate normals (30-year averages)
- Trend analysis
- Station locations

**Suggested Sources to Investigate**:

1. **Environment and Climate Change Canada (ECCC) API**
   - Website: https://api.weather.gc.ca/
   - **Action**: Check station coverage for Ontario
   - Evaluate historical data API vs real-time

2. **Ontario Climate Data Portal**
   - Website: Check for existence of provincial portal
   - **Action**: Assess if exists, data availability

3. **ClimateData.ca**
   - Website: https://climatedata.ca/
   - **Action**: Check API or data download for Ontario
   - Evaluate climate scenario projections

4. **NASA POWER - Agricultural Weather Data**
   - Global coverage at 0.5° resolution
   - **Action**: Test for Ontario coordinates
   - Compare with Canadian sources

**Deliverable for Category 5**:
- Station density map for Ontario
- Recommended approach (gridded vs station-based)
- Historical data availability assessment
- API integration plan

---

### Category 6: Indigenous Territories & Traditional Knowledge (HIGH PRIORITY)

**Objective**: Complete Williams Treaty integration and expand to other Ontario First Nations

**Required Data Points**:
- First Nation community boundaries
- Traditional territory boundaries (where publicly available)
- Treaty areas (historical and modern)
- Community names (official)
- Contact information for data sharing agreements

**Cultural Sensitivity Requirements**:
- Follow OCAP® principles (Ownership, Control, Access, Possession)
- Respect data sovereignty
- Include proper attribution
- Obtain permission for any sensitive data
- Follow protocols in: `src/tools/ontario/prompts.py`

**Suggested Sources to Investigate**:

1. **Statistics Canada - Indigenous Geographies**
   - WFS service mentioned in `src/ingest/ingest_williams_treaty.py:180`
   - **Action**: Implement automated WFS integration
   - Replace manual geocoding with authoritative boundaries

2. **Indigenous Services Canada - First Nations Profiles**
   - Website: https://fnp-ppn.aadnc-aandc.gc.ca/
   - **Action**: Extract Ontario First Nations list
   - Get community information (non-spatial)

3. **Ontario First Nations Maps**
   - **Action**: Search Ontario GeoHub for official boundaries
   - Check with individual First Nations for data sharing

4. **Treaties Recognition Week Resources**
   - **Action**: Verify historical treaty boundaries
   - Ensure Williams Treaty area is accurately represented

5. **Native Land Digital**
   - Website: https://native-land.ca/
   - **Action**: Evaluate as supplementary source
   - Note: Community-generated, verify accuracy

**Current Status**:
- File: `src/ingest/ingest_williams_treaty.py`
- 7 communities manually geocoded
- StatsCan WFS integration pending (line 180)

**Deliverable for Category 6**:
- Complete Ontario First Nations inventory
- WFS integration implementation
- Data sharing protocol documentation
- Attribution requirements
- Recommended approach for sensitive data

---

### Category 7: Species at Risk & Rare Species (HIGH PRIORITY)

**Objective**: Enable queries about endangered species, critical habitat

**Required Data Points**:
- Species name and status (endangered, threatened, special concern)
- Known occurrences (locations may need to be generalized)
- Critical habitat boundaries
- Recovery strategy status
- Population trends

**Suggested Sources to Investigate**:

1. **Ontario Species at Risk Public Registry**
   - Website: https://www.ontario.ca/page/species-risk-ontario
   - **Action**: Check for data downloads or API
   - Determine level of spatial detail available

2. **COSEWIC (Committee on the Status of Endangered Wildlife in Canada)**
   - Website: https://www.cosewic.ca/
   - **Action**: Cross-reference with Ontario data
   - Check assessment reports

3. **Natural Heritage Information Centre (NHIC)**
   - Authority: Ontario Ministry of Natural Resources
   - **Action**: Investigate data access policies
   - Note: May have restricted access due to sensitivity
   - Check for generalized occurrence data

4. **Critical Habitat Boundaries**
   - **Action**: Search Ontario GeoHub for official boundaries
   - Check ECCC for federal SAR critical habitat

**Privacy Considerations**:
- Some rare species locations are protected information
- Use generalized locations (e.g., township level)
- Follow NHIC data sharing protocols

**Deliverable for Category 7**:
- Inventory of accessible species at risk data
- Privacy and sensitivity guidelines
- Data access agreements needed
- Integration plan with appropriate spatial generalization

---

## Technical Requirements

### Data Quality Criteria

All datasets must meet these standards:

1. **Spatial Accuracy**
   - Coordinates in WGS84 (EPSG:4326) or convertible
   - Accuracy documented (e.g., ±10m, ±100m)
   - Invalid geometries handled or flagged

2. **Temporal Currency**
   - Update frequency documented
   - Last update timestamp available
   - Historical data retention policy known

3. **Completeness**
   - Missing data handling strategy
   - Null value conventions documented
   - Coverage gaps identified

4. **Interoperability**
   - Standard formats (GeoJSON, CSV, JSON)
   - Standard vocabularies where applicable
   - Consistent coordinate systems

5. **Accessibility**
   - Open license or compatible terms
   - No cost or sustainable cost model
   - Reliable uptime (>95% if API)

### Integration Specifications

For each dataset, provide:

1. **API Request Examples**
```python
# Example for iNaturalist
import httpx

async def get_observations(
    place_id: int,  # Ontario place ID
    taxon_id: int,  # Species taxon ID
    start_date: str,
    end_date: str
) -> dict:
    url = "https://api.inaturalist.org/v1/observations"
    params = {
        "place_id": place_id,
        "taxon_id": taxon_id,
        "d1": start_date,
        "d2": end_date,
        "quality_grade": "research",
        "per_page": 200
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        return response.json()
```

2. **Data Transformation Logic**
```python
# Example transformation to common schema
def transform_to_standard_schema(raw_data: dict) -> pd.DataFrame:
    """Transform source data to standard format for Ontario handler"""
    records = []
    for obs in raw_data['results']:
        records.append({
            'date': obs['observed_on'],
            'species_common': obs['species_guess'],
            'species_scientific': obs['taxon']['name'],
            'latitude': obs['location'].split(',')[0],
            'longitude': obs['location'].split(',')[1],
            'observer': obs['user']['login'],
            'quality': obs['quality_grade'],
            'photo_url': obs['photos'][0]['url'] if obs['photos'] else None
        })
    return pd.DataFrame(records)
```

3. **Error Handling Requirements**
- Rate limit exceeded (429)
- Authentication failures (401, 403)
- Service unavailable (503)
- Invalid parameters (400)
- No data found (404 or empty results)

4. **Caching Strategy**
- What data can be cached and for how long
- Cache invalidation rules
- Storage requirements

### Database Schema Design

For datasets requiring ingestion to PostGIS:

1. **Table Structure**
```sql
-- Example for biodiversity observations
CREATE TABLE ontario_biodiversity_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    observation_id VARCHAR UNIQUE,  -- Source system ID
    source VARCHAR NOT NULL,  -- 'inaturalist', 'ebird', etc.
    observed_date TIMESTAMP NOT NULL,
    species_common VARCHAR,
    species_scientific VARCHAR NOT NULL,
    location GEOGRAPHY(Point, 4326),
    area_reference VARCHAR,  -- Park or conservation area
    quality_grade VARCHAR,
    observer_id VARCHAR,
    photo_urls TEXT[],
    metadata JSONB,  -- Additional source-specific fields
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_obs_date ON ontario_biodiversity_observations(observed_date);
CREATE INDEX idx_obs_species ON ontario_biodiversity_observations(species_scientific);
CREATE INDEX idx_obs_location ON ontario_biodiversity_observations USING GIST(location);
```

2. **Spatial Indexes**
- GiST indexes for geometry columns
- Covering indexes for common queries

3. **Data Retention Policy**
- How long to keep cached observations
- Update vs append strategy

---

## Research Methodology

### Phase 1: Discovery (Week 1)

**Tasks**:
1. Survey all suggested sources in each category
2. Document what exists vs what doesn't
3. Identify quick wins (easy API integrations)
4. Flag blockers (no API, restricted access, cost)

**Output**:
- Spreadsheet inventory of all sources with:
  - Source name
  - URL
  - API availability (Yes/No/Unknown)
  - License
  - Coverage assessment (Excellent/Good/Fair/Poor)
  - Priority (Critical/High/Medium/Low)
  - Blocker status

### Phase 2: Technical Evaluation (Week 2)

**Tasks**:
1. Register for API keys where needed
2. Test API calls for priority sources
3. Analyze response formats
4. Assess data quality with sample queries
5. Estimate data volumes

**Output**:
- Working API test scripts
- Sample data files
- Data quality report
- Integration complexity assessment

### Phase 3: Design (Week 3)

**Tasks**:
1. Design `OntarioDataHandler` class structure
2. Map datasets to handler methods
3. Design database schemas for ingestion
4. Plan caching architecture
5. Design error handling strategy

**Output**:
- Detailed technical design document
- Class diagrams
- Database schema DDL
- API integration architecture

### Phase 4: Documentation (Week 4)

**Tasks**:
1. Write comprehensive integration guide
2. Document all API endpoints and parameters
3. Create data dictionaries
4. Write attribution requirements
5. Document known limitations

**Output**:
- `ONTARIO_DATA_INTEGRATION_GUIDE.md`
- API reference for each source
- Data schemas and transformations
- Implementation roadmap

---

## Deliverable Format

### Primary Deliverable: Ontario Data Integration Guide

Create a markdown file: `/Users/robertsoden/www/onw/docs/ONTARIO_DATA_INTEGRATION_GUIDE.md`

**Required Sections**:

```markdown
# Ontario Data Integration Guide

## Executive Summary
- Total datasets identified: X
- Ready for immediate integration: Y
- Require data agreements: Z
- Not available/viable: N

## Dataset Inventory

### Category: Biodiversity & Species

#### iNaturalist
- **Status**: ✅ Ready for integration
- **Priority**: Critical
- **API Documentation**: [URL]
- **License**: CC-BY-NC
- **Coverage**: Excellent (100K+ Ontario observations)
- **Update Frequency**: Real-time
- **Rate Limits**: 100 requests/minute
- **Authentication**: None required (optional for higher limits)

**API Endpoints**:
- Observations: `GET https://api.inaturalist.org/v1/observations`
- Species: `GET https://api.inaturalist.org/v1/taxa`

**Sample Request**:
[Code example]

**Sample Response**:
[JSON example]

**Integration Plan**:
[Detailed steps]

**Transformation Logic**:
[Code example]

[Repeat for each dataset...]

## Recommended Architecture

[Class diagrams, sequence diagrams]

## Database Schemas

[Complete DDL for all tables]

## Implementation Roadmap

### Phase 1 (Immediate)
- [ ] Implement iNaturalist integration
- [ ] Implement eBird integration
- [ ] Replace conservation areas placeholder data

### Phase 2 (Short-term)
[...]

## Known Limitations & Gaps

[Document what's not available]

## Attribution Requirements

[How to cite each data source]

## Maintenance & Updates

[How to keep data current]
```

### Secondary Deliverables

1. **Code Templates**: `ontario_handler_template.py`
2. **Ingestion Scripts**: For each dataset requiring database storage
3. **Test Data**: Sample files for testing
4. **API Test Suite**: Automated tests for API integrations
5. **Data Quality Report**: Assessment of each source

---

## Evaluation Criteria

Your research will be evaluated on:

1. **Comprehensiveness** (30%)
   - Did you investigate all suggested sources?
   - Did you identify additional relevant sources?
   - Are there major gaps in coverage?

2. **Technical Accuracy** (25%)
   - Are API specifications correct?
   - Do sample requests actually work?
   - Are data schemas accurate?

3. **Actionability** (25%)
   - Can a developer implement from your documentation?
   - Are integration steps clear and complete?
   - Are code examples functional?

4. **Data Quality Assessment** (10%)
   - Did you evaluate fitness for purpose?
   - Are limitations clearly documented?
   - Did you test with real queries?

5. **Cultural Sensitivity** (10%)
   - Are Indigenous data sovereignty principles followed?
   - Is attribution properly documented?
   - Are privacy considerations addressed?

---

## Success Criteria

Your deliverables should enable:

1. **A developer to implement `OntarioDataHandler`** in 2-3 days using your documentation
2. **Complete replacement of placeholder conservation areas data**
3. **Integration of at least 3 biodiversity data sources** (iNaturalist, eBird, one more)
4. **Production-ready water quality integration** for major Ontario lakes
5. **Automated Williams Treaty boundary ingestion** via StatsCan WFS

The ultimate test: An Ontario user should be able to ask:
- "What birds have been seen in Algonquin Park this month?"
- "How is the water quality in Rice Lake?"
- "Show me species at risk near Curve Lake First Nation"
- "What's the forest cover in the Kawarthas?"

And receive accurate, current data from authoritative Ontario sources.

---

## Resources & References

### Existing Codebase
- Agent state schema: `src/graph/state.py`
- Data handler interface: `src/tools/data_handlers/base.py`
- Example handler: `src/tools/data_handlers/analytics_handler.py`
- Ontario tools: `src/tools/ontario/`
- Ingestion utilities: `src/ingest/utils.py`

### Ontario Government Data Portals
- Ontario Data Catalogue: https://data.ontario.ca/
- Ontario GeoHub: https://geohub.lio.gov.on.ca/
- Land Information Ontario: https://www.ontario.ca/page/land-information-ontario

### Federal Data Portals
- Open Canada: https://open.canada.ca/
- Government of Canada Geospatial Platform: https://geo.ca/

### Documentation Standards
- Follow Google-style docstrings
- Include type hints for all functions
- Provide usage examples
- Document error conditions

---

## Questions & Support

If you encounter blockers or need clarification:

1. **API Access Issues**: Document what you tried and the specific error
2. **License Ambiguity**: Note the specific terms causing concern
3. **Technical Complexity**: Describe the challenge and potential solutions
4. **Data Quality Concerns**: Document specific issues with examples

Remember: The goal is production-ready data integration. Prioritize sources that are:
- ✅ Open and accessible
- ✅ Well-documented
- ✅ Actively maintained
- ✅ Authoritative
- ✅ Spatially and temporally comprehensive

Good luck with your research!
