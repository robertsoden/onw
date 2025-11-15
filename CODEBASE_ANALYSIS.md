# Global Nature Watch (Project Zeno) - Codebase Comprehensive Analysis

## Executive Summary

**Project Name:** Global Nature Watch (Project Zeno)
**Current Focus:** Global geospatial environmental data analysis and visualization  
**Primary Purpose:** LLM-powered agent that provides natural language interface to Global Forest Watch (GFW) analytics APIs and other environmental datasets

This project is a sophisticated LangGraph-based ReAct agent system designed to democratize access to geospatial environmental data through conversational AI, combining advanced NLP with spatial data management.

---

## 1. PROJECT PURPOSE AND GEOGRAPHIC FOCUS

### Current Purpose
- **Primary Mission:** Provide conversational access to global environmental datasets with geospatial analysis capabilities
- **Core Functionality:** Transform natural language queries about land use, forest cover, deforestation, and ecosystem changes into data-driven insights
- **Development Focus:** Environmental monitoring, deforestation tracking, land-use change detection, and carbon flux estimation

### Geographic Coverage
- **Current Scope:** Global (all countries and territories)
- **Administrative Hierarchy:** 6 levels of GADM (Geospatial Data Abstraction Library) subdivisions
  - Country (ADM0)
  - State/Province (ADM1)
  - District/County (ADM2)
  - Municipality (ADM3)
  - Locality (ADM4)
  - Neighborhood (ADM5)

### Data Sources Integration
- **Global Forest Watch (GFW) Analytics API** - Primary data source
- **GADM (v4.1)** - Administrative boundaries
- **Key Biodiversity Areas (KBA)** - Conservation areas
- **WDPA** - World Database on Protected Areas
- **LandMark Database** - Indigenous and Community Lands
- **Custom User-Defined Areas** - User-specific regions of interest

---

## 2. MAIN COMPONENTS

### 2.1 Agent Architecture (LangGraph-based ReAct Agent)
**Location:** `/src/agents/agents.py`

Core Components:
- **Framework:** LangGraph with ReAct (Reasoning and Acting) pattern
- **LLM Models:** Pluggable architecture supporting:
  - Claude Sonnet (primary, configurable)
  - Google Gemini
  - GPT-4
- **State Management:** Persistent conversation state via PostgreSQL checkpointing
- **Tool Execution:** Sequential one-at-a-time (prevents race conditions)

### 2.2 Core Tools (5 Specialized Tools)

#### Tool 1: `pick_aoi` (Area of Interest Selection)
**Location:** `/src/tools/pick_aoi.py`

Features:
- Fuzzy text matching using PostgreSQL trigram similarity
- Multi-source geometric search (GADM, KBA, WDPA, LandMark, Custom)
- LLM-based disambiguation for ambiguous place names
- Translation of non-English place names to English
- Subregion filtering and hierarchical selection
- Database queries: PostGIS with spatial indexing

#### Tool 2: `pick_dataset` (Dataset Selection via RAG)
**Location:** `/src/tools/pick_dataset.py`

Features:
- Retrieval-Augmented Generation (RAG) using OpenAI embeddings
- Vector similarity search against dataset documentation
- LLM evaluation of candidate datasets
- Context layer selection within datasets
- Date range validation with warnings

#### Tool 3: `pull_data` (Data Retrieval Orchestrator)
**Location:** `/src/tools/pull_data.py`

Architecture:
- Strategy pattern with pluggable data handlers
- **Current Handler:** AnalyticsHandler (GFW Analytics API)
- Multi-AOI data pulling with caching
- Error handling and validation
- Support for multiple data sources

#### Tool 4: `generate_insights` (Analysis & Visualization)
**Location:** `/src/tools/generate_insights.py`

Features:
- Data preprocessing and CSV conversion
- LLM analysis with dataset-specific guidelines
- Chart.js/Recharts-compatible JSON output
- Support for multiple chart types:
  - Line, bar, stacked-bar, pie, area, scatter, table
- Follow-up suggestion generation

#### Tool 5: `get_capabilities` (Self-Description)
**Location:** `/src/tools/get_capabilities.py`

Features:
- Dynamic information about agent capabilities
- Lists available datasets and their metadata
- Describes supported geographic scopes
- Prevents hallucination about capabilities

