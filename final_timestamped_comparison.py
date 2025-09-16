#!/usr/bin/env python3
"""
Final comprehensive comparison of timestamped implementations
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime

def generate_final_comparison_report():
    """Generate detailed comparison report with timestamps"""

    print("FINAL IBKR SEARCH IMPLEMENTATION COMPARISON")
    print("=" * 60)
    print("Comparing Legacy vs API with Precise Timestamps")
    print("-" * 60)

    # Load both files
    legacy_file = Path("data/universe_with_ibkr.json")
    backend_file = Path("backend/data/universe_with_ibkr.json")

    if not legacy_file.exists() or not backend_file.exists():
        print("ERROR: Required files not found")
        return

    with open(legacy_file, 'r', encoding='utf-8') as f:
        legacy_data = json.load(f)

    with open(backend_file, 'r', encoding='utf-8') as f:
        backend_data = json.load(f)

    # Extract metadata
    legacy_meta = legacy_data.get('ibkr_search_metadata', {})
    backend_meta = backend_data.get('ibkr_search_metadata', {})

    print("\n1. EXECUTION TIMESTAMPS")
    print("-" * 30)
    print(f"Legacy Implementation:")
    print(f"  Timestamp: {legacy_meta.get('timestamp', 'N/A')}")
    print(f"  Implementation: {legacy_meta.get('implementation', 'N/A')}")

    print(f"\nAPI Implementation:")
    print(f"  Timestamp: {backend_meta.get('timestamp', 'N/A')}")
    print(f"  Implementation: {backend_meta.get('implementation', 'N/A')}")

    # Calculate time difference
    try:
        legacy_time = datetime.fromisoformat(legacy_meta['timestamp'])
        backend_time = datetime.fromisoformat(backend_meta['timestamp'])
        time_diff = abs((backend_time - legacy_time).total_seconds())
        print(f"\nTime Difference: {time_diff:.1f} seconds")
    except:
        print("\nTime Difference: Could not calculate")

    print("\n2. CONFIGURATION COMPARISON")
    print("-" * 30)
    print(f"Timeout Configuration:")
    print(f"  Legacy: {legacy_meta.get('timeout_seconds', 'N/A')} seconds")
    print(f"  API: {backend_meta.get('timeout_seconds', 'N/A')} seconds")
    print(f"  Match: {legacy_meta.get('timeout_seconds') == backend_meta.get('timeout_seconds')}")

    print(f"\nExecution Times (simulated):")
    print(f"  Legacy: {legacy_meta.get('execution_time_seconds', 'N/A')} seconds")
    print(f"  API: {backend_meta.get('execution_time_seconds', 'N/A')} seconds")

    print("\n3. DATA INTEGRITY CHECK")
    print("-" * 30)

    # Remove metadata for comparison
    legacy_without_meta = {k: v for k, v in legacy_data.items() if k != 'ibkr_search_metadata'}
    backend_without_meta = {k: v for k, v in backend_data.items() if k != 'ibkr_search_metadata'}

    # Calculate hashes of core data (without metadata)
    legacy_core_str = json.dumps(legacy_without_meta, sort_keys=True)
    backend_core_str = json.dumps(backend_without_meta, sort_keys=True)

    legacy_core_hash = hashlib.md5(legacy_core_str.encode()).hexdigest()
    backend_core_hash = hashlib.md5(backend_core_str.encode()).hexdigest()

    print(f"Core Data MD5 Hashes (excluding metadata):")
    print(f"  Legacy: {legacy_core_hash}")
    print(f"  API: {backend_core_hash}")
    print(f"  Core data identical: {legacy_core_hash == backend_core_hash}")

    print(f"\nFile Sizes:")
    print(f"  Legacy file: {legacy_file.stat().st_size:,} bytes")
    print(f"  API file: {backend_file.stat().st_size:,} bytes")
    print(f"  Size difference: {abs(legacy_file.stat().st_size - backend_file.stat().st_size)} bytes")

    print("\n4. IBKR SEARCH RESULTS ANALYSIS")
    print("-" * 30)

    # Count IBKR results
    def count_ibkr_results(data):
        stats = {'total': 0, 'found': 0, 'not_found': 0, 'methods': {}}
        for screen_name, screen_data in data.get('screens', {}).items():
            for stock in screen_data.get('stocks', []):
                if stock.get('quantity', 0) > 0:
                    stats['total'] += 1
                    ibkr_details = stock.get('ibkr_details', {})
                    if ibkr_details.get('found'):
                        stats['found'] += 1
                        method = ibkr_details.get('search_method', 'unknown')
                        stats['methods'][method] = stats['methods'].get(method, 0) + 1
                    else:
                        stats['not_found'] += 1
        return stats

    legacy_stats = count_ibkr_results(legacy_data)
    backend_stats = count_ibkr_results(backend_data)

    print(f"Legacy Results:")
    print(f"  Total processed: {legacy_stats['total']}")
    print(f"  Found: {legacy_stats['found']}")
    print(f"  Not found: {legacy_stats['not_found']}")
    print(f"  Methods: {legacy_stats['methods']}")

    print(f"\nAPI Results:")
    print(f"  Total processed: {backend_stats['total']}")
    print(f"  Found: {backend_stats['found']}")
    print(f"  Not found: {backend_stats['not_found']}")
    print(f"  Methods: {backend_stats['methods']}")

    print(f"\nResults Match: {legacy_stats == backend_stats}")

    print("\n5. OUTPUT DIRECTORY VERIFICATION")
    print("-" * 30)
    print(f"Legacy output: {legacy_file}")
    print(f"API output: {backend_file}")
    print(f"Both files exist: {legacy_file.exists() and backend_file.exists()}")

    print("\n6. MIGRATION SUCCESS VERIFICATION")
    print("-" * 30)

    success_criteria = [
        ("Timestamps present", bool(legacy_meta.get('timestamp')) and bool(backend_meta.get('timestamp'))),
        ("Timeout configs match", legacy_meta.get('timeout_seconds') == backend_meta.get('timeout_seconds') == 20),
        ("Core data identical", legacy_core_hash == backend_core_hash),
        ("Search results match", legacy_stats == backend_stats),
        ("Both implementations identified", legacy_meta.get('implementation') == 'legacy' and backend_meta.get('implementation') == 'api'),
        ("Files generated", legacy_file.exists() and backend_file.exists())
    ]

    all_passed = True
    for criterion, passed in success_criteria:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {criterion}")
        if not passed:
            all_passed = False

    print(f"\n7. FINAL VERDICT")
    print("=" * 30)
    if all_passed:
        print("MIGRATION SUCCESSFUL")
        print("Both implementations produce identical results with proper timestamps")
        print("20-second timeouts confirmed in both versions")
        print("Ready for production deployment")
    else:
        print("ISSUES DETECTED - Review required")

    return all_passed, legacy_meta, backend_meta

if __name__ == "__main__":
    success, legacy_meta, backend_meta = generate_final_comparison_report()

    print(f"\nSUMMARY:")
    print(f"Legacy run: {legacy_meta.get('timestamp', 'N/A')}")
    print(f"API run: {backend_meta.get('timestamp', 'N/A')}")
    print(f"Both using 20s timeouts: {legacy_meta.get('timeout_seconds') == backend_meta.get('timeout_seconds') == 20}")
    print(f"Migration status: {'SUCCESS' if success else 'NEEDS REVIEW'}")