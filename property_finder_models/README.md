# Property Finder Models

Shared Pydantic models for the Property Finder ecosystem, providing type-safe data structures for properties, neighborhoods, Wikipedia articles, embeddings, and API contracts.

## Overview

This package serves as the single source of truth for all data models used across the Property Finder ecosystem. It consolidates previously duplicated models from `common_ingest` and `common_embeddings` into a unified, well-organized library.

## Architecture

The models are organized into logical modules:

### Core Models (`core.py`)
- `BaseEnrichedModel` - Base class for enriched entities with timestamps
- `BaseMetadata` - Base class for embedding metadata with correlation IDs
- `generate_uuid()` - Utility for UUID generation

### Geographic Models (`geographic.py`)
- `GeoLocation` - Validated latitude/longitude coordinates
- `GeoPolygon` - Geographic boundaries with validation
- `EnrichedAddress` - Normalized addresses with optional geocoding
- `LocationInfo` - Location metadata for Wikipedia articles

### Entity Models (`entities.py`)
- `EnrichedProperty` - Complete property data with validation
- `EnrichedNeighborhood` - Neighborhood data with boundaries
- `EnrichedWikipediaArticle` - Wikipedia articles with metadata
- `WikipediaSummary` - AI-generated summaries with topics
- `WikipediaEnrichmentMetadata` - Processing metadata

### Embedding Models (`embeddings.py`)
- `EmbeddingData` - Container for vector embeddings
- `PropertyEmbedding` - Property-specific embeddings
- `WikipediaEmbedding` - Wikipedia embeddings with chunking
- `NeighborhoodEmbedding` - Neighborhood embeddings
- `EmbeddingContextMetadata` - Embedding generation context
- `ProcessingMetadata` - Text processing details

### Configuration Models (`config.py`)
- `EmbeddingConfig` - Multi-provider embedding configuration
- `ChromaDBConfig` - Vector database settings
- `ChunkingConfig` - Text chunking parameters
- `ProcessingConfig` - Batch processing settings
- `Config` - Root configuration container

### API Models (`api.py`)
- `PaginationParams` - Standard pagination parameters
- `PropertyFilter`, `NeighborhoodFilter`, etc. - Query filters
- `ResponseMetadata` - API response metadata
- `ResponseLinks` - HATEOAS navigation links
- Response wrappers for all entity types
- `ErrorResponse` - Standard error format

### Enumerations (`enums.py`)
- `PropertyType` - House, condo, apartment, etc.
- `PropertyStatus` - Active, pending, sold, etc.
- `EntityType` - Property, neighborhood, wikipedia
- `SourceType` - Data source identifiers
- `EmbeddingProvider` - Ollama, OpenAI, Gemini, etc.
- `ChunkingMethod` - Simple, semantic, sentence
- Additional enums for processing and augmentation

### Exceptions (`exceptions.py`)
- `PropertyFinderError` - Base exception
- `ValidationError`, `ConfigurationError`, etc. - Specific error types

## Installation

### Understanding Python Editable Installs

#### What is an Editable Install?

An editable install (also called "development install") creates a link between your Python environment and the source code directory, rather than copying files to site-packages. This means:

1. **Live Updates**: Changes to the source code are immediately reflected without reinstalling
2. **Development Friendly**: You can edit, test, and debug without constant reinstallation
3. **Import Works Globally**: The package becomes importable from anywhere in your Python environment

#### How It Works

When you run `pip install -e .` (the `-e` means "editable"):

1. **Setup Process**:
   - pip reads `pyproject.toml` to understand the package structure
   - Creates a `.egg-link` file in site-packages pointing to your source directory
   - Adds the path to `easy-install.pth` so Python knows where to find it
   - Installs all dependencies specified in `pyproject.toml`

2. **File Structure Created**:
   ```
   site-packages/
   ├── property_finder_models.egg-link  # Points to source directory
   └── easy-install.pth                 # Adds path to Python's import system
   
   property_finder_models/
   ├── property_finder_models/          # Actual source code (not copied)
   └── property_finder_models.egg-info/ # Package metadata
   ```

3. **Import Resolution**:
   - When you `import property_finder_models`, Python checks `easy-install.pth`
   - Finds the path to your source directory
   - Imports directly from source, not from site-packages

### For Development

Install the shared models in editable mode with development dependencies:

```bash
cd property_finder_models
pip install -e ".[dev]"
```

This command:
- Installs the package in editable mode (`-e`)
- Includes optional development dependencies (`[dev]`) like pytest, mypy, black
- Makes `property_finder_models` importable from anywhere in your environment

### Migrating Projects from requirements.txt

#### Current Setup (requirements.txt)

