# SQUACK Pipeline - Phase 1: Foundation

Phase 1 implements the foundational components of the SQUACK pipeline using modern Python best practices.

## Components Implemented

### 1. Directory Structure
- Created modular directory structure for clean separation of concerns
- Each module has proper `__init__.py` files for clean imports

### 2. Pydantic V2 Data Models
- **Property**: Complete property data model with validation
- **Location**: Geographic location and neighborhood models  
- **Wikipedia**: Wikipedia article data model
- **Enriched**: Combined models for enriched data output

### 3. Configuration System
- **PipelineSettings**: Main configuration using Pydantic BaseSettings
- **Sub-configurations**: DuckDB, Parquet, Embedding, Data, and Logging configs
- **Environment variables**: Support for `.env` files and environment overrides

### 4. Structured Logging
- **PipelineLogger**: Centralized logging with loguru
- **LoggerAdapter**: Context-aware logging with structured data
- **Decorators**: Execution time logging and data quality metrics

### 5. Base Interfaces
- **BaseLoader**: Abstract interface for data loading operations
- **BaseProcessor**: Abstract interface for data processing
- **BaseWriter**: Abstract interface for data output operations

### 6. Utilities
- **Validation**: Data validation utilities with Pydantic integration
- **Logging**: Structured logging with performance tracking

## Test Scripts

### Test 1: Model Validation
```bash
PYTHONPATH=/Users/ryanknight/projects/temporal/real_estate_ai_search:$PYTHONPATH python -m pytest squack_pipeline/tests/test_models.py -v
```

### Test 2: Configuration Validation
```bash
PYTHONPATH=/Users/ryanknight/projects/temporal/real_estate_ai_search:$PYTHONPATH python -m squack_pipeline.config.settings --validate
```

### Test 3: Generate Model Schema
```bash
PYTHONPATH=/Users/ryanknight/projects/temporal/real_estate_ai_search:$PYTHONPATH python -c "from squack_pipeline.models import Property; print(Property.model_json_schema())"
```

### Test 4: Basic Model Creation
```bash
PYTHONPATH=/Users/ryanknight/projects/temporal/real_estate_ai_search:$PYTHONPATH python -c "
from datetime import date
from squack_pipeline.models import Property, WikipediaArticle
from squack_pipeline.config import PipelineSettings

# Test Property model
prop_data = {
    'listing_id': 'test-001',
    'address': {'street': '123 Test St', 'city': 'TestCity', 'county': 'TestCounty', 'state': 'CA', 'zip': '12345'},
    'coordinates': {'latitude': 37.0, 'longitude': -122.0},
    'property_details': {'square_feet': 1500, 'bedrooms': 3, 'bathrooms': 2.0, 'property_type': 'house', 'year_built': 2000, 'lot_size': 0.25, 'stories': 2, 'garage_spaces': 2},
    'listing_price': 500000.0,
    'price_per_sqft': 333.33,
    'description': 'Test property',
    'listing_date': date(2025, 1, 1),
    'days_on_market': 10
}

prop = Property(**prop_data)
print(f'✓ Property model: {prop.listing_id} - ${prop.listing_price:,.2f}')

# Test settings
settings = PipelineSettings()
print(f'✓ Settings: {settings.pipeline_name} v{settings.pipeline_version}')
print(f'✓ Environment: {settings.environment}')

print('Phase 1 foundation is working correctly!')
"
```

### Test 5: CLI Interface
```bash
PYTHONPATH=/Users/ryanknight/projects/temporal/real_estate_ai_search:$PYTHONPATH python -m squack_pipeline --help
```

### Test 6: Configuration Display
```bash
PYTHONPATH=/Users/ryanknight/projects/temporal/real_estate_ai_search:$PYTHONPATH python -m squack_pipeline show-config
```

### Test 7: Version Check
```bash
PYTHONPATH=/Users/ryanknight/projects/temporal/real_estate_ai_search:$PYTHONPATH python -m squack_pipeline version
```

## Key Features

### Pydantic V2 Benefits
- **4-50x faster validation** with Rust-backed pydantic-core
- **Strict mode validation** for type safety
- **Field validators** for custom business logic
- **JSON schema generation** for documentation

### Configuration Features
- **Environment variable support** with prefixes
- **YAML configuration files** for complex setups
- **Validation on initialization** prevents runtime errors
- **Sub-configuration nesting** for organized settings

### Logging Features
- **Structured logging** with loguru
- **Context binding** for request tracking
- **Performance decorators** for timing
- **Multiple output formats** (console, file, JSON)

## Architecture

```
squack_pipeline/
├── __init__.py
├── __main__.py              # CLI entry point
├── config/                  # Configuration management
│   ├── settings.py          # Pydantic BaseSettings
│   └── schemas.py           # Configuration schemas
├── models/                  # Data models
│   ├── property.py          # Property data model
│   ├── location.py          # Location/neighborhood models
│   ├── wikipedia.py         # Wikipedia article model
│   └── enriched.py          # Enriched output models
├── loaders/                 # Data loading interfaces
│   └── base.py              # Base loader interface
├── processors/              # Data processing interfaces
│   └── base.py              # Base processor interface
├── writers/                 # Data output interfaces
│   └── base.py              # Base writer interface
└── utils/                   # Utility modules
    ├── logging.py           # Structured logging
    └── validation.py        # Data validation
```

## Next Steps

Phase 1 provides the foundation for:
- **Phase 2**: Data loading with DuckDB
- **Phase 3**: Data processing and medallion architecture
- **Phase 4**: Embedding generation with LlamaIndex

The clean, modular architecture ensures maintainability and extensibility for future phases.