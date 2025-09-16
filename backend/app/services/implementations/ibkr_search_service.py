#!/usr/bin/env python3
"""
IBKR Search Service Implementation
Comprehensive enhanced search with multiple strategies to find all available stocks
Processes all unique stocks from universe.json and updates with IBKR identification details

This implementation maintains 100% behavioral compatibility with the legacy code
while organizing it within the API-first architecture.
"""

import json
import re
from difflib import SequenceMatcher
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import threading
import time
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import unicodedata

from ..interfaces import IIBKRSearchService


class IBApi(EWrapper, EClient):
    """
    IBKR API wrapper - identical to legacy implementation
    Extends EWrapper and EClient for Interactive Brokers API communication
    """

    def __init__(self):
        EClient.__init__(self, self)
        self.connected = False
        self.contract_details = []
        self.matching_symbols = []
        self.next_req_id = 1
        self.search_completed = False
        self.symbol_search_completed = False

    def connectAck(self):
        super().connectAck()
        self.connected = True

    def connectionClosed(self):
        super().connectionClosed()
        self.connected = False

    def contractDetails(self, reqId, contractDetails):
        super().contractDetails(reqId, contractDetails)
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
        self.search_completed = True

    def symbolSamples(self, reqId, contractDescriptions):
        super().symbolSamples(reqId, contractDescriptions)
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
        self.symbol_search_completed = True

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        pass


def create_contract_from_ticker(ticker, currency, exchange="SMART"):
    """Create IBKR contract from ticker - identical to legacy"""
    contract = Contract()
    contract.symbol = ticker
    contract.secType = "STK"
    contract.currency = currency
    contract.exchange = exchange
    return contract


def create_contract_from_isin(isin, currency):
    """Create IBKR contract from ISIN - identical to legacy"""
    contract = Contract()
    contract.secIdType = "ISIN"
    contract.secId = isin
    contract.secType = "STK"
    contract.currency = currency
    contract.exchange = "SMART"
    return contract


def similarity_score(str1, str2):
    """Calculate similarity score between two strings - identical to legacy"""
    if not str1 or not str2:
        return 0.0
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


