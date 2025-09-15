# API Migration Plan: Monolith to API-First Architecture

## Overview
Transform the current 11-step monolithic pipeline into a scalable API-first architecture while maintaining **100% behavioral compatibility**. Each step will be thoroughly tested to ensure identical functionality.

## Migration Strategy
- ✅ **Zero Breaking Changes**: Existing CLI functionality remains identical
- ✅ **Interface-First Design**: Define contracts before implementation
- ✅ **Gradual Migration**: One step at a time with full testing
- ✅ **Dual Operation**: CLI and API work simultaneously during transition
- ✅ **Implementation-First Analysis**: Study current code deeply before any changes
- ✅ **Test-Driven Service Design**: Behavior-driven testing for all services
- ✅ **Production-Ready Error Handling**: Structured error responses with proper HTTP codes
- ✅ **Configuration Management**: Environment-based settings and secrets management

---

## Step 0: Repository Structure & Organization
**Goal**: Create clean backend structure and organize existing files

### Actions:
1. **Create backend directory structure**:
   ```
   backend/
   ├── app/
   │   ├── __init__.py
   │   ├── main.py                 # FastAPI entry point
   │   ├── core/
   │   │   ├── __init__.py
   │   │   ├── config.py           # Centralized configuration
   │   │   ├── dependencies.py     # DI container
   │   │   ├── exceptions.py       # Custom exception classes
   │   │   └── middleware.py       # Error handling middleware
   │   ├── services/
   │   │   ├── __init__.py
   │   │   ├── interfaces.py       # Abstract interfaces
   │   │   └── implementations/
   │   │       ├── __init__.py
   │   │       └── legacy/         # Wrapped legacy functions
   │   ├── api/
   │   │   ├── __init__.py
   │   │   └── v1/
   │   │       ├── __init__.py
   │   │       └── endpoints/
   │   │           └── __init__.py
   │   ├── models/
   │   │   ├── __init__.py
   │   │   ├── schemas.py          # Pydantic models
   │   │   └── errors.py           # Error response models
   │   └── tests/
   │       ├── __init__.py
   │       ├── conftest.py         # Test configuration
   │       ├── unit/               # Unit tests
   │       ├── integration/        # Integration tests
   │       └── behavior/           # CLI vs API behavior tests
   ├── requirements.txt
   ├── requirements-dev.txt        # Development dependencies
   ├── pytest.ini                 # Test configuration
   ├── .env.example               # Environment template
   └── Dockerfile
   ```

2. **Move and organize existing files**:
   - Keep `main.py` in root (CLI interface)
   - Move `src/` files to `backend/app/services/implementations/legacy/`
   - Keep `config.py` in root, create new one in `backend/app/core/`

3. **Create initial FastAPI setup**
4. **Verify**: Original CLI still works exactly the same

