-- ============================================================================
-- ONTARIO NATURE WATCH SCHEMA VALIDATION SCRIPT
-- ============================================================================
-- This script validates that the Ontario schema was installed correctly
-- Run with: psql $DATABASE_URL -f db/validate_ontario_schema.sql
-- ============================================================================

-- Set display settings for better output
\x off
\pset border 2

\echo '========================================='
\echo 'ONTARIO NATURE WATCH SCHEMA VALIDATION'
\echo '========================================='
\echo ''

-- ============================================================================
-- 1. CHECK TABLES
-- ============================================================================
\echo '1. CHECKING ONTARIO TABLES...'
\echo '------------------------------'

SELECT
    table_name,
    CASE
        WHEN table_name IN (
            'ontario_provincial_parks',
            'ontario_conservation_reserves',
            'ontario_conservation_authorities',
            'ontario_watersheds',
            'ontario_municipalities',
            'ontario_forest_management_units',
            'ontario_waterbodies',
            'ontario_wetlands',
            'ontario_species_at_risk'
        ) THEN '✓'
        ELSE '✗'
    END AS status
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name LIKE 'ontario_%'
ORDER BY table_name;

\echo ''
SELECT
    COUNT(*) as ontario_tables_found,
    CASE
        WHEN COUNT(*) = 9 THEN '✓ PASS'
        ELSE '✗ FAIL (Expected 9 tables)'
    END as result
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name LIKE 'ontario_%';

\echo ''

-- ============================================================================
-- 2. CHECK EXTENSIONS
-- ============================================================================
\echo '2. CHECKING REQUIRED EXTENSIONS...'
\echo '-----------------------------------'

SELECT
    extname,
    extversion,
    CASE
        WHEN extname IN ('postgis', 'pg_trgm') THEN '✓'
        ELSE '✗'
    END AS status
FROM pg_extension
WHERE extname IN ('postgis', 'pg_trgm')
ORDER BY extname;

\echo ''
SELECT
    COUNT(*) as extensions_found,
    CASE
        WHEN COUNT(*) >= 2 THEN '✓ PASS'
        ELSE '✗ FAIL (Expected postgis and pg_trgm)'
    END as result
FROM pg_extension
WHERE extname IN ('postgis', 'pg_trgm');

\echo ''

-- ============================================================================
-- 3. CHECK SPATIAL INDEXES (GIST)
-- ============================================================================
\echo '3. CHECKING SPATIAL INDEXES (GIST)...'
\echo '--------------------------------------'

SELECT
    tablename,
    indexname,
    '✓' as status
FROM pg_indexes
WHERE tablename LIKE 'ontario_%'
  AND indexdef LIKE '%USING gist%'
ORDER BY tablename, indexname;

\echo ''
SELECT
    COUNT(*) as gist_indexes_found,
    CASE
        WHEN COUNT(*) = 9 THEN '✓ PASS'
        ELSE '✗ FAIL (Expected 9 spatial indexes)'
    END as result
FROM pg_indexes
WHERE tablename LIKE 'ontario_%'
  AND indexdef LIKE '%USING gist%';

\echo ''

-- ============================================================================
-- 4. CHECK TEXT SEARCH INDEXES (GIN)
-- ============================================================================
\echo '4. CHECKING TEXT SEARCH INDEXES (GIN)...'
\echo '-----------------------------------------'

SELECT
    tablename,
    indexname,
    '✓' as status
FROM pg_indexes
WHERE tablename LIKE 'ontario_%'
  AND indexdef LIKE '%USING gin%'
ORDER BY tablename, indexname;

\echo ''
SELECT
    COUNT(*) as gin_indexes_found,
    CASE
        WHEN COUNT(*) = 9 THEN '✓ PASS'
        ELSE '✗ FAIL (Expected 9 text search indexes)'
    END as result
FROM pg_indexes
WHERE tablename LIKE 'ontario_%'
  AND indexdef LIKE '%USING gin%';

\echo ''

