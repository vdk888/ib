"""
Optimized IBKR Search Service Implementation
High-performance concurrent stock search with intelligent caching

Performance Optimizations:
- Concurrent processing with multiple IBKR client connections
- Smart caching to avoid repeated searches
- Progressive fallback strategy (ISIN → Ticker → Name)
- Batch grouping by currency/exchange
- Real-time progress tracking
"""

import asyncio
import json
import time
import os
import threading
from typing import Dict, Any, List, Optional, Tuple, Callable
from pathlib import Path
from datetime import datetime
import re
from difflib import SequenceMatcher
import unicodedata
import logging

# Import IBKR API components
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

# Import the interface
from ..ibkr_interface import IIBKRSearchService

# Set up logging
logger = logging.getLogger(__name__)


class OptimizedIBApi(EWrapper, EClient):
    """
    Optimized IBKR API client with async support and better error handling
    """

    def __init__(self, client_id: int):
        EClient.__init__(self, self)
        self.client_id = client_id
        self.connected = False
        self.contract_details = []
        self.matching_symbols = []
        self.next_req_id = 1
        self.search_completed = False
        self.symbol_search_completed = False
        self.connection_event = threading.Event()
        self.search_event = threading.Event()
        self.symbol_event = threading.Event()
        self._lock = threading.Lock()

    def connectAck(self):
        super().connectAck()
        self.connected = True
        self.connection_event.set()

    def connectionClosed(self):
        super().connectionClosed()
        self.connected = False
        self.connection_event.clear()

    def contractDetails(self, reqId, contractDetails):
        super().contractDetails(reqId, contractDetails)
        with self._lock:
            contract = contractDetails.contract
            details = {
                "symbol": contract.symbol,
                "longName": contractDetails.longName,
                "currency": contract.currency,
                "exchange": contract.exchange,
                "primaryExchange": contract.primaryExchange if contract.primaryExchange else "",
                "conId": contract.conId,
                "contract": contract
            }
            self.contract_details.append(details)

    def contractDetailsEnd(self, reqId):
        super().contractDetailsEnd(reqId)
        with self._lock:
            self.search_completed = True
        self.search_event.set()

    def symbolSamples(self, reqId, contractDescriptions):
        super().symbolSamples(reqId, contractDescriptions)
        with self._lock:
            self.matching_symbols = []
            for desc in contractDescriptions:
                contract = desc.contract
                details = {
                    "symbol": contract.symbol,
                    "secType": contract.secType,
                    "currency": contract.currency,
                    "exchange": contract.exchange,
                    "description": desc.derivativeSecTypes if hasattr(desc, 'derivativeSecTypes') else ''
                }
                if contract.secType == "STK":  # Only stocks
                    self.matching_symbols.append(details)

    def symbolSamplesEnd(self, reqId):
        super().symbolSamplesEnd(reqId)
        with self._lock:
            self.symbol_search_completed = True
        self.symbol_event.set()

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        if errorCode in [200, 162]:  # No security definition found
            with self._lock:
                self.search_completed = True
                self.symbol_search_completed = True
            self.search_event.set()
            self.symbol_event.set()
        logger.debug(f"IBKR Error {errorCode}: {errorString}")

    async def async_wait_for_connection(self, timeout: float = 10.0) -> bool:
        """Wait for connection with asyncio support"""
        def wait_for_event():
            return self.connection_event.wait(timeout)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, wait_for_event)

    async def async_wait_for_search(self, timeout: float = 5.0) -> bool:
        """Wait for search completion with asyncio support using polling like original"""
        start_time = time.time()
        while not self.search_completed and (time.time() - start_time) < timeout:
            await asyncio.sleep(0.05)  # Async equivalent of time.sleep(0.05)
        return self.search_completed

    async def async_wait_for_symbol_search(self, timeout: float = 5.0) -> bool:
        """Wait for symbol search completion with asyncio support using polling like original"""
        start_time = time.time()
        while not self.symbol_search_completed and (time.time() - start_time) < timeout:
            await asyncio.sleep(0.05)  # Async equivalent of time.sleep(0.05)
        return self.symbol_search_completed


