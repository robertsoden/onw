# Shared ontario-environmental-data Setup

Guide for using a single `ontario-environmental-data` installation across multiple projects.

## Overview

Instead of installing the library separately for each project, you can:
1. Clone `ontario-environmental-data` **once** in a shared location
2. Install it in **editable mode** (`pip install -e`)
3. Configure a **shared data directory** for cached datasets
4. Both ONW and williams-treaties use the **same code and data**

## Benefits

✅ **Single data download** - Download datasets once, use everywhere
✅ **Consistent code** - All projects use same library version
✅ **Easy development** - Edit library code, see changes in all projects
✅ **Disk space savings** - No duplicate data files

## Setup Instructions

### 1. Directory Structure

Recommended layout:

```
~/projects/
├── ontario-environmental-data/     # Shared library
│   ├── ontario_data/
│   ├── pyproject.toml
│   └── ...
├── ontario-data/                   # Shared data cache
│   ├── water_advisories/
│   ├── fire_incidents/
│   ├── community_wellbeing/
│   └── census_boundaries/
├── onw/                            # Ontario Nature Watch
│   └── ...
└── williams-treaties/              # Williams Treaties project
    └── ...
```

### 2. Clone the Library Once

```bash
cd ~/projects
git clone https://github.com/robertsoden/ontario-environmental-data.git
```

### 3. Install in Editable Mode

**For ONW:**
```bash
cd ~/projects/onw
pip install -e ~/projects/ontario-environmental-data
```

**For williams-treaties:**
```bash
cd ~/projects/williams-treaties
pip install -e ~/projects/ontario-environmental-data
```

The `-e` flag installs in "editable" mode - both projects point to the same source code.

### 4. Configure Shared Data Directory

Create a configuration file that both projects can use:

**~/.ontario_data_config.yml:**
```yaml
# Shared configuration for ontario-environmental-data

# Shared data directory (adjust path as needed)
data_dir: ~/projects/ontario-data

# Cache settings
cache:
  enabled: true
  ttl_hours: 168  # 1 week

# Data source settings
sources:
  water_advisories:
    csv_path: ~/projects/ontario-data/water_advisories/latest.csv

  fire_incidents:
    data_dir: ~/projects/ontario-data/fire_incidents/

  census_boundaries:
    cache_dir: ~/projects/ontario-data/census_boundaries/

  community_wellbeing:
    csv_path: ~/projects/ontario-data/community_wellbeing/cwb_2021.csv
```

### 5. Update Projects to Use Shared Config

**In ONW (optional enhancement):**

```python
# src/tools/data_handlers/williams_treaty_handler.py
import os
from pathlib import Path

# Use shared data directory
SHARED_DATA_DIR = Path(os.getenv(
    "ONTARIO_DATA_DIR",
    "~/projects/ontario-data"
)).expanduser()

class WilliamsTreatyDataHandler:
    def __init__(self):
        self.data_dir = SHARED_DATA_DIR
        # ... rest of initialization
```

**In williams-treaties:**

```python
# scripts/utils/common.py
import os
from pathlib import Path

# Use shared data directory
SHARED_DATA_DIR = Path(os.getenv(
    "ONTARIO_DATA_DIR",
    "~/projects/ontario-data"
)).expanduser()

def get_data_path(subdir: str) -> Path:
    """Get path in shared data directory."""
    path = SHARED_DATA_DIR / subdir
    path.mkdir(parents=True, exist_ok=True)
    return path
```

## Usage Examples

### Download Data Once, Use Everywhere

**Download water advisories (from either project):**
```bash
# From ONW
cd ~/projects/onw
python -m src.ingest.ingest_water_advisories \
    ~/projects/ontario-data/water_advisories/2024.csv

# OR from williams-treaties
cd ~/projects/williams-treaties
python scripts/10_process_water_advisories.py
```

**Both projects use the same data:**
```bash
ls -lh ~/projects/ontario-data/water_advisories/
# -> 2024.csv (downloaded once, used by both)
```

### Using the Shared Library

**In ONW:**
```python
from ontario_data.sources.isc import WaterAdvisoriesClient
from ontario_data.constants import WILLIAMS_TREATY_FIRST_NATIONS

# Uses shared library code
client = WaterAdvisoriesClient()
advisories = await client.fetch(csv_path="~/projects/ontario-data/water_advisories/2024.csv")
```

**In williams-treaties:**
```python
from ontario_data.sources.isc import WaterAdvisoriesClient
from ontario_data.constants import WILLIAMS_TREATY_FIRST_NATIONS

# Same library, same data
client = WaterAdvisoriesClient()
advisories = await client.fetch(csv_path="~/projects/ontario-data/water_advisories/2024.csv")
```

### Development Workflow

**Edit library code:**
```bash
cd ~/projects/ontario-environmental-data
# Edit ontario_data/sources/isc.py
```

**Changes are immediately available in both projects** (no reinstall needed with `-e`):

```bash
# Test in ONW
cd ~/projects/onw
python -m pytest tests/

# Test in williams-treaties
cd ~/projects/williams-treaties
python scripts/test_water_advisories.py
```

## Environment Variables

Set these in your shell profile (`~/.bashrc` or `~/.zshrc`):

