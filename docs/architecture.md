# Architecture Overview

## 🏗️ Clean Architecture Principles

This project follows **Clean Architecture** (also known as Hexagonal Architecture or Ports & Adapters) to ensure:

- **Separation of Concerns**: Each layer has a single, well-defined responsibility
- **Testability**: Business logic is independent of frameworks and external systems
- **Maintainability**: Changes in one layer don't ripple through the entire system
- **Flexibility**: Easy to swap implementations (e.g., change from Supabase to MongoDB)

## 📐 Layer Structure

```
┌───────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                     │
│              (Streamlit Dashboard - UI)                   │
│  - User interactions                                      │
│  - Data visualization                                     │
│  - Input validation                                       │
└───────────────────────────────────────────────────────────┘
                            ↕️
┌───────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                       │
│              (Use Cases - Orchestration)                  │
│  - AnalyzeMarketRegimeUseCase                            │
│  - CalculateRiskMetricsUseCase                           │
│  - FetchHistoricalDataUseCase                            │
└───────────────────────────────────────────────────────────┘
                            ↕️
┌───────────────────────────────────────────────────────────┐
│                     DOMAIN LAYER                          │
│              (Business Logic - Pure Python)               │
│  - MarketData, MarketRegime, RiskMetrics (entities)      │
│  - RegimeClassifier, RiskCalculator (services)           │
│  - Repository interfaces (contracts)                     │
└───────────────────────────────────────────────────────────┘
                            ↕️
┌───────────────────────────────────────────────────────────┐
│                 INFRASTRUCTURE LAYER                      │
│         (External Systems - Implementations)              │
│  - Binance API client                                    │
│  - Cloudflare R2 storage                                 │
│  - Supabase database                                     │
│  - DuckDB query engine                                   │
└───────────────────────────────────────────────────────────┘
```

## 🔄 Dependency Rule

**Dependencies point INWARD**:
- Presentation → Application → Domain ← Infrastructure
- Domain layer has **ZERO** dependencies on outer layers
- Infrastructure implements interfaces defined in Domain

## 📦 Layer Responsibilities

### 1. Presentation Layer (`src/presentation/`)

**Purpose**: User interface and interaction

**Components**:
- `streamlit_app/app.py`: Main dashboard entry point
- `pages/`: Multi-page sections (Overview, Regime Analysis, Risk Analytics)
- `components/`: Reusable UI components (charts, cards, filters)

**Responsibilities**:
- Render visualizations (Plotly charts)
- Handle user inputs (date pickers, dropdowns)
- Display results from Application layer
- Format data for display

**Dependencies**: Application layer (use cases)

**Example**:
```python
# pages/regime_analysis.py
from src.application.use_cases import AnalyzeMarketRegimeUseCase

use_case = AnalyzeMarketRegimeUseCase(...)
result = use_case.execute(symbol="BTCUSDT", days=30)

st.plotly_chart(create_regime_chart(result))
```

---

### 2. Application Layer (`src/application/`)

**Purpose**: Use case orchestration and workflow coordination

**Components**:
- `use_cases/`: Business workflows
  - `analyze_market_regime.py`: Orchestrate regime classification
  - `calculate_risk_metrics.py`: Orchestrate risk calculations
  - `fetch_historical_data.py`: Fetch and cache data
- `dto/`: Data Transfer Objects for inter-layer communication

**Responsibilities**:
- Coordinate domain services
- Handle transaction boundaries
- Convert between domain models and DTOs
- Implement cross-cutting concerns (logging, caching)

**Dependencies**: Domain layer

**Example**:
```python
# use_cases/analyze_market_regime.py
class AnalyzeMarketRegimeUseCase:
    def __init__(self, data_repo, classifier):
        self.data_repo = data_repo  # Infrastructure
        self.classifier = classifier  # Domain service
    
    def execute(self, symbol: str, days: int) -> RegimeResultDTO:
        # 1. Fetch data (Infrastructure)
        data = self.data_repo.get_recent(symbol, days)
        
        # 2. Classify regime (Domain)
        regime = self.classifier.classify(data)
        
        # 3. Convert to DTO (Application)
        return RegimeResultDTO.from_domain(regime)
```

---

### 3. Domain Layer (`src/domain/`)

