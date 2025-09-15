"""
Dependency injection container
"""
from functools import lru_cache
from .config import Settings

@lru_cache()
def get_settings() -> Settings:
    """Get application settings"""
    return Settings()