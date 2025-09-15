"""
Service interfaces following Interface-First Design principles
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np


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


class IDataParser(ABC):
    """
    Interface for parsing CSV data files
    Handles financial data parsing with precision and validation
    """

    @abstractmethod
    def parse_screener_csv(self, csv_path: str) -> List[Dict[str, Any]]:
        """
        Parse a single screener CSV file and extract standard fields

        Args:
            csv_path: Path to the CSV file

        Returns:
            List of stock dictionaries with standard fields:
            ticker, isin, name, currency, sector, country, price
        """
        pass

    @abstractmethod
    def parse_screener_csv_flexible(
        self,
        csv_path: str,
        additional_fields: Optional[List[tuple]] = None
    ) -> List[Dict[str, Any]]:
        """
        Parse CSV file with both standard and additional custom fields

        Args:
            csv_path: Path to the CSV file
            additional_fields: List of tuples (header_name, subtitle_pattern, field_alias)

        Returns:
            List of stock dictionaries with configured fields
        """
        pass

    @abstractmethod
    def extract_field_data(
        self,
        csv_path: str,
        header_name: str,
        subtitle_pattern: str,
        ticker: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extract specific field data from CSV using header/subtitle pattern

        Args:
            csv_path: Path to the CSV file
            header_name: Header name to match (e.g., 'Price')
            subtitle_pattern: Pattern to match in description (e.g., '180d change')
            ticker: Optional ticker to filter for specific stock

        Returns:
            Dict with field data or None if not found
        """
        pass

    @abstractmethod
    def find_available_fields(
        self,
        csv_path: Optional[str] = None
    ) -> List[tuple]:
        """
        Find all available header/subtitle combinations in a CSV file

        Args:
            csv_path: Path to CSV file, if None uses first available screen

        Returns:
            List of tuples (header, subtitle, column_index)
        """
        pass