**Purpose**: Core business logic (framework-agnostic)

**Components**:
- `models/`: Domain entities
  - `market_data.py`: MarketData, MarketDataCollection
  - `market_regime.py`: MarketRegime, RegimeType
  - `risk_metrics.py`: RiskMetrics, VolatilityForecast
- `services/`: Domain services
  - `regime_classifier.py`: GMM + HMM classification
  - `risk_calculator.py`: VaR, ES, Sharpe, Sortino
  - `technical_analysis.py`: RSI, MACD, Bollinger Bands
- `interfaces/`: Repository contracts
  - `market_data_repository.py`: Abstract data access interface

**Responsibilities**:
- Define business entities and rules
- Implement domain logic (calculations, validations)
- Define contracts (interfaces) for external systems
- **NO** framework dependencies (pure Python)

**Dependencies**: None (pure Python + standard library)

**Example**:
```python
# domain/models/market_data.py
@dataclass(frozen=True)
class MarketData:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    def __post_init__(self):
        self._validate()  # Business rule
    
    def price_change_pct(self) -> float:
        return (self.close - self.open) / self.open
```

---

### 4. Infrastructure Layer (`src/infrastructure/`)

**Purpose**: External system integrations

**Components**:
- `data/`: Data source clients
  - `binance_client.py`: Binance Public Data API
  - `file_loader.py`: Load local CSV/Parquet
- `storage/`: Storage implementations
  - `parquet_manager.py`: Parquet read/write with partitioning
  - `r2_client.py`: Cloudflare R2 (S3-compatible)
  - `duckdb_query_engine.py`: Query Parquet via DuckDB
- `database/`: Database implementations
  - `supabase_client.py`: PostgreSQL via Supabase

**Responsibilities**:
- Implement repository interfaces from Domain
- Handle external API calls
- Manage database connections
- File I/O operations

**Dependencies**: Domain layer (implements interfaces)

**Example**:
```python
# infrastructure/storage/parquet_manager.py
class ParquetMarketDataRepository(IMarketDataRepository):
    """Implementation of domain interface."""
    
    def get_historical(self, symbol: str, start: datetime, end: datetime) -> MarketDataCollection:
        # Read from Parquet files
        df = self.duckdb.query(f"""
            SELECT * FROM 'data/btc/{symbol}/*.parquet'
            WHERE timestamp BETWEEN '{start}' AND '{end}'
        """)
        
        # Convert to domain model
        return MarketDataCollection.from_dataframe(df, symbol=symbol)
```

---

## 🔗 Data Flow Example

**Scenario**: User requests regime analysis for last 30 days

```
1. USER ACTION (Presentation)
   └─> User clicks "Analyze Regime" button

2. PRESENTATION LAYER
   └─> StreamlitApp.display_regime_analysis()
       └─> Calls: use_case.execute(symbol="BTCUSDT", days=30)

3. APPLICATION LAYER (Use Case)
   └─> AnalyzeMarketRegimeUseCase.execute()
       ├─> Fetch data: data_repo.get_recent("BTCUSDT", 30)
       │   └─> (Infrastructure: DuckDB queries Parquet files)
       │
       ├─> Calculate features: technical_analysis.calculate(data)
       │   └─> (Domain: RSI, MACD, Bollinger Bands)
       │
       ├─> Classify regime: classifier.classify(data)
       │   └─> (Domain: GMM + HMM)
       │
       └─> Return: RegimeResultDTO

4. INFRASTRUCTURE LAYER
   └─> ParquetMarketDataRepository.get_recent()
       └─> DuckDB.query("SELECT * FROM parquet_files WHERE ...")
           └─> Returns: MarketDataCollection (domain model)

5. DOMAIN LAYER
   └─> RegimeClassifier.classify(data)
       ├─> Fit GMM model
       ├─> Apply HMM smoothing
       └─> Return: MarketRegime (domain model)

6. BACK TO PRESENTATION
   └─> Display results:
       ├─> Plot regime timeline (Plotly)
       ├─> Show confidence scores
       └─> Display feature importance
```

---

## 🎯 Design Patterns Used

### Repository Pattern
- **Purpose**: Abstract data access
- **Location**: `domain/interfaces/` (interface), `infrastructure/` (implementation)
- **Benefit**: Easy to swap PostgreSQL ↔ MongoDB ↔ CSV files

