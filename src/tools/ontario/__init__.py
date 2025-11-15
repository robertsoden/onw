"""Ontario-specific tools for the Nature Watch agent."""

from src.tools.ontario.compare_ontario_areas import compare_ontario_areas
from src.tools.ontario.get_ontario_statistics import get_ontario_statistics
from src.tools.ontario.ontario_proximity_search import ontario_proximity_search
from src.tools.ontario.pick_ontario_area import pick_ontario_area

__all__ = [
    "pick_ontario_area",
    "ontario_proximity_search",
    "compare_ontario_areas",
    "get_ontario_statistics",
]
