# Uncle Stock Portfolio API - Usage Guide

## Table of Contents
1. [Quick Start](#quick-start)
2. [API Overview](#api-overview)
3. [Authentication Setup](#authentication-setup)
4. [CLI to API Mapping](#cli-to-api-mapping)
5. [Common Use Cases](#common-use-cases)
6. [Error Handling](#error-handling)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites
- Python 3.8+
- FastAPI server running locally
- Environment variables configured (see [Authentication Setup](#authentication-setup))

### Starting the API Server
```bash
# Navigate to backend directory
cd backend

# Start the server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be available at:
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc
- **OpenAPI Spec**: http://127.0.0.1:8000/openapi.json

### First API Call
Test if the server is running:
```bash
curl http://127.0.0.1:8000/health
# Expected: {"status": "healthy", "version": "1.0.0"}
```

---

## API Overview

The Uncle Stock Portfolio API provides **63 endpoints** across 8 main service areas:

| Service Area | Endpoints | Description |
|-------------|-----------|-------------|
| **Screeners** | 10 | Fetch stock data from screener services |
| **Historical Data** | 4 | Parse and analyze historical performance |
| **Universe Management** | 8 | Manage and query the stock universe |
| **Portfolio Operations** | 8 | Portfolio optimization and calculations |
| **Target Allocation** | 6 | Calculate and manage target allocations |
| **Order Management** | 6 | Generate and manage trading orders |
| **Pipeline Orchestration** | 13 | Execute and monitor the full pipeline |
| **IBKR Integration** | 3 | Interactive Brokers search and data |
| **Currency Exchange** | 3 | EUR exchange rate management |

**Total API Endpoints: 61** (plus 2 utility endpoints)

---

## Authentication Setup

### Required Environment Variables

Create a `.env` file in your backend directory:

```bash
# Uncle Stock API Configuration
UNCLE_STOCK_USER_ID=your_uncle_stock_user_id
UNCLE_STOCK_API_URL=https://api.unclestock.com

# Interactive Brokers Configuration
IBKR_HOST=127.0.0.1
IBKR_PORT=7497
IBKR_CLIENT_ID=1

# Exchange Rate API (Optional)
EXCHANGE_RATE_API_KEY=your_api_key

# Logging Configuration
LOG_LEVEL=INFO
DEBUG=false
```

### Configuration Validation
Test your configuration:
```bash
curl http://127.0.0.1:8000/api/v1/screeners/available
# Should return screener list instead of configuration error
```

---

## CLI to API Mapping

The original CLI `python main.py` executes 11 steps. Here's how to replicate each step via API:

| CLI Step | Step Name | API Endpoint | Method | Description |
|----------|-----------|--------------|--------|-------------|
| **Step 1** | Fetch Data | `/api/v1/screeners/fetch` | POST | Fetch current stocks from all screeners |
| **Step 2** | Parse Data | `/api/v1/universe/parse` | POST | Parse CSV files and create universe.json |
| **Step 3** | Parse History | `/api/v1/historical/universe/update` | POST | Update universe with historical data |
| **Step 4** | Optimize Portfolio | `/api/v1/portfolio/optimize` | POST | Optimize portfolio using Sharpe ratio |
| **Step 5** | Update Currency | `/api/v1/currency/update-universe` | POST | Update EUR exchange rates |
| **Step 6** | Calculate Targets | `/api/v1/portfolio/targets/calculate` | POST | Calculate final stock allocations |
| **Step 7** | Calculate Quantities | `/api/v1/orders/positions/targets` | GET | Get account value and calculate quantities |
| **Step 8** | IBKR Search | `/api/v1/ibkr/search-universe` | POST | Search for stocks on IBKR |
| **Step 9** | Rebalance | `/api/v1/orders/generate` | POST | Generate rebalancing orders |
| **Step 10** | Execute Orders | `/api/v1/orders/execute` | POST | Execute orders through IBKR |
| **Step 11** | Check Status | `/api/v1/orders/status` | POST | Check order execution status |

### Complete Pipeline Execution
Execute the entire pipeline with one API call:
```bash
# Run complete 11-step pipeline
curl -X POST http://127.0.0.1:8000/api/v1/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{}'

# Execute specific steps (e.g., steps 1-4)
curl -X POST http://127.0.0.1:8000/api/v1/pipeline/run/steps/1-4 \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## Common Use Cases

### 1. Check Available Data Sources
```bash
# Get list of available screeners
curl http://127.0.0.1:8000/api/v1/screeners/available

# Get available pipeline steps
curl http://127.0.0.1:8000/api/v1/pipeline/steps/available
```

### 2. Fetch Fresh Market Data
```bash
# Fetch from all screeners (makes API calls - costs money)
curl -X POST http://127.0.0.1:8000/api/v1/screeners/fetch

# Read existing data from all screeners (no API calls - free)
curl http://127.0.0.1:8000/api/v1/screeners/data

# Fetch from specific screener (makes API calls)
curl -X POST http://127.0.0.1:8000/api/v1/screeners/fetch/quality_bloom

# Read existing data from specific screener (no API calls)
curl http://127.0.0.1:8000/api/v1/screeners/data/quality_bloom

# Fetch historical data (makes API calls)
curl -X POST http://127.0.0.1:8000/api/v1/screeners/fetch-history

# Read existing historical data (no API calls)
curl http://127.0.0.1:8000/api/v1/screeners/history
```

### 3. Query the Universe
```bash
# Get complete universe data
curl http://127.0.0.1:8000/api/v1/universe

# Get universe metadata
curl http://127.0.0.1:8000/api/v1/universe/metadata

# Get specific stock details
curl http://127.0.0.1:8000/api/v1/universe/stocks/AAPL

# Get multi-screener stocks (high-confidence picks)
curl http://127.0.0.1:8000/api/v1/universe/stocks/multi-screen
```

### 4. Portfolio Analysis
```bash
# Get current portfolio optimization results
curl http://127.0.0.1:8000/api/v1/portfolio/optimization

# Get target allocations
curl http://127.0.0.1:8000/api/v1/portfolio/targets/

# Get current account value (from IBKR)
curl http://127.0.0.1:8000/api/v1/portfolio/account/value
```

### 5. IBKR Integration
```bash
# Check IBKR search service status
curl http://127.0.0.1:8000/api/v1/ibkr/search-status

# Search for all universe stocks on IBKR (Step 8)
curl -X POST http://127.0.0.1:8000/api/v1/ibkr/search-universe

# Search for a specific stock on IBKR (not yet implemented - returns 501)
curl -X POST http://127.0.0.1:8000/api/v1/ibkr/search-stock \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL"}'

# Note: universe_with_ibkr.json is created by search-universe endpoint
# No separate endpoint exists to retrieve it - access file directly
```

### 6. Order Management
```bash
# Generate rebalancing orders (Step 9)
curl -X POST http://127.0.0.1:8000/api/v1/orders/generate

# Get generated orders from file
curl http://127.0.0.1:8000/api/v1/orders

# Execute orders through IBKR (Step 10)
curl -X POST http://127.0.0.1:8000/api/v1/orders/execute

# Check order execution status (Step 11)
curl -X POST http://127.0.0.1:8000/api/v1/orders/status

# Get current positions from IBKR
curl http://127.0.0.1:8000/api/v1/orders/positions/current

# Get target positions/quantities
curl http://127.0.0.1:8000/api/v1/orders/positions/targets
```

### 7. Currency Operations
```bash
# Get current EUR exchange rates
curl http://127.0.0.1:8000/api/v1/currency/rates

# Update exchange rates
curl -X POST http://127.0.0.1:8000/api/v1/currency/update
```

### 8. Historical Analysis
```bash
# Get performance summary for all screeners
curl http://127.0.0.1:8000/api/v1/historical/performance/summary

# Get backtest data for specific screener
curl http://127.0.0.1:8000/api/v1/historical/screeners/backtest/quality_bloom
```

---

## Error Handling

### Standard Error Response Format
All errors follow a consistent structure:
```json
{
  "error_code": "ERROR_TYPE_CODE",
  "message": "Human-readable error message",
  "details": {
    "additional": "context information"
  },
  "retry_after": 300,
  "timestamp": "2025-09-15T14:33:11.963835",
  "request_id": "unique-request-id"
}
```

### Common Error Codes

| HTTP Status | Error Code | Description | Solution |
|------------|------------|-------------|----------|
| **400** | `VALIDATION_ERROR` | Invalid request parameters | Check request format and required fields |
| **404** | `NOT_FOUND` | Resource not found | Verify endpoint URL and resource ID |
| **422** | `UNPROCESSABLE_ENTITY` | Invalid data format | Check JSON structure and data types |
| **500** | `UNCLE_STOCK_INVALID_QUERY` | Uncle Stock configuration error | Set `UNCLE_STOCK_USER_ID` environment variable |
| **500** | `IBKR_CONNECTION_ERROR` | IBKR connection failed | Check IBKR TWS/Gateway is running |
| **503** | `SERVICE_UNAVAILABLE` | Service temporarily unavailable | Wait and retry, check dependencies |

### Configuration Errors
```bash
# Common configuration error:
{
  "error_code": "UNCLE_STOCK_INVALID_QUERY",
  "message": "Uncle Stock User ID not configured",
  "details": {
    "missing_config": "uncle_stock_user_id"
  }
}
```

### IBKR Connection Errors
```bash
# IBKR connection error:
{
  "error_code": "IBKR_CONNECTION_ERROR",
  "message": "Cannot connect to IBKR TWS/Gateway",
  "details": {
    "host": "127.0.0.1",
    "port": 7497,
    "suggestion": "Ensure IBKR TWS or Gateway is running"
  }
}
```

---

## Troubleshooting

### Server Won't Start
1. **Check Python version**: Requires Python 3.8+
2. **Check dependencies**: `pip install -r requirements.txt`
3. **Check port availability**: Try different port with `--port 8001`
4. **Check working directory**: Must be in `backend/` directory

### Configuration Issues
1. **Missing environment variables**: Create `.env` file with required variables
2. **Invalid Uncle Stock User ID**: Contact Uncle Stock support
3. **IBKR connection issues**: Ensure TWS/Gateway is running and accepting API connections

### API Responses Empty or Errors
1. **Check service health**: `curl http://127.0.0.1:8000/health`
2. **Validate configuration**: Test individual service endpoints
3. **Check logs**: Server logs show detailed error information
4. **Check dependencies**: Some endpoints require previous steps to be completed

### Performance Issues
1. **IBKR search slow**: Use batch endpoints instead of individual searches
2. **Large universe queries**: Use pagination parameters where available
3. **Pipeline execution timeout**: Run individual steps instead of complete pipeline

### Data File Issues
1. **Missing universe.json**: Run Step 2 (Parse Data) first
2. **Outdated data**: Run Step 1 (Fetch Data) to refresh
3. **File permissions**: Ensure write access to `data/` directory

---

## Service Health Monitoring

### Health Check Endpoints
```bash
# Main API health
curl http://127.0.0.1:8000/health

# Portfolio service health
curl http://127.0.0.1:8000/api/v1/portfolio/health

# Pipeline service health
curl http://127.0.0.1:8000/api/v1/pipeline/health

# IBKR search service status
curl http://127.0.0.1:8000/api/v1/ibkr/search-status
```

### Monitoring Pipeline Execution
```bash
# Get pipeline execution history
curl http://127.0.0.1:8000/api/v1/pipeline/history

# Monitor specific execution
curl http://127.0.0.1:8000/api/v1/pipeline/runs/{execution_id}/status

# Get execution logs
curl http://127.0.0.1:8000/api/v1/pipeline/runs/{execution_id}/logs
```

---

## API Documentation

- **Interactive Documentation**: http://127.0.0.1:8000/docs
- **Alternative Documentation**: http://127.0.0.1:8000/redoc
- **OpenAPI Specification**: http://127.0.0.1:8000/openapi.json

For detailed endpoint documentation, parameters, and response schemas, visit the interactive documentation at `/docs`.

---

*This guide covers the most common usage patterns. For complete endpoint documentation and advanced features, refer to the interactive API documentation.*