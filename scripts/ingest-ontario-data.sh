#!/bin/bash
# Master script to ingest all Ontario data

set -e

echo "🍁 Ontario Nature Watch Data Ingestion"
echo "======================================"
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Check if PostgreSQL is running
if ! pg_isready &> /dev/null; then
    echo "❌ PostgreSQL is not running"
    echo "Start PostgreSQL first:"
    echo "  - Linux: sudo service postgresql start"
    echo "  - macOS: brew services start postgresql"
    exit 1
fi

# Check if PostGIS is available
echo "Checking PostGIS installation..."
if ! psql -d zeno-data-local -c "SELECT PostGIS_version();" &> /dev/null; then
    echo "❌ PostGIS not installed or not enabled"
    echo "Run: ./scripts/setup-postgis.sh"
    exit 1
fi

echo "✓ PostGIS is ready"
echo ""

# Create data directory
mkdir -p data/ontario

# Run ingestion scripts
echo "=" * 60
echo "Step 1: Ingesting Williams Treaty First Nations territories"
echo "=" * 60
python src/ingest/ingest_williams_treaty.py
echo ""

echo "=" * 60
echo "Step 2: Ingesting Ontario Provincial Parks"
echo "=" * 60
python src/ingest/ingest_ontario_parks.py
echo ""

echo "=" * 60
echo "Step 3: Ingesting Conservation Areas"
echo "=" * 60
python src/ingest/ingest_conservation_areas.py
echo ""

echo "=" * 60
echo "✅ Ontario data ingestion complete!"
echo "=" * 60
echo ""
echo "Verify data:"
echo "  psql -d zeno-data-local -c '\dt ontario*'"
echo "  psql -d zeno-data-local -c '\dt williams*'"
echo ""
echo "Test queries:"
echo "  psql -d zeno-data-local -c 'SELECT COUNT(*) FROM ontario_parks;'"
echo "  psql -d zeno-data-local -c 'SELECT COUNT(*) FROM ontario_conservation_areas;'"
echo "  psql -d zeno-data-local -c 'SELECT COUNT(*) FROM williams_treaty_first_nations;'"
