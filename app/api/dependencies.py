"""Common dependencies and utilities for API routes."""
from typing import Annotated, Dict, Any

from fastapi import Depends

from app.services.domino_service import DominoService

# Dependency to get a domino set by ID, shared across route modules
SetDep = Annotated[Dict[str, Any], Depends(DominoService.get_set)] 