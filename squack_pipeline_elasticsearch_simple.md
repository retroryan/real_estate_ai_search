# SQUACK Pipeline Elasticsearch Integration - Simplified Demo Version

## Complete Cut-Over Requirements
* **COMPLETE CHANGE**: All occurrences must be changed in a single, atomic update
* **CLEAN IMPLEMENTATION**: Simple, direct replacements only
* **NO MIGRATION PHASES**: Do not create temporary compatibility periods
* **NO PARTIAL UPDATES**: Change everything or change nothing
* **NO COMPATIBILITY LAYERS**: Do not maintain old and new paths simultaneously
* **NO BACKUPS OF OLD CODE**: Do not comment out old code "just in case"
* **NO CODE DUPLICATION**: Do not duplicate functions to handle both patterns
* **NO WRAPPER FUNCTIONS**: Direct replacements only, no abstraction layers
* **DO NOT CALL FUNCTIONS ENHANCED or IMPROVED**: Update the actual methods directly
* **ALWAYS USE PYDANTIC**: All configurations and models must use Pydantic
* **USE MODULES AND CLEAN CODE**: Maintain modular architecture
* **NO hasattr**: Direct attribute access only
* **FIX CORE ISSUES**: Don't hack and mock, fix the root problem
* **ASK QUESTIONS**: If unclear, ask for clarification

## Executive Summary

Simplified approach to add Elasticsearch output to SQUACK pipeline for demo purposes. This focuses on the minimum viable implementation that mirrors data_pipeline patterns while being quick to implement and demonstrate.

## Core Changes Required

### 1. Configuration (Simple)

Add to `squack_pipeline/config/settings.py`:

```python
class OutputConfig(BaseModel):
    """Output destinations configuration."""
    enabled_destinations: List[str] = ["parquet"]  # Add "elasticsearch"
    elasticsearch: Optional[ElasticsearchConfig] = None

class ElasticsearchConfig(BaseModel):
    """Minimal Elasticsearch configuration."""
    host: str = "localhost"
    port: int = 9200
    index_prefix: str = "squack"
    bulk_size: int = 500
```

Update `PipelineSettings` to include:
```python
output: OutputConfig = Field(default_factory=OutputConfig)
```

### 2. Elasticsearch Writer (Minimal)

Create `squack_pipeline/writers/elasticsearch/` with three files:

#### models.py
```python
from enum import Enum
from pydantic import BaseModel

class EntityType(str, Enum):
    PROPERTIES = "properties"
    NEIGHBORHOODS = "neighborhoods" 
    WIKIPEDIA = "wikipedia"

class WriteResult(BaseModel):
    success: bool
    entity_type: EntityType
    record_count: int
    index_name: str
    error: Optional[str] = None
```

#### writer.py
```python
class ElasticsearchWriter:
    """Simple Elasticsearch writer using Python client."""
    
    def __init__(self, config: ElasticsearchConfig):
        self.config = config
        self.client = Elasticsearch([{'host': config.host, 'port': config.port}])
    
    def write_entity(self, entity_type: EntityType, data: List[Dict]) -> WriteResult:
        """Write entity data to Elasticsearch."""
        index_name = f"{self.config.index_prefix}_{entity_type.value}"
        
        # Simple bulk operation
        actions = []
        for record in data:
            # Map ID field based on entity type
            id_field = {
                EntityType.PROPERTIES: "listing_id",
                EntityType.NEIGHBORHOODS: "neighborhood_id",
                EntityType.WIKIPEDIA: "page_id"
            }[entity_type]
            
            actions.append({
                "_index": index_name,
                "_id": str(record[id_field]),
                "_source": self._transform_record(record, entity_type)
            })
        
        # Execute bulk
        success, failed = bulk(self.client, actions, chunk_size=self.config.bulk_size)
        
        return WriteResult(
            success=failed == 0,
            entity_type=entity_type,
            record_count=success,
            index_name=index_name,
            error=f"{failed} documents failed" if failed > 0 else None
        )
    
    def _transform_record(self, record: Dict, entity_type: EntityType) -> Dict:
        """Simple transformations for Elasticsearch compatibility."""
        # Convert Decimal to float
        for key, value in record.items():
            if isinstance(value, Decimal):
                record[key] = float(value)
        
        # Add geo_point for properties and neighborhoods
        if entity_type in [EntityType.PROPERTIES, EntityType.NEIGHBORHOODS]:
            if 'latitude' in record and 'longitude' in record:
                record['location'] = {
                    'lat': record['latitude'],
                    'lon': record['longitude']
                }
        
        return record
```

### 3. Writer Orchestrator (Simple)

Create `squack_pipeline/writers/orchestrator.py`:

