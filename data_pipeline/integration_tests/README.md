# Data Pipeline Integration Tests

This directory contains comprehensive integration tests for the data pipeline, focusing on validating Parquet output files, schema compliance, data quality, and end-to-end pipeline execution.

## Test Structure

### Core Test Files

- **`test_parquet_validation.py`** - Focused tests for Parquet file structure, schema, and content validation
- **`test_pipeline_output_validation.py`** - Comprehensive end-to-end pipeline validation tests
- **`conftest.py`** - Pytest configuration and shared fixtures
- **`run_tests.py`** - Convenient test runner script

### Test Categories

1. **Smoke Tests** - Quick validation of basic functionality
2. **Parquet Tests** - Comprehensive validation of Parquet output files
3. **Schema Tests** - Validation of data schemas and types
4. **Data Quality Tests** - Validation of data completeness and correctness
5. **Integration Tests** - End-to-end pipeline execution validation

## Running Tests

### Quick Start

```bash
# Run smoke tests (fastest)
python data_pipeline/integration_tests/run_tests.py smoke

# Run Parquet validation tests
python data_pipeline/integration_tests/run_tests.py parquet

# Run all integration tests
python data_pipeline/integration_tests/run_tests.py full
```

### Using pytest directly

```bash
# Run all integration tests
pytest data_pipeline/integration_tests/ -v

# Run only Parquet tests
pytest data_pipeline/integration_tests/test_parquet_validation.py -v

# Run smoke tests only
pytest -m smoke -v

# Run non-slow tests
pytest -m "not slow" -v

# Run with specific output format
pytest data_pipeline/integration_tests/ -v --tb=short --color=yes
```

### Test Markers

Tests are marked with the following categories:

- `@pytest.mark.integration` - Full pipeline integration tests
- `@pytest.mark.parquet` - Parquet-specific validation tests  
- `@pytest.mark.smoke` - Quick smoke tests
- `@pytest.mark.slow` - Tests that take longer to run

## What the Tests Validate

### Parquet File Validation

- **File Structure**: Verifies Parquet files are created with correct directory structure
- **Schema Compliance**: Validates column names, data types, and array structures
- **Data Completeness**: Ensures all records have required fields populated
- **Embedding Quality**: Validates embedding dimensions and completeness
- **Array Fields**: Verifies Wikipedia `categories` and `key_topics` are proper arrays

### Data Quality Checks

- **Embedding Coverage**: Ensures all records have embeddings generated
- **Correlation IDs**: Validates correlation IDs are present for tracking
- **Schema Consistency**: Verifies consistent data types across records
- **Content Validation**: Checks for appropriate data ranges and formats

### Pipeline Integration

- **End-to-End Execution**: Validates complete pipeline runs without errors
- **Output Destinations**: Verifies data is written to configured outputs
- **Processing Statistics**: Validates record counts and processing metrics
- **Error Handling**: Tests pipeline behavior with various configurations

## Configuration

### Test Settings

Tests use a test-specific configuration with:
- Small sample sizes for faster execution
- Temporary output directories
- Real embedding providers (for integration fidelity)
- Appropriate timeouts and retry settings

### Environment Variables

Set these environment variables if needed:
```bash
export VOYAGE_API_KEY=your-key-here  # For embedding tests
export PYTHONPATH=/path/to/project:$PYTHONPATH
```

### Dependencies

Required packages for running tests:
```bash
pip install pytest pyspark pandas
```

Optional packages for enhanced testing:
```bash
pip install pytest-cov pytest-timeout pytest-xdist
```

## Test Output

### Success Indicators

- ✅ All Parquet files created successfully
- ✅ Schema validation passed for all entity types
- ✅ 100% embedding coverage achieved
- ✅ Data quality thresholds met
- ✅ Array fields properly populated

### Quality Metrics

Tests validate these quality thresholds:
- **Embedding Coverage**: ≥95% of records have embeddings
- **Correlation ID Coverage**: ≥95% of records have correlation IDs  
- **Wikipedia Categories**: ≥80% of articles have category data
- **Wikipedia Topics**: ≥90% of articles have key topics data
- **Schema Compliance**: 100% schema conformity required

## Troubleshooting

### Common Issues

1. **Spark Session Conflicts**: Ensure no other Spark applications are running
2. **Memory Issues**: Reduce sample sizes in test configuration
3. **API Key Issues**: Verify embedding provider credentials are set
4. **File Permissions**: Ensure write permissions to temp directories

### Debug Mode

Run tests with additional debugging:
```bash
pytest data_pipeline/integration_tests/ -v -s --tb=long --log-cli-level=DEBUG
```

### Test Data

Tests use the same data sources as the main pipeline but with smaller sample sizes:
- Properties: SF and Park City real estate data
- Neighborhoods: Geographic neighborhood data  
- Wikipedia: Location-related Wikipedia articles

## Extending Tests

### Adding New Test Cases

1. Create test methods in appropriate test classes
2. Use shared fixtures from `conftest.py`
3. Add appropriate markers (`@pytest.mark.parquet`, etc.)
4. Follow naming conventions (`test_*`)

### Custom Validation

Add entity-specific validation by extending the `_validate_*_schema` methods in `test_parquet_validation.py`.

### Performance Testing

For performance testing, create tests marked with `@pytest.mark.slow` and use larger sample sizes.