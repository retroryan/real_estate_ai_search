# COMMON_MODEL_INGEST.md

## QUESTIONS & CLARIFICATIONS NEEDED

### Critical Questions Before Starting:

1. **Property Finder Models Package Status**
   - Is the `property_finder_models` package already created and functional?
   - Does it contain all the models listed (BaseEnrichedModel, EnrichedProperty, etc.)?
   - Has it been tested independently?
   
ANSWER - Yes - review property_finder_models for completeness

2. **API Schemas Migration**
   - The document mentions moving API schemas (requests/responses) to property_finder_models
   - Should API-specific schemas (PaginationParams, filters, responses) really be in the shared models package?
   - Or should they remain in common_ingest/api/schemas for separation of concerns?

ANSWER - No - these should remain in common_ingest/api/schemas.  and remove them from the property_finder_models package

3. **Running Directory Requirement**
   - Why the strict requirement to ONLY run from `common_ingest/` directory?
   - This seems unusual for a Python package - typically packages should be runnable from anywhere
   - Is this a temporary constraint or permanent design decision?
ANSWER - Would this complicate things? I want to keep things simple and allow for easy isolation of projects because of complex requirements and dependencies.  Can a python load the toml only from a specific directory?
   - 
4. **Existing Integration Tests**
   - Are there existing integration tests we should preserve?
   - What's the current test coverage percentage?
   - Should we maintain test compatibility or rewrite from scratch?

ANSWER - Yes - we should preserve existing unit and integration tests in tests and integration_tests which require a running api server.  We should maintain test compatibility and not rewrite from scratch.

5. **Database and ChromaDB Collections**
   - Will existing ChromaDB collections need migration?
   - Are there any schema changes in the shared models that affect stored data?
   - Should we version the collections during migration?

ANSWER - NO to all 

6. **API Backward Compatibility**
   - Are there external consumers of the API that need backward compatibility?  NO - this is a new application
   - Can we change API response formats if needed?  Answer - ask me the engineer first before changing anything
   - Should we version the API endpoints? Answer - they are already versioned


7. **Logging Configuration**
   - Where should the main logging configuration be defined?
   - Should each module have its own logger or use a shared configuration?
   - What log levels and formats are preferred?

ANSWER - Each module should have its own logger.  and it's own configuration. default to INFO level and a simple format

8. **Circular Dependencies**
   - Could there be circular import issues between common_ingest and property_finder_models?
   - Does property_finder_models import anything from common_ingest?
ANSWER - please evaluate for circular dependencies and propose a fix 


### Assumptions to Verify:

1. **property_finder_models is complete** - Contains all models mentioned in the migration
2. **No data migration needed** - Existing data structures remain compatible
3. **Clean cut-over is feasible** - No external systems depend on current structure
4. **Test environment available** - Can test without affecting production
5. **Version control in place** - Can revert if critical issues arise

### Risk Assessment:

- **HIGH RISK**: Deleting models/ directory before confirming all imports work
- **MEDIUM RISK**: Breaking API compatibility if external consumers exist
- **LOW RISK**: Logging migration (can be done incrementally)

## Complete Cut-Over Requirements

### Key Goals
* **COMPLETE CHANGE**: All occurrences must be changed in a single, atomic update
* **CLEAN IMPLEMENTATION**: Simple, direct replacements only
* **NO MIGRATION PHASES**: Do not create temporary compatibility periods
* **NO PARTIAL UPDATES**: Change everything or change nothing
* **NO COMPATIBILITY LAYERS**: Do not maintain old and new paths simultaneously
* **NO BACKUPS OF OLD CODE**: Do not comment out old code "just in case"
* **NO CODE DUPLICATION**: Do not duplicate functions to handle both patterns
* **NO WRAPPER FUNCTIONS**: Direct replacements only, no abstraction layers
* **DO NOT CREATE "ENHANCED" VERSIONS**: Update existing classes directly
* **CONSISTENT NAMING**: Use snake_case throughout (Python standard)
* **PYDANTIC V2 ONLY**: Use latest Pydantic features without backward compatibility
* **USE LOGGING**: Replace all print statements with proper logging
* **HIGH QUALITY DEMO**: Focus on clean, working code without over-engineering
* **NO MONITORING OVERHEAD**: Skip performance monitoring and schema evolution for simplicity

## Executive Summary

This document outlines the complete migration of `common_ingest` module to use the shared `property_finder_models` package. The migration will be executed in two main phases: infrastructure setup (pyproject.toml) and model replacement (import updates).

## Current State Analysis

