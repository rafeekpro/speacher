"""
Test configuration and fixtures for backend tests.
"""

import os
import sys
import pytest
from unittest.mock import Mock, MagicMock

# Set test environment variables before importing backend modules
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("TESTING", "true")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


@pytest.fixture
def mock_db():
    """Mock database connection."""
    mock_engine = MagicMock()
    mock_session = MagicMock()
    return mock_engine, mock_session
