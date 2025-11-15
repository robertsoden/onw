# Williams Treaty Territory - Adaptation Guide

## Quick Reference for Geographic Adaptation

This guide outlines the specific steps and files needed to adapt the Global Nature Watch system for Williams Treaty Territory.

---

## 1. CORE ADAPTATION POINTS

### A. Geographic Data Integration

**Option 1: Custom Areas Table (Simplest)**
- Store Williams Treaty Territory boundary as GeoJSON in `custom_areas` table
- No code changes required
- Immediate availability through existing AOI picker
- User-specific or global (based on user_id)

**Option 2: Dedicated Territory Table (More Integrated)**
- Create new `geometries_williams_treaty` table
- Update `/src/utils/geocoding_helpers.py`:
  ```python
  WILLIAMS_TREATY_TABLE = "geometries_williams_treaty"
  
  SOURCE_ID_MAPPING = {
      # ... existing entries
      "williams_treaty": {
          "table": WILLIAMS_TREATY_TABLE,
          "id_column": "territory_id"
      }
  }
  ```
- Create ingestion script: `/src/ingest/ingest_williams_treaty.py`
- Add migration in `/db/alembic/versions/`

### B. Regional Configuration

**File:** `/src/user_profile_configs/countries.py`

Add entry:
```python
COUNTRIES = {
    # ... existing entries
    "WTT": "Williams Treaty Territory",  # Custom code
    # ... rest
}
```

Or create new file `/src/user_profile_configs/regions.py`:
```python
REGIONS = {
    "wtc": "Williams Treaty Territory",
}
```

### C. Dataset Coverage Configuration

**File:** `/src/tools/analytics_datasets.yml`

For each dataset, update `geographic_coverage`:
```yaml
- dataset_id: 0
  dataset_name: Global All Ecosystem Disturbance Alerts (DIST-ALERT)
  geographic_coverage: "Global, including Ontario (Williams Treaty Territory)"
  # ... rest of config
```

Update `prompt_instructions` with territory-specific guidance:
```yaml
  prompt_instructions: >
    For Williams Treaty Territory queries, focus on alerts in Ontario region...
```

---

## 2. FILE MODIFICATION CHECKLIST

### Critical Files (Required Changes)

- [ ] `/src/tools/analytics_datasets.yml`
  - Add territory-specific geographic coverage statements
  - Verify all dataset endpoints serve Ontario/Canadian region
  - Add territory-specific prompt instructions

- [ ] `/src/user_profile_configs/countries.py` OR new `regions.py`
  - Add Williams Treaty Territory as selectable region
  - Use for user profile preferences

- [ ] `/src/ingest/` (if creating dedicated table)
  - Create `ingest_williams_treaty.py`
  - Define territory boundary source
  - Set up ingestion pipeline

### Important Files (Optional Enhancement)

- [ ] `/src/utils/geocoding_helpers.py`
  - Add territory source mapping if using dedicated table
  - Add subtype mappings for territory hierarchies

- [ ] `/db/alembic/`
  - Create migration for new geometry table (if needed)
  - Add spatial indexes for territory table

- [ ] `.env` / `.env.local`
  - Territory-specific API endpoints if applicable
  - WRI API key with Ontario coverage

- [ ] `/tests/` or `/experiments/`
  - Add test cases for territory AOI selection
  - Create evaluation dataset for territory queries

---

## 3. DATA WORKFLOW FOR WILLIAMS TREATY TERRITORY

### Step 1: Define Territory Boundary
```python
# Williams Treaty Territory boundary (GeoJSON format)
wtt_geometry = {
    "type": "Polygon",
    "coordinates": [[[...boundary coordinates...]]]
}

# Store in custom_areas table
INSERT INTO custom_areas (
    id, user_id, name, description, geometries
) VALUES (
    'wtt-001', 'admin-user', 'Williams Treaty Territory', 
    'First Nations territory in Ontario', 
    ['{"type":"Polygon","coordinates":[...]}'::json]
)
```

### Step 2: AOI Selection Flow
```
User Query: "Show deforestation in Williams Treaty Territory"
    ↓
pick_aoi tool searches for "Williams Treaty Territory"
    ↓
Finds match in custom_areas or geometries_williams_treaty
    ↓
Returns geometry and metadata (name, source, src_id)
    ↓
Agent stores in state: aoi = {
        "name": "Williams Treaty Territory",
        "src_id": "wtt-001",
        "source": "custom" or "williams_treaty",
        "geometry": {...}
    }
```

### Step 3: Dataset Selection
pick_dataset tool evaluates available datasets for Ontario region
- GFW datasets all have global coverage including Ontario
- Can add territory-specific context layers

### Step 4: Data Retrieval
pull_data tool queries GFW Analytics API with Ontario boundaries
- Analytics API accepts geometry parameters
- Returns data aggregated to territory extent

---

## 4. SAMPLE IMPLEMENTATION

### Minimal Implementation (15 minutes)

1. **Add to countries.py:**
```python
"WTT": "Williams Treaty Territory",
```

2. **Update analytics_datasets.yml** (one entry example):
```yaml
- dataset_id: 0
  dataset_name: Global All Ecosystem Disturbance Alerts (DIST-ALERT)
  geographic_coverage: "Global, including Williams Treaty Territory (Ontario, Canada)"
  prompt_instructions: >
    For Williams Treaty Territory, this dataset monitors vegetation disturbances
    in the Ontario region where the territory is located. Use this dataset to
    show recent vegetation changes and disturbance drivers.
```

3. **Add custom area via SQL:**
```sql
-- After identifying WTT boundary coordinates
INSERT INTO custom_areas (id, name, geometries, user_id)
VALUES ('wtt-primary', 'Williams Treaty Territory', 
        '["{\\"type\\":\\"Polygon\\",\\"coordinates\\":[...]}"]', 
        'admin-user-id');
```

