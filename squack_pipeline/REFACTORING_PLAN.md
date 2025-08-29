# SQUACK Pipeline Refactoring Plan

## Implementation Status

### ✅ Phase 1: Clean Up (COMPLETE)
- Removed hardcoded table names from all loaders
- Deleted old EntityProcessor hierarchy and pipeline files
- Fixed inconsistent return types with ProcessedTable model
- All tests passing

### ✅ Phase 2: Entity Separation (COMPLETE)
- Created entity-specific document converters (PropertyDocumentConverter, NeighborhoodDocumentConverter, WikipediaDocumentConverter)
- Added entity-aware configuration with PipelineEntityConfigs and EntityConfig models
- Implemented pipeline registry pattern with EntityPipelineRegistry for dynamic orchestrator selection
- All components use Pydantic models for type safety

### ✅ Phase 3: Advanced Features (COMPLETE)
- Created cross-entity enrichment orchestrator (EnrichmentOrchestrator)
- Implemented entity-specific writer strategies (PropertyWriterStrategy, NeighborhoodWriterStrategy, WikipediaWriterStrategy)
- All components use Pydantic models and clean modular design

## Critical Issues to Fix

### 1. Remove Hardcoded Table Names
**Files to modify:**
- `loaders/property_loader.py` - Remove default `table_name="bronze_properties"`
- `loaders/neighborhood_loader.py` - Remove default `table_name="bronze_neighborhoods"`
- `loaders/wikipedia_loader.py` - Remove default `table_name="bronze_wikipedia"`
- `loaders/location_loader.py` - Remove default `table_name="bronze_locations"`

**Change:**
```python
# Before
def load(self, source: Optional[Path] = None, table_name: str = "bronze_properties", ...):

# After  
def load(self, source: Optional[Path] = None, table_name: str, ...):  # Required parameter
```

### 2. Delete Old Entity Processing System
**Files to delete:**
- `processors/entity_processor.py` - Entire file (old EntityProcessor hierarchy)
- `orchestrator/pipeline.py` - Old monolithic orchestrator (replaced by main_orchestrator.py)
- `orchestrator/pipeline_simple.py` - Old simplified version

**Files to update:**
- `orchestrator/__init__.py` - Remove PipelineOrchestrator import, use MainPipelineOrchestrator
- `scripts/test_*.py` - Update all test scripts to use new orchestrator
- `README.md` - Remove references to old pipeline

**Reason:** This parallel hierarchy creates confusion and duplicates the new entity-specific processors.

### 3. Fix Inconsistent Return Types
**Problem:** Property orchestrator returns `SimpleNamespace` instead of proper table identifiers

**Solution:** Create a `ProcessedTable` dataclass:
```python
@dataclass
class ProcessedTable:
    """Result of processing a table through a tier."""
    table_name: str
    entity_type: EntityType
    tier: MedallionTier
    record_count: int
    timestamp: int
```

### 4. Create Entity-Specific Document Converters
**New files to create:**
- `embeddings/converters/property_converter.py`
- `embeddings/converters/neighborhood_converter.py`
- `embeddings/converters/wikipedia_converter.py`
- `embeddings/converters/base_converter.py`

**Structure:**
```python
class BaseDocumentConverter(ABC):
    @abstractmethod
    def convert_to_documents(self, data: List[Dict]) -> List[Document]:
        pass
    
    @abstractmethod
    def get_embedding_fields(self) -> List[str]:
        """Return fields to include in embeddings."""
        pass
```

## Architectural Improvements

### 5. Entity-Aware Configuration
**Create:** `config/entity_config.py`

```python
class EntityConfig(BaseModel):
    """Per-entity configuration."""
    
    validation_rules: ValidationRules
    processing_options: ProcessingOptions
    embedding_config: EntityEmbeddingConfig
    output_preferences: OutputPreferences

class PipelineEntityConfigs(BaseModel):
    """All entity configurations."""
    
    properties: EntityConfig
    neighborhoods: EntityConfig
    wikipedia: EntityConfig
```

### 6. Entity Pipeline Registry Pattern
**Create:** `orchestrator/registry.py`

