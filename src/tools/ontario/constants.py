"""Constants and configuration for Ontario Nature Watch tools."""

# Table names for Ontario areas
ONTARIO_PARKS_TABLE = "ontario_parks"
ONTARIO_CONSERVATION_AREAS_TABLE = "ontario_conservation_areas"
WILLIAMS_TREATY_TERRITORIES_TABLE = "williams_treaty_first_nations"

# Source IDs for area identification
ONTARIO_SOURCE_IDS = {
    "ontario_parks": 1,
    "conservation_areas": 2,
    "williams_treaty": 3,
}

# Williams Treaty First Nations
WILLIAMS_TREATY_FIRST_NATIONS = [
    "Alderville First Nation",
    "Curve Lake First Nation",
    "Hiawatha First Nation",
    "Mississaugas of Scugog Island First Nation",
    "Chippewas of Beausoleil First Nation",
    "Chippewas of Georgina Island First Nation",
    "Chippewas of Rama First Nation",
]

# Area type descriptions
AREA_TYPE_DESCRIPTIONS = {
    "park": "Ontario Provincial Parks - protected areas managed by Ontario Parks",
    "conservation": "Conservation Areas - lands managed by Conservation Authorities",
    "treaty": "Williams Treaty First Nations Territories - traditional territories of treaty signatory nations",
}

# Cultural sensitivity guidelines
CULTURAL_SENSITIVITY_GUIDELINES = """
When discussing Williams Treaty First Nations territories:

1. Acknowledge Traditional Territory
   - These are the traditional territories of the Williams Treaty First Nations
   - The land has been stewarded by Indigenous peoples for thousands of years

2. Respectful Language
   - Use proper First Nations names (e.g., "Curve Lake First Nation", not "Curve Lake")
   - Avoid possessive language - say "the territory of..." not "their land"
   - Acknowledge continuing relationship with the land

3. Treaty Context
   - The Williams Treaties were signed in 1923
   - They cover approximately 20,000 square kilometers in central Ontario
   - Treaty rights include hunting, fishing, and gathering

4. Data Sharing
   - Environmental data about these territories should be shared respectfully
   - Acknowledge First Nations as knowledge keepers
   - Be aware that some information may be culturally sensitive

5. Current Engagement
   - First Nations continue active stewardship of these lands
   - Many are engaged in conservation and environmental monitoring
   - Respect ongoing governance and decision-making authority
"""

# Ontario Parks categories
PARK_DESIGNATIONS = [
    "Wilderness Park",
    "Nature Reserve",
    "Natural Environment Park",
    "Waterway Park",
    "Recreational Park",
    "Cultural Heritage Park",
]

# Conservation Authority regions
CONSERVATION_AUTHORITIES = [
    "Kawartha Conservation",
    "Otonabee Region Conservation Authority",
    "Central Lake Ontario Conservation Authority",
    "Lake Simcoe Region Conservation Authority",
    "Trent Conservation Coalition",
    "Ganaraska Region Conservation Authority",
]

# Default search radius (in meters) for proximity searches
DEFAULT_SEARCH_RADIUS_M = 50000  # 50km

# Maximum results to return
MAX_RESULTS = 25
