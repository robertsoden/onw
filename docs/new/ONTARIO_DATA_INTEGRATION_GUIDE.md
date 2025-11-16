# Ontario Data Integration Guide

**Version:** 1.0  
**Date:** November 16, 2025  
**Status:** Production Ready  
**For:** Ontario Nature Watch Platform

---

## Executive Summary

This guide provides comprehensive technical specifications for integrating Ontario environmental and biodiversity datasets into the Ontario Nature Watch platform. 

**Dataset Overview:**
- **Total datasets identified:** 25+
- **Ready for immediate integration:** 12
- **Require API registration:** 3
- **Data agreements needed:** 2
- **Not viable/available:** 3

**Priority Integration Targets:**
1. ✅ **iNaturalist** - 100K+ Ontario observations, real-time
2. ✅ **eBird** - Comprehensive bird observations, free API
3. ✅ **GBIF** - Global biodiversity data with Ontario filtering
4. ✅ **Conservation Ontario Open Data** - WFS/WMS services available
5. ✅ **PWQMN** - Provincial water quality monitoring (400+ stations)
6. ✅ **DataStream** - Standardized water data API (OData v4)
7. ⚠️ **Forest Resources Inventory** - Available via Ontario GeoHub
8. ✅ **Historic Treaties** - Federal open data WFS

---

## Category 1: Biodiversity & Species Observations

### 1.1 iNaturalist API

**Status:** ✅ Production Ready  
**Priority:** CRITICAL  
**Coverage:** Excellent - 100,000+ Ontario observations  
**Update Frequency:** Real-time  
**License:** CC-BY / CC-BY-NC / CC0 (varies by observation)

#### Technical Specifications

**API Base URL:** `https://api.inaturalist.org/v1/`  
**Documentation:** https://api.inaturalist.org/v1/docs/  
**Authentication:** None required for read-only access (optional API key for higher limits)  
**Rate Limits:** 100 requests/minute (recommended: 60 req/min)  
**Data Format:** JSON  
**CRS:** WGS84 (EPSG:4326)

#### Key Endpoints

**Observations Search:**
```
GET /observations
```

**Parameters:**
- `place_id` - Ontario place ID (6942)
- `nelat`, `nelng`, `swlat`, `swlng` - Bounding box
- `taxon_id` - Filter by species
- `quality_grade` - research, needs_id, casual
- `d1`, `d2` - Date range (YYYY-MM-DD)
- `per_page` - Results per page (max 200)
- `page` - Page number
- `order_by` - created_at, observed_on, etc.
- `geo` - true (require coordinates)
- `photos` - true (require photos)

**Species/Taxa Search:**
```
GET /taxa
```

**Parameters:**
- `q` - Search query
- `place_id` - Filter by location
- `rank` - species, genus, family, etc.

#### Sample Request

```python
import requests

# Get recent research-grade observations in Ontario
url = "https://api.inaturalist.org/v1/observations"
params = {
    "place_id": 6942,  # Ontario
    "quality_grade": "research",
    "geo": "true",
    "photos": "true",
    "per_page": 200,
    "order": "desc",
    "order_by": "created_at"
}

response = requests.get(url, params=params)
data = response.json()

for obs in data['results']:
    print(f"Species: {obs['taxon']['name']}")
    print(f"Location: {obs['location']}")
    print(f"Observed: {obs['observed_on']}")
    print(f"Quality: {obs['quality_grade']}")
```

#### Sample Response Structure

```json
{
  "total_results": 245678,
  "page": 1,
  "per_page": 200,
  "results": [
    {
      "id": 123456789,
      "observed_on": "2025-11-15",
      "observed_on_string": "2025-11-15",
      "time_observed_at": "2025-11-15T14:30:00-05:00",
      "created_at": "2025-11-15T15:45:00-05:00",
      "updated_at": "2025-11-16T09:20:00-05:00",
      "quality_grade": "research",
      "license": "CC-BY-NC",
      "location": "44.2312,-78.2642",
      "place_guess": "Peterborough, ON, CA",
      "positional_accuracy": 10,
      "taxon": {
        "id": 47219,
        "name": "Pinus strobus",
        "common_name": "Eastern White Pine",
        "rank": "species",
        "iconic_taxon_name": "Plantae",
        "preferred_common_name": "Eastern White Pine"
      },
      "user": {
        "id": 12345,
        "login": "naturalist123"
      },
      "photos": [
        {
          "id": 987654,
          "url": "https://inaturalist-open-data.s3.amazonaws.com/photos/987654/medium.jpg",
          "license_code": "cc-by-nc"
        }
      ],
      "identifications_count": 3,
      "comments_count": 1,
      "geojson": {
        "type": "Point",
        "coordinates": [-78.2642, 44.2312]
      }
    }
  ]
}
```

#### Data Transformation for AgentState

```python
def transform_inat_observation(obs: dict) -> dict:
    """Transform iNaturalist observation to Ontario agent format."""
    return {
        "source": "iNaturalist",
        "observation_id": obs['id'],
        "species_name": obs['taxon']['name'],
        "common_name": obs['taxon'].get('preferred_common_name', ''),
        "scientific_name": obs['taxon']['name'],
        "taxonomy": {
            "rank": obs['taxon']['rank'],
            "iconic_taxon": obs['taxon'].get('iconic_taxon_name'),
            "taxon_id": obs['taxon']['id']
        },
        "observation_date": obs['observed_on'],
        "observation_datetime": obs.get('time_observed_at'),
        "location": {
            "type": "Point",
            "coordinates": [
                float(obs['location'].split(',')[1]),  # longitude
                float(obs['location'].split(',')[0])   # latitude
            ]
        },
        "accuracy_meters": obs.get('positional_accuracy'),
        "place_name": obs.get('place_guess'),
        "quality_grade": obs['quality_grade'],
        "license": obs.get('license'),
        "observer": obs['user']['login'],
        "photos": [photo['url'] for photo in obs.get('photos', [])],
        "identifications_count": obs.get('identifications_count', 0),
        "url": f"https://www.inaturalist.org/observations/{obs['id']}"
    }
```

#### Integration Strategy

**Caching:**
- Cache observations by spatial grid (0.1° x 0.1°)
- Update frequency: Daily for active areas, weekly for less active
- Store in PostgreSQL with PostGIS

**Database Schema:**
```sql
CREATE TABLE inat_observations (
    id BIGINT PRIMARY KEY,
    taxon_id INTEGER,
    scientific_name VARCHAR(255),
    common_name VARCHAR(255),
    observation_date DATE,
    observation_datetime TIMESTAMP WITH TIME ZONE,
    location GEOGRAPHY(POINT, 4326),
    place_name VARCHAR(255),
    quality_grade VARCHAR(50),
    license VARCHAR(50),
    observer VARCHAR(100),
    photo_urls TEXT[],
    data_source VARCHAR(50) DEFAULT 'iNaturalist',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT check_quality_grade CHECK (quality_grade IN ('research', 'needs_id', 'casual'))
);

CREATE INDEX idx_inat_location ON inat_observations USING GIST(location);
CREATE INDEX idx_inat_date ON inat_observations(observation_date);
CREATE INDEX idx_inat_taxon ON inat_observations(taxon_id);
CREATE INDEX idx_inat_quality ON inat_observations(quality_grade);
```

**Error Handling:**
- Implement exponential backoff for rate limiting
- Cache failed requests for retry
- Log API errors with context

**Attribution:**
> "Observation data provided by iNaturalist (www.inaturalist.org). Individual observations licensed under [specific license]."

---

### 1.2 eBird API 2.0

**Status:** ✅ Production Ready  
**Priority:** CRITICAL  
**Coverage:** Excellent - Ontario bird observations  
**Update Frequency:** Real-time  
**License:** eBird Terms of Use (attribution required)

#### Technical Specifications

**API Base URL:** `https://api.ebird.org/v2/`  
**Documentation:** https://documenter.getpostman.com/view/664302/S1ENwy59  
**Authentication:** API key required (free registration)  
**Registration:** https://ebird.org/api/keygen  
**Rate Limits:** Not publicly specified, recommend 2-5 req/sec  
**Data Format:** JSON  
**CRS:** WGS84 (EPSG:4326)

#### Key Endpoints

**Recent Observations in Region:**
```
GET /data/obs/{regionCode}/recent
GET /data/obs/{regionCode}/recent/{speciesCode}
```

**Region Code:** `CA-ON` (Ontario)  
**Parameters:**
- `back` - Days back (1-30, default 14)
- `maxResults` - Max records (1-10000)
- `hotspot` - true/false
- `includeProvisional` - true/false

**Recent Notable Observations:**
```
GET /data/obs/{regionCode}/recent/notable
```

**Historic Observations on Date:**
```
GET /data/obs/{regionCode}/historic/{y}/{m}/{d}
```

**Hotspots in Region:**
```
GET /ref/hotspot/{regionCode}
```

**Taxonomy:**
```
GET /ref/taxonomy/ebird
```

#### Sample Request

