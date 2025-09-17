"""
Dependency injection container
"""
# Load environment variables first
from dotenv import load_dotenv
from pathlib import Path

# Load .env file from the backend directory
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

from functools import lru_cache
from .config import Settings
from ..services.interfaces import IScreenerService, IUniverseRepository, IPortfolioOptimizer, ITargetAllocationService, IOrderExecutionService, IRebalancingService, IAccountService, IQuantityCalculator, IPipelineOrchestrator, ICurrencyService, IIBKRSearchService, IOrderStatusService, IHistoricalDataService, ITelegramService
from ..services.implementations.screener_service import ScreenerService
from ..services.implementations.uncle_stock_provider import UncleStockProvider
from ..services.implementations.file_manager import FileManager
from ..services.implementations.universe_service import create_universe_service
from ..services.implementations.portfolio_optimizer_service import PortfolioOptimizerService
from ..services.implementations.target_allocation_service import TargetAllocationService
from ..services.implementations.order_execution_service import OrderExecutionService
from ..services.implementations.order_status_service import OrderStatusService
from ..services.implementations.rebalancing_service import RebalancingService
from ..services.implementations.account_service import AccountService
from ..services.implementations.quantity_service import QuantityService
from ..services.implementations.quantity_orchestrator_service import QuantityOrchestratorService
from ..services.implementations.pipeline_orchestrator_service import PipelineOrchestratorService
from ..services.implementations.currency_service import CurrencyService
from ..services.implementations.ibkr_search_service import IBKRSearchService
from ..services.implementations.historical_data_service import HistoricalDataService
from ..services.implementations.telegram_service import TelegramService

@lru_cache()
def get_settings() -> Settings:
    """Get application settings"""
    return Settings()

# Service instances (singleton pattern for stateless services)
_file_manager = None
_uncle_stock_provider = None
_screener_service = None
_universe_service = None
_historical_data_service = None
_portfolio_optimizer_service = None
_target_allocation_service = None
_order_execution_service = None
_order_status_service = None
_rebalancing_service = None
_account_service = None
_quantity_service = None
_quantity_orchestrator_service = None
_pipeline_orchestrator_service = None
_currency_service = None
_ibkr_search_service = None
_telegram_service = None


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


def get_historical_data_service() -> IHistoricalDataService:
    """Get historical data service instance"""
    global _historical_data_service
    if _historical_data_service is None:
        _historical_data_service = HistoricalDataService()
    return _historical_data_service


def get_portfolio_optimizer_service() -> IPortfolioOptimizer:
    """Get portfolio optimizer service instance"""
    global _portfolio_optimizer_service
    if _portfolio_optimizer_service is None:
        _portfolio_optimizer_service = PortfolioOptimizerService("data/universe.json")
    return _portfolio_optimizer_service


def get_target_allocation_service() -> ITargetAllocationService:
    """Get target allocation service instance"""
    global _target_allocation_service
    if _target_allocation_service is None:
        _target_allocation_service = TargetAllocationService()
    return _target_allocation_service


def get_order_execution_service() -> IOrderExecutionService:
    """Get order execution service instance"""
    global _order_execution_service
    if _order_execution_service is None:
        _order_execution_service = OrderExecutionService()
    return _order_execution_service


def get_order_status_service() -> IOrderStatusService:
    """Get order status service instance"""
    global _order_status_service
    if _order_status_service is None:
        _order_status_service = OrderStatusService()
    return _order_status_service


def get_rebalancing_service() -> IRebalancingService:
    """Get rebalancing service instance"""
    global _rebalancing_service
    if _rebalancing_service is None:
        _rebalancing_service = RebalancingService()
    return _rebalancing_service


def get_account_service() -> IAccountService:
    """Get account service instance"""
    global _account_service
    if _account_service is None:
        _account_service = AccountService()
    return _account_service


def get_quantity_service() -> IQuantityCalculator:
    """Get quantity calculator service instance"""
    global _quantity_service
    if _quantity_service is None:
        _quantity_service = QuantityService()
    return _quantity_service


def get_quantity_orchestrator_service() -> QuantityOrchestratorService:
    """Get quantity orchestrator service instance"""
    global _quantity_orchestrator_service
    if _quantity_orchestrator_service is None:
        _quantity_orchestrator_service = QuantityOrchestratorService(
            account_service=get_account_service(),
            quantity_service=get_quantity_service()
        )
    return _quantity_orchestrator_service


def get_pipeline_orchestrator_service() -> IPipelineOrchestrator:
    """Get pipeline orchestrator service instance"""
    global _pipeline_orchestrator_service
    if _pipeline_orchestrator_service is None:
        _pipeline_orchestrator_service = PipelineOrchestratorService(
            screener_service=get_screener_service(),
            universe_service=get_universe_service(),
            historical_data_service=get_historical_data_service(),
            portfolio_optimizer_service=get_portfolio_optimizer_service(),
            currency_service=get_currency_service(),
            target_allocation_service=get_target_allocation_service(),
            quantity_service=get_quantity_service(),
            ibkr_search_service=get_ibkr_search_service(),
            rebalancing_service=get_rebalancing_service(),
            order_execution_service=get_order_execution_service(),
            order_status_service=get_order_status_service(),
            telegram_service=get_telegram_service()
        )
    return _pipeline_orchestrator_service


def get_currency_service() -> ICurrencyService:
    """Get currency service instance"""
    global _currency_service
    if _currency_service is None:
        _currency_service = CurrencyService()
    return _currency_service

def get_ibkr_search_service() -> IIBKRSearchService:
    """Get IBKR search service instance"""
    global _ibkr_search_service
    if _ibkr_search_service is None:
        _ibkr_search_service = IBKRSearchService()
    return _ibkr_search_service


def get_telegram_service() -> ITelegramService:
    """Get Telegram notification service instance"""
    global _telegram_service
    if _telegram_service is None:
        _telegram_service = TelegramService()
    return _telegram_service
