#!/bin/bash
# PostGIS Setup Script for Ubuntu/Debian systems
# This script installs PostGIS and enables it in the required databases

set -e

echo "🗺️  PostGIS Setup Script"
echo "========================"
echo ""

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL is not installed. Please install PostgreSQL first."
    exit 1
fi

# Get PostgreSQL version
PG_VERSION=$(psql --version | grep -oP '\d+' | head -1)
echo "✓ Found PostgreSQL version: $PG_VERSION"

# Install PostGIS
echo ""
echo "📦 Installing PostGIS extension..."
if command -v apt-get &> /dev/null; then
    # Ubuntu/Debian
    sudo apt-get update
    sudo apt-get install -y postgresql-$PG_VERSION-postgis-3 postgis
elif command -v yum &> /dev/null; then
    # CentOS/RHEL
    sudo yum install -y postgis33_$PG_VERSION
elif command -v brew &> /dev/null; then
    # macOS
    brew install postgis
else
    echo "❌ Unsupported package manager. Please install PostGIS manually."
    exit 1
fi

echo "✓ PostGIS packages installed"

# Enable PostGIS in databases
echo ""
echo "🔧 Enabling PostGIS in databases..."

DATABASES=("ontario-nature-watch" "zeno-data-local" "zeno-data_test")

for DB in "${DATABASES[@]}"; do
    echo "  Processing database: $DB"

    # Check if database exists
    if psql -lqt | cut -d \| -f 1 | grep -qw "$DB"; then
        psql -d "$DB" -c "CREATE EXTENSION IF NOT EXISTS postgis;" 2>/dev/null || true
        psql -d "$DB" -c "CREATE EXTENSION IF NOT EXISTS postgis_topology;" 2>/dev/null || true

        # Verify PostGIS version
        VERSION=$(psql -d "$DB" -tAc "SELECT PostGIS_version();" 2>/dev/null || echo "not installed")
        if [ "$VERSION" != "not installed" ]; then
            echo "    ✓ PostGIS enabled (version: $VERSION)"
        else
            echo "    ⚠️  Could not verify PostGIS installation"
        fi
    else
        echo "    ⚠️  Database '$DB' does not exist, skipping..."
    fi
done

echo ""
echo "✅ PostGIS setup complete!"
echo ""
echo "Run database migrations:"
echo "  cd db && alembic upgrade heads"