### Existing Structure
```
common_ingest/
├── models/           # TO BE DELETED
│   ├── __init__.py
│   ├── base.py      # BaseEnrichedModel
│   ├── property.py  # Property models
│   ├── wikipedia.py # Wikipedia models
│   └── embedding.py # Embedding models
├── api/
│   ├── app.py
│   ├── routers/
│   └── schemas/     # API request/response models
├── loaders/         # Data loaders using models
├── utils/           # Utilities using models
├── tests/           # Tests using models
├── requirements.txt # TO BE REPLACED
└── README.md        # TO BE UPDATED
```

### Dependencies to Migrate
Current `requirements.txt` contains:
- pydantic>=2.0
- fastapi>=0.100
- uvicorn>=0.23
- chromadb>=0.4
- Various other dependencies

## Phase 1: Infrastructure Setup

### Goal
Convert common_ingest to use pyproject.toml and prepare for shared models integration.

### Todo List
- [ ] Create `common_ingest/pyproject.toml` with all dependencies
- [ ] Add reference to property_finder_models as local dependency
- [ ] Update README.md to document new setup process
- [ ] Test installation with new pyproject.toml
- [ ] Verify all dependencies are correctly installed
- [ ] Ensure module can be run from common_ingest/ directory
- [ ] Remove requirements.txt file

### Implementation Steps

