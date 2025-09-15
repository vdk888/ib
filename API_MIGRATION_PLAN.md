# API Migration Plan: Monolith to API-First Architecture

## Overview
Transform the current 11-step monolithic pipeline into a scalable API-first architecture while maintaining **100% behavioral compatibility**. Each step will be thoroughly tested to ensure identical functionality.

## Migration Strategy
- ✅ **Zero Breaking Changes**: Existing CLI functionality remains identical
- ✅ **Interface-First Design**: Define contracts before implementation
- ✅ **Gradual Migration**: One step at a time with full testing
- ✅ **Dual Operation**: CLI and API work simultaneously during transition
- ✅ **Implementation-First Analysis**: Study current code deeply before any changes

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
   │   │   └── dependencies.py     # DI container
   │   ├── services/
   │   │   ├── __init__.py
   │   │   ├── interfaces.py       # Abstract interfaces
   │   │   └── implementations/
   │   │       └── __init__.py
   │   ├── api/
   │   │   ├── __init__.py
   │   │   └── v1/
   │   │       ├── __init__.py
   │   │       └── endpoints/
   │   │           └── __init__.py
   │   └── models/
   │       ├── __init__.py
   │       └── schemas.py          # Pydantic models
   ├── requirements.txt
   └── Dockerfile
   ```

2. **Move and organize existing files**:
   - Keep `main.py` in root (CLI interface)
   - Move `src/` files to `backend/app/services/implementations/legacy/`
   - Keep `config.py` in root, create new one in `backend/app/core/`

3. **Create initial FastAPI setup**
4. **Verify**: Original CLI still works exactly the same

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
2. **Create interface**: `IDataProvider` in `services/interfaces.py`
3. **Create implementation**: `UncleStockService` wrapping existing functions
4. **Create API endpoints**:
   - `GET /api/v1/screeners/data` → `get_all_screeners()`
   - `GET /api/v1/screeners/data/{screener_id}` → `get_current_stocks()`
   - `GET /api/v1/screeners/history` → `get_all_screener_histories()`
   - `GET /api/v1/screeners/history/{screener_id}` → `get_screener_history()`
5. **Create Pydantic models** for request/response
6. **Add error handling** and logging
7. **Test CLI**: `python main.py 1` produces identical results
8. **Test API**: Endpoints return same data as CLI functions

**Acceptance Criteria**:
- CLI `step1_fetch_data()` behavior unchanged
- API endpoints return identical data structure
- Same CSV files created in `data/files_exports/`
- Same console output and error messages

**Status**: ⏸️ Not Started

---

## Step 2: Data Parsing Service
**Goal**: Wrap `src/parser.py` functions with API endpoints

### Current Functions:
- `parse_screener_csv()` - Parse single CSV file
- `parse_screener_csv_flexible()` - Parse with additional fields
- `create_universe()` - Create universe from all CSVs
- `save_universe()` - Save universe.json
- `get_stock_field()` - Extract specific field from CSV

### Actions:

#### Phase 1: Deep Analysis (MANDATORY FIRST)
1. **📖 STUDY `src/parser.py` COMPLETELY**:
   - Read every line, understand every function and class
   - Document exact function signatures, parameters, and return types
   - Map all dependencies: csv, json, glob, config imports
   - Note all side effects: JSON file creation, console output
   - Identify error handling patterns and file operations
   - **UPDATE THIS PLAN** with exact implementation details

#### Phase 2: Implementation (ONLY AFTER ANALYSIS)
2. **Create interface**: `IUniverseRepository` and `IDataParser`
3. **Create implementation**: `UniverseService` wrapping existing functions
4. **Create API endpoints**:
   - `POST /api/v1/universe/parse` → `create_universe()` + `save_universe()`
   - `GET /api/v1/universe` → Load and return universe.json
   - `GET /api/v1/universe/stock/{ticker}/field` → `get_stock_field()`
5. **Test CLI**: `python main.py 2` produces identical universe.json
6. **Test API**: Universe data matches CLI output exactly

**Acceptance Criteria**:
- CLI `step2_parse_data()` behavior unchanged
- Identical `data/universe.json` file created
- Same metadata structure and stock counts
- Same console output for parsing results

**Status**: ⏸️ Not Started

---

## Step 3: Historical Data Service
**Goal**: Wrap `src/history_parser.py` functions with API endpoints

### Current Functions:
- `parse_backtest_csv()` - Parse backtest results CSV
- `get_all_backtest_data()` - Parse all backtest CSVs
- `update_universe_with_history()` - Add historical data to universe.json

### Actions:

#### Phase 1: Deep Analysis (MANDATORY FIRST)
1. **📖 STUDY `src/history_parser.py` COMPLETELY**:
   - Read every line, understand every function and type hints
   - Document exact function signatures, parameters, and return types
   - Map all dependencies: csv, json, typing imports
   - Note all side effects: universe.json updates, console output
   - Identify error handling patterns and CSV parsing logic
   - **UPDATE THIS PLAN** with exact implementation details

#### Phase 2: Implementation (ONLY AFTER ANALYSIS)
2. **Create interface**: `IHistoricalDataService`
3. **Create implementation**: `HistoricalDataService` wrapping existing functions
4. **Create API endpoints**:
   - `POST /api/v1/universe/history/update` → `update_universe_with_history()`
   - `GET /api/v1/screeners/backtest` → `get_all_backtest_data()`
   - `GET /api/v1/screeners/backtest/{screener_id}` → `parse_backtest_csv()`
5. **Test CLI**: `python main.py 3` produces identical universe.json with history
6. **Test API**: Historical data matches CLI processing exactly

**Acceptance Criteria**:
- CLI `step3_parse_history()` behavior unchanged
- Identical historical_performance section in universe.json
- Same quarterly data parsing and statistics calculation
- Same console output for performance summary

**Status**: ⏸️ Not Started

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

**Acceptance Criteria**:
- CLI `step7_calculate_quantities()` behavior unchanged
- Identical account_total_value section in universe.json
- Same EUR price, target value, and quantity calculations
- Same Japanese stock lot size handling (100 shares)

**Status**: ⏸️ Not Started

---

## Step 8: IBKR Search Service
**Goal**: Wrap `src/comprehensive_enhanced_search.py` functions with API endpoints

### Current Functions:
- `process_all_universe_stocks()` - Search all stocks on IBKR
- Search and identification logic for IBKR instruments

### Actions:

#### Phase 1: Deep Analysis (MANDATORY FIRST)
1. **📖 STUDY `src/comprehensive_enhanced_search.py` COMPLETELY**:
   - Read every line, understand every function and IBKR search logic
   - Document exact function signatures, parameters, and return types
   - Map all dependencies: IBKR API imports, search algorithms
   - Note all side effects: universe files creation, console output
   - Identify search patterns, instrument matching, and data structures
   - **UPDATE THIS PLAN** with exact implementation details

#### Phase 2: Implementation (ONLY AFTER ANALYSIS)
2. **Create interface**: `IBrokerageSearchService`
3. **Create implementation**: `IBKRSearchService` wrapping existing functions
4. **Create API endpoints**:
   - `POST /api/v1/ibkr/search/all` → `process_all_universe_stocks()`
   - `POST /api/v1/ibkr/search/stocks` → Search specific stocks
   - `GET /api/v1/ibkr/search/results` → Get search results
5. **Test CLI**: `python main.py 8` produces identical IBKR search results
6. **Test API**: Search results match CLI processing exactly

**Acceptance Criteria**:
- CLI `step8_ibkr_search()` behavior unchanged
- Identical IBKR identification details added to stocks
- Same universe_with_ibkr.json file created
- Same search logic and instrument matching

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

**Acceptance Criteria**:
- API pipeline execution produces identical file outputs to CLI
- Same error handling and stopping behavior
- Same console-equivalent logging
- Original CLI `main.py` still works unchanged

**Status**: ⏸️ Not Started

---

## Testing Strategy

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
- [ ] Step 8: IBKR Search Service
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

### **WHY THIS MATTERS:**
- **No Assumptions** - Plans based on reality, not guesswork
- **Zero Surprises** - All edge cases and dependencies identified upfront
- **Perfect Compatibility** - API behavior matches CLI exactly
- **Maintainable Code** - Proper interfaces based on actual requirements

### **WORKFLOW:**
```
Current Code → Deep Analysis → Plan Update → Implementation → Testing
```

**Never skip the analysis phase. Ever.**

---

## Notes

- Each step is independent and can be completed in 1-2 days
- CLI functionality is preserved throughout the entire migration
- API endpoints are additive - no existing code is modified
- Interface-First Design ensures flexibility for future implementations
- React frontend can start development as soon as Step 1 is completed