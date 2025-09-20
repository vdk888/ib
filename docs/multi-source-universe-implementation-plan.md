# Multi-Source Universe Implementation Plan

## Current Situation

### Existing Architecture
The Uncle Stock Portfolio System currently uses a **single-source universe creation** approach:

1. **Step 1 (Screeners)**: Downloads CSV files from Uncle Stock API to `backend/data/files_exports/`
2. **Step 2 (Universe)**: Parses only these CSV files to create `universe.json`

### Current Data Flow
```
Uncle Stock API → CSV Files → Universe Parser → universe.json
```

### Current Configuration
```python
uncle_stock_screens: Dict[str, str] = {
    "quality_bloom": "quality bloom",
    "TOR_Surplus": "TOR Surplus",
    "Moat_Companies": "Moat Companies"
}
```

### Current File Structure
```
backend/data/files_exports/
├── quality_bloom_current_screen.csv
├── TOR_Surplus_current_screen.csv
└── Moat_Companies_current_screen.csv
```

### Current Universe Creation Process
1. Loop through configured screens
2. Transform screen name to safe filename: `{safe_name}_current_screen.csv`
3. Parse each CSV using `parse_screener_csv()`
4. Merge all stocks into single universe structure
5. Apply portfolio optimization

## Expected Result

### Target Architecture
A **multi-source universe creation** system that can integrate:

1. **Uncle Stock CSV Screeners** (existing)
2. **Predefined ETF Lists** (new)
3. **External API Sources** (future)
4. **Any other asset source** (extensible)

### Target Data Flow
```
┌─ Uncle Stock API → CSV Files ─┐
├─ ETF JSON Lists              ├─→ Multi-Source Parser → universe.json
├─ External APIs               │
└─ Future Sources ─────────────┘
```

### Target Configuration
```python
asset_sources: Dict[str, Dict] = {
    "uncle_stock_screeners": {
        "type": "csv_screener",
        "enabled": True,
        "screens": {
            "quality_bloom": "quality bloom",
            "TOR_Surplus": "TOR Surplus",
            "Moat_Companies": "Moat Companies"
        }
    },
    "etf_predefined": {
        "type": "etf_list",
        "enabled": True,
        "file_path": "data/etf_lists/core_etfs.json",
        "screen_name": "Core ETFs"
    },
    "external_scraper": {
        "type": "external_api",
        "enabled": False,
        "api_url": "https://api.example.com/stocks",
        "screen_name": "External Scraper"
    }
}
```

### Target Universe Structure
The `universe.json` would contain multiple screens from different sources:
```json
{
  "metadata": {
    "screens": ["quality bloom", "TOR Surplus", "Moat Companies", "Core ETFs"],
    "source_types": ["csv_screener", "etf_list"],
    "total_stocks": 650,
    "unique_stocks": 550
  },
  "screens": {
    "quality_bloom": { "source_type": "csv_screener", "stocks": [...] },
    "TOR_Surplus": { "source_type": "csv_screener", "stocks": [...] },
    "Moat_Companies": { "source_type": "csv_screener", "stocks": [...] },
    "core_etfs": { "source_type": "etf_list", "stocks": [...] }
  },
  "all_stocks": { /* merged and deduplicated */ }
}
```

## Detailed Implementation Plan

### Phase 1: Interface Definition (Week 1)

#### Step 1.1: Create Core Interfaces
**File**: `backend/app/services/interfaces/asset_source.py`

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pydantic import BaseModel

class Asset(BaseModel):
    """Standardized asset representation"""
    ticker: str
    isin: Optional[str] = None
    name: str
    currency: str
    sector: Optional[str] = None
    country: Optional[str] = None
    price: Optional[float] = None
    additional_fields: Dict[str, Any] = {}

class SourceMetadata(BaseModel):
    """Metadata about an asset source"""
    source_id: str
    source_type: str
    screen_name: str
    enabled: bool
    asset_count: int
    last_updated: datetime

