# Ontario Data Integration - Quick Reference

**For:** Ontario Nature Watch Developers  
**Version:** 1.0  
**Date:** November 16, 2025

---

## 🚀 Quick Start Checklist

### Immediate Actions (Day 1)

1. **Register for API Keys**
   - [ ] eBird: https://ebird.org/api/keygen (instant, free)
   - [ ] DataStream: Contact team (email, 1-2 days)
   - [ ] iNaturalist: Optional, not required

2. **Set Up Environment**
   ```bash
   pip install aiohttp pandas geopandas requests --break-system-packages
   pip install psycopg2-binary sqlalchemy --break-system-packages
   ```

3. **Create Configuration**
   ```python
   # config.py
   EBIRD_API_KEY = "your_key_here"
   DATASTREAM_API_KEY = "your_key_here"
   ```

### Week 1 Goals

- [ ] Test iNaturalist API (no key needed)
- [ ] Test eBird API with Ontario region
- [ ] Set up PostgreSQL with PostGIS
- [ ] Create basic database tables
- [ ] Implement simple caching

---

## 📊 Data Source Priority Matrix

| Source | Priority | Difficulty | Setup Time | Impact |
|--------|----------|-----------|------------|--------|
| **iNaturalist** | ⭐⭐⭐ CRITICAL | Easy | 1 hour | High |
| **eBird** | ⭐⭐⭐ CRITICAL | Easy | 1 hour | High |
| **PWQMN** | ⭐⭐⭐ CRITICAL | Medium | 4 hours | High |
| **Conservation ON** | ⭐⭐⭐ CRITICAL | Medium | 4 hours | High |
| **DataStream** | ⭐⭐ HIGH | Medium | 2 hours | Medium |
| **GBIF** | ⭐⭐ HIGH | Medium | 2 hours | Medium |
| **Historic Treaties** | ⭐⭐ HIGH | Easy | 2 hours | Medium |
| **FRI** | ⭐ MEDIUM | Hard | 8+ hours | Medium |

---

## 🔗 Essential API Endpoints

### iNaturalist (No Auth Required)

```python
# Base URL
BASE = "https://api.inaturalist.org/v1"

# Get observations in Ontario
GET /observations?place_id=6942&quality_grade=research

# Search by bounding box
GET /observations?swlat=44.0&swlng=-78.5&nelat=46.0&nelng=-77.5
```

**Ontario Place ID:** `6942`  
**Rate Limit:** 100 req/min (recommend 60)  
**Max Results:** 200 per page

### eBird (Requires API Key)

```python
# Base URL
BASE = "https://api.ebird.org/v2"

# Recent observations in Ontario
GET /data/obs/CA-ON/recent?back=30
Headers: {"x-ebirdapitoken": "YOUR_KEY"}

# Specific region
GET /data/obs/CA-ON-PE/recent  # Peterborough
```

**Ontario Region Code:** `CA-ON`  
**Max Back Days:** 30  
**Max Results:** 10,000

### PWQMN (Open Data - No Auth)

```python
# Download URLs
STATIONS = "https://files.ontario.ca/moe_mapping/downloads/2Water/PWQMN/PWQMN_Stations.csv"
DATA_2019_2021 = "https://files.ontario.ca/moe_mapping/downloads/2Water/PWQMN/PWQMN-2019_2021Mar.csv"

# Use pandas
import pandas as pd
stations = pd.read_csv(STATIONS)
measurements = pd.read_csv(DATA_2019_2021)
```

### DataStream (Requires API Key)

```python
# Base URL
BASE = "https://api.datastream.org/v1/odata/v4"

# Get observations for PWQMN
GET /Observations?$filter=DOI eq '10.25976/tnw0-3x43'
Headers: {"x-api-key": "YOUR_KEY"}

# Filter by parameter
$filter=DOI eq '10.25976/tnw0-3x43' and CharacteristicName eq 'Total Phosphorus'
```

**PWQMN DOI:** `10.25976/tnw0-3x43`  
**Rate Limit:** 2 req/sec  
**Max Results:** Unlimited (paginated)

---

## 💾 Essential Database Schemas

### Biodiversity (iNaturalist + eBird + GBIF)

```sql
-- Quick setup
CREATE TABLE observations (
    id TEXT PRIMARY KEY,
    source VARCHAR(50),
    scientific_name VARCHAR(255),
    common_name VARCHAR(255),
    obs_date DATE,
    location GEOGRAPHY(POINT, 4326),
    quality_grade VARCHAR(50),
    data JSONB  -- Store full record
);

CREATE INDEX idx_obs_location ON observations USING GIST(location);
CREATE INDEX idx_obs_date ON observations(obs_date);
CREATE INDEX idx_obs_source ON observations(source);
```