### 2.3 Data Models and Database Layer

#### Database Tables
**Location:** `/src/api/data_models.py`

Key Tables:
- `geometries_gadm` - Administrative boundaries (GADM v4.1)
- `geometries_kba` - Key Biodiversity Areas
- `geometries_landmark` - Indigenous and Community Lands
- `geometries_wdpa` - Protected Areas
- `custom_areas` - User-defined geographic areas
- `users` - User accounts with profiles
- `threads` - Conversation threads
- `ratings` - User feedback/ratings
- `daily_usage` - Usage tracking

#### Database Infrastructure
- **PostGIS:** Spatial data storage and querying
- **Async SQLAlchemy:** Async ORM for database operations
- **Connection Pooling:** Async connection management
- **Checkpointing:** LangGraph checkpoint storage in PostgreSQL

### 2.4 Data Ingestion Pipelines

**Location:** `/src/ingest/`

Ingestion Scripts:
1. **GADM Ingestion** (`ingest_gadm.py`)
   - Downloads GADM v4.1 (140+ MB)
   - Processes all 6 administrative levels
   - Chunked ingestion for memory efficiency
   - Creates spatial and text search indexes

2. **KBA Ingestion** (`ingest_kba.py`)
   - Source: S3 NDJSON format
   - Creates site records with biodiversity data
   - Spatial indexing for geometry searches

3. **WDPA Ingestion** (`ingest_wdpa.py`)
   - World Database on Protected Areas
   - Protected area boundaries and metadata

4. **LandMark Ingestion** (`ingest_landmark.py`)
   - Indigenous Peoples and Community Lands
   - Cultural significance boundaries

5. **Dataset Embedding** (`embed_datasets.py`)
   - Creates vector embeddings for RAG system
   - Uses OpenAI embeddings API
   - Stores in Chroma vector database

---

## 3. GEOGRAPHIC CONFIGURATION AND TERRITORY SYSTEM

### Current Territory Structure

#### GADM-Based Administrative Hierarchy
```
Country (gadm_id: "XXX")
  ├─ State/Province (gadm_id: "XXX.1")
  │   ├─ District/County (gadm_id: "XXX.1.1")
  │   │   ├─ Municipality (gadm_id: "XXX.1.1.1")
  │   │   │   ├─ Locality (gadm_id: "XXX.1.1.1.1")
  │   │   │   │   └─ Neighborhood (gadm_id: "XXX.1.1.1.1.1")
```

**ID Format:** Hierarchical dot notation (e.g., "IND.26_1" = Odisha, India)

#### Source Mapping
**Location:** `/src/utils/geocoding_helpers.py`

```python
SOURCE_ID_MAPPING = {
    "kba": {"table": "geometries_kba", "id_column": "sitrecid"},
    "landmark": {"table": "geometries_landmark", "id_column": "landmark_id"},
    "wdpa": {"table": "geometries_wdpa", "id_column": "wdpa_pid"},
    "gadm": {"table": "geometries_gadm", "id_column": "gadm_id"},
    "custom": {"table": "custom_areas", "id_column": "id"},
}
```

#### Subregion Type Mapping
Supported subregion types:
- **Administrative:** country, state, district, municipality, locality, neighbourhood
- **Conservation:** kba (Key Biodiversity Area), wdpa (Protected Area)
- **Cultural:** landmark (Indigenous/Community Land)
- **Custom:** custom-area (user-defined)

---

## 4. SPATIAL DATA SOURCES AND INTEGRATION

### Primary Data Sources

#### 1. GADM (Global Administrative Divisions)
- **Version:** 4.1
- **Coverage:** 140+ countries
- **Resolution:** 6 administrative levels
- **Format:** GeoPackage (GPKG)
- **License:** CC-BY-4.0
- **URL:** https://geodata.ucdavis.edu/gadm/gadm4.1/

#### 2. Global Forest Watch Datasets
Integrated via `/src/tools/analytics_datasets.yml`:

**Dataset ID 0:** Global All Ecosystem Disturbance Alerts (DIST-ALERT)
- Resolution: 30×30 meters
- Update: Weekly (underlying data daily)
- Coverage: Global
- API: `/v0/land_change/dist_alerts/analytics`

**Dataset ID 1:** Global Land Cover (2015-2024)
- Resolution: 30×30 meters
- Coverage: Global
- Annual snapshots
- Land cover classes: 9 types