#### 1.1 Create pyproject.toml
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "common-ingest"
version = "1.0.0"
description = "Data ingestion service for Property Finder"
requires-python = ">=3.9"
dependencies = [
    # Shared models package (local)
    "property-finder-models @ file:///../property_finder_models",
    
    # Core dependencies
    "pydantic>=2.0",
    "python-dotenv>=1.0",
    
    # API dependencies
    "fastapi>=0.100",
    "uvicorn>=0.23",
    "httpx>=0.24",
    
    # Database dependencies
    "chromadb>=0.4",
    "sqlalchemy>=2.0",
    
    # Data processing
    "pandas>=2.0",
    "numpy>=1.24",
    
    # Utilities
    "pyyaml>=6.0",
    "rich>=13.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
    "mypy>=1.0",
    "black>=23.0",
    "ruff>=0.1.0",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["common_ingest*"]
exclude = ["tests*"]

[tool.setuptools.package-data]
common_ingest = ["*.yaml", "*.json"]
```

#### 1.2 Update README.md
Add new installation instructions:
```markdown
## Installation

### Prerequisites
- Python 3.9+
- property_finder_models package installed

### Setup
```bash
# Install shared models first (from project root)
cd property_finder_models
pip install -e .

# Install common_ingest (from project root)
cd ../common_ingest
pip install -e .

# For development
pip install -e ".[dev]"
```

### Running the Service
**IMPORTANT**: All commands MUST be run from the `common_ingest/` directory:

```bash
# Navigate to common_ingest directory
cd /path/to/project/common_ingest

# Start API server (from common_ingest/)
uvicorn api.app:app --reload

# Or with module syntax (from common_ingest/)
python -m uvicorn api.app:app --reload

# Run tests (from common_ingest/)
pytest

# Type checking (from common_ingest/)
mypy .
```

**Note**: The module is designed to work ONLY when run from the `common_ingest/` directory. Running from parent or other directories will cause import errors.
```

#### 1.3 Test Installation
```bash
# Clean environment
pip uninstall common-ingest -y
rm -rf common_ingest.egg-info/

# Install with new setup
cd common_ingest
pip install -e .

# Verify installation
python -c "import common_ingest; print('Success!')"
```

### Review & Testing
- [ ] Verify pyproject.toml is syntactically correct
- [ ] Confirm all dependencies from requirements.txt are included
- [ ] Test installation in clean virtual environment
- [ ] Verify API server starts correctly when run from common_ingest/ directory
- [ ] Run existing tests to ensure no breakage
- [ ] Verify module can ONLY be run from common_ingest/ directory (not parent)

---

## Phase 2: Model Migration

### Goal
Replace all local model imports with shared property_finder_models imports.

### Todo List
- [ ] Update all imports in api/ directory
- [ ] Update all imports in loaders/ directory
- [ ] Update all imports in utils/ directory
- [ ] Update all imports in tests/ directory
- [ ] Replace print statements with logging
- [ ] Delete models/ directory completely
- [ ] Update __init__.py files to export from shared models

### Implementation Steps

#### 2.1 Import Mapping
Create a mapping of all imports to change:

| Old Import | New Import |
|------------|------------|
| `from common_ingest.models.base import BaseEnrichedModel` | `from property_finder_models import BaseEnrichedModel` |
| `from common_ingest.models.property import EnrichedProperty` | `from property_finder_models import EnrichedProperty` |
| `from common_ingest.models.property import EnrichedNeighborhood` | `from property_finder_models import EnrichedNeighborhood` |
| `from common_ingest.models.property import PropertyType` | `from property_finder_models import PropertyType` |
| `from common_ingest.models.property import PropertyStatus` | `from property_finder_models import PropertyStatus` |
| `from common_ingest.models.property import GeoLocation` | `from property_finder_models import GeoLocation` |
| `from common_ingest.models.property import GeoPolygon` | `from property_finder_models import GeoPolygon` |
| `from common_ingest.models.property import EnrichedAddress` | `from property_finder_models import EnrichedAddress` |
| `from common_ingest.models.wikipedia import EnrichedWikipediaArticle` | `from property_finder_models import EnrichedWikipediaArticle` |
| `from common_ingest.models.wikipedia import WikipediaSummary` | `from property_finder_models import WikipediaSummary` |
| `from common_ingest.models.wikipedia import LocationInfo` | `from property_finder_models import LocationInfo` |
| `from common_ingest.models.embedding import EmbeddingData` | `from property_finder_models import EmbeddingData` |
| `from common_ingest.models.embedding import PropertyEmbedding` | `from property_finder_models import PropertyEmbedding` |
| `from common_ingest.models.embedding import WikipediaEmbedding` | `from property_finder_models import WikipediaEmbedding` |
| `from common_ingest.models.embedding import NeighborhoodEmbedding` | `from property_finder_models import NeighborhoodEmbedding` |
| `from common_ingest.api.schemas.requests import *` | `from property_finder_models import PaginationParams, PropertyFilter, etc.` |
| `from common_ingest.api.schemas.responses import *` | `from property_finder_models import ResponseMetadata, PropertyResponse, etc.` |

#### 2.2 Update API Directory
Files to update:
- `api/app.py`
- `api/routers/properties.py`
- `api/routers/neighborhoods.py`
- `api/routers/wikipedia.py`
- `api/schemas/*.py` (if keeping any local schemas)

Example changes:
```python
# OLD: api/routers/properties.py
from common_ingest.models.property import EnrichedProperty
from common_ingest.api.schemas.requests import PropertyFilter
from common_ingest.api.schemas.responses import PropertyResponse

# NEW: api/routers/properties.py
from property_finder_models import (
    EnrichedProperty,
    PropertyFilter,
    PropertyResponse
)
```

#### 2.3 Update Loaders Directory
Files to update:
- `loaders/property_loader.py`
- `loaders/neighborhood_loader.py`
- `loaders/wikipedia_loader.py`
- `loaders/embedding_loader.py`

Example changes:
```python
# OLD: loaders/property_loader.py
from common_ingest.models.property import (
    EnrichedProperty,
    EnrichedAddress,
    PropertyType,
    PropertyStatus
)
import logging  # Add logging

logger = logging.getLogger(__name__)

# NEW: loaders/property_loader.py
from property_finder_models import (
    EnrichedProperty,
    EnrichedAddress,
    PropertyType,
    PropertyStatus
)
import logging

logger = logging.getLogger(__name__)

# Replace any print statements
# OLD: print(f"Loading {len(properties)} properties")
# NEW: logger.info(f"Loading {len(properties)} properties")
```

#### 2.4 Update Utils Directory
Files to update:
- `utils/config.py`
- `utils/database.py`
- `utils/validation.py`
- Any other utility files using models

#### 2.5 Update Tests Directory
Files to update:
- `tests/test_models.py` (delete - models are tested in property_finder_models)
- `tests/test_loaders.py`
- `tests/test_api.py`
- `tests/conftest.py`

Example changes:
```python
# OLD: tests/test_loaders.py
from common_ingest.models.property import EnrichedProperty

# NEW: tests/test_loaders.py
from property_finder_models import EnrichedProperty
```

#### 2.6 Update Logging
Replace all print statements:
```python
# Setup logging in each module
import logging
logger = logging.getLogger(__name__)

# Replace prints
# OLD: print(f"Processing {item}")
# NEW: logger.info(f"Processing {item}")

# OLD: print(f"Error: {e}")
# NEW: logger.error(f"Error processing: {e}")

# OLD: print(f"Warning: {msg}")
# NEW: logger.warning(f"{msg}")
```

#### 2.7 Delete Old Models
```bash
# After all imports are updated and tested
rm -rf common_ingest/models/
```

### Review & Testing
- [ ] Run grep to ensure no old imports remain
- [ ] Verify no print statements remain (grep for print())
- [ ] Run all unit tests
- [ ] Start API server and test all endpoints
- [ ] Test data loading functionality
- [ ] Verify logging is working correctly
- [ ] Run type checking with mypy

---

## Phase 3: Integration Testing

### Goal
Validate the complete migration works end-to-end.

### Todo List
- [ ] Test property data flow: load → store → retrieve → API
- [ ] Test neighborhood data flow
- [ ] Test Wikipedia data flow
- [ ] Test embedding correlation
- [ ] Test API pagination and filtering
- [ ] Performance comparison (should be same or better)

### Test Scripts

#### 3.1 Property Flow Test
```python
# test_property_flow.py
from property_finder_models import EnrichedProperty, EnrichedAddress, PropertyType
from common_ingest.loaders import PropertyLoader
from common_ingest.api import app
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_property_flow():
    # Create test property
    property = EnrichedProperty(
        listing_id="TEST001",
        property_type=PropertyType.HOUSE,
        price=500000,
        bedrooms=3,
        bathrooms=2,
        address=EnrichedAddress(
            street="123 Test St",
            city="San Francisco",
            state="California",
            zip_code="94102"
        )
    )
    
    # Load property
    loader = PropertyLoader()
    loader.load_property(property)
    logger.info("Property loaded successfully")
    
    # Retrieve via API
    # Test API endpoint
    response = test_client.get("/properties/TEST001")
    assert response.status_code == 200
    assert response.json()["data"]["listing_id"] == "TEST001"
    
    logger.info("Property flow test passed!")

if __name__ == "__main__":
    test_property_flow()
```

#### 3.2 Full System Test
```bash
# Run from common_ingest directory
cd common_ingest

# Start API server
python -m uvicorn common_ingest.api.app:app --reload &

# Run test suite
pytest -v

# Test API endpoints
curl http://localhost:8000/properties
curl http://localhost:8000/neighborhoods
curl http://localhost:8000/wikipedia/articles

# Check logs for any errors
grep -i error logs/*.log
```

### Review & Testing
- [ ] All data flows work correctly
- [ ] No import errors
- [ ] No model validation errors
- [ ] API responses match expected schemas
- [ ] Performance is acceptable
- [ ] Logging provides good visibility

---

## Phase 4: Documentation Update

### Goal
Update all documentation to reflect the new structure.

### Todo List
- [ ] Update main README.md
- [ ] Update API documentation
- [ ] Update inline code comments
- [ ] Create migration notes
- [ ] Update any configuration examples

### Documentation Updates

#### 4.1 README.md Updates
- Installation instructions using pyproject.toml
- Import examples using property_finder_models
- Remove references to local models
- Add troubleshooting section

#### 4.2 API Documentation
- Update OpenAPI schemas
- Update example requests/responses
- Update type hints in docstrings

### Review & Testing
- [ ] Documentation is accurate
- [ ] Examples work when copy-pasted
- [ ] No references to old model paths
- [ ] Clear migration path documented

---

## Validation Checklist

### Pre-Migration
- [ ] Backup current working state (git commit)
- [ ] Document current functionality for comparison
- [ ] List all files that import models

### Post-Migration
- [ ] No files import from common_ingest.models
- [ ] All tests pass
- [ ] API server starts without errors
- [ ] All endpoints return correct data
- [ ] Logging works throughout
- [ ] No print statements remain
- [ ] Type checking passes
- [ ] Documentation is updated

### Rollback Plan
Since this is a complete cut-over:
1. If migration fails at any point, fix immediately
2. Do not proceed until current phase is complete
3. No rollback - only move forward with fixes

## Success Criteria

1. **Zero Import Errors**: No references to old model paths
2. **All Tests Pass**: 100% of existing tests work
3. **API Functional**: All endpoints work correctly
4. **Clean Code**: No commented old code, no print statements
5. **Documentation Complete**: All docs reflect new structure
6. **Type Safety**: mypy passes without errors

## Commands Summary

```bash
# Installation (from project root)
cd property_finder_models
pip install -e .
cd ../common_ingest
pip install -e .

# ALL FOLLOWING COMMANDS MUST BE RUN FROM common_ingest/ DIRECTORY
cd common_ingest

# Run API (from common_ingest/)
uvicorn api.app:app --reload

# Test (from common_ingest/)
pytest

# Type check (from common_ingest/)
mypy .

# Find old imports (from common_ingest/)
grep -r "from common_ingest.models" .
grep -r "import common_ingest.models" .

# Find print statements (from common_ingest/)
grep -r "print(" . --include="*.py"
```