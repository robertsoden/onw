# Quick Start Guide - Ontario Nature Watch with Williams Treaty Territory

**Last Updated:** 2025-11-14
**Approach:** Hybrid (Core Ontario + Williams Treaty Territory Enhancement)

---

## What You Have

You now have a complete implementation plan and foundation for building Ontario Nature Watch with specialized Williams Treaty Territory features.

### Documentation Package

1. **Ontario Core Implementation:**
   - `research/ontario-zeno-workplan.md` - Complete technical specification (1,830 lines)
   - `research/ontario-implementation-checklist.md` - Phase-by-phase tasks
   - `research/ONTARIO_PROJECT_SUMMARY.md` - Executive overview
   - `research/README.md` - Sample code usage guide

2. **Williams Treaty Territory Enhancement:**
   - `research/WILLIAMS_TREATY_ENHANCEMENT_PLAN.md` - Hybrid approach specification
   - Database schema for 7 First Nations communities
   - Cultural sensitivity protocols
   - Treaty-specific agent tools

3. **Database Setup (READY TO USE):**
   - `db/alembic/versions/001_ontario_schema.py` - Alembic migration file
   - `research/001_ontario_schema.sql` - Standalone SQL version
   - `db/ONTARIO_SCHEMA_SETUP.md` - Setup and verification guide
   - `db/validate_ontario_schema.sql` - Validation script

4. **Sample Code (Ready to Adapt):**
   - `research/ingest_ontario_parks.py` - Example ingestion script
   - `research/ontario_area_lookup_tool.py` - LangChain tools

---

## Three Ways to Get Started

### **Option A: Just Set Up the Database (15 minutes)**

**Best for:** Getting the foundation in place immediately

```bash
# 1. Navigate to project
cd /Users/robertsoden/www/onw

# 2. Ensure database exists
createdb ontario-nature-watch

# 3. Set environment variable
export DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/ontario-nature-watch"

# 4. Run migration
alembic upgrade head

# 5. Validate
psql $DATABASE_URL -f db/validate_ontario_schema.sql
```

**What you get:**
- 9 Ontario-specific tables ready for data
- Spatial and text search indexes
- Search and analytics functions
- Update triggers

**Next:** Start data ingestion (Option B)

---

### **Option B: Set Up Database + Begin Data Ingestion (1-2 days)**

**Best for:** Getting a working prototype with real data

```bash
# 1. Complete Option A first (database setup)

# 2. Review sample ingestion script
cat research/ingest_ontario_parks.py

# 3. Update Ontario GeoHub URLs (check current endpoints)
# Edit src/ingest/ingest_ontario_parks.py

# 4. Run first ingestion (Provincial Parks)
python src/ingest/ingest_ontario_parks.py

# 5. Verify data
psql $DATABASE_URL -c "SELECT COUNT(*) FROM ontario_provincial_parks;"
# Should return ~340 parks

# 6. Test search function
psql $DATABASE_URL -c "SELECT * FROM search_ontario_areas('Algonquin', NULL, NULL, 5);"
```

**What you get:**
- Working database with Ontario parks data
- Searchable conservation areas
- Foundation for agent queries

**Next:** Build Ontario agent tools (Option C)

---

### **Option C: Full Implementation Following Checklist (8-14 weeks)**

**Best for:** Production-ready system with Williams Treaty Territory

Follow the detailed implementation plan:

```bash
# 1. Review the complete plan
cat research/ontario-implementation-checklist.md
cat research/WILLIAMS_TREATY_ENHANCEMENT_PLAN.md

# 2. Follow Phase 1 (Weeks 1-8): Core Ontario
# - Database setup (completed in Option A)
# - Data ingestion for all Ontario datasets
# - Ontario agent development
# - Testing

# 3. Follow Phase 2 (Weeks 9-12): Williams Treaty Territory
# - WTT database extensions
# - 7 First Nations communities data
# - Treaty-specific tools
# - Cultural sensitivity implementation

# 4. Follow Phase 3 (Weeks 13-14): Integration & Deployment
# - End-to-end testing
# - Documentation
# - Deployment
```

**What you get:**
- Complete Ontario Nature Watch system
- Enhanced Williams Treaty Territory features
- Production-ready deployment
- Community-engaged approach

---

## Understanding the Architecture

### Hybrid Approach