```python
class EntityPipelineRegistry:
    """Registry for entity-specific pipelines."""
    
    _pipelines: Dict[EntityType, Type[BaseEntityOrchestrator]] = {}
    
    @classmethod
    def register(cls, entity_type: EntityType):
        """Decorator to register entity pipelines."""
        def wrapper(orchestrator_class):
            cls._pipelines[entity_type] = orchestrator_class
            return orchestrator_class
        return wrapper
    
    @classmethod
    def get_orchestrator(cls, entity_type: EntityType, settings, connection_manager):
        """Get orchestrator instance for entity type."""
        if entity_type not in cls._pipelines:
            raise ValueError(f"No pipeline registered for {entity_type}")
        return cls._pipelines[entity_type](settings, connection_manager)

# Usage:
@EntityPipelineRegistry.register(EntityType.PROPERTY)
class PropertyPipelineOrchestrator(BaseEntityOrchestrator):
    ...
```

### 7. Cross-Entity Enrichment Phase
**Create:** `orchestrator/enrichment_orchestrator.py`

```python
class EnrichmentOrchestrator:
    """Optional cross-entity enrichment after Gold tier."""
    
    def enrich_all(self, gold_tables: Dict[EntityType, ProcessedTable]):
        """Run all cross-entity enrichments."""
        
        # Property-Neighborhood enrichment
        if EntityType.PROPERTY in gold_tables and EntityType.NEIGHBORHOOD in gold_tables:
            self.enrich_properties_with_neighborhoods(...)
        
        # Property-Wikipedia enrichment  
        if EntityType.PROPERTY in gold_tables and EntityType.WIKIPEDIA in gold_tables:
            self.enrich_properties_with_wikipedia(...)
```

### 8. Entity-Specific Writer Strategies
**Create:** `writers/strategies/`
- `property_write_strategy.py`
- `neighborhood_write_strategy.py`
- `wikipedia_write_strategy.py`

Each strategy handles entity-specific transformations for output.

## Implementation Priority

### Phase 1: Clean Up (1 day)
1. ✅ Remove hardcoded table names from loaders
2. ✅ Delete old EntityProcessor hierarchy
3. ✅ Fix return types in orchestrators

### Phase 2: Entity Separation (COMPLETE)
4. ✅ Create entity-specific document converters
5. ✅ Add entity-aware configuration
6. ✅ Implement pipeline registry pattern

### Phase 3: Advanced Features (COMPLETE)
7. ✅ Add cross-entity enrichment phase
8. ✅ Create entity-specific writer strategies
9. ✅ Add entity-specific validation rules (via EntityConfig)

## Benefits After Refactoring

1. **True Entity Separation**: Each entity has its own complete pipeline
2. **Type Safety**: Consistent interfaces and return types
3. **Extensibility**: Easy to add new entity types via registry
4. **Maintainability**: Clear separation of concerns
5. **Testability**: Entity pipelines can be tested in isolation
6. **Configuration**: Fine-grained control per entity type

## Testing Strategy

### Missing Tests to Add
1. **Unit tests for entity orchestrators**:
   - `tests/orchestrator/test_property_orchestrator.py`
   - `tests/orchestrator/test_neighborhood_orchestrator.py`
   - `tests/orchestrator/test_wikipedia_orchestrator.py`

2. **Integration tests for entity pipelines**:
   - Test each entity pipeline end-to-end in isolation
   - Test cross-entity enrichment separately

3. **Configuration tests**:
   - Test entity-specific configuration loading
   - Test configuration validation per entity

## Code Quality Issues

### Naming Inconsistencies
- Some processors use `process()` method
- Others use `process_entity()` method
- Standardize on single interface

### Missing Type Hints
- Many methods missing return type hints
- Dict[str, Any] used too broadly - create specific types

### Error Handling
- Inconsistent error handling across orchestrators
- Should have entity-specific error types

## Success Metrics

- No hardcoded values in entity-agnostic code
- Each entity pipeline runs independently
- New entities can be added without modifying existing code
- All entity-specific logic is in entity-specific modules
- Cross-cutting concerns are clearly separated
- 100% test coverage for entity orchestrators
- Type hints on all public methods
- Consistent naming conventions throughout