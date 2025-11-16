"""add ontario biodiversity and water quality tables

Revision ID: 002_ontario_biodiversity
Revises: 001_ontario_schema
Create Date: 2025-11-16 00:00:00.000000

This migration adds tables for Ontario environmental data integration:
- Biodiversity observations (iNaturalist, eBird, GBIF)
- Water quality monitoring (PWQMN)
- Forest resources inventory
- Supporting tables and views
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_ontario_biodiversity"
down_revision: Union[str, None] = "001_ontario_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create Ontario biodiversity and water quality tables."""

    # ============================================================================
    # BIODIVERSITY OBSERVATIONS - iNaturalist
    # ============================================================================
    op.create_table(
        "inat_observations",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("taxon_id", sa.Integer()),
        sa.Column("scientific_name", sa.String(255)),
        sa.Column("common_name", sa.String(255)),
        sa.Column("taxonomy_rank", sa.String(50)),
        sa.Column("iconic_taxon", sa.String(50)),
        sa.Column("observation_date", sa.Date()),
        sa.Column("observation_datetime", sa.DateTime(timezone=True)),
        sa.Column(
            "location", Geography(geometry_type="POINT", srid=4326), nullable=False
        ),
        sa.Column("place_name", sa.String(255)),
        sa.Column("positional_accuracy", sa.Float()),
        sa.Column(
            "quality_grade",
            sa.String(50),
            sa.CheckConstraint(
                "quality_grade IN ('research', 'needs_id', 'casual')",
                name="check_quality_grade",
            ),
        ),
        sa.Column("license", sa.String(50)),
        sa.Column("observer", sa.String(100)),
        sa.Column("photo_urls", postgresql.ARRAY(sa.Text())),
        sa.Column("identifications_count", sa.Integer(), server_default="0"),
        sa.Column("comments_count", sa.Integer(), server_default="0"),
        sa.Column("url", sa.String(500)),
        sa.Column("data_source", sa.String(50), server_default="iNaturalist"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for iNaturalist
    op.create_index(
        "idx_inat_location",
        "inat_observations",
        ["location"],
        postgresql_using="gist",
    )
    op.create_index("idx_inat_date", "inat_observations", ["observation_date"])
    op.create_index("idx_inat_taxon", "inat_observations", ["taxon_id"])
    op.create_index("idx_inat_quality", "inat_observations", ["quality_grade"])
    op.create_index(
        "idx_inat_scientific_name", "inat_observations", ["scientific_name"]
    )

    # ============================================================================
    # BIODIVERSITY OBSERVATIONS - eBird
    # ============================================================================
    op.create_table(
        "ebird_observations",
        sa.Column("submission_id", sa.String(50), nullable=False),
        sa.Column("species_code", sa.String(10)),
        sa.Column("common_name", sa.String(255)),
        sa.Column("scientific_name", sa.String(255)),
        sa.Column("observation_datetime", sa.DateTime(timezone=True)),
        sa.Column(
            "location", Geography(geometry_type="POINT", srid=4326), nullable=False
        ),
        sa.Column("location_name", sa.String(255)),
        sa.Column("location_id", sa.String(50)),
        sa.Column("count", sa.Integer()),
        sa.Column("obs_valid", sa.Boolean(), server_default="true"),
        sa.Column("obs_reviewed", sa.Boolean(), server_default="false"),
        sa.Column("url", sa.String(500)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("submission_id"),
    )

    # Indexes for eBird
    op.create_index(
        "idx_ebird_location", "ebird_observations", ["location"], postgresql_using="gist"
    )
    op.create_index(
        "idx_ebird_datetime", "ebird_observations", ["observation_datetime"]
    )
    op.create_index("idx_ebird_species", "ebird_observations", ["species_code"])
    op.create_index(
        "idx_ebird_scientific_name", "ebird_observations", ["scientific_name"]
    )

    # ============================================================================
    # BIODIVERSITY OBSERVATIONS - GBIF
    # ============================================================================
    op.create_table(
        "gbif_occurrences",
        sa.Column("gbif_key", sa.BigInteger(), nullable=False),
        sa.Column("dataset_key", sa.String(50)),
        sa.Column("scientific_name", sa.String(255)),
        sa.Column("kingdom", sa.String(100)),
        sa.Column("phylum", sa.String(100)),
        sa.Column("class_name", sa.String(100)),  # 'class' is reserved keyword
        sa.Column("family", sa.String(100)),
        sa.Column("genus", sa.String(100)),
        sa.Column("species", sa.String(255)),
        sa.Column("location", Geography(geometry_type="POINT", srid=4326)),
        sa.Column("coordinate_uncertainty", sa.Float()),
        sa.Column("event_date", sa.Date()),
        sa.Column("year", sa.Integer()),
        sa.Column("month", sa.Integer()),
        sa.Column("day", sa.Integer()),
        sa.Column("basis_of_record", sa.String(50)),
        sa.Column("institution_code", sa.String(100)),
        sa.Column("collection_code", sa.String(100)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("gbif_key"),
    )

    # Indexes for GBIF
    op.create_index(
        "idx_gbif_location", "gbif_occurrences", ["location"], postgresql_using="gist"
    )
    op.create_index("idx_gbif_date", "gbif_occurrences", ["event_date"])
    op.create_index("idx_gbif_species", "gbif_occurrences", ["scientific_name"])
    op.create_index("idx_gbif_year", "gbif_occurrences", ["year"])

    # ============================================================================
    # WATER QUALITY - PWQMN Stations
    # ============================================================================
    op.create_table(
        "pwqmn_stations",
        sa.Column("station_id", sa.String(20), nullable=False),
        sa.Column("station_name", sa.String(255)),
        sa.Column("water_body", sa.String(255)),
        sa.Column(
            "location", Geography(geometry_type="POINT", srid=4326), nullable=False
        ),
        sa.Column("drainage_area_km2", sa.Float()),
        sa.Column("conservation_authority", sa.String(100)),
        sa.Column("active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("station_id"),
    )

    # Indexes for PWQMN stations
    op.create_index(
        "idx_pwqmn_location", "pwqmn_stations", ["location"], postgresql_using="gist"
    )
    op.create_index("idx_pwqmn_waterbody", "pwqmn_stations", ["water_body"])
    op.create_index("idx_pwqmn_ca", "pwqmn_stations", ["conservation_authority"])

    # ============================================================================
    # WATER QUALITY - PWQMN Measurements
    # ============================================================================
    op.create_table(
        "pwqmn_measurements",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("station_id", sa.String(20), nullable=False),
        sa.Column("sample_date", sa.Date(), nullable=False),
        sa.Column("parameter_name", sa.String(100), nullable=False),
        sa.Column("value", sa.Float()),
        sa.Column("unit", sa.String(20)),
        sa.Column("mdl_flag", sa.String(10)),
        sa.Column("qa_flag", sa.String(10)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["station_id"], ["pwqmn_stations.station_id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "station_id",
            "sample_date",
            "parameter_name",
            name="uq_pwqmn_station_date_param",
        ),
    )

    # Indexes for PWQMN measurements
    op.create_index("idx_pwqmn_meas_date", "pwqmn_measurements", ["sample_date"])
    op.create_index("idx_pwqmn_meas_param", "pwqmn_measurements", ["parameter_name"])
    op.create_index(
        "idx_pwqmn_meas_station_date", "pwqmn_measurements", ["station_id", "sample_date"]
    )

    # ============================================================================
    # SPECIES CODES LOOKUP (for FRI and other datasets)
    # ============================================================================
    op.create_table(
        "species_codes",
        sa.Column("code", sa.String(10), nullable=False),
        sa.Column("scientific_name", sa.String(255)),
        sa.Column("common_name", sa.String(255)),
        sa.Column("species_type", sa.String(50)),  # tree, shrub, etc.
        sa.Column("source", sa.String(50)),  # FRI, other
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("code"),
    )

    # ============================================================================
    # MATERIALIZED VIEWS
    # ============================================================================

    # Unified biodiversity observations view
    op.execute(
        """
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
            url,
            created_at
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
            url,
            created_at
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
            NULL AS url,
            created_at
        FROM gbif_occurrences
        WHERE location IS NOT NULL;
        """
    )

    # Indexes on materialized view
    op.execute(
        "CREATE INDEX idx_bio_obs_location ON biodiversity_observations USING GIST(location);"
    )
    op.execute("CREATE INDEX idx_bio_obs_date ON biodiversity_observations(obs_date);")
    op.execute("CREATE INDEX idx_bio_obs_source ON biodiversity_observations(source);")
    op.execute(
        "CREATE INDEX idx_bio_obs_species ON biodiversity_observations(scientific_name);"
    )

    # Water quality summary view
    op.execute(
        """
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
        """
    )

    # Indexes on water quality summary view
    op.execute(
        "CREATE INDEX idx_wq_summary_location ON water_quality_summary USING GIST(location);"
    )
    op.execute(
        "CREATE INDEX idx_wq_summary_param ON water_quality_summary(parameter_name);"
    )
    op.execute(
        "CREATE INDEX idx_wq_summary_waterbody ON water_quality_summary(water_body);"
    )


def downgrade() -> None:
    """Drop Ontario biodiversity and water quality tables."""

    # Drop materialized views
    op.execute("DROP MATERIALIZED VIEW IF EXISTS water_quality_summary;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS biodiversity_observations;")

    # Drop tables in reverse order
    op.drop_table("species_codes")
    op.drop_table("pwqmn_measurements")
    op.drop_table("pwqmn_stations")
    op.drop_table("gbif_occurrences")
    op.drop_table("ebird_observations")
    op.drop_table("inat_observations")