**Core Ontario (Weeks 1-8):**
- 340+ Provincial Parks
- 36 Conservation Authorities
- 290+ Conservation Reserves
- Watersheds, municipalities, forests
- Full Ontario agent capabilities

**Williams Treaty Territory Enhancement (Weeks 9-12):**
- Treaty boundary and 7 First Nations
- Cultural heritage sites (non-sensitive)
- Treaty-specific water bodies
- Cultural sensitivity protocols
- First Nations partnership framework

### Database Schema

```
Ontario Tables (9):
├── ontario_provincial_parks (~340 records expected)
├── ontario_conservation_reserves (~290 records)
├── ontario_conservation_authorities (36 records - EXACT)
├── ontario_watersheds (300+ records)
├── ontario_municipalities (444 records)
├── ontario_forest_management_units (47 records)
├── ontario_waterbodies (major lakes, rivers)
├── ontario_wetlands (evaluated wetlands)
└── ontario_species_at_risk (generalized locations)

Williams Treaty Territory Tables (5 - to be added in Phase 2):
├── williams_treaty_territory (1 record - treaty boundary)
├── williams_treaty_first_nations (7 records - EXACT)
├── williams_treaty_heritage_sites (non-sensitive only)
├── williams_treaty_conservation_areas (links to Ontario tables)
└── williams_treaty_water_bodies (Rice Lake, Scugog Lake, etc.)
```

---

## Key Data Sources

### Ontario Data (Phase 1)
- **Ontario GeoHub:** https://geohub.lio.gov.on.ca
  - Provincial Parks, Conservation Reserves
  - Conservation Authorities, Watersheds
  - Municipalities, FMUs, Water bodies
- **Conservation Ontario:** https://conservationontario.ca
- **Federal CPCAD:** Filter for Ontario (`PROV_TERR = 'ON'`)

### Williams Treaty Territory Data (Phase 2)
- **Indigenous Services Canada:** Treaty boundaries, First Nations profiles
- **Native Land Digital:** Traditional territories (indicative)
- **First Nations Direct:** Community websites and data sharing
- **Ontario Archaeological Database:** Heritage sites (restricted access)

---

## Timeline Overview

### Fast Track (4 weeks minimum)
- Week 1: Database + Ontario parks ingestion
- Week 2: Conservation authorities + watersheds
- Week 3: Ontario agent basic tools
- Week 4: Williams Treaty Territory basic layer

### Standard Track (10-14 weeks recommended)
- **Weeks 1-3:** Foundation & core data ingestion
- **Weeks 4-6:** Ontario agent customization
- **Weeks 7-8:** Testing & frontend
- **Weeks 9-10:** Williams Treaty Territory data layer
- **Weeks 11-12:** Treaty-specific agent features
- **Weeks 13-14:** Integration, testing, deployment

---

## Budget Summary

| Component | Cost (CAD) |
|-----------|------------|
| Core Ontario Development | $40,000 |
| Williams Treaty Territory Enhancement | $28,000 |
| Integration & Testing | $10,000 |
| Documentation | $6,000 |
| Project Management | $12,000 |
| Contingency (15%) | $14,400 |
| **Total Development** | **$110,400** |
| Infrastructure (Year 1) | $13,320 |
| One-time costs | $10,000 |
| **TOTAL (Year 1)** | **$133,720** |

---

## Success Criteria

### Database Setup (Immediate)
- ✅ All 9 Ontario tables created
- ✅ All 18 indexes (9 GIST + 9 GIN) created
- ✅ All 3 functions working
- ✅ All 6 triggers active
- ✅ Validation script passes

### Data Quality (After Ingestion)
- ✅ ~340 provincial parks
- ✅ Exactly 36 Conservation Authorities
- ✅ All geometries valid (0 invalid)
- ✅ All projections EPSG:4326
- ✅ No duplicate records

### Williams Treaty Territory (Phase 2)
- ✅ Exactly 7 First Nations communities
- ✅ Treaty boundary accurately mapped
- ✅ Traditional names verified with communities
- ✅ 0 sensitive sites disclosed without permission
- ✅ Cultural protocols implemented

### Agent Performance
- ✅ >90% accuracy on Ontario queries
- ✅ >95% accuracy on Williams Treaties facts
- ✅ 100% culturally appropriate language
- ✅ Spatial queries <2 seconds

---

## Immediate Next Steps

