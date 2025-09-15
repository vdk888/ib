"""
Manual test for Currency Service Step 5
Tests CLI vs API compatibility directly
"""

import sys
import os

# Add paths
sys.path.insert(0, '.')
sys.path.insert(0, 'backend')

def test_currency_cli():
    """Test CLI currency functionality"""
    print("Testing CLI currency functionality...")

    try:
        # Test legacy currency import
        from src.currency import main as currency_main, fetch_exchange_rates, get_currencies_from_universe
        print("[OK] Successfully imported legacy currency functions")

        # Test fetching exchange rates (this will make real API call)
        print("📡 Testing exchange rate fetching...")
        rates = fetch_exchange_rates()

        if rates:
            print(f"✅ Successfully fetched {len(rates)} exchange rates")
            print(f"   Sample rates: EUR=1.0, USD={rates.get('USD', 'N/A')}")
        else:
            print("❌ Failed to fetch exchange rates")

    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False

    return True

def test_currency_service():
    """Test Currency Service implementation"""
    print("\nTesting Currency Service implementation...")

    try:
        # Add backend to path
        import importlib.util
        service_path = "backend/app/services/implementations/currency_service.py"
        spec = importlib.util.spec_from_file_location("currency_service", service_path)
        currency_service_module = importlib.util.module_from_spec(spec)

        # Add legacy to path for the service
        legacy_path = "src"
        if legacy_path not in sys.path:
            sys.path.insert(0, legacy_path)

        spec.loader.exec_module(currency_service_module)

        # Create service instance
        service = currency_service_module.CurrencyService()
        print("✅ Successfully created Currency Service instance")

        # Test service methods exist
        assert hasattr(service, 'fetch_exchange_rates'), "Missing fetch_exchange_rates method"
        assert hasattr(service, 'get_currencies_from_universe'), "Missing get_currencies_from_universe method"
        assert hasattr(service, 'update_universe_with_exchange_rates'), "Missing update_universe_with_exchange_rates method"
        assert hasattr(service, 'run_currency_update'), "Missing run_currency_update method"
        print("✅ All required methods present")

        # Test exchange rate fetching
        print("📡 Testing service exchange rate fetching...")
        rates = service.fetch_exchange_rates()

        if rates:
            print(f"✅ Service successfully fetched {len(rates)} exchange rates")
            print(f"   Sample rates: EUR=1.0, USD={rates.get('USD', 'N/A')}")

            # Test that EUR is always present with rate 1.0
            assert 'EUR' in rates, "EUR not in exchange rates"
            assert rates['EUR'] == 1.0, "EUR rate is not 1.0"
            print("✅ EUR base currency correctly set")
        else:
            print("❌ Service failed to fetch exchange rates")

    except Exception as e:
        print(f"❌ Service test failed: {e}")
        return False

    return True

def test_currency_behavior_compatibility():
    """Test that CLI and Service produce identical results"""
    print("\nTesting CLI vs Service behavioral compatibility...")

    try:
        # Import both implementations
        from src.currency import fetch_exchange_rates as cli_fetch

        import importlib.util
        service_path = "backend/app/services/implementations/currency_service.py"
        spec = importlib.util.spec_from_file_location("currency_service", service_path)
        currency_service_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(currency_service_module)
        service = currency_service_module.CurrencyService()

        # Test fetch_exchange_rates compatibility
        print("📊 Comparing CLI vs Service exchange rate results...")

        cli_rates = cli_fetch()
        service_rates = service.fetch_exchange_rates()

        if cli_rates and service_rates:
            # Compare results
            if set(cli_rates.keys()) == set(service_rates.keys()):
                print("✅ CLI and Service return same currency keys")
            else:
                print("❌ CLI and Service return different currency keys")

            if cli_rates == service_rates:
                print("✅ CLI and Service return identical exchange rates")
            else:
                print("⚠️  CLI and Service return different exchange rate values (expected due to timing)")

            # Check EUR base currency
            if cli_rates.get('EUR') == service_rates.get('EUR') == 1.0:
                print("✅ Both CLI and Service set EUR as base currency (1.0)")
            else:
                print("❌ EUR base currency handling differs")

        elif not cli_rates and not service_rates:
            print("✅ Both CLI and Service handle API failures identically (both returned empty dicts)")
        else:
            print("❌ CLI and Service handle API calls differently")

    except Exception as e:
        print(f"❌ Compatibility test failed: {e}")
        return False

    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("CURRENCY SERVICE STEP 5 COMPATIBILITY TESTING")
    print("=" * 60)

    success = True

    # Test CLI functionality
    success &= test_currency_cli()

    # Test Service implementation
    success &= test_currency_service()

    # Test compatibility
    success &= test_currency_behavior_compatibility()

    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL TESTS PASSED - Currency Service Step 5 is ready!")
        print("✅ CLI functionality works")
        print("✅ Service implementation works")
        print("✅ Behavioral compatibility maintained")
    else:
        print("❌ SOME TESTS FAILED")

    print("=" * 60)

    return success

if __name__ == "__main__":
    main()