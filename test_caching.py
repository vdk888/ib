#!/usr/bin/env python3
"""
Test caching functionality
"""

import sys
from pathlib import Path

# Add backend path for database service import
sys.path.append(str(Path(__file__).parent / 'backend' / 'app'))
sys.path.append(str(Path(__file__).parent / 'backend'))

# Direct import to avoid dependency issues
from backend.app.services.database_service import get_database_service

def test_database_separation():
    """Test that legacy and API use separate databases"""

    print("Testing database separation...")

    # Test legacy database (data/ibkr_cache.db)
    legacy_db_path = "data/ibkr_cache.db"
    legacy_db = get_database_service(legacy_db_path)

    print(f"Legacy database path: {legacy_db_path}")
    print(f"Legacy database instance: {id(legacy_db)}")

    # Test API database (backend/data/ibkr_cache.db)
    api_db_path = "backend/data/ibkr_cache.db"
    api_db = get_database_service(api_db_path)

    print(f"API database path: {api_db_path}")
    print(f"API database instance: {id(api_db)}")

    # Verify they are different instances
    print(f"Databases are separate: {legacy_db is not api_db}")

    # Test cache stats
    legacy_stats = legacy_db.get_cache_stats()
    api_stats = api_db.get_cache_stats()

    print(f"\nLegacy cache stats: {legacy_stats}")
    print(f"API cache stats: {api_stats}")

    # Test storing a sample entry in each
    print("\nTesting cache storage...")

    # Store in legacy cache
    legacy_success = legacy_db.store_result(
        isin="TEST001",
        ticker="TEST",
        name="Test Stock Legacy",
        currency="USD",
        found=True,
        ibkr_details={'symbol': 'TEST', 'found': True}
    )

    # Store in API cache
    api_success = api_db.store_result(
        isin="TEST002",
        ticker="TEST2",
        name="Test Stock API",
        currency="USD",
        found=True,
        ibkr_details={'symbol': 'TEST2', 'found': True}
    )

    print(f"Legacy storage success: {legacy_success}")
    print(f"API storage success: {api_success}")

    # Check updated stats
    legacy_stats_after = legacy_db.get_cache_stats()
    api_stats_after = api_db.get_cache_stats()

    print(f"\nLegacy cache stats after: {legacy_stats_after}")
    print(f"API cache stats after: {api_stats_after}")

    # Check if we can retrieve the entries
    legacy_entry = legacy_db.get_cached_result("TEST001", "TEST")
    api_entry = api_db.get_cached_result("TEST002", "TEST2")

    print(f"\nLegacy entry retrieved: {legacy_entry is not None}")
    print(f"API entry retrieved: {api_entry is not None}")

    # Cross-check (should be None)
    legacy_check_api = legacy_db.get_cached_result("TEST002", "TEST2")
    api_check_legacy = api_db.get_cached_result("TEST001", "TEST")

    print(f"Legacy DB cannot see API entry: {legacy_check_api is None}")
    print(f"API DB cannot see legacy entry: {api_check_legacy is None}")

if __name__ == "__main__":
    test_database_separation()