**⚠️ TESTING REQUIREMENTS:**
- **Activate virtual environment FIRST**: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)
- **Save ALL tests in**: `backend\app\tests\` directory
- **Run tests with**: `pytest backend/app/tests/` from project root
- **🚨 MANDATORY**: ALL tests must pass 100% before step validation
- **🚨 MANDATORY**: ALL tests must pass 100% before step validation

**Testing**: Run `python main.py` and ensure identical output

**Status**: ⏸️ Not Started

---

## Step 1: Data Fetching Service (Uncle Stock API)
**Goal**: Wrap `src/screener.py` functions with API endpoints

### Current Functions:
- `get_current_stocks()` - Fetch current stocks from screener
- `get_screener_history()` - Fetch backtest history
- `get_all_screeners()` - Fetch from all configured screeners
- `get_all_screener_histories()` - Fetch all histories

### Actions:

#### Phase 1: Deep Analysis (MANDATORY FIRST)
1. **📖 STUDY `src/screener.py` COMPLETELY**:
   - Read every line, understand every function
   - Document exact function signatures and return types
   - Map all dependencies: requests, config imports, file operations
   - Note all side effects: CSV file creation, console prints
   - Identify error handling patterns and timeout values
   - **UPDATE THIS PLAN** with exact implementation details

#### Phase 2: Implementation (ONLY AFTER ANALYSIS)
2. **Create configuration models**:
   ```python
   class UncleStockSettings(BaseSettings):
       uncle_stock_user_id: str
       uncle_stock_timeout: int = 60
       retry_attempts: int = 3
       max_results_per_screener: int = 200

       class Config:
           env_prefix = "UNCLE_STOCK_"
   ```

3. **Create custom exceptions**:
   ```python
   class UncleStockAPIError(Exception):
       """Base exception for Uncle Stock API errors"""

   class UncleStockTimeoutError(UncleStockAPIError):
       """Raised when Uncle Stock API times out"""

   class UncleStockRateLimitError(UncleStockAPIError):
       """Raised when Uncle Stock API rate limit exceeded"""
   ```

4. **Create interface**: `IDataProvider` in `services/interfaces.py`
5. **Create implementation**: `UncleStockService` wrapping existing functions
6. **Create Pydantic models** for request/response:
   ```python
   class ScreenerDataResponse(BaseModel):
       screener_id: str
       symbols: List[str]
       csv_file_path: Optional[str]
       total_count: int
       fetched_at: datetime

   class ErrorResponse(BaseModel):
       error_code: str
       message: str
       details: Optional[Dict[str, Any]] = None
       retry_after: Optional[int] = None
   ```

7. **Create API endpoints with proper error handling**:
   - `GET /api/v1/screeners/data` → `get_all_screeners()`
   - `GET /api/v1/screeners/data/{screener_id}` → `get_current_stocks()`
   - `GET /api/v1/screeners/history` → `get_all_screener_histories()`
   - `GET /api/v1/screeners/history/{screener_id}` → `get_screener_history()`

#### Phase 3: Testing (MANDATORY)
8. **Create unit tests in `backend\app\tests\`**:
   ```python
   class TestUncleStockService:
       def test_fetch_screener_data_success(self):
           # Test successful data fetching behavior

       def test_fetch_screener_data_timeout(self):
           # Test timeout handling behavior

       def test_fetch_screener_data_invalid_screener(self):
           # Test error handling for invalid screener
   ```

9. **Create integration tests in `backend\app\tests\`**:
   ```python
   class TestScreenerAPIEndpoints:
       def test_get_screener_data_endpoint(self):
           # Test full endpoint behavior

       def test_error_response_format(self):
           # Test error response structure
   ```

10. **Create behavior verification tests in `backend\app\tests\`**:
    ```python
    class TestCLIVsAPIBehavior:
        def test_identical_output_screener_data(self):
            # Verify CLI and API produce identical results

        def test_identical_file_creation(self):
            # Verify same CSV files are created
    ```

**⚠️ TESTING REQUIREMENTS:**
- **Activate virtual environment FIRST**: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)
- **Save ALL tests in**: `backend\app\tests\` directory
- **Run tests with**: `pytest backend/app/tests/` from project root
- **🚨 MANDATORY**: ALL tests must pass 100% before step validation

#### Phase 4: Error Handling & Monitoring
11. **Add structured error handlers**:
    ```python
    @app.exception_handler(UncleStockTimeoutError)
    async def timeout_handler(request, exc):
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                error_code="UNCLE_STOCK_TIMEOUT",
                message="Uncle Stock API temporarily unavailable",
                retry_after=60
            ).dict()
        )
    ```

12. **Add logging and monitoring**:
    ```python
    logger.info("Fetching screener data", extra={
        "screener_id": screener_id,
        "user_id": user_id,
        "request_id": request.headers.get("X-Request-ID")
    })
    ```

#### Phase 5: Final Verification
13. **Test CLI**: `python main.py 1` produces identical results
14. **Test API**: Endpoints return same data with proper error handling
15. **Performance test**: Verify no significant latency increase
16. **Documentation**: Update API docs with new endpoints

**Acceptance Criteria**:
- CLI `step1_fetch_data()` behavior unchanged
- API endpoints return identical data structure
- Same CSV files created in `data/files_exports/`
- Same console output and error messages

**Status**: 🔄 Analysis Complete - Ready for Implementation

---

## Step 2: Data Parsing Service
**Goal**: Wrap `src/parser.py` functions with API endpoints

### ✅ ANALYSIS COMPLETE - Current Implementation Details:

#### Core Functions Identified:
1. **`find_column_index(headers, description_row, header_name, subtitle_pattern)`**
   - Purpose: Find column index based on header name and subtitle pattern matching
   - Returns: int (column index) or None if not found
   - Used internally by other parsing functions

2. **`extract_field_data(csv_path, header_name, subtitle_pattern, ticker=None)`**
   - Purpose: Extract specific field data from CSV file using header/subtitle pattern
   - Parameters: CSV path, header name, subtitle pattern, optional ticker filter
   - Returns: dict (single stock) or list (all stocks) or None if not found
   - Side effects: File I/O, console error printing

3. **`parse_screener_csv_flexible(csv_path, additional_fields=None)`**
   - Purpose: Parse CSV with both standard and custom additional fields
   - Parameters: CSV path, optional additional fields list as tuples (header, subtitle, alias)
   - Returns: list of stock dictionaries with all configured fields
   - Standard fields: ticker, isin, name, currency, sector, country, price
   - Side effects: File I/O, console error printing

4. **`parse_screener_csv(csv_path)`**
   - Purpose: Parse CSV with only standard fields (no additional fields)
   - Parameters: CSV path
   - Returns: list of stock dictionaries with standard fields only
   - Side effects: File I/O, console error printing

5. **`create_universe()`**
   - Purpose: Parse ALL screener CSV files and aggregate into universe structure
   - Parameters: None (uses global config)
   - Returns: dict with metadata, screens, and all_stocks sections
   - Dependencies: UNCLE_STOCK_SCREENS, ADDITIONAL_FIELDS, EXTRACT_ADDITIONAL_FIELDS from config
   - Side effects: Multiple file I/O operations, console progress printing
   - File paths: `data/files_exports/{safe_name}_current_screen.csv`

6. **`save_universe(universe, output_path='data/universe.json')`**
   - Purpose: Save universe data to JSON file with summary statistics
   - Parameters: universe dict, optional output path (defaults to 'data/universe.json')
   - Returns: None
   - Side effects: JSON file creation, detailed console output with statistics

7. **`get_stock_field(ticker, header_name, subtitle_pattern, screen_name=None)`**
   - Purpose: Search for specific field value for a ticker across screens
   - Parameters: ticker symbol, header name, subtitle pattern, optional screen filter
   - Returns: dict with ticker, field, value, screen or None if not found
   - Side effects: Multiple file I/O operations if searching all screens

8. **`find_available_fields(csv_path=None)`**
   - Purpose: Discover all available header/subtitle combinations in a CSV
   - Parameters: optional CSV path (uses first available screen if None)
   - Returns: list of tuples (header, subtitle, column_index)
   - Side effects: File I/O

#### Dependencies Mapped:
- **Standard library**: csv, json, os, glob, sys
- **External config**: config.py with UNCLE_STOCK_SCREENS, ADDITIONAL_FIELDS, EXTRACT_ADDITIONAL_FIELDS
- **File system**: data/files_exports/ directory for CSV inputs, data/ for JSON output

#### CSV File Structure Understanding:
- Line 1: Optional sep= separator line (skipped if present)
- Line 2: Headers (symbol, ISIN, name, Price, etc.)
- Line 3: Subheaders
- Line 4: Description row (used for pattern matching like 'per share in stock price currency')
- Line 5+: Data rows

#### Error Handling Patterns:
- Try-catch blocks around all file operations
- Console error printing with file path context
- Graceful handling of missing files, invalid data, parsing errors
- Return None or empty lists on errors

#### Side Effects Documented:
1. **File I/O**: Reads from data/files_exports/*.csv, writes to data/universe.json
2. **Console Output**: Progress messages, error messages, statistics summaries
3. **Global Config Dependencies**: Uses UNCLE_STOCK_SCREENS mapping and field configurations

#### CLI Integration:
- Called via `step2_parse_data()` in main.py lines 62-74
- Simple wrapper: calls `create_universe()` then `save_universe(universe)`
- Returns boolean True on success

### Actions:

#### Phase 2: Implementation (ANALYSIS COMPLETE ✅)
1. **Create interfaces**: `IUniverseRepository` and `IDataParser` in `services/interfaces.py`
2. **Create implementation**: `UniverseService` wrapping existing functions in legacy parser
3. **Create API endpoints**:
   - `POST /api/v1/universe/parse` → `create_universe()` + `save_universe()`
   - `GET /api/v1/universe` → Load and return universe.json
   - `GET /api/v1/universe/stock/{ticker}/field` → `get_stock_field()`
   - `GET /api/v1/universe/fields/available` → `find_available_fields()`
4. **Test CLI**: `python main.py 2` produces identical universe.json
5. **Test API**: Universe data matches CLI output exactly

**⚠️ TESTING REQUIREMENTS:**
- **Activate virtual environment FIRST**: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)
- **Save ALL tests in**: `backend\app\tests\` directory
- **Run tests with**: `pytest backend/app/tests/` from project root
- **🚨 MANDATORY**: ALL tests must pass 100% before step validation

**Acceptance Criteria**:
- ✅ CLI `step2_parse_data()` behavior unchanged
- ✅ Identical `data/universe.json` file created
- ✅ Same metadata structure and stock counts
- ✅ Same console output for parsing results

**Status**: ✅ IMPLEMENTATION COMPLETE - VERIFIED WORKING

### 🎯 **VERIFICATION RESULTS**:
- **CLI Test**: `python main.py 2` produces identical output (501 total stocks, 438 unique stocks)
- **API Test**: `POST /api/v1/universe/parse` creates identical universe structure
- **Data Consistency**: Universe metadata, screens, and all_stocks sections are identical between CLI and API
- **Field Access**: `GET /api/v1/universe/stock/{ticker}/field` successfully retrieves stock field data
- **File Operations**: API correctly handles working directory changes to access CSV files

### 📋 **IMPLEMENTED ENDPOINTS**:
- `POST /api/v1/universe/parse` → `create_universe()` + `save_universe()`
- `GET /api/v1/universe` → Load and return universe.json
- `GET /api/v1/universe/metadata` → Get universe metadata only
- `GET /api/v1/universe/stock/{ticker}/field` → `get_stock_field()`
- `GET /api/v1/universe/stocks/{ticker}` → Get specific stock data
- `GET /api/v1/universe/fields/available` → `find_available_fields()`

### 🔧 **TECHNICAL IMPLEMENTATION**:
- **Interfaces**: `IDataParser` and `IUniverseRepository` in `backend/app/services/interfaces.py`
- **Service**: `UniverseService` wrapping legacy functions in `backend/app/services/implementations/universe_service.py`
- **Models**: Complete Pydantic models for request/response validation
- **Working Directory Fix**: Proper path resolution for CSV files when API runs from backend directory
- **Dependency Injection**: Singleton service instance in `backend/app/core/dependencies.py`

---

## Step 3: Historical Data Service
**Goal**: Wrap `src/history_parser.py` functions with API endpoints

### Current Functions Analysis (COMPLETED):

#### `parse_backtest_csv(csv_path: str, debug: bool = False) -> Dict[str, Any]`
- **Purpose**: Parse single backtest CSV file for performance metrics
- **Dependencies**: `csv`, `os`, file I/O operations
- **Returns**: Dict with `metadata`, `quarterly_performance`, `statistics` sections
- **Side Effects**: File reading, optional debug console prints
- **Error Handling**: Returns `{"error": "message"}` on file not found or parsing errors
- **CSV Parsing Logic**:
  - Metadata: First 13 lines contain key-value pairs
  - Statistics: Found by "Return" and "Period SD" headers, extracts total/yearly data
  - Quarterly Data: "Quarter return" lines matched with quarter headers from previous lines

#### `get_all_backtest_data() -> Dict[str, Dict[str, Any]]`
- **Purpose**: Parse all backtest CSV files for configured screeners
- **Dependencies**: `UNCLE_STOCK_SCREENS` from config, calls `parse_backtest_csv()`
- **Returns**: Dict mapping screener keys to their parsed performance data
- **Side Effects**: Console prints for each screener processed (`+` success, `X` error)
- **CSV Path Pattern**: `data/files_exports/{safe_name}_backtest_results.csv`
- **Name Sanitization**: Replaces spaces and slashes with underscores

#### `update_universe_with_history() -> bool`
- **Purpose**: Update universe.json with historical performance data in metadata section
- **Dependencies**: `json`, file I/O, calls `get_all_backtest_data()`
- **File Operations**: Reads `data/universe.json`, writes updated version back
- **Side Effects**: Console prints (`+` success, `X` error), modifies universe.json
- **Data Structure Added**: `metadata.historical_performance` with:
  - `screen_name`, `backtest_metadata`, `key_statistics`
  - `quarterly_summary` (total_quarters, avg_quarterly_return, quarterly_std)
  - `quarterly_data` (complete quarterly performance arrays)
- **Statistics Calculation**: Averages quarterly returns and standard deviations
- **Error Handling**: Graceful handling of missing files and parsing errors

#### `display_performance_summary()`
- **Purpose**: Display formatted console summary of performance data
- **Dependencies**: Calls `get_all_backtest_data()`
- **Side Effects**: Console output with headers, metadata, statistics, quarterly summary
- **Output Format**: Structured with headers, key metrics (return, std dev, Sharpe ratio)

### Actions:

#### Phase 1: Deep Analysis (COMPLETED ✅)
1. **✅ STUDIED `src/history_parser.py` COMPLETELY**:
   - ✅ Analyzed all 4 functions with exact signatures and return types
   - ✅ Mapped dependencies: csv, json, os, config.UNCLE_STOCK_SCREENS
   - ✅ Documented side effects: universe.json updates, console output patterns
   - ✅ Identified CSV parsing logic: metadata (lines 1-13), statistics headers, quarterly data extraction
   - ✅ Documented error handling: file not found, parsing exceptions, graceful error objects

#### Phase 2: Implementation (READY TO START)
2. **Create interface**: `IHistoricalDataService` in `services/interfaces.py`
3. **Create implementation**: `HistoricalDataService` wrapping existing functions
4. **Create API endpoints**:
   - `POST /api/v1/universe/history/update` → `update_universe_with_history()`
   - `GET /api/v1/screeners/backtest` → `get_all_backtest_data()`
   - `GET /api/v1/screeners/backtest/{screener_id}` → `parse_backtest_csv()`
   - `GET /api/v1/universe/history/summary` → `display_performance_summary()` (formatted JSON)
5. **Test CLI**: `python main.py 3` produces identical universe.json with history
6. **Test API**: Historical data matches CLI processing exactly

**⚠️ TESTING REQUIREMENTS:**
- **Activate virtual environment FIRST**: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)
- **Save ALL tests in**: `backend\app\tests\` directory
- **Run tests with**: `pytest backend/app/tests/` from project root
- **🚨 MANDATORY**: ALL tests must pass 100% before step validation

**Acceptance Criteria**:
- CLI `step3_parse_history()` behavior unchanged
- Identical `historical_performance` section structure in universe.json
- Same quarterly data parsing and statistics calculation (avg returns, std dev)
- Same console output patterns (`+` success, `X` error messages)
- Same CSV path resolution and name sanitization logic
- Same error handling for missing files and parsing failures

**Status**: 🔄 Analysis Complete - Ready for Implementation

---

## Step 4: Portfolio Optimization Service
**Goal**: Wrap `src/portfolio_optimizer.py` functions with API endpoints

### Current Functions:
- `load_universe_data()` - Load universe.json
- `extract_quarterly_returns()` - Extract returns DataFrame
- `optimize_portfolio()` - Run Sharpe ratio optimization
- `update_universe_with_portfolio()` - Add optimization results to universe.json

### Actions:

#### Phase 1: Deep Analysis (MANDATORY FIRST)
1. **📖 STUDY `src/portfolio_optimizer.py` COMPLETELY**:
   - Read every line, understand every function and scientific computing logic
   - Document exact function signatures, parameters, and return types
   - Map all dependencies: numpy, pandas, scipy.optimize imports
   - Note all side effects: universe.json updates, console output
   - Identify optimization algorithms and mathematical formulas
   - **UPDATE THIS PLAN** with exact implementation details

#### Phase 2: Implementation (ONLY AFTER ANALYSIS)
2. **Create interface**: `IPortfolioOptimizer`
3. **Create implementation**: `PortfolioOptimizerService` wrapping existing functions
4. **Create API endpoints**:
   - `POST /api/v1/portfolio/optimize` → `optimize_portfolio()`
   - `GET /api/v1/portfolio/optimization` → Get optimization results from universe.json
   - `GET /api/v1/portfolio/returns` → `extract_quarterly_returns()`
5. **Test CLI**: `python main.py 4` produces identical optimization results
6. **Test API**: Portfolio allocations match CLI output exactly

**⚠️ TESTING REQUIREMENTS:**
- **Activate virtual environment FIRST**: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)
- **Save ALL tests in**: `backend\app\tests\` directory
- **Run tests with**: `pytest backend/app/tests/` from project root
- **🚨 MANDATORY**: ALL tests must pass 100% before step validation

**Acceptance Criteria**:
- CLI `step4_optimize_portfolio()` behavior unchanged
- Identical portfolio_optimization section in universe.json
- Same optimal weights and Sharpe ratio calculations
- Same correlation matrix and individual stats

**Status**: ⏸️ Not Started

---

## Step 5: Currency Exchange Service
**Goal**: Wrap `src/currency.py` functions with API endpoints

### Current Functions:
- `fetch_exchange_rates()` - Get rates from exchangerate-api.com
- `get_currencies_from_universe()` - Extract currencies from universe
- `update_universe_with_exchange_rates()` - Add EUR rates to stocks

### Actions:

#### Phase 1: Deep Analysis (MANDATORY FIRST)
1. **📖 STUDY `src/currency.py` COMPLETELY**:
   - Read every line, understand every function and API calls
   - Document exact function signatures, parameters, and return types
   - Map all dependencies: requests, json imports, external API
   - Note all side effects: universe.json updates, console output
   - Identify API endpoints, timeout values, and error handling
   - **UPDATE THIS PLAN** with exact implementation details

#### Phase 2: Implementation (ONLY AFTER ANALYSIS)
2. **Create interface**: `ICurrencyService`
3. **Create implementation**: `CurrencyService` wrapping existing functions
4. **Create API endpoints**:
   - `POST /api/v1/currency/update` → `main()` function
   - `GET /api/v1/currency/rates` → `fetch_exchange_rates()`
   - `GET /api/v1/universe/currencies` → `get_currencies_from_universe()`
5. **Test CLI**: `python main.py 5` produces identical exchange rate updates
6. **Test API**: Currency data matches CLI processing exactly

**⚠️ TESTING REQUIREMENTS:**
- **Activate virtual environment FIRST**: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)
- **Save ALL tests in**: `backend\app\tests\` directory
- **Run tests with**: `pytest backend/app/tests/` from project root
- **🚨 MANDATORY**: ALL tests must pass 100% before step validation

**Acceptance Criteria**:
- CLI `step5_update_currency()` behavior unchanged
- Identical eur_exchange_rate fields added to all stocks
- Same exchange rate API calls and responses
- Same console output for currency processing

**Status**: ⏸️ Not Started

---

## Step 6: Target Allocation Service
**Goal**: Wrap `src/targetter.py` functions with API endpoints

### Current Functions:
- `extract_screener_allocations()` - Get optimizer results
- `rank_stocks_in_screener()` - Rank by 180d performance
- `calculate_pocket_allocation()` - Calculate allocation by rank
- `calculate_final_allocations()` - Final stock allocations

### Actions:

#### Phase 1: Deep Analysis (MANDATORY FIRST)
1. **📖 STUDY `src/targetter.py` COMPLETELY**:
   - Read every line, understand every function and allocation logic
   - Document exact function signatures, parameters, and return types
   - Map all dependencies: config imports, mathematical calculations
   - Note all side effects: universe.json updates, console output
   - Identify ranking algorithms and allocation formulas
   - **UPDATE THIS PLAN** with exact implementation details

#### Phase 2: Implementation (ONLY AFTER ANALYSIS)
2. **Create interface**: `ITargetAllocationService`
3. **Create implementation**: `TargetAllocationService` wrapping existing functions
4. **Create API endpoints**:
   - `POST /api/v1/portfolio/targets/calculate` → `calculate_final_allocations()`
   - `GET /api/v1/portfolio/targets` → Get final allocations from universe.json
   - `GET /api/v1/portfolio/rankings` → Stock rankings by screener
5. **Test CLI**: `python main.py 6` produces identical target allocations
6. **Test API**: Target calculations match CLI output exactly

**⚠️ TESTING REQUIREMENTS:**
- **Activate virtual environment FIRST**: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)
- **Save ALL tests in**: `backend\app\tests\` directory
- **Run tests with**: `pytest backend/app/tests/` from project root
- **🚨 MANDATORY**: ALL tests must pass 100% before step validation

**Acceptance Criteria**:
- CLI `step6_calculate_targets()` behavior unchanged
- Identical final_target, rank, and allocation fields in universe.json
- Same ranking logic and pocket allocation calculations
- Same console output for allocation summary

**Status**: ⏸️ Not Started

---

## Step 7: Quantity Calculation Service
**Goal**: Wrap `src/qty.py` functions with API endpoints

### Current Functions:
- `get_account_total_value()` - Fetch from IBKR
- `calculate_stock_quantities()` - Calculate quantities from account value
- `calculate_stock_fields()` - Calculate EUR price, target value, quantity

### Actions:

#### Phase 1: Deep Analysis (MANDATORY FIRST)
1. **📖 STUDY `src/qty.py` COMPLETELY**:
   - Read every line, understand every function and IBKR integration
   - Document exact function signatures, parameters, and return types
   - Map all dependencies: ib_utils imports, threading, time
   - Note all side effects: universe.json updates, IBKR connections
   - Identify IBKR API calls, connection logic, and quantity calculations
   - **UPDATE THIS PLAN** with exact implementation details

#### Phase 2: Implementation (ONLY AFTER ANALYSIS)
2. **Create interface**: `IAccountService` and `IQuantityCalculator`
3. **Create implementation**: `AccountService` and `QuantityService` wrapping existing functions
4. **Create API endpoints**:
   - `GET /api/v1/account/value` → `get_account_total_value()`
   - `POST /api/v1/portfolio/quantities/calculate` → `calculate_stock_quantities()`
   - `GET /api/v1/portfolio/quantities` → Get quantity data from universe.json
5. **Test CLI**: `python main.py 7` produces identical quantity calculations
6. **Test API**: Account value and quantities match CLI exactly

**⚠️ TESTING REQUIREMENTS:**
- **Activate virtual environment FIRST**: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)
- **Save ALL tests in**: `backend\app\tests\` directory
- **Run tests with**: `pytest backend/app/tests/` from project root
- **🚨 MANDATORY**: ALL tests must pass 100% before step validation

**Acceptance Criteria**:
- CLI `step7_calculate_quantities()` behavior unchanged
- Identical account_total_value section in universe.json
- Same EUR price, target value, and quantity calculations
- Same Japanese stock lot size handling (100 shares)

**Status**: ⏸️ Not Started

---

## Step 8: IBKR Search Service
**Goal**: Wrap `src/comprehensive_enhanced_search.py` functions with API endpoints

### ⚠️ **CRITICAL PERFORMANCE ISSUE**
The current implementation searches stocks **one by one** in IBKR, resulting in **30+ minute runtimes** for large universes. This step MUST include performance optimization analysis and implementation.

### Current Functions:
- `process_all_universe_stocks()` - Search all stocks on IBKR (EXTREMELY SLOW)
- Search and identification logic for IBKR instruments

### Actions:

#### Phase 1: Deep Analysis (MANDATORY FIRST)
1. **📖 STUDY `src/comprehensive_enhanced_search.py` COMPLETELY**:
   - Read every line, understand every function and IBKR search logic
   - Document exact function signatures, parameters, and return types
   - Map all dependencies: IBKR API imports, search algorithms
   - Note all side effects: universe files creation, console output
   - Identify search patterns, instrument matching, and data structures
   - **ANALYZE PERFORMANCE BOTTLENECKS**: Document why searches are slow
   - **RESEARCH OPTIMIZATION OPTIONS**: Investigate IBKR API batch capabilities
   - **UPDATE THIS PLAN** with exact implementation details and optimization strategy

#### Phase 2: Performance Optimization Research (MANDATORY)
2. **Investigate IBKR API batch capabilities**:
   - Research if IBKR API supports batch symbol lookup
   - Analyze concurrent search possibilities (threading/asyncio)
   - Investigate caching strategies for previously searched symbols
   - Document rate limiting constraints and connection pooling options
   - **GOAL**: Reduce 30-minute runtime to under 5 minutes

#### Phase 3: Implementation (ONLY AFTER ANALYSIS & OPTIMIZATION RESEARCH)
3. **Create interface**: `IBrokerageSearchService` with performance considerations
4. **Create optimized implementation**: `IBKRSearchService` with:
   - Batch processing where possible
   - Concurrent search implementation (if safe with IBKR API)
   - Symbol caching mechanism
   - Progress tracking for long-running operations
   - Async endpoints for non-blocking operations
5. **Create API endpoints**:
   - `POST /api/v1/ibkr/search/all` → Optimized `process_all_universe_stocks()`
   - `POST /api/v1/ibkr/search/batch` → Batch search multiple stocks
   - `POST /api/v1/ibkr/search/stocks` → Search specific stocks
   - `GET /api/v1/ibkr/search/results` → Get search results
   - `GET /api/v1/ibkr/search/progress/{task_id}` → Get search progress
   - `GET /api/v1/ibkr/search/cache/stats` → Get cache statistics

#### Phase 4: Performance Testing & Validation
6. **Benchmark original vs optimized implementation**:
   - Measure search time for 50, 100, 200+ stocks
   - Document performance improvements achieved
   - Verify search accuracy remains 100% identical
7. **Test CLI**: `python main.py 8` produces identical IBKR search results
8. **Test API**: Search results match CLI processing exactly
9. **Load testing**: Validate API can handle multiple concurrent search requests

**⚠️ TESTING REQUIREMENTS:**
- **Activate virtual environment FIRST**: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)
- **Save ALL tests in**: `backend\app\tests\` directory
- **Run tests with**: `pytest backend/app/tests/` from project root
- **🚨 MANDATORY**: ALL tests must pass 100% before step validation

**Acceptance Criteria**:
- CLI `step8_ibkr_search()` behavior unchanged
- Identical IBKR identification details added to stocks
- Same universe_with_ibkr.json file created
- Same search logic and instrument matching
- **PERFORMANCE REQUIREMENT**: Reduce search time from 30+ minutes to under 5 minutes
- **API ENHANCEMENT**: Provide async endpoints with progress tracking
- **CACHING**: Implement symbol caching to avoid repeated searches
- **RELIABILITY**: Handle IBKR API failures gracefully with retry logic

**Status**: ⏸️ Not Started

---

## Step 9: Rebalancing Orders Service
**Goal**: Wrap `src/rebalancer.py` functions with API endpoints

### Current Functions:
- `main()` - Generate rebalancing orders
- Order generation logic based on target quantities vs current positions

### Actions:

#### Phase 1: Deep Analysis (MANDATORY FIRST)
1. **📖 STUDY `src/rebalancer.py` COMPLETELY**:
   - Read every line, understand every function and rebalancing logic
   - Document exact function signatures, parameters, and return types
   - Map all dependencies: order generation algorithms
   - Note all side effects: orders.json creation, console output
   - Identify buy/sell/hold decision logic and order calculations
   - **UPDATE THIS PLAN** with exact implementation details

#### Phase 2: Implementation (ONLY AFTER ANALYSIS)
2. **Create interface**: `IRebalancingService`
3. **Create implementation**: `RebalancingService` wrapping existing functions
4. **Create API endpoints**:
   - `POST /api/v1/orders/generate` → `main()` function
   - `GET /api/v1/orders` → Get generated orders from orders.json
   - `GET /api/v1/orders/preview` → Preview orders without saving
5. **Test CLI**: `python main.py 9` produces identical rebalancing orders
6. **Test API**: Order generation matches CLI exactly

**⚠️ TESTING REQUIREMENTS:**
- **Activate virtual environment FIRST**: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)
- **Save ALL tests in**: `backend\app\tests\` directory
- **Run tests with**: `pytest backend/app/tests/` from project root
- **🚨 MANDATORY**: ALL tests must pass 100% before step validation

**Acceptance Criteria**:
- CLI `step9_rebalancer()` behavior unchanged
- Identical data/orders.json file created
- Same order calculation logic for buy/sell/hold decisions
- Same console output for rebalancing summary

**Status**: ⏸️ Not Started

---

## Step 10: Order Execution Service
**Goal**: Wrap `src/order_executor.py` functions with API endpoints

### Current Functions:
- `main()` - Execute orders through IBKR API
- Order execution and confirmation logic

### Actions:

#### Phase 1: Deep Analysis (MANDATORY FIRST)
1. **📖 STUDY `src/order_executor.py` COMPLETELY**:
   - Read every line, understand every function and execution logic
   - Document exact function signatures, parameters, and return types
   - Map all dependencies: IBKR API imports, order submission
   - Note all side effects: IBKR order submissions, console output
   - Identify execution patterns, error handling, and confirmation logic
   - **UPDATE THIS PLAN** with exact implementation details

#### Phase 2: Implementation (ONLY AFTER ANALYSIS)
2. **Create interface**: `IOrderExecutionService`
3. **Create implementation**: `OrderExecutionService` wrapping existing functions
4. **Create API endpoints**:
   - `POST /api/v1/orders/execute` → `main()` function
   - `GET /api/v1/orders/execution/status` → Get execution status
   - `POST /api/v1/orders/execute/preview` → Dry run execution
5. **Test CLI**: `python main.py 10` produces identical order execution
6. **Test API**: Execution results match CLI exactly

**⚠️ TESTING REQUIREMENTS:**
- **Activate virtual environment FIRST**: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)
- **Save ALL tests in**: `backend\app\tests\` directory
- **Run tests with**: `pytest backend/app/tests/` from project root
- **🚨 MANDATORY**: ALL tests must pass 100% before step validation

**Acceptance Criteria**:
- CLI `step10_execute_orders()` behavior unchanged
- Same IBKR API calls and order submissions
- Same execution confirmation and error handling
- Same console output for execution results

**Status**: ⏸️ Not Started

---

## Step 11: Order Status Checking Service
**Goal**: Wrap `src/order_status_checker.py` functions with API endpoints

### Current Functions:
- `main()` - Check order status and verify execution
- Status checking and verification logic

### Actions:

#### Phase 1: Deep Analysis (MANDATORY FIRST)
1. **📖 STUDY `src/order_status_checker.py` COMPLETELY**:
   - Read every line, understand every function and status checking logic
   - Document exact function signatures, parameters, and return types
   - Map all dependencies: IBKR API imports, status verification
   - Note all side effects: status reports, console output
   - Identify verification patterns, comparison logic, and reporting
   - **UPDATE THIS PLAN** with exact implementation details

#### Phase 2: Implementation (ONLY AFTER ANALYSIS)
2. **Create interface**: `IOrderStatusService`
3. **Create implementation**: `OrderStatusService` wrapping existing functions
4. **Create API endpoints**:
   - `POST /api/v1/orders/status/check` → `main()` function
   - `GET /api/v1/orders/status` → Get current order status
   - `GET /api/v1/orders/verification` → Get verification results
5. **Test CLI**: `python main.py 11` produces identical status checking
6. **Test API**: Status checking matches CLI exactly

**⚠️ TESTING REQUIREMENTS:**
- **Activate virtual environment FIRST**: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)
- **Save ALL tests in**: `backend\app\tests\` directory
- **Run tests with**: `pytest backend/app/tests/` from project root
- **🚨 MANDATORY**: ALL tests must pass 100% before step validation

**Acceptance Criteria**:
- CLI `step11_check_order_status()` behavior unchanged
- Same order status verification logic
- Same comparison with orders.json
- Same console output for status summary

**Status**: ⏸️ Not Started

---

## Step 12: Pipeline Orchestration Service
**Goal**: Create unified pipeline API that orchestrates all steps

### Actions:
1. **Create interface**: `IPipelineOrchestrator`
2. **Create implementation**: `PipelineService` that calls all step services
3. **Create API endpoints**:
   - `POST /api/v1/pipeline/run` → Run full pipeline (like `run_all_steps()`)
   - `POST /api/v1/pipeline/run/{step_number}` → Run individual step
   - `GET /api/v1/pipeline/status/{run_id}` → Get pipeline execution status
   - `GET /api/v1/pipeline/history` → Get execution history
4. **Add async execution** with status tracking
5. **Add error recovery** and resume functionality
6. **Test**: Full pipeline API produces identical results to CLI

**⚠️ TESTING REQUIREMENTS:**
- **Activate virtual environment FIRST**: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)
- **Save ALL tests in**: `backend\app\tests\` directory
- **Run tests with**: `pytest backend/app/tests/` from project root
- **🚨 MANDATORY**: ALL tests must pass 100% before step validation

**Acceptance Criteria**:
- API pipeline execution produces identical file outputs to CLI
- Same error handling and stopping behavior
- Same console-equivalent logging
- Original CLI `main.py` still works unchanged

**Status**: ⏸️ Not Started

---

## Enhanced Architecture Components

### Configuration Management

Each service will have dedicated configuration following the pattern:

```python
# backend/app/core/config.py
from pydantic import BaseSettings
from typing import Optional

