-- Williams Treaty Data Sources Schema
-- Migration: 002_williams_treaty_data.sql
-- Description: Create tables for water advisories, fire data, infrastructure projects, and community well-being data
-- Ported from: https://github.com/robertsoden/williams-treaties

-- Ensure PostGIS and extensions are enabled
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================================
-- FIRST NATIONS WATER ADVISORIES
-- ============================================================================
-- Tracks drinking water advisories for First Nations communities
-- Source: Indigenous Services Canada
CREATE TABLE IF NOT EXISTS ontario_water_advisories (
    id SERIAL PRIMARY KEY,
    advisory_id VARCHAR(100) UNIQUE,
    community_name VARCHAR(255) NOT NULL,
    first_nation VARCHAR(255),
    region VARCHAR(100), -- Ontario region
    geometry GEOMETRY(Point, 4326) NOT NULL,
    advisory_type VARCHAR(100), -- Boil Water Advisory, Do Not Consume, etc.
    advisory_date DATE NOT NULL,
    lift_date DATE, -- NULL if still active
    duration_days INTEGER, -- Calculated: days from advisory_date to lift_date or present
    is_active BOOLEAN DEFAULT TRUE,
    reason TEXT,
    water_system_name VARCHAR(255),
    population_affected INTEGER,
    data_source VARCHAR(100) DEFAULT 'Indigenous Services Canada',
    source_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for water advisories
CREATE INDEX idx_water_advisories_geom ON ontario_water_advisories USING GIST(geometry);
CREATE INDEX idx_water_advisories_community ON ontario_water_advisories USING GIN(community_name gin_trgm_ops);
CREATE INDEX idx_water_advisories_active ON ontario_water_advisories(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_water_advisories_type ON ontario_water_advisories(advisory_type);
CREATE INDEX idx_water_advisories_date ON ontario_water_advisories(advisory_date);

-- ============================================================================
-- ONTARIO FIRE INCIDENTS (Historical)
-- ============================================================================
-- Historical fire perimeter data from Ontario Ministry of Natural Resources
-- Source: Ontario GeoHub
CREATE TABLE IF NOT EXISTS ontario_fire_incidents (
    id SERIAL PRIMARY KEY,
    fire_id VARCHAR(100) UNIQUE,
    fire_number VARCHAR(50),
    fire_year INTEGER NOT NULL,
    fire_name VARCHAR(255),
    geometry GEOMETRY(MultiPolygon, 4326) NOT NULL, -- Fire perimeter
    point_geometry GEOMETRY(Point, 4326), -- Fire origin point
    ignition_date DATE,
    discovery_date DATE,
    under_control_date DATE,
    out_date DATE,
    area_ha NUMERIC, -- Burned area in hectares
    fire_cause VARCHAR(100), -- Lightning, Human, Unknown, etc.
    fire_region VARCHAR(100),
    fire_zone VARCHAR(50),
    fuel_type VARCHAR(100), -- Vegetation/fuel type
    initial_attack_success BOOLEAN,
    suppression_cost NUMERIC,
    data_source VARCHAR(100) DEFAULT 'Ontario MNRF',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for fire incidents
CREATE INDEX idx_fire_incidents_geom ON ontario_fire_incidents USING GIST(geometry);
CREATE INDEX idx_fire_incidents_point_geom ON ontario_fire_incidents USING GIST(point_geometry);
CREATE INDEX idx_fire_incidents_year ON ontario_fire_incidents(fire_year);
CREATE INDEX idx_fire_incidents_date ON ontario_fire_incidents(ignition_date);
CREATE INDEX idx_fire_incidents_cause ON ontario_fire_incidents(fire_cause);
CREATE INDEX idx_fire_incidents_region ON ontario_fire_incidents(fire_region);

-- ============================================================================
-- FIRE DANGER RATINGS (Current/Recent)
-- ============================================================================
-- Current fire weather and danger ratings from Canadian Wildland Fire Information System
-- Source: CWFIS (Natural Resources Canada)
CREATE TABLE IF NOT EXISTS ontario_fire_danger (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(50),
    station_name VARCHAR(255),
    geometry GEOMETRY(Point, 4326) NOT NULL,
    observation_date DATE NOT NULL,
    observation_time TIME,
    temperature_c NUMERIC,
    relative_humidity NUMERIC,
    wind_speed_kmh NUMERIC,
    precipitation_mm NUMERIC,
    fwi NUMERIC, -- Fire Weather Index
    ffmc NUMERIC, -- Fine Fuel Moisture Code
    dmc NUMERIC, -- Duff Moisture Code
    dc NUMERIC, -- Drought Code
    isi NUMERIC, -- Initial Spread Index
    bui NUMERIC, -- Buildup Index
    danger_class VARCHAR(20), -- Low, Moderate, High, Very High, Extreme
    data_source VARCHAR(100) DEFAULT 'CWFIS',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(station_id, observation_date)
);

-- Indexes for fire danger
CREATE INDEX idx_fire_danger_geom ON ontario_fire_danger USING GIST(geometry);
CREATE INDEX idx_fire_danger_station ON ontario_fire_danger(station_id);
CREATE INDEX idx_fire_danger_date ON ontario_fire_danger(observation_date DESC);
CREATE INDEX idx_fire_danger_class ON ontario_fire_danger(danger_class);

-- ============================================================================
-- INDIGENOUS INFRASTRUCTURE PROJECTS
-- ============================================================================
-- Infrastructure projects in First Nations communities
-- Source: Indigenous Community Infrastructure Management (ICIM)
CREATE TABLE IF NOT EXISTS ontario_indigenous_infrastructure (
    id SERIAL PRIMARY KEY,
    project_id VARCHAR(100) UNIQUE,
    community_name VARCHAR(255) NOT NULL,
    first_nation VARCHAR(255),
    geometry GEOMETRY(Point, 4326) NOT NULL,
    project_name VARCHAR(500),
    infrastructure_category VARCHAR(100), -- Education, Health, Housing, Water/Wastewater, etc.
    infrastructure_type VARCHAR(200),
    project_status VARCHAR(100), -- Completed, In Progress, Planned, etc.
    project_start_date DATE,
    project_completion_date DATE,
    funding_amount NUMERIC,
    funding_source VARCHAR(255),
    project_description TEXT,
    asset_condition VARCHAR(50), -- Good, Fair, Poor
    within_williams_treaty BOOLEAN DEFAULT FALSE,
    data_source VARCHAR(100) DEFAULT 'ICIM',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for infrastructure
CREATE INDEX idx_infrastructure_geom ON ontario_indigenous_infrastructure USING GIST(geometry);
CREATE INDEX idx_infrastructure_community ON ontario_indigenous_infrastructure USING GIN(community_name gin_trgm_ops);
CREATE INDEX idx_infrastructure_category ON ontario_indigenous_infrastructure(infrastructure_category);
CREATE INDEX idx_infrastructure_status ON ontario_indigenous_infrastructure(project_status);
CREATE INDEX idx_infrastructure_williams ON ontario_indigenous_infrastructure(within_williams_treaty) WHERE within_williams_treaty = TRUE;

-- ============================================================================
-- COMMUNITY WELL-BEING INDEX
-- ============================================================================
-- Community Well-Being (CWB) scores for First Nations and other communities
-- Source: Indigenous Services Canada / Statistics Canada
CREATE TABLE IF NOT EXISTS ontario_community_wellbeing (
    id SERIAL PRIMARY KEY,
    csd_code VARCHAR(20) UNIQUE, -- Census Subdivision code
    community_name VARCHAR(255) NOT NULL,
    community_type VARCHAR(100), -- First Nation, Inuit, Non-Indigenous, etc.
    geometry GEOMETRY(MultiPolygon, 4326) NOT NULL,
    census_year INTEGER NOT NULL,
    population INTEGER,
    cwb_score NUMERIC, -- Overall CWB score (0-100)
    education_score NUMERIC, -- Education component (0-100)
    labour_force_score NUMERIC, -- Labour force component (0-100)
    income_score NUMERIC, -- Income component (0-100)
    housing_score NUMERIC, -- Housing component (0-100)
    province VARCHAR(50) DEFAULT 'Ontario',
    within_williams_treaty BOOLEAN DEFAULT FALSE,
    data_source VARCHAR(100) DEFAULT 'ISC/StatCan',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for community well-being
CREATE INDEX idx_cwb_geom ON ontario_community_wellbeing USING GIST(geometry);
CREATE INDEX idx_cwb_community ON ontario_community_wellbeing USING GIN(community_name gin_trgm_ops);
CREATE INDEX idx_cwb_type ON ontario_community_wellbeing(community_type);
CREATE INDEX idx_cwb_year ON ontario_community_wellbeing(census_year);
CREATE INDEX idx_cwb_score ON ontario_community_wellbeing(cwb_score);
CREATE INDEX idx_cwb_williams ON ontario_community_wellbeing(within_williams_treaty) WHERE within_williams_treaty = TRUE;

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to calculate active water advisory duration
CREATE OR REPLACE FUNCTION calculate_advisory_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.lift_date IS NOT NULL THEN
        NEW.duration_days := NEW.lift_date - NEW.advisory_date;
        NEW.is_active := FALSE;
    ELSE
        NEW.duration_days := CURRENT_DATE - NEW.advisory_date;
        NEW.is_active := TRUE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically calculate advisory duration
CREATE TRIGGER update_advisory_duration
    BEFORE INSERT OR UPDATE ON ontario_water_advisories
    FOR EACH ROW
    EXECUTE FUNCTION calculate_advisory_duration();

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers to all new tables
CREATE TRIGGER update_water_advisories_updated_at
    BEFORE UPDATE ON ontario_water_advisories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fire_incidents_updated_at
    BEFORE UPDATE ON ontario_fire_incidents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fire_danger_updated_at
    BEFORE UPDATE ON ontario_fire_danger
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_infrastructure_updated_at
    BEFORE UPDATE ON ontario_indigenous_infrastructure
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cwb_updated_at
    BEFORE UPDATE ON ontario_community_wellbeing
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Active water advisories
CREATE OR REPLACE VIEW active_water_advisories AS
SELECT
    advisory_id,
    community_name,
    first_nation,
    advisory_type,
    advisory_date,
    duration_days,
    population_affected,
    geometry
FROM ontario_water_advisories
WHERE is_active = TRUE
ORDER BY duration_days DESC;

-- Recent fire incidents (last 10 years)
CREATE OR REPLACE VIEW recent_fire_incidents AS
SELECT
    fire_id,
    fire_number,
    fire_year,
    fire_name,
    area_ha,
    fire_cause,
    ignition_date,
    geometry
FROM ontario_fire_incidents
WHERE fire_year >= EXTRACT(YEAR FROM CURRENT_DATE) - 10
ORDER BY fire_year DESC, area_ha DESC;

-- Infrastructure projects within Williams Treaty territories
CREATE OR REPLACE VIEW williams_treaty_infrastructure AS
SELECT
    project_id,
    community_name,
    project_name,
    infrastructure_category,
    project_status,
    funding_amount,
    geometry
FROM ontario_indigenous_infrastructure
WHERE within_williams_treaty = TRUE
ORDER BY community_name, infrastructure_category;

-- First Nations community well-being scores
CREATE OR REPLACE VIEW first_nations_cwb AS
SELECT
    csd_code,
    community_name,
    census_year,
    population,
    cwb_score,
    education_score,
    labour_force_score,
    income_score,
    housing_score,
    within_williams_treaty,
    geometry
FROM ontario_community_wellbeing
WHERE community_type LIKE '%First Nation%'
ORDER BY census_year DESC, cwb_score ASC;

-- ============================================================================
-- GRANTS (Adjust based on your user setup)
-- ============================================================================
-- Example: GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
-- Example: GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app_user;