-- ============================================================================
-- 5. CHECK FUNCTIONS
-- ============================================================================
\echo '5. CHECKING FUNCTIONS...'
\echo '-------------------------'

SELECT
    routine_name,
    routine_type,
    CASE
        WHEN routine_name IN (
            'search_ontario_areas',
            'calculate_protected_area_coverage',
            'update_updated_at_column'
        ) THEN '✓'
        ELSE '✗'
    END AS status
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND (routine_name LIKE '%ontario%'
       OR routine_name IN ('search_ontario_areas', 'calculate_protected_area_coverage', 'update_updated_at_column'))
ORDER BY routine_name;

\echo ''
SELECT
    COUNT(*) as functions_found,
    CASE
        WHEN COUNT(*) >= 3 THEN '✓ PASS'
        ELSE '✗ FAIL (Expected at least 3 functions)'
    END as result
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN (
      'search_ontario_areas',
      'calculate_protected_area_coverage',
      'update_updated_at_column'
  );

\echo ''

-- ============================================================================
-- 6. CHECK TRIGGERS
-- ============================================================================
\echo '6. CHECKING UPDATE TRIGGERS...'
\echo '-------------------------------'

SELECT
    event_object_table as table_name,
    trigger_name,
    '✓' as status
FROM information_schema.triggers
WHERE event_object_table LIKE 'ontario_%'
  AND trigger_name LIKE 'update_%_updated_at'
ORDER BY event_object_table;

\echo ''
SELECT
    COUNT(*) as triggers_found,
    CASE
        WHEN COUNT(*) = 6 THEN '✓ PASS'
        ELSE '✗ FAIL (Expected 6 triggers for updated_at)'
    END as result
FROM information_schema.triggers
WHERE event_object_table LIKE 'ontario_%'
  AND trigger_name LIKE 'update_%_updated_at';

\echo ''

-- ============================================================================
-- 7. TEST GEOMETRY SUPPORT
-- ============================================================================
\echo '7. TESTING GEOMETRY SUPPORT...'
\echo '-------------------------------'

SELECT
    ST_IsValid(ST_GeomFromText('POINT(-79.5 44.5)', 4326)) AS geometry_valid,
    ST_SRID(ST_GeomFromText('POINT(-79.5 44.5)', 4326)) AS srid,
    ST_GeometryType(ST_GeomFromText('MULTIPOLYGON(((-79.5 44.5, -79.4 44.5, -79.4 44.6, -79.5 44.6, -79.5 44.5)))', 4326)) AS multipolygon_type,
    CASE
        WHEN ST_IsValid(ST_GeomFromText('POINT(-79.5 44.5)', 4326))
         AND ST_SRID(ST_GeomFromText('POINT(-79.5 44.5)', 4326)) = 4326
        THEN '✓ PASS'
        ELSE '✗ FAIL'
    END as result;

\echo ''

-- ============================================================================
-- 8. CHECK FOREIGN KEY CONSTRAINTS
-- ============================================================================
\echo '8. CHECKING FOREIGN KEY CONSTRAINTS...'
\echo '---------------------------------------'

SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table,
    ccu.column_name AS foreign_column,
    '✓' as status
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_name LIKE 'ontario_%'
ORDER BY tc.table_name;

\echo ''
SELECT
    COUNT(*) as foreign_keys_found,
    CASE
        WHEN COUNT(*) >= 1 THEN '✓ PASS'
        ELSE '⚠ WARNING (Expected at least 1 foreign key)'
    END as result
FROM information_schema.table_constraints AS tc
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_name LIKE 'ontario_%';

\echo ''

-- ============================================================================
-- 9. CHECK TABLE ROW COUNTS
-- ============================================================================
\echo '9. CHECKING TABLE ROW COUNTS (DATA STATUS)...'
\echo '----------------------------------------------'

SELECT
    'ontario_provincial_parks' as table_name,
    COUNT(*) as row_count,
    CASE
        WHEN COUNT(*) > 0 THEN '✓ Has Data'
        ELSE '○ Empty (awaiting ingestion)'
    END as status
