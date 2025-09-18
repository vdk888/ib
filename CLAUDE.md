# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the **Uncle Stock Portfolio System** - a comprehensive financial portfolio management platform that combines data screening, portfolio optimization, and automated trading execution. The system has **FULLY MIGRATED** from a legacy CLI pipeline to a modern API-first architecture.

### Core Architecture

**IMPORTANT UPDATE**: The repository now contains only the modern API backend implementation:

1. **Modern API Backend** (`backend/` directory) - FastAPI-based microservices architecture with complete functionality
2. **Legacy Implementation** - Available as `backend/app/services/implementations/legacy/` modules for reference only

**Note**: There is no longer a standalone `main.py` or `src/` directory - all functionality has been consolidated into the FastAPI backend with legacy code preserved in the implementations directory.

## Development Commands

### Environment Setup
```bash
# Install dependencies for root level utilities (optional)
pip install -r requirements.txt

# Install dependencies for API backend (primary)
cd backend && pip install -r requirements.txt
```

### Running the System

#### API Backend (Primary Method)
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
# Run tests for backend API
cd backend && pytest

# Run root level tests (if any)
pytest

# Test specific API endpoints using curl
curl -X GET "http://127.0.0.1:8000/health"
curl -X GET "http://127.0.0.1:8000/docs"
```

### Linting and Code Quality
```bash
# Format code
black .