class IBKRSearchService(IIBKRSearchService):
    """
    IBKR Search Service Implementation
    Contains the exact same logic as the legacy comprehensive_enhanced_search.py
    """

    def extract_unique_stocks(self, universe_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract unique stocks from universe.json - identical to legacy"""
        unique_stocks = {}

        # Process all screens
        for screen_name, screen_data in universe_data.get('screens', {}).items():
            for stock in screen_data.get('stocks', []):
                # Use ticker as unique key
                ticker = stock.get('ticker')
                if ticker:
                    current_stock = {
                        'ticker': ticker,
                        'isin': stock.get('isin'),
                        'name': stock.get('name'),
                        'currency': stock.get('currency'),
                        'sector': stock.get('sector'),
                        'country': stock.get('country'),
                        'quantity': stock.get('quantity', 0),
                        'final_target': stock.get('final_target', 0)
                    }

                    # If ticker already exists, pick the one with highest quantity
                    # (to handle stocks appearing in multiple screens)
                    if ticker in unique_stocks:
                        existing_quantity = unique_stocks[ticker].get('quantity', 0)
                        current_quantity = current_stock.get('quantity', 0)

                        # Keep the occurrence with the highest quantity
                        # If quantities are equal, keep the one with highest final_target
                        if (current_quantity > existing_quantity or
                            (current_quantity == existing_quantity and
                             current_stock.get('final_target', 0) > unique_stocks[ticker].get('final_target', 0))):
                            unique_stocks[ticker] = current_stock
                    else:
                        unique_stocks[ticker] = current_stock

        # Filter to only include stocks with quantities > 0
        filtered_stocks = [stock for stock in unique_stocks.values() if stock.get('quantity', 0) > 0]
        return filtered_stocks

    def get_all_ticker_variations(self, ticker: str) -> List[str]:
        """Generate comprehensive ticker variations - identical to legacy"""
        variations = [ticker]

        # Remove exchange suffix
        base_ticker = re.sub(r'\.[A-Z]+$', '', ticker)
        if base_ticker != ticker:
            variations.append(base_ticker)

        # Japanese stocks (.T suffix) - specific handling
        if '.T' in ticker:
            base = ticker.replace('.T', '')
            variations.append(base)
            # Some Japanese stocks are listed with different numbers
            if base.isdigit():
                # Try common variations for numbered Japanese stocks
                base_num = int(base)
                # Sometimes stocks are listed with slight variations (rare but possible)
                variations.append(str(base_num))

        # Share class variations
        if '-A' in ticker:
            # ROCK-A.CO -> ROCKA, ROCK.A
            no_dash = ticker.replace('-A', 'A')
            variations.append(no_dash)
            variations.append(re.sub(r'\.[A-Z]+$', '', no_dash))

            dot_class = ticker.replace('-A', '.A')
            variations.append(dot_class)
            variations.append(re.sub(r'\.[A-Z]+$', '', dot_class))

        if '-B' in ticker:
            # NEWA-B.ST -> NEWA.B, NEWAB
            dot_class = ticker.replace('-B', '.B')
            variations.append(dot_class)
            variations.append(re.sub(r'\.[A-Z]+$', '', dot_class))

            no_dash = ticker.replace('-B', 'B')
            variations.append(no_dash)
            variations.append(re.sub(r'\.[A-Z]+$', '', no_dash))

        # Greek stocks - try without .AT suffix and with different formats
        if '.AT' in ticker:
            base = ticker.replace('.AT', '')
            variations.append(base)
            # Try common Greek stock formats
            if len(base) <= 6:
                variations.append(base + 'A')  # Some Greek stocks have A suffix

        # London stocks - try different formats
        if '.L' in ticker:
            base = ticker.replace('.L', '')
            variations.append(base)

        # Finnish stocks (.HE suffix)
        if '.HE' in ticker:
            base = ticker.replace('.HE', '')
            variations.append(base)

        # French stocks (.PA suffix)
        if '.PA' in ticker:
            base = ticker.replace('.PA', '')
            variations.append(base)

        # Remove duplicates
        seen = set()
        variations = [x for x in variations if not (x in seen or seen.add(x))]

        return variations

    def is_valid_match(
        self,
        universe_stock: Dict[str, Any],
        ibkr_contract: Dict[str, Any],
        search_method: str = "unknown"
    ) -> Tuple[bool, str]:
        """Validation with different rules based on search method - identical to legacy"""
        universe_name = universe_stock['name'].lower()
        ibkr_name = ibkr_contract['longName'].lower()

        # Must have currency match
        if ibkr_contract['currency'] != universe_stock['currency']:
            return False, "Currency mismatch"

        # Extract key company identifiers - clean punctuation first
        # Special handling for L'OREAL type names - join L + OREAL = LOREAL
        universe_clean = re.sub(r"[''`\-\.\,\(\)\[\]]", "", universe_name)  # Remove completely, don't replace with space
        ibkr_clean = re.sub(r"[''`\-\.\,\(\)\[\]]", "", ibkr_name)

        # Handle accented characters - normalize to ASCII
        universe_clean = unicodedata.normalize('NFD', universe_clean).encode('ascii', 'ignore').decode('ascii')
        ibkr_clean = unicodedata.normalize('NFD', ibkr_clean).encode('ascii', 'ignore').decode('ascii')

        universe_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', universe_clean))
        ibkr_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', ibkr_clean))

        # Remove common corporate suffixes that don't help with matching
        ignore_words = {
            'ltd', 'plc', 'inc', 'corp', 'sa', 'ab', 'oyj', 'group', 'international',
            'company', 'limited', 'corporation', 'societe', 'anonyme', 'systems',
            'software', 'commercial', 'industrial', 'authority', 'public', 'co', 'oy'
        }

        universe_key_words = universe_words - ignore_words
        ibkr_key_words = ibkr_words - ignore_words

        word_overlap = len(universe_key_words & ibkr_key_words)
        name_similarity = similarity_score(universe_name, ibkr_name)

        # Check for exact key word matches
        exact_matches = []
        for word in universe_key_words:
            if word in ibkr_key_words:
                exact_matches.append(word)

        # Different validation rules based on search method
        if search_method == "ticker":
            # Be more lenient for ticker matches - ticker match + currency is strong signal
            if name_similarity > 0.3:  # Very lenient for ticker matches
                return True, f"Ticker match + similarity: {name_similarity:.2f}"
            elif word_overlap >= 1:  # Any word overlap for ticker matches
                return True, f"Ticker match + word overlap: {word_overlap}"
            else:
                return True, f"Ticker match (currency confirmed): {name_similarity:.2f}"

        elif search_method == "isin":
            # ISIN should be reliable, but add safety check for name similarity
            # to catch data quality issues (wrong ISIN in source data)
            if name_similarity > 0.6:  # Require at least 60% similarity for ISIN matches
                return True, f"ISIN match + good similarity: {name_similarity:.2f}"
            elif word_overlap >= 2:  # Or at least 2 meaningful word overlap (excluding corporate suffixes)
                return True, f"ISIN match + strong word overlap: {word_overlap}"
            elif word_overlap >= 1 and name_similarity > 0.4:  # 1 word + decent similarity
                return True, f"ISIN match + word overlap + similarity: {word_overlap}, {name_similarity:.2f}"
            else:
                # ISIN match but insufficient name similarity - likely data quality issue
                return False, f"ISIN match but poor name similarity: {name_similarity:.2f}, word_overlap: {word_overlap} (possible wrong ISIN)"

        else:
            # Name-based search - more strict validation
            if name_similarity > 0.8:  # Very high similarity is OK
                return True, f"High similarity: {name_similarity:.2f}"
            elif exact_matches and name_similarity > 0.5:  # Exact key word match + decent similarity
                return True, f"Exact word match ({','.join(exact_matches)}): {name_similarity:.2f}"
            elif word_overlap >= 2 and name_similarity > 0.6:  # Good overlap + decent similarity
                return True, f"Word overlap: {word_overlap}, similarity: {name_similarity:.2f}"
            elif word_overlap >= 1 and name_similarity > 0.7:  # Some overlap + high similarity
                return True, f"Some overlap + high similarity: {word_overlap}, {name_similarity:.2f}"
            else:
                return False, f"Insufficient match: overlap={word_overlap}, similarity={name_similarity:.2f}"

    def search_by_name_matching(
        self,
        app: Any,
        stock: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Use reqMatchingSymbols to search by company name parts - identical to legacy"""
        name = stock['name'].lower()
        search_terms = []

        # Extract meaningful words from company name
        words = re.findall(r'\b[a-zA-Z]{3,}\b', stock['name'])  # Words with 3+ letters

        # Add individual words
        for word in words[:3]:  # Try first 3 meaningful words
            if word.lower() not in ['ltd', 'plc', 'inc', 'corp', 'sa', 'ab', 'oyj', 'group', 'international']:
                search_terms.append(word)

        # Add combinations
        if len(words) >= 2:
            search_terms.append(f"{words[0]} {words[1]}")

        # Special cases based on known mappings
        if 'everplay' in name:
            search_terms.extend(['everplay', 'EVPL'])
        if 'sarantis' in name:
            search_terms.extend(['sarantis', 'SAR'])
        if 'dewhurst' in name:
            search_terms.extend(['dewhurst', 'DWHT'])
        if 'ilyda' in name:
            search_terms.extend(['ilyda'])
        if 'thessaloniki' in name or 'port' in name:
            search_terms.extend(['thessaloniki', 'port', 'OLTH'])

        all_matches = []

        for term in search_terms:
            if len(term) < 2:
                continue

            try:
                app.matching_symbols = []
                app.symbol_search_completed = False
                app.reqMatchingSymbols(app.next_req_id, term)
                app.next_req_id += 1

                timeout_start = time.time()
                while not app.symbol_search_completed and (time.time() - timeout_start) < 20:
                    time.sleep(0.05)

                # Convert matching symbols to contract details
                for match in app.matching_symbols:
                    if match['currency'] == stock['currency']:  # Currency filter
                        # Get full contract details
                        contract = create_contract_from_ticker(match['symbol'], match['currency'], match['exchange'])

                        app.contract_details = []
                        app.search_completed = False
                        app.reqContractDetails(app.next_req_id, contract)
                        app.next_req_id += 1

                        timeout_start = time.time()
                        while not app.search_completed and (time.time() - timeout_start) < 20:
                            time.sleep(0.05)

                        all_matches.extend(app.contract_details)
                        time.sleep(0.1)

                time.sleep(0.2)

            except Exception as e:
                pass

        return all_matches

    def comprehensive_stock_search(
        self,
        app: Any,
        stock: Dict[str, Any],
        verbose: bool = False
    ) -> Tuple[Optional[Dict[str, Any]], float]:
        """Comprehensive search using multiple strategies - identical to legacy"""
        if verbose:
            print(f"Searching: {stock['name']} ({stock.get('ticker', 'N/A')})")

        all_contracts = []
        search_method = "unknown"

        # Strategy 1: ISIN search
        if stock.get('isin') and stock.get('isin') not in ['null', '', None]:
            if verbose:
                print(f"  Strategy 1 - ISIN: {stock['isin']}")
            contract = create_contract_from_isin(stock['isin'], stock['currency'])

            app.contract_details = []
            app.search_completed = False
            app.reqContractDetails(app.next_req_id, contract)
            app.next_req_id += 1

            timeout_start = time.time()
            while not app.search_completed and (time.time() - timeout_start) < 20:
                time.sleep(0.05)

            if app.contract_details:
                # Mark these as ISIN results
                for contract in app.contract_details:
                    contract['_search_method'] = 'isin'
                all_contracts.extend(app.contract_details)
                if verbose:
                    print(f"    ISIN found: {len(app.contract_details)} results")

        # Strategy 2: Ticker variations on SMART exchange
        # Always try ticker search if we have a ticker, regardless of ISIN results
        # (ISIN results might get rejected during validation)
        if stock.get('ticker'):
            if verbose:
                print(f"  Strategy 2 - Ticker variations")
            ticker = stock['ticker']
            currency = stock['currency']
            variations = self.get_all_ticker_variations(ticker)
            if verbose:
                print(f"    Variations: {variations}")

            for variant in variations:
                if verbose:
                    print(f"    Trying: {variant} ({currency})")
                contract = create_contract_from_ticker(variant, currency, "SMART")

                app.contract_details = []
                app.search_completed = False
                app.reqContractDetails(app.next_req_id, contract)
                app.next_req_id += 1

                timeout_start = time.time()
                while not app.search_completed and (time.time() - timeout_start) < 20:
                    time.sleep(0.05)

                if app.contract_details:
                    # Mark these as ticker results
                    for contract in app.contract_details:
                        contract['_search_method'] = 'ticker'
                    all_contracts.extend(app.contract_details)
                    if verbose:
                        print(f"      FOUND with {variant}!")
                    break  # Found it, move on

                time.sleep(0.1)

        # Strategy 3: Name-based symbol matching
        if not all_contracts:
            if verbose:
                print(f"  Strategy 3 - Name-based search")
            name_matches = self.search_by_name_matching(app, stock)
            if name_matches:
                # Mark these as name results
                for contract in name_matches:
                    contract['_search_method'] = 'name'
                all_contracts.extend(name_matches)
                if verbose:
                    print(f"    Name search found: {len(name_matches)} results")

        # Match and score results with validation based on search method
        if all_contracts:
            valid_matches = []

            if verbose:
                print(f"  Evaluating {len(all_contracts)} potential matches...")

            for contract in all_contracts:
                contract_search_method = contract.get('_search_method', 'unknown')
                is_valid, reason = self.is_valid_match(stock, contract, contract_search_method)

                if is_valid:
                    name_sim = similarity_score(stock['name'].lower(), contract['longName'].lower())
                    if verbose:
                        print(f"    VALID: {contract['symbol']}: {contract['longName'][:40]} -> {reason}")
                    valid_matches.append((contract, name_sim))
                else:
                    if verbose:
                        print(f"    REJECTED: {contract['symbol']}: {contract['longName'][:40]} -> {reason}")

            if valid_matches:
                # Sort by name similarity and pick the best
                valid_matches.sort(key=lambda x: x[1], reverse=True)
                best_match = valid_matches[0][0]
                best_score = valid_matches[0][1]
                # Keep the individual search method that was used for this specific match
                best_match['search_method'] = best_match.get('_search_method', 'unknown')
            else:
                best_match = None
                best_score = 0.0

            return best_match, best_score

        return None, 0.0

    def update_universe_with_ibkr_details(
        self,
        universe_data: Dict[str, Any],
        stock_ticker: str,
        ibkr_details: Dict[str, Any]
    ) -> None:
        """Update universe.json with IBKR identification details - identical to legacy"""
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

    def mark_stock_not_found(
        self,
        universe_data: Dict[str, Any],
        stock_ticker: str
    ) -> None:
        """Mark stock as not found in IBKR - identical to legacy"""
        for screen_name, screen_data in universe_data.get('screens', {}).items():
            for stock in screen_data.get('stocks', []):
                if stock.get('ticker') == stock_ticker:
                    stock['ibkr_details'] = {
                        'found': False,
                        'search_attempted': True
                    }

    def process_all_universe_stocks(self) -> Dict[str, Any]:
        """Process all stocks from universe.json and update with IBKR details - identical to legacy"""

        # Load universe.json
        script_dir = Path(__file__).parent
        universe_path = script_dir.parent.parent.parent.parent / 'data' / 'universe.json'

        if not universe_path.exists():
            print(f"Error: universe.json not found at {universe_path}")
            return {}

        with open(universe_path, 'r', encoding='utf-8') as f:
            universe_data = json.load(f)

        # Extract unique stocks
        unique_stocks = self.extract_unique_stocks(universe_data)
        print(f"Found {len(unique_stocks)} unique stocks with quantities > 0")

        if len(unique_stocks) == 0:
            print("❌ No stocks with quantities > 0 found. Exiting.")
            return {}

        # Connect to IBKR
        app = IBApi()
        app.connect("127.0.0.1", 4002, clientId=20)

        api_thread = threading.Thread(target=app.run, daemon=True)
        api_thread.start()

        timeout = 10
        start_time = time.time()
        while not app.connected and (time.time() - start_time) < timeout:
            time.sleep(0.1)

        if not app.connected:
            print("Failed to connect to IB Gateway")
            return {}

        print("Connected to IB Gateway")
        print("="*80)

        # Statistics
        stats = {
            'total': len(unique_stocks),
            'found_isin': 0,
            'found_ticker': 0,
            'found_name': 0,
            'not_found': 0,
            'not_found_stocks': []
        }

        # Process each stock
        for i, stock in enumerate(unique_stocks, 1):
            ticker = stock['ticker']
            print(f"\n[{i}/{len(unique_stocks)}] Processing: {stock['name']} ({ticker})")

            # Search for the stock
            # Debug for L'Oréal specifically
            debug = ticker == "OR.PA"
            match, score = self.comprehensive_stock_search(app, stock, verbose=debug)

            if match and score > 0.0:
                # Determine search method
                search_method = "unknown"
                if stock.get('isin') and stock.get('isin') not in ['null', '', None]:
                    # Check if found by ISIN
                    test_contract = create_contract_from_isin(stock['isin'], stock['currency'])
                    app.contract_details = []
                    app.search_completed = False
                    app.reqContractDetails(app.next_req_id, test_contract)
                    app.next_req_id += 1

                    timeout_start = time.time()
                    while not app.search_completed and (time.time() - timeout_start) < 20:
                        time.sleep(0.05)

                    if app.contract_details:
                        search_method = "isin"
                        stats['found_isin'] += 1
                    else:
                        search_method = "ticker"
                        stats['found_ticker'] += 1
                else:
                    # If no ISIN, check if found by ticker or name
                    if match['symbol'].upper() in [v.upper() for v in self.get_all_ticker_variations(ticker)]:
                        search_method = "ticker"
                        stats['found_ticker'] += 1
                    else:
                        search_method = "name"
                        stats['found_name'] += 1

                # Add search method and score to match details
                match['search_method'] = search_method
                match['match_score'] = score

                # Update universe data
                self.update_universe_with_ibkr_details(universe_data, ticker, match)

                print(f"  FOUND: {match['symbol']} on {match['exchange']} (method: {search_method}, score: {score:.1%})")
            else:
                # Mark as not found
                self.mark_stock_not_found(universe_data, ticker)
                stats['not_found'] += 1
                stats['not_found_stocks'].append({
                    'ticker': ticker,
                    'name': stock['name'],
                    'currency': stock['currency'],
                    'country': stock.get('country', 'Unknown')
                })
                print(f"  NOT FOUND")

            # Small delay between searches
            time.sleep(0.5)

        # Disconnect from IBKR
        app.disconnect()

        # Save updated universe.json
        output_path = script_dir.parent.parent.parent.parent / 'data' / 'universe_with_ibkr.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(universe_data, f, indent=2, ensure_ascii=False)

        # Print final statistics
        print("\n" + "="*80)
        print("COMPREHENSIVE SEARCH RESULTS")
        print("="*80)
        print(f"Total unique stocks: {stats['total']}")
        print(f"Found via ISIN: {stats['found_isin']} ({stats['found_isin']/stats['total']*100:.1f}%)")
        print(f"Found via ticker: {stats['found_ticker']} ({stats['found_ticker']/stats['total']*100:.1f}%)")
        print(f"Found via name: {stats['found_name']} ({stats['found_name']/stats['total']*100:.1f}%)")
        print(f"Not found: {stats['not_found']} ({stats['not_found']/stats['total']*100:.1f}%)")

        total_found = stats['found_isin'] + stats['found_ticker'] + stats['found_name']
        print(f"\nOVERALL COVERAGE: {total_found}/{stats['total']} ({total_found/stats['total']*100:.1f}%)")

        if stats['not_found_stocks']:
            print(f"\nSTOCKS NOT FOUND IN IBKR ({len(stats['not_found_stocks'])}):")
            for stock in stats['not_found_stocks']:
                print(f"  - {stock['name']} ({stock['ticker']}) - {stock['currency']} - {stock['country']}")

        print(f"\nUpdated universe saved to: {output_path}")

        return stats