"""
Simple configuration without pydantic-settings dependency
"""
import os
from pathlib import Path

# Get the root directory (where main.py and config.py are located)
ROOT_DIR = Path(__file__).parent.parent.parent.parent

class SimpleSettings:
    """Simple configuration for testing"""
    log_level: str = "INFO"
    environment: str = "development"
    debug: bool = False
    data_directory: str = str(ROOT_DIR / "data")

# Global settings instance
settings = SimpleSettings()