**Dataset ID 2:** Global Natural/Semi-Natural Grassland Extent
- Resolution: 30×30 meters
- Period: 2000-2022 (annual)
- Global coverage

**Dataset ID 3:** SBTN Natural Lands Map
- Year: 2020 (fixed)
- Resolution: 30×30 meters
- Binary: natural vs non-natural classification

**Dataset ID 4:** Tree Cover Loss (Hansen/UMD/GLAD)
- Period: 2001-2024 (annual)
- Resolution: 30×30 meters
- Includes GHG emissions (MgCO2e)

**Dataset ID 5:** Tree Cover Gain
- Period: 2000-2020 (5-year intervals)
- Resolution: 30×30 meters
- Cumulative layer

**Dataset ID 6:** Forest Greenhouse Gas Net Flux
- Period: 2001-2024 (annual averages)
- Resolution: 30×30 meters
- Balance between emissions and removals

**Dataset ID 7:** Tree Cover (Year 2000 baseline)
- Fixed baseline: 2000
- Resolution: 30×30 meters

**Dataset ID 8:** Tree Cover Loss by Dominant Driver
- Period: 2001-2024
- Resolution: ~1 km (0.01 degree)
- Driver classes: 7 types
- Sources: WRI + Google DeepMind

**Dataset ID 9:** Deforestation (sLUC) Emission Factors
- Period: 2020-2024 reporting (2001-2020 assessment)
- Crop-specific factors
- Administrative scales: ADM0, ADM1, ADM2

#### 3. Key Biodiversity Areas (KBA)
- **Source:** Global database
- **Format:** S3 NDJSON (`s3://ndjson-layers/KBAsGlobal_2024_September_03_POL.ndjson`)
- **Coverage:** Critical biodiversity sites globally
- **ID Column:** sitrecid

#### 4. Protected Areas (WDPA)
- **Name:** World Database on Protected Areas
- **Global coverage of protected and conservation areas