Most projects currently use `requirements.txt`:
```txt
# requirements.txt
pydantic>=2.0
fastapi>=0.100
chromadb>=0.4
# ... other dependencies
```

With local imports like:
```python
# Old way - importing from local modules
from common_ingest.models.property import EnrichedProperty
from common_ingest.models.base import BaseEnrichedModel
```

#### Migration Steps

##### 1. Create pyproject.toml

Replace `requirements.txt` with `pyproject.toml` in each project:

**For common_ingest/pyproject.toml:**
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "common-ingest"
version = "1.0.0"
requires-python = ">=3.9"
dependencies = [
    # Local shared models package
    "property-finder-models @ file:///../property_finder_models",
    # Previous requirements.txt dependencies
    "fastapi>=0.100",
    "uvicorn>=0.23",
    "chromadb>=0.4",
    "pydantic>=2.0",  # Still needed for other Pydantic usage
    # ... rest of your dependencies from requirements.txt
]

[tool.setuptools.packages.find]
where = ["."]
include = ["common_ingest*"]
```

**For common_embeddings/pyproject.toml:**
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "common-embeddings"
version = "1.0.0"
requires-python = ">=3.9"
dependencies = [
    # Local shared models package
    "property-finder-models @ file:///../property_finder_models",
    # Previous requirements.txt dependencies
    "chromadb>=0.4",
    "ollama>=0.1",
    "numpy>=1.24",
    # ... rest of your dependencies from requirements.txt
]

[tool.setuptools.packages.find]
where = ["."]
include = ["common_embeddings*"]
```

##### 2. Update Imports

Change all model imports throughout the codebase:

```python
# Old imports (DELETE these)
from common_ingest.models.property import EnrichedProperty
from common_ingest.models.base import BaseEnrichedModel
from common_embeddings.models.config import ChromaDBConfig

# New imports (USE these)
from property_finder_models import EnrichedProperty
from property_finder_models import BaseEnrichedModel
from property_finder_models import ChromaDBConfig
```

Or import multiple at once:
```python
from property_finder_models import (
    EnrichedProperty,
    EnrichedNeighborhood,
    PropertyType,
    PropertyStatus,
    ChromaDBConfig,
    EmbeddingData
)
```

##### 3. Delete Old Model Files

Remove the now-redundant model files:
```bash
# In common_ingest
rm -rf common_ingest/models/

# In common_embeddings  
rm -rf common_embeddings/models/
```

##### 4. Install the Packages

Install both the shared models and the project in editable mode:

```bash
# First, install shared models
cd property_finder_models
pip install -e .

# Then install common_ingest with its dependencies
cd ../common_ingest
pip install -e .

# Or install common_embeddings with its dependencies
cd ../common_embeddings
pip install -e .
```

##### 5. Update Any Configuration Files

If you have config files that reference model paths, update them:

```yaml
# Old config.yaml
models:
  base_path: "common_ingest.models"
  
# New config.yaml  
models:
  base_path: "property_finder_models"
```

##### 6. Update Docker/CI Configuration

If using Docker or CI, update to install from pyproject.toml:

```dockerfile
# Old Dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt

# New Dockerfile
COPY pyproject.toml .
COPY property_finder_models/ ./property_finder_models/
RUN pip install -e ./property_finder_models
RUN pip install -e .
```

### How Other Projects Use the Shared Models

Once installed, other projects can use the models as if they were any other installed package:

```python
# In any Python file in common_ingest or common_embeddings
from property_finder_models import (
    EnrichedProperty,
    EnrichedAddress,
    PropertyType,
    PropertyStatus,
    ChromaDBConfig,
    EmbeddingData,
    generate_uuid
)

# Create instances just like before
property = EnrichedProperty(
    listing_id="PROP123",
    property_type=PropertyType.HOUSE,
    price=Decimal("500000"),
    bedrooms=3,
    bathrooms=2,
    address=EnrichedAddress(
        street="123 Main St",
        city="San Francisco",
        state="California",
        zip_code="94102"
    )
)

# Use in API endpoints
@app.post("/properties", response_model=PropertyResponse)
async def create_property(property: EnrichedProperty):
    # Process property...
    return PropertyResponse(data=property)
```

### Benefits of This Approach

1. **Single Source of Truth**: Models defined once, used everywhere
2. **Type Safety**: IDEs and type checkers recognize the models
3. **Easy Updates**: Change a model once, all projects get the update
4. **No Path Issues**: Python's import system handles everything
5. **Development Friendly**: Editable installs mean instant updates
6. **Dependency Management**: pip handles all transitive dependencies

### Troubleshooting

**Import Errors After Migration:**
```bash
# Verify installation
pip list | grep property-finder-models

# Reinstall if needed
cd property_finder_models
pip install -e . --force-reinstall
```