class IAssetSource(ABC):
    """Interface for any asset source"""

    @abstractmethod
    async def get_assets(self) -> List[Asset]:
        """Retrieve assets from this source"""
        pass

    @abstractmethod
    def get_source_metadata(self) -> SourceMetadata:
        """Get metadata about this source"""
        pass

    @abstractmethod
    def validate_configuration(self) -> bool:
        """Validate source configuration"""
        pass
```

#### Step 1.2: Extend Universe Service Interface
**File**: `backend/app/services/interfaces/__init__.py`

```python
class IUniverseRepository(ABC):
    # Existing methods (keep for backward compatibility)
    def create_universe(self) -> Dict[str, Any]: ...
    def save_universe(self, universe: Dict[str, Any], output_path: str) -> None: ...

    # NEW: Multi-source methods
    @abstractmethod
    async def create_universe_from_sources(
        self,
        sources: List[IAssetSource]
    ) -> Dict[str, Any]:
        """Create universe from multiple asset sources"""
        pass

    @abstractmethod
    async def get_available_sources(self) -> List[SourceMetadata]:
        """Get all configured and available sources"""
        pass
```

### Phase 2: Legacy Adapter Implementation (Week 1-2)

#### Step 2.1: Create CSV Screener Source Adapter
**File**: `backend/app/services/implementations/sources/csv_screener_source.py`

```python
class UncleStockCSVSource(IAssetSource):
    """Adapter for existing Uncle Stock CSV files"""

    def __init__(self, screen_id: str, screen_name: str, csv_path: str):
        self.screen_id = screen_id
        self.screen_name = screen_name
        self.csv_path = csv_path

    async def get_assets(self) -> List[Asset]:
        """Convert existing CSV parsing to Asset objects"""
        # Use existing parse_screener_csv logic
        csv_stocks = parse_screener_csv(self.csv_path)

        assets = []
        for stock in csv_stocks:
            asset = Asset(
                ticker=stock['ticker'],
                isin=stock.get('isin'),
                name=stock.get('name', ''),
                currency=stock.get('currency', ''),
                sector=stock.get('sector'),
                country=stock.get('country'),
                price=stock.get('price'),
                additional_fields={
                    k: v for k, v in stock.items()
                    if k not in ['ticker', 'isin', 'name', 'currency', 'sector', 'country', 'price']
                }
            )
            assets.append(asset)

        return assets

    def get_source_metadata(self) -> SourceMetadata:
        return SourceMetadata(
            source_id=self.screen_id,
            source_type="csv_screener",
            screen_name=self.screen_name,
            enabled=os.path.exists(self.csv_path),
            asset_count=len(self.get_assets()) if os.path.exists(self.csv_path) else 0,
            last_updated=datetime.fromtimestamp(os.path.getmtime(self.csv_path)) if os.path.exists(self.csv_path) else None
        )

    def validate_configuration(self) -> bool:
        return os.path.exists(self.csv_path)
```

#### Step 2.2: Create Source Factory
**File**: `backend/app/services/implementations/sources/source_factory.py`

```python
class AssetSourceFactory:
    """Factory to create asset sources from configuration"""

    @staticmethod
    def create_csv_screener_sources(config: Dict) -> List[IAssetSource]:
        """Create CSV screener sources from config"""
        sources = []
        screens = config.get('screens', {})

        for screen_id, screen_name in screens.items():
            safe_name = screen_name.replace(' ', '_').replace('/', '_')
            csv_path = f"backend/data/files_exports/{safe_name}_current_screen.csv"

            source = UncleStockCSVSource(screen_id, screen_name, csv_path)
            if source.validate_configuration():
                sources.append(source)

        return sources

    @staticmethod
    def create_sources_from_config(asset_sources_config: Dict) -> List[IAssetSource]:
        """Create all sources from configuration"""
        all_sources = []

        for source_id, source_config in asset_sources_config.items():
            if not source_config.get('enabled', True):
                continue

            source_type = source_config.get('type')

            if source_type == 'csv_screener':
                sources = AssetSourceFactory.create_csv_screener_sources(source_config)
                all_sources.extend(sources)
            # elif source_type == 'etf_list':
            #     # Will implement in Phase 3
            # elif source_type == 'external_api':
            #     # Will implement in Phase 4

        return all_sources