class BaseServiceSettings(BaseSettings):
    """Base configuration for all services"""
    log_level: str = "INFO"
    environment: str = "development"
    debug: bool = False

class UncleStockSettings(BaseServiceSettings):
    uncle_stock_user_id: str
    uncle_stock_timeout: int = 60
    retry_attempts: int = 3
    max_results_per_screener: int = 200

    class Config:
        env_prefix = "UNCLE_STOCK_"

class IBKRSettings(BaseServiceSettings):
    ibkr_host: str = "127.0.0.1"
    ibkr_port: int = 4002
    ibkr_client_id: int = 1
    connection_timeout: int = 10

    class Config:
        env_prefix = "IBKR_"

class PortfolioSettings(BaseServiceSettings):
    max_ranked_stocks: int = 30
    max_allocation: float = 0.10
    min_allocation: float = 0.01
    risk_free_rate: float = 0.02

    class Config:
        env_prefix = "PORTFOLIO_"
```

### Error Handling Framework

Structured error handling across all services:

```python
# backend/app/core/exceptions.py
from typing import Optional, Dict, Any
from fastapi import HTTPException

class BaseServiceError(Exception):
    """Base exception for all service errors"""
    def __init__(self, message: str, error_code: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class ExternalAPIError(BaseServiceError):
    """Base for external API errors"""
    pass

class UncleStockAPIError(ExternalAPIError):
    """Uncle Stock API specific errors"""
    pass

class IBKRError(ExternalAPIError):
    """IBKR API specific errors"""
    pass

class ValidationError(BaseServiceError):
    """Data validation errors"""
    pass

class ConfigurationError(BaseServiceError):
    """Configuration and setup errors"""
    pass

# backend/app/models/errors.py
from pydantic import BaseModel
from typing import Optional, Dict, Any

class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    retry_after: Optional[int] = None
    timestamp: str
    request_id: Optional[str] = None

class ValidationErrorDetail(BaseModel):
    field: str
    message: str
    invalid_value: Any

class ValidationErrorResponse(ErrorResponse):
    validation_errors: List[ValidationErrorDetail]
```

### Middleware Setup

```python
# backend/app/core/middleware.py
import uuid
import time
import logging
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.time()

        logger.info("Request started", extra={
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "user_agent": request.headers.get("user-agent")
        })

        response = await call_next(request)

        process_time = time.time() - start_time

        logger.info("Request completed", extra={
            "request_id": request_id,
            "status_code": response.status_code,
            "process_time": process_time
        })

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)

        return response
