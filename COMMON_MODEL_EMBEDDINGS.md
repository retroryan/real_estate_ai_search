# COMMON_MODEL_EMBEDDINGS.md

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

This document outlines the complete migration of `common_embeddings` module to use the shared `property_finder_models` package. The migration focuses on replacing all model definitions with imports from the shared package while maintaining the correlation and processing logic.

## Current State Analysis

### Existing Structure
```
common_embeddings/
├── models/              # TO BE DELETED
│   ├── __init__.py
│   ├── base.py         # BaseMetadata
│   ├── config.py       # Configuration models
│   ├── metadata.py     # Metadata models
│   ├── processing.py   # Processing models
│   ├── statistics.py   # Statistics models
│   ├── correlation.py  # Correlation models
│   ├── interfaces.py   # Abstract interfaces
│   ├── exceptions.py   # Custom exceptions
│   └── enums.py        # Enumerations
├── correlation/         # Correlation engine using models
├── pipeline/           # Processing pipeline using models
├── providers/          # Embedding providers using models
├── storage/            # Storage layer using models
├── tests/              # Tests using models
├── requirements.txt    # TO BE REPLACED
└── README.md           # TO BE UPDATED
```

### Dependencies to Migrate
Current `requirements.txt` contains:
- pydantic>=2.0
- chromadb>=0.4
- ollama>=0.1
- numpy>=1.24
- Various provider SDKs

## Phase 1: Infrastructure Setup

### Goal
Convert common_embeddings to use pyproject.toml and prepare for shared models integration.

### Todo List
- [ ] Create `common_embeddings/pyproject.toml` with all dependencies
- [ ] Add reference to property_finder_models as local dependency
- [ ] Update README.md to document new setup process
- [ ] Test installation with new pyproject.toml
- [ ] Verify all dependencies are correctly installed
- [ ] Ensure module can be run from common_embeddings/ directory
- [ ] Remove requirements.txt file

### Implementation Steps

