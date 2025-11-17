# Ontario Data Handler - Fallback System

**Date:** November 16, 2025
**Version:** 1.1
**Feature:** Automatic Fallback to Global Datasets

---

## Overview

The Ontario Data Handler now includes an **intelligent fallback system** that automatically uses global datasets (Global Forest Watch Analytics) when Ontario-specific data is not available or returns insufficient results.

This ensures users always get environmental data for Ontario areas, even when specialized Ontario datasets haven't been fully implemented yet.

---

## How It Works

### Fallback Hierarchy

```
1. TRY Ontario-Specific Data
   ↓ (if no data or not implemented)
2. FALLBACK to Global Datasets (GFW Analytics)
   ↓ (if still no data)
3. RETURN error message
```

### Automatic Fallback Triggers

The system falls back to global datasets when:

1. **Ontario source not implemented yet**
   - Example: User requests GBIF data (Phase 2 feature)
   - System tries Ontario handler → Falls back to GFW

2. **Ontario source returns no data**
   - Example: iNaturalist has no observations for the date range
   - System tries iNaturalist → Falls back to GFW forest data

3. **API key not configured**
   - Example: eBird key not set in `.env`
   - System tries eBird → Falls back to GFW

4. **Request for non-biodiversity metrics**
   - Example: User requests forest cover or tree loss
   - System immediately uses GFW (Ontario doesn't have forest datasets yet)

---

## What Datasets Are Available

### Ontario-Specific (Phase 1) ✅

| Data Type | Source | API Key | Status |
|-----------|--------|---------|--------|
| Biodiversity | iNaturalist | None | ✅ Working |
| Birds | eBird | Free | ✅ Working |

### Global Fallback (Always Available) ✅

| Data Type | Source | Status |
|-----------|--------|--------|
| Tree Cover | GFW | ✅ Working |
| Tree Loss | GFW | ✅ Working |
| Forest Carbon Flux | GFW | ✅ Working |
| Land Cover | GFW | ✅ Working |
| Protected Areas | GFW | ✅ Working |
| Grasslands | GFW | ✅ Working |

### Ontario-Specific (Future Phases) ⏳

| Data Type | Source | Phase | Status |
|-----------|--------|-------|--------|
| Water Quality | PWQMN | Phase 2 | ⏳ Planned |
| Water Quality | DataStream | Phase 2 | ⏳ Planned |
| Biodiversity | GBIF | Phase 2 | ⏳ Planned |
| Forest Inventory | FRI | Phase 3 | ⏳ Planned |

---

## Usage Examples

### Example 1: Biodiversity Query (Uses Ontario Data)

**User Query:**
```
"What species have been seen in Algonquin Park this month?"
```

**System Behavior:**
```python
1. Tries iNaturalist (Ontario-specific) ✅
2. Returns: 150 observations from iNaturalist
   Message: "Found 150 observations of 45 species in Algonquin Provincial Park"
```

**No fallback needed** - Ontario data available!

---

### Example 2: Forest Cover Query (Uses Global Data)

**User Query:**
```
"What is the tree cover in Algonquin Park?"
```

**System Behavior:**
```python
1. Ontario handler recognizes forest metric
2. Immediately uses GFW (Ontario doesn't have forest data yet)
3. Returns: Tree cover percentage from Global Forest Watch
   Message: "[Using global dataset] Tree cover: 87.5%"
```

**Falls back immediately** - Uses GFW data.

---

### Example 3: No Ontario Data Available (Falls Back)

**User Query:**
```
"What species were seen in remote area XYZ last year?"
```

**System Behavior:**
```python
1. Tries iNaturalist ❌
   - No observations found in that area/time
2. Falls back to GFW ✅
   - Returns forest/land cover data instead
3. Message: "[Using global dataset] Tree cover and land cover data available"
```

**Falls back gracefully** - Still provides useful environmental data.

---

### Example 4: eBird Key Missing (Falls Back)

**User Query:**
```
"What birds have been seen in Algonquin Park?"
```

**System Behavior:**
```python
1. Tries eBird ❌
   - API key not configured
2. Falls back to iNaturalist ✅
   - Returns general biodiversity (includes some birds)
3. Message: "Found 120 observations (includes birds and other species)"
```

**Falls back to alternate source** - User still gets bird data.

---

## Implementation Details

### Code Location

- **Handler:** `src/tools/data_handlers/ontario_handler.py`
- **Tool:** `src/tools/ontario/get_ontario_statistics.py`
- **Tests:** `tests/tools/test_ontario_handler.py`

### Key Methods

```python
class OntarioDataHandler(DataSourceHandler):
    def _get_fallback_handler(self):
        """Lazy initialize Analytics Handler for global datasets."""
        if self.fallback_handler is None:
            from src.tools.data_handlers.analytics_handler import AnalyticsHandler
            self.fallback_handler = AnalyticsHandler()
        return self.fallback_handler

    async def pull_data(self, ...):
        """
        Try Ontario sources first, then fall back to global datasets.
        """
        # Try Ontario-specific source
        if source == "iNaturalist":
            result = await self._pull_inat_data(...)
            if result.success and result.data_points_count > 0:
                return result

        # Fall back to global datasets
        fallback_handler = self._get_fallback_handler()
        if fallback_handler.can_handle(dataset):
            fallback_result = await fallback_handler.pull_data(...)
            fallback_result.message = f"[Using global dataset] {fallback_result.message}"
            return fallback_result
```

---

## Metric-Specific Routing

The `get_ontario_statistics` tool automatically routes to the appropriate data source:

```python
if metric == "birds":
    # Use eBird (Ontario-specific)
    dataset = {"source": "eBird"}

elif metric in ["forest_cover", "tree_cover", "tree_loss"]:
    # Use GFW (global)
    dataset = {"source": "Tree cover", "dataset_name": "Tree cover"}

else:
    # Default to iNaturalist (Ontario-specific)
    dataset = {"source": "iNaturalist"}
```

**Supported Metrics:**
- `biodiversity` → iNaturalist (Ontario)
- `birds` → eBird (Ontario)
- `forest_cover` → GFW (global)
- `tree_cover` → GFW (global)
- `tree_loss` → GFW (global)
- `deforestation` → GFW (global)

---

## User Experience

### Clear Communication

The system always tells users which data source was used:

**Ontario Data:**
```json
{
  "data_source": "iNaturalist",
  "message": "Found 150 observations in Algonquin Provincial Park"
}
```

**Global Data (Fallback):**
```json
{
  "data_source": "Global Forest Watch",
  "message": "[Using global dataset] Tree cover: 87.5%",
  "note": "Using global dataset (Ontario-specific data for this metric not yet available)"
}
```

**Both Sources:**
```json
{
  "data_source": "iNaturalist (via global dataset)",
  "message": "Found data using global biodiversity database"
}
```

---

## Testing

### Test Coverage

```python
# Test 1: Normal Ontario data retrieval
test_pull_inat_data_success()

# Test 2: Fallback when Ontario returns no data
test_inat_no_data_falls_back()

# Test 3: Fallback when source not implemented
test_pull_data_unsupported_source_falls_back()

# Test 4: Fallback when API key missing
test_pull_data_no_ebird_key()
```

### Run Tests

```bash
pytest tests/tools/test_ontario_handler.py -v -k fallback
```

---

## Advantages

✅ **Always Returns Data**
- Users never get "no data available" errors unnecessarily
- System tries multiple sources before giving up

✅ **Seamless Experience**
- Fallback happens automatically
- Users don't need to know about data source complexities

✅ **Clear Attribution**
- Messages clearly indicate which source provided the data
- Users know if they're seeing Ontario-specific or global data

✅ **Graceful Degradation**
- System works even when Ontario sources are down
- Continues to function during Phase 2/3 development

✅ **Future-Proof**
- As Ontario sources are added, they take priority
- Global data remains available as backup

---

## Configuration

### No Additional Setup Required

The fallback system works out-of-the-box with existing configuration:

```bash
# .env - Only Ontario-specific keys needed
EBIRD_API_KEY=your_key_here  # Optional

# GFW APIs don't require keys - fallback works automatically
```

---

## Monitoring

### Logs Show Fallback Behavior

```
INFO: Ontario handler attempting iNaturalist data for query: species in Algonquin...
INFO: iNaturalist returned no data, trying fallback...
INFO: Falling back to global datasets (GFW Analytics) for Tree cover
INFO: [Using global dataset] Successfully retrieved tree cover data
```

### Message Prefixes

- `"[Using global dataset]"` → Data came from fallback
- No prefix → Data came from Ontario-specific source

---

## Future Enhancements

### Phase 2 (Weeks 3-4)
- [ ] PWQMN water quality with GFW watershed fallback
- [ ] DataStream API with alternate water quality sources
- [ ] GBIF biodiversity with iNaturalist fallback

### Phase 3 (Weeks 5-6)
- [ ] FRI forest data with GFW forest fallback
- [ ] Intelligent source prioritization based on data quality
- [ ] Multi-source aggregation (combine Ontario + global)

### Phase 4 (Weeks 7-8)
- [ ] Caching layer to reduce fallback frequency
- [ ] Predictive fallback (check data availability before querying)
- [ ] User preference for Ontario-only vs. global data

---

## Troubleshooting

### Problem: Always Using Fallback for Biodiversity

**Cause:** iNaturalist might be rate-limited or down

**Solution:**
```bash
# Check logs
grep "iNaturalist" logs/app.log

# Verify API accessibility
curl "https://api.inaturalist.org/v1/observations?place_id=6942&per_page=1"
```

### Problem: Fallback Not Working

**Cause:** Analytics handler not available

**Solution:**
```python
# Verify analytics handler is imported correctly
from src.tools.data_handlers.analytics_handler import AnalyticsHandler
handler = AnalyticsHandler()
assert handler.can_handle(dataset) is True
```

### Problem: Want Ontario-Only Data (No Fallback)

**Solution:**
```python
# Modify handler temporarily
handler = OntarioDataHandler()
handler.fallback_handler = None  # Disable fallback

# Or check result message
if "[Using global dataset]" in result.message:
    # This came from fallback
    pass
```

---

## Summary

The fallback system ensures that **Ontario Nature Watch always provides environmental data**, whether from Ontario-specific sources (iNaturalist, eBird) or global datasets (Global Forest Watch).

**Key Benefits:**
- 🎯 Always returns data when possible
- 🔄 Seamless automatic fallback
- 📊 Clear data source attribution
- 🚀 Works during development phases
- ✅ No extra configuration needed

**Current Status:**
- ✅ iNaturalist → GFW fallback working
- ✅ eBird → iNaturalist/GFW fallback working
- ✅ Forest metrics → Direct to GFW working
- ✅ Tests passing
- ✅ Documentation complete

---

**Document Version:** 1.1
**Last Updated:** November 16, 2025
**Status:** Production Ready
