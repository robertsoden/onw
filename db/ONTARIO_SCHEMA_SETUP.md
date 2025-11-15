# Ontario Schema Setup Guide

## Overview

This guide walks you through setting up the Ontario Nature Watch database schema.

## Prerequisites

- PostgreSQL 12+ installed
- PostGIS 3.0+ extension available
- Database created (e.g., `ontario-nature-watch`)
- Database connection configured in `.env`

## Step 1: Apply the Migration

### Using Alembic (Recommended)

```bash
# Make sure you're in the project root directory
cd /Users/robertsoden/www/onw

# Ensure database URL is set
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/ontario-nature-watch"

# Or for synchronous connection (Alembic uses psycopg2)
export DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/ontario-nature-watch"

# Run the migration
alembic upgrade head
```

### Using SQL Directly (Alternative)

If you prefer to run the SQL directly:

```bash
# Using the standalone SQL file from research folder
psql $DATABASE_URL -f research/001_ontario_schema.sql

# Or using psql with connection parameters
psql -h localhost -U postgres -d ontario-nature-watch -f research/001_ontario_schema.sql
```

## Step 2: Verify Installation

After running the migration, verify that all tables and functions were created successfully.

### Check Tables

```sql
-- List all Ontario tables
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name LIKE 'ontario_%'
ORDER BY table_name;
```

**Expected Output (8 tables):**
```
ontario_conservation_authorities
ontario_conservation_reserves
ontario_forest_management_units
ontario_municipalities
ontario_provincial_parks
ontario_species_at_risk
ontario_waterbodies
ontario_watersheds
ontario_wetlands
```

### Check Extensions

```sql
-- Verify PostGIS and pg_trgm extensions are enabled
SELECT extname, extversion
FROM pg_extension
WHERE extname IN ('postgis', 'pg_trgm');
```

**Expected Output:**
```
extname  | extversion
---------+-----------
postgis  | 3.4.0 (or similar)
pg_trgm  | 1.6 (or similar)
```

### Check Spatial Indexes

```sql
-- List all GIST indexes (spatial indexes) on Ontario tables
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename LIKE 'ontario_%'
  AND indexdef LIKE '%USING gist%'
ORDER BY tablename, indexname;
```

**Expected Output (9 spatial indexes):**
```
ontario_conservation_authorities | idx_ont_ca_geom
ontario_conservation_reserves    | idx_ont_reserves_geom
ontario_forest_management_units  | idx_ont_fmus_geom
ontario_municipalities          | idx_ont_municipalities_geom
ontario_provincial_parks        | idx_ont_parks_geom
ontario_species_at_risk         | idx_ont_species_geom
ontario_waterbodies             | idx_ont_water_geom
ontario_watersheds              | idx_ont_watersheds_geom
ontario_wetlands                | idx_ont_wetlands_geom
```

### Check Text Search Indexes (GIN)

```sql
-- List all GIN indexes (fuzzy text search) on Ontario tables
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename LIKE 'ontario_%'
  AND indexdef LIKE '%USING gin%'
ORDER BY tablename, indexname;
```

**Expected Output (9 text search indexes):**
```
ontario_conservation_authorities | idx_ont_ca_name
ontario_conservation_reserves    | idx_ont_reserves_name
ontario_forest_management_units  | idx_ont_fmus_name
ontario_municipalities          | idx_ont_municipalities_name
ontario_provincial_parks        | idx_ont_parks_name
ontario_species_at_risk         | idx_ont_species_name
ontario_waterbodies             | idx_ont_water_name
ontario_watersheds              | idx_ont_watersheds_name
ontario_wetlands                | idx_ont_wetlands_name
```

### Check Functions

```sql
-- List Ontario-specific functions
SELECT
    routine_name,
    routine_type,
    data_type
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND (routine_name LIKE '%ontario%'
       OR routine_name IN ('search_ontario_areas', 'calculate_protected_area_coverage'))
ORDER BY routine_name;
```

**Expected Output (3 functions):**
```
calculate_protected_area_coverage | FUNCTION | record
search_ontario_areas             | FUNCTION | record
update_updated_at_column         | FUNCTION | trigger
```

### Check Triggers

```sql
-- List all triggers on Ontario tables
SELECT
    trigger_name,
    event_object_table,
    action_timing,
    event_manipulation
FROM information_schema.triggers
WHERE event_object_table LIKE 'ontario_%'
ORDER BY event_object_table, trigger_name;
```

**Expected Output (6 triggers for updated_at):**
```
update_ontario_conservation_authorities_updated_at
update_ontario_conservation_reserves_updated_at
update_ontario_forest_management_units_updated_at
update_ontario_municipalities_updated_at
update_ontario_provincial_parks_updated_at
update_ontario_watersheds_updated_at
```

## Step 3: Test Functions

### Test Search Function

```sql
-- Test the unified search function (should return empty results initially)
SELECT * FROM search_ontario_areas('Algonquin', NULL, NULL, 5);
```

**Expected:** Empty result set (no data ingested yet)

If you want to test with sample data:

```sql
-- Insert a test park
INSERT INTO ontario_provincial_parks (
    park_id,
    park_name,
    park_class,
    geometry,
    size_ha
) VALUES (
    'TEST001',
    'Test Park',
    'Natural Environment',
    ST_GeomFromText('MULTIPOLYGON(((
        -79.5 44.5, -79.4 44.5, -79.4 44.6, -79.5 44.6, -79.5 44.5
    )))', 4326),
    10000
);

-- Now search for it
SELECT * FROM search_ontario_areas('Test', NULL, NULL, 5);

-- Clean up test data
DELETE FROM ontario_provincial_parks WHERE park_id = 'TEST001';
```

### Test Protected Area Coverage Function

```sql
-- Test coverage calculation with a sample geometry (Toronto area)
SELECT * FROM calculate_protected_area_coverage(
    ST_GeomFromText('POLYGON((
        -79.7 43.5, -79.1 43.5, -79.1 43.9, -79.7 43.9, -79.7 43.5
    ))', 4326)
);
```

**Expected:** Should return coverage statistics (likely 0% until data is ingested)

### Test Triggers

```sql
-- Insert a test record
INSERT INTO ontario_provincial_parks (
    park_id, park_name, park_class, geometry, size_ha
) VALUES (
    'TRIGGER_TEST',
    'Trigger Test Park',
    'Test',
    ST_GeomFromText('MULTIPOLYGON(((-79.5 44.5, -79.4 44.5, -79.4 44.6, -79.5 44.6, -79.5 44.5)))', 4326),
    1000
);

-- Check created_at and updated_at
SELECT park_name, created_at, updated_at
FROM ontario_provincial_parks
WHERE park_id = 'TRIGGER_TEST';

-- Wait a moment, then update the record
SELECT pg_sleep(2);

UPDATE ontario_provincial_parks
SET size_ha = 1500
WHERE park_id = 'TRIGGER_TEST';

-- Check that updated_at changed
SELECT park_name, created_at, updated_at
FROM ontario_provincial_parks
WHERE park_id = 'TRIGGER_TEST';

-- Clean up
DELETE FROM ontario_provincial_parks WHERE park_id = 'TRIGGER_TEST';
```

**Expected:** `updated_at` should be later than `created_at` after the UPDATE

## Step 4: Verify Geometry Support

```sql
-- Check PostGIS version and geometry type support
SELECT PostGIS_Full_Version();

-- Test geometry creation and validation
SELECT
    ST_IsValid(
        ST_GeomFromText('MULTIPOLYGON(((-79.5 44.5, -79.4 44.5, -79.4 44.6, -79.5 44.6, -79.5 44.5)))', 4326)
    ) AS is_valid,
    ST_GeometryType(
        ST_GeomFromText('MULTIPOLYGON(((-79.5 44.5, -79.4 44.5, -79.4 44.6, -79.5 44.6, -79.5 44.5)))', 4326)
    ) AS geom_type,
    ST_SRID(
        ST_GeomFromText('MULTIPOLYGON(((-79.5 44.5, -79.4 44.5, -79.4 44.6, -79.5 44.6, -79.5 44.5)))', 4326)
    ) AS srid;
```

**Expected Output:**
```
is_valid | geom_type              | srid
---------|------------------------|------
t        | ST_MultiPolygon        | 4326
```

## Step 5: Check Constraints and Foreign Keys

```sql
-- List all foreign key constraints on Ontario tables
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_name LIKE 'ontario_%'
ORDER BY tc.table_name;
```

**Expected Output (1 foreign key):**
```
table_name          | column_name               | foreign_table_name                | foreign_column_name
--------------------|---------------------------|-----------------------------------|--------------------
ontario_watersheds  | conservation_authority_id | ontario_conservation_authorities  | id
```

## Complete Validation Script

Run this complete validation script to check everything at once:

```sql
-- ============================================================================
-- ONTARIO SCHEMA VALIDATION SCRIPT
-- ============================================================================

-- Set display settings for better output
\x off
\pset border 2

\echo '====================================='
\echo 'ONTARIO NATURE WATCH SCHEMA VALIDATION'
\echo '====================================='

\echo ''
\echo '1. CHECKING TABLES...'
SELECT COUNT(*) as ontario_table_count
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name LIKE 'ontario_%';

\echo ''
\echo 'Expected: 9 tables'

\echo ''
\echo '2. CHECKING EXTENSIONS...'
SELECT extname, extversion
FROM pg_extension
WHERE extname IN ('postgis', 'pg_trgm');

\echo ''
\echo 'Expected: postgis and pg_trgm'

\echo ''
\echo '3. CHECKING SPATIAL INDEXES (GIST)...'
SELECT COUNT(*) as gist_index_count
FROM pg_indexes
WHERE tablename LIKE 'ontario_%'
  AND indexdef LIKE '%USING gist%';

\echo ''
\echo 'Expected: 9 spatial indexes'

\echo ''
\echo '4. CHECKING TEXT SEARCH INDEXES (GIN)...'
SELECT COUNT(*) as gin_index_count
FROM pg_indexes
WHERE tablename LIKE 'ontario_%'
  AND indexdef LIKE '%USING gin%';

\echo ''
\echo 'Expected: 9 text search indexes'

\echo ''
\echo '5. CHECKING FUNCTIONS...'
SELECT routine_name
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN (
      'search_ontario_areas',
      'calculate_protected_area_coverage',
      'update_updated_at_column'
  )
ORDER BY routine_name;

\echo ''
\echo 'Expected: 3 functions'

\echo ''
\echo '6. CHECKING TRIGGERS...'
SELECT COUNT(*) as trigger_count
FROM information_schema.triggers
WHERE event_object_table LIKE 'ontario_%';

\echo ''
\echo 'Expected: 6 triggers'

\echo ''
\echo '7. TESTING GEOMETRY SUPPORT...'
SELECT
    ST_IsValid(ST_GeomFromText('POINT(-79.5 44.5)', 4326)) AS geom_valid,
    ST_SRID(ST_GeomFromText('POINT(-79.5 44.5)', 4326)) AS correct_srid;

\echo ''
\echo 'Expected: geom_valid = t, correct_srid = 4326'

\echo ''
\echo '8. CHECKING TABLE ROW COUNTS...'
SELECT
    'ontario_provincial_parks' as table_name,
    COUNT(*) as row_count
FROM ontario_provincial_parks
UNION ALL
SELECT 'ontario_conservation_authorities', COUNT(*) FROM ontario_conservation_authorities
UNION ALL
SELECT 'ontario_conservation_reserves', COUNT(*) FROM ontario_conservation_reserves
UNION ALL
SELECT 'ontario_watersheds', COUNT(*) FROM ontario_watersheds
UNION ALL
SELECT 'ontario_municipalities', COUNT(*) FROM ontario_municipalities
UNION ALL
SELECT 'ontario_forest_management_units', COUNT(*) FROM ontario_forest_management_units
UNION ALL
SELECT 'ontario_waterbodies', COUNT(*) FROM ontario_waterbodies
UNION ALL
SELECT 'ontario_wetlands', COUNT(*) FROM ontario_wetlands
UNION ALL
SELECT 'ontario_species_at_risk', COUNT(*) FROM ontario_species_at_risk;

\echo ''
\echo 'Expected: All 0 (data not yet ingested)'

\echo ''
\echo '====================================='
\echo 'VALIDATION COMPLETE'
\echo '====================================='
```

**Save this as:** `/Users/robertsoden/www/onw/db/validate_ontario_schema.sql`

**Run with:**
```bash
psql $DATABASE_URL -f db/validate_ontario_schema.sql
```

## Troubleshooting

### Issue: "Extension postgis does not exist"

**Solution:**
```sql
-- Install PostGIS extension
CREATE EXTENSION postgis;
CREATE EXTENSION pg_trgm;
```

Or on the system level:
```bash
# Ubuntu/Debian
sudo apt-get install postgresql-postgis postgresql-contrib

# macOS (Homebrew)
brew install postgis

# Then in psql
CREATE EXTENSION postgis;
```

### Issue: "Permission denied for schema public"

**Solution:**
```sql
-- Grant permissions to your user
GRANT ALL ON SCHEMA public TO your_username;
GRANT ALL ON ALL TABLES IN SCHEMA public TO your_username;
```

### Issue: Alembic can't connect to database

**Solution:**
```bash
# Check your DATABASE_URL format
# For Alembic, use psycopg2 (not asyncpg)
export DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/dbname"

# Test connection
psql $DATABASE_URL -c "SELECT version();"
```

### Issue: Migration already applied

**Solution:**
```bash
# Check current migration state
alembic current

# To rollback one migration
alembic downgrade -1

# To rollback to specific revision
alembic downgrade <revision_id>

# To reapply
alembic upgrade head
```

## Next Steps

After successfully setting up the schema:

1. ✅ **Data Ingestion**: Proceed to ingest Ontario data
   - See: `research/ontario-implementation-checklist.md` (Phase 2)
   - Start with: `src/ingest/ingest_ontario_parks.py`

2. ✅ **Verify Data Quality**: After ingestion, run data quality tests
   - See: `tests/test_ontario_data_quality.py`

3. ✅ **Agent Setup**: Configure Ontario-specific agent tools
   - See: `research/WILLIAMS_TREATY_ENHANCEMENT_PLAN.md` (Section 6)

## Summary Checklist

- [ ] PostgreSQL 12+ installed with PostGIS
- [ ] Database created
- [ ] DATABASE_URL configured in `.env`
- [ ] Migration applied (`alembic upgrade head`)
- [ ] All 9 tables created
- [ ] All 18 indexes created (9 GIST + 9 GIN)
- [ ] All 3 functions created
- [ ] All 6 triggers created
- [ ] Validation script passes
- [ ] Geometry support verified
- [ ] Ready for data ingestion

---

**Database Schema Version:** 001_ontario_schema
**Created:** 2025-11-14
**Author:** Ontario Nature Watch Team