```

### Phase 3: ETF List Source Implementation (Week 2)

#### Step 3.1: Create ETF List Source
**File**: `backend/app/services/implementations/sources/etf_list_source.py`

```python
class ETFListSource(IAssetSource):
    """Source for predefined ETF lists"""

    def __init__(self, source_id: str, screen_name: str, file_path: str):
        self.source_id = source_id
        self.screen_name = screen_name
        self.file_path = file_path

    async def get_assets(self) -> List[Asset]:
        """Load ETFs from JSON file"""
        with open(self.file_path, 'r') as f:
            etf_data = json.load(f)

        assets = []
        for etf in etf_data.get('etfs', []):
            asset = Asset(
                ticker=etf['ticker'],
                isin=etf.get('isin'),
                name=etf['name'],
                currency=etf.get('currency', 'USD'),
                sector=etf.get('sector', 'ETF'),
                country=etf.get('country'),
                price=None,  # Will be fetched separately if needed
                additional_fields={
                    'expense_ratio': etf.get('expense_ratio'),
                    'aum': etf.get('aum'),
                    'inception_date': etf.get('inception_date')
                }
            )
            assets.append(asset)

        return assets

    def get_source_metadata(self) -> SourceMetadata:
        return SourceMetadata(
            source_id=self.source_id,
            source_type="etf_list",
            screen_name=self.screen_name,
            enabled=os.path.exists(self.file_path),
            asset_count=len(self.get_assets()) if os.path.exists(self.file_path) else 0,
            last_updated=datetime.fromtimestamp(os.path.getmtime(self.file_path)) if os.path.exists(self.file_path) else None
        )

    def validate_configuration(self) -> bool:
        if not os.path.exists(self.file_path):
            return False

        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
                return 'etfs' in data and isinstance(data['etfs'], list)
        except (json.JSONDecodeError, KeyError):
            return False
```

#### Step 3.2: Create Sample ETF Data File
**File**: `backend/data/etf_lists/core_etfs.json`

```json
{
  "name": "Core ETFs",
  "description": "Essential ETFs for diversified portfolio",
  "last_updated": "2025-09-20",
  "etfs": [
    {
      "ticker": "VTI",
      "isin": "US9229087690",
      "name": "Vanguard Total Stock Market ETF",
      "currency": "USD",
      "sector": "Equity",
      "country": "United States",
      "expense_ratio": 0.03,
      "aum": 1500000000000,
      "inception_date": "2001-05-24"
    },
    {
      "ticker": "VEA",
      "isin": "US9220427424",
      "name": "Vanguard FTSE Developed Markets ETF",
      "currency": "USD",
      "sector": "Equity",
      "country": "International",
      "expense_ratio": 0.05,
      "aum": 100000000000,
      "inception_date": "2007-07-20"
    },
    {
      "ticker": "BND",
      "isin": "US9219378356",
      "name": "Vanguard Total Bond Market ETF",
      "currency": "USD",
      "sector": "Fixed Income",
      "country": "United States",
      "expense_ratio": 0.03,
      "aum": 250000000000,
      "inception_date": "2007-04-03"
    }
  ]
}
```

#### Step 3.3: Update Source Factory
Add ETF support to the factory:

```python
@staticmethod
def create_etf_list_sources(source_config: Dict) -> List[IAssetSource]:
    """Create ETF list sources from config"""
    file_path = source_config.get('file_path')
    screen_name = source_config.get('screen_name', 'ETF List')
    source_id = source_config.get('source_id', 'etf_list')

    source = ETFListSource(source_id, screen_name, file_path)
    if source.validate_configuration():
        return [source]
    return []
