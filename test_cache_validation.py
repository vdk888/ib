#!/usr/bin/env python3
"""
Test cache validation logic directly
"""

import sqlite3
import json
import sys
from pathlib import Path

# Add backend path for database service import
sys.path.append(str(Path(__file__).parent / 'backend'))

# Import just the database service directly
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

@dataclass
class IBKRCacheEntry:
    """Represents a cached IBKR search result"""
    isin: str
    ticker: str
    name: str
    currency: str
    found: bool
    ibkr_symbol: Optional[str]
    ibkr_contract_id: Optional[int]
    search_method: Optional[str]
    search_date: datetime
    raw_ibkr_details: Dict[str, Any]

def get_cached_result(db_path: str, isin: str, ticker: str, max_age_days: int = 365) -> Optional[IBKRCacheEntry]:
    """Get cached IBKR search result if exists and not expired"""
    try:
        cutoff_date = datetime.now() - timedelta(days=max_age_days)

        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM ibkr_search_cache
                WHERE isin = ? AND ticker = ? AND search_date > ?
                ORDER BY search_date DESC
                LIMIT 1
            """, (isin, ticker, cutoff_date.isoformat()))

            row = cursor.fetchone()
            if row:
                return IBKRCacheEntry(
                    isin=row['isin'],
                    ticker=row['ticker'],
                    name=row['name'],
                    currency=row['currency'],
                    found=bool(row['found']),
                    ibkr_symbol=row['ibkr_symbol'],
                    ibkr_contract_id=row['ibkr_contract_id'],
                    search_method=row['search_method'],
                    search_date=datetime.fromisoformat(row['search_date']),
                    raw_ibkr_details=json.loads(row['raw_ibkr_details']) if row['raw_ibkr_details'] else {}
                )
    except Exception as e:
        print(f"Error getting cached result: {e}")

    return None

def test_cache_validation():
    """Test cache validation for problematic stocks"""

    # Test with the 3 problem stocks
    problem_stocks = [
        {'ticker': 'CMB.MI', 'isin': 'IT0001128047', 'name': 'Cembre S.p.A.', 'currency': 'EUR'},
        {'ticker': '6061.T', 'isin': 'JP3952300006', 'name': 'Universal Engeisha Co Ltd', 'currency': 'JPY'},
        {'ticker': 'EVPL.L', 'isin': 'GB00BZCZ8L01', 'name': 'Everplay Group PLC', 'currency': 'GBP'}
    ]

    db_path = 'backend/data/ibkr_cache.db'

    print("Testing Cache Validation Logic")
    print("=" * 40)

    for stock in problem_stocks:
        ticker = stock['ticker']
        isin = stock['isin']

        print(f"\nTesting {ticker}:")

        # Get cached entry
        cached_entry = get_cached_result(db_path, isin, ticker)

        if cached_entry:
            print(f"  Found in cache: found={cached_entry.found}")

            # Apply same validation logic as our modified code
            import copy
            raw_details = copy.deepcopy(cached_entry.raw_ibkr_details)
            raw_details['found'] = cached_entry.found

            # Normalize conId field
            if 'contract_id' in raw_details and 'conId' not in raw_details:
                raw_details['conId'] = raw_details['contract_id']

            # Check if entry is actually usable (has valid conId for found entries)
            is_valid_cache = True
            if cached_entry.found:
                # For found entries, must have valid conId
                con_id = raw_details.get('conId', 0)
                if not con_id or con_id == 0:
                    is_valid_cache = False
                    print(f"  ❌ Cache entry marked as found but has no valid conId ({con_id}) - should force IBKR API search")
                else:
                    print(f"  ✅ Valid cache entry with conId={con_id}")
            else:
                print(f"  ✅ Cache entry correctly marked as not found")

            if is_valid_cache:
                print(f"  Result: CACHED (will use cached data)")
            else:
                print(f"  Result: UNCACHED (will force IBKR API search)")
        else:
            print(f"  No cache entry found")

if __name__ == "__main__":
    test_cache_validation()