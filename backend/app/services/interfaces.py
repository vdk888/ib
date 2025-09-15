"""
Service interfaces following Interface-First Design principles
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime


class IDataProvider(ABC):
    """
    Interface for fetching financial data from external sources
    Following fintech best practices for financial data abstraction
    """

    @abstractmethod
    async def get_current_stocks(
        self,
        query_name: str,
        max_results: int = 200
    ) -> Dict[str, Any]:
        """
        Fetch current stocks from a screener query

        Args:
            query_name: Screener query identifier
            max_results: Maximum number of stocks to return

        Returns:
            Dict with keys: success, data, raw_response, csv_file
        """
        pass

    @abstractmethod
    async def get_screener_history(
        self,
        query_name: str
    ) -> Dict[str, Any]:
        """
        Fetch backtest history from a screener query

        Args:
            query_name: Screener query identifier

        Returns:
            Dict with keys: success, data, raw_response, csv_file
        """
        pass

    @abstractmethod
    async def get_all_screeners(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetch current stocks from all configured screeners

        Returns:
            Dict mapping screener IDs to their results
        """
        pass

    @abstractmethod
    async def get_all_screener_histories(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetch backtest history from all configured screeners

        Returns:
            Dict mapping screener IDs to their history results
        """
        pass

    @abstractmethod
    def get_screener_configurations(self) -> Dict[str, str]:
        """
        Get available screener configurations

        Returns:
            Dict mapping screener IDs to their display names
        """
        pass


class IFileManager(ABC):
    """
    Interface for managing data files with financial compliance
    Ensures audit trail and data persistence requirements
    """

    @abstractmethod
    def save_csv_data(
        self,
        content: str,
        filename: str,
        directory: str = "data/files_exports"
    ) -> str:
        """
        Save CSV data to file with proper directory management

        Args:
            content: CSV content to save
            filename: Target filename
            directory: Target directory

        Returns:
            Full path to saved file
        """
        pass

    @abstractmethod
    def sanitize_filename(self, name: str) -> str:
        """
        Sanitize filename for file system compatibility

        Args:
            name: Original name

        Returns:
            Sanitized filename
        """
        pass

    @abstractmethod
    def ensure_directory_exists(self, directory: str) -> None:
        """
        Ensure directory exists, create if necessary

        Args:
            directory: Directory path to check/create
        """
        pass


class IScreenerService(ABC):
    """
    High-level screener service interface
    Orchestrates data fetching and file management
    """

    @abstractmethod
    async def fetch_screener_data(
        self,
        screener_id: str,
        max_results: int = 200
    ) -> Dict[str, Any]:
        """
        Fetch current data for a specific screener
        """
        pass

    @abstractmethod
    async def fetch_screener_history(
        self,
        screener_id: str
    ) -> Dict[str, Any]:
        """
        Fetch historical data for a specific screener
        """
        pass

    @abstractmethod
    async def fetch_all_screener_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetch current data for all screeners
        """
        pass

    @abstractmethod
    async def fetch_all_screener_histories(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetch historical data for all screeners
        """
        pass

    @abstractmethod
    def get_available_screeners(self) -> Dict[str, str]:
        """
        Get list of available screeners
        """
        pass