"""Service layer for domino operations."""
import random
import time
import logging
import uuid
import json
from typing import Dict, List, Any, Optional, Tuple

import redis
from fastapi import HTTPException, status

from app.core.config import SET_EXPIRY_SECONDS, USE_REDIS, REDIS_URL, REDIS_PREFIX
from app.models.schemas import SetSummary, PileInfo

logger = logging.getLogger(__name__)

# Redis client for persistent storage
redis_client = None
if USE_REDIS:
    try:
        redis_client = redis.from_url(REDIS_URL)
        logger.info(f"Connected to Redis at {REDIS_URL}")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        logger.warning("Falling back to in-memory storage")

# In-memory storage (Limitations: Volatile, not scalable, potential concurrency issues in high load)
# Only used if Redis is not configured
domino_sets: Dict[str, Dict[str, Any]] = {}
last_accessed: Dict[str, float] = {}  # Stores timestamp of last access


class DominoService:
    """Service for manipulating domino sets and tiles."""

    @staticmethod
    def _get_redis_key(set_id: str) -> str:
        """Get Redis key for a domino set."""
        return f"{REDIS_PREFIX}set:{set_id}"
    
    @staticmethod
    def _get_redis_access_key(set_id: str) -> str:
        """Get Redis key for last accessed time."""
        return f"{REDIS_PREFIX}access:{set_id}"

    @staticmethod
    def generate_tiles(set_type: str) -> List[str]:
        """Generates a standard set of domino tiles."""
        try:
            max_value = {
                "double-six": 6, "double-nine": 9, "double-twelve": 12,
                "double-fifteen": 15, "double-eighteen": 18
            }[set_type]
        except KeyError as e:
            # This should ideally be caught by Pydantic validation, but good practice
            logger.error(f"Invalid set_type '{set_type}' passed to generate_tiles.")
            raise ValueError(f"Invalid set type: {set_type}") from e

        return [
            f"{i}{j}"
            for i in range(max_value + 1)
            for j in range(i, max_value + 1)
        ]

    @staticmethod
    def get_all_sets() -> Dict[str, Dict[str, Any]]:
        """Get all active domino sets."""
        if USE_REDIS and redis_client:
            # Get all sets from Redis
            all_sets = {}
            # Get all set keys
            set_keys = redis_client.keys(f"{REDIS_PREFIX}set:*")
            
            for key in set_keys:
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                set_id = key_str.split(":")[-1]
                set_data = redis_client.get(key_str)
                if set_data:
                    all_sets[set_id] = json.loads(set_data)
                    # Add set_id to the data for later reference
                    all_sets[set_id]["set_id"] = set_id
            
            return all_sets
        else:
            # Return a copy of the in-memory sets with set_id added
            result = {}
            for set_id, set_data in domino_sets.items():
                # Create a copy to avoid modifying the original
                set_copy = set_data.copy()
                set_copy["set_id"] = set_id
                result[set_id] = set_copy
            return result

    @staticmethod
    def delete_set(set_id: str) -> bool:
        """
        Delete a domino set.
        
        Returns:
            bool: True if deleted, False if not found
        """
        if USE_REDIS and redis_client:
            # Delete from Redis
            redis_key = DominoService._get_redis_key(set_id)
            access_key = DominoService._get_redis_access_key(set_id)
            
            # Check if set exists
            if not redis_client.exists(redis_key):
                return False
                
            # Delete keys
            redis_client.delete(redis_key)
            redis_client.delete(access_key)
            logger.info(f"Deleted domino set {set_id} from Redis")
            return True
        else:
            # Delete from in-memory storage
            if set_id not in domino_sets:
                return False
                
            del domino_sets[set_id]
            if set_id in last_accessed:
                del last_accessed[set_id]
                
            logger.info(f"Deleted domino set {set_id} from memory")
            return True

    @staticmethod
    def clean_expired_sets():
        """Removes sets that haven't been accessed for a defined duration."""
        current_time = time.time()
        
        if USE_REDIS and redis_client:
            # Clean expired sets from Redis
            all_keys = redis_client.keys(f"{REDIS_PREFIX}access:*")
            expired_keys = []
            
            for key in all_keys:
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                set_id = key_str.split(":")[-1]
                last_access = float(redis_client.get(key_str) or 0)
                
                if current_time - last_access > SET_EXPIRY_SECONDS:
                    expired_keys.append(key_str)
                    redis_client.delete(f"{REDIS_PREFIX}set:{set_id}")
                    redis_client.delete(key_str)
                    logger.info(f"Expired set {set_id} removed from Redis due to inactivity.")
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired sets from Redis.")
        else:
            # Clean from in-memory storage
            expired_set_ids = [
                set_id for set_id, last_time in last_accessed.items()
                if current_time - last_time > SET_EXPIRY_SECONDS
            ]

            cleaned_count = 0
            for set_id in expired_set_ids:
                if set_id in domino_sets:
                    del domino_sets[set_id]
                    del last_accessed[set_id]
                    cleaned_count += 1
                    logger.info(f"Expired set {set_id} removed from memory due to inactivity.")

            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired sets from memory.")

    @staticmethod
    def get_set(set_id: str) -> Dict[str, Any]:
        """Get a domino set or raise an exception if not found."""
        current_time = time.time()
        
        if USE_REDIS and redis_client:
            # Get from Redis
            redis_key = DominoService._get_redis_key(set_id)
            redis_data = redis_client.get(redis_key)
            
            if not redis_data:
                logger.warning(f"Attempted access to non-existent set_id: {set_id}")
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domino set not found.")
            
            # Update last accessed time
            redis_client.set(
                DominoService._get_redis_access_key(set_id), 
                str(current_time),
                ex=SET_EXPIRY_SECONDS
            )
            
            set_data = json.loads(redis_data)
            # Add set_id to the data for later reference
            set_data["set_id"] = set_id
            return set_data
        else:
            # Get from in-memory storage
            if set_id not in domino_sets:
                logger.warning(f"Attempted access to non-existent set_id: {set_id}")
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domino set not found.")
            
            # Update last accessed time
            last_accessed[set_id] = current_time
            
            # Create a copy to avoid modifying the original
            set_data = domino_sets[set_id].copy()
            # Add set_id to the data for later reference
            set_data["set_id"] = set_id
            return set_data

    @staticmethod
    def get_set_summary(set_id: str, domino_set: Dict[str, Any]) -> SetSummary:
        """Generate a summary of the current set state."""
        piles_info = {
            name: PileInfo(count=len(pile))
            for name, pile in domino_set.get("piles", {}).items()
        }
        return SetSummary(
            set_id=set_id,
            type=domino_set["type"],
            tiles_remaining=len(domino_set.get("tiles", [])),
            piles=piles_info
        )

    @staticmethod
    def create_set(set_type: str, num_sets: int) -> Tuple[str, Dict[str, Any]]:
        """Create a new domino set."""
        set_id = str(uuid.uuid4())
        tiles = DominoService.generate_tiles(set_type) * num_sets
        random.shuffle(tiles)

        domino_set_data = {
            "type": set_type,
            "tiles": tiles,  # The main 'boneyard'
            "piles": {},      # Named piles (e.g., player hands, draw pile)
            "created_at": time.time(),
            "version": 1      # For optimistic concurrency control
        }
        
        if USE_REDIS and redis_client:
            # Store in Redis with expiration
            redis_client.set(
                DominoService._get_redis_key(set_id),
                json.dumps(domino_set_data),
                ex=SET_EXPIRY_SECONDS
            )
            # Set last accessed time
            redis_client.set(
                DominoService._get_redis_access_key(set_id),
                str(time.time()),
                ex=SET_EXPIRY_SECONDS
            )
        else:
            # Store in memory
            domino_sets[set_id] = domino_set_data
            last_accessed[set_id] = time.time()
        
        logger.info(f"Created new domino set {set_id} (type: {set_type}, sets: {num_sets}, tiles: {len(tiles)})")
        # Add set_id to the returned data for reference
        domino_set_data["set_id"] = set_id
        return set_id, domino_set_data

    @staticmethod
    def _save_set(set_id: str, domino_set: Dict[str, Any]):
        """Save a domino set back to storage."""
        # Increment version for optimistic concurrency control
        domino_set["version"] = domino_set.get("version", 0) + 1
        
        # Remove set_id from data before saving (it's the key, not part of the data)
        data_to_save = domino_set.copy()
        if "set_id" in data_to_save:
            del data_to_save["set_id"]
            
        if USE_REDIS and redis_client:
            # Update in Redis
            redis_client.set(
                DominoService._get_redis_key(set_id),
                json.dumps(data_to_save),
                ex=SET_EXPIRY_SECONDS
            )
            # Refresh expiration on access time
            redis_client.expire(DominoService._get_redis_access_key(set_id), SET_EXPIRY_SECONDS)
        else:
            # In-memory storage needs to be updated explicitly
            domino_sets[set_id] = data_to_save

    @staticmethod
    def shuffle_set(domino_set: Dict[str, Any], only_remaining: bool = False) -> int:
        """
        Shuffle tiles in a domino set.
        
        Args:
            domino_set: The domino set to shuffle
            only_remaining: If True, shuffle only the boneyard. If False, collect all tiles and shuffle.
            
        Returns:
            Number of tiles remaining in the boneyard after shuffling
        """
        if only_remaining:
            random.shuffle(domino_set["tiles"])
        else:
            # Collect all tiles
            all_tiles = domino_set["tiles"][:]  # Create copy
            for pile_tiles in domino_set.get("piles", {}).values():
                all_tiles.extend(pile_tiles)

            # Shuffle and reset
            random.shuffle(all_tiles)
            domino_set["tiles"] = all_tiles
            domino_set["piles"] = {}  # Reset piles

        # Save the updated set if needed (for Redis)
        if USE_REDIS and redis_client:
            set_id = domino_set.get("set_id")
            if set_id:
                DominoService._save_set(set_id, domino_set)

        return len(domino_set["tiles"])

    @staticmethod
    def draw_tiles(domino_set: Dict[str, Any], count: int) -> Tuple[List[str], int]:
        """
        Draw tiles from the boneyard.
        
        Args:
            domino_set: The domino set to draw from
            count: Number of tiles to draw
            
        Returns:
            Tuple of (drawn tiles, remaining tiles count)
        """
        if count > len(domino_set["tiles"]):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot draw {count} tiles, only {len(domino_set['tiles'])} remaining in the boneyard."
            )

        drawn_tiles = domino_set["tiles"][:count]
        domino_set["tiles"] = domino_set["tiles"][count:]
        
        # Save the updated set if needed (for Redis)
        if USE_REDIS and redis_client:
            set_id = domino_set.get("set_id")
            if set_id:
                DominoService._save_set(set_id, domino_set)
                
        return drawn_tiles, len(domino_set["tiles"])

    @staticmethod
    def add_to_pile(
        domino_set: Dict[str, Any], 
        pile_name: str, 
        tiles_to_add: List[str],
        set_id: Optional[str] = None  # Added for Redis support
    ) -> Tuple[List[str], Dict[str, List[str]]]:
        """
        Move tiles from boneyard to a named pile.
        
        Args:
            domino_set: The domino set
            pile_name: Name of the pile to add to
            tiles_to_add: List of tiles to add to the pile
            set_id: Optional set_id for Redis storage
            
        Returns:
            Tuple of (added_tiles, updated piles dict)
        """
        boneyard = domino_set["tiles"]
        piles = domino_set.setdefault("piles", {})  # Ensure 'piles' key exists

        if missing_tiles := [tile for tile in tiles_to_add if tile not in boneyard]:
            logger.warning(f"Add to pile '{pile_name}' failed: Tiles {missing_tiles} not found in boneyard.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot add tiles to pile '{pile_name}'. The following tiles were not found in the boneyard: {', '.join(missing_tiles)}"
            )

        # Use a temporary list to handle potential duplicates in request safely
        boneyard_after_removal = list(boneyard)  # Copy
        added_tiles_actual = []
        for tile in tiles_to_add:
            try:
                boneyard_after_removal.remove(tile)
                added_tiles_actual.append(tile)  # Keep track of what was actually moved
            except ValueError as e:
                # This case should technically be caught by the initial check, but handles edge cases/duplicates
                logger.error(f"Consistency issue: Tile {tile} requested for pile '{pile_name}' was not found during removal despite initial check.")
                # Fail outright
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Internal inconsistency error while trying to move tile {tile}. Please try again."
                ) from e

        # Update the actual boneyard
        domino_set["tiles"] = boneyard_after_removal

        # Add to the target pile
        if pile_name not in piles:
            piles[pile_name] = []
        piles[pile_name].extend(added_tiles_actual)  # Add the tiles confirmed removed
        
        # Save the updated set if needed (for Redis)
        if USE_REDIS and redis_client and set_id:
            DominoService._save_set(set_id, domino_set)
            
        return added_tiles_actual, piles

    @staticmethod
    def list_pile(domino_set: Dict[str, Any], pile_name: str) -> List[str]:
        """Get the tiles in a specific pile."""
        piles = domino_set.get("piles", {})
        if pile_name not in piles:
            logger.warning(f"List pile failed: Pile '{pile_name}' not found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Pile '{pile_name}' not found."
            )
        
        return piles[pile_name]

    @staticmethod
    def create_pile(set_id: str, pile_name: str) -> Dict[str, List[str]]:
        """
        Create a new empty pile for a domino set.
        
        Args:
            set_id: ID of the domino set
            pile_name: Name of the pile to create
            
        Returns:
            Dictionary of all piles for the set
            
        Raises:
            HTTPException: If set not found or pile already exists
        """
        domino_set = DominoService.get_set(set_id)
        
        piles = domino_set.setdefault("piles", {})
        
        if pile_name in piles:
            logger.warning(f"Create pile failed: Pile '{pile_name}' already exists for set {set_id}.")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Pile '{pile_name}' already exists."
            )
            
        piles[pile_name] = []
        
        # Save the updated set if needed (for Redis)
        if USE_REDIS and redis_client:
            DominoService._save_set(set_id, domino_set)
            
        logger.info(f"Created new empty pile '{pile_name}' for set {set_id}")
        return piles

    @staticmethod
    def draw_from_pile(
        domino_set: Dict[str, Any], 
        pile_name: str,
        set_id: Optional[str] = None  # Added for Redis support
    ) -> Tuple[str, int]:
        """Draw a random tile from a pile."""
        piles = domino_set.get("piles", {})
        if pile_name not in piles or not piles[pile_name]:
            logger.warning(f"Draw from pile '{pile_name}' failed: Pile not found or empty.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pile '{pile_name}' not found or is empty."
            )

        pile = piles[pile_name]
        drawn_tile = random.choice(pile)
        pile.remove(drawn_tile)  # Remove the drawn tile
        
        # Save the updated set if needed (for Redis)
        if USE_REDIS and redis_client and set_id:
            DominoService._save_set(set_id, domino_set)
            
        return drawn_tile, len(pile)

    @staticmethod
    def return_to_boneyard(
        domino_set: Dict[str, Any], 
        pile_name: str, 
        tiles_to_return: List[str],
        set_id: Optional[str] = None  # Added for Redis support
    ) -> Tuple[List[str], int]:
        """
        Return tiles from a pile back to the boneyard.
        
        Args:
            domino_set: The domino set
            pile_name: Name of the pile to return from
            tiles_to_return: List of tiles to return to boneyard
            set_id: Optional set_id for Redis storage
            
        Returns:
            Tuple of (returned_tiles, boneyard_count)
        """
        piles = domino_set.get("piles", {})
        if pile_name not in piles:
            logger.warning(f"Return from pile '{pile_name}' failed: Pile not found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Pile '{pile_name}' not found."
            )

        pile = piles[pile_name]

        if missing_tiles := [tile for tile in tiles_to_return if tile not in pile]:
            logger.warning(f"Return from pile '{pile_name}' failed: Tiles {missing_tiles} not found in pile.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot return tiles from pile '{pile_name}'. The following tiles were not found in the pile: {', '.join(missing_tiles)}"
            )

        # Use a temporary list to handle potential duplicates in request safely
        pile_after_removal = list(pile)  # Copy
        returned_tiles_actual = []
        for tile in tiles_to_return:
            try:
                pile_after_removal.remove(tile)
                returned_tiles_actual.append(tile)
            except ValueError as e:
                logger.error(f"Consistency issue: Tile {tile} requested for return from pile '{pile_name}' was not found during removal despite initial check.")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Internal inconsistency error while trying to return tile {tile}. Please try again."
                ) from e

        # Update the actual pile and boneyard
        piles[pile_name] = pile_after_removal
        domino_set["tiles"].extend(returned_tiles_actual)  # Add back to boneyard
        
        # Save the updated set if needed (for Redis)
        if USE_REDIS and redis_client and set_id:
            DominoService._save_set(set_id, domino_set)
            
        return returned_tiles_actual, len(domino_set["tiles"]) 