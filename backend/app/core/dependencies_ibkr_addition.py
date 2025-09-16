"""
Additional dependencies for IBKR Search Service
"""
from ..services.ibkr_interface import IIBKRSearchService
from ..services.implementations.ibkr_search_service import IBKRSearchService

# Global singleton for IBKR search service
_ibkr_search_service = None

def get_ibkr_search_service() -> IIBKRSearchService:
    """Get IBKR search service instance"""
    global _ibkr_search_service
    if _ibkr_search_service is None:
        settings = get_settings()
        _ibkr_search_service = IBKRSearchService(
            ibkr_host=getattr(settings, 'ibkr_host', '127.0.0.1'),
            ibkr_port=getattr(settings, 'ibkr_port', 4002)
        )
    return _ibkr_search_service
