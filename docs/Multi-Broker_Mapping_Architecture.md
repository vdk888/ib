# Multi-Broker Mapping Architecture: Interface-First Design

## Executive Summary

This document outlines the migration from single-broker (IBKR) mapping to a unified multi-broker mapping system that supports IBKR, Alpaca, and future brokers through a clean Interface-First Design approach.

## Current State Analysis

### Pipeline Step 8: IBKR Search (Current Implementation)

**Location**: `backend/app/services/implementations/pipeline_orchestrator_service.py:1173`

**Current Function**:
```python
def _step8_ibkr_search(self) -> bool:
    """Step 8: Search stocks on IBKR"""
    result = self.ibkr_search_service.process_all_universe_stocks()
    # Creates: data/universe_with_ibkr.json
```

**Input**: `data/universe.json` (portfolio-optimized universe data)
**Output**: `data/universe_with_ibkr.json` (universe + IBKR contract mappings)

**Dependencies**:
- Step 7 (Calculate Quantities) must complete first
- Step 9 (Rebalance) depends on Step 8 output

### Current Limitations

1. **Single Broker Only**: Only maps to IBKR, limiting order execution options
2. **Hardcoded Dependencies**: Step 9 expects `universe_with_ibkr.json` specifically
3. **No Asset Type Optimization**: Can't route crypto to specialized exchanges
4. **No Fallback Strategy**: If IBKR doesn't have an asset, no alternatives

## Proposed Architecture: Multi-Broker Mapping

### Core Design Principles

1. **Interface-First**: Define contracts before implementation
2. **Single Source of Truth**: One output file for all brokers
3. **Broker Agnostic**: Order generation doesn't know about specific brokers
4. **Fresh Data**: Re-fetch broker asset lists on each run
5. **Graceful Degradation**: If one broker fails, others continue

### Interface Design

```python
# Core broker matching interface
class IBrokerMatcher(ABC):
    @abstractmethod
    async def match_stocks(self, stocks: List[Dict]) -> Dict[str, BrokerMappingResult]:
        """Match universe stocks to broker-specific tradable instruments"""
        pass

    @abstractmethod
    async def refresh_tradable_assets(self) -> bool:
        """Update broker's tradable assets database"""
        pass

    @abstractmethod
    def get_broker_name(self) -> str:
        """Return broker identifier (ibkr, alpaca, crypto_com)"""
        pass

# Multi-broker orchestration interface
class IUniverseMappingService(ABC):
    @abstractmethod
    async def create_mapped_universe(self) -> Dict[str, Any]:
        """Transform universe.json → universe_mapped.json with all broker mappings"""
        pass

    @abstractmethod
    async def register_broker_matcher(self, matcher: IBrokerMatcher) -> None:
        """Add a new broker to the mapping process"""
        pass
```

### Data Structure Evolution

#### Current Structure: `universe_with_ibkr.json`
```json
{
  "screens": {
    "screener1": {
      "stocks": [
        {
          "ticker": "AAPL",
          "ibkr_details": {
            "found": true,
            "symbol": "AAPL",
            "conId": 265598,
            "exchange": "NASDAQ"
          }
        }
      ]
    }
  }
}
```

#### Proposed Structure: `universe_mapped.json`
```json
{
  "metadata": {
    "created_at": "2024-09-20T10:30:00Z",
    "brokers_included": ["ibkr", "alpaca"],
    "mapping_stats": {
      "total_stocks": 150,
      "fully_mapped": 142,
      "partially_mapped": 6,
      "unmapped": 2
    }
  },
  "screens": {
    "screener1": {
      "stocks": [
        {
          "ticker": "AAPL",
          "broker_mappings": {
            "ibkr": {
              "found": true,
              "symbol": "AAPL",
              "conId": 265598,
              "exchange": "NASDAQ",
              "search_method": "ticker"
            },
            "alpaca": {
              "found": true,
              "symbol": "AAPL",
              "asset_id": "904837e3-3b76-47ec-b432-046db621571b",
              "asset_class": "us_equity",
              "tradable": true
            },
            "crypto_com": {
              "found": false,
              "reason": "not_crypto_asset"
            }
          },
          "best_broker": "alpaca",
          "execution_preference": ["alpaca", "ibkr"]
        }
      ]
    }
  }
}
```

## Implementation Plan

### Phase 1: Interface Definition and Abstraction (Week 1)

#### Step 1.1: Create Broker Matcher Interface
**File**: `backend/app/services/interfaces.py`

Add the `IBrokerMatcher` and `IUniverseMappingService` interfaces to the existing interfaces file.

#### Step 1.2: Extract IBKR Matcher
**File**: `backend/app/services/implementations/ibkr_broker_matcher.py`