### Water Quality (PWQMN/DataStream)

```sql
-- Quick setup
CREATE TABLE water_stations (
    station_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(255),
    water_body VARCHAR(255),
    location GEOGRAPHY(POINT, 4326)
);

CREATE TABLE water_measurements (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(20),
    sample_date DATE,
    parameter VARCHAR(100),
    value REAL,
    unit VARCHAR(20)
);

CREATE INDEX idx_wm_station_date ON water_measurements(station_id, sample_date);
CREATE INDEX idx_wm_param ON water_measurements(parameter);
```

---

## 🔍 Common Query Patterns

### 1. Birds in Algonquin Park (Last 30 Days)

```python
# eBird
url = "https://api.ebird.org/v2/data/obs/CA-ON/recent"
params = {"back": 30}
headers = {"x-ebirdapitoken": EBIRD_KEY}

response = requests.get(url, headers=headers, params=params)
observations = response.json()

# Filter for Algonquin area (approx bounds)
algonquin = [
    obs for obs in observations
    if 45.0 < obs['lat'] < 46.0 and -78.5 < obs['lng'] < -77.5
]
```

### 2. Species in Area

```python
# iNaturalist
url = "https://api.inaturalist.org/v1/observations"
params = {
    "swlat": 44.0,
    "swlng": -78.5,
    "nelat": 44.5,
    "nelng": -78.0,
    "quality_grade": "research",
    "per_page": 200
}

response = requests.get(url, params=params)
observations = response.json()['results']

# Extract unique species
species = set(obs['taxon']['name'] for obs in observations)
```

### 3. Water Quality for Lake

```python
# PWQMN
import pandas as pd

stations = pd.read_csv(STATIONS_URL)
measurements = pd.read_csv(MEASUREMENTS_URL)

# Filter for Rice Lake
rice_lake_stations = stations[stations['WATER_BODY'] == 'Rice Lake']
station_ids = rice_lake_stations['STN'].tolist()

# Get measurements
rice_lake_data = measurements[
    measurements['STN'].isin(station_ids) &
    (measurements['PARMNAME'] == 'Total Phosphorus')
]

# Recent average
recent = rice_lake_data[rice_lake_data['SAMPLE_DATE'] >= '2024-01-01']
avg_tp = recent['VALUE'].mean()
```

### 4. Conservation Authority for Location

```python
# Using Conservation Ontario WFS
from owslib.wfs import WebFeatureService

wfs_url = "https://services1.arcgis.com/.../WFSServer"
wfs = WebFeatureService(wfs_url, version='2.0.0')

# Point in polygon query
# (Implementation depends on WFS capabilities)
```

---

## ⚡ Performance Tips

### Caching Strategy

```python
# Simple file cache
import json
from pathlib import Path
from datetime import datetime, timedelta

def cache_get(key: str, ttl_hours: int = 24):
    cache_file = Path(f"cache/{key}.json")
    
    if cache_file.exists():
        mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - mtime < timedelta(hours=ttl_hours):
            with open(cache_file) as f:
                return json.load(f)
    
    return None

def cache_set(key: str, data):
    Path("cache").mkdir(exist_ok=True)
    with open(f"cache/{key}.json", 'w') as f:
        json.dump(data, f)
```

### Rate Limiting

```python
import asyncio
from datetime import datetime

class RateLimiter:
    def __init__(self, requests_per_minute: int):
        self.rate = requests_per_minute
        self.last_request = datetime.now()
    
    async def wait(self):
        now = datetime.now()
        elapsed = (now - self.last_request).total_seconds()
        min_interval = 60.0 / self.rate
        
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        
        self.last_request = datetime.now()

# Usage
limiter = RateLimiter(60)
await limiter.wait()
# Make request
```

### Spatial Indexing

```sql
-- Create spatial index
CREATE INDEX idx_location ON observations USING GIST(location);

-- Use with queries
SELECT * FROM observations
WHERE ST_DWithin(
    location::geography,
    ST_MakePoint(-78.3, 44.3)::geography,
    10000  -- 10km
);

-- Bounding box query (faster)
SELECT * FROM observations
WHERE location && ST_MakeEnvelope(-78.5, 44.0, -78.0, 44.5, 4326);
```

---

## 🐛 Common Issues & Solutions

### Issue 1: iNaturalist Rate Limiting

