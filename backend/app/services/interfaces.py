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


class IOrderExecutionService(ABC):
    """
    Interface for IBKR order execution service
    Handles order execution workflow with IBKR TWS/Gateway API
    Following Interface-First Design for financial trading systems
    """

    @abstractmethod
    async def load_orders(self, orders_file: str = "orders.json") -> Dict[str, Any]:
        """
        Load orders from JSON file in data directory

        Args:
            orders_file: Filename of orders JSON (default: "orders.json")

        Returns:
            Dict containing:
            - metadata: Order summary statistics (total_orders, buy_orders, sell_orders)
            - orders: List of order dictionaries with execution details

        Raises:
            FileNotFoundError: If orders file doesn't exist
            ValueError: If orders file format is invalid
        """
        pass

    @abstractmethod
    async def connect_to_ibkr(
        self,
        host: str = "127.0.0.1",
        port: int = 4002,
        client_id: int = 20,
        timeout: int = 15
    ) -> bool:
        """
        Establish connection to IBKR Gateway/TWS

        Args:
            host: IBKR Gateway host (default: localhost)
            port: IBKR Gateway port (default: 4002 for paper trading)
            client_id: Client ID for API connection (default: 20)
            timeout: Connection timeout in seconds (default: 15)

        Returns:
            True if connection successful and ready for trading, False otherwise

        Side Effects:
            - Establishes TCP connection to IBKR
            - Starts background thread for message processing
            - Retrieves account ID and next valid order ID
        """
        pass

    @abstractmethod
    async def execute_orders(
        self,
        max_orders: Optional[int] = None,
        delay_between_orders: float = 1.0,
        order_type: str = "GTC_MKT"
    ) -> Dict[str, Any]:
        """
        Execute loaded orders through IBKR API

        Args:
            max_orders: Limit execution to first N orders (None for all)
            delay_between_orders: Delay in seconds between order submissions
            order_type: Order type (MKT, GTC_MKT, MOO, DAY)

        Returns:
            Dict containing:
            - executed_count: Number of orders successfully submitted
            - failed_count: Number of orders that failed to submit
            - total_orders: Total orders processed
            - order_statuses: Dict mapping order_id to status info

        Side Effects:
            - Places actual orders in IBKR account
            - Generates extensive console output
            - Updates internal order tracking state
        """
        pass

    @abstractmethod
    async def get_order_statuses(self, wait_time: int = 30) -> Dict[str, Any]:
        """
        Get current status of all submitted orders

        Args:
            wait_time: Time to wait for status updates in seconds

        Returns:
            Dict containing:
            - status_summary: Count of orders by status (Filled, PreSubmitted, etc.)
            - total_filled_shares: Total shares filled across all orders
            - pending_orders_count: Number of orders still pending
            - order_details: Dict mapping order_id to detailed status info

        Side Effects:
            - Waits for specified time to collect status updates
            - Prints status summary to console
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Disconnect from IBKR Gateway/TWS

        Side Effects:
            - Closes IBKR API connection
            - Cleans up background threads
            - Prints disconnection confirmation
        """
        pass

    @abstractmethod
    async def run_execution(
        self,
        orders_file: str = "orders.json",
        max_orders: Optional[int] = None,
        delay_between_orders: float = 1.0,
        order_type: str = "GTC_MKT"
    ) -> Dict[str, Any]:
        """
        Complete order execution workflow

        Args:
            orders_file: Orders JSON filename in data directory
            max_orders: Limit execution to first N orders
            delay_between_orders: Delay between order submissions
            order_type: IBKR order type

        Returns:
            Dict containing:
            - success: Boolean indicating overall success
            - execution_summary: Summary of execution results
            - order_statuses: Final status of all orders
            - error_message: Error description if failed

        Side Effects:
            - Complete order execution workflow from load to status check
            - Extensive console output matching CLI behavior
            - File I/O for orders.json reading
            - IBKR API interactions (connection, orders, status)
        """
        pass

    @abstractmethod
    def create_ibkr_contract(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create IBKR contract specification from order data

        Args:
            order_data: Order dictionary with stock_info and ibkr_details

        Returns:
            Dict containing IBKR Contract parameters:
            - symbol, secType, exchange, primaryExchange, currency, conId

        Note:
            This is a utility method for contract creation without IBKR dependencies
        """
        pass

    @abstractmethod
    def create_ibkr_order(
        self,
        action: str,
        quantity: int,
        order_type: str = "GTC_MKT"
    ) -> Dict[str, Any]:
        """
        Create IBKR order specification

        Args:
            action: Order action (BUY or SELL)
            quantity: Number of shares to trade
            order_type: Order type (MKT, GTC_MKT, MOO, DAY)

        Returns:
            Dict containing IBKR Order parameters:
            - action, totalQuantity, orderType, tif, eTradeOnly, firmQuoteOnly

        Note:
            This is a utility method for order creation without IBKR dependencies
        """
        pass


class ITargetAllocationService(ABC):
    """
    Interface for calculating final stock allocations based on:
    1. Screener allocations from portfolio optimizer
    2. Stock performance ranking within each screener (180d price change)
    3. Linear allocation within screener (best: MAX_ALLOCATION%, worst: MIN_ALLOCATION%)
    Following Interface-First Design for financial systems
    """

    @abstractmethod
    def load_universe_data(self) -> Dict[str, Any]:
        """
        Load universe.json data from data/universe.json

        Returns:
            Dict containing complete universe data structure

        Raises:
            FileNotFoundError: If universe.json does not exist
        """
        pass

    @abstractmethod
    def extract_screener_allocations(self, universe_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract screener allocations from portfolio optimization results

        Args:
            universe_data: Complete universe data from load_universe_data()

        Returns:
            Dict with screener keys and their target allocations (as decimals)

        Raises:
            ValueError: If no portfolio optimization results found
        """
        pass

    @abstractmethod
    def parse_180d_change(self, price_change_str: str) -> float:
        """
        Parse price_180d_change string to float

        Args:
            price_change_str: String like "12.45%" or "-5.23%"

        Returns:
            Float value (e.g., 12.45 or -5.23)
            Returns 0.0 if parsing fails
        """
        pass

    @abstractmethod
    def rank_stocks_in_screener(self, stocks: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], int, float]]:
        """
        Rank stocks within a screener by 180d price change performance

        Args:
            stocks: List of stock dictionaries from screener

        Returns:
            List of tuples: (stock_dict, rank, performance_180d)
            Rank 1 = best performing, highest rank number = worst performing
        """
        pass

    @abstractmethod
    def calculate_pocket_allocation(self, rank: int, total_stocks: int) -> float:
        """
        Calculate pocket allocation within screener based on rank
        Only top MAX_RANKED_STOCKS get allocation: Rank 1 gets MAX_ALLOCATION%, rank MAX_RANKED_STOCKS gets MIN_ALLOCATION%
        Ranks beyond MAX_RANKED_STOCKS get 0%

        Args:
            rank: Stock rank (1 = best)
            total_stocks: Total number of stocks in screener

        Returns:
            Pocket allocation percentage (0.00 to MAX_ALLOCATION)
        """
        pass

    @abstractmethod
    def calculate_final_allocations(self, universe_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Calculate final allocations for all stocks

        Args:
            universe_data: Complete universe data

        Returns:
            Dict with stock tickers as keys and allocation data as values:
            {
                'ticker': {
                    'ticker': str,
                    'screener': str,
                    'rank': int,
                    'performance_180d': float,
                    'pocket_allocation': float,
                    'screener_target': float,
                    'final_allocation': float
                }
            }
        """
        pass

    @abstractmethod
    def update_universe_with_allocations(
        self,
        universe_data: Dict[str, Any],
        final_allocations: Dict[str, Dict[str, Any]]
    ) -> bool:
        """
        Update universe.json with final allocation data

        Args:
            universe_data: Universe data dictionary (modified in-place)
            final_allocations: Final allocation data for each ticker

        Returns:
            bool: True if successful, False otherwise

        Side Effects:
            Modifies universe_data adding: rank, allocation_target, screen_target, final_target
            Updates both screens.stocks and all_stocks sections
        """
        pass

    @abstractmethod
    def save_universe(self, universe_data: Dict[str, Any]) -> None:
        """
        Save updated universe data to data/universe.json

        Args:
            universe_data: Complete universe data to save

        Side Effects:
            Writes to "data/universe.json" file with proper formatting
        """
        pass

    @abstractmethod
    def get_allocation_summary(self, final_allocations: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get allocation summary data (equivalent to display_allocation_summary but returns JSON)

        Args:
            final_allocations: Final allocation data

        Returns:
            Dict containing:
            - sorted_allocations: List of allocation data sorted by final_allocation desc
            - total_allocation: Total allocation percentage
            - top_10_allocations: Top 10 allocations for quick reference
        """
        pass

    @abstractmethod
    def main(self) -> bool:
        """
        Main target allocation orchestration function

        Returns:
            bool: True if allocation calculation successful, False otherwise

        Side Effects:
            - Loads universe data
            - Calculates final allocations
            - Displays allocation summary
            - Updates universe.json with allocation data
            - Saves updated universe data
            - Prints progress and results to console
        """
        pass


class ICurrencyService(ABC):
    """
    Interface for currency exchange rate management
    Handles fetching EUR-based exchange rates and updating universe.json with currency data
    Following Interface-First Design for financial systems with external API integration
    """

    @abstractmethod
    def fetch_exchange_rates(self) -> Dict[str, float]:
        """
        Fetch current EUR-based exchange rates from external API

        External API Integration:
        - Uses exchangerate-api.com free API
        - Base currency: EUR (European Euro)
        - Endpoint: https://api.exchangerate-api.com/v4/latest/EUR
        - Timeout: 10 seconds
        - No API key required (free tier)

        Returns:
            Dict with currency codes as keys and exchange rates as values
            Always includes EUR with rate 1.0 as base currency
            Returns empty dict on API failures or network issues

        Side Effects:
            Console output: Success messages with currency count or error messages

        Error Handling:
            - HTTP status code errors (non-200 responses)
            - Network timeout (10-second limit)
            - JSON parsing errors
            - General request exceptions
            All errors result in empty dict return with console error messages
        """
        pass

    @abstractmethod
    def get_currencies_from_universe(self) -> set:
        """
        Extract all unique currency codes from universe.json file

        File Operations:
        - Reads from "data/universe.json" (hardcoded path)
        - UTF-8 encoding for international character support
        - Searches both "screens" and "all_stocks" sections

        Data Extraction Logic:
        - Iterates through screens.{}.stocks[].currency fields
        - Iterates through all_stocks.{}.currency fields
        - Collects unique currency codes into set (de-duplicated)

        Returns:
            Set of unique currency codes found in universe data
            Returns empty set if file missing or JSON parsing fails

        Side Effects:
            Console output: Success with currency count and sorted comma-separated list

        Error Handling:
            - File not found (data/universe.json missing)
            - JSON parsing errors
            - Missing or invalid currency fields (gracefully skipped)
            All errors result in empty set return with console error messages
        """
        pass

    @abstractmethod
    def update_universe_with_exchange_rates(self, exchange_rates: Dict[str, float]) -> bool:
        """
        Update universe.json by adding EUR exchange rates to ALL stock objects

        File Operations:
        - Reads "data/universe.json" with UTF-8 encoding
        - Writes updated JSON back to same file
        - Pretty formatting: 2-space indent, ensure_ascii=False for international chars

        Update Logic:
        - Processes ALL stocks in "screens" sections: screens.{}.stocks[]
        - Processes ALL stocks in "all_stocks" section: all_stocks.{}
        - Adds "eur_exchange_rate" field to each stock dictionary
        - Tracks separate counters for screens vs all_stocks updates

        Args:
            exchange_rates: Dict with currency codes and their EUR exchange rates

        Returns:
            bool: True if successful file update, False on any errors

        Side Effects:
            - Modifies data/universe.json file on disk
            - Console output: Progress messages with update counts for each section
            - Console output: Total summary and warnings for missing rates

        Statistics Tracking:
        - updated_stocks_screens: Count of stocks updated in screens sections
        - updated_stocks_all: Count of stocks updated in all_stocks section
        - missing_rates: Set of currencies without exchange rate data

        Error Handling:
        - File not found (universe.json missing)
        - JSON parsing errors (invalid JSON format)
        - File write permission issues
        - Missing currency field in stock data (gracefully skipped)
        All errors result in False return with console error messages
        """
        pass

    @abstractmethod
    def display_exchange_rate_summary(self, exchange_rates: Dict[str, float]) -> None:
        """
        Display formatted console table of fetched exchange rates

        Console Output Format:
        - Header: "EXCHANGE RATES TO EUR" with 50 "=" character border
        - Currency list: Alphabetically sorted by currency code
        - Rate precision: 4 decimal places for all rates
        - Special handling: EUR displays as "(base currency)" instead of rate
        - Rate interpretation: "1 EUR = {rate} {currency}" format

        Args:
            exchange_rates: Dict with currency codes and their EUR exchange rates

        Side Effects:
            Prints formatted exchange rate table to console
            Box-style formatting with header borders
        """
        pass

    @abstractmethod
    def run_currency_update(self) -> bool:
        """
        Execute complete 3-step currency update workflow

        Workflow Steps:
        1. "Analyzing currencies in universe.json..." → get_currencies_from_universe()
        2. "Fetching current exchange rates..." → fetch_exchange_rates()
        3. "Updating universe.json with EUR exchange rates..." → update_universe_with_exchange_rates()

        Console Output:
        - Main header: "Uncle Stock Currency Exchange Rate Updater" (60 "=" chars)
        - Step progress: Numbered steps with descriptive messages
        - Exchange rate summary table via display_exchange_rate_summary()
        - Success confirmation with feature description
        - Error messages for each step failure

        Returns:
            bool: True if entire workflow completed successfully, False on any step failure

        Side Effects:
        - Complete console output matching original CLI behavior exactly
        - File I/O: Reads and updates data/universe.json
        - External API call: Fetches from exchangerate-api.com
        - All individual function side effects included

        Error Handling:
        - Early exit on any step failure
        - Top-level exception handler for unexpected errors
        - Maintains original CLI error message format

        CLI Integration:
        This method provides identical behavior to currency.main() for CLI compatibility
        """
        pass


class IRebalancingService(ABC):
    """
    Interface for portfolio rebalancing and order generation
    Connects to IBKR API to fetch current positions and generates orders
    Following Interface-First Design for trading system integration
    """

    @abstractmethod
    def load_universe_data(self, universe_file: str) -> Dict[str, Any]:
        """
        Load universe data with IBKR details and target quantities

        Args:
            universe_file: Path to universe_with_ibkr.json file

        Returns:
            Dict containing complete universe data structure

        Raises:
            FileNotFoundError: If universe file does not exist
        """
        pass

    @abstractmethod
    def calculate_target_quantities(self, universe_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Calculate target quantities by aggregating across all screens for each IBKR symbol

        Args:
            universe_data: Complete universe data from load_universe_data()

        Returns:
            Dict mapping IBKR symbol to total target quantity

        Side Effects:
            Prints progress to console for target calculation
        """
        pass

    @abstractmethod
    def fetch_current_positions(self) -> Tuple[Dict[str, int], Dict[str, Dict[str, Any]]]:
        """
        Fetch current positions from IBKR account via live API connection

        Returns:
            Tuple of (current_positions, contract_details)
            - current_positions: Dict mapping symbol to current quantity
            - contract_details: Dict mapping symbol to IBKR contract info

        Side Effects:
            - Establishes connection to IBKR Gateway (127.0.0.1:4002)
            - Prints connection status and position data to console
            - Uses threading for IBKR API message processing

        Raises:
            Exception: If connection to IBKR Gateway fails or timeout
        """
        pass

    @abstractmethod
    def generate_orders(
        self,
        target_quantities: Dict[str, int],
        current_positions: Dict[str, int],
        symbol_details: Dict[str, Dict[str, Any]],
        current_contract_details: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate buy/sell orders to reach target quantities

        Args:
            target_quantities: Dict mapping symbol to target quantity
            current_positions: Dict mapping symbol to current quantity
            symbol_details: Symbol information from universe data
            current_contract_details: IBKR contract details from fetch_current_positions()

        Returns:
            List of order dictionaries with structure:
            {
                'symbol': str,
                'action': 'BUY'|'SELL',
                'quantity': int,
                'current_quantity': int,
                'target_quantity': int,
                'stock_info': {
                    'ticker': str,
                    'name': str,
                    'currency': str,
                    'screens': List[str]
                },
                'ibkr_details': {
                    'symbol': str,
                    'exchange': str,
                    'primaryExchange': str,
                    'conId': int
                }
            }

        Side Effects:
            Prints order generation progress and summary to console
        """
        pass

    @abstractmethod
    def save_orders_json(
        self,
        orders: List[Dict[str, Any]],
        output_file: str = "orders.json"
    ) -> None:
        """
        Save orders to JSON file with metadata

        Args:
            orders: List of order dictionaries from generate_orders()
            output_file: Output file path (defaults to "orders.json" in data directory)

        Side Effects:
            Creates data/orders.json with complete metadata structure
        """
        pass

    @abstractmethod
    def run_rebalancing(self, universe_file: str) -> Dict[str, Any]:
        """
        Execute complete rebalancing process orchestration

        Args:
            universe_file: Path to universe_with_ibkr.json file

        Returns:
            Dict containing:
            - orders: List of generated orders
            - metadata: Summary statistics
            - target_quantities: Dict of calculated targets
            - current_positions: Dict of current positions

        Side Effects:
            - Loads universe data
            - Calculates target quantities
            - Fetches current positions from IBKR
            - Generates orders
            - Saves orders to data/orders.json
            - Prints complete rebalancing summary to console
        """
        pass


class IOrderStatusService(ABC):
    """
    Interface for order status checking and verification against IBKR
    Handles connection to IBKR Gateway, data collection, and comparison with orders.json
    Following Interface-First Design for trading system verification
    """

    @abstractmethod
    def load_orders_json(self, orders_file: str = "orders.json") -> Dict[str, Any]:
        """
        Load orders from JSON file created by rebalancer

        Args:
            orders_file: Path to orders JSON file (defaults to data/orders.json)

        Returns:
            Dict containing:
            - metadata: Order metadata with total_orders count
            - orders: List of order dictionaries

        Side Effects:
            Console output showing file path and total orders loaded

        Raises:
            FileNotFoundError: If orders.json file does not exist
        """
        pass

    @abstractmethod
    def connect_to_ibkr(self) -> bool:
        """
        Establish connection to IBKR Gateway with enhanced order detection

        Connection Details:
            - Host: 127.0.0.1:4002
            - Client ID: 99 (high ID to avoid conflicts and see ALL orders)
            - Timeout: 15 seconds for connection
            - Extended wait: 10 seconds to capture orders with high IDs (up to 500+)
            - Threading: Daemon thread for API message processing

        Returns:
            True if connected and account ID received, False otherwise

        Side Effects:
            - Creates IBKR API connection thread
            - Console output for connection status and immediate order callbacks
            - Populates initial order data during connection phase

        Raises:
            Exception: If connection to IBKR Gateway fails
        """
        pass

    @abstractmethod
    def fetch_account_data(self) -> None:
        """
        Comprehensive data fetching using multiple IBKR API methods

        API Methods Used:
            - reqAllOpenOrders(): Gets ALL open orders (not just from current client)
            - reqOpenOrders(): Gets orders from current client
            - reqAutoOpenOrders(True): Requests automatic order binding
            - reqPositions(): Gets all positions
            - reqCompletedOrders(False): Gets all completed orders (not just API orders)
            - reqExecutions(1, exec_filter): Gets executions from today

        Timeouts:
            - 20-second extended timeout for high order IDs (up to 500+)
            - Progress updates every 6 seconds

        Side Effects:
            - Populates open_orders, completed_orders, positions, executions data
            - Console progress updates with counts and max order ID
            - Request completion tracking via flags
        """
        pass

    @abstractmethod
    def analyze_orders(self) -> Dict[str, Any]:
        """
        Core comparison logic between JSON orders and IBKR status

        Comparison Strategy:
            - Creates lookup dictionaries by symbol
            - Matches orders by symbol and action (BUY/SELL)
            - Tracks found_in_ibkr, missing_from_ibkr, quantity_mismatches

        Returns:
            Dict containing:
            - found_in_ibkr: int count of matched orders
            - missing_from_ibkr: int count of missing orders
            - quantity_mismatches: int count of quantity differences
            - success_rate: float percentage of successful matches
            - missing_orders: List of orders not found in IBKR
            - extra_ibkr_orders: List of IBKR orders not in JSON
            - analysis_table: List of comparison results for each order

        Side Effects:
            Console output with formatted comparison table and summary statistics
        """
        pass

    @abstractmethod
    def get_missing_order_analysis(self, missing_orders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detailed failure analysis with known patterns and recommendations

        Known Failure Patterns:
            - AAPL: Account restriction - direct NASDAQ routing disabled (Error 10311)
            - DPM: Contract not supported - TSE contract resolution failed (Error 202)
            - AJ91: Liquidity constraints - volume too large (Error 202)
            - MOUR: Extreme illiquidity - even small orders rejected (Error 202)

        Args:
            missing_orders: List of order dictionaries not found in IBKR

        Returns:
            Dict containing:
            - failure_analysis: List of detailed failure information for each order
            - recommendations: List of actionable recommendations
            - failure_patterns: Dict of known failure reasons by symbol

        Side Effects:
            Console output with detailed failure analysis and recommendations
        """
        pass

    @abstractmethod
    def get_order_status_summary(self) -> Dict[str, Any]:
        """
        Get detailed status breakdown of all IBKR orders

        Returns:
            Dict containing:
            - orders_by_status: Dict mapping status to list of orders
            - status_counts: Dict mapping status to count
            - total_orders: int total number of orders
            - order_details: List of all order information

        Side Effects:
            Console output with comprehensive order status tables by status group
        """
        pass

    @abstractmethod
    def get_positions_summary(self) -> Dict[str, Any]:
        """
        Get current account positions summary

        Returns:
            Dict containing:
            - positions: Dict mapping symbol to position information
            - total_positions: int count of positions
            - market_values: Dict mapping symbol to market value
            - total_market_value: float sum of all market values

        Side Effects:
            Console output with formatted position table and summary
        """
        pass

    @abstractmethod
    def run_status_check(self) -> bool:
        """
        Execute complete order status check workflow

        Workflow:
            1. Load orders from JSON (data/orders.json)
            2. Connect to IBKR Gateway (127.0.0.1:4002)
            3. Fetch current account data (orders, positions, executions)
            4. Analyze orders (comparison between JSON and IBKR)
            5. Show detailed status breakdown
            6. Show current positions
            7. Disconnect from IBKR

        Returns:
            True if status check completed successfully, False if failed

        Side Effects:
            - Complete console output workflow matching CLI behavior
            - IBKR API connection and disconnection
            - Data collection and analysis
            - Formatted reporting tables and summaries

        Raises:
            Exception: If any step in the workflow fails
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        Disconnect from IBKR Gateway and cleanup resources

        Side Effects:
            - Closes IBKR API connection
            - Stops message processing thread
            - Console output confirming disconnection
        """
        pass

    @abstractmethod
    def get_verification_results(self) -> Dict[str, Any]:
        """
        Get verification results without console output for API responses

        Returns:
            Dict containing complete verification results suitable for JSON API responses:
            - comparison_summary: Summary statistics
            - order_matches: List of matched orders
            - missing_orders: List of missing orders with analysis
            - extra_orders: List of extra IBKR orders
            - positions: Current position data
            - order_status_breakdown: Orders grouped by status
        """
        pass


class IPipelineOrchestrator(ABC):
    """
    Interface for pipeline orchestration service
    Handles complete 11-step fintech pipeline execution with CLI compatibility
    Following Interface-First Design for trading system orchestration
    """

    @abstractmethod
    async def run_full_pipeline(self, execution_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute complete 11-step pipeline with fail-fast error handling (equivalent to CLI run_all_steps())

        Args:
            execution_id: Optional execution ID for tracking (generated if not provided)

        Returns:
            Dict containing:
            - execution_id: Unique execution identifier
            - success: Boolean indicating overall pipeline success
            - completed_steps: List of successfully completed step numbers
            - failed_step: Step number that failed (None if all successful)
            - execution_time: Total execution time in seconds
            - created_files: Dict mapping step numbers to created files
            - step_results: Dict mapping step numbers to detailed results
            - error_message: Error description if pipeline failed

        Side Effects:
            - Creates complete file ecosystem matching CLI behavior exactly
            - Structured logging of all console output from original CLI
            - Background task execution with real-time status tracking
        """
        pass

    @abstractmethod
    async def run_individual_step(
        self,
        step_number: int,
        execution_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute single pipeline step (equivalent to CLI python main.py [step_number])

        Args:
            step_number: Step number to execute (1-11)
            execution_id: Optional execution ID for tracking

        Returns:
            Dict containing:
            - execution_id: Unique execution identifier
            - step_number: Step number executed
            - step_name: Human-readable step name
            - success: Boolean indicating step success
            - execution_time: Step execution time in seconds
            - created_files: List of files created by this step
            - console_output: Captured console output from step
            - error_message: Error description if step failed

        Side Effects:
            - Executes specific step function (step1_fetch_data through step11_check_order_status)
            - File creation/modification matching CLI behavior
            - Console output capture and structured logging
        """
        pass

    @abstractmethod
    async def run_step_range(
        self,
        start_step: int,
        end_step: int,
        execution_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute range of pipeline steps with fail-fast behavior

        Args:
            start_step: First step number to execute (1-11)
            end_step: Last step number to execute (1-11)
            execution_id: Optional execution ID for tracking

        Returns:
            Dict containing:
            - execution_id: Unique execution identifier
            - success: Boolean indicating range success
            - start_step: First step number
            - end_step: Last step number
            - completed_steps: List of successfully completed step numbers
            - failed_step: Step number that failed (None if all successful)
            - execution_time: Total execution time in seconds
            - step_results: Dict mapping step numbers to detailed results

        Side Effects:
            - Sequential execution of steps in range with fail-fast stopping
            - File creation/modification for each step
            - Structured logging and status tracking
        """
        pass

    @abstractmethod
    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """
        Get real-time status of running or completed pipeline execution

        Args:
            execution_id: Execution identifier from run_full_pipeline or run_individual_step

        Returns:
            Dict containing:
            - execution_id: Execution identifier
            - status: Execution status (running, completed, failed, not_found)
            - current_step: Currently executing step (None if not running)
            - completed_steps: List of completed step numbers
            - failed_step: Step number that failed (None if no failure)
            - start_time: Execution start timestamp
            - execution_time: Current or total execution time in seconds
            - progress_percentage: Execution progress (0-100)
            - estimated_remaining_time: Estimated remaining time in seconds (None if not calculable)
        """
        pass

    @abstractmethod
    async def get_execution_logs(
        self,
        execution_id: str,
        step_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get structured execution logs for pipeline run

        Args:
            execution_id: Execution identifier
            step_number: Optional step number to filter logs (None for all steps)

        Returns:
            Dict containing:
            - execution_id: Execution identifier
            - logs: List of structured log entries with timestamp, step, level, message
            - step_logs: Dict mapping step numbers to their specific logs (if step_number is None)
            - total_log_entries: Total number of log entries
        """
        pass

    @abstractmethod
    async def get_execution_results(self, execution_id: str) -> Dict[str, Any]:
        """
        Get detailed execution results and created files

        Args:
            execution_id: Execution identifier

        Returns:
            Dict containing:
            - execution_id: Execution identifier
            - success: Overall execution success
            - created_files: Dict mapping step numbers to created file paths
            - file_summaries: Dict with file metadata (size, creation time, etc.)
            - step_summaries: Dict with step execution summaries
            - performance_metrics: Execution performance data
        """
        pass

    @abstractmethod
    async def resume_failed_pipeline(
        self,
        execution_id: str,
        from_step: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Resume failed pipeline execution from specified step

        Args:
            execution_id: Original execution identifier that failed
            from_step: Step number to resume from (None to auto-detect from failure point)

        Returns:
            Dict containing:
            - execution_id: New execution identifier for resumed run
            - original_execution_id: Original failed execution identifier
            - resumed_from_step: Step number resumed from
            - success: Boolean indicating resume success
            - completed_steps: List of completed steps in resumed run
            - execution_time: Total time for resumed portion
        """
        pass

    @abstractmethod
    async def get_pipeline_history(
        self,
        limit: int = 50,
        status_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get history of pipeline executions

        Args:
            limit: Maximum number of executions to return
            status_filter: Optional status filter (completed, failed, running)

        Returns:
            Dict containing:
            - executions: List of execution summaries
            - total_executions: Total number of executions in history
            - filtered_count: Number of executions matching filter
        """
        pass

    @abstractmethod
    def get_available_steps(self) -> Dict[str, Any]:
        """
        Get list of all available pipeline steps with descriptions

        Returns:
            Dict containing:
            - steps: Dict mapping step numbers to step information
            - total_steps: Total number of available steps
            - step_aliases: Dict mapping CLI aliases to step numbers
        """
        pass

    @abstractmethod
    async def validate_pipeline_dependencies(self) -> Dict[str, Any]:
        """
        Validate that all pipeline dependencies and prerequisites are met

        Returns:
            Dict containing:
            - valid: Boolean indicating if all dependencies are met
            - checks: Dict mapping dependency names to validation results
            - missing_dependencies: List of missing dependencies
            - recommendations: List of recommendations to fix issues
        """
        pass

    @abstractmethod
    def get_step_function_mapping(self) -> Dict[int, callable]:
        """
        Get mapping of step numbers to their corresponding functions

        Returns:
            Dict mapping step numbers (1-11) to callable step functions

        Note:
            This method provides access to the original CLI step functions
            for direct wrapping and execution preservation
        """
        pass


class IAccountService(ABC):
    """
    Interface for IBKR account data management
    Handles connection to Interactive Brokers API and account value fetching
    Following fintech security and reliability standards
    """

    @abstractmethod
    async def get_account_total_value(self) -> Tuple[Optional[float], Optional[str]]:
        """
        Connect to IBKR and fetch account net liquidation value

        IBKR Integration Details:
        - Connects to 127.0.0.1:4002 (paper trading gateway)
        - Uses threading for API message processing
        - 10-second connection timeout with retry logic
        - Requests NetLiquidation from account summary

        Returns:
            Tuple of (total_value: float, currency: str) on success
            Tuple of (None, None) on failure (connection issues, timeout, etc.)

        Side Effects:
            - Creates/destroys IBKR API connection
            - Console output for connection status and values
            - Threading: Spawns daemon thread for message processing

        Error Handling:
            - Connection failures to IB Gateway
            - Timeout scenarios (connection, account ID, data retrieval)
            - Missing account ID from managedAccounts callback
            - Network connectivity issues
        """
        pass

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test IBKR connection without fetching account data

        Returns:
            Dict with connection test results:
            - connected: bool
            - account_id: Optional[str]
            - connection_time: float (seconds)
            - error_message: Optional[str]
        """
        pass


class IQuantityCalculator(ABC):
    """
    Interface for portfolio quantity calculations
    Handles EUR conversions, target allocations, and stock quantity computations
    Following financial precision standards and risk management principles
    """

    @abstractmethod
    def calculate_stock_quantities(
        self,
        universe_data: Dict[str, Any],
        account_value: float
    ) -> int:
        """
        Calculate EUR prices and quantities for all stocks based on account value and target allocations

        Processing Logic:
        - Handles both "screens" and "all_stocks" categories in universe data
        - Integrates with portfolio_optimization.optimal_allocations from metadata
        - Counts total processed, minimal allocations (<1e-10), meaningful allocations (>1e-10)

        Args:
            universe_data: Complete universe data structure from universe.json
            account_value: Total account value in EUR for allocation calculations

        Returns:
            int: Total number of stocks processed with quantity calculations

        Side Effects:
            - Modifies universe_data in-place with new calculated fields
            - Console progress output for processing status
            - Updates stock dictionaries with eur_price, target_value_eur, quantity fields

        Validation:
        - Validates stock dictionaries structure
        - Handles missing screen data gracefully
        - Processes both screen context and all_stocks context
        """
        pass

    @abstractmethod
    def calculate_stock_fields(
        self,
        stock: Dict[str, Any],
        account_value: float,
        screen_allocation: Optional[float] = None
    ) -> None:
        """
        Calculate EUR price, target value, and quantity for individual stock

        Financial Calculations:
        - EUR price conversion: price / eur_exchange_rate
        - Target value: account_value * final_target
        - Quantity calculation: target_value_eur / eur_price

        Target Allocation Logic:
        - If screen_allocation provided: final_target = allocation_target * screen_allocation
        - If screen_allocation None: uses existing final_target (for all_stocks context)

        Japanese Stock Handling:
        - Detects JPY currency stocks
        - Rounds to 100-share lots (minimum lot size requirement)
        - Conservative rounding DOWN to avoid fractional lot purchases

        Args:
            stock: Stock dictionary to update with calculated fields
            account_value: Total account value in EUR
            screen_allocation: Optional screen allocation factor (for screen context)

        Side Effects:
            - Modifies stock dictionary in-place with new fields:
              * eur_price: EUR equivalent price (6 decimal precision)
              * target_value_eur: Target value in EUR (2 decimal precision)
              * quantity: Integer quantity to purchase
              * allocation_note: "minimal_allocation" flag for very small allocations
            - Console output for Japanese stock lot size adjustments

        Error Handling:
            - ValueError, TypeError, ZeroDivisionError with graceful fallback to 0 values
            - Missing or invalid price/exchange rate data handling
        """
        pass

    @abstractmethod
    def update_universe_json(
        self,
        account_value: float,
        currency: str
    ) -> bool:
        """
        Update universe.json with account value and calculate all stock quantities

        File Operations:
        - Reads data/universe.json with UTF-8 encoding
        - Creates top-level "account_total_value" section with value, currency, timestamp
        - Writes updated universe.json back to disk

        Account Value Storage Structure:
        {
            "account_total_value": {
                "value": float,
                "currency": str,
                "timestamp": str (YYYY-MM-DD HH:MM:SS format)
            }
        }

        Args:
            account_value: Total account value (already rounded to nearest 100€)
            currency: Account currency (typically "EUR")

        Returns:
            bool: True on successful update, False on failure

        Side Effects:
            - Modifies universe.json file on disk
            - Console output for success/failure status
            - Updates all stocks with calculated quantities

        Error Handling:
            - File not found (universe.json missing)
            - JSON parsing errors
            - File write permission issues
            - Invalid universe data structure
        """
        pass

    @abstractmethod
    def round_account_value_conservatively(self, account_value: float) -> float:
        """
        Round account value DOWN to nearest 100€ for conservative allocation calculations

        Risk Management:
        - Prevents over-allocation beyond account capacity
        - Avoids fractional quantity issues
        - Conservative approach for financial safety

        Args:
            account_value: Original account value in EUR

        Returns:
            float: Rounded account value (DOWN to nearest 100€)

        Example:
            €9,847.32 → €9,800.00
            €10,000.00 → €10,000.00
            €10,099.99 → €10,000.00
        """
        pass


class IIBKRSearchService(ABC):
    """
    Interface for IBKR stock identification and symbol search service
    Handles comprehensive stock search using multiple strategies with IBKR Gateway API
    Following Interface-First Design for trading system integration
    """

    @abstractmethod
    def extract_unique_stocks(self, universe_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract unique stocks from universe.json using ticker as key
        Only includes stocks with quantities > 0

        Args:
            universe_data: Complete universe data structure from universe.json

        Returns:
            List of unique stock dictionaries with fields:
            - ticker, isin, name, currency, sector, country, quantity, final_target

        Logic:
            - Processes all screens in universe data
            - Uses ticker as unique identifier
            - For duplicates: picks stock with highest quantity
            - If quantities equal: picks stock with highest final_target
        """
        pass

    @abstractmethod
    def get_all_ticker_variations(self, ticker: str) -> List[str]:
        """
        Generate comprehensive ticker format variations for different exchanges
        Handles exchange suffixes, share classes, and regional variations

        Args:
            ticker: Original ticker string (e.g., "OR.PA", "ROCK-A.CO")

        Returns:
            List of ticker variations for search:
            - OR.PA → ["OR.PA", "OR"]
            - ROCK-A.CO → ["ROCK-A.CO", "ROCKA", "ROCK.A", "ROCKA", "ROCK.A"]

        Special Handling:
            - Japanese stocks (.T suffix): removes .T
            - Share classes (-A, -B): converts to .A/.B and removes dashes
            - Greek stocks (.AT): removes .AT, adds A suffix variants
            - European exchanges (.PA, .L, .HE): removes suffixes
        """
        pass

    @abstractmethod
    def is_valid_match(
        self,
        universe_stock: Dict[str, Any],
        ibkr_contract: Dict[str, Any],
        search_method: str = "unknown"
    ) -> Tuple[bool, str]:
        """
        Validate if IBKR contract matches universe stock using method-specific criteria

        Args:
            universe_stock: Stock dict with name, currency from universe
            ibkr_contract: IBKR contract details with longName, currency
            search_method: Search method used ("isin", "ticker", "name")

        Returns:
            Tuple of (is_valid: bool, reason: str)

        Validation Rules by Method:
            - isin: Requires 60% name similarity OR 2+ word overlap
            - ticker: Very lenient (30% similarity OR any word overlap)
            - name: Strict (80% similarity OR exact words + 50% similarity)

        Required Validations:
            - Currency match (mandatory for all methods)
            - Name similarity with punctuation/accent normalization
            - Word overlap analysis (excludes corporate suffixes)
        """
        pass

    @abstractmethod
    def search_by_name_matching(
        self,
        app: Any,
        stock: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Use reqMatchingSymbols to search by company name parts
        Fallback method when ISIN and ticker searches fail

        Args:
            app: IBApi instance for IBKR communication
            stock: Stock dictionary with name, currency fields

        Returns:
            List of matching contract details from IBKR

        Search Logic:
            - Extracts meaningful words from company name (3+ letters)
            - Tries individual words and combinations
            - Uses special mappings for known problematic stocks
            - Filters by currency match before detailed contract lookup
            - 5-second timeout per search term, 3-second timeout for contract details
        """
        pass

    @abstractmethod
    def comprehensive_stock_search(
        self,
        app: Any,
        stock: Dict[str, Any],
        verbose: bool = False
    ) -> Tuple[Optional[Dict[str, Any]], float]:
        """
        Comprehensive search using multiple strategies with validation

        Args:
            app: IBApi instance for IBKR communication
            stock: Stock dictionary with ticker, isin, name, currency
            verbose: Enable debug console output

        Returns:
            Tuple of (best_match_contract: Dict, similarity_score: float)
            Returns (None, 0.0) if no valid matches found

        Search Strategy (Sequential):
            1. ISIN search (if available) - highest confidence
            2. Ticker variations on SMART exchange
            3. Name-based symbol matching (fallback)

        Each strategy marks results with '_search_method' for validation
        Best match selection based on name similarity score
        """
        pass

    @abstractmethod
    def update_universe_with_ibkr_details(
        self,
        universe_data: Dict[str, Any],
        stock_ticker: str,
        ibkr_details: Dict[str, Any]
    ) -> None:
        """
        Update universe.json with IBKR identification details for all instances of stock

        Args:
            universe_data: Universe data dictionary (modified in-place)
            stock_ticker: Ticker to search for and update
            ibkr_details: IBKR contract details to add

        Side Effects:
            Modifies universe_data in-place by adding 'ibkr_details' section:
            {
                'found': True,
                'symbol': str,
                'longName': str,
                'exchange': str,
                'primaryExchange': str,
                'conId': int,
                'search_method': str,
                'match_score': float
            }

        Updates all instances of the stock across all screens where ticker matches
        """
        pass

    @abstractmethod
    def mark_stock_not_found(
        self,
        universe_data: Dict[str, Any],
        stock_ticker: str
    ) -> None:
        """
        Mark stock as not found in IBKR across all instances

        Args:
            universe_data: Universe data dictionary (modified in-place)
            stock_ticker: Ticker to mark as not found

        Side Effects:
            Modifies universe_data in-place by adding 'ibkr_details' section:
            {
                'found': False,
                'search_attempted': True
            }
        """
        pass

    @abstractmethod
    def process_all_universe_stocks(self) -> Dict[str, Any]:
        """
        Main orchestration function - process all stocks from universe.json sequentially
        Maintains exact behavior compatibility with legacy implementation

        File Operations:
            - Reads from: data/universe.json
            - Writes to: data/universe_with_ibkr.json

        IBKR Connection:
            - Host: 127.0.0.1:4002
            - Client ID: 20
            - Connection timeout: 10 seconds

        Processing Logic:
            - Extracts unique stocks (ticker-based deduplication)
            - Filters to stocks with quantity > 0
            - Sequential processing with 0.5s delays between stocks
            - Three-strategy search per stock
            - Statistics tracking by search method

        Returns:
            Dict containing:
            - total: Total unique stocks processed
            - found_isin: Count found via ISIN search
            - found_ticker: Count found via ticker search
            - found_name: Count found via name search
            - not_found: Count not found in IBKR
            - not_found_stocks: List of stocks not found with details

        Side Effects:
            - Creates universe_with_ibkr.json file
            - Extensive console output matching legacy exactly
            - IBKR API connection establishment and cleanup
            - Progress reporting for each stock processed

        Console Output:
            - Connection status
            - Per-stock progress: [N/total] Processing: name (ticker)
            - Search results: FOUND/NOT FOUND with method and score
            - Final statistics table with percentages
            - Coverage summary and missing stock details
        """
        pass


class ITelegramService(ABC):
    """
    Interface for Telegram notification service
    Provides real-time notifications for pipeline execution and system events
    Following Interface-First Design for external messaging service integration
    """

    @abstractmethod
    async def send_message(
        self,
        message: str,
        parse_mode: str = "Markdown",
        disable_notification: bool = False
    ) -> bool:
        """
        Send a message to the configured Telegram chat

        Args:
            message: Text message to send (supports Markdown formatting)
            parse_mode: Message formatting mode (Markdown, HTML, or None)
            disable_notification: Send message silently without notification

        Returns:
            bool: True if message sent successfully, False otherwise

        Side Effects:
            - Sends HTTP request to Telegram Bot API
            - May trigger notification to user's device
        """
        pass

    @abstractmethod
    async def notify_step_start(
        self,
        step_number: int,
        step_name: str,
        execution_id: str
    ) -> bool:
        """
        Send notification when pipeline step starts execution

        Args:
            step_number: Pipeline step number (1-11)
            step_name: Human-readable step name
            execution_id: Unique execution identifier

        Returns:
            bool: True if notification sent successfully

        Side Effects:
            - Formats and sends step start notification
            - Includes execution timestamp and step details
        """
        pass

    @abstractmethod
    async def notify_step_complete(
        self,
        step_number: int,
        step_name: str,
        execution_id: str,
        success: bool,
        execution_time: float,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send notification when pipeline step completes

        Args:
            step_number: Pipeline step number (1-11)
            step_name: Human-readable step name
            execution_id: Unique execution identifier
            success: Whether step completed successfully
            execution_time: Step execution duration in seconds
            details: Optional additional details (files created, errors, etc.)

        Returns:
            bool: True if notification sent successfully

        Side Effects:
            - Formats success/failure notification with timing
            - Includes error details if step failed
            - Shows created files and processing statistics
        """
        pass

    @abstractmethod
    async def notify_pipeline_start(
        self,
        pipeline_type: str,
        target_steps: List[int],
        execution_id: str
    ) -> bool:
        """
        Send notification when pipeline execution begins

        Args:
            pipeline_type: Type of pipeline (daily, monthly, manual)
            target_steps: List of steps to be executed
            execution_id: Unique execution identifier

        Returns:
            bool: True if notification sent successfully

        Side Effects:
            - Sends pipeline start notification with step overview
            - Includes execution type and expected duration
        """
        pass

    @abstractmethod
    async def notify_pipeline_complete(
        self,
        pipeline_type: str,
        execution_id: str,
        success: bool,
        completed_steps: List[int],
        failed_step: Optional[int],
        execution_time: float,
        summary_stats: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send notification when pipeline execution completes

        Args:
            pipeline_type: Type of pipeline (daily, monthly, manual)
            execution_id: Unique execution identifier
            success: Whether entire pipeline succeeded
            completed_steps: List of successfully completed steps
            failed_step: Step number where pipeline failed (if any)
            execution_time: Total pipeline execution time in seconds
            summary_stats: Optional execution summary statistics

        Returns:
            bool: True if notification sent successfully

        Side Effects:
            - Sends comprehensive pipeline completion report
            - Includes success/failure status, timing, and statistics
            - Provides failure details if pipeline failed
        """
        pass

    @abstractmethod
    async def send_daily_summary(
        self,
        portfolio_value: float,
        active_positions: int,
        orders_executed: int,
        performance_change: Optional[float] = None
    ) -> bool:
        """
        Send daily portfolio performance summary

        Args:
            portfolio_value: Current total portfolio value in EUR
            active_positions: Number of active stock positions
            orders_executed: Number of orders executed today
            performance_change: Daily performance change percentage

        Returns:
            bool: True if summary sent successfully

        Side Effects:
            - Sends formatted daily portfolio summary
            - Includes key performance metrics and statistics
        """
        pass

    @abstractmethod
    async def send_error_alert(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send critical error alert notification

        Args:
            error_type: Type of error (SERVICE_FAILURE, API_ERROR, etc.)
            error_message: Detailed error message
            context: Optional context information (step, service, etc.)

        Returns:
            bool: True if alert sent successfully

        Side Effects:
            - Sends high-priority error notification
            - Includes error details and troubleshooting context
        """
        pass

    @abstractmethod
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get current Telegram service configuration and status

        Returns:
            Dict containing:
            - configured: Whether service is properly configured
            - bot_token_valid: Whether bot token is valid format
            - chat_id_configured: Whether chat ID is set
            - last_message_sent: Timestamp of last successful message
            - message_count: Total messages sent in current session

        Side Effects:
            - None (read-only status check)
        """
        pass