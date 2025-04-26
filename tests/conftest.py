"""Pytest configuration and fixtures for testing the Domino Boneyard API."""
import os
import pytest
import asyncio
from unittest.mock import patch
from fastapi.testclient import TestClient
from asyncio import AbstractEventLoop

# Set test environment
os.environ["DOMINO_ENV"] = "testing"
os.environ["DOMINO_USE_REDIS"] = "false"  # Use in-memory storage for tests

# Import app after setting environment variables
from app.core.app import create_app
from app.services.domino_service import DominoService, domino_sets, last_accessed


@pytest.fixture(scope="session")
def event_loop() -> AbstractEventLoop:
    """Create and yield an event loop for asyncio tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def app():
    """Create a test application."""
    return create_app()


@pytest.fixture
def client(app):
    """Create a test client for the application."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_domino_storage():
    """Clean domino_sets and last_accessed before and after each test."""
    # Clear data before test
    domino_sets.clear()
    last_accessed.clear()
    yield
    # Clear data after test
    domino_sets.clear()
    last_accessed.clear()


@pytest.fixture
def sample_domino_set():
    """Create a sample domino set for testing."""
    set_type = "double-six"
    num_sets = 1
    set_id, domino_set = DominoService.create_set(set_type, num_sets)
    return set_id, domino_set


@pytest.fixture
def sample_domino_set_with_piles(sample_domino_set):
    """Create a sample domino set with piles for testing."""
    set_id, domino_set = sample_domino_set
    
    # Create two piles
    pile1_name = "player1"
    pile2_name = "player2"
    
    # Take first 7 tiles for player1
    player1_tiles = domino_set["tiles"][:7]
    DominoService.add_to_pile(domino_set, pile1_name, player1_tiles, set_id)
    
    # Take next 7 tiles for player2
    player2_tiles = domino_set["tiles"][:7]  # Now these are the first 7 after previous removal
    DominoService.add_to_pile(domino_set, pile2_name, player2_tiles, set_id)
    
    return set_id, domino_set


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing Redis functionality."""
    with patch("app.services.domino_service.redis_client") as mock_client:
        mock_client.get.return_value = None  # Default behavior for get
        yield mock_client 