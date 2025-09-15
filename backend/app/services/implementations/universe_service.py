"""
Universe Service Implementation
Wraps legacy parser.py functions with service interface
"""
import json
import os
from typing import Dict, Any, List, Optional
from ..interfaces import IDataParser, IUniverseRepository

# Import legacy parser functions
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'legacy'))
from .legacy.parser import (
    parse_screener_csv,
    parse_screener_csv_flexible,
    extract_field_data,
    find_available_fields,
    create_universe,
    save_universe,
    get_stock_field,
    find_column_index
)


class DataParserService(IDataParser):
    """
    Data Parser Service implementation
    Wraps legacy parser functions for CSV data processing
    """

    def parse_screener_csv(self, csv_path: str) -> List[Dict[str, Any]]:
        """
        Parse a single screener CSV file and extract standard fields

        Args:
            csv_path: Path to the CSV file

        Returns:
            List of stock dictionaries with standard fields
        """
        return parse_screener_csv(csv_path)

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
        return parse_screener_csv_flexible(csv_path, additional_fields)

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
        result = extract_field_data(csv_path, header_name, subtitle_pattern, ticker)
        return result

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
        return find_available_fields(csv_path)


class UniverseService(IUniverseRepository):
    """
    Universe Repository Service implementation
    Handles universe data creation, storage, and retrieval
    """

    def __init__(self, data_parser: IDataParser):
        """
        Initialize UniverseService with data parser dependency

        Args:
            data_parser: IDataParser implementation for CSV processing
        """
        self.data_parser = data_parser

    def create_universe(self) -> Dict[str, Any]:
        """
        Parse all screener CSV files and create universe structure

        Returns:
            Universe dictionary with metadata, screens, and all_stocks sections
        """
        # We need to change to the project root directory to make the legacy function work
        import os
        current_dir = os.getcwd()

        # Calculate project root (go up from backend/app/services/implementations to project root)
        project_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', '..', '..', '..'
        ))

        try:
            # Change to project root where data/files_exports/ exists
            os.chdir(project_root)
            return create_universe()
        finally:
            # Always restore original directory
            os.chdir(current_dir)

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
        import os
        current_dir = os.getcwd()

        # Calculate project root for proper path resolution
        project_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', '..', '..', '..'
        ))

        try:
            # Change to project root for consistent path behavior
            os.chdir(project_root)
            save_universe(universe, output_path)
        finally:
            # Always restore original directory
            os.chdir(current_dir)

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
        import os
        current_dir = os.getcwd()

        # Calculate project root for proper path resolution
        project_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', '..', '..', '..'
        ))

        try:
            # Change to project root for consistent path behavior
            os.chdir(project_root)

            if not os.path.exists(file_path):
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                universe = json.load(f)
            return universe
        except Exception as e:
            print(f"Error loading universe from {file_path}: {e}")
            return None
        finally:
            # Always restore original directory
            os.chdir(current_dir)

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
        return get_stock_field(ticker, header_name, subtitle_pattern, screen_name)

    def get_universe_metadata(self, universe: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from universe structure

        Args:
            universe: Universe dictionary

        Returns:
            Metadata dictionary with stats and configuration
        """
        return universe.get('metadata', {})

    def get_all_stocks(self, universe: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get all unique stocks from universe

        Args:
            universe: Universe dictionary

        Returns:
            Dictionary of all unique stocks with their data
        """
        return universe.get('all_stocks', {})

    def get_stocks_by_screen(
        self,
        universe: Dict[str, Any],
        screen_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get stocks for a specific screen

        Args:
            universe: Universe dictionary
            screen_id: Screen identifier

        Returns:
            List of stocks for the specified screen
        """
        screens = universe.get('screens', {})
        screen_data = screens.get(screen_id, {})
        return screen_data.get('stocks', [])

    def search_stocks_by_ticker(
        self,
        universe: Dict[str, Any],
        ticker: str
    ) -> Optional[Dict[str, Any]]:
        """
        Search for a specific stock by ticker in universe

        Args:
            universe: Universe dictionary
            ticker: Stock ticker to search for

        Returns:
            Stock data dictionary or None if not found
        """
        all_stocks = self.get_all_stocks(universe)
        return all_stocks.get(ticker)

    def get_stocks_in_multiple_screens(
        self,
        universe: Dict[str, Any]
    ) -> List[tuple]:
        """
        Get stocks that appear in multiple screens

        Args:
            universe: Universe dictionary

        Returns:
            List of tuples (ticker, stock_data) for multi-screen stocks
        """
        all_stocks = self.get_all_stocks(universe)
        multi_screen_stocks = [
            (ticker, data) for ticker, data in all_stocks.items()
            if len(data.get('screens', [])) > 1
        ]
        return multi_screen_stocks


def create_universe_service() -> UniverseService:
    """
    Factory function to create UniverseService with dependencies

    Returns:
        Configured UniverseService instance
    """
    data_parser = DataParserService()
    return UniverseService(data_parser)