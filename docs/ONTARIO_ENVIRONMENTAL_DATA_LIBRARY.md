# Using the Ontario Environmental Data Library in ONW

This document explains how to integrate and use the `ontario-environmental-data` library within Ontario Nature Watch.

## Overview

The `ontario-environmental-data` library extracts reusable data access components that were originally embedded in ONW's handlers. This provides:

- **Shared codebase** with the williams-treaties project
- **Cleaner separation** between data access and LLM integration
- **Easier testing** of data clients independently
- **Community resource** for other Ontario environmental projects

## Library Location

**Repository:** https://github.com/robertsoden/ontario-environmental-data
**Development:** `/Users/robertsoden/ontario-environmental-data`

## Architecture

### Before (Monolithic)

```
ONW Handler
├── API client code
├── Data parsing logic
├── Model definitions
├── Database storage
└── LLM integration
```

### After (Library-Based)

```
ontario-environmental-data library
├── API clients
├── Data models (Pydantic)
├── Processing utilities
└── Constants

ONW Handler (thin wrapper)
├── Uses library clients
├── Stores in database
└── Integrates with LLM
```

## Integration Strategy

### Phase 1: Add as Dependency ✅ (Current)

Keep current ONW handlers while library is developed:

```toml
# pyproject.toml
dependencies = [
    "ontario-environmental-data @ git+https://github.com/robertsoden/ontario-environmental-data.git",
]
```

### Phase 2: Gradual Migration (Future)

Refactor handlers to use library:

**Before:**
```python
# src/tools/data_handlers/williams_treaty_handler.py
class WilliamsTreatyDataHandler:
    async def _pull_water_advisories(self, aoi, start_date, end_date):
        # Custom CSV parsing logic here
        # Database queries here
        # Transform to DataPullResult
```

**After:**
```python
# src/tools/data_handlers/williams_treaty_handler.py
from ontario_data.sources.isc import WaterAdvisoriesClient
from ontario_data.models import WaterAdvisory

class WilliamsTreatyDataHandler:
    def __init__(self):
        self.water_client = WaterAdvisoriesClient()

    async def _pull_water_advisories(self, aoi, start_date, end_date):
        # Use library client to fetch data
        advisories = await self.water_client.fetch_from_database(
            geometry=aoi["geometry"],
            start_date=start_date,
            end_date=end_date
        )

        # Transform to ONW format
        return self._to_data_pull_result(advisories)
```

## Usage Examples

### Using Water Advisories Client

```python
from ontario_data.sources.isc import WaterAdvisoriesClient
from ontario_data.models import WaterAdvisory

async def fetch_advisories_for_area(csv_path: str, aoi_bounds: tuple):
    """Fetch water advisories for a specific area."""

    async with WaterAdvisoriesClient() as client:
        # Load all advisories
        advisories = await client.fetch(csv_path=csv_path, province="ON")

        # Filter by bounds (manual for now, spatial utils coming)
        filtered = [
            adv for adv in advisories
            if (aoi_bounds[0] <= adv.latitude <= aoi_bounds[2] and
                aoi_bounds[1] <= adv.longitude <= aoi_bounds[3])
        ]

        # Store in ONW database
        await store_advisories(filtered)

        return filtered
```

### Using Data Models for Validation

```python
from ontario_data.models import WaterAdvisory

# Validate incoming data
try:
    advisory = WaterAdvisory(
        advisory_id="ON-2024-001",
        community_name="Example First Nation",
        region="Ontario",
        advisory_type="Boil Water Advisory",
        advisory_date="2024-01-15",
        latitude=44.5,
        longitude=-79.5,
    )
    # Data is validated by Pydantic
except ValidationError as e:
    # Handle validation errors
    print(f"Invalid data: {e}")
```

### Using Constants

```python
from ontario_data.constants import (
    WILLIAMS_TREATY_FIRST_NATIONS,
    ISC_WATER_ADVISORIES_URL,
)

# Check if community is in Williams Treaty
if community_name in WILLIAMS_TREATY_FIRST_NATIONS:
    # Special handling for Williams Treaty territories
    pass

# Use standard URLs
print(f"Data source: {ISC_WATER_ADVISORIES_URL}")
```

## Benefits for ONW

### 1. Cleaner Code

Handlers become thin wrappers that focus on:
- Database integration
- LLM agent interface
- ONW-specific logic

Library handles:
- Data fetching
- Parsing and validation
- Data models

### 2. Easier Testing

Test data clients independently:

```python
# Test library client (no database needed)
from ontario_data.sources.isc import WaterAdvisoriesClient

async def test_water_advisories_client():
    client = WaterAdvisoriesClient()
    advisories = await client.fetch(csv_data=SAMPLE_CSV)
    assert len(advisories) > 0
    assert all(isinstance(adv, WaterAdvisory) for adv in advisories)
```

### 3. Shared Improvements

Improvements to data clients benefit both:
- ONW (LLM-powered queries)
- williams-treaties (web mapping)
- Other Ontario projects

### 4. Community Contribution

Others can:
- Add new data sources
- Improve existing clients
- Report issues
- Contribute documentation

## Migration Path

### Current State (No Changes Required)

ONW continues to work with embedded handlers:
- `williams_treaty_handler.py` - Database-backed queries
- `ontario_handler.py` - iNaturalist, eBird APIs
- All existing functionality preserved

### Future Refactoring (Optional)