```python
import requests

API_KEY = "your_api_key_here"
headers = {"x-ebirdapitoken": API_KEY}

# Get recent observations in Ontario
url = "https://api.ebird.org/v2/data/obs/CA-ON/recent"
params = {
    "back": 30,
    "maxResults": 1000
}

response = requests.get(url, headers=headers, params=params)
observations = response.json()

for obs in observations:
    print(f"{obs['comName']} ({obs['sciName']})")
    print(f"Location: {obs['locName']}")
    print(f"Date: {obs['obsDt']}")
    print(f"Count: {obs.get('howMany', 'X')}")
```

#### Sample Response Structure

```json
[
  {
    "speciesCode": "norcar",
    "comName": "Northern Cardinal",
    "sciName": "Cardinalis cardinalis",
    "locId": "L123456",
    "locName": "Peterborough--Jackson Park",
    "obsDt": "2025-11-15 14:30",
    "howMany": 2,
    "lat": 44.2975,
    "lng": -78.3167,
    "obsValid": true,
    "obsReviewed": true,
    "locationPrivate": false,
    "subId": "S987654321"
  }
]
```

#### Data Transformation

```python
def transform_ebird_observation(obs: dict) -> dict:
    """Transform eBird observation to Ontario agent format."""
    return {
        "source": "eBird",
        "observation_id": obs['subId'],
        "species_code": obs['speciesCode'],
        "common_name": obs['comName'],
        "scientific_name": obs['sciName'],
        "observation_datetime": obs['obsDt'],
        "location": {
            "type": "Point",
            "coordinates": [obs['lng'], obs['lat']]
        },
        "location_name": obs['locName'],
        "location_id": obs['locId'],
        "count": obs.get('howMany'),
        "valid": obs.get('obsValid', True),
        "reviewed": obs.get('obsReviewed', False),
        "url": f"https://ebird.org/checklist/{obs['subId']}"
    }
```

#### Integration Strategy

**Database Schema:**
```sql
CREATE TABLE ebird_observations (
    submission_id VARCHAR(50) PRIMARY KEY,
    species_code VARCHAR(10),
    common_name VARCHAR(255),
    scientific_name VARCHAR(255),
    observation_datetime TIMESTAMP WITH TIME ZONE,
    location GEOGRAPHY(POINT, 4326),
    location_name VARCHAR(255),
    location_id VARCHAR(50),
    count INTEGER,
    obs_valid BOOLEAN DEFAULT true,
    obs_reviewed BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ebird_location ON ebird_observations USING GIST(location);
CREATE INDEX idx_ebird_datetime ON ebird_observations(observation_datetime);
CREATE INDEX idx_ebird_species ON ebird_observations(species_code);
```

**Attribution:**
> "Bird observation data provided by eBird (www.ebird.org). Accessed [date]."

---

### 1.3 GBIF (Global Biodiversity Information Facility)

**Status:** ✅ Production Ready  
**Priority:** HIGH  
**Coverage:** Excellent - Global with Ontario filtering  
**Update Frequency:** Weekly  
**License:** Varies by dataset (CC0, CC-BY, CC-BY-NC)

#### Technical Specifications

**API Base URL:** `https://api.gbif.org/v1/`  
**Documentation:** https://techdocs.gbif.org/en/openapi/  
**Authentication:** None for search, required for downloads  
**Rate Limits:** 100,000 records max via search API  
**Recommended:** Use download API for bulk data  
**Data Format:** JSON, DarwinCore  
**CRS:** WGS84 (EPSG:4326)

#### Key Endpoints

**Occurrence Search:**
```
GET /occurrence/search
```

**Parameters:**
- `country=CA`
- `stateProvince=Ontario`
- `hasCoordinate=true`
- `hasGeospatialIssue=false`
- `year=2024`
- `month=1,2,3`
- `taxonKey` - Species identifier
- `datasetKey` - Specific dataset
- `limit` - Records per page (max 300)
- `offset` - Pagination offset

**Occurrence Download (for large datasets):**
```
POST /occurrence/download/request
```

**Species Search:**
```
GET /species/search
```

#### Sample Request

```python
import requests

# Search for observations in Ontario
url = "https://api.gbif.org/v1/occurrence/search"
params = {
    "country": "CA",
    "stateProvince": "Ontario",
    "hasCoordinate": "true",
    "hasGeospatialIssue": "false",
    "year": "2024",
    "limit": 300
}

response = requests.get(url, params=params)
data = response.json()

print(f"Total results: {data['count']}")
for record in data['results']:
    print(f"{record.get('scientificName')}")
    print(f"Lat: {record.get('decimalLatitude')}, Lon: {record.get('decimalLongitude')}")
    print(f"Date: {record.get('eventDate')}")
```

#### Sample Response Structure

```json
{
  "offset": 0,
  "limit": 300,
  "endOfRecords": false,
  "count": 125000,
  "results": [
    {
      "key": 1234567890,
      "datasetKey": "abc-123-def",
      "publishingCountry": "CA",
      "protocol": "DWC_ARCHIVE",
      "scientificName": "Pinus strobus L.",
      "kingdom": "Plantae",
      "phylum": "Tracheophyta",
      "class": "Pinopsida",
      "order": "Pinales",
      "family": "Pinaceae",
      "genus": "Pinus",
      "species": "Pinus strobus",
      "genericName": "Pinus",
      "specificEpithet": "strobus",
      "taxonRank": "SPECIES",
      "decimalLatitude": 44.2312,
      "decimalLongitude": -78.2642,
      "coordinateUncertaintyInMeters": 100,
      "stateProvince": "Ontario",
      "country": "CA",
      "countryCode": "CA",
      "eventDate": "2024-06-15T00:00:00",
      "year": 2024,
      "month": 6,
      "day": 15,
      "basisOfRecord": "HUMAN_OBSERVATION",
      "institutionCode": "ROM",
      "collectionCode": "ROMBOT"
    }
  ]
}
```

#### Integration Strategy

**Use Cases:**
- Supplement iNaturalist and eBird data
- Historical occurrence records
- Museum and herbarium specimens
- Research-grade biodiversity data

**Caching:**
- Full Ontario download quarterly
- Incremental updates monthly
- Store in normalized tables

**Database Schema:**
```sql
CREATE TABLE gbif_occurrences (
    gbif_key BIGINT PRIMARY KEY,
    dataset_key VARCHAR(50),
    scientific_name VARCHAR(255),
    kingdom VARCHAR(100),
    phylum VARCHAR(100),
    class VARCHAR(100),
    family VARCHAR(100),
    genus VARCHAR(100),
    species VARCHAR(255),
    location GEOGRAPHY(POINT, 4326),
    coordinate_uncertainty REAL,
    event_date DATE,
    basis_of_record VARCHAR(50),
    institution_code VARCHAR(100),
    collection_code VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_gbif_location ON gbif_occurrences USING GIST(location);
CREATE INDEX idx_gbif_date ON gbif_occurrences(event_date);
CREATE INDEX idx_gbif_species ON gbif_occurrences(scientific_name);
```

**Attribution:**
> "Species occurrence data from GBIF.org. [Citation DOI if using download]"

---

## Category 2: Forest Cover & Vegetation

### 2.1 Ontario Forest Resources Inventory (FRI)

**Status:** ⚠️ Available, Complex Integration  
**Priority:** HIGH  
**Coverage:** Managed Forest Zone (~555,000 km²)  
**Update Frequency:** 10-year cycle per forest management unit  
**License:** Open Government License - Ontario

#### Technical Specifications

**Source:** Ontario GeoHub  
**Portal:** https://geohub.lio.gov.on.ca/  
**Format:** Shapefile, GeoDatabase, REST Services  
**CRS:** NAD83 / Ontario MNR Lambert (EPSG:3161)  
**Current Version:** Term 2 (T2) 2018-2028

#### Data Access Methods

**1. Direct Download (per Forest Management Unit):**
https://geohub.lio.gov.on.ca/maps/lio::forest-resource-inventory-term-2-t2-2018-2028/

**2. WMS Service:**
```
https://ws.lioservices.lrc.gov.on.ca/arcgis2/rest/services/LIO_Cartographic/LIO_Topographic/MapServer
```

**3. WFS Service:**
```
https://ws.lioservices.lrc.gov.on.ca/arcgis2/services/LIO_OPEN_DATA/LIO_Open_Data/MapServer/WFSServer
```

#### Key Attributes

- `POLYTYPE` - Stand type code
- `SPCOMP` - Species composition (e.g., "Pw70Pr20Sw10")
- `AGE` - Stand age
- `HT` - Height class
- `DENSITY` - Crown closure
- `YRORG` - Year of origin
- `DEVSTAGE` - Development stage
- `FORMOD` - Forest modifier

#### Sample Data Processing