FROM ontario_provincial_parks
UNION ALL
SELECT 'ontario_conservation_reserves', COUNT(*),
    CASE WHEN COUNT(*) > 0 THEN '✓ Has Data' ELSE '○ Empty' END
FROM ontario_conservation_reserves
UNION ALL
SELECT 'ontario_conservation_authorities', COUNT(*),
    CASE WHEN COUNT(*) > 0 THEN '✓ Has Data' ELSE '○ Empty' END
FROM ontario_conservation_authorities
UNION ALL
SELECT 'ontario_watersheds', COUNT(*),
    CASE WHEN COUNT(*) > 0 THEN '✓ Has Data' ELSE '○ Empty' END
FROM ontario_watersheds
UNION ALL
SELECT 'ontario_municipalities', COUNT(*),
    CASE WHEN COUNT(*) > 0 THEN '✓ Has Data' ELSE '○ Empty' END
FROM ontario_municipalities
UNION ALL
SELECT 'ontario_forest_management_units', COUNT(*),
    CASE WHEN COUNT(*) > 0 THEN '✓ Has Data' ELSE '○ Empty' END
FROM ontario_forest_management_units
UNION ALL
SELECT 'ontario_waterbodies', COUNT(*),
    CASE WHEN COUNT(*) > 0 THEN '✓ Has Data' ELSE '○ Empty' END
FROM ontario_waterbodies
UNION ALL
SELECT 'ontario_wetlands', COUNT(*),
    CASE WHEN COUNT(*) > 0 THEN '✓ Has Data' ELSE '○ Empty' END
FROM ontario_wetlands
UNION ALL
SELECT 'ontario_species_at_risk', COUNT(*),
    CASE WHEN COUNT(*) > 0 THEN '✓ Has Data' ELSE '○ Empty' END
FROM ontario_species_at_risk;

\echo ''

-- ============================================================================
-- 10. TEST SEARCH FUNCTION
-- ============================================================================
\echo '10. TESTING SEARCH FUNCTION...'
\echo '-------------------------------'

-- Test the search function exists and runs without error
\echo 'Running: SELECT * FROM search_ontario_areas(''test'', NULL, NULL, 1);'

DO $$
BEGIN
    PERFORM * FROM search_ontario_areas('test', NULL, NULL, 1);
    RAISE NOTICE '✓ PASS - search_ontario_areas() function works';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE '✗ FAIL - search_ontario_areas() function error: %', SQLERRM;
END $$;

\echo ''

-- ============================================================================
-- 11. TEST PROTECTED AREA COVERAGE FUNCTION
-- ============================================================================
\echo '11. TESTING PROTECTED AREA COVERAGE FUNCTION...'
\echo '------------------------------------------------'

-- Test coverage calculation function
\echo 'Running: SELECT * FROM calculate_protected_area_coverage(...);'

DO $$
DECLARE
    test_geom GEOMETRY;
BEGIN
    test_geom := ST_GeomFromText('POLYGON((-79.7 43.5, -79.1 43.5, -79.1 43.9, -79.7 43.9, -79.7 43.5))', 4326);
    PERFORM * FROM calculate_protected_area_coverage(test_geom);
    RAISE NOTICE '✓ PASS - calculate_protected_area_coverage() function works';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE '✗ FAIL - calculate_protected_area_coverage() function error: %', SQLERRM;
END $$;

\echo ''

-- ============================================================================
-- 12. SUMMARY
-- ============================================================================
\echo '========================================='
\echo 'VALIDATION SUMMARY'
\echo '========================================='
\echo ''