### Strategy Pattern
- **Purpose**: Interchangeable algorithms
- **Example**: Different risk calculation strategies (Historical VaR, Monte Carlo, etc.)

### Factory Pattern
- **Purpose**: Object creation
- **Example**: Database connection factory (development vs production)

### DTO Pattern
- **Purpose**: Data transfer between layers
- **Location**: `application/dto/`
- **Benefit**: Decouples presentation from domain models

---

## 🧪 Testing Strategy

### Unit Tests (`tests/unit/`)
- **Target**: Domain layer (pure business logic)
- **Dependencies**: None (mocked)
- **Speed**: Fast (<1s)
- **Coverage Goal**: ≥90%

**Example**:
```python
def test_market_data_validation():
    # No external dependencies
    with pytest.raises(ValueError):
        MarketData(open=-100, ...)  # Negative price should fail
```

### Integration Tests (`tests/integration/`)
- **Target**: Infrastructure layer
- **Dependencies**: Real databases, APIs (mocked or test instances)
- **Speed**: Slower (5-30s)
- **Coverage Goal**: ≥70%

**Example**:
```python
def test_parquet_repository():
    # Uses real DuckDB and test Parquet files
    repo = ParquetMarketDataRepository()
    data = repo.get_historical("BTCUSDT", start, end)
    assert len(data) > 0
```

---

## 📊 Data Architecture

### Hot Storage (PostgreSQL via Supabase)
- **Purpose**: Recent data (last 30 days)
- **Why**: Fast inserts, real-time queries
- **Schema**:
  ```sql
  CREATE TABLE market_data (
      timestamp TIMESTAMPTZ PRIMARY KEY,
      symbol VARCHAR(20),
      open NUMERIC,
      high NUMERIC,
      low NUMERIC,
      close NUMERIC,
      volume NUMERIC,
      interval VARCHAR(10)
  );
  ```

### Warm Storage (Parquet on Cloudflare R2)
- **Purpose**: Historical data (3 years)
- **Why**: Cheap storage, efficient analytics
- **Partitioning**: `symbol/interval/year-month/data.parquet`
  - Example: `btcusdt/1h/2024-01/data.parquet`

### Query Engine (DuckDB)
- **Purpose**: Query Parquet files without full download
- **Why**: HTTP range requests (only fetch needed columns/rows)
- **Example**:
  ```python
  duckdb.query("""
      SELECT * FROM 'https://r2.dev/btcusdt/1h/2024-*.parquet'
      WHERE timestamp >= '2024-01-01'
  """)
  ```

---

## 🔧 Technology Choices

| Layer | Technology | Reason |
|-------|-----------|--------|
| Presentation | Streamlit | Fast prototyping, native data viz |
| Application | Pure Python | Business logic, no framework lock-in |
| Domain | Pure Python | Framework-agnostic, 100% testable |
| Infrastructure | Boto3, Supabase, DuckDB | Production-ready, free tiers |

---

## 🚀 Deployment Strategy

### Development
- **Environment**: Local machine
- **Database**: SQLite or local Supabase
- **Storage**: Local Parquet files

### Staging
- **Environment**: Streamlit Cloud
- **Database**: Supabase (free tier)
- **Storage**: Cloudflare R2 (free tier)

### Production
- **Environment**: Streamlit Cloud (or self-hosted)
- **Database**: Supabase (paid tier for performance)
- **Storage**: Cloudflare R2 (scalable)
- **CI/CD**: GitHub Actions
  - Run tests on every push
  - Auto-deploy to Streamlit Cloud on merge to `main`

---

## 📝 Key Takeaways

1. **Domain is King**: Business logic lives in Domain layer (pure Python)
2. **Interfaces First**: Define contracts before implementations
3. **Test the Core**: 90%+ coverage on Domain layer (easiest to test)
4. **Swap Freely**: Change databases/frameworks without touching business logic
5. **Keep it Simple**: Don't over-engineer (YAGNI principle)

This architecture ensures:
✅ Code is maintainable for 2+ years  
✅ New features can be added without breaking existing code  
✅ Tests run in <10 seconds (unit tests)  
✅ Easy to onboard new developers (clear boundaries)