```python
import geopandas as gpd

# Load FRI data for a forest management unit
fri_data = gpd.read_file("path/to/FRI_shapefile.shp")

# Filter for specific area
aoi_bounds = (-78.5, 44.0, -78.0, 44.5)  # minx, miny, maxx, maxy
fri_filtered = fri_data.cx[aoi_bounds[0]:aoi_bounds[2], aoi_bounds[1]:aoi_bounds[3]]

# Parse species composition
def parse_species_comp(spcomp_str):
    """
    Parse species composition string.
    Example: "Pw70Pr20Sw10" -> {"Pw": 70, "Pr": 20, "Sw": 10}
    """
    species = {}
    i = 0
    while i < len(spcomp_str):
        if spcomp_str[i:i+2].isalpha():
            sp_code = spcomp_str[i:i+2]
            i += 2
            pct = ""
            while i < len(spcomp_str) and spcomp_str[i].isdigit():
                pct += spcomp_str[i]
                i += 1
            if pct:
                species[sp_code] = int(pct)
    return species

fri_filtered['species_dict'] = fri_filtered['SPCOMP'].apply(parse_species_comp)
```

#### Integration Strategy

**Approach:**
- Pre-process FRI data per forest management unit
- Ingest into PostGIS with proper spatial indexing
- Provide summary statistics by area of interest
- Link to species codes table

**Database Schema:**
```sql
CREATE TABLE fri_stands (
    id SERIAL PRIMARY KEY,
    fmu_name VARCHAR(100),
    polytype VARCHAR(50),
    species_composition VARCHAR(100),
    age INTEGER,
    height_class VARCHAR(10),
    density INTEGER,
    year_origin INTEGER,
    development_stage VARCHAR(50),
    geometry GEOGRAPHY(MULTIPOLYGON, 4326),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_fri_geometry ON fri_stands USING GIST(geometry);
CREATE INDEX idx_fri_fmu ON fri_stands(fmu_name);

-- Species composition table
CREATE TABLE fri_species (
    stand_id INTEGER REFERENCES fri_stands(id),
    species_code VARCHAR(2),
    percentage INTEGER,
    PRIMARY KEY (stand_id, species_code)
);

-- Species codes lookup
CREATE TABLE species_codes (
    code VARCHAR(2) PRIMARY KEY,
    scientific_name VARCHAR(255),
    common_name VARCHAR(255)
);
```

**Known Limitations:**
- Data vintage varies by FMU (some units not updated since 2010-2015)
- Does not cover Far North regions
- Complex attribute interpretation required
- Large file sizes (several GB per FMU)

---

### 2.2 Global Forest Watch - Canada Coverage

**Status:** ✅ Already Integrated (via analytics_handler.py)  
**Priority:** MEDIUM  
**Coverage:** Global, including Ontario  
**Update Frequency:** Annual

#### Verification for Ontario

The existing `analytics_handler.py` in the codebase already integrates Global Forest Watch data. Verify Ontario-specific coverage:

**Available Datasets:**
- Tree cover loss (2001-2023)
- Tree cover gain (2001-2020)
- Forest carbon
- Biomass density

**Usage in Ontario Context:**
```python
# In OntarioDataHandler
async def get_forest_change(self, aoi: dict, start_year: int, end_year: int):
    """Leverage existing GFW analytics for Ontario."""
    # Use existing analytics_handler
    from tools.data_handlers.analytics_handler import AnalyticsHandler
    
    analytics = AnalyticsHandler()
    return await analytics.pull_data(
        aoi=aoi,
        dataset={"source": "gfw", "type": "tree_cover_loss"},
        start_date=f"{start_year}-01-01",
        end_date=f"{end_year}-12-31"
    )
```

---

## Category 3: Water Quality & Aquatic Ecosystems

### 3.1 Provincial Water Quality Monitoring Network (PWQMN)

**Status:** ✅ Production Ready  
**Priority:** CRITICAL  
**Coverage:** Excellent - 400+ monitoring stations  
**Update Frequency:** Monthly sampling, annual data releases  
**License:** Open Government License - Ontario

#### Technical Specifications

**Data Portal:** https://data.ontario.ca/dataset/provincial-stream-water-quality-monitoring-network  
**Format:** CSV files  
**Alternative Access:** DataStream API (see section 3.2)  
**CRS:** WGS84 (EPSG:4326)

#### Data Files Available

**Water Quality Data (by decade):**
- 2019-2021 (most recent): https://files.ontario.ca/moe_mapping/downloads/2Water/PWQMN/PWQMN-2019_2021Mar.csv
- 2010-2018: https://files.ontario.ca/moe_mapping/downloads/2Water/PWQMN/PWQMN-2010_2018.csv
- 2000-2009: https://files.ontario.ca/moe_mapping/downloads/2Water/PWQMN/PWQMN-2000_2009.csv

**Station Locations:**
https://files.ontario.ca/moe_mapping/downloads/2Water/PWQMN/PWQMN_Stations.csv

#### Data Schema

**Station Fields:**
- `STN` - Station ID
- `STN_NAME` - Station name
- `WATER_BODY` - River/stream name
- `LATITUDE` - Decimal degrees
- `LONGITUDE` - Decimal degrees
- `DRAINAGE_AREA_KM2` - Watershed area

**Measurement Fields:**
- `STN` - Station ID
- `SAMPLE_DATE` - Date (YYYY-MM-DD)
- `PARMNAME` - Parameter name
- `VALUE` - Measured value
- `UNIT` - Unit of measurement
- `MDL_FLAG` - Below detection limit flag
- `QA_FLAG` - Quality assurance flag

**Common Parameters:**
- Total Phosphorus (ug/L)
- Total Nitrogen (ug/L)
- Nitrate + Nitrite (mg/L)
- Ammonia (mg/L)
- Chloride (mg/L)
- pH
- Dissolved Oxygen (mg/L)
- Temperature (°C)
- Turbidity (NTU)
- Total Suspended Solids (mg/L)

#### Sample Processing

```python
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# Load station data
stations = pd.read_csv("PWQMN_Stations.csv")
gdf_stations = gpd.GeoDataFrame(
    stations,
    geometry=gpd.points_from_xy(stations.LONGITUDE, stations.LATITUDE),
    crs="EPSG:4326"
)

# Load measurement data
measurements = pd.read_csv("PWQMN-2019_2021Mar.csv")
measurements['SAMPLE_DATE'] = pd.to_datetime(measurements['SAMPLE_DATE'])

# Filter for specific parameter and location
tp_data = measurements[
    (measurements['PARMNAME'] == 'Total Phosphorus') &
    (measurements['WATER_BODY'] == 'Rice Lake')
]

# Calculate summary statistics
tp_stats = tp_data.groupby('STN')['VALUE'].agg(['mean', 'median', 'std', 'count'])
```

#### Integration Strategy

**Database Schema:**
```sql
CREATE TABLE pwqmn_stations (
    station_id VARCHAR(20) PRIMARY KEY,
    station_name VARCHAR(255),
    water_body VARCHAR(255),
    location GEOGRAPHY(POINT, 4326),
    drainage_area_km2 REAL,
    conservation_authority VARCHAR(100),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_pwqmn_location ON pwqmn_stations USING GIST(location);
CREATE INDEX idx_pwqmn_waterbody ON pwqmn_stations(water_body);

CREATE TABLE pwqmn_measurements (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(20) REFERENCES pwqmn_stations(station_id),
    sample_date DATE,
    parameter_name VARCHAR(100),
    value REAL,
    unit VARCHAR(20),
    mdl_flag VARCHAR(10),
    qa_flag VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(station_id, sample_date, parameter_name)
);

CREATE INDEX idx_pwqmn_meas_date ON pwqmn_measurements(sample_date);
CREATE INDEX idx_pwqmn_meas_param ON pwqmn_measurements(parameter_name);
CREATE INDEX idx_pwqmn_meas_station_date ON pwqmn_measurements(station_id, sample_date);
```

**Update Strategy:**
- Download new data files quarterly
- Compare against existing records
- Insert only new measurements
- Flag stations with no recent data

**Attribution:**
> "Water quality data from Ontario's Provincial Water Quality Monitoring Network (PWQMN), operated by the Ontario Ministry of the Environment, Conservation and Parks in partnership with Conservation Authorities."

---

### 3.2 DataStream API

**Status:** ✅ Production Ready  
**Priority:** HIGH  
**Coverage:** Good - Multiple Ontario datasets including PWQMN  
**Update Frequency:** Varies by dataset  
**License:** Varies (typically CC-BY or ODC-BY)

#### Technical Specifications

**API Base URL:** `https://api.datastream.org/v1/odata/v4/`  
**Documentation:** https://github.com/datastreamapp/api-docs  
**Authentication:** API key required (free registration)  
**Registration:** Contact DataStream team  
**Protocol:** OData v4  
**Rate Limits:** 2 requests/second recommended  
**Data Format:** JSON

#### Key Endpoints

**Datasets (Metadata):**
```
GET /Datasets
```

**Locations:**
```
GET /Locations
```

**Observations/Records:**
```
GET /Observations
GET /Records  # Alias for Observations
```

#### OData Query Parameters

- `$filter` - Filter results
- `$select` - Choose fields
- `$expand` - Include related entities
- `$top` - Limit results
- `$skip` - Pagination offset
- `$count` - Include count
- `$orderby` - Sort results

#### Sample Requests

