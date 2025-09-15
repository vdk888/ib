"""
Dependency injection container
"""
from functools import lru_cache
from .config import Settings
from ..services.interfaces import IScreenerService
from ..services.implementations.screener_service import ScreenerService
from ..services.implementations.uncle_stock_provider import UncleStockProvider
from ..services.implementations.file_manager import FileManager

@lru_cache()
def get_settings() -> Settings:
    """Get application settings"""
    return Settings()

# Service instances (singleton pattern for stateless services)
_file_manager = None
_uncle_stock_provider = None
_screener_service = None


def get_file_manager() -> FileManager:
    """Get file manager instance"""
    global _file_manager
    if _file_manager is None:
        _file_manager = FileManager()
    return _file_manager


def get_uncle_stock_provider() -> UncleStockProvider:
    """Get Uncle Stock provider instance"""
    global _uncle_stock_provider
    if _uncle_stock_provider is None:
        _uncle_stock_provider = UncleStockProvider(get_file_manager())
    return _uncle_stock_provider


def get_screener_service() -> IScreenerService:
    """Get screener service instance"""
    global _screener_service
    if _screener_service is None:
        _screener_service = ScreenerService(
            data_provider=get_uncle_stock_provider(),
            file_manager=get_file_manager()
        )
    return _screener_service