**Symptom:** HTTP 429 errors  
**Solution:**
```python
# Implement backoff
import time

def fetch_with_retry(url, params, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, params=params)
        
        if response.status_code == 429:
            wait_time = (2 ** attempt) * 5  # Exponential backoff
            time.sleep(wait_time)
            continue
        
        return response
    
    raise Exception("Max retries exceeded")
```

### Issue 2: Large PWQMN Files

**Symptom:** Memory errors loading CSV  
**Solution:**
```python
# Use chunked reading
import pandas as pd

chunks = []
for chunk in pd.read_csv(url, chunksize=10000):
    # Filter in chunks
    filtered = chunk[chunk['WATER_BODY'] == 'Rice Lake']
    chunks.append(filtered)

data = pd.concat(chunks)
```

### Issue 3: Coordinate System Mismatches

**Symptom:** Points appear in wrong locations  
**Solution:**
```python
import geopandas as gpd

# Ensure correct CRS
gdf = gpd.GeoDataFrame(data, geometry=geometry, crs="EPSG:4326")

# Transform if needed
gdf_transformed = gdf.to_crs("EPSG:3161")  # Ontario MNR Lambert
```

---

## 📝 Testing Checklist

### Unit Tests

```python
# test_ontario_handler.py
import pytest

@pytest.mark.asyncio
async def test_inat_fetch():
    """Test iNaturalist data fetch."""
    client = INaturalistClient()
    
    bounds = (44.0, -78.5, 44.5, -78.0)  # Peterborough area
    
    obs = await client.get_observations(
        bounds=bounds,
        start_date="2024-06-01",
        end_date="2024-06-30"
    )
    
    assert len(obs) > 0
    assert all('taxon' in o for o in obs)

@pytest.mark.asyncio
async def test_ebird_fetch():
    """Test eBird data fetch."""
    client = EBirdClient(api_key=EBIRD_KEY)
    
    obs = await client.get_recent_observations(back_days=7)
    
    assert len(obs) > 0
    assert all('comName' in o for o in obs)
```

### Integration Tests

```python
@pytest.mark.integration
async def test_end_to_end_biodiversity():
    """Test complete biodiversity query."""
    handler = OntarioDataHandler(config)
    
    aoi = {
        "type": "Polygon",
        "coordinates": [[...]]  # Algonquin Park
    }
    
    dataset = {"source": "iNaturalist"}
    
    result = await handler.pull_data(
        aoi=aoi,
        dataset=dataset,
        start_date="2024-06-01",
        end_date="2024-06-30"
    )
    
    assert result.success
    assert len(result.data) > 0
    
    # Verify all observations in AOI
    for obs in result.data:
        coords = obs['location']['coordinates']
        # Check coords in bounds...
```

---

## 🎯 Success Metrics

### Week 1 Targets

- [ ] Successfully fetch 100+ iNaturalist observations
- [ ] Successfully fetch 50+ eBird observations
- [ ] Query responds in < 2 seconds (cached)
- [ ] Database has 1000+ observations

### Month 1 Targets

- [ ] 10,000+ biodiversity observations cached
- [ ] 5+ water quality stations with recent data
- [ ] 36 Conservation Authority boundaries ingested
- [ ] Williams Treaty boundaries loaded
- [ ] Sub-second response for common queries

### Production Ready

- [ ] 100,000+ observations across all sources
- [ ] Daily automated updates
- [ ] 99% uptime for queries
- [ ] Comprehensive error handling
- [ ] Full attribution system

---

## 📚 Essential Reading

### API Documentation

1. **iNaturalist API v1**  
   https://api.inaturalist.org/v1/docs/
   
2. **eBird API 2.0**  
   https://documenter.getpostman.com/view/664302/S1ENwy59
   
3. **GBIF API**  
   https://techdocs.gbif.org/en/openapi/
   
4. **DataStream API**  
   https://github.com/datastreamapp/api-docs

### Data Portals

1. **Ontario Data Catalogue**  
   https://data.ontario.ca/
   
2. **Conservation Ontario Open Data**  
   https://co-opendata-camaps.hub.arcgis.com/
   
3. **Ontario GeoHub**  
   https://geohub.lio.gov.on.ca/

---

## 🆘 Getting Help

### API Issues

- **iNaturalist:** https://forum.inaturalist.org/
- **eBird:** ebird@cornell.edu
- **GBIF:** helpdesk@gbif.org
- **DataStream:** info@datastreamproject.org
- **Ontario Open Data:** opendata@ontario.ca

### Development Support

- Review full integration guide: `ONTARIO_DATA_INTEGRATION_GUIDE.md`
- Check code template: `ontario_handler.py`
- Test with sample data before production

---

**Quick Reference Version 1.0 | November 16, 2025**