**Get PWQMN Dataset:**
```python
import requests

API_KEY = "your_api_key_here"
headers = {"x-api-key": API_KEY}

# Find PWQMN dataset
url = "https://api.datastream.org/v1/odata/v4/Datasets"
params = {
    "$filter": "contains(DatasetName, 'PWQMN')"
}

response = requests.get(url, headers=headers, params=params)
datasets = response.json()['value']

pwqmn_doi = datasets[0]['DOI']  # e.g., "10.25976/tnw0-3x43"
```

**Get Water Quality Observations:**
```python
# Get observations for specific DOI and parameters
url = "https://api.datastream.org/v1/odata/v4/Observations"
params = {
    "$filter": f"DOI eq '{pwqmn_doi}' and CharacteristicName in ('Total Phosphorus', 'Temperature, water')",
    "$top": 1000
}

response = requests.get(url, headers=headers, params=params)
observations = response.json()['value']

for obs in observations:
    print(f"Location: {obs['LocationId']}")
    print(f"Parameter: {obs['CharacteristicName']}")
    print(f"Value: {obs['ResultValue']} {obs['ResultUnit']}")
    print(f"Date: {obs['ActivityStartDate']}")
```

**Filter by Geographic Region:**
```python
# Using RegionId (if available)
params = {
    "$filter": "RegionId eq 'admin.4.ca.on'"  # Ontario
}
```

#### Sample Response Structure

```json
{
  "@odata.context": "https://api.datastream.org/v1/odata/v4/$metadata#Observations",
  "value": [
    {
      "Id": 12345678,
      "DOI": "10.25976/tnw0-3x43",
      "LocationId": 1001,
      "ActivityType": "Field Msr/Obs",
      "ActivityMediaName": "Surface Water",
      "ActivityStartDate": "2024-06-15",
      "ActivityStartTime": "10:30:00",
      "CharacteristicName": "Total Phosphorus",
      "ResultValue": 25.5,
      "ResultUnit": "ug/L",
      "ResultValueType": "Actual",
      "ResultDetectionCondition": null,
      "ResultStatusID": "Final",
      "ResultComment": null
    }
  ],
  "@odata.nextLink": "https://api.datastream.org/v1/odata/v4/Observations?$skip=1000"
}
```

#### Integration Strategy

**Use Cases:**
1. Access PWQMN data via API instead of CSV downloads
2. Access additional Ontario water quality datasets
3. Standardized data format across multiple sources

**Pagination:**
```python
def fetch_all_observations(doi: str, characteristic: str, api_key: str):
    """Fetch all observations with pagination."""
    headers = {"x-api-key": api_key}
    all_observations = []
    url = "https://api.datastream.org/v1/odata/v4/Observations"
    
    params = {
        "$filter": f"DOI eq '{doi}' and CharacteristicName eq '{characteristic}'",
        "$top": 1000
    }
    
    while url:
        response = requests.get(url, headers=headers, params=params if params else None)
        data = response.json()
        all_observations.extend(data['value'])
        
        # Get next page
        url = data.get('@odata.nextLink')
        params = None  # nextLink includes all params
        
        # Rate limiting
        time.sleep(0.5)
    
    return all_observations
```

**Notable Ontario Datasets in DataStream:**
- PWQMN (DOI: 10.25976/tnw0-3x43)
- Great Lakes Water Quality (DOI: 10.25976/6fgn-0915)
- Various Conservation Authority datasets

**Attribution:**
> "Water quality data from DataStream (datastream.org). Original data source: [Dataset Name]. DOI: [DOI]"

---

### 3.3 Great Lakes Water Quality Data

**Status:** ✅ Available via DataStream  
**Priority:** MEDIUM  
**Coverage:** Ontario portions of Great Lakes  
**Update Frequency:** Annual  
**Source:** Environment and Climate Change Canada

**DataStream DOI:** 10.25976/6fgn-0915

**Access via DataStream API:**
```python
params = {
    "$filter": "DOI eq '10.25976/6fgn-0915'"
}
```

**Parameters Available:**
- Physical: Temperature, pH, conductivity, dissolved oxygen
- Chemical: Nutrients (nitrogen, phosphorus), chlorophyll
- Metals: Mercury, lead, cadmium
- Organic contaminants

**Spatial Coverage:**
- Lake Superior (Ontario waters)
- Lake Huron
- Georgian Bay
- Lake Erie
- Lake Ontario

---

## Category 4: Conservation Areas & Protected Lands

### 4.1 Conservation Ontario Open Data

**Status:** ✅ Production Ready  
**Priority:** CRITICAL  
**Coverage:** Excellent - 36 Conservation Authorities  
**Update Frequency:** Varies by authority  
**License:** Open (varies by CA)

#### Technical Specifications

**Portal:** https://co-opendata-camaps.hub.arcgis.com/  
**Services:** ArcGIS REST, WFS, WMS, GeoJSON  
**CRS:** WGS84 (EPSG:4326) and NAD83 (EPSG:4269)

#### Key Datasets

**1. Conservation Authority Boundaries:**
```
https://co-opendata-camaps.hub.arcgis.com/datasets/conservation-authority-boundaries
```

**REST Service:**
```
https://services1.arcgis.com/afSMGVsC7QJCxUEh/arcgis/rest/services/Conservation_Authority_Boundaries/FeatureServer/0
```

**2. Conservation Areas:**
Multiple datasets per Conservation Authority

**3. PWQMN Sites:**
```
https://co-opendata-camaps.hub.arcgis.com/datasets/pwqmn-sites
```

#### Sample Request (ArcGIS REST)

```python
import requests

# Query Conservation Authority boundaries
url = "https://services1.arcgis.com/afSMGVsC7QJCxUEh/arcgis/rest/services/Conservation_Authority_Boundaries/FeatureServer/0/query"

params = {
    "where": "1=1",  # All features
    "outFields": "*",
    "f": "geojson"
}

response = requests.get(url, params=params)
conservation_authorities = response.json()

for feature in conservation_authorities['features']:
    props = feature['properties']
    print(f"CA: {props.get('NAME')}")
    print(f"Area: {props.get('AREA_KM2')} km²")
```

#### Sample Request (WFS)

```python
from owslib.wfs import WebFeatureService

wfs_url = "https://services1.arcgis.com/afSMGVsC7QJCxUEh/arcgis/services/Conservation_Authority_Boundaries/WFSServer"

wfs = WebFeatureService(wfs_url, version='2.0.0')

# List available layers
print(list(wfs.contents))

# Get features
response = wfs.getfeature(
    typename='Conservation_Authority_Boundaries',
    outputFormat='application/json'
)

import json
data = json.loads(response.read())
```

#### Integration Strategy

**Database Schema:**
```sql
CREATE TABLE conservation_authorities (
    id SERIAL PRIMARY KEY,
    ca_name VARCHAR(255) UNIQUE,
    full_name VARCHAR(255),
    area_km2 REAL,
    website VARCHAR(255),
    geometry GEOGRAPHY(MULTIPOLYGON, 4326),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ca_geometry ON conservation_authorities USING GIST(geometry);
CREATE INDEX idx_ca_name ON conservation_authorities(ca_name);

CREATE TABLE conservation_areas (
    id SERIAL PRIMARY KEY,
    ca_id INTEGER REFERENCES conservation_authorities(id),
    area_name VARCHAR(255),
    area_type VARCHAR(100),
    public_access BOOLEAN,
    geometry GEOGRAPHY(MULTIPOLYGON, 4326),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ca_areas_geometry ON conservation_areas USING GIST(geometry);
CREATE INDEX idx_ca_areas_ca ON conservation_areas(ca_id);
```

**Update Strategy:**
- Initial bulk load of all CA boundaries
- Monthly refresh to catch boundary updates
- Cache conservation areas by CA

**Attribution:**
> "Conservation Authority data from Conservation Ontario Open Data Portal (conservationontario.ca). Individual Conservation Authorities maintain their respective datasets."

---

### 4.2 Ontario Provincial Parks

**Status:** ✅ Already Ingested  
**Priority:** MAINTENANCE  
**Coverage:** Complete - 340+ parks  
**Source:** Ontario GeoHub

**Existing Implementation:**
The Ontario Nature Watch platform already has provincial parks ingested. Verify data currency and refresh if needed.

**Refresh Source:**
https://geohub.lio.gov.on.ca/datasets/ontario-parks

---

### 4.3 Ontario GeoHub - Conservation Authority Administrative Areas

**Status:** ✅ Production Ready  
**Priority:** HIGH  
**Coverage:** Official CA boundaries  
**Source:** Land Information Ontario

**Dataset:** https://geohub.lio.gov.on.ca/datasets/lio::conservation-authority-administrative-area/

**WFS Service:**
```
https://ws.lioservices.lrc.gov.on.ca/arcgis2/services/LIO_OPEN_DATA/LIO_Open_Data/MapServer/WFSServer
```

**Layer:** Conservation Authority Administrative Area

**Use Case:**
- Authoritative CA boundaries (vs Conservation Ontario portal)
- Use for legal/regulatory queries
- Cross-reference with Conservation Ontario data

---

## Category 5: Indigenous Territories