#### 1.1 Create pyproject.toml
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "common-embeddings"
version = "1.0.0"
description = "Embedding generation and correlation pipeline for Property Finder"
requires-python = ">=3.9"
dependencies = [
    # Shared models package (local)
    "property-finder-models @ file:///../property_finder_models",
    
    # Core dependencies
    "pydantic>=2.0",
    "python-dotenv>=1.0",
    
    # Vector database
    "chromadb>=0.4",
    
    # Embedding providers
    "ollama>=0.1",
    "openai>=1.0",
    "google-generativeai>=0.3",
    "voyageai>=0.2",
    "cohere>=4.0",
    
    # Data processing
    "numpy>=1.24",
    "pandas>=2.0",
    "tiktoken>=0.5",
    
    # Utilities
    "pyyaml>=6.0",
    "rich>=13.0",
    "tqdm>=4.65",
    "tenacity>=8.2",
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
include = ["common_embeddings*"]
exclude = ["tests*"]

[tool.setuptools.package-data]
common_embeddings = ["*.yaml", "*.json"]
```

#### 1.2 Update README.md
Add new installation instructions:
```markdown
## Installation

### Prerequisites
- Python 3.9+
- property_finder_models package installed
- Ollama server running (for local embeddings)

### Setup
```bash
# Install shared models first (from project root)
cd property_finder_models
pip install -e .

# Install common_embeddings (from project root)
cd ../common_embeddings
pip install -e .

# For development
pip install -e ".[dev]"
```

### Running the Pipeline
**IMPORTANT**: All commands MUST be run from the `common_embeddings/` directory:

```bash
# Navigate to common_embeddings directory
cd /path/to/project/common_embeddings

# Create embeddings (from common_embeddings/)
python -m pipeline.main create --entity-type property

# Or with full module path (from common_embeddings/)
python pipeline/main.py create --entity-type property

# Run correlation (from common_embeddings/)
python -m correlation.engine correlate

# Run tests (from common_embeddings/)
pytest

# Type checking (from common_embeddings/)
mypy .
```

**Note**: The module is designed to work ONLY when run from the `common_embeddings/` directory. Running from parent or other directories will cause import errors.
```

#### 1.3 Test Installation
```bash
# Clean environment
pip uninstall common-embeddings -y
rm -rf common_embeddings.egg-info/

# Install with new setup
cd common_embeddings
pip install -e .

# Verify installation
python -c "import common_embeddings; print('Success!')"
```

### Review & Testing
- [ ] Verify pyproject.toml is syntactically correct
- [ ] Confirm all dependencies from requirements.txt are included
- [ ] Test installation in clean virtual environment
- [ ] Verify pipeline runs correctly when executed from common_embeddings/ directory
- [ ] Run existing tests to ensure no breakage
- [ ] Verify module can ONLY be run from common_embeddings/ directory (not parent)

---

## Phase 2: Model Migration

### Goal
Replace all local model imports with shared property_finder_models imports.

### Todo List
- [ ] Update all imports in correlation/ directory
- [ ] Update all imports in pipeline/ directory
- [ ] Update all imports in providers/ directory
- [ ] Update all imports in storage/ directory
- [ ] Update all imports in tests/ directory
- [ ] Replace print statements with logging
- [ ] Delete models/ directory completely
- [ ] Handle any models unique to embeddings (keep minimal local models if needed)

### Implementation Steps

#### 2.1 Import Mapping
Create a mapping of all imports to change:

| Old Import | New Import |
|------------|------------|
| `from common_embeddings.models.base import BaseMetadata` | `from property_finder_models import BaseMetadata` |
| `from common_embeddings.models.config import Config` | `from property_finder_models import Config` |
| `from common_embeddings.models.config import EmbeddingConfig` | `from property_finder_models import EmbeddingConfig` |
| `from common_embeddings.models.config import ChromaDBConfig` | `from property_finder_models import ChromaDBConfig` |
| `from common_embeddings.models.config import ChunkingConfig` | `from property_finder_models import ChunkingConfig` |
| `from common_embeddings.models.config import ProcessingConfig` | `from property_finder_models import ProcessingConfig` |
| `from common_embeddings.models.enums import EntityType` | `from property_finder_models import EntityType` |
| `from common_embeddings.models.enums import SourceType` | `from property_finder_models import SourceType` |
| `from common_embeddings.models.enums import EmbeddingProvider` | `from property_finder_models import EmbeddingProvider` |
| `from common_embeddings.models.enums import ChunkingMethod` | `from property_finder_models import ChunkingMethod` |
| `from common_embeddings.models.exceptions import *` | `from property_finder_models import CommonEmbeddingsError, etc.` |

#### 2.2 Identify Embeddings-Specific Models
Some models may be specific to embeddings and not in shared models:
- `correlation.py` models (ChunkGroup, ValidationResult, etc.)
- `statistics.py` models (PipelineStatistics, BatchProcessorStatistics, etc.)
- `processing.py` models (ProcessingResult, BatchProcessingResult, etc.)
- `interfaces.py` (IDataLoader, IEmbeddingProvider, etc.)

For these, create a minimal local models file:
```python
# common_embeddings/models_local.py
"""
Local models specific to embeddings pipeline that aren't shared.
These are implementation details not needed by other modules.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from property_finder_models import BaseMetadata, EntityType

# Keep only embeddings-specific models here
class ChunkGroup(BaseModel):
    """Group of chunks from same document."""
    parent_id: str
    chunks: List[str]
    total_chunks: int

class PipelineStatistics(BaseModel):
    """Statistics for pipeline execution."""
    total_processed: int
    successful: int
    failed: int
    duration_seconds: float

# ... other embeddings-specific models
```

#### 2.3 Update Correlation Directory
Files to update:
- `correlation/engine.py`
- `correlation/validator.py`
- `correlation/mapper.py`

Example changes:
```python
# OLD: correlation/engine.py
from common_embeddings.models.metadata import BaseMetadata
from common_embeddings.models.enums import EntityType
from common_embeddings.models.correlation import CorrelationMapping
import logging  # Add logging

logger = logging.getLogger(__name__)

# NEW: correlation/engine.py
from property_finder_models import BaseMetadata, EntityType
from common_embeddings.models_local import CorrelationMapping  # If kept local
import logging

logger = logging.getLogger(__name__)

# Replace any print statements
# OLD: print(f"Correlating {entity_type} embeddings")
# NEW: logger.info(f"Correlating {entity_type} embeddings")
```

#### 2.4 Update Pipeline Directory
Files to update:
- `pipeline/main.py`
- `pipeline/processor.py`
- `pipeline/chunker.py`
- `pipeline/batch_processor.py`

Example changes:
```python
# OLD: pipeline/processor.py
from common_embeddings.models.config import Config
from common_embeddings.models.processing import ProcessingResult
from common_embeddings.models.enums import ChunkingMethod

# NEW: pipeline/processor.py
from property_finder_models import Config, ChunkingMethod
from common_embeddings.models_local import ProcessingResult  # If kept local
import logging

logger = logging.getLogger(__name__)
```

#### 2.5 Update Providers Directory
Files to update:
- `providers/base.py`
- `providers/ollama_provider.py`
- `providers/openai_provider.py`
- `providers/gemini_provider.py`
- Other provider implementations

Example changes:
```python
# OLD: providers/ollama_provider.py
from common_embeddings.models.config import EmbeddingConfig
from common_embeddings.models.enums import EmbeddingProvider

# NEW: providers/ollama_provider.py
from property_finder_models import EmbeddingConfig, EmbeddingProvider
import logging

logger = logging.getLogger(__name__)
```

#### 2.6 Update Storage Directory
Files to update:
- `storage/chromadb_store.py`
- `storage/metadata_store.py`

Example changes:
```python
# OLD: storage/chromadb_store.py
from common_embeddings.models.config import ChromaDBConfig
from common_embeddings.models.metadata import BaseMetadata

# NEW: storage/chromadb_store.py
from property_finder_models import ChromaDBConfig, BaseMetadata
import logging

logger = logging.getLogger(__name__)
```

#### 2.7 Update Tests Directory
Files to update:
- Remove `tests/test_models.py` (models tested in property_finder_models)
- Update `tests/test_correlation.py`
- Update `tests/test_pipeline.py`
- Update `tests/test_providers.py`
- Update `tests/conftest.py`

#### 2.8 Update Logging
Replace all print statements:
```python
# Setup logging in each module
import logging
logger = logging.getLogger(__name__)

# Configure logging format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Replace prints
# OLD: print(f"Processing batch {batch_num}")
# NEW: logger.info(f"Processing batch {batch_num}")

# OLD: print(f"ERROR: {e}")
# NEW: logger.error(f"Processing failed: {e}", exc_info=True)
```

#### 2.9 Delete Old Models
```bash
# After all imports are updated and tested
rm -rf common_embeddings/models/

# Keep only local models if needed
# Keep common_embeddings/models_local.py if created
```

### Review & Testing
- [ ] Run grep to ensure no old imports remain
- [ ] Verify no print statements remain (grep for print())
- [ ] Run all unit tests
- [ ] Test embedding generation pipeline
- [ ] Test correlation engine
- [ ] Verify logging is working correctly
- [ ] Run type checking with mypy

---

## Phase 3: Integration Testing

### Goal
Validate the complete migration works end-to-end.

### Todo List
- [ ] Test property embedding generation
- [ ] Test Wikipedia embedding generation
- [ ] Test neighborhood embedding generation
- [ ] Test correlation with source data
- [ ] Test batch processing
- [ ] Test all embedding providers
- [ ] Performance comparison

### Test Scripts

#### 3.1 Embedding Generation Test
```python
# test_embedding_generation.py
from property_finder_models import (
    EnrichedProperty,
    EnrichedAddress,
    PropertyType,
    Config,
    EmbeddingProvider
)
from common_embeddings.pipeline import EmbeddingPipeline
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_embedding_generation():
    # Configure
    config = Config()
    config.embedding.provider = EmbeddingProvider.OLLAMA
    config.embedding.ollama_model = "nomic-embed-text"
    
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
    
    # Generate embedding
    pipeline = EmbeddingPipeline(config)
    result = pipeline.process_property(property)
    
    assert result.success
    assert len(result.embedding) == 384  # nomic-embed-text dimension
    logger.info("Embedding generation test passed!")

if __name__ == "__main__":
    test_embedding_generation()
```

#### 3.2 Correlation Test
```python
# test_correlation.py
from property_finder_models import EntityType
from common_embeddings.correlation import CorrelationEngine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_correlation():
    engine = CorrelationEngine()
    
    # Test property correlation
    results = engine.correlate(
        entity_type=EntityType.PROPERTY,
        source_path="data/properties.json",
        collection_name="property_embeddings"
    )
    
    assert results.total_correlated > 0
    assert len(results.missing_embeddings) == 0
    logger.info(f"Correlated {results.total_correlated} properties")
    
    # Test Wikipedia correlation
    results = engine.correlate(
        entity_type=EntityType.WIKIPEDIA_ARTICLE,
        source_path="data/wikipedia.db",
        collection_name="wikipedia_embeddings"
    )
    
    assert results.total_correlated > 0
    logger.info(f"Correlated {results.total_correlated} Wikipedia articles")

if __name__ == "__main__":
    test_correlation()
```

#### 3.3 Full Pipeline Test
```bash
# Navigate to common_embeddings directory (REQUIRED)
cd common_embeddings

# Test property embeddings (from common_embeddings/)
python -m pipeline.main create \
    --entity-type property \
    --source-path ../data/properties.json

# Test Wikipedia embeddings (from common_embeddings/)
python -m pipeline.main create \
    --entity-type wikipedia \
    --source-path ../data/wikipedia.db

# Run correlation (from common_embeddings/)
python -m correlation.engine correlate --all

# Check results (from common_embeddings/)
python -m pipeline.main stats
```

### Review & Testing
- [ ] All pipelines run without errors
- [ ] Embeddings are generated correctly
- [ ] Correlation finds all matches
- [ ] No import errors
- [ ] Performance is acceptable
- [ ] Logging provides good visibility

---

## Phase 4: Documentation Update

### Goal
Update all documentation to reflect the new structure.

### Todo List
- [ ] Update main README.md
- [ ] Update pipeline documentation
- [ ] Update provider documentation
- [ ] Update inline code comments
- [ ] Create migration notes

### Documentation Updates

#### 4.1 README.md Updates
- Installation instructions using pyproject.toml
- Import examples using property_finder_models
- Remove references to local models (except models_local.py if kept)
- Add troubleshooting section

#### 4.2 Pipeline Documentation
- Update configuration examples
- Update usage examples
- Document any local models that remain

### Review & Testing
- [ ] Documentation is accurate
- [ ] Examples work when copy-pasted
- [ ] No references to old model paths
- [ ] Clear migration path documented

---

## Phase 5: Optimization and Cleanup

### Goal
Optimize the migrated code and ensure clean implementation.

### Todo List
- [ ] Remove any duplicate utility functions
- [ ] Consolidate configuration loading
- [ ] Optimize import statements
- [ ] Remove unused imports
- [ ] Format code with black/ruff

### Optimization Steps

#### 5.1 Import Optimization
```python
# Consolidate imports at module level
# OLD: Multiple import statements
from property_finder_models import BaseMetadata
from property_finder_models import EntityType
from property_finder_models import SourceType

# NEW: Single import statement
from property_finder_models import (
    BaseMetadata,
    EntityType,
    SourceType,
    EmbeddingProvider,
    Config
)
```

#### 5.2 Configuration Consolidation
```python
# Create single configuration loader
# common_embeddings/utils/config.py
from property_finder_models import Config
import logging

logger = logging.getLogger(__name__)

def load_config(config_path: str = "config.yaml") -> Config:
    """Load configuration from file or use defaults."""
    try:
        # Load from YAML if exists
        config = Config.from_yaml(config_path)
        logger.info(f"Loaded config from {config_path}")
    except FileNotFoundError:
        # Use defaults
        config = Config()
        logger.info("Using default configuration")
    
    return config
```

### Review & Testing
- [ ] Code is properly formatted
- [ ] No duplicate code remains
- [ ] Imports are optimized
- [ ] Configuration is centralized

---

## Validation Checklist

### Pre-Migration
- [ ] Backup current working state (git commit)
- [ ] Document current pipeline functionality
- [ ] List all files that import models
- [ ] Identify embeddings-specific models to keep

### Post-Migration
- [ ] No files import from common_embeddings.models (except models_local if kept)
- [ ] All tests pass
- [ ] Pipeline runs without errors
- [ ] Correlation works correctly
- [ ] All providers function
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
3. **Pipeline Functional**: All embedding generation works
4. **Correlation Works**: Can correlate embeddings with source data
5. **Clean Code**: No commented old code, no print statements
6. **Documentation Complete**: All docs reflect new structure
7. **Type Safety**: mypy passes without errors

## Commands Summary

```bash
# Installation (from project root)
cd property_finder_models
pip install -e .
cd ../common_embeddings
pip install -e .

# ALL FOLLOWING COMMANDS MUST BE RUN FROM common_embeddings/ DIRECTORY
cd common_embeddings

# Generate embeddings (from common_embeddings/)
python -m pipeline.main create --entity-type property

# Run correlation (from common_embeddings/)
python -m correlation.engine correlate

# Test (from common_embeddings/)
pytest

# Type check (from common_embeddings/)
mypy .

# Find old imports (from common_embeddings/)
grep -r "from common_embeddings.models" . --include="*.py"
grep -r "import common_embeddings.models" . --include="*.py"

# Find print statements (from common_embeddings/)
grep -r "print(" . --include="*.py"

# Check logging (from common_embeddings/)
grep -r "logger\." . --include="*.py" | wc -l  # Should be > 0
```

## Special Considerations for Embeddings

### Models to Keep Local
Since common_embeddings has some specialized models for pipeline execution that aren't shared:

1. **Keep in models_local.py**:
   - Pipeline execution models (ProcessingResult, BatchProcessingResult)
   - Statistics models (PipelineStatistics, SystemStatistics)
   - Correlation-specific models (ChunkGroup, ValidationResult)
   - Interface definitions (if using abstract base classes)

2. **Move to shared**:
   - All configuration models
   - All enums
   - All base models
   - All entity models
   - All exceptions

### Provider Abstraction
The provider abstraction should continue to work with shared models:
```python
# providers/base.py
from abc import ABC, abstractmethod
from property_finder_models import EmbeddingConfig
from typing import List, Optional

class EmbeddingProvider(ABC):
    """Base class for embedding providers."""
    
    def __init__(self, config: EmbeddingConfig):
        self.config = config
    
    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        pass
```

This maintains clean separation while using shared configuration models.