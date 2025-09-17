"""
Centralized configuration management
"""
from pydantic_settings import BaseSettings
from typing import Optional, Dict
import os
from pathlib import Path

# Get the root directory (where main.py and config.py are located)
ROOT_DIR = Path(__file__).parent.parent.parent

class BaseServiceSettings(BaseSettings):
    """Base configuration for all services"""
    log_level: str = "INFO"
    environment: str = "development"
    debug: bool = False

class UncleStockSettings(BaseServiceSettings):
    user_id: Optional[str] = None
    uncle_stock_timeout: int = 60
    retry_attempts: int = 3
    max_results_per_screener: int = 200

    # Screener configurations matching legacy config.py
    uncle_stock_screens: Dict[str, str] = {
        "quality_bloom": "quality bloom",
        "TOR_Surplus": "TOR Surplus",
        "Moat_Companies": "Moat Companies"
    }

    # Additional fields configuration for universe.json
    # Format: List of tuples (header_name, subtitle_pattern, field_alias, description)
    additional_fields: list = [
        # Price-related fields
        ('Price', '180d change', 'price_180d_change', 'Price change over 180 days'),
    ]

    # Enable/disable additional fields extraction
    extract_additional_fields: bool = True

    # Data directory paths
    data_exports_dir: str = "data/files_exports"

    class Config:
        env_prefix = "UNCLE_STOCK_"
        env_file = str(ROOT_DIR / ".env")
        extra = "ignore"

class IBKRSettings(BaseServiceSettings):
    ibkr_host: str = "host.docker.internal"
    ibkr_port: int = 4002
    ibkr_client_id: int = 1
    connection_timeout: int = 10

    class Config:
        env_prefix = "IBKR_"

class PortfolioSettings(BaseServiceSettings):
    max_ranked_stocks: int = 30
    max_allocation: float = 0.10
    min_allocation: float = 0.01
    risk_free_rate: float = 0.02

    class Config:
        env_prefix = "PORTFOLIO_"

class TelegramSettings(BaseServiceSettings):
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None
    enabled: bool = True
    timeout: int = 10

    class Config:
        env_prefix = "TELEGRAM_"
        env_file = str(Path(__file__).parent.parent / ".env")

class Settings(BaseServiceSettings):
    """Main application settings"""
    # File paths
    data_directory: str = str(ROOT_DIR / "data")
    exports_directory: str = str(ROOT_DIR / "data" / "files_exports")

    # Service configurations
    uncle_stock: UncleStockSettings = UncleStockSettings()
    ibkr: IBKRSettings = IBKRSettings()
    portfolio: PortfolioSettings = PortfolioSettings()
    telegram: TelegramSettings = TelegramSettings()

    class Config:
        env_file = str(ROOT_DIR / ".env")

# Global settings instance
settings = Settings()