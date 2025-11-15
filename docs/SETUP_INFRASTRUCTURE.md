# Infrastructure Setup Guide

Complete guide for setting up the development infrastructure for Ontario Nature Watch.

## Prerequisites

- Python 3.12+
- PostgreSQL 16+
- uv (Python package manager)

## Quick Start

```bash
# 1. Install Python dependencies
uv sync

# 2. Set up environment files
cp .env.example .env
cp .env.local.example .env.local
# Edit .env with your API keys

# 3. Start PostgreSQL (if not running)
# Linux:
sudo service postgresql start

# macOS:
brew services start postgresql

# 4. Set up databases
./scripts/setup-database.sh

# 5. Install PostGIS
./scripts/setup-postgis.sh

# 6. Run migrations
cd db
DATABASE_URL="postgresql+asyncpg://$(whoami)@localhost:5432/zeno-data-local" \
  ../.venv/bin/alembic upgrade heads

# 7. Start the services
make dev
```

## Detailed Setup Steps

### 1. Python Environment

The project uses `uv` for dependency management:

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies (creates .venv and installs packages)
uv sync
```

### 2. Environment Configuration

Create and configure environment files:

```bash
cp .env.example .env
cp .env.local.example .env.local
```

Edit `.env` to add your API keys:
- `ANTHROPIC_API_KEY` - For Claude models
- `GOOGLE_API_KEY` - For Gemini models
- `OPENAI_API_KEY` - For OpenAI models
- `WRI_API_KEY` and `WRI_BEARER_TOKEN` - For WRI data access

The `.env.local` file overrides settings for local development.

### 3. PostgreSQL Setup

#### Install PostgreSQL

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib
```

**macOS:**
```bash
brew install postgresql@16
brew services start postgresql@16
```

#### Configure PostgreSQL

The setup script handles database creation and role configuration:

```bash
./scripts/setup-database.sh
```

This script:
- Creates a PostgreSQL role for your user
- Creates three databases: `ontario-nature-watch`, `zeno-data-local`, `zeno-data_test`
- Updates `.env.local` with correct database URLs

#### Manual Database Creation (if needed)

```bash
# Create role
psql -U postgres -c "CREATE ROLE $(whoami) WITH SUPERUSER LOGIN;"

# Create databases
createdb ontario-nature-watch
createdb zeno-data-local
createdb zeno-data_test
```

### 4. PostGIS Installation

PostGIS is required for geographic data support:

```bash
./scripts/setup-postgis.sh
```

This installs PostGIS and enables it in all project databases.

**Manual PostGIS Setup:**

```bash
# Ubuntu/Debian
sudo apt-get install -y postgresql-16-postgis-3 postgis

# macOS
brew install postgis

# Enable in databases
psql -d zeno-data-local -c "CREATE EXTENSION IF NOT EXISTS postgis;"
psql -d ontario-nature-watch -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

### 5. Database Migrations

Run Alembic migrations to create all tables:

```bash
cd db
DATABASE_URL="postgresql+asyncpg://$(whoami)@localhost:5432/zeno-data-local" \
  ../.venv/bin/alembic upgrade heads
```

This creates:
- User management tables
- Thread/conversation tables
- LangGraph checkpoint tables for agent state
- Custom areas (with PostGIS)
- Ontario-specific schema
- Williams Treaty Territory tables

### 6. Dataset Embeddings (Optional)

Build the dataset lookup RAG database:

```bash
# If you have WRI AWS credentials, download reference data
aws s3 cp s3://zeno-static-data/zeno_data_clean_v2.csv data/

# Generate embeddings
.venv/bin/python src/ingest/embed_datasets.py
```

### 7. Start Services

```bash
# Start all services (API + Frontend)
make dev

# Or start individually:
make api       # API only (http://localhost:8000)
make frontend  # Frontend only (http://localhost:8501)
```

## Verification

### Check PostgreSQL

```bash
# Check if PostgreSQL is running
pg_isready

# List databases
psql -l

# Check PostGIS version
psql -d zeno-data-local -c "SELECT PostGIS_version();"
```

### Check Database Tables

```bash
psql -d zeno-data-local -c "\dt"
```

Expected tables:
- `users` - User accounts
- `threads` - Conversation threads
- `checkpoints`, `checkpoint_writes` - LangGraph state
- `custom_areas` - User-defined areas
- `ontario_parks`, `ontario_conservation_areas` - Ontario data
- `williams_treaty_first_nations` - Treaty territories

### Test Database Connection

```bash
.venv/bin/python -c "
import asyncio
import asyncpg

async def test():
    conn = await asyncpg.connect('postgresql://$(whoami)@localhost:5432/zeno-data-local')
    print('✅ Connection successful!')
    print(await conn.fetchval('SELECT version()'))
    await conn.close()

asyncio.run(test())
"
```

## Troubleshooting

### PostgreSQL Not Running

```bash
# Linux
sudo service postgresql status
sudo service postgresql start

# macOS
brew services list
brew services start postgresql@16
```

### Permission Denied Errors

If you get permission errors with PostgreSQL:

1. Check if your user has a PostgreSQL role:
   ```bash
   psql -U postgres -c "\du"
   ```

2. Create role if missing:
   ```bash
   psql -U postgres -c "CREATE ROLE $(whoami) WITH SUPERUSER LOGIN;"
   ```

3. Update `pg_hba.conf` to allow local connections:
   ```
   # Add this line for trust authentication (development only!)
   local   all             all                                     trust
   ```

### PostGIS Not Available

If PostGIS installation fails:

1. Check PostgreSQL version:
   ```bash
   psql --version
   ```

2. Install matching PostGIS version:
   ```bash
   sudo apt-get install postgresql-{VERSION}-postgis-3
   ```

3. Verify installation:
   ```bash
   ls /usr/share/postgresql/{VERSION}/extension/postgis*
   ```

### Migration Errors

If migrations fail:

1. Check database connection:
   ```bash
   psql -d zeno-data-local -c "SELECT 1;"
   ```

2. Check Alembic heads:
   ```bash
   cd db
   DATABASE_URL="..." alembic heads
   ```

3. Reset database (CAUTION: destroys data):
   ```bash
   dropdb zeno-data-local
   createdb zeno-data-local
   # Re-run migrations
   ```

## Development Workflow

### Making Database Changes

1. Create new migration:
   ```bash
   cd db
   alembic revision -m "description of changes"
   ```

2. Edit the generated file in `db/alembic/versions/`

3. Apply migration:
   ```bash
   DATABASE_URL="..." alembic upgrade head
   ```

### Resetting Development Database

```bash
# Drop and recreate
dropdb zeno-data-local
createdb zeno-data-local

# Re-run setup
./scripts/setup-postgis.sh
cd db && DATABASE_URL="..." alembic upgrade heads
```

## Production Considerations

For production deployments:

1. **Don't use trust authentication** - Configure proper password-based authentication in `pg_hba.conf`

2. **Use environment-specific credentials** - Store in secure secrets management

3. **Enable SSL connections** - Configure PostgreSQL SSL and update connection strings

4. **Regular backups** - Set up automated database backups

5. **Monitoring** - Use tools like PgHero or CloudWatch for database monitoring

6. **Connection pooling** - Configure pgBouncer or similar for production workloads
