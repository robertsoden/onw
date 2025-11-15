"""Unit tests for Ontario agent router."""

import pytest

from src.agents.agent_router import (
    AgentType,
    can_switch_agents,
    detect_ontario_query,
    get_agent_description,
    select_agent,
)


class TestDetectOntarioQuery:
    """Test Ontario query detection logic."""

    @pytest.mark.parametrize(
        "query,expected",
        [
            # Ontario-specific queries
            ("What parks are in Ontario?", True),
            ("Tell me about Algonquin Park", True),
            ("Parks near Peterborough", True),
            ("Toronto conservation areas", True),
            ("Curve Lake First Nation", True),
            ("Kawarthas region", True),
            ("Lake Simcoe parks", True),
            ("Georgian Bay conservation", True),
            ("Killarney Provincial Park", True),
            ("Williams Treaty territories", True),
            ("Conservation Authority areas", True),
            # Global queries (should not match)
            ("Deforestation in the Amazon", False),
            ("California protected areas", False),
            ("Forest loss in Brazil", False),
            ("Yellowstone National Park", False),
            ("African wildlife reserves", False),
            # Edge cases - "on" in other words
            ("Deforestation trends", False),  # "on" in "deforestation"
            ("Information about forests", False),  # "on" in "information"
            ("Conservation in Peru", False),  # "on" in "conservation"
            # Explicit Ontario mentions with "on"
            ("What's going on in Ontario?", True),  # "on" as word
            ("Parks on the Ontario border", True),  # "on" as word
        ],
    )
    def test_ontario_query_detection(self, query, expected):
        """Test that Ontario queries are correctly detected."""
        result = detect_ontario_query(query)
        assert (
            result == expected
        ), f"Query '{query}' should {'be' if expected else 'not be'} detected as Ontario"

    def test_detect_with_context_previous_agent(self):
        """Test detection using previous agent context."""
        query = "Tell me more about that area"
        context = {"previous_agent": "ontario"}

        result = detect_ontario_query(query, context)
        assert result is True

    def test_detect_with_context_user_location(self):
        """Test detection using user location context."""
        query = "What parks are nearby?"
        context = {"user_location": {"province": "Ontario"}}

        result = detect_ontario_query(query, context)
        assert result is True

    def test_detect_without_context(self):
        """Test that generic queries without context go to global."""
        query = "What can you tell me about parks?"

        result = detect_ontario_query(query)
        assert result is False


class TestSelectAgent:
    """Test agent selection logic."""

    @pytest.mark.parametrize(
        "query,expected_agent",
        [
            # Ontario queries
            ("Parks near Peterborough", "ontario"),
            ("Algonquin deforestation", "ontario"),
            ("Toronto urban parks", "ontario"),
            ("Ontario biodiversity", "ontario"),
            # Global queries
            ("Amazon rainforest", "global"),
            ("California wildfires", "global"),
            ("African savanna", "global"),
            # Ambiguous queries default to global
            ("Forest data", "global"),
            ("Protected areas", "global"),
        ],
    )
    def test_agent_selection(self, query, expected_agent):
        """Test that correct agent is selected for queries."""
        agent = select_agent(query)
        assert agent == expected_agent

    def test_force_agent_selection(self):
        """Test forcing a specific agent."""
        query = "Parks in California"  # Would normally be global

        # Force Ontario
        agent = select_agent(query, force="ontario")
        assert agent == "ontario"

        # Force global
        agent = select_agent(query, force="global")
        assert agent == "global"

    def test_agent_selection_with_context(self):
        """Test agent selection with context."""
        query = "Tell me more"  # Generic query

        # With Ontario context
        context = {"previous_agent": "ontario"}
        agent = select_agent(query, context)
        assert agent == "ontario"

        # With global context
        context = {"previous_agent": "global"}
        agent = select_agent(query, context)
        assert agent == "global"


class TestGetAgentDescription:
    """Test agent description retrieval."""

    def test_ontario_description(self):
        """Test Ontario agent description."""
        desc = get_agent_description("ontario")
        assert "Ontario" in desc
        assert "provincial parks" in desc.lower()

    def test_global_description(self):
        """Test global agent description."""
        desc = get_agent_description("global")
        assert "Global" in desc
        assert "worldwide" in desc.lower()

    def test_unknown_agent(self):
        """Test description for unknown agent type."""
        desc = get_agent_description("unknown")
        assert "Unknown" in desc


class TestCanSwitchAgents:
    """Test agent switching logic."""

    def test_allow_switch_short_conversation(self):
        """Test switching is allowed for short conversations."""
        conversation = ["Hello", "Hi there"]

        can_switch = can_switch_agents("global", "ontario", conversation)
        assert can_switch is True

    def test_block_switch_during_workflow(self):
        """Test switching is blocked during active workflow."""
        conversation = [
            "Show me parks in Ontario",
            "I've selected Algonquin Park",
            "Great, analyzing that area",
        ]

        can_switch = can_switch_agents("ontario", "global", conversation)
        assert can_switch is False

    def test_allow_switch_after_workflow(self):
        """Test switching is allowed after workflow completes."""
        conversation = [
            "Show me parks in Ontario",
            "I've found Algonquin Park",
            "Tell me about Brazil now",  # New topic
        ]

        # Mock as long conversation without active workflow indicators
        can_switch = can_switch_agents("ontario", "global", conversation)
        # Should allow since no active workflow
        assert can_switch is True

    @pytest.mark.parametrize(
        "conversation,expected",
        [
            # Short conversation - allow
            (["Q1", "A1"], True),
            # Long conversation without workflow - allow
            (
                [
                    "Q1",
                    "A1",
                    "Q2",
                    "A2",
                    "New topic about different region",
                ],
                True,
            ),
            # Active workflow - block
            (
                [
                    "Q1",
                    "Selected area",
                    "Pulling data for analysis",
                ],
                False,
            ),
        ],
    )
    def test_switching_scenarios(self, conversation, expected):
        """Test various switching scenarios."""
        can_switch = can_switch_agents("ontario", "global", conversation)
        assert can_switch == expected


class TestWordBoundaryMatching:
    """Test that short keywords use word boundary matching."""

    def test_on_as_word_boundary(self):
        """Test 'on' matches only as whole word."""
        # Should match
        assert detect_ontario_query("Parks on the lake") is True
        assert detect_ontario_query("What's going on in this area?") is True

        # Should NOT match
        assert detect_ontario_query("Deforestation trends") is False
        assert detect_ontario_query("Information about parks") is False
        assert detect_ontario_query("Conservation efforts") is False

    def test_longer_keywords_substring_match(self):
        """Test that longer keywords use substring matching."""
        # "ontario" in "Ontario" should match
        assert detect_ontario_query("Ontario parks") is True

        # "algonquin" in "Algonquin" should match
        assert detect_ontario_query("Algonquin wilderness") is True

        # "peterborough" should match
        assert detect_ontario_query("Peterborough region") is True
