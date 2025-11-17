# Complete Source Code for ontario-environmental-data

This document contains ALL the source code files for the ontario-environmental-data library.
Copy each section to create the corresponding file in your GitHub repository.

## Repository Structure

```
ontario-environmental-data/
├── ontario_data/
│   ├── __init__.py
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── isc.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── water_advisory.py
│   │   ├── fire.py
│   │   ├── infrastructure.py
│   │   └── community.py
│   └── constants/
│       ├── __init__.py
│       ├── first_nations.py
│       ├── regions.py
│       └── data_sources.py
├── examples/
│   ├── README.md
│   └── fetch_water_advisories.py
├── pyproject.toml
├── README.md
└── LICENSE
```

---

## pyproject.toml

```toml
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
```

---

## README.md

See the full README at: https://github.com/robertsoden/onw/blob/claude/port-ontario-scripts-017wPK7YNPCCwCfe9k2BXCNP/LIBRARY_CREATION_SUMMARY.md

Or use this minimal version:

```markdown
# Ontario Environmental Data

A Python library for accessing Ontario environmental and social data sources.

## Installation

\`\`\`bash
pip install ontario-environmental-data
\`\`\`

## Quick Start

\`\`\`python
from ontario_data.sources.isc import WaterAdvisoriesClient

async with WaterAdvisoriesClient() as client:
    advisories = await client.fetch(csv_path="data.csv", province="ON")
    active = [adv for adv in advisories if adv.is_active]
    print(f"Found {len(active)} active water advisories")
\`\`\`

## Features

- Unified API clients for Ontario data sources
- Pydantic data models with validation
- Async/await support
- Cultural sensitivity guidelines

## License

MIT License
```

---

## LICENSE

```
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
```

---

## ontario_data/__init__.py

```python
"""Ontario Environmental Data - A Python library for Ontario data access."""

__version__ = "0.1.0"

from ontario_data import constants, models, processors, sources

__all__ = ["constants", "models", "processors", "sources", "__version__"]
```

---

## ontario_data/sources/__init__.py

```python
"""Data source clients for Ontario environmental data."""

from ontario_data.sources.base import BaseClient, DataSourceError

__all__ = ["BaseClient", "DataSourceError"]
```

---

## ontario_data/sources/base.py

```python
"""Base classes for data source clients."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import aiohttp


class DataSourceError(Exception):
    """Base exception for data source errors."""
    pass


class BaseClient(ABC):
    """
    Abstract base class for data source clients.

    Provides common functionality for:
    - HTTP requests with retry logic
    - Rate limiting
    - Error handling
    """

    def __init__(
        self,
        base_url: str,
        rate_limit: int = 60,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self.base_url = base_url
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    @abstractmethod
    async def fetch(self, **kwargs) -> List[Any]:
        """Fetch data from the source."""
        pass

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
```

---

## ontario_data/sources/isc.py

See the ISC client code I provided above (369 lines).
It includes:
- `WaterAdvisoriesClient`
- `InfrastructureClient`
- `CommunityWellbeingClient`

---

## ontario_data/models/__init__.py

```python
"""Data models for Ontario environmental data."""

from ontario_data.models.water_advisory import WaterAdvisory
from ontario_data.models.fire import FireIncident, FireDanger
from ontario_data.models.infrastructure import InfrastructureProject
from ontario_data.models.community import CommunityWellbeing

__all__ = [
    "WaterAdvisory",
    "FireIncident",
    "FireDanger",
    "InfrastructureProject",
    "CommunityWellbeing",
]
```

---

## ontario_data/models/water_advisory.py

See the WaterAdvisory model code I provided above (116 lines).

---

## ontario_data/models/fire.py

Get from: `/home/user/ontario-environmental-data/ontario_data/models/fire.py`

---

## ontario_data/models/infrastructure.py

Get from: `/home/user/ontario-environmental-data/ontario_data/models/infrastructure.py`

---

## ontario_data/models/community.py

Get from: `/home/user/ontario-environmental-data/ontario_data/models/community.py`

---

## ontario_data/constants/__init__.py

```python
"""Ontario-specific constants and configuration."""

from ontario_data.constants.first_nations import (
    WILLIAMS_TREATY_FIRST_NATIONS,
    ONTARIO_FIRST_NATIONS,
)
from ontario_data.constants.regions import (
    CONSERVATION_AUTHORITIES,
    FIRE_REGIONS,
)
from ontario_data.constants.data_sources import (
    ISC_WATER_ADVISORIES_URL,
    CWFIS_API_BASE,
    ONTARIO_GEOHUB_BASE,
    STATCAN_CENSUS_BASE,
)

__all__ = [
    "WILLIAMS_TREATY_FIRST_NATIONS",
    "ONTARIO_FIRST_NATIONS",
    "CONSERVATION_AUTHORITIES",
    "FIRE_REGIONS",
    "ISC_WATER_ADVISORIES_URL",
    "CWFIS_API_BASE",
    "ONTARIO_GEOHUB_BASE",
    "STATCAN_CENSUS_BASE",
]
```

---

## ontario_data/constants/first_nations.py

```python
"""Constants for Ontario First Nations."""

WILLIAMS_TREATY_FIRST_NATIONS = [
    "Alderville First Nation",
    "Curve Lake First Nation",
    "Hiawatha First Nation",
    "Mississaugas of Scugog Island First Nation",
    "Chippewas of Beausoleil First Nation",
    "Chippewas of Georgina Island First Nation",
    "Chippewas of Rama First Nation",
]

ONTARIO_FIRST_NATIONS = WILLIAMS_TREATY_FIRST_NATIONS + [
    "Six Nations of the Grand River",
    "Mississaugas of the Credit First Nation",
    "Mohawks of the Bay of Quinte",
]

CULTURAL_GUIDELINES = """
When working with First Nations data:

1. Respect Indigenous Data Sovereignty
2. Use proper terminology
3. Acknowledge treaty context
4. Support communities responsibly
"""
```

---

## ontario_data/constants/regions.py

Get from: `/home/user/ontario-environmental-data/ontario_data/constants/regions.py`

---

## ontario_data/constants/data_sources.py

Get from: `/home/user/ontario-environmental-data/ontario_data/constants/data_sources.py`

---

## Next Steps

1. Create repository structure on GitHub
2. Copy-paste each file
3. Commit with: `git commit -m "Initial commit: Ontario Environmental Data library"`
4. Push to main

**OR** download the complete files from the ONW repository branch I just pushed.

All model files are also available in the ONW repository at:
https://github.com/robertsoden/onw/tree/claude/port-ontario-scripts-017wPK7YNPCCwCfe9k2BXCNP
