"""add ontario schema for nature watch

Revision ID: 001_ontario_schema
Revises: d1d3e7357b26
Create Date: 2025-11-14 00:00:00.000000

This migration adds Ontario-specific tables for the Nature Watch system:
- Provincial parks, conservation reserves, conservation authorities
- Watersheds, municipalities, forest management units
- Water bodies, wetlands, species at risk
- Unified search functions and spatial statistics
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_ontario_schema"
down_revision: Union[str, None] = "d1d3e7357b26"  # Latest migration in the project
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Ontario Nature Watch schema."""

    # Enable required extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")  # For fuzzy text search

    # ============================================================================
    # ONTARIO PROVINCIAL PARKS
    # ============================================================================
    op.create_table(
        "ontario_provincial_parks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("park_id", sa.String(50), unique=True),
        sa.Column("park_name", sa.String(255), nullable=False),
        sa.Column("park_class", sa.String(50)),  # Wilderness, Natural Environment, etc.
        sa.Column("geometry", Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=False),
        sa.Column("size_ha", sa.Numeric()),
        sa.Column("regulation_date", sa.Date()),
        sa.Column("operating_season", sa.String(100)),
        sa.Column("facilities", postgresql.JSONB()),  # camping, trails, etc.
        sa.Column("website", sa.String(255)),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id")
    )

    # Indexes for parks
    op.create_index("idx_ont_parks_geom", "ontario_provincial_parks", ["geometry"], postgresql_using="gist")
    op.create_index("idx_ont_parks_name", "ontario_provincial_parks", ["park_name"], postgresql_using="gin", postgresql_ops={"park_name": "gin_trgm_ops"})
    op.create_index("idx_ont_parks_class", "ontario_provincial_parks", ["park_class"])

    # ============================================================================
    # ONTARIO CONSERVATION RESERVES
    # ============================================================================
    op.create_table(
        "ontario_conservation_reserves",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reserve_id", sa.String(50), unique=True),
        sa.Column("reserve_name", sa.String(255), nullable=False),
        sa.Column("geometry", Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=False),
        sa.Column("size_ha", sa.Numeric()),
        sa.Column("regulation_date", sa.Date()),
        sa.Column("purpose", sa.Text()),
        sa.Column("management_plan", sa.String(255)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id")
    )

    op.create_index("idx_ont_reserves_geom", "ontario_conservation_reserves", ["geometry"], postgresql_using="gist")
    op.create_index("idx_ont_reserves_name", "ontario_conservation_reserves", ["reserve_name"], postgresql_using="gin", postgresql_ops={"reserve_name": "gin_trgm_ops"})

    # ============================================================================
    # ONTARIO CONSERVATION AUTHORITIES
    # ============================================================================
    op.create_table(
        "ontario_conservation_authorities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("authority_id", sa.String(50), unique=True),
        sa.Column("authority_name", sa.String(255), nullable=False),
        sa.Column("acronym", sa.String(10)),
        sa.Column("geometry", Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=False),
        sa.Column("jurisdiction_area_ha", sa.Numeric()),
        sa.Column("watershed_count", sa.Integer()),
        sa.Column("municipalities_served", postgresql.ARRAY(sa.Text())),
        sa.Column("programs", postgresql.JSONB()),
        sa.Column("contact_email", sa.String(255)),
        sa.Column("website", sa.String(255)),
        sa.Column("established_year", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id")
    )

    op.create_index("idx_ont_ca_geom", "ontario_conservation_authorities", ["geometry"], postgresql_using="gist")
    op.create_index("idx_ont_ca_name", "ontario_conservation_authorities", ["authority_name"], postgresql_using="gin", postgresql_ops={"authority_name": "gin_trgm_ops"})
    op.create_index("idx_ont_ca_acronym", "ontario_conservation_authorities", ["acronym"])

    # ============================================================================
    # ONTARIO WATERSHEDS
    # ============================================================================
    op.create_table(
        "ontario_watersheds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("watershed_id", sa.String(50), unique=True),
        sa.Column("watershed_name", sa.String(255), nullable=False),
        sa.Column("watershed_code", sa.String(50)),
        sa.Column("geometry", Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=False),
        sa.Column("area_ha", sa.Numeric()),
        sa.Column("primary_drainage", sa.String(100)),  # Lake Ontario, Lake Huron, etc.
        sa.Column("conservation_authority_id", sa.Integer()),
        sa.Column("tertiary_watershed", sa.String(100)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["conservation_authority_id"], ["ontario_conservation_authorities.id"])
    )

    op.create_index("idx_ont_watersheds_geom", "ontario_watersheds", ["geometry"], postgresql_using="gist")
    op.create_index("idx_ont_watersheds_name", "ontario_watersheds", ["watershed_name"], postgresql_using="gin", postgresql_ops={"watershed_name": "gin_trgm_ops"})
    op.create_index("idx_ont_watersheds_ca", "ontario_watersheds", ["conservation_authority_id"])

    # ============================================================================
    # ONTARIO MUNICIPALITIES
    # ============================================================================
    op.create_table(
        "ontario_municipalities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("municipality_id", sa.String(50), unique=True),
        sa.Column("municipality_name", sa.String(255), nullable=False),
        sa.Column("municipality_type", sa.String(50)),  # City, Town, Township, etc.
        sa.Column("county", sa.String(100)),
        sa.Column("geometry", Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=False),
        sa.Column("area_ha", sa.Numeric()),
        sa.Column("population", sa.Integer()),
        sa.Column("upper_tier", sa.String(255)),  # For two-tier municipalities
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id")
    )

    op.create_index("idx_ont_municipalities_geom", "ontario_municipalities", ["geometry"], postgresql_using="gist")
    op.create_index("idx_ont_municipalities_name", "ontario_municipalities", ["municipality_name"], postgresql_using="gin", postgresql_ops={"municipality_name": "gin_trgm_ops"})
    op.create_index("idx_ont_municipalities_county", "ontario_municipalities", ["county"])

    # ============================================================================
    # ONTARIO FOREST MANAGEMENT UNITS
    # ============================================================================
    op.create_table(
        "ontario_forest_management_units",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fmu_id", sa.String(50), unique=True),
        sa.Column("fmu_name", sa.String(255), nullable=False),
        sa.Column("fmu_code", sa.String(10)),
        sa.Column("geometry", Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=False),
        sa.Column("area_ha", sa.Numeric()),
        sa.Column("management_company", sa.String(255)),
        sa.Column("plan_start_year", sa.Integer()),
        sa.Column("plan_end_year", sa.Integer()),
        sa.Column("plan_document_url", sa.String(255)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id")
    )

    op.create_index("idx_ont_fmus_geom", "ontario_forest_management_units", ["geometry"], postgresql_using="gist")
    op.create_index("idx_ont_fmus_name", "ontario_forest_management_units", ["fmu_name"], postgresql_using="gin", postgresql_ops={"fmu_name": "gin_trgm_ops"})
    op.create_index("idx_ont_fmus_code", "ontario_forest_management_units", ["fmu_code"])

    # ============================================================================
    # ONTARIO WATER BODIES
    # ============================================================================
    op.create_table(
        "ontario_waterbodies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("waterbody_id", sa.String(50), unique=True),
        sa.Column("waterbody_name", sa.String(255)),
        sa.Column("waterbody_type", sa.String(50)),  # Lake, River, Stream, Pond
        sa.Column("geometry", Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=False),
        sa.Column("surface_area_ha", sa.Numeric()),
        sa.Column("perimeter_km", sa.Numeric()),
        sa.Column("great_lake", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id")
    )

    op.create_index("idx_ont_water_geom", "ontario_waterbodies", ["geometry"], postgresql_using="gist")
    op.create_index("idx_ont_water_name", "ontario_waterbodies", ["waterbody_name"], postgresql_using="gin", postgresql_ops={"waterbody_name": "gin_trgm_ops"})
    op.create_index("idx_ont_water_type", "ontario_waterbodies", ["waterbody_type"])
    op.create_index("idx_ont_water_great_lake", "ontario_waterbodies", ["great_lake"], postgresql_where=sa.text("great_lake = true"))

    # ============================================================================
    # ONTARIO WETLANDS
    # ============================================================================
    op.create_table(
        "ontario_wetlands",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("wetland_id", sa.String(50), unique=True),
        sa.Column("wetland_name", sa.String(255)),
        sa.Column("geometry", Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=False),
        sa.Column("area_ha", sa.Numeric()),
        sa.Column("wetland_type", sa.String(50)),  # Marsh, Swamp, Bog, Fen
        sa.Column("provincial_significance", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("evaluated", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id")
    )

    op.create_index("idx_ont_wetlands_geom", "ontario_wetlands", ["geometry"], postgresql_using="gist")
    op.create_index("idx_ont_wetlands_name", "ontario_wetlands", ["wetland_name"], postgresql_using="gin", postgresql_ops={"wetland_name": "gin_trgm_ops"})
    op.create_index("idx_ont_wetlands_significant", "ontario_wetlands", ["provincial_significance"], postgresql_where=sa.text("provincial_significance = true"))

    # ============================================================================
    # ONTARIO SPECIES AT RISK (Sensitive - generalized locations)
    # ============================================================================
    op.create_table(
        "ontario_species_at_risk",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("occurrence_id", sa.String(50), unique=True),
        sa.Column("species_name", sa.String(255), nullable=False),
        sa.Column("scientific_name", sa.String(255)),
        sa.Column("saro_status", sa.String(50)),  # Endangered, Threatened, etc.
        sa.Column("last_observation_date", sa.Date()),
        sa.Column("geometry", Geometry(geometry_type="POINT", srid=4326)),  # GENERALIZED
        sa.Column("generalized_location", sa.String(255)),
        sa.Column("habitat_type", sa.String(100)),
        sa.Column("habitat_description", sa.Text()),
        sa.Column("data_sensitivity", sa.String(20), server_default=sa.text("'HIGH'")),
        sa.Column("access_restricted", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id")
    )

    op.create_index("idx_ont_species_geom", "ontario_species_at_risk", ["geometry"], postgresql_using="gist")
    op.create_index("idx_ont_species_name", "ontario_species_at_risk", ["species_name"], postgresql_using="gin", postgresql_ops={"species_name": "gin_trgm_ops"})
    op.create_index("idx_ont_species_status", "ontario_species_at_risk", ["saro_status"])

    # ============================================================================
    # UPDATE TRIGGERS
    # ============================================================================
    # Create trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Apply triggers to all tables
    tables = [
        "ontario_provincial_parks",
        "ontario_conservation_reserves",
        "ontario_conservation_authorities",
        "ontario_watersheds",
        "ontario_municipalities",
        "ontario_forest_management_units"
    ]

    for table in tables:
        op.execute(f"""
            CREATE TRIGGER update_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """)

    # ============================================================================
    # SEARCH FUNCTION
    # ============================================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION search_ontario_areas(
            search_query TEXT,
            area_types TEXT[] DEFAULT NULL,
            region VARCHAR DEFAULT NULL,
            limit_count INTEGER DEFAULT 10
        ) RETURNS TABLE (
            id INTEGER,
            name VARCHAR,
            type VARCHAR,
            subtype VARCHAR,
            geometry GEOMETRY,
            size_ha NUMERIC,
            relevance NUMERIC
        ) AS $$
        BEGIN
            RETURN QUERY
            -- Provincial Parks
            SELECT
                p.id,
                p.park_name::VARCHAR as name,
                'provincial_park'::VARCHAR as type,
                p.park_class::VARCHAR as subtype,
                p.geometry,
                p.size_ha,
                similarity(p.park_name, search_query) as relevance
            FROM ontario_provincial_parks p
            WHERE (area_types IS NULL OR 'provincial_park' = ANY(area_types))
                AND (p.park_name ILIKE '%' || search_query || '%'
                     OR similarity(p.park_name, search_query) > 0.3)

            UNION ALL

            -- Conservation Reserves
            SELECT
                r.id,
                r.reserve_name::VARCHAR as name,
                'conservation_reserve'::VARCHAR as type,
                'protected_area'::VARCHAR as subtype,
                r.geometry,
                r.size_ha,
                similarity(r.reserve_name, search_query) as relevance
            FROM ontario_conservation_reserves r
            WHERE (area_types IS NULL OR 'conservation_reserve' = ANY(area_types))
                AND (r.reserve_name ILIKE '%' || search_query || '%'
                     OR similarity(r.reserve_name, search_query) > 0.3)

            UNION ALL

            -- Conservation Authorities
            SELECT
                c.id,
                c.authority_name::VARCHAR as name,
                'conservation_authority'::VARCHAR as type,
                'watershed_management'::VARCHAR as subtype,
                c.geometry,
                c.jurisdiction_area_ha as size_ha,
                similarity(c.authority_name, search_query) as relevance
            FROM ontario_conservation_authorities c
            WHERE (area_types IS NULL OR 'conservation_authority' = ANY(area_types))
                AND (c.authority_name ILIKE '%' || search_query || '%'
                     OR c.acronym ILIKE '%' || search_query || '%'
                     OR similarity(c.authority_name, search_query) > 0.3)

            UNION ALL

            -- Municipalities
            SELECT
                m.id,
                m.municipality_name::VARCHAR as name,
                'municipality'::VARCHAR as type,
                m.municipality_type::VARCHAR as subtype,
                m.geometry,
                m.area_ha as size_ha,
                similarity(m.municipality_name, search_query) as relevance
            FROM ontario_municipalities m
            WHERE (area_types IS NULL OR 'municipality' = ANY(area_types))
                AND (m.municipality_name ILIKE '%' || search_query || '%'
                     OR similarity(m.municipality_name, search_query) > 0.3)

            ORDER BY relevance DESC
            LIMIT limit_count;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # ============================================================================
    # PROTECTED AREA COVERAGE FUNCTION
    # ============================================================================
    op.execute("""
        CREATE OR REPLACE FUNCTION calculate_protected_area_coverage(
            input_geometry GEOMETRY
        ) RETURNS TABLE (
            total_area_ha NUMERIC,
            protected_area_ha NUMERIC,
            coverage_percentage NUMERIC,
            park_count INTEGER,
            reserve_count INTEGER
        ) AS $$
        BEGIN
            RETURN QUERY
            WITH area_calc AS (
                SELECT ST_Area(input_geometry::geography) / 10000 as total_ha
            ),
            parks_intersect AS (
                SELECT
                    COUNT(*) as park_count,
                    SUM(ST_Area(ST_Intersection(p.geometry, input_geometry)::geography) / 10000) as park_area_ha
                FROM ontario_provincial_parks p
                WHERE ST_Intersects(p.geometry, input_geometry)
            ),
            reserves_intersect AS (
                SELECT
                    COUNT(*) as reserve_count,
                    SUM(ST_Area(ST_Intersection(r.geometry, input_geometry)::geography) / 10000) as reserve_area_ha
                FROM ontario_conservation_reserves r
                WHERE ST_Intersects(r.geometry, input_geometry)
            )
            SELECT
                a.total_ha,
                COALESCE(p.park_area_ha, 0) + COALESCE(r.reserve_area_ha, 0) as protected_ha,
                ((COALESCE(p.park_area_ha, 0) + COALESCE(r.reserve_area_ha, 0)) / a.total_ha * 100) as coverage_pct,
                p.park_count::INTEGER,
                r.reserve_count::INTEGER
            FROM area_calc a
            CROSS JOIN parks_intersect p
            CROSS JOIN reserves_intersect r;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # ============================================================================
    # TABLE COMMENTS
    # ============================================================================
    op.execute("COMMENT ON TABLE ontario_provincial_parks IS 'Ontario Provincial Parks with boundaries, classification, and facilities'")
    op.execute("COMMENT ON TABLE ontario_conservation_authorities IS 'Ontario Conservation Authorities managing watersheds and natural resources'")
    op.execute("COMMENT ON TABLE ontario_watersheds IS 'Watershed boundaries in Ontario'")
    op.execute("COMMENT ON TABLE ontario_municipalities IS 'Municipal boundaries in Ontario'")
    op.execute("COMMENT ON TABLE ontario_forest_management_units IS 'Forest Management Units for sustainable forestry'")
    op.execute("COMMENT ON TABLE ontario_species_at_risk IS 'Species at Risk occurrences (GENERALIZED locations for public access)'")
    op.execute("COMMENT ON FUNCTION search_ontario_areas IS 'Unified search across all Ontario area types with fuzzy matching'")
    op.execute("COMMENT ON FUNCTION calculate_protected_area_coverage IS 'Calculate protected area coverage for a given geometry'")


def downgrade() -> None:
    """Drop Ontario Nature Watch schema."""

    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS calculate_protected_area_coverage(GEOMETRY)")
    op.execute("DROP FUNCTION IF EXISTS search_ontario_areas(TEXT, TEXT[], VARCHAR, INTEGER)")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    # Drop tables (in reverse order of dependencies)
    op.drop_table("ontario_species_at_risk")
    op.drop_table("ontario_wetlands")
    op.drop_table("ontario_waterbodies")
    op.drop_table("ontario_forest_management_units")
    op.drop_table("ontario_municipalities")
    op.drop_table("ontario_watersheds")
    op.drop_table("ontario_conservation_authorities")
    op.drop_table("ontario_conservation_reserves")
    op.drop_table("ontario_provincial_parks")

    # Note: Not dropping extensions as they might be used by other parts of the system