```

### Phase 4: Multi-Source Universe Service Implementation (Week 2-3)

#### Step 4.1: Implement Multi-Source Universe Creation
**File**: `backend/app/services/implementations/universe_service.py`

```python
class UniverseService(IUniverseRepository):
    # Keep existing methods...

    async def create_universe_from_sources(
        self,
        sources: List[IAssetSource]
    ) -> Dict[str, Any]:
        """Create universe from multiple asset sources"""
        from datetime import datetime

        universe = {
            'metadata': {
                'screens': [],
                'source_types': [],
                'total_stocks': 0,
                'unique_stocks': 0,
                'created_at': datetime.now().isoformat(),
                'created_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'sources': []
            },
            'screens': {},
            'all_stocks': {}
        }

        unique_stocks = {}
        total_stocks = 0

        # Process each source
        for source in sources:
            source_metadata = source.get_source_metadata()
            assets = await source.get_assets()

            # Convert assets to legacy format for compatibility
            stocks = []
            for asset in assets:
                stock_data = {
                    'ticker': asset.ticker,
                    'isin': asset.isin,
                    'name': asset.name,
                    'currency': asset.currency,
                    'sector': asset.sector,
                    'country': asset.country,
                    'price': asset.price,
                    **asset.additional_fields
                }
                stocks.append(stock_data)

            # Store screen data
            screen_id = source_metadata.source_id
            universe['screens'][screen_id] = {
                'name': source_metadata.screen_name,
                'source_type': source_metadata.source_type,
                'count': len(stocks),
                'stocks': stocks
            }

            # Update metadata
            universe['metadata']['screens'].append(source_metadata.screen_name)
            if source_metadata.source_type not in universe['metadata']['source_types']:
                universe['metadata']['source_types'].append(source_metadata.source_type)

            universe['metadata']['sources'].append({
                'source_id': source_metadata.source_id,
                'source_type': source_metadata.source_type,
                'screen_name': source_metadata.screen_name,
                'asset_count': len(stocks),
                'last_updated': source_metadata.last_updated.isoformat() if source_metadata.last_updated else None
            })

            # Add to unique stocks collection
            for stock in stocks:
                ticker = stock['ticker']
                if ticker not in unique_stocks:
                    unique_stocks[ticker] = stock
                    unique_stocks[ticker]['screens'] = [source_metadata.screen_name]
                else:
                    # Stock exists in multiple screens
                    if 'screens' not in unique_stocks[ticker]:
                        unique_stocks[ticker]['screens'] = []
                    if source_metadata.screen_name not in unique_stocks[ticker]['screens']:
                        unique_stocks[ticker]['screens'].append(source_metadata.screen_name)

            total_stocks += len(stocks)

        # Finalize universe
        universe['all_stocks'] = unique_stocks
        universe['metadata']['total_stocks'] = total_stocks
        universe['metadata']['unique_stocks'] = len(unique_stocks)

        return universe

    async def get_available_sources(self) -> List[SourceMetadata]:
        """Get all configured sources"""
        from ...core.config import settings

        sources = AssetSourceFactory.create_sources_from_config(
            settings.asset_sources
        )

        return [source.get_source_metadata() for source in sources]
```

### Phase 5: Configuration Updates (Week 3)

#### Step 5.1: Update Configuration Schema
**File**: `backend/app/core/config.py`

```python
class UncleStockSettings(BaseServiceSettings):
    # Keep existing settings...

    # NEW: Multi-source configuration
    asset_sources: Dict[str, Dict] = {
        "uncle_stock_screeners": {
            "type": "csv_screener",
            "enabled": True,
            "screens": {
                "quality_bloom": "quality bloom",
                "TOR_Surplus": "TOR Surplus",
                "Moat_Companies": "Moat Companies"
            }
        },
        "etf_predefined": {
            "type": "etf_list",
            "enabled": True,
            "source_id": "core_etfs",
            "file_path": "backend/data/etf_lists/core_etfs.json",
            "screen_name": "Core ETFs"
        }
    }

    # Feature flag for gradual rollout
    enable_multi_source_universe: bool = False
