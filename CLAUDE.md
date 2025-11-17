# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Global Nature Watch** (project-zeno) is an LLM-powered agent that provides a language interface for geospatial environmental data. The core is a ReAct agent implemented in LangGraph that can:
- Search for areas of interest (protected areas, First Nations territories, administrative boundaries)
- Select appropriate environmental datasets using RAG
- Retrieve statistics from analytics APIs
- Generate insights and visualizations

The system uses **agent routing** to switch between a global agent and an Ontario-specific agent based on query context.

## Architecture

### Agent System
- **Framework**: LangGraph with ReAct pattern
- **Models**: Pluggable LLM support (Gemini, Claude Sonnet, GPT-4)
- **State Management**: PostgreSQL checkpointer for conversation persistence
- **Tool Execution**: Sequential, one-at-a-time tool calling (no parallel execution)

### Agent Routing
The system routes queries to specialized agents:
- **Global Agent** (`src/agents/agents.py`): Worldwide protected areas and environmental data
- **Ontario Agent** (`src/agents/ontario_agent.py`): Ontario parks, conservation areas, Williams Treaty territories
- **Router** (`src/agents/agent_router.py`): Keyword-based routing logic

Query routing is based on geographic keywords (e.g., "Ontario", "Peterborough", "Algonquin") and context from previous messages.

### Core Tools
Both agents use specialized tools in `src/tools/`:

**Global Agent Tools:**
- `pick_aoi`: PostGIS-based AOI selection with fuzzy text matching
- `pick_dataset`: RAG-based dataset selection using OpenAI embeddings
- `pull_data`: Retrieves data from GFW Analytics API via pluggable handlers
- `generate_insights`: Transforms data into insights and Chart.js visualizations
- `get_capabilities`: Describes agent capabilities

**Ontario Agent Tools:** (`src/tools/ontario/`)
- `pick_ontario_area`: Search Ontario parks, conservation areas, treaty territories
- `ontario_proximity_search`: Find areas near a location
- `compare_ontario_areas`: Compare multiple areas side-by-side
- `get_ontario_statistics`: Ontario-specific environmental data (placeholder)

### Agent State Schema
The agent maintains stateful conversations using `AgentState` TypedDict in `src/graph/`:
- `messages`: Conversation history
- `aoi`, `subregion_aois`, `aoi_name`: Selected areas of interest
- `dataset`: Selected dataset metadata
- `raw_data`, `start_date`, `end_date`: Retrieved data
- `insights`, `charts_data`: Generated visualizations

### Data Sources
- **PostGIS**: Geometry storage and spatial queries (GADM, KBA, WDPA, Ontario parks, conservation areas, treaty territories)
- **GFW Analytics API**: Primary environmental data source
- **Vector Store**: RAG dataset selection (LanceDB with OpenAI embeddings)

## Development Commands

### Setup
```bash
# Install dependencies
uv sync

# Copy environment files
cp .env.example .env
cp .env.local.example .env.local
# Edit both files with your credentials
```

### Infrastructure
```bash
make up           # Start Docker (PostgreSQL + Langfuse + ClickHouse)
make down         # Stop Docker services
make logs         # View Docker logs
```

### Data Ingestion
After starting infrastructure, ingest datasets (run from repository root):
```bash
# Build RAG database for dataset selection
uv run python src/ingest/embed_datasets.py

# OR sync from S3 (requires WRI AWS credentials)
aws s3 sync s3://zeno-static-data/ data/

# Ingest geographic data (2-10 GB each)
python src/ingest/ingest_gadm.py              # Administrative boundaries
python src/ingest/ingest_kba.py               # Key Biodiversity Areas
python src/ingest/ingest_landmark.py          # Land & Marine Key Areas
python src/ingest/ingest_wdpa.py              # Protected areas (~10 GB)

# Ontario-specific ingestion
python src/ingest/ingest_ontario_parks.py     # Ontario provincial parks
python src/ingest/ingest_conservation_areas.py # Conservation areas
python src/ingest/ingest_williams_treaty.py   # First Nations territories
```

### Running Services
```bash
make api          # Run API with hot reload (port 8000)
make frontend     # Run Streamlit frontend (port 8501)
make dev          # Start both API + frontend (requires infrastructure running)
```

### Testing
```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test suites
uv run pytest tests/api/          # API tests
uv run pytest tests/agent/        # Agent tests
uv run pytest tests/tools/        # Tool tests

# Single test file
uv run pytest tests/tools/test_ontario_tools.py -v
```

The test suite uses a separate `zeno-db_test` database (auto-created by `make up`).

### Code Quality
```bash
# Format code
uv run ruff format

# Lint code
uv run ruff check

# Auto-fix linting issues
uv run ruff check --fix
```

## Key Implementation Patterns

### Adding a New Tool
1. Create tool function in `src/tools/` with `@tool` decorator
2. Add to agent's tools list in `src/agents/agents.py` or `src/agents/ontario_agent.py`
3. Update `AgentState` schema in `src/graph/` if tool needs new state fields
4. Document tool in agent's system prompt
5. Write tests in `tests/tools/`

### Adding a New Data Source
1. Create handler class implementing `DataSourceHandler` interface in `src/tools/data_handlers/`
2. Register handler in `DataPullOrchestrator` (`src/tools/pull_data.py`)
3. Add dataset metadata to `src/tools/analytics_datasets.yml`
4. Regenerate RAG embeddings: `python src/ingest/embed_datasets.py`
5. Add tests in `tests/tools/`

### Adding an Ontario Dataset
Ontario-specific datasets should be ingested into the `ontario_areas` table with proper categorization:
- Add ingestion script to `src/ingest/ingest_<dataset>.py`
- Use `area_type` field to distinguish: 'park', 'conservation', 'treaty'
- Include proper attribution and data sovereignty metadata
- Test with Ontario agent tools

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1
```

### Agent Routing Logic
When modifying routing behavior, update keywords in `src/agents/agent_router.py`:
- Add location keywords to `ONTARIO_INDICATORS` dict
- Consider word boundary matching for short keywords
- Test with various query patterns

## CLI Tools

User management CLI is available in `src/cli.py`:
```bash
uv run python src/cli.py --help
```

See `docs/CLI.md` for detailed CLI documentation.

## Important Notes

- **Tool execution is sequential**: Tools execute one at a time to ensure state consistency
- **State is persistent**: Conversations persist across sessions via PostgreSQL checkpointer
- **Agent routing is keyword-based**: Not LLM-based (fast and deterministic)
- **Williams Treaty First Nations**: When working with Indigenous territories, follow cultural protocols in `src/tools/ontario/prompts.py`
- **RAG dataset selection**: Dataset descriptions are embedded and searched via semantic similarity
- **Chart.js compatibility**: `generate_insights` outputs Recharts-compatible JSON for frontend rendering

## Related Documentation

- Agent architecture details: `docs/AGENT_ARCHITECTURE.md`
- CLI documentation: `docs/CLI.md`
- Frontend repository: https://github.com/wri/project-zeno-next
- Deployment infrastructure: https://github.com/wri/project-zeno-deploy
