"""
File management service implementation
Handles CSV file operations with exact legacy compatibility
"""
import os
from pathlib import Path
from typing import Optional
import logging

from ..interfaces import IFileManager
from ...core.exceptions import FileOperationError

logger = logging.getLogger(__name__)


class FileManager(IFileManager):
    """
    File management implementation matching legacy behavior
    Ensures 100% compatibility with existing file operations
    """

    def save_csv_data(
        self,
        content: str,
        filename: str,
        directory: str = "data/files_exports"
    ) -> str:
        """
        Save CSV data to file with legacy-compatible directory management

        This exactly replicates the legacy behavior:
        1. Create directory if it doesn't exist
        2. Save content to file with UTF-8 encoding
        3. Return full file path
        4. Print success message to console (for CLI compatibility)
        """
        try:
            # Ensure directory exists (legacy: os.makedirs("data/files_exports", exist_ok=True))
            self.ensure_directory_exists(directory)

            # Construct full file path
            full_path = os.path.join(directory, filename)

            # Save file with UTF-8 encoding (matching legacy implementation)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Print success message for CLI compatibility
            # This matches the exact legacy print statement
            print(f"Saved {filename} to: {full_path}")

            logger.info(f"Successfully saved CSV file: {full_path}")
            return full_path

        except OSError as e:
            error_msg = f"Failed to save CSV file {filename}: {str(e)}"
            # Print warning for CLI compatibility (matches legacy behavior)
            print(f"Warning: Could not save CSV file: {str(e)}")
            logger.error(error_msg)
            raise FileOperationError(error_msg, details={"filename": filename, "directory": directory})

    def sanitize_filename(self, name: str) -> str:
        """
        Sanitize filename to match legacy implementation

        Legacy behavior:
        - Replace spaces with underscores
        - Replace forward slashes with underscores

        This ensures identical filename generation as the legacy system
        """
        # Exact replication of legacy logic:
        # safe_query_name = query_name.replace(' ', '_').replace('/', '_')
        return name.replace(' ', '_').replace('/', '_')

    def ensure_directory_exists(self, directory: str) -> None:
        """
        Ensure directory exists, create if necessary

        Matches legacy: os.makedirs("data/files_exports", exist_ok=True)
        """
        try:
            os.makedirs(directory, exist_ok=True)
            logger.debug(f"Directory ensured: {directory}")
        except OSError as e:
            error_msg = f"Failed to create directory {directory}: {str(e)}"
            logger.error(error_msg)
            raise FileOperationError(error_msg, details={"directory": directory})

    def get_csv_filename(self, query_name: str, file_type: str) -> str:
        """
        Generate CSV filename following legacy naming convention

        Args:
            query_name: Original query name
            file_type: Type of file ('current_screen' or 'backtest_results')

        Returns:
            Sanitized filename matching legacy format
        """
        safe_query_name = self.sanitize_filename(query_name)
        return f"{safe_query_name}_{file_type}.csv"