```

## Testing Strategy

### Test Structure

```
backend/app/tests/
├── conftest.py                 # Shared test configuration
├── unit/                       # Unit tests (isolated)
│   ├── services/
│   │   ├── test_uncle_stock_service.py
│   │   ├── test_portfolio_service.py
│   │   └── test_ibkr_service.py
│   └── utils/
├── integration/                # Integration tests (with dependencies)
│   ├── test_api_endpoints.py
│   ├── test_service_integration.py
│   └── test_database_operations.py
├── behavior/                   # CLI vs API behavior verification
│   ├── test_cli_api_equivalence.py
│   └── test_file_output_comparison.py
└── performance/                # Performance tests
    ├── test_api_latency.py
    └── test_memory_usage.py
```

### Test Configuration

```python
# backend/app/tests/conftest.py
import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock
from backend.app.main import app
from backend.app.core.config import Settings

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture
def mock_uncle_stock_api():
    mock = AsyncMock()
    mock.fetch_screener_data.return_value = {
        "success": True,
        "data": ["AAPL", "GOOGL", "MSFT"],
        "csv_file": "test_screener.csv"
    }
    return mock

@pytest.fixture
def test_settings():
    return Settings(
        uncle_stock_user_id="test_user",
        uncle_stock_timeout=30,
        environment="test"
    )

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
```

### For Each Step:

1. **Deep Code Analysis Phase**:
   - Read and analyze the current implementation file completely
   - Document all functions, their inputs, outputs, and side effects
   - Map all dependencies, imports, and external calls
   - Identify all file I/O operations and data transformations
   - Note error handling patterns and console output
   - Update the step plan in API_MIGRATION_PLAN.md to reflect exact current implementation
   - **CRITICAL**: Plan must match reality before proceeding

2. **Behavior Verification**:
   - Run CLI step before changes
   - Capture all outputs (files, console, data structures)
   - Run CLI step after changes
   - Verify 100% identical outputs

3. **API Verification**:
   - Call API endpoint
   - Verify response matches CLI function output
   - Verify same side effects (files created, data updated)

4. **Integration Testing**:
   - Run full CLI pipeline after each step
   - Verify end-to-end pipeline still works
   - Check no regression in any previous steps

### Test Artifacts:
- Console output comparisons
- File content diffs (universe.json, orders.json, CSVs)
- Data structure comparisons (JSON schema validation)

---

## Success Criteria

✅ **Zero Breaking Changes**: Original CLI works exactly as before
✅ **API Functionality**: All endpoints return correct data
✅ **File Compatibility**: Same JSON/CSV files created
✅ **Error Handling**: Same error conditions and messages
✅ **Performance**: No significant performance degradation
✅ **React Ready**: Frontend can consume all necessary APIs

---

## Progress Tracking

- [ ] Step 0: Repository Structure & Organization
- [ ] Step 1: Data Fetching Service (Uncle Stock API)
- [ ] Step 2: Data Parsing Service
- [ ] Step 3: Historical Data Service
- [ ] Step 4: Portfolio Optimization Service
- [ ] Step 5: Currency Exchange Service
- [ ] Step 6: Target Allocation Service
- [ ] Step 7: Quantity Calculation Service
- [ ] Step 8: IBKR Search Service ⚠️ **CRITICAL**: Performance optimization required (30min → <5min)
- [ ] Step 9: Rebalancing Orders Service
- [ ] Step 10: Order Execution Service
- [ ] Step 11: Order Status Checking Service
- [ ] Step 12: Pipeline Orchestration Service

**Current Status**: ⏸️ Ready to Begin Step 0

---

## 🚨 CRITICAL IMPLEMENTATION RULE

### **ANALYSIS-FIRST MANDATORY PROCESS**

For **EVERY STEP**, you must:

1. **📖 DEEP CODE STUDY FIRST** - Completely read and understand the current implementation
2. **📝 UPDATE THE PLAN** - Modify this document to reflect the exact current implementation
3. **✅ PLAN APPROVAL** - Ensure the plan matches reality 100% before proceeding
4. **🔧 IMPLEMENTATION** - Only then create the API layer
5. **🧪 TESTING VALIDATION** - ALL tests must pass 100% before step completion

### **WHY THIS MATTERS:**
- **No Assumptions** - Plans based on reality, not guesswork
- **Zero Surprises** - All edge cases and dependencies identified upfront
- **Perfect Compatibility** - API behavior matches CLI exactly
- **Maintainable Code** - Proper interfaces based on actual requirements
- **Quality Assurance** - 100% test pass rate ensures reliable, production-ready code

### **WORKFLOW:**
```
Current Code → Deep Analysis → Plan Update → Implementation → Testing → 100% PASS VALIDATION
```

**Never skip the analysis phase. Ever.**

---

## Dependencies & Requirements

### Core Dependencies
```txt
# backend/requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
httpx==0.25.2
python-multipart==0.0.6