```bash
# Shared data directory
export ONTARIO_DATA_DIR=~/projects/ontario-data

# Library path (if not installed via pip)
export PYTHONPATH=~/projects/ontario-environmental-data:$PYTHONPATH
```

## Verifying the Setup

### Check Library Location

```bash
# From ONW
cd ~/projects/onw
python -c "import ontario_data; print(ontario_data.__file__)"
# -> ~/projects/ontario-environmental-data/ontario_data/__init__.py

# From williams-treaties
cd ~/projects/williams-treaties
python -c "import ontario_data; print(ontario_data.__file__)"
# -> ~/projects/ontario-environmental-data/ontario_data/__init__.py
```

Both should point to the same location!

### Check Data Directory

```bash
tree ~/projects/ontario-data
# ontario-data/
# ├── water_advisories/
# │   └── 2024.csv
# ├── fire_incidents/
# │   └── ontario_fires_2020-2024.geojson
# └── community_wellbeing/
#     └── cwb_2021.csv
```

## Shared Data Management

### Download Script Example

Create a helper script to manage shared data:

**~/projects/ontario-data/download_all.sh:**
```bash
#!/bin/bash
# Download all Ontario datasets to shared cache

ONTARIO_DATA_DIR=~/projects/ontario-data

echo "📥 Downloading Ontario datasets to $ONTARIO_DATA_DIR"

# Water advisories
echo "Downloading water advisories..."
# Download from ISC website
# wget -O $ONTARIO_DATA_DIR/water_advisories/latest.csv <URL>

# Census boundaries (large download, ~500MB)
echo "Downloading census boundaries..."
if [ ! -f "$ONTARIO_DATA_DIR/census_boundaries/csd_2021.zip" ]; then
    wget -O $ONTARIO_DATA_DIR/census_boundaries/csd_2021.zip \
        "https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/files-fichiers/lcsd000b21a_e.zip"
    unzip -d $ONTARIO_DATA_DIR/census_boundaries/ \
        $ONTARIO_DATA_DIR/census_boundaries/csd_2021.zip
fi

# Community well-being
echo "Downloading CWB data..."
# Download from ISC

echo "✅ All datasets downloaded!"
```

### Data Update Strategy

**Option 1: Manual updates**
```bash
cd ~/projects/ontario-data
./download_all.sh
```

**Option 2: Cron job (automated)**
```bash
# Update water advisories weekly
0 0 * * 0 cd ~/projects/ontario-data && ./update_water_advisories.sh
```

## Virtual Environments

If using separate virtual environments for each project:

**ONW virtual environment:**
```bash
cd ~/projects/onw
python -m venv venv
source venv/bin/activate
pip install -e ~/projects/ontario-environmental-data
# Install ONW dependencies
pip install -r requirements.txt
```

**williams-treaties virtual environment:**
```bash
cd ~/projects/williams-treaties
python -m venv venv
source venv/bin/activate
pip install -e ~/projects/ontario-environmental-data
# Install williams-treaties dependencies
pip install -r requirements.txt
```

Both environments point to the **same library source** but have **separate dependencies**.

## Troubleshooting

### Library not found

**Problem:** `ModuleNotFoundError: No module named 'ontario_data'`

**Solution:**
```bash
# Ensure installed in editable mode
pip install -e ~/projects/ontario-environmental-data

# Or add to PYTHONPATH
export PYTHONPATH=~/projects/ontario-environmental-data:$PYTHONPATH
```

### Data files not found

**Problem:** Can't find CSV files

**Solution:**
```bash
# Check data directory
ls -la ~/projects/ontario-data/

# Set environment variable
export ONTARIO_DATA_DIR=~/projects/ontario-data

# Or use absolute paths in scripts
csv_path = Path("~/projects/ontario-data/water_advisories/2024.csv").expanduser()
```

### Changes not reflected

**Problem:** Edited library code but changes not showing

**Solution:**
```bash
# Verify editable install
pip show ontario-environmental-data | grep Location
# Should show: ~/projects/ontario-environmental-data

# Reinstall if needed
pip uninstall ontario-environmental-data
pip install -e ~/projects/ontario-environmental-data

# Restart Python interpreter
```

## Alternative: Docker Setup

For even more consistency across projects:

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  ontario-data:
    image: python:3.11
    volumes:
      - ~/projects/ontario-environmental-data:/app/ontario-environmental-data
      - ~/projects/ontario-data:/data
      - ~/projects/onw:/app/onw
      - ~/projects/williams-treaties:/app/williams-treaties
    environment:
      - ONTARIO_DATA_DIR=/data
```

## Summary

✅ **One library installation** - `pip install -e ~/projects/ontario-environmental-data`
✅ **One data directory** - `~/projects/ontario-data`
✅ **Multiple projects** - ONW, williams-treaties, others
✅ **Shared cache** - Download once, use everywhere
✅ **Easy development** - Edit once, test everywhere

**Key Commands:**
```bash
# Clone library once
git clone https://github.com/robertsoden/ontario-environmental-data.git ~/projects/ontario-environmental-data

# Install in each project
cd ~/projects/onw
pip install -e ~/projects/ontario-environmental-data

cd ~/projects/williams-treaties
pip install -e ~/projects/ontario-environmental-data

# Set shared data directory
export ONTARIO_DATA_DIR=~/projects/ontario-data
```

Now both projects use the **same code** and **same data**! 🎉
