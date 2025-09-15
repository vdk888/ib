#!/usr/bin/env python3
"""
Basic functionality test for Step 1 implementation
Tests the implementation without requiring live API calls
"""
import asyncio
import sys
import os
from unittest.mock import patch, Mock

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.implementations.file_manager import FileManager
from app.services.implementations.uncle_stock_provider import UncleStockProvider
from app.services.implementations.screener_service import ScreenerService


def test_file_manager():
    """Test file manager functionality"""
    print("Testing File Manager...")

    file_manager = FileManager()

    # Test filename sanitization (core legacy compatibility)
    test_cases = [
        ("quality bloom", "quality_bloom"),
        ("TOR Surplus", "TOR_Surplus"),
        ("Moat Companies", "Moat_Companies"),
        ("test/query with spaces", "test_query_with_spaces"),
    ]

    for input_name, expected in test_cases:
        result = file_manager.sanitize_filename(input_name)
        assert result == expected, f"Expected {expected}, got {result}"
        print(f"  + '{input_name}' -> '{result}'")

    # Test CSV filename generation
    filename = file_manager.get_csv_filename("quality bloom", "current_screen")
    expected = "quality_bloom_current_screen.csv"
    assert filename == expected, f"Expected {expected}, got {filename}"
    print(f"  + CSV filename: {filename}")

    print("File Manager: PASSED\n")


async def test_uncle_stock_provider_structure():
    """Test Uncle Stock provider structure without API calls"""
    print("Testing Uncle Stock Provider Structure...")

    # Mock the settings to avoid configuration error
    with patch('app.services.implementations.uncle_stock_provider.settings') as mock_settings:
        mock_settings.uncle_stock.uncle_stock_user_id = "test_user"
        mock_settings.uncle_stock.uncle_stock_timeout = 60
        mock_settings.uncle_stock.uncle_stock_screens = {
            "quality_bloom": "quality bloom",
            "TOR_Surplus": "TOR Surplus",
            "Moat_Companies": "Moat Companies"
        }
        mock_settings.uncle_stock.data_exports_dir = "data/files_exports"

        provider = UncleStockProvider()

        # Test configuration access
        screeners = provider.get_screener_configurations()
        assert len(screeners) == 3, f"Expected 3 screeners, got {len(screeners)}"
        assert "quality_bloom" in screeners, "Missing quality_bloom screener"
        print(f"  + Configured screeners: {list(screeners.keys())}")

        print("Uncle Stock Provider Structure: PASSED\n")


async def test_screener_service_structure():
    """Test screener service structure"""
    print("Testing Screener Service Structure...")

    # Mock dependencies
    with patch('app.services.implementations.screener_service.UncleStockProvider') as MockProvider:
        mock_provider = Mock()
        mock_provider.get_screener_configurations.return_value = {
            "quality_bloom": "quality bloom",
            "TOR_Surplus": "TOR Surplus"
        }
        MockProvider.return_value = mock_provider

        service = ScreenerService()

        # Test available screeners
        screeners = service.get_available_screeners()
        assert len(screeners) == 2, f"Expected 2 screeners, got {len(screeners)}"
        print(f"  + Available screeners: {list(screeners.keys())}")

        print("Screener Service Structure: PASSED\n")


def test_import_structure():
    """Test that all imports work correctly"""
    print("Testing Import Structure...")

    # Test interface imports
    from app.services.interfaces import IDataProvider, IFileManager, IScreenerService
    print("  + Interface imports successful")

    # Test implementation imports
    from app.services.implementations import FileManager, UncleStockProvider, ScreenerService
    print("  + Implementation imports successful")

    # Test API imports
    from app.main import app
    print("  + FastAPI app import successful")

    # Test endpoint imports
    from app.api.v1.endpoints.screeners import router
    print("  + Screener endpoints import successful")

    print("Import Structure: PASSED\n")


def test_pydantic_models():
    """Test Pydantic model structure"""
    print("Testing Pydantic Models...")

    from app.models.schemas import (
        ScreenerDataResponse, ScreenerHistoryResponse,
        AllScreenersResponse, LegacyScreenerResponse
    )

    # Test legacy response model (critical for compatibility)
    legacy_response = LegacyScreenerResponse(
        success=True,
        data=["AAPL", "GOOGL", "MSFT"],
        raw_response="test,data",
        csv_file="test.csv"
    )

    # Verify structure matches legacy exactly
    response_dict = legacy_response.dict()
    required_keys = {"success", "data", "raw_response", "csv_file"}
    assert all(key in response_dict for key in required_keys), "Missing required keys"
    print("  + Legacy response structure valid")

    # Test enhanced response model
    enhanced_response = ScreenerDataResponse(
        success=True,
        data=["AAPL", "GOOGL"],
        raw_response="test,data",
        csv_file="test.csv",
        screener_name="Test Screener"
    )

    assert enhanced_response.symbol_count == 2, "Symbol count auto-calculation failed"
    print("  + Enhanced response structure valid")

    print("Pydantic Models: PASSED\n")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("STEP 1 BASIC FUNCTIONALITY TEST")
    print("=" * 60)
    print("Testing implementation structure and core functionality")
    print()

    try:
        # Run all tests
        test_import_structure()
        test_file_manager()
        await test_uncle_stock_provider_structure()
        await test_screener_service_structure()
        test_pydantic_models()

        print("=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        print("+ Import structure working correctly")
        print("+ File manager legacy compatibility verified")
        print("+ Service structure properly implemented")
        print("+ Pydantic models working correctly")
        print()
        print("Implementation is ready for integration testing with live API")

        return True

    except Exception as e:
        print("=" * 60)
        print("TEST FAILED!")
        print("=" * 60)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)