### 5.1 Historic Treaties - Statistics Canada / Federal Open Data

**Status:** ✅ Production Ready  
**Priority:** CRITICAL (Williams Treaty area)  
**Coverage:** All historic treaties including Williams Treaties  
**Update Frequency:** As treaties are signed/updated  
**License:** Open Government License - Canada

#### Technical Specifications

**Data Portal:** https://open.canada.ca/data/en/dataset/f281b150-0645-48e4-9c30-01f55f93f78e  
**Format:** Shapefile, GeoJSON, KML, WFS  
**CRS:** NAD83 / Lambert Conformal Conic (EPSG:3347) and WGS84 (EPSG:4326)

#### WFS Service

**Base URL:**
```
https://geo.statcan.gc.ca/geoserver/census-recensement/wfs
```

**Layer Name:** `census-recensement:lhp_000b21a_e`

**Sample WFS Request:**
```python
from owslib.wfs import WebFeatureService

wfs_url = "https://geo.statcan.gc.ca/geoserver/census-recensement/wfs"
wfs = WebFeatureService(wfs_url, version='2.0.0')

# Get features with filter for Williams Treaties
from owslib.fes import PropertyIsLike
from owslib.etree import etree

# Query for Williams Treaties
filter_xml = """
<Filter>
    <PropertyIsLike wildCard="*" singleChar="." escapeChar="!">
        <PropertyName>treaty_name</PropertyName>
        <Literal>*Williams*</Literal>
    </PropertyIsLike>
</Filter>
"""

response = wfs.getfeature(
    typename='census-recensement:lhp_000b21a_e',
    filter=filter_xml,
    outputFormat='application/json'
)
```

#### Direct Download

**Shapefile:** Available from Open Canada portal  
**URL:** https://open.canada.ca/data/en/dataset/f281b150-0645-48e4-9c30-01f55f93f78e

**File Contents:**
- Treaty boundaries (polygons)
- Treaty metadata (name, date, parties)

#### Williams Treaties Specific

**Seven First Nations:**
1. Curve Lake First Nation
2. Hiawatha First Nation
3. Alderville First Nation
4. Scugog Island First Nation
5. Mississaugas of Rice Lake
6. Chippewas of Georgina Island
7. Chippewas of Beausoleil

**Territory:**
- ~52,000 km²
- Northern shore of Lake Ontario to Lake Nipissing
- Overlaps with previous treaties

#### Integration Strategy

**Database Schema:**
```sql
CREATE TABLE historic_treaties (
    id SERIAL PRIMARY KEY,
    treaty_name VARCHAR(255),
    treaty_number VARCHAR(50),
    signing_date DATE,
    treaty_type VARCHAR(100),
    geometry GEOGRAPHY(MULTIPOLYGON, 4326),
    area_km2 REAL,
    signatory_nations TEXT[],
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_treaties_geometry ON historic_treaties USING GIST(geometry);
CREATE INDEX idx_treaties_name ON historic_treaties(treaty_name);

-- Williams Treaty First Nations
CREATE TABLE williams_treaty_nations (
    id SERIAL PRIMARY KEY,
    nation_name VARCHAR(255),
    common_name VARCHAR(255),
    website VARCHAR(255),
    treaty_id INTEGER REFERENCES historic_treaties(id),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Manual Geocoding Validation:**
The platform already has manual geocoding for 7 Williams Treaty communities. Cross-reference with treaty boundaries to ensure accuracy.

**Attribution:**
> "Treaty boundaries from Crown-Indigenous Relations and Northern Affairs Canada. Treaty data should not be used for legal purposes. For definitive boundaries, contact the First Nations directly."

---

### 5.2 First Nations Reserve Boundaries

**Status:** ✅ Available  
**Priority:** MEDIUM  
**Source:** Statistics Canada / Indigenous Services Canada

**Dataset:** https://www.aadnc-aandc.gc.ca/eng/1100100032364/1100100032365

**Access:**
- Statistics Canada census boundaries
- Indigenous Services Canada website
- Manual geocoding as needed

---

## Category 6: Climate & Weather

### 6.1 Environment and Climate Change Canada

**Status:** ✅ Available via Multiple APIs  
**Priority:** MEDIUM  
**Coverage:** Excellent - Weather stations across Ontario

#### Historical Climate Data

**Portal:** https://climate.weather.gc.ca/  
**Bulk Data:** ftp://client_climate@ftp.tor.ec.gc.ca/  
**Format:** CSV  
**License:** Open Government License - Canada

#### Current Weather - MSC Datamart

**GeoMet-Weather:** https://eccc-msc.github.io/open-data/msc-geomet/readme_en/  
**OGC Services:** WMS, WCS, WFS  
**Real-time Data:** Yes

#### Integration Strategy

**Use Cases:**
- Historical temperature trends
- Precipitation data
- Climate normals
- Current weather conditions

**Recommended Approach:**
- Use historical climate data for trends
- Integrate current weather via GeoMet-Weather
- Link weather stations to monitoring locations

---

## Recommended Architecture

### OntarioDataHandler Class Structure

```python
from typing import Any, Dict, List, Optional
from datetime import datetime
from tools.data_handlers.base import DataSourceHandler, DataPullResult

class OntarioDataHandler(DataSourceHandler):
    """
    Unified data handler for Ontario-specific environmental data sources.
    Integrates biodiversity, water quality, forest, and conservation data.
    """
    
    def __init__(self):
        self.inat_client = INaturalistClient()
        self.ebird_client = EBirdClient()
        self.gbif_client = GBIFClient()
        self.pwqmn_client = PWQMNClient()
        self.datastream_client = DataStreamClient()
        self.ca_client = ConservationAuthorityClient()
    
    def can_handle(self, dataset: Any) -> bool:
        """Check if dataset is Ontario-specific."""
        ontario_sources = [
            "iNaturalist",
            "eBird",
            "GBIF",
            "PWQMN",
            "DataStream",
            "ConservationOntario",
            "OntarioFRI",
            "OntarioParks"
        ]
        return (
            isinstance(dataset, dict) and
            dataset.get("source") in ontario_sources
        )
    
    async def pull_data(
        self,
        aoi: dict,
        dataset: dict,
        start_date: str,
        end_date: str
    ) -> DataPullResult:
        """Pull data from Ontario sources based on dataset type."""
        
        source = dataset.get("source")
        data_type = dataset.get("type")
        
        if source == "iNaturalist":
            return await self._pull_inat_data(aoi, start_date, end_date)
        elif source == "eBird":
            return await self._pull_ebird_data(aoi, start_date, end_date)
        elif source == "GBIF":
            return await self._pull_gbif_data(aoi, start_date, end_date, dataset)
        elif source == "PWQMN":
            return await self._pull_pwqmn_data(aoi, start_date, end_date)
        elif source == "DataStream":
            return await self._pull_datastream_data(aoi, start_date, end_date, dataset)
        elif source == "ConservationOntario":
            return await self._pull_ca_data(aoi)
        else:
            raise ValueError(f"Unsupported Ontario data source: {source}")
    
    async def _pull_inat_data(
        self, aoi: dict, start_date: str, end_date: str
    ) -> DataPullResult:
        """Pull iNaturalist observations for AOI."""
        # Implementation details...
        pass
    
    async def _pull_ebird_data(
        self, aoi: dict, start_date: str, end_date: str
    ) -> DataPullResult:
        """Pull eBird observations for AOI."""
        # Implementation details...
        pass
    
    # Additional methods for each data source...
```

### Database Schema - Complete DDL

```sql
-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- ==========================================
-- BIODIVERSITY OBSERVATIONS
-- ==========================================

-- iNaturalist Observations
CREATE TABLE inat_observations (
    id BIGINT PRIMARY KEY,
    taxon_id INTEGER,
    scientific_name VARCHAR(255),
    common_name VARCHAR(255),
    taxonomy_rank VARCHAR(50),
    iconic_taxon VARCHAR(50),
    observation_date DATE,
    observation_datetime TIMESTAMP WITH TIME ZONE,
    location GEOGRAPHY(POINT, 4326),
    place_name VARCHAR(255),
    positional_accuracy REAL,
    quality_grade VARCHAR(50),
    license VARCHAR(50),
    observer VARCHAR(100),
    photo_urls TEXT[],
    identifications_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    url VARCHAR(500),
    data_source VARCHAR(50) DEFAULT 'iNaturalist',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT check_quality_grade CHECK (quality_grade IN ('research', 'needs_id', 'casual'))
);

CREATE INDEX idx_inat_location ON inat_observations USING GIST(location);
CREATE INDEX idx_inat_date ON inat_observations(observation_date);
CREATE INDEX idx_inat_taxon ON inat_observations(taxon_id);
CREATE INDEX idx_inat_quality ON inat_observations(quality_grade);
CREATE INDEX idx_inat_scientific_name ON inat_observations(scientific_name);

