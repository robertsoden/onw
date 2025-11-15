"""Ontario Nature Watch Agent configuration.

This module provides an Ontario-specific agent with specialized tools
and prompts for Ontario protected areas and First Nations territories.
"""

import os
from datetime import datetime
from typing import Optional

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from src.graph import AgentState
from src.tools.ontario import (
    compare_ontario_areas,
    get_ontario_statistics,
    ontario_proximity_search,
    pick_ontario_area,
)
from src.tools.ontario.prompts import (
    ONTARIO_SYSTEM_PROMPT,
    WILLIAMS_TREATY_CONTEXT_PROMPT,
)
from src.utils.config import APISettings
from src.utils.env_loader import load_environment_variables
from src.utils.llms import MODEL

# Ontario-specific tools
ontario_tools = [
    pick_ontario_area,
    ontario_proximity_search,
    compare_ontario_areas,
    get_ontario_statistics,
]


def get_ontario_prompt(user: Optional[dict] = None) -> str:
    """
    Generate the Ontario-specific agent prompt.

    Args:
        user: Optional user information

    Returns:
        Formatted system prompt for Ontario agent
    """
    current_date = datetime.now().strftime("%Y-%m-%d")

    base_prompt = ONTARIO_SYSTEM_PROMPT

    # Add current date context
    base_prompt += f"\n\nCurrent date: {current_date}. Use this for relative time queries.\n"

    # Add Williams Treaty context
    base_prompt += f"\n\n## Williams Treaty Context\n\n{WILLIAMS_TREATY_CONTEXT_PROMPT}\n"

    # Add tool usage instructions
    base_prompt += """
## Tool Usage

**pick_ontario_area**: Search for Ontario parks, conservation areas, or First Nations territories by name.
- Use this when the user mentions a specific Ontario location
- Supports filtering by area type ('park', 'conservation', 'treaty')
- Returns detailed information and geometry

**ontario_proximity_search**: Find Ontario areas near a specific location.
- Use this when the user asks "what's near..." or "areas around..."
- Requires coordinates (latitude, longitude) or use geocoding first
- Supports radius filtering (default: 50km)

**compare_ontario_areas**: Compare multiple Ontario areas side-by-side.
- Use this when the user wants to compare 2-5 areas
- Provides size, type, designation, and management details
- Useful for decision-making between different areas

**get_ontario_statistics**: Get environmental data for Ontario areas.
- NOTE: This tool is a placeholder pending dataset integration
- Will provide biodiversity, forest cover, and species data
- Currently returns implementation status

## Workflow

1. **Location Identification**: Use pick_ontario_area to find the user's area of interest
2. **Nearby Search**: If needed, use ontario_proximity_search for proximity queries
3. **Comparison**: Use compare_ontario_areas when comparing multiple areas
4. **Statistics**: Use get_ontario_statistics for environmental data (when available)

## Cultural Sensitivity

When discussing Williams Treaty First Nations territories:
- Always use proper First Nations names (e.g., "Curve Lake First Nation")
- Acknowledge traditional territory and ongoing stewardship
- Follow cultural protocols outlined in the system prompt
- Be respectful and aware of data sovereignty
"""

    return base_prompt


# Use same checkpointer infrastructure as main agent
load_environment_variables()

DATABASE_URL = os.environ["DATABASE_URL"].replace(
    "postgresql+asyncpg://", "postgresql://"
)

_ontario_checkpointer_pool: AsyncConnectionPool = None


async def get_ontario_checkpointer_pool() -> AsyncConnectionPool:
    """Get or create the Ontario agent checkpointer connection pool."""
    global _ontario_checkpointer_pool
    if _ontario_checkpointer_pool is None:
        _ontario_checkpointer_pool = AsyncConnectionPool(
            DATABASE_URL,
            min_size=APISettings.db_pool_size,
            max_size=APISettings.db_max_overflow + APISettings.db_pool_size,
            kwargs={
                "row_factory": dict_row,
                "autocommit": True,
                "prepare_threshold": 0,
            },
            open=False,
        )
        await _ontario_checkpointer_pool.open()
    return _ontario_checkpointer_pool


async def close_ontario_checkpointer_pool():
    """Close the Ontario agent checkpointer connection pool."""
    global _ontario_checkpointer_pool
    if _ontario_checkpointer_pool:
        await _ontario_checkpointer_pool.close()
        _ontario_checkpointer_pool = None


async def fetch_ontario_checkpointer() -> AsyncPostgresSaver:
    """Get an AsyncPostgresSaver for the Ontario agent."""
    pool = await get_ontario_checkpointer_pool()
    checkpointer = AsyncPostgresSaver(pool)
    return checkpointer


async def fetch_ontario_agent_anonymous(
    user: Optional[dict] = None,
) -> CompiledStateGraph:
    """
    Setup the Ontario Nature Watch agent for anonymous users.

    Args:
        user: Optional user information

    Returns:
        Compiled LangGraph agent
    """
    ontario_agent = create_react_agent(
        model=MODEL,
        tools=ontario_tools,
        state_schema=AgentState,
        prompt=get_ontario_prompt(user),
    )
    return ontario_agent


async def fetch_ontario_agent(
    user: Optional[dict] = None
) -> CompiledStateGraph:
    """
    Setup the Ontario Nature Watch agent with checkpointing.

    Args:
        user: Optional user information

    Returns:
        Compiled LangGraph agent with PostgreSQL checkpointer
    """
    checkpointer = await fetch_ontario_checkpointer()
    ontario_agent = create_react_agent(
        model=MODEL,
        tools=ontario_tools,
        state_schema=AgentState,
        prompt=get_ontario_prompt(user),
        checkpointer=checkpointer,
    )
    return ontario_agent
