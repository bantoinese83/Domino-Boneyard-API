"""Configuration settings for the application."""
import os
from typing import List

# --- Environment ---
ENV = os.getenv("DOMINO_ENV", "production")
DEBUG = ENV.lower() != "production"

# --- API Configuration ---
API_VERSION = os.getenv("DOMINO_API_VERSION", "1.2.0")
SET_EXPIRY_SECONDS = int(os.getenv("DOMINO_SET_EXPIRY_SECONDS", str(14 * 24 * 60 * 60)))  # 14 days default

# --- Security Settings ---
# In production, set this to your actual frontend domain(s)
CORS_ORIGINS: List[str] = os.getenv("DOMINO_CORS_ORIGINS", "*").split(",")
CORS_ALLOW_CREDENTIALS = os.getenv("DOMINO_CORS_CREDENTIALS", "false").lower() == "true"

# --- Logging Configuration ---
LOG_LEVEL = os.getenv("DOMINO_LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv(
    "DOMINO_LOG_FORMAT", 
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# --- Domino Configuration ---
VALID_DOMINO_TYPES = ["double-six", "double-nine", "double-twelve", "double-fifteen", "double-eighteen"]

# --- Data Storage Config ---
# If set to true, will use Redis for persistence instead of in-memory storage
USE_REDIS = os.getenv("DOMINO_USE_REDIS", "false").lower() == "true"
REDIS_URL = os.getenv("DOMINO_REDIS_URL", "redis://localhost:6379/0")
REDIS_PREFIX = os.getenv("DOMINO_REDIS_PREFIX", "domino:") 