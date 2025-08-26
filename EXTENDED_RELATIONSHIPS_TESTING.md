# Extended Relationship Testing

## Quick Test

Run the comprehensive Extended relationship test:

```bash
PYTHONPATH=. python test_extended_relationships.py
```

## Individual Relationship Tests

Test specific relationship types by modifying the test script to run only specific test functions:

### HAS_FEATURE Relationships
```bash
PYTHONPATH=. python -c "from test_extended_relationships import *; spark = create_spark_session(); test_has_feature_relationships(spark); spark.stop()"
```

### OF_TYPE Relationships
```bash
PYTHONPATH=. python -c "from test_extended_relationships import *; spark = create_spark_session(); test_of_type_relationships(spark); spark.stop()"
```

### IN_PRICE_RANGE Relationships
```bash
PYTHONPATH=. python -c "from test_extended_relationships import *; spark = create_spark_session(); test_in_price_range_relationships(spark); spark.stop()"
```

### IN_COUNTY Relationships
```bash
PYTHONPATH=. python -c "from test_extended_relationships import *; spark = create_spark_session(); test_in_county_relationships(spark); spark.stop()"
```

### IN_TOPIC_CLUSTER Relationships
```bash
PYTHONPATH=. python -c "from test_extended_relationships import *; spark = create_spark_session(); test_in_topic_cluster_relationships(spark); spark.stop()"
```

## Full Pipeline Test with Extended

Run the complete pipeline with all Extended relationships:

```bash
PYTHONPATH=. python -m data_pipeline --sample-size 5 --test-mode
```

## Verify Relationship Creation

Check that Extended relationships are created in the pipeline output:

```bash
PYTHONPATH=. python -c "
from data_pipeline.core.pipeline_runner import DataPipelineRunner
runner = DataPipelineRunner()
result = runner.run_full_pipeline_with_embeddings()
relationships = runner._build_relationships(result)
print('Extended Relationships Created:')
for rel_type in ['has_feature', 'of_type', 'in_price_range', 'neighborhood_in_county', 'property_in_topic', 'neighborhood_in_topic']:
    if rel_type in relationships:
        print(f'  ✓ {rel_type}')
"
```

## Expected Output

When successful, you should see:
- ✅ All 6 relationship test categories passing
- 🎉 Message confirming Extended relationships are working
- Relationship counts for each type
- Sample relationships displayed for verification