### Today (30 minutes)
1. ✅ Review this quick start guide
2. ✅ Choose your approach (Option A, B, or C)
3. ✅ Set up database (Option A)
4. ✅ Run validation script

### This Week
1. ✅ Complete database setup
2. ✅ Source Ontario GeoHub API keys (if needed)
3. ✅ Review and adapt sample ingestion script
4. ✅ Test with one dataset (Provincial Parks)

### Next Week
1. ✅ Ingest core datasets (parks, CAs, watersheds)
2. ✅ Validate data quality
3. ✅ Start Williams Treaty Territory data sourcing
4. ✅ Begin agent tool development

---

## Common Commands

### Database
```bash
# Create database
createdb ontario-nature-watch

# Apply migrations
alembic upgrade head

# Validate schema
psql $DATABASE_URL -f db/validate_ontario_schema.sql

# Check table counts
psql $DATABASE_URL -c "SELECT 'parks' as type, COUNT(*) FROM ontario_provincial_parks UNION ALL SELECT 'CAs', COUNT(*) FROM ontario_conservation_authorities;"

# Test search
psql $DATABASE_URL -c "SELECT * FROM search_ontario_areas('Algonquin', NULL, NULL, 5);"
```

### Data Ingestion
```bash
# Run sample ingestion
python src/ingest/ingest_ontario_parks.py

# Check logs
tail -f logs/ingestion.log
```

### Development
```bash
# Start API
make api

# Start frontend
make frontend

# Run tests
pytest tests/test_ontario_data_quality.py -v
```

---

## Getting Help

### Documentation References
- **Core Ontario:** `research/ontario-zeno-workplan.md`
- **Implementation Checklist:** `research/ontario-implementation-checklist.md`
- **Williams Treaty Territory:** `research/WILLIAMS_TREATY_ENHANCEMENT_PLAN.md`
- **Database Setup:** `db/ONTARIO_SCHEMA_SETUP.md`

### Troubleshooting
- See: `db/ONTARIO_SCHEMA_SETUP.md` → Troubleshooting section
- Check: `research/ontario-implementation-checklist.md` → Common Issues

### Community Resources
- Ontario GeoHub Support: lio@ontario.ca
- Conservation Ontario: info@conservationontario.ca
- Indigenous Services Canada: Open Data portal

---

## What's Already Done

✅ **Complete Planning:**
- Full Ontario implementation specification
- Williams Treaty Territory enhancement plan
- Phase-by-phase checklists

✅ **Database Foundation:**
- Alembic migration ready to run
- All tables, indexes, functions defined
- Validation script created
- Setup documentation complete

✅ **Sample Code:**
- Ingestion script template (parks)
- LangChain tools template
- Agent prompts examples

---

## What You Need to Do

**Phase 1 (Core Ontario):**
- [ ] Set up database (15 min) ← START HERE
- [ ] Obtain Ontario GeoHub data access
- [ ] Adapt and run ingestion scripts
- [ ] Build Ontario agent tools
- [ ] Test and validate

**Phase 2 (Williams Treaty Territory):**
- [ ] Source treaty boundary data
- [ ] Contact First Nations communities
- [ ] Create WTT database schema
- [ ] Ingest WTT-specific data
- [ ] Build treaty-specific tools

**Phase 3 (Integration):**
- [ ] Test Ontario + WTT together
- [ ] Frontend customization
- [ ] Documentation finalization
- [ ] Deployment

---

## Ready to Begin?

**Recommended path:**

```bash
# 1. Start with database setup (Option A) - 15 minutes
cd /Users/robertsoden/www/onw
createdb ontario-nature-watch
export DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/ontario-nature-watch"
alembic upgrade head
psql $DATABASE_URL -f db/validate_ontario_schema.sql

# 2. If validation passes, you're ready for data ingestion
# Review: research/ontario-implementation-checklist.md (Phase 2)

# 3. Start with one dataset to test
# Review and adapt: research/ingest_ontario_parks.py
```

---

**You have everything you need to start building Ontario Nature Watch with Williams Treaty Territory enhancement. The foundation is ready - let's build it!**

---

**Questions?**
- Technical implementation: Review `research/ontario-zeno-workplan.md`
- Database issues: See `db/ONTARIO_SCHEMA_SETUP.md`
- Williams Treaty Territory: Check `research/WILLIAMS_TREATY_ENHANCEMENT_PLAN.md`
- Quick reference: Use `research/ontario-implementation-checklist.md`
