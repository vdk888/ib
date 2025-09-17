"""
SQLite database service for IBKR search result caching
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

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

class IBKRDatabaseService:
    """Service for managing IBKR search result cache in SQLite"""

    def __init__(self, db_path: str = "data/ibkr_cache.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    def _initialize_database(self):
        """Initialize database with required schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ibkr_search_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        isin TEXT NOT NULL,
                        ticker TEXT NOT NULL,
                        name TEXT NOT NULL,
                        currency TEXT,
                        found BOOLEAN NOT NULL,
                        ibkr_symbol TEXT,
                        ibkr_contract_id INTEGER,
                        search_method TEXT,
                        search_date TIMESTAMP NOT NULL,
                        raw_ibkr_details TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(isin, ticker)
                    )
                """)

                # Create index for fast lookups
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_isin_ticker
                    ON ibkr_search_cache(isin, ticker)
                """)

                # Create index for date-based queries
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_search_date
                    ON ibkr_search_cache(search_date)
                """)

                conn.commit()
                logger.info(f"Database initialized at {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def get_cached_result(self, isin: str, ticker: str, max_age_days: int = 365) -> Optional[IBKRCacheEntry]:
        """
        Get cached IBKR search result if exists and not expired

        Args:
            isin: Stock ISIN
            ticker: Stock ticker
            max_age_days: Maximum age in days before cache expires (default: 365)

        Returns:
            IBKRCacheEntry if found and valid, None otherwise
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)

            with sqlite3.connect(self.db_path) as conn:
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
            logger.error(f"Failed to get cached result for {isin}/{ticker}: {e}")

        return None

    def store_result(self,
                    isin: str,
                    ticker: str,
                    name: str,
                    currency: str,
                    found: bool,
                    ibkr_details: Dict[str, Any]) -> bool:
        """
        Store IBKR search result in cache

        Args:
            isin: Stock ISIN
            ticker: Stock ticker
            name: Stock name
            currency: Stock currency
            found: Whether IBKR details were found
            ibkr_details: Complete IBKR details dictionary

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            search_date = datetime.now()

            # Extract specific fields from ibkr_details
            ibkr_symbol = ibkr_details.get('symbol') if found else None
            ibkr_contract_id = ibkr_details.get('contract_id') if found else None
            search_method = ibkr_details.get('search_method') if found else None

            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO ibkr_search_cache
                    (isin, ticker, name, currency, found, ibkr_symbol, ibkr_contract_id,
                     search_method, search_date, raw_ibkr_details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    isin, ticker, name, currency, found,
                    ibkr_symbol, ibkr_contract_id, search_method,
                    search_date.isoformat(),
                    json.dumps(ibkr_details)
                ))
                conn.commit()

                logger.debug(f"Stored cache entry for {isin}/{ticker}, found: {found}")
                return True

        except Exception as e:
            logger.error(f"Failed to store result for {isin}/{ticker}: {e}")
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) as total FROM ibkr_search_cache")
                total = cursor.fetchone()[0]

                cursor = conn.execute("SELECT COUNT(*) as found FROM ibkr_search_cache WHERE found = 1")
                found = cursor.fetchone()[0]

                cursor = conn.execute("""
                    SELECT COUNT(*) as recent
                    FROM ibkr_search_cache
                    WHERE search_date > ?
                """, ((datetime.now() - timedelta(days=30)).isoformat(),))
                recent = cursor.fetchone()[0]

                return {
                    'total_entries': total,
                    'found_entries': found,
                    'not_found_entries': total - found,
                    'recent_entries_30d': recent,
                    'hit_rate': (found / total * 100) if total > 0 else 0
                }

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}

    def cleanup_expired_entries(self, max_age_days: int = 365) -> int:
        """
        Remove expired cache entries

        Args:
            max_age_days: Maximum age in days before entries are considered expired

        Returns:
            Number of entries removed
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=max_age_days)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM ibkr_search_cache
                    WHERE search_date < ?
                """, (cutoff_date.isoformat(),))

                removed_count = cursor.rowcount
                conn.commit()

                logger.info(f"Cleaned up {removed_count} expired cache entries")
                return removed_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired entries: {e}")
            return 0

    def get_cached_stocks(self, stocks: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Separate stocks into cached and uncached lists

        Args:
            stocks: List of stock dictionaries with 'isin', 'ticker', etc.

        Returns:
            Tuple of (cached_stocks, uncached_stocks) where cached_stocks have ibkr_details populated
        """
        cached_stocks = []
        uncached_stocks = []

        try:
            for stock in stocks:
                isin = stock.get('isin', '')
                ticker = stock.get('ticker', '')

                if not isin or not ticker:
                    uncached_stocks.append(stock)
                    continue

                cached_entry = self.get_cached_result(isin, ticker)

                if cached_entry:
                    # Create stock copy with cached IBKR details
                    cached_stock = stock.copy()
                    cached_stock['ibkr_details'] = cached_entry.raw_ibkr_details
                    cached_stocks.append(cached_stock)
                    logger.debug(f"Cache hit for {isin}/{ticker}")
                else:
                    uncached_stocks.append(stock)
                    logger.debug(f"Cache miss for {isin}/{ticker}")

        except Exception as e:
            logger.error(f"Failed to check cache for stocks: {e}")
            # On error, treat all as uncached
            return [], stocks

        logger.info(f"Cache stats: {len(cached_stocks)} hits, {len(uncached_stocks)} misses")
        return cached_stocks, uncached_stocks

# Singleton instance
_db_service_instance = None

def get_database_service() -> IBKRDatabaseService:
    """Get singleton database service instance"""
    global _db_service_instance
    if _db_service_instance is None:
        _db_service_instance = IBKRDatabaseService()
    return _db_service_instance