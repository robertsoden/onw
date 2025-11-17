"""Tests for Ontario Data Handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.tools.data_handlers.ontario_handler import (
    OntarioDataHandler,
    OntarioConfig,
    INaturalistClient,
    EBirdClient,
)


@pytest.fixture
def ontario_config():
    """Create test configuration."""
    return OntarioConfig(
        ebird_api_key="test_ebird_key",
        datastream_api_key="test_datastream_key",
        inat_rate_limit=60,
        cache_ttl_hours=24,
    )


@pytest.fixture
def ontario_handler(ontario_config):
    """Create Ontario handler instance."""
    return OntarioDataHandler(ontario_config)


@pytest.fixture
def algonquin_aoi():
    """Algonquin Park test AOI."""
    return {
        "name": "Algonquin Provincial Park",
        "type": "park",
        "subtype": "protected-area",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-78.5, 45.5],
                    [-78.5, 46.0],
                    [-77.5, 46.0],
                    [-77.5, 45.5],
                    [-78.5, 45.5],
                ]
            ],
        },
    }


@pytest.fixture
def sample_inat_response():
    """Sample iNaturalist API response."""
    return {
        "total_results": 2,
        "page": 1,
        "per_page": 200,
        "results": [
            {
                "id": 123456,
                "observed_on": "2024-06-15",
                "time_observed_at": "2024-06-15T14:30:00-05:00",
                "quality_grade": "research",
                "license": "CC-BY-NC",
                "location": "44.2312,-78.2642",
                "place_guess": "Algonquin Park, ON",
                "positional_accuracy": 10,
                "taxon": {
                    "id": 47219,
                    "name": "Pinus strobus",
                    "preferred_common_name": "Eastern White Pine",
                    "rank": "species",
                    "iconic_taxon_name": "Plantae",
                },
                "user": {"id": 12345, "login": "naturalist123"},
                "photos": [
                    {
                        "id": 987654,
                        "url": "https://inaturalist-open-data.s3.amazonaws.com/photos/987654/medium.jpg",
                    }
                ],
                "identifications_count": 3,
                "comments_count": 1,
            },
            {
                "id": 123457,
                "observed_on": "2024-06-16",
                "time_observed_at": "2024-06-16T10:15:00-05:00",
                "quality_grade": "research",
                "license": "CC-BY",
                "location": "44.2500,-78.2700",
                "place_guess": "Algonquin Park, ON",
                "positional_accuracy": 15,
                "taxon": {
                    "id": 9853,
                    "name": "Alces alces",
                    "preferred_common_name": "Moose",
                    "rank": "species",
                    "iconic_taxon_name": "Mammalia",
                },
                "user": {"id": 12346, "login": "wildlife_watcher"},
                "photos": [],
                "identifications_count": 5,
                "comments_count": 2,
            },
        ],
    }


@pytest.fixture
def sample_ebird_response():
    """Sample eBird API response."""
    return [
        {
            "speciesCode": "norcar",
            "comName": "Northern Cardinal",
            "sciName": "Cardinalis cardinalis",
            "locId": "L123456",
            "locName": "Algonquin Park--Visitor Centre",
            "obsDt": "2024-06-15 14:30",
            "howMany": 2,
            "lat": 45.5,
            "lng": -78.3,
            "obsValid": True,
            "obsReviewed": True,
            "locationPrivate": False,
            "subId": "S987654321",
        },
        {
            "speciesCode": "gcrrav",
            "comName": "Common Raven",
            "sciName": "Corvus corax",
            "locId": "L123457",
            "locName": "Algonquin Park--Canoe Lake",
            "obsDt": "2024-06-15 15:45",
            "howMany": 1,
            "lat": 45.6,
            "lng": -78.4,
            "obsValid": True,
            "obsReviewed": True,
            "locationPrivate": False,
            "subId": "S987654322",
        },
    ]


class TestOntarioDataHandler:
    """Test Ontario Data Handler functionality."""

    def test_can_handle_inat(self, ontario_handler):
        """Test handler recognizes iNaturalist datasets."""
        dataset = {"source": "iNaturalist", "type": "observations"}
        assert ontario_handler.can_handle(dataset) is True

    def test_can_handle_ebird(self, ontario_handler):
        """Test handler recognizes eBird datasets."""
        dataset = {"source": "eBird", "type": "observations"}
        assert ontario_handler.can_handle(dataset) is True

    def test_cannot_handle_unknown(self, ontario_handler):
        """Test handler rejects unknown datasets."""
        dataset = {"source": "Unknown", "type": "observations"}
        assert ontario_handler.can_handle(dataset) is False

    def test_get_bounds_from_polygon_aoi(self, ontario_handler, algonquin_aoi):
        """Test extracting bounds from polygon AOI."""
        bounds = ontario_handler._get_bounds_from_aoi(algonquin_aoi)
        assert bounds == (45.5, -78.5, 46.0, -77.5)

    def test_get_bounds_from_point(self, ontario_handler):
        """Test extracting bounds from point geometry."""
        point_aoi = {
            "geometry": {"type": "Point", "coordinates": [-78.3, 44.3]},
        }
        bounds = ontario_handler._get_bounds_from_aoi(point_aoi)
        # Should create buffer around point
        assert len(bounds) == 4
        assert bounds[0] < 44.3 < bounds[2]  # lat within bounds
        assert bounds[1] < -78.3 < bounds[3]  # lon within bounds

    def test_point_in_bounds(self, ontario_handler):
        """Test point in bounds checking."""
        bounds = (44.0, -79.0, 45.0, -78.0)
        assert ontario_handler._point_in_bounds((44.5, -78.5), bounds) is True
        assert ontario_handler._point_in_bounds((43.5, -78.5), bounds) is False
        assert ontario_handler._point_in_bounds((44.5, -79.5), bounds) is False

    @pytest.mark.asyncio
    async def test_pull_inat_data_success(
        self, ontario_handler, algonquin_aoi, sample_inat_response
    ):
        """Test successful iNaturalist data pull."""
        with patch("aiohttp.ClientSession") as mock_session:
            # Mock the API response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=sample_inat_response)

            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
                mock_response
            )

            result = await ontario_handler.pull_data(
                query="Test query",
                aoi=algonquin_aoi,
                subregion_aois=[],
                subregion="",
                subtype="park",
                dataset={"source": "iNaturalist", "type": "observations"},
                start_date="2024-06-01",
                end_date="2024-06-30",
            )

            assert result.success is True
            assert result.data_points_count == 2
            assert len(result.data) == 2
            assert result.data[0]["source"] == "iNaturalist"
            assert result.data[0]["common_name"] == "Eastern White Pine"

    @pytest.mark.asyncio
    async def test_pull_ebird_data_success(
        self, ontario_handler, algonquin_aoi, sample_ebird_response
    ):
        """Test successful eBird data pull."""
        with patch("aiohttp.ClientSession") as mock_session:
            # Mock the API response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=sample_ebird_response)

            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
                mock_response
            )

            result = await ontario_handler.pull_data(
                query="Test birds query",
                aoi=algonquin_aoi,
                subregion_aois=[],
                subregion="",
                subtype="park",
                dataset={"source": "eBird", "type": "observations"},
                start_date="2024-06-01",
                end_date="2024-06-30",
            )

            assert result.success is True
            assert result.data_points_count == 2
            assert len(result.data) == 2
            assert result.data[0]["source"] == "eBird"
            assert result.data[0]["common_name"] == "Northern Cardinal"

    @pytest.mark.asyncio
    async def test_pull_data_no_ebird_key(self, algonquin_aoi):
        """Test eBird data pull without API key."""
        handler = OntarioDataHandler(OntarioConfig(ebird_api_key=None))

        result = await handler.pull_data(
            query="Test query",
            aoi=algonquin_aoi,
            subregion_aois=[],
            subregion="",
            subtype="park",
            dataset={"source": "eBird", "type": "observations"},
            start_date="2024-06-01",
            end_date="2024-06-30",
        )

        assert result.success is False
        assert "API key not configured" in result.message

    @pytest.mark.asyncio
    async def test_pull_data_unsupported_source_falls_back(
        self, ontario_handler, algonquin_aoi
    ):
        """Test that unsupported Ontario source falls back to global datasets."""
        # Mock the fallback handler
        from unittest.mock import AsyncMock

        mock_fallback = AsyncMock()
        mock_fallback.can_handle.return_value = True
        mock_fallback.pull_data = AsyncMock(
            return_value=DataPullResult(
                success=True,
                data={"tree_cover": 75.5},
                message="Tree cover data retrieved",
                data_points_count=1,
            )
        )
        ontario_handler.fallback_handler = mock_fallback

        dataset = {"source": "TreeCoverGFW", "dataset_name": "Tree cover"}
        result = await ontario_handler.pull_data(
            query="Tree cover query",
            aoi=algonquin_aoi,
            subregion_aois=[],
            subregion="",
            subtype="park",
            dataset=dataset,
            start_date="2024-01-01",
            end_date="2024-12-31",
        )

        # Should succeed via fallback
        assert result.success is True
        assert "[Using global dataset]" in result.message
        assert mock_fallback.pull_data.called

    @pytest.mark.asyncio
    async def test_inat_no_data_falls_back(self, ontario_handler, algonquin_aoi):
        """Test that when iNaturalist returns no data, it falls back."""
        with patch("aiohttp.ClientSession") as mock_session:
            # Mock empty iNaturalist response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"results": []})

            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
                mock_response
            )

            # Mock fallback handler
            from unittest.mock import AsyncMock

            mock_fallback = AsyncMock()
            mock_fallback.can_handle.return_value = True
            mock_fallback.pull_data = AsyncMock(
                return_value=DataPullResult(
                    success=True,
                    data={"forest_data": "some_data"},
                    message="Fallback data retrieved",
                    data_points_count=10,
                )
            )
            ontario_handler.fallback_handler = mock_fallback

            result = await ontario_handler.pull_data(
                query="Biodiversity query",
                aoi=algonquin_aoi,
                subregion_aois=[],
                subregion="",
                subtype="park",
                dataset={"source": "iNaturalist", "type": "observations"},
                start_date="2024-06-01",
                end_date="2024-06-30",
            )

            # Should succeed via fallback
            assert result.success is True
            assert "[Using global dataset]" in result.message


class TestINaturalistClient:
    """Test iNaturalist client functionality."""

    def test_transform_observation(self, sample_inat_response):
        """Test observation transformation."""
        obs = sample_inat_response["results"][0]
        transformed = INaturalistClient.transform_observation(obs)

        assert transformed["source"] == "iNaturalist"
        assert transformed["observation_id"] == "123456"
        assert transformed["scientific_name"] == "Pinus strobus"
        assert transformed["common_name"] == "Eastern White Pine"
        assert transformed["quality_grade"] == "research"
        assert transformed["location"]["type"] == "Point"
        assert transformed["location"]["coordinates"] == [-78.2642, 44.2312]
        assert transformed["observer"] == "naturalist123"
        assert len(transformed["photos"]) == 1

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting functionality."""
        client = INaturalistClient(rate_limit=60)

        # First request should not wait
        start = datetime.now()
        await client._rate_limit_wait()
        first_duration = (datetime.now() - start).total_seconds()

        assert first_duration < 0.1  # Should be immediate

        # Second request immediately after should wait
        start = datetime.now()
        await client._rate_limit_wait()
        second_duration = (datetime.now() - start).total_seconds()

        assert second_duration >= 0.9  # Should wait ~1 second (60 req/min)