class IBKRSearchService(IIBKRSearchService):
    """
    Optimized IBKR Search Service with concurrent processing and caching
    """

    def __init__(self,
                 max_connections: int = 5,
                 cache_enabled: bool = True,
                 ibkr_host: str = "127.0.0.1",
                 ibkr_port: int = 4002):
        self.max_connections = max_connections
        self.cache_enabled = cache_enabled
        self.ibkr_host = ibkr_host
        self.ibkr_port = ibkr_port

        # Connection pool
        self.connection_pool = []
        self.available_connections = asyncio.Queue()
        self.connection_lock = asyncio.Lock()

        # Cache
        self.cache: Dict[str, Tuple[Optional[Dict[str, Any]], float]] = {}
        self.cache_stats = {"hits": 0, "misses": 0}

        # Progress tracking
        self.current_progress = {"current": 0, "total": 0, "current_stock": ""}

    async def _initialize_connection_pool(self):
        """Initialize pool of IBKR connections"""
        if self.connection_pool:
            return  # Already initialized

        logger.info(f"Initializing {self.max_connections} IBKR connections...")

        for i in range(self.max_connections):
            client_id = 100 + i  # Use different client IDs
            app = OptimizedIBApi(client_id)

            # Start API thread
            api_thread = threading.Thread(target=app.run, daemon=True)
            api_thread.start()

            # Connect
            app.connect(self.ibkr_host, self.ibkr_port, client_id)

            # Wait for connection
            if await app.async_wait_for_connection():
                self.connection_pool.append(app)
                await self.available_connections.put(app)
                logger.debug(f"Connection {client_id} established")
            else:
                logger.warning(f"Failed to establish connection {client_id}")

        logger.info(f"Connection pool initialized with {len(self.connection_pool)} connections")

    async def _get_connection(self) -> OptimizedIBApi:
        """Get an available connection from the pool"""
        if not self.connection_pool:
            await self._initialize_connection_pool()

        return await self.available_connections.get()

    async def _return_connection(self, app: OptimizedIBApi):
        """Return a connection to the pool"""
        await self.available_connections.put(app)

    def _get_cache_key(self, stock: Dict[str, Any]) -> str:
        """Generate cache key for stock"""
        ticker = stock.get('ticker', '')
        isin = stock.get('isin', '')
        currency = stock.get('currency', '')
        return f"{ticker}:{isin}:{currency}"

    def _get_from_cache(self, stock: Dict[str, Any]) -> Optional[Tuple[Optional[Dict[str, Any]], float]]:
        """Get result from cache if available"""
        if not self.cache_enabled:
            return None

        cache_key = self._get_cache_key(stock)
        if cache_key in self.cache:
            self.cache_stats["hits"] += 1
            return self.cache[cache_key]

        self.cache_stats["misses"] += 1
        return None

    def _save_to_cache(self, stock: Dict[str, Any], result: Tuple[Optional[Dict[str, Any]], float]):
        """Save result to cache"""
        if not self.cache_enabled:
            return

        cache_key = self._get_cache_key(stock)
        self.cache[cache_key] = result

    def extract_unique_stocks(self, universe_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract unique stocks from universe data using ticker as key"""
        unique_stocks = {}

        # Process all screens
        for screen_name, screen_data in universe_data.get('screens', {}).items():
            for stock in screen_data.get('stocks', []):
                # Use ticker as unique key
                ticker = stock.get('ticker')
                if ticker and ticker not in unique_stocks:
                    unique_stocks[ticker] = {
                        'ticker': ticker,
                        'isin': stock.get('isin'),
                        'name': stock.get('name'),
                        'currency': stock.get('currency'),
                        'sector': stock.get('sector'),
                        'country': stock.get('country')
                    }

        return list(unique_stocks.values())

    def _get_ticker_variations(self, ticker: str) -> List[str]:
        """Generate comprehensive ticker variations"""
        variations = [ticker]

        # Remove exchange suffix
        base_ticker = re.sub(r'\\.[A-Z]+$', '', ticker)
        if base_ticker != ticker:
            variations.append(base_ticker)

        # Japanese stocks (.T suffix)
        if '.T' in ticker:
            base = ticker.replace('.T', '')
            variations.append(base)
            if base.isdigit():
                variations.append(str(int(base)))

        # Share class variations
        if '-A' in ticker:
            no_dash = ticker.replace('-A', 'A')
            variations.extend([no_dash, re.sub(r'\\.[A-Z]+$', '', no_dash)])
            dot_class = ticker.replace('-A', '.A')
            variations.extend([dot_class, re.sub(r'\\.[A-Z]+$', '', dot_class)])

        if '-B' in ticker:
            dot_class = ticker.replace('-B', '.B')
            variations.extend([dot_class, re.sub(r'\\.[A-Z]+$', '', dot_class)])
            no_dash = ticker.replace('-B', 'B')
            variations.extend([no_dash, re.sub(r'\\.[A-Z]+$', '', no_dash)])

        # Exchange-specific variations
        exchange_suffixes = ['.AT', '.L', '.HE', '.PA']
        for suffix in exchange_suffixes:
            if suffix in ticker:
                base = ticker.replace(suffix, '')
                variations.append(base)
                if suffix == '.AT' and len(base) <= 6:
                    variations.append(base + 'A')

        # Remove duplicates while preserving order
        seen = set()
        return [x for x in variations if not (x in seen or seen.add(x))]

    def _similarity_score(self, str1: str, str2: str) -> float:
        """Calculate similarity score between two strings"""
        if not str1 or not str2:
            return 0.0
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    def validate_stock_match(
        self,
        universe_stock: Dict[str, Any],
        ibkr_contract: Dict[str, Any],
        search_method: str
    ) -> Tuple[bool, str]:
        """Validate if IBKR contract matches universe stock"""
        universe_name = universe_stock['name'].lower()
        ibkr_name = ibkr_contract['longName'].lower()

        # Must have currency match
        if ibkr_contract['currency'] != universe_stock['currency']:
            return False, "Currency mismatch"

        # Clean and normalize names
        universe_clean = re.sub(r"[''`\-\.\,\(\)\[\]]", "", universe_name)
        ibkr_clean = re.sub(r"[''`\-\.\,\(\)\[\]]", "", ibkr_name)

        # Normalize to ASCII
        universe_clean = unicodedata.normalize('NFD', universe_clean).encode('ascii', 'ignore').decode('ascii')
        ibkr_clean = unicodedata.normalize('NFD', ibkr_clean).encode('ascii', 'ignore').decode('ascii')

        universe_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', universe_clean))
        ibkr_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', ibkr_clean))

        # Remove common corporate suffixes
        ignore_words = {
            'ltd', 'plc', 'inc', 'corp', 'sa', 'ab', 'oyj', 'group', 'international',
            'company', 'limited', 'corporation', 'societe', 'anonyme', 'systems',
            'software', 'commercial', 'industrial', 'authority', 'public', 'co', 'oy'
        }

        universe_key_words = universe_words - ignore_words
        ibkr_key_words = ibkr_words - ignore_words

        word_overlap = len(universe_key_words & ibkr_key_words)
        name_similarity = self._similarity_score(universe_name, ibkr_name)

        # Different validation rules based on search method
        if search_method == "ticker":
            if name_similarity > 0.3:
                return True, f"Ticker match + similarity: {name_similarity:.2f}"
            elif word_overlap >= 1:
                return True, f"Ticker match + word overlap: {word_overlap}"
            else:
                return True, f"Ticker match (currency confirmed): {name_similarity:.2f}"

        elif search_method == "isin":
            if name_similarity > 0.6:
                return True, f"ISIN match + good similarity: {name_similarity:.2f}"
            elif word_overlap >= 2:
                return True, f"ISIN match + strong word overlap: {word_overlap}"
            elif word_overlap >= 1 and name_similarity > 0.4:
                return True, f"ISIN match + word overlap + similarity: {word_overlap}, {name_similarity:.2f}"
            else:
                return False, f"ISIN match but poor name similarity: {name_similarity:.2f}, word_overlap: {word_overlap}"

        else:  # name-based search
            if name_similarity > 0.8:
                return True, f"High similarity: {name_similarity:.2f}"
            elif word_overlap >= 2 and name_similarity > 0.6:
                return True, f"Word overlap: {word_overlap}, similarity: {name_similarity:.2f}"
            elif word_overlap >= 1 and name_similarity > 0.7:
                return True, f"Some overlap + high similarity: {word_overlap}, {name_similarity:.2f}"
            else:
                return False, f"Insufficient match: overlap={word_overlap}, similarity={name_similarity:.2f}"

    async def search_by_isin(
        self,
        isin: str,
        currency: str,
        connection_id: int = 1
    ) -> List[Dict[str, Any]]:
        """Search for stock by ISIN using specific IBKR connection"""
        app = await self._get_connection()

        try:
            contract = Contract()
            contract.secIdType = "ISIN"
            contract.secId = isin
            contract.secType = "STK"
            contract.currency = currency
            contract.exchange = "SMART"

            # Reset state before search
            with app._lock:
                app.contract_details = []
                app.search_completed = False

            app.reqContractDetails(app.next_req_id, contract)
            app.next_req_id += 1

            # Wait for result
            await app.async_wait_for_search(timeout=5.0)

            # Mark search method
            for contract_detail in app.contract_details:
                contract_detail['_search_method'] = 'isin'

            return app.contract_details.copy()

        finally:
            await self._return_connection(app)

    async def search_by_ticker_variations(
        self,
        ticker: str,
        currency: str,
        connection_id: int = 1
    ) -> List[Dict[str, Any]]:
        """Search for stock by ticker and all its variations"""
        app = await self._get_connection()

        try:
            variations = self._get_ticker_variations(ticker)
            all_results = []

            for variant in variations:
                contract = Contract()
                contract.symbol = variant
                contract.secType = "STK"
                contract.currency = currency
                contract.exchange = "SMART"

                # Reset state before search
                with app._lock:
                    app.contract_details = []
                    app.search_completed = False

                app.reqContractDetails(app.next_req_id, contract)
                app.next_req_id += 1

                # Wait for result
                await app.async_wait_for_search(timeout=3.0)

                if app.contract_details:
                    # Mark search method and return first successful match
                    for contract_detail in app.contract_details:
                        contract_detail['_search_method'] = 'ticker'
                    all_results.extend(app.contract_details.copy())
                    break  # Found match, stop searching variations

                # Small delay between variations
                await asyncio.sleep(0.1)

            return all_results

        finally:
            await self._return_connection(app)

    async def search_by_company_name(
        self,
        stock: Dict[str, Any],
        connection_id: int = 1
    ) -> List[Dict[str, Any]]:
        """Search for stock by company name parts using reqMatchingSymbols"""
        app = await self._get_connection()

        try:
            name = stock['name'].lower()
            search_terms = []

            # Extract meaningful words
            words = re.findall(r'\\b[a-zA-Z]{3,}\\b', stock['name'])

            # Add individual words
            for word in words[:3]:
                if word.lower() not in ['ltd', 'plc', 'inc', 'corp', 'sa', 'ab', 'oyj', 'group', 'international']:
                    search_terms.append(word)

            # Add combinations
            if len(words) >= 2:
                search_terms.append(f"{words[0]} {words[1]}")

            # Special cases for known mappings
            special_mappings = {
                'everplay': ['everplay', 'EVPL'],
                'sarantis': ['sarantis', 'SAR'],
                'dewhurst': ['dewhurst', 'DWHT'],
                'ilyda': ['ilyda'],
                'thessaloniki': ['thessaloniki', 'port', 'OLTH'],
                'port': ['thessaloniki', 'port', 'OLTH']
            }

            for key, terms in special_mappings.items():
                if key in name:
                    search_terms.extend(terms)

            all_matches = []

            for term in search_terms:
                if len(term) < 2:
                    continue

                try:
                    with app._lock:
                        app.matching_symbols = []
                        app.symbol_search_completed = False

                    app.reqMatchingSymbols(app.next_req_id, term)
                    app.next_req_id += 1

                    # Wait for symbol search
                    await app.async_wait_for_symbol_search(timeout=5.0)

                    # Get contract details for matches
                    for match in app.matching_symbols:
                        if match['currency'] == stock['currency']:
                            contract = Contract()
                            contract.symbol = match['symbol']
                            contract.secType = "STK"
                            contract.currency = match['currency']
                            contract.exchange = match['exchange']

                            with app._lock:
                                app.contract_details = []
                                app.search_completed = False

                            app.reqContractDetails(app.next_req_id, contract)
                            app.next_req_id += 1

                            await app.async_wait_for_search(timeout=3.0)

                            for contract_detail in app.contract_details:
                                contract_detail['_search_method'] = 'name'
                            all_matches.extend(app.contract_details.copy())

                            await asyncio.sleep(0.1)

                    await asyncio.sleep(0.2)

                except Exception as e:
                    logger.debug(f"Error in name search for term '{term}': {e}")
                    continue

            return all_matches

        finally:
            await self._return_connection(app)

    async def search_single_stock(
        self,
        stock: Dict[str, Any],
        use_cache: bool = True
    ) -> Tuple[Optional[Dict[str, Any]], float]:
        """Search for a single stock using comprehensive multi-strategy approach"""

        # Check cache first
        if use_cache:
            cached_result = self._get_from_cache(stock)
            if cached_result is not None:
                return cached_result

        all_contracts = []

        # Strategy 1: ISIN search (fastest and most reliable)
        if stock.get('isin') and stock.get('isin') not in ['null', '', None]:
            logger.debug(f"Trying ISIN search for {stock['ticker']}: {stock['isin']}")
            isin_results = await self.search_by_isin(stock['isin'], stock['currency'])
            all_contracts.extend(isin_results)

        # Strategy 2: Ticker variations (always try if we have a ticker)
        if stock.get('ticker'):
            logger.debug(f"Trying ticker search for {stock['ticker']}")
            ticker_results = await self.search_by_ticker_variations(stock['ticker'], stock['currency'])
            all_contracts.extend(ticker_results)

        # Strategy 3: Name-based search (fallback if no results yet)
        if not all_contracts:
            logger.debug(f"Trying name search for {stock['ticker']}: {stock['name']}")
            name_results = await self.search_by_company_name(stock)
            all_contracts.extend(name_results)

        # Validate and score results
        if all_contracts:
            valid_matches = []

            for contract in all_contracts:
                search_method = contract.get('_search_method', 'unknown')
                is_valid, reason = self.validate_stock_match(stock, contract, search_method)

                if is_valid:
                    name_sim = self._similarity_score(stock['name'].lower(), contract['longName'].lower())
                    logger.debug(f"Valid match for {stock['ticker']}: {contract['symbol']} -> {reason}")
                    valid_matches.append((contract, name_sim))
                else:
                    logger.debug(f"Rejected match for {stock['ticker']}: {contract['symbol']} -> {reason}")

            if valid_matches:
                # Sort by similarity and pick best
                valid_matches.sort(key=lambda x: x[1], reverse=True)
                best_match = valid_matches[0][0]
                best_score = valid_matches[0][1]

                # Keep search method info
                best_match['search_method'] = best_match.get('_search_method', 'unknown')
                best_match['match_score'] = best_score

                result = (best_match, best_score)

                # Cache the result
                if use_cache:
                    self._save_to_cache(stock, result)

                return result

        # No match found
        result = (None, 0.0)
        if use_cache:
            self._save_to_cache(stock, result)

        return result

    async def search_multiple_stocks(
        self,
        stocks: List[Dict[str, Any]],
        max_concurrent: int = 5,
        use_cache: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Tuple[Optional[Dict[str, Any]], float]]:
        """Search for multiple stocks concurrently with progress tracking"""

        if max_concurrent > self.max_connections:
            max_concurrent = self.max_connections

        # Initialize connection pool
        await self._initialize_connection_pool()

        results = {}
        semaphore = asyncio.Semaphore(max_concurrent)

        async def search_single_with_semaphore(stock: Dict[str, Any], index: int):
            async with semaphore:
                result = await self.search_single_stock(stock, use_cache)

                # Update progress
                if progress_callback:
                    progress_callback(index + 1, len(stocks), stock.get('ticker', 'Unknown'))

                return stock.get('ticker'), result

        # Create tasks for all stocks
        tasks = [
            search_single_with_semaphore(stock, i)
            for i, stock in enumerate(stocks)
        ]

        # Execute all tasks concurrently
        completed_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in completed_results:
            if isinstance(result, Exception):
                logger.error(f"Search failed: {result}")
                continue
            ticker, search_result = result
            results[ticker] = search_result

        return results

    def _update_universe_with_ibkr_details(self, universe_data: Dict[str, Any], stock_ticker: str, ibkr_details: Dict[str, Any]):
        """Update universe.json with IBKR identification details"""
        # Update in all screens where this stock appears
        for screen_name, screen_data in universe_data.get('screens', {}).items():
            for stock in screen_data.get('stocks', []):
                if stock.get('ticker') == stock_ticker:
                    # Add IBKR details
                    stock['ibkr_details'] = {
                        'found': True,
                        'symbol': ibkr_details['symbol'],
                        'longName': ibkr_details['longName'],
                        'exchange': ibkr_details['exchange'],
                        'primaryExchange': ibkr_details.get('primaryExchange', ''),
                        'conId': ibkr_details.get('conId', 0),
                        'search_method': ibkr_details.get('search_method', 'unknown'),
                        'match_score': ibkr_details.get('match_score', 0.0)
                    }

    def _mark_stock_not_found(self, universe_data: Dict[str, Any], stock_ticker: str):
        """Mark stock as not found in IBKR"""
        for screen_name, screen_data in universe_data.get('screens', {}).items():
            for stock in screen_data.get('stocks', []):
                if stock.get('ticker') == stock_ticker:
                    stock['ibkr_details'] = {
                        'found': False,
                        'search_attempted': True
                    }

    async def process_universe_stocks(
        self,
        universe_path: str = 'data/universe.json',
        output_path: str = 'data/universe_with_ibkr.json',
        max_concurrent: int = 5,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Process all unique stocks from universe.json with optimized concurrent search"""

        start_time = time.time()

        # Load universe data
        if not os.path.exists(universe_path):
            raise FileNotFoundError(f"Universe file not found: {universe_path}")

        with open(universe_path, 'r', encoding='utf-8') as f:
            universe_data = json.load(f)

        # Extract unique stocks
        unique_stocks = self.extract_unique_stocks(universe_data)
        logger.info(f"Found {len(unique_stocks)} unique stocks in universe.json")

        # Statistics
        stats = {
            'total': len(unique_stocks),
            'found_isin': 0,
            'found_ticker': 0,
            'found_name': 0,
            'not_found': 0,
            'not_found_stocks': [],
            'execution_time_seconds': 0
        }

        # Progress callback
        def progress_callback(current: int, total: int, current_stock: str):
            logger.info(f"[{current}/{total}] Processing: {current_stock}")

        # Search all stocks concurrently
        results = await self.search_multiple_stocks(
            unique_stocks,
            max_concurrent=max_concurrent,
            use_cache=use_cache,
            progress_callback=progress_callback
        )

        # Process results and update universe
        for stock in unique_stocks:
            ticker = stock['ticker']
            match, score = results.get(ticker, (None, 0.0))

            if match and score > 0.0:
                # Update universe data
                self._update_universe_with_ibkr_details(universe_data, ticker, match)

                # Update statistics based on search method
                search_method = match.get('search_method', 'unknown')
                if search_method == 'isin':
                    stats['found_isin'] += 1
                elif search_method == 'ticker':
                    stats['found_ticker'] += 1
                elif search_method == 'name':
                    stats['found_name'] += 1

                logger.info(f"FOUND: {ticker} -> {match['symbol']} on {match['exchange']} "
                           f"(method: {search_method}, score: {score:.1%})")
            else:
                # Mark as not found
                self._mark_stock_not_found(universe_data, ticker)
                stats['not_found'] += 1
                stats['not_found_stocks'].append({
                    'ticker': ticker,
                    'name': stock['name'],
                    'currency': stock['currency'],
                    'country': stock.get('country', 'Unknown')
                })
                logger.info(f"NOT FOUND: {ticker}")

        # Save updated universe
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(universe_data, f, indent=2, ensure_ascii=False)

        # Calculate execution time
        stats['execution_time_seconds'] = time.time() - start_time

        # Print final statistics
        logger.info("=" * 80)
        logger.info("OPTIMIZED IBKR SEARCH RESULTS")
        logger.info("=" * 80)
        logger.info(f"Total unique stocks: {stats['total']}")
        logger.info(f"Found via ISIN: {stats['found_isin']} ({stats['found_isin']/stats['total']*100:.1f}%)")
        logger.info(f"Found via ticker: {stats['found_ticker']} ({stats['found_ticker']/stats['total']*100:.1f}%)")
        logger.info(f"Found via name: {stats['found_name']} ({stats['found_name']/stats['total']*100:.1f}%)")
        logger.info(f"Not found: {stats['not_found']} ({stats['not_found']/stats['total']*100:.1f}%)")

        total_found = stats['found_isin'] + stats['found_ticker'] + stats['found_name']
        logger.info(f"OVERALL COVERAGE: {total_found}/{stats['total']} ({total_found/stats['total']*100:.1f}%)")
        logger.info(f"EXECUTION TIME: {stats['execution_time_seconds']:.1f} seconds")

        if self.cache_enabled:
            cache_stats = self.get_cache_statistics()
            logger.info(f"CACHE PERFORMANCE: {cache_stats['hit_rate']:.1%} hit rate "
                       f"({cache_stats['cache_hits']} hits, {cache_stats['cache_misses']} misses)")

        if stats['not_found_stocks']:
            logger.info(f"STOCKS NOT FOUND ({len(stats['not_found_stocks'])}):")
            for stock in stats['not_found_stocks']:
                logger.info(f"  - {stock['name']} ({stock['ticker']}) - {stock['currency']} - {stock['country']}")

        logger.info(f"Updated universe saved to: {output_path}")

        return stats

    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = self.cache_stats["hits"] / total_requests if total_requests > 0 else 0.0

        return {
            "cache_hits": self.cache_stats["hits"],
            "cache_misses": self.cache_stats["misses"],
            "hit_rate": hit_rate,
            "total_cached_symbols": len(self.cache)
        }

    async def clear_cache(self) -> bool:
        """Clear all cached search results"""
        self.cache.clear()
        self.cache_stats = {"hits": 0, "misses": 0}
        return True

    async def get_connection_pool_status(self) -> Dict[str, Any]:
        """Get status of IBKR connection pool"""
        return {
            "total_connections": len(self.connection_pool),
            "available_connections": self.available_connections.qsize(),
            "max_connections": self.max_connections,
            "connections_healthy": sum(1 for app in self.connection_pool if app.connected)
        }

    async def cleanup(self):
        """Cleanup connections and resources"""
        for app in self.connection_pool:
            try:
                app.disconnect()
            except Exception as e:
                logger.debug(f"Error disconnecting IBKR client: {e}")

        self.connection_pool.clear()
        while not self.available_connections.empty():
            try:
                self.available_connections.get_nowait()
            except:
                break