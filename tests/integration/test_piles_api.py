"""Integration tests for the Piles API endpoints."""
import pytest
from fastapi import status
from app.services.domino_service import DominoService


class TestPilesAPI:
    """Integration tests for domino pile management endpoints."""

    def test_create_pile(self, client, sample_domino_set):
        """Test creating a new pile."""
        set_id, _ = sample_domino_set
        
        # Send request to create a pile
        response = client.post(
            f"/api/set/{set_id}/pile/new",
            json={"name": "test_pile"}
        )
        
        # Verify response
        assert response.status_code == status.HTTP_201_CREATED
        
        # Check response structure
        data = response.json()
        assert data["set_id"] == set_id
        assert data["pile_name"] == "test_pile"
        assert data["tiles"] == []
        
        # Verify Location header
        assert "Location" in response.headers
        assert response.headers["Location"] == f"/api/set/{set_id}/pile/test_pile"
        
        # Verify pile exists in set
        updated_set = DominoService.get_set(set_id)
        assert "test_pile" in updated_set["piles"]
        assert updated_set["piles"]["test_pile"] == []

    def test_create_pile_duplicate_name(self, client, sample_domino_set):
        """Test creating a pile with a duplicate name."""
        set_id, _ = sample_domino_set
        
        # Create pile
        DominoService.create_pile(set_id, "test_pile")
        
        # Attempt to create a pile with the same name
        response = client.post(
            f"/api/set/{set_id}/pile/new",
            json={"name": "test_pile"}
        )
        
        # Verify response
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"].lower()

    def test_create_pile_nonexistent_set(self, client):
        """Test creating a pile for a nonexistent set."""
        response = client.post(
            "/api/set/nonexistent-id/pile/new",
            json={"name": "test_pile"}
        )
        
        # Verify response
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_get_pile(self, client, sample_domino_set):
        """Test getting a pile."""
        set_id, domino_set = sample_domino_set
        
        # Create pile and add some tiles
        DominoService.create_pile(set_id, "test_pile")
        DominoService.add_to_pile(domino_set, "test_pile", ["12", "34"])
        
        # Send request to get pile
        response = client.get(f"/api/set/{set_id}/pile/test_pile")
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        
        # Check response structure
        data = response.json()
        assert data["set_id"] == set_id
        assert data["pile_name"] == "test_pile"
        assert data["tiles"] == ["12", "34"]

    def test_get_pile_nonexistent(self, client, sample_domino_set):
        """Test getting a nonexistent pile."""
        set_id, _ = sample_domino_set
        
        response = client.get(f"/api/set/{set_id}/pile/nonexistent")
        
        # Verify response
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "nonexistent" in response.json()["detail"].lower()

    def test_add_to_pile(self, client, sample_domino_set):
        """Test adding tiles to a pile."""
        set_id, domino_set = sample_domino_set
        
        # Create pile
        DominoService.create_pile(set_id, "test_pile")
        
        # Get tiles to add
        tiles_to_add = domino_set["tiles"][:3]
        
        # Send request to add tiles to pile
        response = client.post(
            f"/api/set/{set_id}/pile/test_pile/add",
            json={"tiles": tiles_to_add}
        )
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        
        # Check response structure
        data = response.json()
        assert data["set_id"] == set_id
        assert "piles" in data
        assert "tiles_remaining" in data
        
        # Verify tiles added to pile
        updated_set = DominoService.get_set(set_id)
        assert "test_pile" in updated_set["piles"]
        assert len(updated_set["piles"]["test_pile"]) > 0

    def test_add_to_pile_tiles_not_in_boneyard(self, client, sample_domino_set):
        """Test adding tiles not in the boneyard to a pile."""
        set_id, _ = sample_domino_set
        
        # Create pile
        DominoService.create_pile(set_id, "test_pile")
        
        # Send request to add tiles not in the boneyard
        response = client.post(
            f"/api/set/{set_id}/pile/test_pile/add",
            json={"tiles": [[10, 10], [11, 11]]}
        )
        
        # Verify response - expecting a validation error (422)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_piles(self, client, sample_domino_set):
        """Test listing piles."""
        set_id, _ = sample_domino_set
        
        # Create piles
        DominoService.create_pile(set_id, "pile1")
        DominoService.create_pile(set_id, "pile2")
        
        # Send request to list piles
        response = client.get(f"/api/set/{set_id}/pile")
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        
        # Check response structure
        data = response.json()
        assert isinstance(data, list)
        pile_names = [pile["pile_name"] for pile in data]
        assert "pile1" in pile_names
        assert "pile2" in pile_names
        assert all(pile["set_id"] == set_id for pile in data)

    def test_list_piles_empty(self, client, sample_domino_set):
        """Test listing piles when none exist."""
        set_id, _ = sample_domino_set
        
        # Send request to list piles
        response = client.get(f"/api/set/{set_id}/pile")
        
        # Verify response
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_delete_pile(self, client, sample_domino_set):
        """Test deleting a pile."""
        set_id, domino_set = sample_domino_set
        
        # Create pile and add tiles
        DominoService.create_pile(set_id, "test_pile")
        tiles = domino_set["tiles"][:3]
        DominoService.add_to_pile(domino_set, "test_pile", tiles)
        
        # Initial remaining tiles count
        initial_count = len(DominoService.get_set(set_id)["tiles"])
        
        # Send request to delete pile
        response = client.delete(f"/api/set/{set_id}/pile/test_pile")
        
        # Verify response
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify pile is gone
        updated_set = DominoService.get_set(set_id)
        assert "test_pile" not in updated_set["piles"]
        
        # Verify tiles were returned to boneyard
        assert len(updated_set["tiles"]) == initial_count + 3

    def test_delete_pile_nonexistent(self, client, sample_domino_set):
        """Test deleting a nonexistent pile."""
        set_id, _ = sample_domino_set
        
        response = client.delete(f"/api/set/{set_id}/pile/nonexistent")
        
        # Verify response
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "nonexistent" in response.json()["detail"].lower() 