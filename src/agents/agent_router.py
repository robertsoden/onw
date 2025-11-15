"""Agent router - selects between global and Ontario-specific agents.

This module provides routing logic to determine which agent to use
based on the user's query and context.
"""

import re
from typing import Dict, Literal, Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

AgentType = Literal["global", "ontario"]

# Ontario-specific keywords and patterns
ONTARIO_INDICATORS = {
    "provinces": ["ontario", "on"],
    "cities": [
        "toronto",
        "ottawa",
        "peterborough",
        "kawartha",
        "orillia",
        "barrie",
        "kingston",
        "belleville",
        "cobourg",
    ],
    "regions": [
        "kawarthas",
        "georgian bay",
        "lake simcoe",
        "rice lake",
        "lake ontario",
        "cottage country",
        "muskoka",
    ],
    "parks": [
        "algonquin",
        "killarney",
        "quetico",
        "pinery",
        "bon echo",
        "arrowhead",
        "silent lake",
    ],
    "first_nations": [
        "alderville",
        "curve lake",
        "hiawatha",
        "scugog island",
        "beausoleil",
        "georgina island",
        "rama",
        "williams treaty",
        "first nation",
        "indigenous",
    ],
    "conservation": [
        "conservation area",
        "conservation authority",
        "kawartha conservation",
        "otonabee conservation",
        "trca",
    ],
}


def detect_ontario_query(query: str, context: Optional[Dict] = None) -> bool:
    """
    Detect if a query is Ontario-specific.

    Args:
        query: User's query text
        context: Optional context information (previous messages, location, etc.)

    Returns:
        True if query is Ontario-specific, False otherwise
    """
    query_lower = query.lower()

    # Check for explicit Ontario indicators
    for category, keywords in ONTARIO_INDICATORS.items():
        for keyword in keywords:
            # Use word boundary matching for short keywords to avoid false positives
            # e.g., "on" in "deforestation" should not match
            if len(keyword) <= 2:
                # Use word boundaries for short keywords
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, query_lower):
                    logger.info(
                        f"Ontario query detected - category: {category}, keyword: {keyword}"
                    )
                    return True
            else:
                # Simple substring match for longer keywords
                if keyword in query_lower:
                    logger.info(
                        f"Ontario query detected - category: {category}, keyword: {keyword}"
                    )
                    return True

    # Check context if provided
    if context:
        # Check if previous messages were Ontario-focused
        if context.get("previous_agent") == "ontario":
            logger.info("Ontario query detected - previous agent was Ontario")
            return True

        # Check if user has Ontario preference
        if context.get("user_location", {}).get("province") == "Ontario":
            logger.info("Ontario query detected - user location is Ontario")
            return True

    return False


def select_agent(
    query: str, context: Optional[Dict] = None, force: Optional[AgentType] = None
) -> AgentType:
    """
    Select which agent to use for a query.

    Args:
        query: User's query text
        context: Optional context information
        force: Force a specific agent type (for testing or user preference)

    Returns:
        Agent type to use: 'ontario' or 'global'
    """
    if force:
        logger.info(f"Forced agent selection: {force}")
        return force

    if detect_ontario_query(query, context):
        logger.info("Selected Ontario agent")
        return "ontario"

    logger.info("Selected global agent")
    return "global"


def get_agent_description(agent_type: AgentType) -> str:
    """
    Get a description of the selected agent.

    Args:
        agent_type: Type of agent

    Returns:
        Human-readable description
    """
    descriptions = {
        "ontario": "Ontario Nature Watch - Specialized in Ontario provincial parks, conservation areas, and Williams Treaty First Nations territories",
        "global": "Global Nature Watch - Worldwide protected areas, biodiversity data, and environmental analytics",
    }
    return descriptions.get(agent_type, "Unknown agent")


def can_switch_agents(
    from_agent: AgentType, to_agent: AgentType, conversation_history: list
) -> bool:
    """
    Determine if it's appropriate to switch between agents mid-conversation.

    Args:
        from_agent: Current agent type
        to_agent: Proposed new agent type
        conversation_history: List of previous messages

    Returns:
        True if switching is allowed, False otherwise
    """
    # Allow switching if conversation is short (< 3 messages)
    if len(conversation_history) < 3:
        return True

    # Don't switch if user is mid-workflow (has selected AOI/dataset)
    recent_messages = conversation_history[-3:]
    workflow_indicators = [
        "selected",
        "analyzing",
        "pulling data",
        "generating insights",
    ]

    for msg in recent_messages:
        msg_text = str(msg).lower()
        if any(indicator in msg_text for indicator in workflow_indicators):
            logger.info(
                "Agent switching blocked - user is mid-workflow"
            )
            return False

    logger.info(f"Agent switching allowed: {from_agent} -> {to_agent}")
    return True


# Example usage and testing
if __name__ == "__main__":
    test_queries = [
        "What's the deforestation in Algonquin Park?",
        "Show me parks near Peterborough",
        "Curve Lake First Nation territory",
        "Deforestation in the Amazon",
        "Protected areas in California",
        "Conservation areas in Ontario",
        "Forest loss in Brazil",
    ]

    print("Agent Routing Test\n" + "=" * 50)
    for query in test_queries:
        agent = select_agent(query)
        print(f"\nQuery: {query}")
        print(f"Agent: {agent}")
        print(f"Description: {get_agent_description(agent)}")
