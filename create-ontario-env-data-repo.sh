#!/bin/bash
# Script to recreate the ontario-environmental-data repository
# Run this script to create the library structure locally, then push to GitHub

set -e

REPO_NAME="ontario-environmental-data"

echo "📦 Creating $REPO_NAME repository structure..."

# Create directory structure
mkdir -p $REPO_NAME/{ontario_data/{sources,models,constants,processors,ingestion},examples,docs,tests}

cd $REPO_NAME

# Initialize git
git init
git branch -M main

echo "✅ Directory structure created"
echo ""
echo "📝 Creating package files..."

# Create pyproject.toml
cat > pyproject.toml << 'PYPROJECT_EOF'
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "ontario-environmental-data"
version = "0.1.0"
description = "Python library for accessing Ontario environmental and social data sources"
readme = "README.md"
requires-python = ">=3.9"
license = {text = "MIT"}
authors = [
    {name = "Robert Soden"}
]
keywords = [
    "ontario",
    "environmental-data",
    "geospatial",
    "indigenous-data",
    "canada",
]

dependencies = [
    "aiohttp>=3.9.0",
    "geopandas>=0.14.0",
    "pandas>=2.0.0",
    "pydantic>=2.0.0",
    "shapely>=2.0.0",
    "python-dateutil>=2.8.0",
    "requests>=2.31.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
]

[project.urls]
Homepage = "https://github.com/robertsoden/ontario-environmental-data"
Repository = "https://github.com/robertsoden/ontario-environmental-data"
Issues = "https://github.com/robertsoden/ontario-environmental-data/issues"
PYPROJECT_EOF

# Create README.md
cat > README.md << 'README_EOF'
# Ontario Environmental Data

A Python library for accessing and processing Ontario environmental and social data sources.

## Overview

`ontario-environmental-data` provides a unified interface for accessing diverse Ontario data sources including:

- **Indigenous Services Canada (ISC)** - Water advisories, infrastructure, community well-being
- **Canadian Wildland Fire Information System (CWFIS)** - Fire weather and danger ratings
- **Ontario GeoHub** - Provincial geospatial data
- **Statistics Canada** - Census boundaries and demographics

This library was created to support multiple Ontario environmental projects with shared data access needs.

## Installation

```bash
pip install ontario-environmental-data
```

Or from source:

```bash
git clone https://github.com/robertsoden/ontario-environmental-data
cd ontario-environmental-data
pip install -e .
```

## Quick Start

```python
from ontario_data.sources.isc import WaterAdvisoriesClient

async with WaterAdvisoriesClient() as client:
    advisories = await client.fetch(csv_path="data.csv", province="ON")
    active = [adv for adv in advisories if adv.is_active]
    print(f"Found {len(active)} active water advisories")
```

## Features

- ✅ Unified API clients for Ontario data sources
- ✅ Standardized data models with Pydantic validation
- ✅ Async/await support
- ✅ Cultural sensitivity guidelines for Indigenous data
- ✅ Comprehensive documentation

## Data Sources

### Indigenous Services Canada
- Water Advisories
- Infrastructure (ICIM)
- Community Well-Being (CWB)

### Fire Data
- Historical fire incidents (Ontario MNRF)
- Fire danger ratings (CWFIS)

### Statistics Canada
- Census boundaries
- Community demographics

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Credits

Created by Robert Soden and contributors.

Original projects:
- [williams-treaties](https://github.com/robertsoden/williams-treaties)
- [Ontario Nature Watch](https://github.com/robertsoden/onw)
README_EOF

# Create LICENSE
cat > LICENSE << 'LICENSE_EOF'
MIT License

Copyright (c) 2024 Robert Soden and contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
LICENSE_EOF

echo "✅ Core files created"
echo ""
echo "📂 Next steps:"
echo "   cd $REPO_NAME"
echo "   # Copy Python source files from /home/user/ontario-environmental-data/ontario_data/"
echo "   # Or download the full source from the ONW repository documentation"
echo "   git add ."
echo "   git commit -m 'Initial commit: Ontario Environmental Data library'"
echo "   git remote add origin https://github.com/robertsoden/ontario-environmental-data.git"
echo "   git push -u origin main"
echo ""
echo "✅ Repository skeleton created!"