Wrap the existing IBKR search logic in the new interface:
```python
class IBKRBrokerMatcher(IBrokerMatcher):
    def __init__(self, ibkr_search_service: IIBKRSearchService):
        self.ibkr_search_service = ibkr_search_service

    async def match_stocks(self, stocks: List[Dict]) -> Dict[str, BrokerMappingResult]:
        # Wrap existing process_all_universe_stocks() logic
        pass
```

#### Step 1.3: Create Alpaca Matcher
**File**: `backend/app/services/implementations/alpaca_broker_matcher.py`

```python
class AlpacaBrokerMatcher(IBrokerMatcher):
    async def refresh_tradable_assets(self) -> bool:
        # Call existing alpaca_utils/tradable_assets.py logic
        # Save to backend/data/alpaca_tradable_assets.json
        pass

    async def match_stocks(self, stocks: List[Dict]) -> Dict[str, BrokerMappingResult]:
        # Simple symbol matching against alpaca_tradable_assets.json
        pass
```

### Phase 2: Multi-Broker Service Implementation (Week 2)

#### Step 2.1: Universe Mapping Service
**File**: `backend/app/services/implementations/universe_mapping_service.py`

```python
class UniverseMappingService(IUniverseMappingService):
    def __init__(self):
        self.broker_matchers: List[IBrokerMatcher] = []

    async def create_mapped_universe(self) -> Dict[str, Any]:
        # 1. Load universe.json
        # 2. For each broker, refresh assets and match stocks
        # 3. Combine results into universe_mapped.json structure
        # 4. Add metadata and mapping statistics
        # 5. Save to backend/data/universe_mapped.json
        pass
```

#### Step 2.2: Broker Registration System
Create a factory/registry pattern for clean broker management:

```python
# In universe_mapping_service.py
async def register_broker_matcher(self, matcher: IBrokerMatcher) -> None:
    await matcher.refresh_tradable_assets()
    self.broker_matchers.append(matcher)

# Usage in service initialization
mapping_service = UniverseMappingService()
await mapping_service.register_broker_matcher(IBKRBrokerMatcher(ibkr_search_service))
await mapping_service.register_broker_matcher(AlpacaBrokerMatcher())
```

### Phase 3: Pipeline Integration (Week 3)

#### Step 3.1: Update Pipeline Step 8
**File**: `backend/app/services/implementations/pipeline_orchestrator_service.py`

Transform the current `_step8_ibkr_search()` into `_step8_broker_mapping()`:

```python
def _step8_broker_mapping(self) -> bool:
    """Step 8: Map stocks to all available brokers"""
    try:
        result = self.universe_mapping_service.create_mapped_universe()
        # Success if we found mappings for majority of stocks
        stats = result.get('metadata', {}).get('mapping_stats', {})
        total_stocks = stats.get('total_stocks', 0)
        mapped_stocks = stats.get('fully_mapped', 0) + stats.get('partially_mapped', 0)
        return mapped_stocks > (total_stocks * 0.7)  # 70% success threshold
    except Exception as e:
        print(f"Step 8 failed: {e}")
        return False
```

#### Step 3.2: Update Step Metadata
Update the pipeline step information:

```python
8: PipelineStepInfo(
    step_number=8,
    step_name="Multi-Broker Mapping",  # Updated name
    description="Map universe stocks to all available brokers (IBKR, Alpaca, etc.)",  # Updated description
    aliases=["8", "step8", "brokers", "mapping"],  # Added aliases
    dependencies=[7],
    creates_files=["data/universe_mapped.json"],  # Updated output file
    modifies_files=[]
),
```

#### Step 3.3: Update Step 9 Dependencies
**File**: `backend/app/services/implementations/pipeline_orchestrator_service.py`

```python
def _step9_rebalancer(self) -> bool:
    """Step 9: Generate rebalancing orders"""
    try:
        # Updated to use new multi-broker file
        result = self.rebalancing_service.run_rebalancing("backend/data/universe_mapped.json")
        return len(result.get('orders', [])) > 0
```

### Phase 4: Order Generation Adaptation (Week 4)

#### Step 4.1: Update Rebalancing Service
**File**: `backend/app/services/implementations/rebalancing_service.py`

Modify the `load_universe_data()` method to handle the new broker mapping structure:

```python
def load_universe_data(self, universe_file: str) -> Dict[str, Any]:
    # Load universe_mapped.json instead of universe_with_ibkr.json
    # Extract broker mappings for order generation
    # Maintain backward compatibility for existing order structure
    pass
```

#### Step 4.2: Broker Selection Logic
Add broker selection logic to the rebalancing service:

```python
def select_best_broker_for_stock(self, stock: Dict[str, Any]) -> str:
    """Select optimal broker based on asset type and availability"""
    broker_mappings = stock.get('broker_mappings', {})

    # Priority logic:
    # 1. Use pre-calculated best_broker if available
    if 'best_broker' in stock:
        return stock['best_broker']

    # 2. Asset type based routing
    asset_type = self.classify_asset_type(stock)
    if asset_type == 'crypto':
        return self.select_first_available(['crypto_com', 'alpaca'], broker_mappings)
    elif asset_type in ['us_equity', 'etf']:
        return self.select_first_available(['alpaca', 'ibkr'], broker_mappings)
    else:
        return self.select_first_available(['ibkr'], broker_mappings)
```

## Technical Implementation Details

### Alpaca Symbol Matching Algorithm

```python
async def match_stocks(self, stocks: List[Dict]) -> Dict[str, BrokerMappingResult]:
    # Load fresh tradable assets
    with open('backend/data/alpaca_tradable_assets.json', 'r') as f:
        alpaca_assets = json.load(f)

    # Create symbol lookup dictionary
    symbol_lookup = {asset['symbol']: asset for asset in alpaca_assets['us_equity']}

    results = {}
    for stock in stocks:
        ticker = stock['ticker']

        # Direct symbol match (simple for Alpaca)
        if ticker in symbol_lookup:
            asset = symbol_lookup[ticker]
            results[ticker] = BrokerMappingResult(
                found=True,
                symbol=asset['symbol'],
                asset_id=asset['id'],
                asset_class='us_equity',
                tradable=asset['tradable']
            )
        else:
            results[ticker] = BrokerMappingResult(
                found=False,
                reason='symbol_not_found'
            )

    return results
```

### Error Handling Strategy

1. **Broker Failure Isolation**: If one broker matching fails, others continue
2. **Partial Success**: Generate output even if some brokers fail
3. **Detailed Logging**: Track which stocks failed mapping and why
4. **Graceful Degradation**: System works with any subset of brokers

### Performance Considerations

1. **Asset Refresh Optimization**: Only refresh if data is older than 24 hours
2. **Parallel Broker Matching**: Run broker matchers concurrently
3. **Caching Strategy**: Cache expensive IBKR searches, simple Alpaca lookups don't need caching
4. **Memory Management**: Stream process large broker asset lists

## Testing Strategy

### Unit Tests
- `test_ibkr_broker_matcher.py`: Verify IBKR wrapper behavior
- `test_alpaca_broker_matcher.py`: Test symbol matching logic
- `test_universe_mapping_service.py`: Test orchestration and output format

### Integration Tests
- `test_pipeline_step8_multi_broker.py`: Verify step 8 produces correct output
- `test_step8_to_step9_compatibility.py`: Ensure step 9 can consume new format

### End-to-End Tests
- Full pipeline run with multi-broker mapping
- Order generation using universe_mapped.json
- Verify order routing uses correct broker mappings

## Migration Path

### Backward Compatibility
During transition, maintain both outputs:
- `universe_with_ibkr.json` (legacy format for safety)
- `universe_mapped.json` (new multi-broker format)

### Rollout Strategy
1. **Week 1-2**: Implement interfaces and services
2. **Week 3**: Deploy with dual output (old + new formats)
3. **Week 4**: Update order generation to use new format
4. **Week 5**: Remove legacy format after validation

## Success Metrics

### Technical Metrics
- **Mapping Coverage**: >85% of universe stocks mapped to at least one broker
- **Multi-Broker Coverage**: >60% of stocks mapped to multiple brokers
- **Performance**: Step 8 completes in <2 minutes for 200 stocks

### Business Metrics
- **Execution Options**: Increase in executable orders due to broker diversity
- **Cost Optimization**: Route orders to brokers with better fees/execution
- **Reliability**: Reduced single-point-of-failure risk

## Future Extensions

### Phase 5: Advanced Routing (Future)
- **Dynamic Broker Selection**: Real-time broker capability checking
- **Cost Optimization**: Route based on commission structures
- **Geographic Optimization**: Route based on market hours and liquidity

### Phase 6: Additional Brokers (Future)
- **Crypto.com Integration**: Cryptocurrency-focused routing
- **Regional Brokers**: European/Asian broker integration
- **Specialized Brokers**: Options, futures, forex brokers

## Conclusion

This multi-broker mapping architecture provides a clean, extensible foundation for supporting multiple brokers while maintaining the Interface-First Design principles. The single output file (`universe_mapped.json`) simplifies downstream order generation while providing comprehensive broker mapping information for intelligent routing decisions.

The migration preserves existing functionality while opening up significant opportunities for execution optimization and risk reduction through broker diversification.