class IUniverseRepository(ABC):
    """
    Interface for universe data management
    Handles creation, storage, and retrieval of universe data
    """

    @abstractmethod
    def create_universe(self) -> Dict[str, Any]:
        """
        Parse all screener CSV files and create universe structure

        Returns:
            Universe dictionary with metadata, screens, and all_stocks sections
        """
        pass

    @abstractmethod
    def save_universe(
        self,
        universe: Dict[str, Any],
        output_path: str = 'data/universe.json'
    ) -> None:
        """
        Save universe data to JSON file with summary statistics

        Args:
            universe: Universe dictionary
            output_path: Path to save the JSON file
        """
        pass

    @abstractmethod
    def load_universe(
        self,
        file_path: str = 'data/universe.json'
    ) -> Optional[Dict[str, Any]]:
        """
        Load universe data from JSON file

        Args:
            file_path: Path to the universe JSON file

        Returns:
            Universe dictionary or None if file not found
        """
        pass

    @abstractmethod
    def get_stock_field(
        self,
        ticker: str,
        header_name: str,
        subtitle_pattern: str,
        screen_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get specific field value for a stock from screener data

        Args:
            ticker: Stock ticker (e.g., 'GRR.AX')
            header_name: Header name (e.g., 'Price')
            subtitle_pattern: Subtitle pattern (e.g., '180d change')
            screen_name: Optional screen name to search in

        Returns:
            Dict with ticker, field, value, screen or None if not found
        """
        pass


class IHistoricalDataService(ABC):
    """
    Interface for historical performance data processing
    Handles backtest CSV parsing and universe.json updates with historical metrics
    """

    @abstractmethod
    async def parse_backtest_csv(
        self,
        csv_path: str,
        debug: bool = False
    ) -> Dict[str, Any]:
        """
        Parse a single backtest results CSV file to extract historical performance metrics

        Args:
            csv_path: Path to the backtest results CSV file
            debug: Enable debug console output

        Returns:
            Dict containing:
            - metadata: Backtest configuration and period info
            - quarterly_performance: Array of quarterly performance data
            - statistics: Key performance statistics (returns, std dev, Sharpe ratio)
            - error: Error message if parsing failed
        """
        pass

    @abstractmethod
    async def get_all_backtest_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Parse all backtest CSV files for configured screeners

        Returns:
            Dict mapping screener IDs to their parsed performance data
            Each screener entry contains metadata, quarterly_performance, and statistics
        """
        pass

    @abstractmethod
    async def update_universe_with_history(self) -> bool:
        """
        Update universe.json with historical performance data in metadata section

        Side Effects:
            - Reads data/universe.json
            - Adds metadata.historical_performance section with:
              * screen_name, backtest_metadata, key_statistics
              * quarterly_summary (total_quarters, avg_quarterly_return, quarterly_std)
              * quarterly_data (complete quarterly performance arrays)
            - Writes updated universe.json back to disk
            - Console output for success/error status

        Returns:
            True if successful, False if failed
        """
        pass

    @abstractmethod
    async def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get formatted performance summary for all screeners

        Returns:
            Dict containing structured performance data suitable for API responses
            Equivalent to display_performance_summary() but returns JSON instead of console output
        """
        pass

    @abstractmethod
    async def get_screener_backtest_data(self, screener_id: str) -> Dict[str, Any]:
        """
        Get backtest data for a specific screener

        Args:
            screener_id: Screener identifier from UNCLE_STOCK_SCREENS config

        Returns:
            Dict containing parsed backtest data or error information
        """
        pass


class IPortfolioOptimizer(ABC):
    """
    Interface for portfolio optimization using modern portfolio theory
    Implements Sharpe ratio maximization with scientific computing precision
    Following Interface-First Design for financial systems
    """

    @abstractmethod
    def load_universe_data(self) -> Dict[str, Any]:
        """
        Load universe.json data from data directory

        Returns:
            Dict containing complete universe data structure

        Raises:
            FileNotFoundError: If universe.json does not exist
        """
        pass

    @abstractmethod
    def extract_quarterly_returns(self, universe_data: Dict[str, Any]) -> pd.DataFrame:
        """
        Extract quarterly returns for each screener from universe data

        Args:
            universe_data: Complete universe data from load_universe_data()

        Returns:
            DataFrame with columns=screener_keys, index=quarters, values=decimal_returns
            Values are decimal (e.g., 0.05 for 5%), not percentages
        """
        pass

    @abstractmethod
    def calculate_portfolio_stats(
        self,
        weights: np.ndarray,
        returns: pd.DataFrame,
        risk_free_rate: float = 0.02/4
    ) -> Tuple[float, float, float]:
        """
        Calculate portfolio statistics with annualization

        Args:
            weights: Portfolio weights array (must sum to 1)
            returns: Quarterly returns DataFrame
            risk_free_rate: Quarterly risk-free rate (default: 2% annual / 4)

        Returns:
            Tuple of (expected_annual_return, annual_volatility, sharpe_ratio)
        """
        pass

    @abstractmethod
    def optimize_portfolio(
        self,
        returns: pd.DataFrame,
        risk_free_rate: float = 0.02/4
    ) -> Dict[str, Any]:
        """
        Optimize portfolio to maximize Sharpe ratio using SLSQP

        Args:
            returns: Quarterly returns DataFrame from extract_quarterly_returns()
            risk_free_rate: Quarterly risk-free rate

        Returns:
            Dict with keys:
            - optimal_weights: Dict[screener_name, weight]
            - portfolio_stats: Dict with expected_annual_return, annual_volatility, sharpe_ratio
            - individual_stats: Dict[screener_name, stats] with individual metrics
            - correlation_matrix: Dict of correlation matrix
            - optimization_success: bool
            - optimization_message: str
        """
        pass

    @abstractmethod
    def update_universe_with_portfolio(
        self,
        universe_data: Dict[str, Any],
        portfolio_results: Dict[str, Any]
    ) -> None:
        """
        Update universe data with portfolio optimization results

        Args:
            universe_data: Universe data to update (modified in-place)
            portfolio_results: Results from optimize_portfolio()

        Side Effects:
            Modifies universe_data['metadata']['portfolio_optimization']
        """
        pass

    @abstractmethod
    def save_universe(self, universe_data: Dict[str, Any]) -> None:
        """
        Save updated universe data to data/universe.json

        Args:
            universe_data: Complete universe data to save

        Side Effects:
            Writes to "data/universe.json" file
        """
        pass

    @abstractmethod
    def display_portfolio_results(self, portfolio_results: Dict[str, Any]) -> None:
        """
        Display portfolio optimization results to console

        Args:
            portfolio_results: Results from optimize_portfolio()

        Side Effects:
            Prints formatted tables to console
        """
        pass

    @abstractmethod
    def main(self) -> bool:
        """
        Main portfolio optimization orchestration function

        Returns:
            bool: True if optimization successful, False otherwise

        Side Effects:
            - Loads universe data
            - Runs optimization
            - Updates universe.json
            - Prints results to console
        """
        pass