-- Overall status check
WITH validation_checks AS (
    SELECT
        CASE
            WHEN (SELECT COUNT(*) FROM information_schema.tables
                  WHERE table_schema = 'public' AND table_name LIKE 'ontario_%') = 9
            THEN 1 ELSE 0
        END as tables_ok,
        CASE
            WHEN (SELECT COUNT(*) FROM pg_extension
                  WHERE extname IN ('postgis', 'pg_trgm')) >= 2
            THEN 1 ELSE 0
        END as extensions_ok,
        CASE
            WHEN (SELECT COUNT(*) FROM pg_indexes
                  WHERE tablename LIKE 'ontario_%' AND indexdef LIKE '%USING gist%') = 9
            THEN 1 ELSE 0
        END as spatial_indexes_ok,
        CASE
            WHEN (SELECT COUNT(*) FROM pg_indexes
                  WHERE tablename LIKE 'ontario_%' AND indexdef LIKE '%USING gin%') = 9
            THEN 1 ELSE 0
        END as text_indexes_ok,
        CASE
            WHEN (SELECT COUNT(*) FROM information_schema.routines
                  WHERE routine_schema = 'public'
                    AND routine_name IN ('search_ontario_areas', 'calculate_protected_area_coverage', 'update_updated_at_column')) >= 3
            THEN 1 ELSE 0
        END as functions_ok,
        CASE
            WHEN (SELECT COUNT(*) FROM information_schema.triggers
                  WHERE event_object_table LIKE 'ontario_%') = 6
            THEN 1 ELSE 0
        END as triggers_ok
)
SELECT
    CASE
        WHEN tables_ok = 1 THEN '✓' ELSE '✗'
    END || ' Tables (9/9)' as tables,
    CASE
        WHEN extensions_ok = 1 THEN '✓' ELSE '✗'
    END || ' Extensions (2/2)' as extensions,
    CASE
        WHEN spatial_indexes_ok = 1 THEN '✓' ELSE '✗'
    END || ' Spatial Indexes (9/9)' as spatial_idx,
    CASE
        WHEN text_indexes_ok = 1 THEN '✓' ELSE '✗'
    END || ' Text Indexes (9/9)' as text_idx,
    CASE
        WHEN functions_ok = 1 THEN '✓' ELSE '✗'
    END || ' Functions (3/3)' as functions,
    CASE
        WHEN triggers_ok = 1 THEN '✓' ELSE '✗'
    END || ' Triggers (6/6)' as triggers
FROM validation_checks;

\echo ''

-- Final pass/fail
WITH validation_checks AS (
    SELECT
        CASE
            WHEN (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'ontario_%') = 9
             AND (SELECT COUNT(*) FROM pg_extension WHERE extname IN ('postgis', 'pg_trgm')) >= 2
             AND (SELECT COUNT(*) FROM pg_indexes WHERE tablename LIKE 'ontario_%' AND indexdef LIKE '%USING gist%') = 9
             AND (SELECT COUNT(*) FROM pg_indexes WHERE tablename LIKE 'ontario_%' AND indexdef LIKE '%USING gin%') = 9
             AND (SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name IN ('search_ontario_areas', 'calculate_protected_area_coverage', 'update_updated_at_column')) >= 3
             AND (SELECT COUNT(*) FROM information_schema.triggers WHERE event_object_table LIKE 'ontario_%') = 6
            THEN 'PASS'
            ELSE 'FAIL'
        END as overall_status
)
SELECT
    CASE
        WHEN overall_status = 'PASS' THEN '✓✓✓ ALL CHECKS PASSED ✓✓✓'
        ELSE '✗✗✗ SOME CHECKS FAILED ✗✗✗'
    END as result,
    CASE
        WHEN overall_status = 'PASS' THEN 'Ontario schema is ready for data ingestion'
        ELSE 'Please review failed checks above and re-run migration'
    END as next_steps
FROM validation_checks;

\echo ''
\echo '========================================='
\echo 'END OF VALIDATION'
\echo '========================================='
\echo ''
\echo 'Next Steps:'
\echo '1. If all checks passed: Begin data ingestion (see research/ontario-implementation-checklist.md Phase 2)'
\echo '2. If any checks failed: Review errors above and re-run: alembic upgrade head'
\echo '3. For help: See db/ONTARIO_SCHEMA_SETUP.md'
\echo ''