# Data & Scientific Computing
numpy==1.25.2
pandas==2.1.3
scipy==1.11.4

# External APIs
requests==2.31.0
python-dotenv==1.0.0

# File Processing
openpyxl==3.1.2
```

### Development Dependencies
```txt
# backend/requirements-dev.txt
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0
httpx==0.25.2  # For testing async clients
factory-boy==3.3.0  # Test data factories

# Code Quality
black==23.11.0
isort==5.12.0
flake8==6.1.0
mypy==1.7.1

# Documentation
mkdocs==1.5.3
mkdocs-material==9.4.8
```

### Test Configuration
```ini
# backend/pytest.ini
[tool:pytest]
testpaths = backend/app/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --cov=backend/app
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=80
asyncio_mode = auto
markers =
    unit: Unit tests
    integration: Integration tests
    behavior: CLI vs API behavior tests
    slow: Slow tests
    external_api: Tests that call external APIs
```

### Environment Template
```bash
# .env.example
# Uncle Stock API Configuration
UNCLE_STOCK_USER_ID=your_user_id_here
UNCLE_STOCK_TIMEOUT=60
UNCLE_STOCK_RETRY_ATTEMPTS=3
UNCLE_STOCK_MAX_RESULTS_PER_SCREENER=200

# IBKR Configuration
IBKR_HOST=127.0.0.1
IBKR_PORT=4002
IBKR_CLIENT_ID=1
IBKR_CONNECTION_TIMEOUT=10