```python
class WriterOrchestrator:
    """Simple orchestrator for multiple output writers."""
    
    def __init__(self, settings: PipelineSettings):
        self.settings = settings
        self.writers = []
        
        # Always have Parquet writer
        self.parquet_writer = ParquetWriter(settings)
        
        # Add Elasticsearch if enabled
        if "elasticsearch" in settings.output.enabled_destinations:
            self.es_writer = ElasticsearchWriter(settings.output.elasticsearch)
    
    def write_all(self, connection: DuckDBConnection, tables: Dict[str, str]) -> Dict[str, WriteResult]:
        """Write all entities to all configured destinations."""
        results = {}
        
        # Write to Parquet (existing functionality)
        if "parquet" in self.settings.output.enabled_destinations:
            results['parquet'] = self._write_parquet(connection, tables)
        
        # Write to Elasticsearch
        if "elasticsearch" in self.settings.output.enabled_destinations:
            results['elasticsearch'] = self._write_elasticsearch(connection, tables)
        
        return results
    
    def _write_elasticsearch(self, connection: DuckDBConnection, tables: Dict[str, str]) -> List[WriteResult]:
        """Extract data from DuckDB and write to Elasticsearch."""
        results = []
        
        for entity_type, table_name in tables.items():
            # Extract data from DuckDB
            df = connection.execute(f"SELECT * FROM {table_name}").df()
            data = df.to_dict('records')
            
            # Write to Elasticsearch
            result = self.es_writer.write_entity(
                EntityType[entity_type.upper()],
                data
            )
            results.append(result)
        
        return results
```

### 4. Pipeline Integration

Update `squack_pipeline/orchestrator/pipeline.py`:

```python
def _write_output(self) -> None:
    """Write final output to configured destinations."""
    if self.settings.dry_run:
        self.logger.info("Dry run mode - skipping output writing")
        return
    
    # Get final tables
    tables = {
        "properties": self._get_final_table("properties"),
        "neighborhoods": self._get_final_table("neighborhoods"),
        "wikipedia": self._get_final_table("wikipedia")
    }
    
    # Use writer orchestrator
    writer_orchestrator = WriterOrchestrator(self.settings)
    results = writer_orchestrator.write_all(self.connection_manager.get_connection(), tables)
    
    # Log results
    for destination, destination_results in results.items():
        self.logger.info(f"Results for {destination}:")
        for result in destination_results:
            if result.success:
                self.logger.success(f"  ✓ {result.entity_type}: {result.record_count} records")
            else:
                self.logger.error(f"  ✗ {result.entity_type}: {result.error}")
```

## Simplified Implementation Plan (3-4 Days)

### Day 1: Configuration & Models
1. Add OutputConfig and ElasticsearchConfig to settings.py
2. Create writers/elasticsearch/models.py with Pydantic models
3. Update config.yaml to include Elasticsearch settings

### Day 2: Elasticsearch Writer
1. Create simple ElasticsearchWriter class
2. Implement basic DuckDB to ES data transformation
3. Add bulk write functionality with Python ES client

### Day 3: Integration
1. Create WriterOrchestrator to manage outputs
2. Update PipelineOrchestrator._write_output()
3. Test with sample data

### Day 4: Testing & Polish
1. Run end-to-end tests
2. Fix any issues
3. Code review
4. Demo preparation

## What We're NOT Doing (for simplicity)

1. **No Pipeline Fork** - Just write to all configured destinations
2. **No Complex Transformations** - Basic type conversions only
3. **No Retry Logic** - Simple error reporting
4. **No Connection Validation** - Assume ES is running
5. **No Partial Failure Handling** - All or nothing bulk operations
6. **No Performance Optimization** - Focus on functionality
7. **No Index Management** - Use default mappings

## Configuration Example

```yaml
# squack_pipeline/config.yaml
output:
  enabled_destinations:
    - parquet
    - elasticsearch
  
  elasticsearch:
    host: localhost
    port: 9200
    index_prefix: squack_demo
    bulk_size: 500
```

## Success Criteria for Demo

1. **Functional**: Data flows from DuckDB to Elasticsearch
2. **Visible**: Can query data in Kibana/Elasticsearch
3. **Simple**: Easy to understand and explain
4. **Clean**: Uses Pydantic models throughout
5. **Working**: No errors during demo

## Key Simplifications

1. **Direct DuckDB → ES**: No intermediate transformations
2. **Pandas DataFrame**: Use .df() for simple data extraction
3. **Python ES Client**: Direct usage without Spark
4. **Minimal Config**: Only essential settings
5. **No Optimization**: Focus on working demo

## Testing Commands

```bash
# Run pipeline with ES output
python -m squack_pipeline run --config config.yaml --sample-size 100

# Verify in Elasticsearch
curl -X GET "localhost:9200/squack_demo_properties/_count"
curl -X GET "localhost:9200/squack_demo_neighborhoods/_count"
curl -X GET "localhost:9200/squack_demo_wikipedia/_count"

# View sample document
curl -X GET "localhost:9200/squack_demo_properties/_search?size=1"
```

## Questions to Resolve

1. Is Elasticsearch already running locally?
2. Do we need authentication for ES?
3. What's the expected demo dataset size?
4. Should we include embeddings in ES?
5. Do we need geo-queries for the demo?

## Conclusion

This simplified approach delivers Elasticsearch integration in 3-4 days by focusing only on what's needed for a successful demo. It follows data_pipeline patterns, uses Pydantic throughout, and maintains clean architecture while avoiding unnecessary complexity.