```

### Phase 6: API Integration (Week 3-4)

#### Step 6.1: Update Universe API Endpoints
**File**: `backend/app/api/v1/endpoints/universe.py`

```python
@router.post("/parse-multi-source", response_model=ParseUniverseResponse)
async def parse_universe_multi_source(
    request: ParseUniverseRequest,
    universe_service: IUniverseRepository = Depends(get_universe_service)
) -> ParseUniverseResponse:
    """
    Parse universe from multiple configured sources

    This endpoint creates universe.json from all enabled asset sources:
    - Uncle Stock CSV screeners
    - Predefined ETF lists
    - External API sources (when available)
    """
    try:
        start_time = time.time()

        # Get all configured sources
        from ....services.implementations.sources.source_factory import AssetSourceFactory
        from ....core.config import settings

        sources = AssetSourceFactory.create_sources_from_config(
            settings.uncle_stock.asset_sources
        )

        if not sources:
            raise HTTPException(
                status_code=404,
                detail="No valid asset sources found. Check configuration and data files."
            )

        # Create universe from all sources
        universe = await universe_service.create_universe_from_sources(sources)

        # Save universe
        universe_service.save_universe(universe, request.output_path)

        processing_time = time.time() - start_time
        metadata = universe_service.get_universe_metadata(universe)

        return ParseUniverseResponse(
            success=True,
            message=f"Multi-source universe created with {metadata.get('unique_stocks', 0)} unique stocks from {len(sources)} sources",
            universe_path=request.output_path,
            metadata=metadata,
            processing_time=processing_time
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create multi-source universe: {str(e)}"
        )

@router.get("/sources", response_model=List[Dict])
async def get_asset_sources(
    universe_service: IUniverseRepository = Depends(get_universe_service)
):
    """Get all configured asset sources and their status"""
    try:
        sources_metadata = await universe_service.get_available_sources()
        return [metadata.dict() for metadata in sources_metadata]

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve asset sources: {str(e)}"
        )
```

#### Step 6.2: Update Existing Parse Endpoint
Add backward compatibility with feature flag:

```python
@router.post("/parse", response_model=ParseUniverseResponse)
async def parse_universe(
    request: ParseUniverseRequest,
    use_multi_source: bool = Query(
        default=False,
        description="Use multi-source universe creation"
    ),
    universe_service: IUniverseRepository = Depends(get_universe_service)
) -> ParseUniverseResponse:
    """
    Parse screener CSV files and create universe.json

    Supports both legacy (CSV only) and new (multi-source) modes.
    """
    try:
        from ....core.config import settings

        # Check if multi-source is enabled and requested
        if use_multi_source and settings.uncle_stock.enable_multi_source_universe:
            # Delegate to multi-source endpoint
            return await parse_universe_multi_source(request, universe_service)
        else:
            # Use legacy single-source method
            start_time = time.time()
            universe = universe_service.create_universe()
            universe_service.save_universe(universe, request.output_path)

            processing_time = time.time() - start_time
            metadata = universe_service.get_universe_metadata(universe)

            return ParseUniverseResponse(
                success=True,
                message=f"Universe created successfully with {metadata.get('unique_stocks', 0)} unique stocks",
                universe_path=request.output_path,
                metadata=metadata,
                processing_time=processing_time
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create universe: {str(e)}"
        )
```

### Phase 7: Testing & Validation (Week 4)

#### Step 7.1: Unit Tests
**File**: `backend/app/tests/test_multi_source_universe.py`

```python
import pytest
from unittest.mock import Mock, patch
from app.services.implementations.sources.etf_list_source import ETFListSource
from app.services.implementations.sources.csv_screener_source import UncleStockCSVSource

