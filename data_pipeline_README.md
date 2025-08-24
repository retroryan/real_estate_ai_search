# Data Pipeline - Apache Spark Processing

A unified data pipeline for processing real estate and Wikipedia data with embeddings generation.

## Installation

From the project root directory:

```bash
pip install -e .
```

## Quick Start

### Test Mode (Fastest - 10 records)
```bash
python -m data_pipeline --test-mode
```

### Development Mode (Default - 20 records)
```bash
python -m data_pipeline
```


## Command Line Options

### Data Subsetting
Control the amount of data processed for faster testing:

```bash
# Enable subsetting with default sample size
python -m data_pipeline --subset

# Specify exact sample size
python -m data_pipeline --subset --sample-size 50

# Choose sampling method
python -m data_pipeline --subset --sample-size 30 --sample-method random
```

### Embedding Models
Select different embedding providers and models:

```bash
# Use Voyage AI (default)
python -m data_pipeline --embedding-provider voyage

# Use local Ollama
python -m data_pipeline --embedding-provider ollama --embedding-model nomic-embed-text

# Use OpenAI
python -m data_pipeline --embedding-provider openai --embedding-model text-embedding-3-small

# Use mock embeddings for testing (no API calls)
python -m data_pipeline --embedding-provider mock
```

### Spark Configuration
Control Spark resource usage:

```bash
# Use specific number of cores
python -m data_pipeline --cores 4

# Use 2 cores with custom memory (set in config)
python -m data_pipeline --cores 2
```

### Output Options
Specify where results are saved:

```bash
# Custom output path
python -m data_pipeline --output /path/to/results

# Override output format via environment
OUTPUT_FORMAT=json python -m data_pipeline
```

### Operational Commands

```bash
# Show current configuration and exit
python -m data_pipeline --show-config

# Validate configuration without running
python -m data_pipeline --validate-only

# Set logging level
python -m data_pipeline --log-level DEBUG
```

## Environment-Based Configuration

The pipeline automatically adjusts settings based on environment:

### Development (default)
- Data subsetting: Enabled (20 records)
- Spark: local[2]
- Memory: 2GB
- Debug logging available


## Common Usage Patterns

### Quick Testing
```bash
# Fastest test with mock embeddings
python -m data_pipeline --test-mode --embedding-provider mock

# Test with 5 records using Voyage
python -m data_pipeline --subset --sample-size 5

# Test with specific cores
python -m data_pipeline --test-mode --cores 2
```

### Development Workflow
```bash
# Check configuration
python -m data_pipeline --show-config

# Validate setup
python -m data_pipeline --validate-only

# Run with debug logging
python -m data_pipeline --subset --sample-size 20 --log-level DEBUG
```


## Configuration

The pipeline uses a comprehensive configuration system:

- **Config file**: `data_pipeline/config.yaml`
- **Environment variables**: Override any setting
- **CLI arguments**: Highest priority

### Key Configuration Sections

- **data_subset**: Control data sampling for testing
- **embedding**: Configure embedding providers and models
- **spark**: Spark session settings
- **processing**: Quality checks and performance options
- **output**: Format and destination settings

## Environment Variables

Override configuration via environment variables:

```bash
# Data subsetting
export DATA_SUBSET_ENABLED=true
export DATA_SUBSET_SAMPLE_SIZE=50

# Embedding provider
export EMBEDDING_PROVIDER=voyage
export VOYAGE_API_KEY=your-key-here

# Spark settings
export SPARK_MASTER=local[4]

# Run with overrides
python -m data_pipeline
```

## Troubleshooting

### Check Configuration
```bash
python -m data_pipeline --show-config
```

### Validate Environment
```bash
python -m data_pipeline --validate-only
```

### Debug Mode
```bash
python -m data_pipeline --log-level DEBUG --test-mode
```

### Common Issues

**Out of Memory**: Reduce batch size or use fewer cores
```bash
python -m data_pipeline --cores 2 --subset --sample-size 10
```

**API Rate Limits**: Use mock provider for testing
```bash
python -m data_pipeline --embedding-provider mock
```

**Slow Processing**: Enable subsetting
```bash
python -m data_pipeline --subset --sample-size 20
```

## Performance Tips

1. **For Testing**: Always use `--test-mode` or `--subset`
2. **For Development**: Use default settings (20 records)
3. **For Full Data**: Disable subsetting in config.yaml
4. **For Debugging**: Add `--log-level DEBUG`
5. **For Speed**: Use `--embedding-provider mock` during development

## Examples

### Minimal Test Run
```bash
python -m data_pipeline --test-mode --embedding-provider mock
```

### Standard Development Run
```bash
python -m data_pipeline --subset --sample-size 30
```

### Full Data Run
```bash
python -m data_pipeline --cores 8
```

### Custom Configuration
```bash
python -m data_pipeline \
  --subset --sample-size 100 \
  --embedding-provider voyage \
  --embedding-model voyage-3 \
  --cores 4 \
  --output ./results/test_run
```

## Next Steps

- Review configuration: `data_pipeline/config.yaml`
- Check logs: `logs/pipeline.log`
- Monitor output: `data/processed/unified_dataset/`
- Validate results: Use `--validate-only` before production runs