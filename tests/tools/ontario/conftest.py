"""Test fixtures for Ontario tools tests."""

from unittest.mock import AsyncMock, patch

import pytest
import structlog


# Mock database pool globally for all Ontario tool tests
@pytest.fixture(scope="session", autouse=True)
def mock_database_pool():
    """Mock database connection pool to avoid requiring running PostgreSQL."""
    with patch("src.utils.database.get_global_pool") as mock_pool:
        mock_pool.return_value = AsyncMock()
        yield mock_pool


@pytest.fixture
def structlog_context():
    """Set up structlog context for tests."""
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        user_id="test-user-123",
        request_id="test-request-456",
    )
    yield
    structlog.contextvars.clear_contextvars()