When ready, refactor to use library:

1. **Add Library Dependency**
   ```bash
   pip install ontario-environmental-data
   ```

2. **Update Imports**
   ```python
   from ontario_data.sources.isc import WaterAdvisoriesClient
   from ontario_data.models import WaterAdvisory
   ```

3. **Refactor Handlers**
   - Use library clients for data fetching
   - Keep ONW-specific database logic
   - Maintain LLM integration

4. **Remove Duplicate Code**
   - Remove embedded parsing logic
   - Use library models
   - Use library constants

## What Stays in ONW

These components remain ONW-specific:

### Database Handlers
```python
# src/tools/data_handlers/williams_treaty_handler.py
class WilliamsTreatyDataHandler:
    async def pull_data(...) -> DataPullResult:
        # ONW-specific method signature
        # Database queries for LLM agent
        # DataPullResult format
```

### LLM Integration
```python
# src/tools/ontario/get_ontario_statistics.py
@tool("get_ontario_statistics")
async def get_ontario_statistics(...):
    # LangChain tool definitions
    # Agent state management
    # Tool message formatting
```

### Database Schema
```sql
-- db/migrations/002_williams_treaty_data.sql
-- PostGIS tables for LLM queries
-- Spatial indexes
-- Views and triggers
```

## What Moves to Library

These components are extracted to library:

### API Clients
```python
# ontario_data/sources/isc.py
class WaterAdvisoriesClient(BaseClient):
    async def fetch(csv_path, province):
        # CSV parsing
        # Data fetching
        # Returns WaterAdvisory objects
```

### Data Models
```python
# ontario_data/models/water_advisory.py
class WaterAdvisory(BaseModel):
    # Pydantic models
    # Validation
    # GeoJSON export
```

### Constants
```python
# ontario_data/constants/first_nations.py
WILLIAMS_TREATY_FIRST_NATIONS = [...]
```

## Example: Refactored Water Advisory Handler

**Before (Embedded):**

```python
class WilliamsTreatyDataHandler:
    async def _pull_water_advisories(self, aoi, start_date, end_date):
        # 100+ lines of CSV parsing
        # Date parsing logic
        # Geometry creation
        # Database queries
        # Transform to DataPullResult
```

**After (Library-Based):**

```python
from ontario_data.sources.isc import WaterAdvisoriesClient
from ontario_data.models import WaterAdvisory

class WilliamsTreatyDataHandler:
    def __init__(self):
        self.water_client = WaterAdvisoriesClient()

    async def _pull_water_advisories(self, aoi, start_date, end_date):
        # Query database for pre-loaded advisories
        advisories = await self._query_water_advisories_db(
            aoi, start_date, end_date
        )

        # Transform to ONW format (10 lines instead of 100)
        return DataPullResult(
            success=True,
            data=[self._to_dict(adv) for adv in advisories],
            message=f"Found {len(advisories)} water advisories",
            data_points_count=len(advisories),
        )
```

## Testing Strategy

### Test Library Independently

```bash
cd ontario-environmental-data
pytest tests/
```

### Test ONW Integration

```bash
cd onw
pytest tests/tools/test_williams_treaty_handler.py
```

### Integration Tests

```python
# tests/integration/test_library_integration.py
async def test_water_advisories_end_to_end():
    # 1. Fetch using library
    client = WaterAdvisoriesClient()
    advisories = await client.fetch(csv_path="test_data.csv")

    # 2. Store in ONW database
    handler = WilliamsTreatyDataHandler()
    await handler.store_advisories(advisories)

    # 3. Query via handler
    result = await handler.pull_data(
        dataset={"source": "WaterAdvisories"},
        aoi=test_aoi
    )

    # 4. Verify results
    assert result.success
    assert len(result.data) > 0
```

## Timeline

### Phase 1: Library Creation (Current)
✅ Create `ontario-environmental-data` repository
✅ Extract data models
✅ Extract API clients
✅ Add documentation and examples

### Phase 2: Parallel Development
- Develop library independently
- Keep ONW handlers as-is
- Add library as optional dependency

### Phase 3: Gradual Migration
- Refactor ONW handlers to use library
- Remove duplicate code
- Maintain backward compatibility

### Phase 4: Full Integration
- Library handles all data access
- ONW handlers are thin wrappers
- Shared improvements benefit both projects

## Questions & Answers

**Q: Do we need to change ONW immediately?**
A: No, ONW continues to work with current handlers. Library integration is optional and gradual.

**Q: Will this break existing functionality?**
A: No, changes are additive. Current code remains functional.

**Q: When should we migrate?**
A: After library is stable and well-tested. Migration can be done handler-by-handler.

**Q: What if the library doesn't have a feature we need?**
A: Keep ONW-specific code in ONW. Library is for shared components only.

## See Also

- **Library Repository:** https://github.com/robertsoden/ontario-environmental-data
- **Library Documentation:** https://github.com/robertsoden/ontario-environmental-data#readme
- **Williams Treaties Integration:** https://github.com/robertsoden/williams-treaties
- **ONW Handlers:** `src/tools/data_handlers/`

## Contact

For questions about library integration:
- Open an issue in the `ontario-environmental-data` repository
- Discuss in the ONW project discussions

---

**Document Version:** 1.1
**Last Updated:** November 2024
**Status:** Library published at https://github.com/robertsoden/ontario-environmental-data