class TestETFListSource:
    @pytest.fixture
    def etf_source(self):
        return ETFListSource("test_etf", "Test ETFs", "test_etfs.json")

    def test_validate_configuration_success(self, etf_source):
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data='{"etfs": []}')):
            assert etf_source.validate_configuration() == True

    def test_get_assets(self, etf_source):
        etf_data = {
            "etfs": [
                {
                    "ticker": "VTI",
                    "name": "Vanguard Total Stock Market ETF",
                    "currency": "USD"
                }
            ]
        }
        with patch('builtins.open', mock_open(read_data=json.dumps(etf_data))):
            assets = etf_source.get_assets()
            assert len(assets) == 1
            assert assets[0].ticker == "VTI"

class TestMultiSourceUniverse:
    @pytest.mark.asyncio
    async def test_create_universe_from_sources(self):
        # Test that multiple sources are properly combined
        mock_csv_source = Mock(spec=IAssetSource)
        mock_etf_source = Mock(spec=IAssetSource)

        # Set up mock returns
        mock_csv_source.get_assets.return_value = [...]
        mock_etf_source.get_assets.return_value = [...]

        universe_service = UniverseService(mock_data_parser)
        universe = await universe_service.create_universe_from_sources([
            mock_csv_source, mock_etf_source
        ])

        assert 'screens' in universe
        assert len(universe['metadata']['source_types']) == 2
```

#### Step 7.2: Integration Tests
Test complete pipeline with real data files:

```python
class TestMultiSourceIntegration:
    @pytest.mark.asyncio
    async def test_full_pipeline_with_etf_source(self):
        """Test complete pipeline with CSV + ETF sources"""
        # Create test ETF file
        # Run parse_universe_multi_source endpoint
        # Validate resulting universe.json structure
        pass
```

### Phase 8: Documentation & Deployment (Week 4)

#### Step 8.1: Update API Documentation
Add examples for new endpoints in OpenAPI schema

#### Step 8.2: Update CLAUDE.md
Document new configuration options and usage patterns

#### Step 8.3: Gradual Rollout Plan
1. Deploy with `enable_multi_source_universe: false`
2. Test manually with `use_multi_source=true` parameter
3. Enable feature flag when validated
4. Eventually deprecate legacy endpoint

## Migration Strategy

### Backward Compatibility
- Existing API endpoints continue to work unchanged
- Legacy configuration format remains supported
- Feature flag controls new functionality

### Testing Strategy
1. **Unit Tests**: Each source type independently
2. **Integration Tests**: Multi-source combinations
3. **End-to-End Tests**: Full pipeline with real data
4. **Performance Tests**: Ensure no regression in processing time

### Rollback Plan
- Feature flag allows instant rollback to legacy behavior
- No database schema changes required
- Configuration changes are additive only

## Risk Mitigation

### Technical Risks
- **Performance**: Async source processing prevents blocking
- **Data Quality**: Validation at source and universe level
- **Configuration Complexity**: Clear documentation and examples

### Business Risks
- **Gradual Rollout**: Feature flag ensures safe deployment
- **Monitoring**: Track universe creation success rates and processing times
- **Fallback**: Legacy system remains available

## Success Metrics

### Technical Metrics
- Universe creation time < 30 seconds (current benchmark)
- Support for 3+ source types
- 100% backward compatibility

### Business Metrics
- Increased universe diversity (more stocks from varied sources)
- Reduced dependence on single API (Uncle Stock)
- Foundation for future source integrations

## Future Extensions

### Phase 9: External API Sources (Future)
- REST API integration for external data sources
- Rate limiting and error handling
- Caching strategies

### Phase 10: Real-time Price Integration (Future)
- Live price feeds for ETFs and stocks
- Price update scheduling
- Historical price data storage

### Phase 11: User-Defined Sources (Future)
- UI for configuring custom sources
- CSV upload functionality
- Source validation and testing tools