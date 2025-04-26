"""Integration tests for the Sets API endpoints."""
import pytest
from fastapi import status
from app.services.domino_service import domino_sets, DominoService


class TestSetsAPI:
    """Integration tests for domino set management endpoints."""

    def test_create_set(self, client):
        """Test creating a new domino set."""
        # Send request to create a set
        response = client.post(
            "/api/set/new",
            json={"type": "double-six", "sets": 1}
        )
        
        # Verify response
        assert response.status_code == status.HTTP_201_CREATED
        
        # Check response structure
        data = response.json()
        assert "set_id" in data
        assert data["type"] == "double-six"
        assert data["tiles_remaining"] == 28
        
        # Verify Location header
        assert "Location" in response.headers
        assert response.headers["Location"] == f"/api/set/{data['set_id']}"
        
        # Verify set exists in storage
        assert data["set_id"] in domino_sets

    def test_create_set_invalid_type(self, client):
        """Test creating a set with invalid type."""
        response = client.post(
            "/api/set/new",
            json={"type": "invalid-type", "sets": 1}
        )
        
        # Verify response - FastAPI uses 422 for validation errors by default
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "must be one of" in response.json()["detail"][0]["msg"].lower()

    def test_create_set_invalid_sets_count(self, client):
        """Test creating a set with invalid sets count."""
        response = client.post(
            "/api/set/new",
            json={"type": "double-six", "sets": 0}
        )
        
        # Verify response
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_set_state(self, client, sample_domino_set):
        """Test getting the state of a domino set."""
        set_id, _ = sample_domino_set
        
        # Send request to get set state
        response = client.get(f"/api/set/{set_id}")
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        
        # Check response structure
        data = response.json()
        assert data["set_id"] == set_id
        assert data["type"] == "double-six"
        assert data["tiles_remaining"] == 28
        assert "piles" in data
        assert isinstance(data["piles"], dict)

    def test_get_set_state_nonexistent(self, client):
        """Test getting a nonexistent set state."""
        response = client.get("/api/set/nonexistent-id")
        
        # Verify response
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_list_sets_empty(self, client):
        """Test listing sets when none exist."""
        response = client.get("/api/set")
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_list_sets(self, client):
        """Test listing sets."""
        # Create two sets
        set_id1, _ = DominoService.create_set("double-six", 1)
        set_id2, _ = DominoService.create_set("double-nine", 1)
        
        # Send request to list sets
        response = client.get("/api/set")
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        
        # Check response structure
        data = response.json()
        assert len(data) == 2
        
        # Extract set_ids from response
        set_ids = [item["set_id"] for item in data]
        assert set_id1 in set_ids
        assert set_id2 in set_ids

    def test_shuffle_set_remaining(self, client, sample_domino_set):
        """Test shuffling remaining tiles in a set."""
        set_id, _ = sample_domino_set
        
        # Send request to shuffle remaining tiles
        response = client.post(
            f"/api/set/{set_id}/shuffle",
            params={"remaining": True}
        )
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        
        # Check response structure
        data = response.json()
        assert data["set_id"] == set_id
        assert data["tiles_remaining"] == 28
        assert "message" in data
        assert "shuffled" in data["message"].lower()

    def test_shuffle_set_all(self, client, sample_domino_set_with_piles):
        """Test shuffling all tiles in a set."""
        set_id, domino_set = sample_domino_set_with_piles
        
        # Capture initial state
        initial_boneyard_count = len(domino_set["tiles"])
        assert initial_boneyard_count < 28  # Some tiles should be in piles
        
        # Send request to shuffle all tiles
        response = client.post(
            f"/api/set/{set_id}/shuffle",
            params={"remaining": False}
        )
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        
        # Check response structure
        data = response.json()
        assert data["set_id"] == set_id
        assert data["tiles_remaining"] == 28  # All tiles should be back in boneyard
        
        # Verify state change
        updated_set = DominoService.get_set(set_id)
        assert len(updated_set["tiles"]) == 28
        assert updated_set["piles"] == {}  # Piles should be empty

    def test_draw_tiles(self, client, sample_domino_set):
        """Test drawing tiles from a set."""
        set_id, domino_set = sample_domino_set
        
        # Remember the first few tiles
        expected_tiles = domino_set["tiles"][:5]
        
        # Send request to draw tiles
        response = client.post(
            f"/api/set/{set_id}/draw",
            json={"count": 5}
        )
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        
        # Check response structure
        data = response.json()
        assert data["set_id"] == set_id
        assert data["tiles_remaining"] == 23
        assert data["tiles_drawn"] == expected_tiles
        
        # Verify state change
        updated_set = DominoService.get_set(set_id)
        assert len(updated_set["tiles"]) == 23
        for tile in expected_tiles:
            assert tile not in updated_set["tiles"]

    def test_draw_tiles_too_many(self, client, sample_domino_set):
        """Test drawing more tiles than available."""
        set_id, _ = sample_domino_set
        
        # Send request to draw too many tiles
        response = client.post(
            f"/api/set/{set_id}/draw",
            json={"count": 100}
        )
        
        # Verify response
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "cannot draw" in response.json()["detail"].lower()

    def test_delete_set(self, client, sample_domino_set):
        """Test deleting a domino set."""
        set_id, _ = sample_domino_set
        
        # Send request to delete set
        response = client.delete(f"/api/set/{set_id}")
        
        # Verify response
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify set is gone
        assert set_id not in domino_sets
        
        # Verify 404 on second attempt
        response2 = client.delete(f"/api/set/{set_id}")
        assert response2.status_code == status.HTTP_404_NOT_FOUND 