"""Test script for Ontario Agent integration.

This script tests the Ontario agent's tools and routing logic.
"""

import asyncio

from src.agents.agent_router import select_agent, get_agent_description


def test_agent_routing():
    """Test the agent routing logic."""
    print("=" * 60)
    print("Ontario Agent Routing Test")
    print("=" * 60)
    print()

    test_cases = [
        # Ontario queries
        ("What parks are near Peterborough?", "ontario"),
        ("Tell me about Algonquin Park", "ontario"),
        ("Curve Lake First Nation territory information", "ontario"),
        ("Conservation areas in the Kawarthas", "ontario"),
        ("Toronto parks", "ontario"),
        ("Ontario protected areas", "ontario"),
        # Global queries
        ("Deforestation in the Amazon", "global"),
        ("Protected areas in California", "global"),
        ("Forest loss in Brazil over the past year", "global"),
        ("What's happening in Yellowstone?", "global"),
        # Ambiguous queries (should go global by default)
        ("What can you do?", "global"),
        ("Show me forest data", "global"),
    ]

    passed = 0
    failed = 0

    for query, expected_agent in test_cases:
        selected = select_agent(query)
        status = "✓" if selected == expected_agent else "✗"

        if selected == expected_agent:
            passed += 1
        else:
            failed += 1

        print(f"{status} Query: {query}")
        print(f"  Expected: {expected_agent}, Got: {selected}")
        if selected != expected_agent:
            print(f"  MISMATCH!")
        print()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


async def test_ontario_agent_import():
    """Test that Ontario agent can be imported and initialized."""
    print("\n" + "=" * 60)
    print("Ontario Agent Import Test")
    print("=" * 60)
    print()

    try:
        from src.agents import (
            fetch_ontario_agent_anonymous,
            select_agent,
            AgentType,
        )

        print("✓ Successfully imported Ontario agent functions")

        # Test agent description
        desc = get_agent_description("ontario")
        print(f"✓ Ontario agent description: {desc}")

        desc_global = get_agent_description("global")
        print(f"✓ Global agent description: {desc_global}")

        print("\n✓ Ontario agent integration successful!")
        return True

    except Exception as e:
        print(f"✗ Error importing Ontario agent: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_ontario_tools_import():
    """Test that Ontario tools can be imported."""
    print("\n" + "=" * 60)
    print("Ontario Tools Import Test")
    print("=" * 60)
    print()

    try:
        from src.tools.ontario import (
            pick_ontario_area,
            ontario_proximity_search,
            compare_ontario_areas,
            get_ontario_statistics,
        )

        print("✓ Successfully imported all Ontario tools:")
        print("  - pick_ontario_area")
        print("  - ontario_proximity_search")
        print("  - compare_ontario_areas")
        print("  - get_ontario_statistics")

        return True

    except Exception as e:
        print(f"✗ Error importing Ontario tools: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n🍁 Ontario Nature Watch Agent Test Suite\n")

    # Test 1: Agent routing
    routing_ok = test_agent_routing()

    # Test 2: Agent import
    import_ok = await test_ontario_agent_import()

    # Test 3: Tools import
    tools_ok = await test_ontario_tools_import()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Agent Routing:  {'PASS' if routing_ok else 'FAIL'}")
    print(f"Agent Import:   {'PASS' if import_ok else 'FAIL'}")
    print(f"Tools Import:   {'PASS' if tools_ok else 'FAIL'}")
    print("=" * 60)

    if routing_ok and import_ok and tools_ok:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
