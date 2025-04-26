"""Unit tests for the DominoService class."""
import pytest
from fastapi import HTTPException
from unittest.mock import patch, MagicMock

from app.services.domino_service import DominoService, domino_sets, last_accessed


class TestDominoService:
    """Test suite for the DominoService class."""

    def test_generate_tiles_double_six(self):
        """Test generating tiles for a double-six set."""
        tiles = DominoService.generate_tiles("double-six")
        assert len(tiles) == 28
        assert "00" in tiles
        assert "66" in tiles
        assert "06" in tiles
        assert "77" not in tiles

    def test_generate_tiles_double_nine(self):
        """Test generating tiles for a double-nine set."""
        tiles = DominoService.generate_tiles("double-nine")
        assert len(tiles) == 55
        assert "00" in tiles
        assert "99" in tiles
        assert "09" in tiles
        assert "XX" not in tiles

    def test_generate_tiles_invalid_type(self):
        """Test generating tiles with invalid type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid set type"):
            DominoService.generate_tiles("invalid-type")

    def test_create_set(self):
        """Test creating a new domino set."""
        set_id, domino_set = DominoService.create_set("double-six", 1)
        
        # Verify set_id is a string (UUID)
        assert isinstance(set_id, str)
        
        # Verify set was stored in domino_sets
        assert set_id in domino_sets
        
        # Verify set was stored in last_accessed
        assert set_id in last_accessed
        
        # Verify domino_set structure
        assert domino_set["type"] == "double-six"
        assert len(domino_set["tiles"]) == 28
        assert domino_set["piles"] == {}
        assert "created_at" in domino_set
        assert "version" in domino_set
        assert "set_id" in domino_set

    def test_create_set_multiple(self):
        """Test creating a domino set with multiple copies."""
        set_id, domino_set = DominoService.create_set("double-six", 2)
        
        # Verify we have double the tiles
        assert len(domino_set["tiles"]) == 56  # 28 * 2

    def test_get_set_existing(self):
        """Test getting an existing domino set."""
        # Create a set first
        set_id, _ = DominoService.create_set("double-six", 1)
        
        # Get the set
        retrieved_set = DominoService.get_set(set_id)
        
        # Verify structure
        assert retrieved_set["type"] == "double-six"
        assert len(retrieved_set["tiles"]) == 28
        assert retrieved_set["set_id"] == set_id

    def test_get_set_nonexistent(self):
        """Test getting a nonexistent domino set raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            DominoService.get_set("nonexistent-id")
        
        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()

    def test_get_all_sets_empty(self):
        """Test getting all sets when none exist."""
        sets = DominoService.get_all_sets()
        assert sets == {}

    def test_get_all_sets(self):
        """Test getting all sets."""
        # Create two sets
        set_id1, _ = DominoService.create_set("double-six", 1)
        set_id2, _ = DominoService.create_set("double-nine", 1)
        
        # Get all sets
        all_sets = DominoService.get_all_sets()
        
        # Verify both sets are present
        assert set_id1 in all_sets
        assert set_id2 in all_sets
        
        # Verify structure of the first set
        assert all_sets[set_id1]["type"] == "double-six"
        assert all_sets[set_id1]["set_id"] == set_id1
        
        # Verify structure of the second set
        assert all_sets[set_id2]["type"] == "double-nine"
        assert all_sets[set_id2]["set_id"] == set_id2

    def test_delete_set_existing(self):
        """Test deleting an existing set."""
        # Create a set first
        set_id, _ = DominoService.create_set("double-six", 1)
        
        # Delete the set
        result = DominoService.delete_set(set_id)
        
        # Verify result
        assert result is True
        
        # Verify set is removed from domino_sets
        assert set_id not in domino_sets
        
        # Verify set is removed from last_accessed
        assert set_id not in last_accessed

    def test_delete_set_nonexistent(self):
        """Test deleting a nonexistent set."""
        result = DominoService.delete_set("nonexistent-id")
        assert result is False

    def test_shuffle_set_remaining(self):
        """Test shuffling only remaining tiles in the boneyard."""
        # Create a set and capture original tiles
        set_id, domino_set = DominoService.create_set("double-six", 1)
        original_tiles = domino_set["tiles"].copy()
        
        # Shuffle only remaining tiles
        tiles_remaining = DominoService.shuffle_set(domino_set, only_remaining=True)
        
        # Verify number of tiles hasn't changed
        assert tiles_remaining == 28
        assert len(domino_set["tiles"]) == 28
        
        # Verify tiles have been shuffled (order has changed)
        # Note: In rare cases, shuffling might result in the same order
        # This is a probabilistic test
        assert domino_set["tiles"] != original_tiles or len(original_tiles) <= 1

    def test_shuffle_set_all(self):
        """Test shuffling all tiles including ones in piles."""
        # Create a set with piles
        set_id, domino_set = DominoService.create_set("double-six", 1)
        
        # Add some tiles to piles
        DominoService.add_to_pile(domino_set, "player1", domino_set["tiles"][:5], set_id)
        DominoService.add_to_pile(domino_set, "player2", domino_set["tiles"][:3], set_id)
        
        # Verify setup: 20 tiles in boneyard, 8 in piles
        assert len(domino_set["tiles"]) == 20
        assert len(domino_set["piles"]["player1"]) == 5
        assert len(domino_set["piles"]["player2"]) == 3
        
        # Shuffle all tiles
        tiles_remaining = DominoService.shuffle_set(domino_set, only_remaining=False)
        
        # Verify all tiles are back in the boneyard
        assert tiles_remaining == 28
        assert len(domino_set["tiles"]) == 28
        
        # Verify piles are empty
        assert domino_set["piles"] == {}

    def test_draw_tiles_success(self):
        """Test drawing tiles successfully."""
        # Create a set
        set_id, domino_set = DominoService.create_set("double-six", 1)
        
        # Remember the first few tiles
        expected_tiles = domino_set["tiles"][:5]
        
        # Draw 5 tiles
        drawn_tiles, remaining = DominoService.draw_tiles(domino_set, 5)
        
        # Verify drawn tiles
        assert drawn_tiles == expected_tiles
        assert remaining == 23
        assert len(domino_set["tiles"]) == 23

    def test_draw_tiles_too_many(self):
        """Test drawing more tiles than available raises HTTPException."""
        # Create a set
        set_id, domino_set = DominoService.create_set("double-six", 1)
        
        # Try to draw too many tiles
        with pytest.raises(HTTPException) as exc_info:
            DominoService.draw_tiles(domino_set, 100)
        
        assert exc_info.value.status_code == 409
        assert "cannot draw" in str(exc_info.value.detail).lower()

    def test_add_to_pile_success(self):
        """Test adding tiles to a pile successfully."""
        # Create a set
        set_id, domino_set = DominoService.create_set("double-six", 1)
        
        # Remember the first few tiles
        tiles_to_add = domino_set["tiles"][:3]
        
        # Add tiles to a pile
        added_tiles, piles = DominoService.add_to_pile(domino_set, "player1", tiles_to_add, set_id)
        
        # Verify added tiles
        assert added_tiles == tiles_to_add
        assert "player1" in piles
        assert piles["player1"] == tiles_to_add
        
        # Verify tiles are removed from boneyard
        assert len(domino_set["tiles"]) == 25
        for tile in tiles_to_add:
            assert tile not in domino_set["tiles"]

    def test_add_to_pile_missing_tiles(self):
        """Test adding missing tiles to a pile raises HTTPException."""
        # Create a set
        set_id, domino_set = DominoService.create_set("double-six", 1)
        
        # Try to add tiles that don't exist in the boneyard
        with pytest.raises(HTTPException) as exc_info:
            DominoService.add_to_pile(domino_set, "player1", ["XX", "YY"], set_id)
        
        assert exc_info.value.status_code == 400
        assert "not found in the boneyard" in str(exc_info.value.detail).lower()

    @pytest.mark.parametrize("use_redis", [True, False])
    def test_save_set(self, use_redis):
        """Test saving a domino set with and without Redis."""
        # Create a set
        set_id, domino_set = DominoService.create_set("double-six", 1)
        
        # Setup for testing _save_set with Redis
        with patch("app.services.domino_service.USE_REDIS", use_redis), \
             patch("app.services.domino_service.redis_client") as mock_redis:
            
            if use_redis:
                mock_redis.set.return_value = True
                mock_redis.expire.return_value = True
                
            # Call _save_set
            DominoService._save_set(set_id, domino_set)
            
            if use_redis:
                # Verify Redis calls
                mock_redis.set.assert_called_once()
                mock_redis.expire.assert_called_once()
            else:
                # Verify in-memory update
                assert domino_sets[set_id]["version"] == domino_set["version"] 