#### 5. Indigenous and Community Lands
- **Source:** LandMark database
- **Coverage:** IPCLC (Indigenous Peoples' and Community Lands and Territories)

#### 6. Custom User-Defined Areas
- **Storage:** PostgreSQL JSONB geometries
- **Format:** GeoJSON
- **Per-User:** Isolated by user_id
- **Types:** Single or multiple geometries (GeometryCollection)

### Data API Integration
**Location:** `/src/tools/data_handlers/analytics_handler.py`

- **Primary API:** GFW Analytics API
- **Base Configuration:** Environment-based (`EOAPI_BASE_URL`)
- **Authentication:** WRI API credentials (`WRI_API_KEY`, `WRI_BEARER_TOKEN`)
- **Rate Limiting:** Handled by client library
- **Data Format:** JSON responses with spatial aggregation

### Spatial Database Features
- **PostGIS Extension:** Full spatial SQL support
- **Spatial Indexes:** GiST indexes on geometry columns
- **Text Search:** GIN indexes on name columns for trigram similarity
- **Fuzzy Matching:** PostgreSQL `pg_trgm` extension with configurable thresholds

---

## 5. TRAINING DATA AND MODEL CONFIGURATIONS

### Configuration Files

#### Environment Configuration
**Location:** `.env.example`

Key Configuration Variables:
```
# LLM Models
MODEL=gemini (default: Claude Sonnet alternatives)
SMALL_MODEL=gemini-flash

# Database
DATABASE_URL=postgresql+asyncpg://...
TEST_DATABASE_URL=postgresql+asyncpg://...zeno-db_test

# API Services
EOAPI_BASE_URL=https://eoapi.staging.globalnaturewatch.org
WRI_API_KEY=<wri-api-key>
WRI_BEARER_TOKEN=<wri-bearer-token>

# LLM APIs
OPENAI_API_KEY=<openai-api-key>
ANTHROPIC_API_KEY=<anthropic-api-key>
GOOGLE_API_KEY=<google-api-key>

# Langfuse (Observability)
LANGFUSE_SECRET_KEY=<langfuse-secret-key>
LANGFUSE_PUBLIC_KEY=<langfuse-public-key>
LANGFUSE_HOST=http://localhost:3000

# Frontend
MAPBOX_API_TOKEN=<mapbox-api-key>
STREAMLIT_URL=http://localhost:8501

# Dataset Embeddings
DATASET_EMBEDDINGS_DB=zeno-docs-openai-index-v4
```

#### Datasets Configuration
**Location:** `/src/tools/analytics_datasets.yml`

YAML-based dataset metadata including:
- dataset_id and dataset_name
- Geographic coverage and resolution
- Update frequency and content dates
- Context layers available
- Analytics API endpoints
- Prompt instructions for LLM
- Methodology documentation
- Cautions and limitations
- Providers and citations

#### API Settings
**Location:** `/src/utils/config.py`

Configuration Parameters:
```python
class APISettings:
    admin_user_daily_quota: int = 100
    regular_user_daily_quota: int = 25
    pro_user_daily_quota: int = 50
    machine_user_daily_quota: int = 99999
    anonymous_user_daily_quota: int = 10
    ip_address_daily_quota: int = 50
    enable_quota_checking: bool = True
```

#### User Profile Configuration
**Location:** `/src/user_profile_configs/`

Modules:
- `countries.py` - ISO 3166-1 country codes (all 250+ countries)
- `sectors.py` - Industry sectors and job roles
- `gis_expertise.py` - GIS skill levels
- `languages.py` - Supported languages
- `topics.py` - Environmental topics of interest

---

## 6. EVALUATION DATASETS AND STRUCTURE

### Test and Evaluation Framework
**Location:** `/tests/` and `/experiments/`

#### E2E Test Dataset
**File:** `/experiments/e2e_test_dataset.csv`

Test Case Structure:
```csv
query,expected_aoi_id,expected_aoi_name,expected_subregion,
expected_aoi_subtype,expected_aoi_source,expected_dataset_id,
expected_dataset_name,expected_context_layer,expected_start_date,
expected_end_date,expected_answer,test_group,priority,status
```

Test Categories:
- **GADM Tests:** Tests for admin boundaries at levels 0-5
- **KBA Tests:** Key Biodiversity Area selection
- **Dataset Identification:** 10+ datasets across scales
- **Data Interpretation:** Answer quality evaluation
- **Investigator Tests:** Complex reasoning scenarios

#### Test Group Organization
**CSV Files in `/experiments/`:**
1. `Zeno test dataset(S2 GADM 0-1).csv` - Country and state tests
2. `Zeno test dataset(S2 GADM 2).csv` - District-level tests
3. `Zeno test dataset(S2 GADM 3).csv` - Municipality-level tests
4. `Zeno test dataset(S2 GADM 4).csv` - Locality-level tests
5. `Zeno test dataset(S2 T1 Dataset ID).csv` - Dataset identification
6. `Zeno test dataset(S5 T2-01 Investigator).csv` - Complex reasoning
7. `Zeno test dataset(S5 T2-02 Investigator).csv` - Data analysis

### Evaluation Metrics
**Location:** `/tests/agent/tool_evaluators.py` and `/tests/agent/e2e/`

Evaluation Dimensions:
1. **AOI Accuracy:** Expected vs actual location ID, name, subtype, source
2. **Dataset Selection:** Expected vs actual dataset ID and context layers
3. **Data Pull:** Start/end date accuracy, row counts, data availability
4. **Answer Quality:** Semantic similarity and correctness
5. **Overall Score:** Composite weighted metric

### Test Execution Framework
**Location:** `/tests/agent/e2e/config.py`

Configuration Options:
```python
class TestConfig:
    test_mode: str  # "local" or "api"
    langfuse_dataset: Optional[str]  # Langfuse dataset for cloud-based evals
    sample_size: int  # 1 (single) or -1 (all)
    test_file: str  # CSV test file path
    output_filename: Optional[str]
    num_workers: int  # Parallel test execution
```

Test Output Structure:
- `*_detailed.csv` - Full evaluation results with scores
- `*_summary.csv` - Aggregated metrics

---

## 7. KEY CONFIGURATION FILES FOR GEOGRAPHIC ADAPTATION

### Critical Files to Modify for New Territory

#### 1. **Geography Database Initialization**
- **File:** `/src/ingest/ingest_gadm.py`
- **Change:** If using non-GADM boundaries, create similar script
- **Impact:** Populates `geometries_gadm` table with territory boundaries

#### 2. **Dataset Configuration**
- **File:** `/src/tools/analytics_datasets.yml`
- **Change:** Update geographic coverage for each dataset
- **Example:** Williams Treaty Territory specific imagery endpoints
- **Impact:** Dataset selection and availability checking

#### 3. **Geocoding Helpers**
- **File:** `/src/utils/geocoding_helpers.py`
- **Change:** Add territory-specific ID mappings if not in GADM
- **Current Mappings:** 
  - Source tables
  - ID columns
  - Subtype mappings
- **Impact:** AOI selection and geometry queries

#### 4. **User Profile Countries**
- **File:** `/src/user_profile_configs/countries.py`
- **Change:** Add territory if not standard ISO country
- **Current:** All ISO 3166-1 countries plus custom entries
- **Impact:** User profile filtering by region

#### 5. **Analytics Datasets Metadata**
- **File:** `/src/tools/analytics_datasets.yml` (detailed)
- **Change:** Territory-specific coverage statements
- **Key Fields:**
  - `geographic_coverage`: Describe territory coverage
  - `analytics_api_endpoint`: Territory-specific endpoints
  - `start_date`/`end_date`: Data availability windows
  - `prompt_instructions`: Territory-specific guidance

#### 6. **Environment Configuration**
- **File:** `.env` / `.env.local`
- **Change:** Territory-specific API keys and endpoints
- **Variables:**
  - `EOAPI_BASE_URL`: Earth Observation API for imagery
  - Dataset-specific API credentials

#### 7. **Custom Area Support**
- **File:** `/src/api/data_models.py` (CustomAreaOrm table)
- **Current:** Full support for user-defined geometries
- **Change:** Can store Williams Treaty Territory GeoJSON directly
- **No code change needed** - store as custom areas

### Database Migration Files
**Location:** `/db/alembic/versions/`

- Manage schema changes for new tables
- Track geometry column additions
- Version control for spatial indexes

---

## 8. CODEBASE STRUCTURE OVERVIEW

```
project-zeno/
├── src/
│   ├── agents/              # LangGraph agent implementation
│   │   └── agents.py        # ReAct agent with tool definitions
│   ├── api/                 # FastAPI application
│   │   ├── app.py          # Main API routes
│   │   ├── data_models.py  # SQLAlchemy ORM models
│   │   ├── schemas.py      # Pydantic API schemas
│   │   └── auth/           # Authentication and authorization
│   ├── tools/              # Core agent tools
│   │   ├── pick_aoi.py     # Geographic selection tool
│   │   ├── pick_dataset.py # Dataset selection via RAG
│   │   ├── pull_data.py    # Data retrieval orchestrator
│   │   ├── generate_insights.py  # Analysis and visualization
│   │   ├── get_capabilities.py   # Agent self-description
│   │   ├── analytics_datasets.yml # Dataset metadata
│   │   ├── data_handlers/  # Data source handlers
│   │   │   ├── base.py     # Handler interface
│   │   │   └── analytics_handler.py  # GFW API handler
│   │   └── code_executors/ # Code execution engines
│   ├── ingest/             # Data ingestion pipelines
│   │   ├── ingest_gadm.py
│   │   ├── ingest_kba.py
│   │   ├── ingest_wdpa.py
│   │   ├── ingest_landmark.py
│   │   ├── embed_datasets.py
│   │   └── utils.py        # Shared ingestion utilities
│   ├── frontend/           # Streamlit UI
│   │   ├── app.py          # Main frontend
│   │   ├── pages/
│   │   └── utils.py
│   ├── graph/              # LangGraph state definitions
│   │   └── state.py
│   ├── user_profile_configs/  # User profile options
│   │   ├── countries.py
│   │   ├── sectors.py
│   │   ├── gis_expertise.py
│   │   ├── languages.py
│   │   └── topics.py
│   ├── utils/              # Shared utilities
│   │   ├── config.py       # Configuration management
│   │   ├── database.py     # Database connection pooling
│   │   ├── geocoding_helpers.py  # Geographic utilities
│   │   ├── llms.py         # LLM initialization
│   │   ├── env_loader.py   # Environment variables
│   │   └── logging_config.py    # Structured logging
│   └── cli.py              # Command-line interface
├── db/
│   ├── alembic/            # Database migrations
│   │   ├── env.py
│   │   ├── alembic.ini
│   │   └── versions/       # Migration scripts
│   ├── Dockerfile
│   └── entrypoint.sh
├── tests/
│   ├── api/                # API endpoint tests
│   ├── agent/              # Agent tests
│   │   ├── e2e/           # End-to-end tests
│   │   │   ├── config.py  # Test configuration
│   │   │   └── core.py    # Test execution
│   │   └── tool_evaluators.py
│   └── tools/              # Individual tool tests
├── experiments/            # Evaluation experiments
│   ├── e2e_test_dataset.csv
│   ├── eval_utils.py
│   ├── eval_gadm.py
│   ├── eval_dataset_identification.py
│   ├── eval_data_interpretation.py
│   └── eval_investi_gator.py
├── docs/
│   ├── AGENT_ARCHITECTURE.md
│   ├── CLI.md
│   └── DEPLOYMENT_PHASES.md
├── nbs/                    # Jupyter notebooks for development
├── rag/                    # RAG-related utilities
├── stac/                   # STAC catalog integration
├── docker-compose.yaml     # Local development setup
├── docker-compose.dev.yaml
├── Dockerfile
├── pyproject.toml          # Python dependencies
├── Makefile                # Development commands
├── .env.example            # Example environment config
└── README.md               # Project documentation
```

---

## 9. TECHNOLOGY STACK

### Core Dependencies
- **LangChain:** 0.3.26+ (LLM framework)
- **LangGraph:** 0.5.4+ (Agent orchestration)
- **FastAPI:** 0.116.1+ (Web framework)
- **SQLAlchemy:** 2.0.41+ (ORM)
- **PostGIS:** Spatial database extension
- **Pydantic:** 2.11.7+ (Data validation)

### Data Processing
- **GeoPandas:** 1.0.1 (Geospatial data)
- **Fiona:** 1.10.1 (Geospatial I/O)
- **Pandas:** 2.2.3 (Data manipulation)
- **Rio-STAC:** 0.11.0 (STAC catalog access)

### Machine Learning & Embeddings
- **Chroma:** Vector storage for RAG
- **OpenAI Embeddings:** Semantic search

### Infrastructure
- **PostgreSQL:** 12+ (primary database)
- **PostGIS:** 3.0+ (spatial extension)
- **Langfuse:** 3.3.4 (LLM observability)
- **Docker & Docker Compose:** Container orchestration

### LLM Support
- Claude (Claude Sonnet, Haiku) - Anthropic
- Google Gemini (Gemini, Gemini Flash)
- GPT-4 - OpenAI
- Pluggable architecture for others

---

## 10. ADAPTATION PATHWAY FOR WILLIAMS TREATY TERRITORY

### Strategic Approach

For adapting this system to Williams Treaty Territory in Canada:

1. **Geospatial Data Layer**
   - Create Williams Treaty Territory boundary (GeoJSON/GeoPackage)
   - Store in `custom_areas` table or new `geometries_williams_treaty` table
   - Assign unique ID for reference

2. **Dataset Integration**
   - Verify which GFW datasets cover Ontario/Canada region
   - Add territory-specific context to dataset descriptions
   - Adjust date ranges based on available data

3. **AOI Selection**
   - Add Williams Treaty Territory to pickable locations
   - Include with existing GADM country/province options
   - Support as parent region for subregion queries

4. **Configuration Updates**
   - Add "Williams Treaty Territory" to countries.py or create new region config
   - Update analytics_datasets.yml with territory-specific coverage
   - Configure API endpoints for territory-specific data retrieval

5. **User Profiling**
   - Add territory option to user preference configuration
   - Create custom sectors/roles if Indigenous-specific

6. **Testing & Evaluation**
   - Create test cases for territory AOI selection
   - Validate dataset queries return expected data
   - Build evaluation dataset for territory-specific queries

---

## Summary

This codebase represents a comprehensive geospatial AI system with:
- **Global scope** supporting 140+ countries and multiple geographic hierarchies
- **Extensible architecture** allowing territory-specific customization
- **Production-ready** with comprehensive testing, monitoring, and configuration management
- **Modular design** enabling isolated changes for new geographic areas without affecting global functionality

The system is well-positioned for adaptation to specific territories like Williams Treaty Territory through configuration changes rather than code rewrites.