### Full Implementation (2-3 hours)

1. Create `/src/ingest/ingest_williams_treaty.py`
2. Update `/src/utils/geocoding_helpers.py` with territory mapping
3. Add database migration for territory table
4. Update all dataset configuration files
5. Create test cases in `/experiments/e2e_test_dataset.csv`
6. Add evaluation dataset for territory queries

---

## 5. TESTING TERRITORY INTEGRATION

### Unit Tests
Create `/tests/tools/test_pick_aoi_williams_treaty.py`:
```python
async def test_pick_aoi_williams_treaty():
    # Test AOI selection for Williams Treaty Territory
    result = await pick_aoi(
        question="Show deforestation in Williams Treaty Territory",
        place="Williams Treaty Territory"
    )
    assert result.aoi["name"] == "Williams Treaty Territory"
    assert result.aoi["source"] in ["custom", "williams_treaty"]
```

### Integration Tests
Add to `/experiments/e2e_test_dataset.csv`:
```csv
Show forest loss in Williams Treaty Territory over 2020-2024,
wtt-001,Williams Treaty Territory,,custom-area,custom,4,
Tree cover loss,,2020-01-01,2024-12-31,
[expected answer about Ontario forests],
g1,high,new
```

### Manual Testing
```bash
# Terminal 1: Start API
make api

# Terminal 2: Test query
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Show me deforestation alerts in Williams Treaty Territory for 2024"}],
    "thread_id": "test-wtt-001"
  }'
```

---

## 6. CONFIGURATION BY DATA SOURCE

### Global Forest Watch Datasets
**Status:** Ready to use, global coverage includes Ontario
**Change Needed:** Geographic coverage statement update only

Example GFW API call for Williams Treaty Territory:
```
GET /v0/land_change/tree_cover_loss/analytics
?geostore_id={wtt_geostore_id}
&start_date=2020-01-01
&end_date=2024-12-31
```

### GADM Hierarchy
**Status:** Canada/Ontario already in system
**Usage:** Can select parent regions (Canada, Ontario) and show WTT as subset
**Change Needed:** Optional - add WTT as ADM level below Ontario

### Custom/Indigenous Lands Integration
**Status:** LandMark database may contain WTT areas
**Check:** Search geometries_landmark for existing WTT records
```sql
SELECT * FROM geometries_landmark 
WHERE name ILIKE '%Williams%' OR name ILIKE '%Anishinaabe%';
```

---

## 7. USER EXPERIENCE IMPROVEMENTS

### Territory-Specific Prompts
Update agent system prompts to mention Williams Treaty Territory:
```python
# In /src/agents/agents.py
system_prompt = """
...
You can help users analyze geospatial data for any location, including:
- Countries and regions
- Protected areas and key biodiversity areas
- Indigenous territories (e.g., Williams Treaty Territory)
- User-defined custom areas
...
"""
```

### Help Text Updates
Update `/src/tools/get_capabilities.py`:
```python
def _load_datasets_info() -> str:
    """Load dataset information from the datasets configuration."""
    # ... existing code
    
    return f"""
    ...
    SUPPORTED AREAS OF INTEREST:
    - Administrative boundaries: Countries, states, provinces, districts
    - Conservation areas: Key Biodiversity Areas (KBA), Protected Areas
    - Indigenous territories: Including Williams Treaty Territory
    ...
    """
```

---

## 8. DEPLOYMENT CHECKLIST

Before going to production:

- [ ] Territory boundary geometry verified for accuracy
- [ ] All dataset configurations updated with coverage statements
- [ ] AOI picker returns Williams Treaty Territory in search results
- [ ] Test queries for common analysis types work
- [ ] Users can select territory in profiles
- [ ] API endpoints serve data for territory bounds
- [ ] Documentation updated (README, docs/AGENT_ARCHITECTURE.md)
- [ ] Langfuse tracking includes territory in metadata
- [ ] Performance tested with territory geometry queries
- [ ] Database indexes optimized for territory queries

---

## 9. PERFORMANCE CONSIDERATIONS

### Geometry Query Optimization

Large territory geometries may slow fuzzy text search:
```sql
-- Add text search index if not present
CREATE INDEX idx_geometries_name_gin ON geometries_williams_treaty 
USING GIN (name gin_trgm_ops);

-- Add spatial index for efficient geometry operations
CREATE INDEX idx_geometries_geom_gist ON geometries_williams_treaty 
USING GIST (geometry);
```

### Caching Strategy
- Cache territory geometry after first query (LRU cache)
- Store geostore_id from GFW API for quick lookups
- Cache dataset availability checks per territory

---

## 10. FUTURE ENHANCEMENTS

### Phase 2: Territory-Specific Analytics
- Custom indicators for WTT-specific environmental metrics
- Cultural heritage site data integration
- Community-contributed environmental observations

### Phase 3: Relationship Management
- Show relationship between WTT and larger GADM units (Ontario, Canada)
- Comparative analysis (WTT vs Ontario, vs Canada)
- Multi-territory queries and aggregations

### Phase 4: Customization
- Territory-specific language support (including Indigenous languages if applicable)
- Custom chart types for specific environmental concerns
- Integration with community environmental monitoring platforms

---

## Summary

Williams Treaty Territory can be integrated into Global Nature Watch through:

1. **Minimal Effort:** Add to custom areas (15 min, configuration only)
2. **Standard Implementation:** Create dedicated table with proper ingestion (2-3 hours)
3. **Full Integration:** Include in all documentation, testing, and UI flows (1-2 days)

All approaches maintain backward compatibility and don't impact global functionality. The system's modular architecture supports territory-specific customization without code changes to core agent logic.

