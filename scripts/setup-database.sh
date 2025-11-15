#!/bin/bash
# Complete Database Setup Script
# Sets up PostgreSQL, creates databases, and runs migrations

set -e

echo "🗄️  Database Setup Script"
echo "========================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if PostgreSQL is running
if ! pg_isready &> /dev/null; then
    echo -e "${RED}❌ PostgreSQL is not running${NC}"
    echo "Please start PostgreSQL first:"
    echo "  - Linux: sudo service postgresql start"
    echo "  - macOS: brew services start postgresql"
    exit 1
fi

echo -e "${GREEN}✓ PostgreSQL is running${NC}"

# Get current user
CURRENT_USER=$(whoami)
echo "Current user: $CURRENT_USER"
echo ""

# Create PostgreSQL role if it doesn't exist
echo "🔧 Setting up PostgreSQL role..."
psql -U postgres -tc "SELECT 1 FROM pg_roles WHERE rolname='$CURRENT_USER'" | grep -q 1 || \
    psql -U postgres -c "CREATE ROLE $CURRENT_USER WITH SUPERUSER LOGIN;" || \
    echo -e "${YELLOW}⚠️  Role may already exist or you may not have permissions${NC}"

# Create databases
echo ""
echo "🗄️  Creating databases..."

DATABASES=("ontario-nature-watch" "zeno-data-local" "zeno-data_test")

for DB in "${DATABASES[@]}"; do
    echo -n "  Creating '$DB'... "
    createdb "$DB" 2>/dev/null && echo -e "${GREEN}✓${NC}" || echo -e "${YELLOW}already exists${NC}"
done

# Update .env.local with correct database URLs
echo ""
echo "📝 Updating .env.local configuration..."
if [ -f .env.local ]; then
    sed -i.bak "s|DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://$CURRENT_USER@localhost:5432/zeno-data-local|" .env.local
    sed -i.bak "s|TEST_DATABASE_URL=.*|TEST_DATABASE_URL=postgresql+asyncpg://$CURRENT_USER@localhost:5432/zeno-data_test|" .env.local
    echo -e "${GREEN}✓ Configuration updated${NC}"
else
    echo -e "${YELLOW}⚠️  .env.local not found, skipping...${NC}"
fi

echo ""
echo -e "${GREEN}✅ Database setup complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Install PostGIS: ./scripts/setup-postgis.sh"
echo "  2. Run migrations: cd db && DATABASE_URL=postgresql+asyncpg://$CURRENT_USER@localhost:5432/zeno-data-local ../venv/bin/alembic upgrade heads"
echo "  3. Start the API: make api"