**Old Imports Still Being Used:**
```bash
# Find all old imports that need updating
grep -r "from common_ingest.models" .
grep -r "from common_embeddings.models" .
```

**Package Not Found:**
```bash
# Check Python can find it
python -c "import property_finder_models; print(property_finder_models.__file__)"
```

## Usage Examples

### Creating a Property

```python
from property_finder_models import (
    EnrichedProperty,
    EnrichedAddress,
    PropertyType,
    PropertyStatus
)
from decimal import Decimal

property = EnrichedProperty(
    listing_id="PROP123",
    property_type=PropertyType.HOUSE,
    price=Decimal("750000"),
    bedrooms=3,
    bathrooms=2.5,
    square_feet=2000,
    address=EnrichedAddress(
        street="123 Main St",
        city="San Francisco",
        state="California",
        zip_code="94102"
    ),
    features=["hardwood floors", "updated kitchen", "garage"],
    status=PropertyStatus.ACTIVE
)
```

### Working with Embeddings

```python
from property_finder_models import (
    EmbeddingData,
    PropertyEmbedding,
    EmbeddingContextMetadata,
    EmbeddingProvider
)

# Create embedding data
embedding = EmbeddingData(
    embedding_id="emb_123",
    vector=[0.1, 0.2, 0.3, ...],  # 384-dimensional vector
    dimension=384,
    model_name="nomic-embed-text",
    provider="ollama"
)

# Create property embedding for storage
prop_embedding = PropertyEmbedding(
    embedding_id="emb_123",
    listing_id="PROP123",
    vector=[0.1, 0.2, 0.3, ...],
    metadata={"city": "San Francisco", "price": 750000},
    text="Beautiful 3BR house in San Francisco..."
)
```

### API Request/Response

```python
from property_finder_models import (
    PropertyFilter,
    PaginationParams,
    PropertyListResponse,
    ResponseMetadata
)

# Create filter for API request
filter = PropertyFilter(
    city="San Francisco",
    min_price=500000,
    max_price=1000000,
    min_bedrooms=2,
    include_embeddings=False
)

# Create pagination
pagination = PaginationParams(page=1, page_size=20)

# Create API response
response = PropertyListResponse(
    data=[property1, property2, ...],
    metadata=ResponseMetadata.from_pagination(
        total_count=100,
        page=1,
        page_size=20
    )
)
```

### Configuration

```python
from property_finder_models import Config, EmbeddingProvider

# Create configuration
config = Config()
config.embedding.provider = EmbeddingProvider.OLLAMA
config.embedding.ollama_model = "nomic-embed-text"
config.chromadb.persist_directory = "./data/embeddings"
config.chunking.chunk_size = 800
config.processing.batch_size = 100
```

## Testing

Run the test suite:

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=property_finder_models

# Run specific test file
pytest tests/test_models.py

# Run specific test class
pytest tests/test_models.py::TestEntityModels

# Run with verbose output
pytest -v
```

## Model Validation

All models use Pydantic V2 for automatic validation:

- **Type checking** - Ensures correct data types
- **Range validation** - Validates numeric ranges (e.g., lat/lon bounds)
- **String validation** - Checks for empty strings, length limits
- **Custom validators** - Business logic validation
- **Automatic serialization** - JSON/dict conversion

Example validation:
```python
from property_finder_models import GeoLocation

# Valid location
loc = GeoLocation(lat=37.7749, lon=-122.4194)

# Invalid - raises ValidationError
try:
    loc = GeoLocation(lat=91, lon=0)  # Latitude out of range
except ValueError as e:
    print(f"Validation error: {e}")
```

## Design Principles

1. **Single Source of Truth** - One definition for each model
2. **Type Safety** - Full Pydantic V2 validation
3. **Clean Architecture** - Logical organization by domain
4. **No Duplication** - Consolidated from multiple modules
5. **Direct Replacement** - No compatibility layers or wrappers
6. **Snake Case** - Consistent Python naming conventions

## Migration from Old Models

This package replaces models from:
- `common_ingest/models/`
- `common_embeddings/models/`

Update imports:
```python
# Old
from common_ingest.models.property import EnrichedProperty
from common_embeddings.models.config import ChromaDBConfig

# New
from property_finder_models import EnrichedProperty, ChromaDBConfig
```

## Contributing

When adding new models:

1. Place in the appropriate module (geographic, entities, etc.)
2. Inherit from appropriate base class
3. Add comprehensive field validation
4. Include docstrings with descriptions
5. Add to module's `__init__.py` exports
6. Write unit tests in `tests/test_models.py`
7. Update this README with usage examples

## License

Part of the Property Finder project. See parent repository for license details.