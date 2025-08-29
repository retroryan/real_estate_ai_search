# SQUACK Pipeline Architecture Review

## Current State Analysis

### ✅ What's Working Well

1. **Entity-Specific Orchestrators**: Clean separation at the orchestration level
   - `PropertyPipelineOrchestrator`
   - `NeighborhoodPipelineOrchestrator`
   - `WikipediaPipelineOrchestrator`

2. **Base Class Hierarchy**: Good use of abstract base classes
   - `BaseEntityOrchestrator` provides consistent interface
   - `BaseLoader` for all data loaders
   - `TransformationProcessor` for tier processors

3. **Medallion Architecture**: Bronze → Silver → Gold tiers are well-defined

4. **Performance**: 45x improvement from nested structure preservation

### ❌ Critical Issues Found

#### 1. **Hardcoded Dependencies**
```python
# Problem: Hardcoded table names in loaders
def load(self, source=None, table_name="bronze_properties", ...):  # BAD
```
**Impact**: Breaks flexibility, couples loaders to specific table names

#### 2. **Duplicate Processing Hierarchies**
- Old system: `EntityProcessor` → `PropertyProcessor`
- New system: `PropertySilverProcessor`, `PropertyGoldProcessor`
- Both exist simultaneously!

#### 3. **Incomplete Entity Coverage**
```python
# DocumentConverter only handles properties
def convert_gold_properties_to_documents(...)  # EXISTS
def convert_gold_neighborhoods_to_documents(...)  # MISSING!
def convert_gold_wikipedia_to_documents(...)  # MISSING!
```

#### 4. **Type Safety Issues**
```python
# Inconsistent return types
return SimpleNamespace(table_name=output_table)  # Property orchestrator
return TableIdentifier(...)  # Expected interface
```

#### 5. **Cross-Cutting Concerns Not Integrated**
- `CrossEntityEnrichmentProcessor` exists but unused
- `GeographicEnrichmentProcessor` not integrated
- No clear enrichment phase in pipeline

## Proposed Clean Architecture

### Layer 1: Data Loading (Entity-Agnostic)
```
BaseLoader (abstract)
    ├── PropertyLoader      (loads properties)
    ├── NeighborhoodLoader  (loads neighborhoods)
    └── WikipediaLoader     (loads wikipedia)

Rules:
- NO hardcoded table names
- NO entity-specific logic in base
- ALWAYS use DuckDB STRUCT for nested data
```

### Layer 2: Processing (Entity-Specific)
```
Tier Processors (per entity, per tier):
    Properties:
        ├── PropertySilverProcessor
        └── PropertyGoldProcessor
    Neighborhoods:
        ├── NeighborhoodSilverProcessor
        └── NeighborhoodGoldProcessor
    Wikipedia:
        ├── WikipediaSilverProcessor
        └── WikipediaGoldProcessor

Rules:
- Each processor handles ONE entity type
- Each processor handles ONE tier transformation
- Consistent interface: process(input_table: str) -> str
```

### Layer 3: Orchestration (Entity Pipelines)
```
BaseEntityOrchestrator (abstract)
    ├── PropertyPipelineOrchestrator
    ├── NeighborhoodPipelineOrchestrator
    └── WikipediaPipelineOrchestrator

MainPipelineOrchestrator (coordinates all entities)

Rules:
- Each orchestrator owns its entity's complete pipeline
- Consistent Bronze → Silver → Gold flow
- Optional enrichment phase after Gold
```

### Layer 4: Cross-Entity Enrichment (Optional)
```
EnrichmentOrchestrator
    ├── Property-Neighborhood enrichment
    ├── Property-Wikipedia enrichment
    └── Neighborhood aggregations

Rules:
- ONLY runs after all Gold tiers complete
- OPTIONAL - can be skipped
- Creates enriched_ tables, preserves originals
```

### Layer 5: Output (Entity-Aware)
```
WriterOrchestrator
    ├── ElasticsearchWriter
    │   ├── PropertyTransformer
    │   ├── NeighborhoodTransformer
    │   └── WikipediaTransformer
    └── ParquetWriter

Rules:
- Entity-specific transformations for output
- Handles format conversions (Decimal → float)
- Preserves nested structures
```

## Key Design Principles

### 1. **Single Responsibility**
Each class has ONE clear purpose:
- Loaders: Load data into DuckDB
- Processors: Transform between tiers
- Orchestrators: Coordinate pipeline flow
- Writers: Output to destinations

### 2. **Entity Isolation**
Entity-specific logic is ONLY in entity-specific classes:
- No `if entity_type == "property"` conditionals
- No mixed entity processing
- Clear boundaries between entities

### 3. **Consistent Interfaces**
All similar components share interfaces:
```python
# All processors
def process(input_table: str) -> str

# All orchestrators  
def run(sample_size: Optional[int]) -> Dict[str, Any]

# All loaders
def load(table_name: str, sample_size: Optional[int]) -> str
```

### 4. **Type Safety**
Strong typing throughout:
```python
# Not this
def process(data: Dict[str, Any]) -> Any

# But this
def process(input_table: TableIdentifier) -> ProcessedTable
```

### 5. **Configuration-Driven**
Entity-specific configuration:
```yaml
entities:
  properties:
    validation:
      required_fields: ["listing_id", "price"]
      min_price: 0
    processing:
      denormalize_fields: ["city", "state", "bedrooms"]
    embedding:
      fields: ["description", "amenities", "features"]
  
  neighborhoods:
    validation:
      required_fields: ["neighborhood_id", "name"]
    processing:
      aggregate_metrics: true
    embedding:
      fields: ["characteristics", "demographics"]
```

## Migration Path

### Phase 1: Quick Fixes (4 hours)
1. Remove hardcoded table names from loaders
2. Delete old EntityProcessor hierarchy
3. Fix return type inconsistencies

### Phase 2: Complete Entity Separation (1 day)
4. Create entity-specific document converters
5. Add entity-aware configuration
6. Implement pipeline registry

### Phase 3: Polish (1 day)
7. Add comprehensive tests
8. Add type hints everywhere
9. Standardize error handling

## Expected Outcomes

### Before Refactoring
- Mixed concerns throughout codebase
- Hardcoded values limiting flexibility
- Duplicate processing paths
- Incomplete entity coverage
- Type safety issues

### After Refactoring
- ✅ Clean entity separation
- ✅ No hardcoded dependencies
- ✅ Single processing path per entity
- ✅ Complete entity coverage
- ✅ Full type safety
- ✅ 100% test coverage
- ✅ Easy to add new entities
- ✅ Maintainable and extensible

## Performance Considerations

The refactoring maintains all performance gains:
- Nested structures preserved (45x faster)
- DuckDB STRUCT types used throughout
- No unnecessary flattening/reconstruction
- Efficient batch processing

## Conclusion

The SQUACK pipeline has good bones but needs targeted refactoring to achieve true modularity. The proposed changes will:
1. Eliminate all hardcoded dependencies
2. Create clear entity boundaries
3. Improve type safety
4. Enable easy extension
5. Maintain performance gains

Total effort: ~2.5 days
Risk: Low (changes are mostly structural)
Impact: High (much cleaner, more maintainable code)