# Lint code
flake8 .
```

## Data Pipeline Architecture

### API-Based Pipeline Flow
The system implements the traditional 11-step process through RESTful API endpoints:

1. **Data Fetching** - `/api/v1/screeners/*` - Retrieve stock data from Uncle Stock API screeners
2. **Data Parsing** - `/api/v1/universe/*` - Process CSV files and create `universe.json`
3. **Historical Analysis** - `/api/v1/historical/*` - Parse backtest performance data
4. **Portfolio Optimization** - `/api/v1/portfolio/*` - Apply Sharpe ratio maximization
5. **Currency Conversion** - `/api/v1/currency/*` - Update EUR exchange rates
6. **Target Calculation** - `/api/v1/portfolio/targets/*` - Calculate stock allocations
7. **Quantity Calculation** - `/api/v1/orders/quantities` - Get IBKR account value and calculate quantities
8. **IBKR Search** - `/api/v1/ibkr-search/*` - Match stocks with Interactive Brokers symbols
9. **Order Generation** - `/api/v1/orders/generate` - Create rebalancing orders
10. **Order Execution** - `/api/v1/orders/execute` - Execute trades through IBKR API
11. **Status Verification** - `/api/v1/orders/status` - Verify order execution and results

### Pipeline Orchestration
- `/api/v1/pipeline/*` - Workflow orchestration endpoints for running multiple steps

### Key Data Files
- `data/universe.json` - Central stock universe with allocations
- `backend/data/universe.json` - Backend copy of universe data
- `backend/data/universe_with_ibkr.json` - Universe with IBKR symbol mappings
- `backend/data/orders.json` - Generated trading orders
- `data/files_exports/` - CSV exports from screeners

## Configuration Management

### Environment Variables (.env)
```bash
UNCLE_STOCK_USER_ID=your_user_id    # Required for API access
IBKR_HOST=127.0.0.1                 # Interactive Brokers Gateway host
IBKR_PORT=4002                      # IB Gateway port (paper: 4002, live: 4001)
IBKR_CLIENT_ID=1                    # IB API client ID

# Additional environment variables found in repository:
TELEGRAM_BOT_TOKEN=token            # Telegram notifications
TELEGRAM_CHAT_ID=chat_id            # Telegram chat ID
TELEGRAM_ENABLED=true               # Enable Telegram notifications
LOG_LEVEL=INFO                      # Logging level
ENVIRONMENT=development             # Environment (development/production)
DEBUG=false                         # Debug mode
```

### Portfolio Configuration (config.py)
- `MAX_RANKED_STOCKS=30` - Only top 30 stocks get allocation
- `MAX_ALLOCATION=0.10` - Maximum 10% allocation per stock
- `MIN_ALLOCATION=0.01` - Minimum 1% allocation for included stocks
- `PORTFOLIO_MAX_RANKED_STOCKS` - Environment variable override
- `PORTFOLIO_MAX_ALLOCATION` - Environment variable override

## API Implementation Status

The system has **COMPLETED MIGRATION** to API-first architecture following the **Interface-First Design** methodology:

### Migration Principles (Achieved)
- **Complete API Coverage** - All 11 pipeline steps available as API endpoints
- **Service-Oriented Design** - Each step implemented as independent service
- **Production-Ready** - Full error handling, monitoring, and Docker deployment
- **Legacy Preservation** - Original implementations preserved in `backend/app/services/implementations/legacy/`

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
- **Screeners** (`/api/v1/screeners/*`) - Stock data fetching from Uncle Stock API
- **Historical** (`/api/v1/historical/*`) - Performance analysis and backtesting data
- **Universe** (`/api/v1/universe/*`) - Stock universe management and processing
- **Portfolio** (`/api/v1/portfolio/*`) - Optimization and allocation calculations
- **Target Allocation** (`/api/v1/portfolio/targets/*`) - Specific target calculation endpoints
- **Orders** (`/api/v1/orders/*`) - Order management and execution
- **Pipeline** (`/api/v1/pipeline/*`) - Workflow orchestration and automation
- **IBKR Search** (`/api/v1/ibkr-search/*`) - Interactive Brokers integration
- **Currency** (`/api/v1/currency/*`) - Exchange rate management

### Additional Features
- **Health Check** (`/health`) - System health monitoring
- **API Documentation** (`/docs`, `/redoc`) - Interactive API documentation
- **Request Logging** - Comprehensive middleware for request tracking
- **Error Handling** - Standardized error responses with request IDs

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

### When Working with API Backend (`backend/` directory) - Primary Development
- Follow FastAPI and Pydantic patterns for all new development
- Use dependency injection for service interfaces
- Implement proper HTTP status codes and error responses
- Maintain OpenAPI documentation completeness
- Interface-first, service-based, scalable architecture
- All business logic should be in service implementations
- Use the existing middleware for logging and error handling

### When Working with Legacy Code (`backend/app/services/implementations/legacy/`)
- These modules are reference implementations only
- Each module handles one step of the original pipeline
- Functions maintain backwards compatibility for reference
- All file I/O uses `data/` directory for persistence
- **Do not modify legacy code** - create new API implementations instead

### Code Patterns
- **Configuration**: Centralized in `config.py` with environment overrides
- **Data Processing**: Pandas-heavy workflows with JSON serialization
- **External APIs**: Requests-based with comprehensive error handling
- **Financial Calculations**: NumPy/SciPy for optimization algorithms
- **Trading**: ibapi for Interactive Brokers integration

## Repository Documentation Files

The repository includes several additional documentation files for specific aspects:

- **`API_USAGE_GUIDE.md`** - Comprehensive API usage examples and workflows
- **`API_IMPLEMENTATION_DIAGNOSTIC.md`** - Detailed implementation status and diagnostics
- **`ORDER_STATUS_DIAGNOSTIC.md`** - Order status tracking troubleshooting guide
- **`PRODUCTION_DEPLOYMENT_PLAN.md`** - Production deployment instructions
- **`0_dev.md`** - Development notes and implementation history
- **`.claude/agents/fintech-api-migration-specialist.md`** - Specialized agent for fintech migrations

## Additional Testing and Utilities

- **`test_order_status_direct.py`** - Direct order status testing script
- **Multiple Docker profiles** - Basic, with Redis, with proxy configurations
- **Telegram integration** - Notification system for trading updates

## Troubleshooting Common Issues

### API Issues (Primary)
1. Confirm FastAPI server is running on port 8000: `cd backend && uvicorn app.main:app --reload`
2. Check API documentation at `http://127.0.0.1:8000/docs`
3. Verify environment variables in both root `.env` and `backend/.env`
4. Test individual endpoints using Swagger UI or curl
5. Check logs for service-specific error details

### Pipeline Failures
1. Check `.env` file for required credentials (especially `UNCLE_STOCK_USER_ID`)
2. Verify IBKR Gateway is running and accessible
3. Ensure `data/` directory has proper write permissions
4. Check network connectivity for external API calls
5. Use health check endpoint: `curl http://127.0.0.1:8000/health`

### Trading Issues
1. Verify IBKR account permissions for API trading
2. Check client ID conflicts (each connection needs unique ID)
3. Confirm market hours for order execution
4. Review order status and rejection reasons in IBKR logs
5. Use order status endpoint: `curl -X POST http://127.0.0.1:8000/api/v1/orders/status`

### Docker Deployment Issues
1. Ensure all environment variables are set in `.env`
2. Check Docker container health status
3. Verify volume mounts for data persistence
4. Use appropriate profile for your setup (basic, with-redis, with-proxy)