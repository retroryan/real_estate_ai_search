# Phase 1 Testing Guide

## Overview

Phase 1 implements the pipeline fork infrastructure that enables routing DataFrames to graph or search processing paths after text processing completes. This guide provides instructions for testing the implementation.

## Prerequisites

Ensure you have the following installed:
- Python 3.10+
- Apache Spark
- Neo4j (if testing graph writes)
- Required Python packages

## Test Components

### Unit Tests

Run the unit tests for the PipelineFork class:

```bash
python -m pytest data_pipeline/tests/test_pipeline_fork.py -v
```

### Integration Test

Run the comprehensive Phase 1 integration test:

```bash
python test_phase1_fork.py
```

This test verifies:
1. Fork configuration loading
2. Fork routing logic
3. Pipeline integration with fork
4. Graph path remains unchanged

## Manual Testing

### Test 1: Verify Fork Configuration

Check that the fork configuration is properly loaded:

```python
from data_pipeline.config.loader import load_configuration

config = load_configuration()
print(f"Fork enabled paths: {config.fork.enabled_paths}")
```

Expected output:
```
Fork enabled paths: ['graph']
```

### Test 2: Run Pipeline with Graph Path Only

Run the pipeline with only the graph path enabled:

```bash
python -m data_pipeline --sample-size 5
```

Expected behavior:
- Pipeline runs normally
- Graph entities are extracted
- Neo4j write completes (if configured)
- No search path messages appear

### Test 3: Enable Search Path (Preparation for Phase 2)

Edit `data_pipeline/config.yaml`:

```yaml
fork:
  enabled_paths:
    - graph
    - search  # Uncomment this line
```

Run the pipeline:

```bash
python -m data_pipeline --sample-size 5
```

Expected output should include:
```
🔀 Fork point: Routing to processing paths...
   📊 Processing graph path...
   🔍 Search path enabled but not yet implemented (Phase 2)
```

### Test 4: Validate DataFrame Routing

Use Python interactive session:

```python
from pyspark.sql import SparkSession
from data_pipeline.core.pipeline_fork import PipelineFork, ForkConfiguration

# Create Spark session
spark = SparkSession.builder.appName("test").master("local[1]").getOrCreate()

# Create test DataFrames
properties_df = spark.createDataFrame([("p1", 100000)], ["id", "price"])
neighborhoods_df = spark.createDataFrame([("n1", "Downtown")], ["id", "name"])
wikipedia_df = spark.createDataFrame([("w1", "Article")], ["id", "title"])

# Test fork routing
fork_config = ForkConfiguration(enabled_paths=["graph", "search"])
fork = PipelineFork(fork_config)

result, routed = fork.route(properties_df, neighborhoods_df, wikipedia_df)
print(f"Graph success: {result.graph_success}")
print(f"Search success: {result.search_success}")
print(f"Routed paths: {list(routed.keys())}")
```

Expected output:
```
Graph success: True
Search success: True
Routed paths: ['graph', 'search']
```

## Verification Checklist

✅ **Configuration**
- [ ] Fork configuration section exists in config.yaml
- [ ] ForkConfig added to PipelineConfig model
- [ ] Default configuration has only 'graph' enabled

✅ **Code Structure**
- [ ] PipelineFork class created with clean Pydantic models
- [ ] No caching implemented (deferred to later phase)
- [ ] Fork integrated after text processing in pipeline_runner.py

✅ **Functionality**
- [ ] DataFrames route correctly to enabled paths
- [ ] Graph path continues to work unchanged
- [ ] Search path can be enabled but shows "not implemented" message
- [ ] No errors when running with sample data

✅ **Testing**
- [ ] Unit tests pass
- [ ] Integration test passes
- [ ] Manual pipeline run completes successfully

## Common Issues and Solutions

### Issue: ImportError for PipelineFork

**Solution:** Ensure you're in the project root directory when running tests.

### Issue: Fork configuration not found

**Solution:** Check that config.yaml has the fork section and that you're using the latest configuration loader.

### Issue: Pipeline fails with fork enabled

**Solution:** Verify that:
1. The fork is placed after text processing (not after entity extraction)
2. All DataFrames are passed to the fork (properties, neighborhoods, wikipedia)
3. The fork handles None DataFrames gracefully

## Performance Validation

The fork should add minimal overhead. To verify:

1. Run pipeline without fork (comment out fork code temporarily)
2. Run pipeline with fork enabled
3. Compare execution times

Expected overhead: < 1% for small datasets, negligible for large datasets

## Next Steps

With Phase 1 complete, you can proceed to:
- Phase 2: Elasticsearch Separation
- Phase 3: Property Document Implementation
- Phase 4: Neighborhood Document Implementation
- Phase 5: Wikipedia Document Implementation
- Phase 6: Integration and Testing

## Summary

Phase 1 successfully implements a minimal, clean pipeline fork that:
- Routes DataFrames to processing paths based on configuration
- Preserves existing graph processing functionality
- Uses Pydantic models throughout
- Adds minimal overhead
- Sets the foundation for search path implementation