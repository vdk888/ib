"""
Dependency injection container
"""
from functools import lru_cache
from .config import Settings
from ..services.interfaces import IScreenerService, IUniverseRepository, IPortfolioOptimizer
from ..services.implementations.screener_service import ScreenerService
from ..services.implementations.uncle_stock_provider import UncleStockProvider
from ..services.implementations.file_manager import FileManager
from ..services.implementations.universe_service import create_universe_service
from ..services.implementations.portfolio_optimizer_service import PortfolioOptimizerService

@lru_cache()
def get_settings() -> Settings:
    """Get application settings"""
    return Settings()

# Service instances (singleton pattern for stateless services)
_file_manager = None
_uncle_stock_provider = None
_screener_service = None
_universe_service = None
_portfolio_optimizer_service = None


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


def get_universe_service() -> IUniverseRepository:
    """Get universe service instance"""
    global _universe_service
    if _universe_service is None:
        _universe_service = create_universe_service()
    return _universe_service


def get_portfolio_optimizer_service() -> IPortfolioOptimizer:
    """Get portfolio optimizer service instance"""
    global _portfolio_optimizer_service
    if _portfolio_optimizer_service is None:
        _portfolio_optimizer_service = PortfolioOptimizerService()
    return _portfolio_optimizer_service