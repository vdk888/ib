# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the **Uncle Stock Portfolio System** - a comprehensive financial portfolio management platform that combines data screening, portfolio optimization, and automated trading execution. The system is undergoing active migration from a monolithic CLI pipeline to a modern API-first architecture.

### Core Architecture

The codebase has two main execution environments:

1. **Legacy CLI Pipeline** (`main.py` + `src/` modules) - Original 11-step monolithic workflow
2. **Modern API Backend** (`backend/` directory) - FastAPI-based microservices architecture

Both systems maintain **100% behavioral compatibility** during the migration phase.

## Development Commands

### Environment Setup
```bash
# Install dependencies for CLI pipeline
pip install -r requirements.txt

# Install dependencies for API backend
cd backend && pip install -r requirements.txt
```

### Running the System

#### CLI Pipeline (Legacy)
```bash
# Run complete pipeline (all 11 steps)
python main.py

# Run individual steps
python main.py 1          # Fetch data from screeners
python main.py parse      # Parse CSV files and create universe.json
python main.py portfolio  # Optimize portfolio allocations
python main.py ibkr       # Search stocks on Interactive Brokers
python main.py execute    # Execute trading orders

# Get help with available commands
python main.py help
```

#### API Backend (Modern)
```bash
# Start development server
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Access API documentation
# Swagger UI: http://127.0.0.1:8000/docs
# ReDoc: http://127.0.0.1:8000/redoc
```

#### Docker Deployment
```bash
# Basic deployment
docker-compose up -d

# With Redis caching
docker-compose --profile with-redis up -d

# Full production setup with proxy
docker-compose --profile with-redis --profile with-proxy up -d
```

### Testing Commands
```bash
# Run tests for legacy components
pytest

# Test API endpoints (when available)
cd backend && pytest

# Test specific pipeline step
python main.py <step_number>
```

### Linting and Code Quality
```bash
# Format code
black .

# Lint code
flake8 .
```

## Data Pipeline Architecture

### 11-Step Pipeline Flow
The system follows a sequential 11-step process for portfolio management:

1. **Data Fetching** - Retrieve stock data from Uncle Stock API screeners
2. **Data Parsing** - Process CSV files and create `universe.json`
3. **Historical Analysis** - Parse backtest performance data
4. **Portfolio Optimization** - Apply Sharpe ratio maximization
5. **Currency Conversion** - Update EUR exchange rates
6. **Target Calculation** - Calculate stock allocations
7. **Quantity Calculation** - Get IBKR account value and calculate quantities
8. **IBKR Search** - Match stocks with Interactive Brokers symbols
9. **Order Generation** - Create rebalancing orders
10. **Order Execution** - Execute trades through IBKR API
11. **Status Verification** - Verify order execution and results

### Key Data Files
- `data/universe.json` - Central stock universe with allocations
- `data/universe_with_ibkr.json` - Universe with IBKR symbol mappings
- `data/orders.json` - Generated trading orders
- `data/files_exports/` - CSV exports from screeners

## Configuration Management

### Environment Variables (.env)
```bash
UNCLE_STOCK_USER_ID=your_user_id    # Required for API access
IBKR_HOST=127.0.0.1                 # Interactive Brokers Gateway host
IBKR_PORT=4002                      # IB Gateway port (paper: 4002, live: 4001)
IBKR_CLIENT_ID=1                    # IB API client ID
```

### Portfolio Configuration (config.py)
- `MAX_RANKED_STOCKS=30` - Only top 30 stocks get allocation
- `MAX_ALLOCATION=0.10` - Maximum 10% allocation per stock
- `MIN_ALLOCATION=0.01` - Minimum 1% allocation for included stocks

## API Migration Status

The system is actively migrating to API-first architecture following the **Interface-First Design** methodology:

### Migration Principles
- **Zero Breaking Changes** - CLI functionality remains identical
- **Dual Operation** - Both CLI and API work simultaneously
- **Service-Oriented Design** - Each step becomes an independent service
- **Production-Ready** - Full error handling and monitoring

### Backend Structure
```
backend/
├── app/
│   ├── main.py                 # FastAPI entry point
│   ├── core/                   # Configuration, dependencies, middleware
│   ├── services/               # Business logic interfaces
│   │   └── implementations/    # Service implementations
│   ├── api/v1/endpoints/       # REST API endpoints (8 service areas)
│   ├── models/                 # Pydantic schemas and error models
│   └── tests/                  # API tests
```

### API Services Available
- **Screeners** (7 endpoints) - Stock data fetching
- **Historical** (4 endpoints) - Performance analysis
- **Universe** (12 endpoints) - Stock universe management
- **Portfolio** (10 endpoints) - Optimization and allocation
- **Orders** (11 endpoints) - Order management and execution
- **Pipeline** (8 endpoints) - Workflow orchestration
- **IBKR Search** (6 endpoints) - Interactive Brokers integration
- **Currency** (5 endpoints) - Exchange rate management

## Trading Integration

### Interactive Brokers Setup
The system integrates with Interactive Brokers (IBKR) for:
- Stock symbol resolution and validation
- Account balance retrieval
- Order placement and execution
- Position monitoring

**Requirements:**
- IB Gateway or TWS running locally
- Proper API configuration (ports 4001/4002)
- Valid IBKR account with API access enabled

### Risk Management
- Maximum 10% allocation per single stock
- Only top 30 ranked stocks receive allocation
- Portfolio rebalancing based on performance rankings
- Comprehensive order verification and status checking

## Development Guidelines

### When Working with Legacy Code (`src/` directory)
- Each module handles one step of the pipeline
- Functions maintain backwards compatibility
- All file I/O uses `data/` directory for persistence
- Error handling focuses on pipeline continuation

### When Working with API Backend (`backend/` directory)
- Follow FastAPI and Pydantic patterns
- Use dependency injection for service interfaces
- Implement proper HTTP status codes and error responses
- Maintain OpenAPI documentation completeness
- interface first, service based, scalable

### Code Patterns
- **Configuration**: Centralized in `config.py` with environment overrides
- **Data Processing**: Pandas-heavy workflows with JSON serialization
- **External APIs**: Requests-based with comprehensive error handling
- **Financial Calculations**: NumPy/SciPy for optimization algorithms
- **Trading**: ibapi for Interactive Brokers integration

## Troubleshooting Common Issues

### Pipeline Failures
1. Check `.env` file for required credentials
2. Verify IBKR Gateway is running and accessible
3. Ensure `data/` directory has proper write permissions
4. Check network connectivity for external API calls

### API Issues
1. Confirm FastAPI server is running on port 8000
2. Check logs for service-specific error details
3. Verify environment variables in Docker containers
4. Test individual endpoints using Swagger UI

### Trading Issues
1. Verify IBKR account permissions for API trading
2. Check client ID conflicts (each connection needs unique ID)
3. Confirm market hours for order execution
4. Review order status and rejection reasons in IBKR logs