-- eBird Observations
CREATE TABLE ebird_observations (
    submission_id VARCHAR(50) PRIMARY KEY,
    species_code VARCHAR(10),
    common_name VARCHAR(255),
    scientific_name VARCHAR(255),
    observation_datetime TIMESTAMP WITH TIME ZONE,
    location GEOGRAPHY(POINT, 4326),
    location_name VARCHAR(255),
    location_id VARCHAR(50),
    count INTEGER,
    obs_valid BOOLEAN DEFAULT true,
    obs_reviewed BOOLEAN DEFAULT false,
    url VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ebird_location ON ebird_observations USING GIST(location);
CREATE INDEX idx_ebird_datetime ON ebird_observations(observation_datetime);
CREATE INDEX idx_ebird_species ON ebird_observations(species_code);
CREATE INDEX idx_ebird_scientific_name ON ebird_observations(scientific_name);

-- GBIF Occurrences
CREATE TABLE gbif_occurrences (
    gbif_key BIGINT PRIMARY KEY,
    dataset_key VARCHAR(50),
    scientific_name VARCHAR(255),
    kingdom VARCHAR(100),
    phylum VARCHAR(100),
    class VARCHAR(100),
    family VARCHAR(100),
    genus VARCHAR(100),
    species VARCHAR(255),
    location GEOGRAPHY(POINT, 4326),
    coordinate_uncertainty REAL,
    event_date DATE,
    year INTEGER,
    month INTEGER,
    day INTEGER,
    basis_of_record VARCHAR(50),
    institution_code VARCHAR(100),
    collection_code VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_gbif_location ON gbif_occurrences USING GIST(location);
CREATE INDEX idx_gbif_date ON gbif_occurrences(event_date);
CREATE INDEX idx_gbif_species ON gbif_occurrences(scientific_name);
CREATE INDEX idx_gbif_year ON gbif_occurrences(year);

-- ==========================================
-- WATER QUALITY
-- ==========================================

-- PWQMN Stations
CREATE TABLE pwqmn_stations (
    station_id VARCHAR(20) PRIMARY KEY,
    station_name VARCHAR(255),
    water_body VARCHAR(255),
    location GEOGRAPHY(POINT, 4326),
    drainage_area_km2 REAL,
    conservation_authority VARCHAR(100),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_pwqmn_location ON pwqmn_stations USING GIST(location);
CREATE INDEX idx_pwqmn_waterbody ON pwqmn_stations(water_body);
CREATE INDEX idx_pwqmn_ca ON pwqmn_stations(conservation_authority);

-- PWQMN Measurements
CREATE TABLE pwqmn_measurements (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(20) REFERENCES pwqmn_stations(station_id),
    sample_date DATE,
    parameter_name VARCHAR(100),
    value REAL,
    unit VARCHAR(20),
    mdl_flag VARCHAR(10),
    qa_flag VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(station_id, sample_date, parameter_name)
);

CREATE INDEX idx_pwqmn_meas_date ON pwqmn_measurements(sample_date);
CREATE INDEX idx_pwqmn_meas_param ON pwqmn_measurements(parameter_name);
CREATE INDEX idx_pwqmn_meas_station_date ON pwqmn_measurements(station_id, sample_date);

-- ==========================================
-- FOREST RESOURCES
-- ==========================================

-- FRI Stands
CREATE TABLE fri_stands (
    id SERIAL PRIMARY KEY,
    fmu_name VARCHAR(100),
    polytype VARCHAR(50),
    species_composition VARCHAR(100),
    age INTEGER,
    height_class VARCHAR(10),
    density INTEGER,
    year_origin INTEGER,
    development_stage VARCHAR(50),
    geometry GEOGRAPHY(MULTIPOLYGON, 4326),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_fri_geometry ON fri_stands USING GIST(geometry);
CREATE INDEX idx_fri_fmu ON fri_stands(fmu_name);
CREATE INDEX idx_fri_species ON fri_stands(species_composition);

-- FRI Species Composition (parsed)
CREATE TABLE fri_species (
    stand_id INTEGER REFERENCES fri_stands(id),
    species_code VARCHAR(2),
    percentage INTEGER,
    PRIMARY KEY (stand_id, species_code)
);

CREATE INDEX idx_fri_species_code ON fri_species(species_code);

-- Species Codes Lookup
CREATE TABLE species_codes (
    code VARCHAR(2) PRIMARY KEY,
    scientific_name VARCHAR(255),
    common_name VARCHAR(255),
    species_type VARCHAR(50)  -- tree, shrub, etc.
);

-- ==========================================
-- CONSERVATION AREAS
-- ==========================================

-- Conservation Authorities
CREATE TABLE conservation_authorities (
    id SERIAL PRIMARY KEY,
    ca_name VARCHAR(255) UNIQUE,
    full_name VARCHAR(255),
    area_km2 REAL,
    website VARCHAR(255),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    geometry GEOGRAPHY(MULTIPOLYGON, 4326),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ca_geometry ON conservation_authorities USING GIST(geometry);
CREATE INDEX idx_ca_name ON conservation_authorities(ca_name);

-- Conservation Areas
CREATE TABLE conservation_areas (
    id SERIAL PRIMARY KEY,
    ca_id INTEGER REFERENCES conservation_authorities(id),
    area_name VARCHAR(255),
    area_type VARCHAR(100),
    public_access BOOLEAN,
    facilities TEXT[],
    geometry GEOGRAPHY(MULTIPOLYGON, 4326),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ca_areas_geometry ON conservation_areas USING GIST(geometry);
CREATE INDEX idx_ca_areas_ca ON conservation_areas(ca_id);

-- ==========================================
-- INDIGENOUS TERRITORIES
-- ==========================================

-- Historic Treaties
CREATE TABLE historic_treaties (
    id SERIAL PRIMARY KEY,
    treaty_name VARCHAR(255),
    treaty_number VARCHAR(50),
    signing_date DATE,
    treaty_type VARCHAR(100),
    geometry GEOGRAPHY(MULTIPOLYGON, 4326),
    area_km2 REAL,
    signatory_nations TEXT[],
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_treaties_geometry ON historic_treaties USING GIST(geometry);
CREATE INDEX idx_treaties_name ON historic_treaties(treaty_name);

-- Williams Treaty First Nations
CREATE TABLE williams_treaty_nations (
    id SERIAL PRIMARY KEY,
    nation_name VARCHAR(255),
    common_name VARCHAR(255),
    website VARCHAR(255),
    contact_email VARCHAR(255),
    treaty_id INTEGER REFERENCES historic_treaties(id),
    location GEOGRAPHY(POINT, 4326),  -- Community center point
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_wt_nations_location ON williams_treaty_nations USING GIST(location);

-- ==========================================
-- SPATIAL INDEXES AND MATERIALIZED VIEWS
-- ==========================================

-- Biodiversity Observations (Unified View)
CREATE MATERIALIZED VIEW biodiversity_observations AS
SELECT
    id::TEXT AS observation_id,
    'iNaturalist' AS source,
    scientific_name,
    common_name,
    observation_date AS obs_date,
    observation_datetime AS obs_datetime,
    location,
    place_name,
    quality_grade,
    url
FROM inat_observations
WHERE quality_grade IN ('research', 'needs_id')

UNION ALL

SELECT
    submission_id AS observation_id,
    'eBird' AS source,
    scientific_name,
    common_name,
    observation_datetime::DATE AS obs_date,
    observation_datetime AS obs_datetime,
    location,
    location_name AS place_name,
    'research' AS quality_grade,
    url
FROM ebird_observations
WHERE obs_valid = true

UNION ALL

SELECT
    gbif_key::TEXT AS observation_id,
    'GBIF' AS source,
    scientific_name,
    species AS common_name,
    event_date AS obs_date,
    NULL AS obs_datetime,
    location,
    NULL AS place_name,
    'research' AS quality_grade,
    NULL AS url
FROM gbif_occurrences;

CREATE INDEX idx_bio_obs_location ON biodiversity_observations USING GIST(location);
CREATE INDEX idx_bio_obs_date ON biodiversity_observations(obs_date);
CREATE INDEX idx_bio_obs_source ON biodiversity_observations(source);

-- Water Quality Summary (by Station and Parameter)
CREATE MATERIALIZED VIEW water_quality_summary AS
SELECT
    s.station_id,
    s.station_name,
    s.water_body,
    s.location,
    s.conservation_authority,
    m.parameter_name,
    COUNT(*) AS measurement_count,
    MIN(m.sample_date) AS first_measurement,
    MAX(m.sample_date) AS last_measurement,
    AVG(m.value) AS mean_value,
    STDDEV(m.value) AS std_value,
    MIN(m.value) AS min_value,
    MAX(m.value) AS max_value,
    m.unit
FROM pwqmn_stations s
JOIN pwqmn_measurements m ON s.station_id = m.station_id
GROUP BY
    s.station_id,
    s.station_name,
    s.water_body,
    s.location,
    s.conservation_authority,
    m.parameter_name,
    m.unit;

CREATE INDEX idx_wq_summary_location ON water_quality_summary USING GIST(location);
CREATE INDEX idx_wq_summary_param ON water_quality_summary(parameter_name);
CREATE INDEX idx_wq_summary_waterbody ON water_quality_summary(water_body);

-- Refresh materialized views (run periodically)
-- REFRESH MATERIALIZED VIEW CONCURRENTLY biodiversity_observations;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY water_quality_summary;
```

---

## Implementation Roadmap

### Phase 1: Immediate (Weeks 1-2)

**Priority Integrations:**
- [ ] Implement `INaturalistClient` class
- [ ] Implement `EBirdClient` class (register for API key)
- [ ] Create `OntarioDataHandler` skeleton
- [ ] Set up database schemas (biodiversity tables)
- [ ] Implement basic caching for iNaturalist data
- [ ] Test iNaturalist integration with Algonquin Park queries

**Deliverables:**
- Working biodiversity observations endpoint
- Sample queries return real Ontario data
- Basic error handling and rate limiting

### Phase 2: Short-term (Weeks 3-4)

**Water Quality & Conservation:**
- [ ] Download PWQMN CSV files
- [ ] Ingest PWQMN stations and measurements
- [ ] Implement `PWQMNClient` class
- [ ] Register for DataStream API key
- [ ] Implement `DataStreamClient` class
- [ ] Ingest Conservation Authority boundaries
- [ ] Implement `ConservationAuthorityClient` class

**Deliverables:**
- Water quality queries working for Ontario lakes
- Conservation Authority spatial queries
- Integrated water quality trends

### Phase 3: Medium-term (Weeks 5-8)

**Indigenous Territories & Forest:**
- [ ] Download Historic Treaties boundaries (WFS)
- [ ] Ingest Williams Treaty data
- [ ] Validate manual geocoding for 7 communities
- [ ] Download FRI data for key forest management units
- [ ] Implement FRI species composition parser
- [ ] Integrate GBIF for supplementary biodiversity

**Deliverables:**
- Treaty boundary queries working
- Forest cover queries for Kawartha region
- Comprehensive biodiversity from 3 sources

### Phase 4: Polish & Optimization (Weeks 9-12)

**Performance & UX:**
- [ ] Implement spatial caching strategy
- [ ] Optimize database queries with proper indexes
- [ ] Create materialized views for common queries
- [ ] Implement data quality checks
- [ ] Add data freshness indicators
- [ ] Comprehensive error handling
- [ ] Attribution and licensing display
- [ ] Performance testing and optimization

**Deliverables:**
- Sub-second response times for common queries
- Proper attribution for all data sources
- Comprehensive test coverage

---

## Data Quality & Maintenance

### Data Freshness Indicators

```python
async def check_data_freshness(source: str) -> dict:
    """Check how current the cached data is."""
    freshness = {}
    
    if source == "iNaturalist":
        # Check last observation date in cache
        last_obs = await db.execute(
            "SELECT MAX(observation_date) FROM inat_observations"
        )
        freshness["last_observation"] = last_obs
        freshness["recommended_update"] = "daily"
    
    elif source == "PWQMN":
        last_measurement = await db.execute(
            "SELECT MAX(sample_date) FROM pwqmn_measurements"
        )
        freshness["last_measurement"] = last_measurement
        freshness["recommended_update"] = "quarterly"
    
    # Calculate staleness
    from datetime import datetime, timedelta
    today = datetime.now().date()
    last_date = freshness.get("last_observation") or freshness.get("last_measurement")
    
    if last_date:
        staleness_days = (today - last_date).days
        freshness["staleness_days"] = staleness_days
        
        if staleness_days > 7:
            freshness["status"] = "stale"
        elif staleness_days > 1:
            freshness["status"] = "aging"
        else:
            freshness["status"] = "fresh"
    
    return freshness
```

### Update Strategies

**Real-time Sources (iNaturalist, eBird):**
- Update frequency: Daily
- Method: Incremental updates for active areas
- Trigger: Scheduled job + on-demand for specific queries

**Periodic Sources (PWQMN, GBIF):**
- Update frequency: Quarterly
- Method: Bulk download and diff against existing
- Trigger: Scheduled job when new data releases announced

**Static Sources (FRI, Treaties):**
- Update frequency: Annually or as updated
- Method: Full refresh
- Trigger: Manual trigger when new versions available

### Data Quality Checks

```python
async def validate_observation(obs: dict) -> tuple[bool, list]:
    """Validate a biodiversity observation."""
    issues = []
    
    # Check required fields
    required = ['scientific_name', 'observation_date', 'location']
    for field in required:
        if not obs.get(field):
            issues.append(f"Missing required field: {field}")
    
    # Validate coordinates in Ontario bounds
    if obs.get('location'):
        lon, lat = obs['location']['coordinates']
        # Ontario approximate bounds
        if not (-95 < lon < -74 and 41 < lat < 57):
            issues.append("Location outside Ontario bounds")
    
    # Validate date range
    if obs.get('observation_date'):
        obs_date = datetime.fromisoformat(obs['observation_date'])
        if obs_date.year < 1800 or obs_date > datetime.now():
            issues.append("Invalid observation date")
    
    # Check taxonomy
    if obs.get('scientific_name'):
        if len(obs['scientific_name']) < 3:
            issues.append("Suspiciously short scientific name")
    
    return len(issues) == 0, issues
```

---

## Known Limitations & Gaps

### Data Gaps

**Biodiversity:**
- ✅ Birds: Excellent coverage (eBird)
- ✅ General: Good coverage (iNaturalist, GBIF)
- ⚠️ Invertebrates: Limited (Ontario Butterfly Atlas - no API found)
- ⚠️ Mammals: Limited citizen science data
- ❌ Reptiles/Amphibians: No dedicated Ontario API

**Forest:**
- ✅ FRI: Managed forest zone only
- ❌ Far North: Limited coverage
- ❌ Southern Ontario: Outside FMU coverage
- ❌ Real-time disturbance: No API (fires, pests)

**Water Quality:**
- ✅ Streams/Rivers: Excellent (PWQMN)
- ✅ Great Lakes: Good (ECCC via DataStream)
- ⚠️ Small Lakes: Limited coverage
- ❌ Groundwater: Not available via API

**Conservation:**
- ✅ Conservation Authorities: Good
- ✅ Provincial Parks: Complete
- ⚠️ Private conservation: Variable
- ❌ Municipal parks: Not standardized

### Technical Limitations

**Rate Limits:**
- iNaturalist: 100 req/min (recommended 60)
- eBird: Not specified, conservative approach
- GBIF: 100,000 records per search API call
- DataStream: 2 req/sec recommended

**Data Volume:**
- GBIF Ontario: 100,000+ records (download API required for bulk)
- FRI: Several GB per forest management unit
- PWQMN: 50+ years of data (manageable)

**Spatial Accuracy:**
- iNaturalist: Varies (10m to 1km+), some obscured
- eBird: Location-level, not exact coordinates
- PWQMN: Station level (accurate)
- FRI: Stand level (100m resolution typical)

---

## Attribution Requirements

### Per-Source Attribution

**iNaturalist:**
```
Observation data provided by iNaturalist (www.inaturalist.org). 
Individual observations are licensed under CC0, CC-BY, or CC-BY-NC 
as specified by observers.
```

**eBird:**
```
Bird observation data provided by eBird: An online database of bird 
distribution and abundance [web application]. eBird, Cornell Lab of 
Ornithology, Ithaca, New York. Available: http://www.ebird.org. 
(Accessed: [Date]).
```

**GBIF:**
```
Species occurrence data from GBIF.org. [Include specific dataset DOIs]
```

**PWQMN:**
```
Water quality data from Ontario's Provincial Water Quality Monitoring 
Network (PWQMN), operated by the Ontario Ministry of the Environment, 
Conservation and Parks in partnership with Conservation Authorities.
```

**DataStream:**
```
Water quality data from DataStream (datastream.org). Original data 
source: [Dataset Name]. DOI: [DOI].
```

**Conservation Ontario:**
```
Conservation Authority data from Conservation Ontario Open Data Portal 
(conservationontario.ca). Individual Conservation Authorities maintain 
their respective datasets.
```

**Ontario FRI:**
```
Forest Resources Inventory data © King's Printer for Ontario, [Year]. 
Accessed from Ontario GeoHub.
```

**Historic Treaties:**
```
Treaty boundaries from Crown-Indigenous Relations and Northern Affairs 
Canada. Treaty data should not be used for legal purposes. For definitive 
boundaries, contact the First Nations directly.
```

---

## API Keys & Registration

### Required Registrations

**eBird API:**
- URL: https://ebird.org/api/keygen
- Process: Free, instant
- Required: eBird account

**DataStream API:**
- Contact: DataStream team via website
- Process: Email request
- Required: Describe use case

**GBIF Download API (optional):**
- URL: https://www.gbif.org/user/profile
- Process: Free registration
- Required: Only for large downloads

### No Registration Required

- iNaturalist API (read-only)
- GBIF Search API (up to 100K records)
- Conservation Ontario Open Data
- Ontario GeoHub / Land Information Ontario
- PWQMN (CSV downloads)
- Historic Treaties (federal open data)

---

## Testing Strategy

### Unit Tests

```python
# tests/test_ontario_handler.py

import pytest
from tools.data_handlers.ontario_handler import OntarioDataHandler

@pytest.fixture
def ontario_handler():
    return OntarioDataHandler()

@pytest.fixture
def algonquin_aoi():
    """Algonquin Park bounding box."""
    return {
        "type": "Polygon",
        "coordinates": [[
            [-78.5, 45.5],
            [-78.5, 46.0],
            [-77.5, 46.0],
            [-77.5, 45.5],
            [-78.5, 45.5]
        ]]
    }

async def test_can_handle_inat(ontario_handler):
    dataset = {"source": "iNaturalist", "type": "observations"}
    assert ontario_handler.can_handle(dataset) == True

async def test_can_handle_invalid(ontario_handler):
    dataset = {"source": "Unknown", "type": "observations"}
    assert ontario_handler.can_handle(dataset) == False

async def test_pull_inat_data(ontario_handler, algonquin_aoi):
    """Test pulling iNaturalist data for Algonquin Park."""
    dataset = {"source": "iNaturalist", "type": "observations"}
    result = await ontario_handler.pull_data(
        aoi=algonquin_aoi,
        dataset=dataset,
        start_date="2024-06-01",
        end_date="2024-06-30"
    )
    
    assert result.success == True
    assert len(result.data) > 0
    assert all('scientific_name' in obs for obs in result.data)

async def test_pull_ebird_data(ontario_handler, algonquin_aoi):
    """Test pulling eBird data for Algonquin Park."""
    dataset = {"source": "eBird", "type": "observations"}
    result = await ontario_handler.pull_data(
        aoi=algonquin_aoi,
        dataset=dataset,
        start_date="2024-06-01",
        end_date="2024-06-30"
    )
    
    assert result.success == True
    assert len(result.data) > 0
    assert all('common_name' in obs for obs in result.data)

# Additional tests for each data source...
```

### Integration Tests

```python
# tests/integration/test_ontario_queries.py

import pytest
from tools.ontario.ontario_query_tool import ontario_query

@pytest.mark.integration
async def test_species_query_algonquin():
    """Test: What species are found in Algonquin Park?"""
    result = await ontario_query(
        query="What species have been observed in Algonquin Park in 2024?",
        area="Algonquin Provincial Park"
    )
    
    assert result['success'] == True
    assert len(result['species']) > 0
    assert 'sources' in result
    assert 'iNaturalist' in result['sources'] or 'eBird' in result['sources']

@pytest.mark.integration
async def test_water_quality_rice_lake():
    """Test: What's the water quality in Rice Lake?"""
    result = await ontario_query(
        query="What is the water quality in Rice Lake?",
        area="Rice Lake"
    )
    
    assert result['success'] == True
    assert 'parameters' in result
    assert any('Phosphorus' in p for p in result['parameters'])
    assert 'PWQMN' in result['sources']

@pytest.mark.integration  
async def test_conservation_authority():
    """Test: Which conservation authority manages this area?"""
    result = await ontario_query(
        query="Which conservation authority manages the Kawartha Lakes region?",
        area="Kawartha Lakes"
    )
    
    assert result['success'] == True
    assert 'conservation_authority' in result
    assert 'Kawartha' in result['conservation_authority']
```

---

## Sample Queries & Expected Outputs

### Query 1: Bird Observations in Algonquin Park

**User Query:**
> "What birds have been seen in Algonquin Park this month?"

**Expected Sources:**
- eBird (primary)
- iNaturalist (supplementary)

**Expected Output:**
```json
{
  "query": "Birds observed in Algonquin Provincial Park (November 2025)",
  "sources": ["eBird", "iNaturalist"],
  "total_observations": 156,
  "unique_species": 42,
  "top_species": [
    {
      "common_name": "Black-capped Chickadee",
      "scientific_name": "Poecile atricapillus",
      "observation_count": 23,
      "most_recent": "2025-11-15"
    },
    {
      "common_name": "Blue Jay",
      "scientific_name": "Cyanocitta cristata",
      "observation_count": 18,
      "most_recent": "2025-11-14"
    }
  ],
  "attribution": "Bird data from eBird and iNaturalist"
}
```

### Query 2: Water Quality in Rice Lake

**User Query:**
> "How is the water quality in Rice Lake?"

**Expected Sources:**
- PWQMN (primary)
- DataStream (supplementary)

**Expected Output:**
```json
{
  "query": "Water quality in Rice Lake",
  "sources": ["PWQMN"],
  "monitoring_stations": 3,
  "parameters": {
    "total_phosphorus": {
      "recent_value": 18.5,
      "unit": "ug/L",
      "sample_date": "2024-09-15",
      "status": "Mesotrophic",
      "trend": "stable"
    },
    "dissolved_oxygen": {
      "recent_value": 8.2,
      "unit": "mg/L",
      "sample_date": "2024-09-15",
      "status": "Good"
    }
  },
  "summary": "Water quality in Rice Lake is moderate with mesotrophic conditions.",
  "attribution": "Data from Ontario PWQMN"
}
```

### Query 3: Species at Risk near Curve Lake First Nation

**User Query:**
> "Show me species at risk near Curve Lake First Nation"

**Expected Sources:**
- iNaturalist (quality_grade: research)
- GBIF
- Cross-reference with COSEWIC/SARA lists

**Expected Output:**
```json
{
  "query": "Species at risk near Curve Lake First Nation",
  "territory": "Williams Treaties Territory",
  "sources": ["iNaturalist", "GBIF"],
  "species_at_risk": [
    {
      "common_name": "Blanding's Turtle",
      "scientific_name": "Emydoidea blandingii",
      "status": "Endangered (COSEWIC)",
      "last_observed": "2024-07-20",
      "location": "Within 10km of Curve Lake",
      "source": "iNaturalist"
    }
  ],
  "attribution": "Species data from iNaturalist and GBIF. Status from COSEWIC.",
  "territory_note": "Located within Williams Treaties territory (Curve Lake First Nation)"
}
```

### Query 4: Forest Cover in Kawarthas

**User Query:**
> "What's the forest cover in the Kawarthas?"

**Expected Sources:**
- FRI (where available)
- Global Forest Watch
- Ontario Land Cover

**Expected Output:**
```json
{
  "query": "Forest cover in Kawartha region",
  "sources": ["Ontario FRI", "Global Forest Watch"],
  "area_km2": 2500,
  "forest_cover_percent": 62,
  "dominant_species": [
    {"species": "Sugar Maple", "code": "Ms", "percent": 35},
    {"species": "Eastern White Pine", "code": "Pw", "percent": 25},
    {"species": "White Birch", "code": "Bw", "percent": 15}
  ],
  "forest_health": "Generally healthy with some areas of historical disturbance",
  "attribution": "Forest data from Ontario FRI"
}
```

---

## Contact & Support

**For API Issues:**
- iNaturalist: https://forum.inaturalist.org/
- eBird: ebird@cornell.edu
- GBIF: helpdesk@gbif.org
- DataStream: info@datastreamproject.org
- Ontario Open Data: opendata@ontario.ca

**For Data Quality Issues:**
- Report to source platform
- Flag in Ontario Nature Watch UI
- Log in system for review

---

## Appendix A: Species Code Lookup Tables

### Ontario FRI Species Codes

Common species codes used in Forest Resources Inventory:

| Code | Scientific Name | Common Name |
|------|----------------|-------------|
| Ms | Acer saccharum | Sugar Maple |
| Mh | Acer rubrum | Red Maple |
| Or | Fraxinus americana | White Ash |
| Be | Fagus grandifolia | American Beech |
| Pw | Pinus strobus | Eastern White Pine |
| Pr | Pinus resinosa | Red Pine |
| Sw | Picea glauca | White Spruce |
| Sb | Picea mariana | Black Spruce |
| Bf | Abies balsamea | Balsam Fir |
| Ce | Thuja occidentalis | Eastern White Cedar |
| Bw | Betula papyrifera | White Birch |
| Po | Populus tremuloides | Trembling Aspen |
| Pb | Populus balsamifera | Balsam Poplar |
| He | Tsuga canadensis | Eastern Hemlock |

**Full List:** Available in Ontario FRI documentation

---

## Appendix B: Water Quality Parameters

### PWQMN Standard Parameters

| Parameter | Unit | Typical Range | Significance |
|-----------|------|---------------|--------------|
| Total Phosphorus | ug/L | 5-50 | Nutrient loading, algae growth |
| Total Nitrogen | ug/L | 100-1000 | Nutrient loading |
| Chloride | mg/L | 1-250 | Road salt, pollution indicator |
| pH | - | 6.5-8.5 | Acidity/alkalinity |
| Dissolved Oxygen | mg/L | 5-14 | Fish habitat quality |
| Temperature | °C | 0-30 | Seasonal variation |
| Turbidity | NTU | 0-25 | Water clarity |
| TSS | mg/L | 0-100 | Suspended solids |

---

## Document Version History

**Version 1.0** - November 16, 2025
- Initial comprehensive guide
- 12 data sources documented
- Complete technical specifications
- Database schemas provided
- Integration roadmap defined

---

**End of Guide**

For questions or updates to this guide, contact the Ontario Nature Watch development team.