class TestEBirdClient:
    """Test eBird client functionality."""

    def test_transform_observation(self, sample_ebird_response):
        """Test eBird observation transformation."""
        obs = sample_ebird_response[0]
        transformed = EBirdClient.transform_observation(obs)

        assert transformed["source"] == "eBird"
        assert transformed["observation_id"] == "S987654321"
        assert transformed["species_code"] == "norcar"
        assert transformed["common_name"] == "Northern Cardinal"
        assert transformed["scientific_name"] == "Cardinalis cardinalis"
        assert transformed["location"]["type"] == "Point"
        assert transformed["location"]["coordinates"] == [-78.3, 45.5]
        assert transformed["count"] == 2
        assert transformed["valid"] is True

    @pytest.mark.asyncio
    async def test_ebird_client_init(self):
        """Test eBird client initialization."""
        client = EBirdClient(api_key="test_key")
        assert client.api_key == "test_key"
        assert client.headers == {"x-ebirdapitoken": "test_key"}


class TestOntarioConfig:
    """Test Ontario configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = OntarioConfig()
        assert config.ebird_api_key is None
        assert config.datastream_api_key is None
        assert config.inat_rate_limit == 60
        assert config.cache_ttl_hours == 24

    def test_custom_config(self):
        """Test custom configuration values."""
        config = OntarioConfig(
            ebird_api_key="my_key",
            datastream_api_key="my_stream_key",
            inat_rate_limit=120,
            cache_ttl_hours=12,
        )
        assert config.ebird_api_key == "my_key"
        assert config.datastream_api_key == "my_stream_key"
        assert config.inat_rate_limit == 120
        assert config.cache_ttl_hours == 12