# Portfolio Configuration
PORTFOLIO_MAX_RANKED_STOCKS=30
PORTFOLIO_MAX_ALLOCATION=0.10
PORTFOLIO_MIN_ALLOCATION=0.01
PORTFOLIO_RISK_FREE_RATE=0.02

# Application Configuration
LOG_LEVEL=INFO
ENVIRONMENT=development
DEBUG=false

# File Paths
DATA_DIRECTORY=./data
EXPORTS_DIRECTORY=./data/files_exports
```

## Documentation Requirements

### API Documentation
Each endpoint must include:
- **OpenAPI/Swagger documentation**
- **Request/Response examples**
- **Error response examples**
- **Rate limiting information**
- **Authentication requirements**

### Service Documentation
Each service must include:
- **Interface documentation**
- **Configuration options**
- **Error handling guide**
- **Testing examples**
- **Performance characteristics**

### Migration Documentation
- **CLI to API mapping guide**
- **Breaking changes log**
- **Migration timeline**
- **Rollback procedures**

## Performance Standards

### Response Time Targets
- **API endpoints**: < 2 seconds (95th percentile)
- **CLI compatibility**: No more than 10% slower than original
- **Memory usage**: No more than 50MB increase per request
- **File operations**: Identical to current implementation

### Monitoring Requirements
- **Request/response logging**
- **Error rate tracking**
- **Performance metrics**
- **External API status monitoring**
- **Resource usage monitoring**

---

## Notes

- Each step is independent and can be completed in 1-2 days
- CLI functionality is preserved throughout the entire migration
- API endpoints are additive - no existing code is modified
- Interface-First Design ensures flexibility for future implementations
- React frontend can start development as soon as Step 1 is completed