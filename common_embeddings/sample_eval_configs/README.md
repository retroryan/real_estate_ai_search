# Sample Evaluation Configurations

This directory contains sample configuration files for evaluating embedding models. Copy these files to create your own `eval_configs/` directory.

## Quick Start

```bash
# Copy all sample configs to create your eval_configs
cp -r ../sample_eval_configs ../eval_configs

# Or copy specific configs you need
cp voyage.yaml ../eval_configs/
cp nomic.yaml ../eval_configs/
```

## Configuration Files

### Model-Specific Configs

- **`nomic.yaml`** - Configuration for Nomic embeddings via Ollama
- **`mxbai.yaml`** - Configuration for MxBai embeddings via Ollama
- **`voyage.yaml`** - Configuration for Voyage AI cloud embeddings

### Base and Test Configs

- **`eval.config.yaml`** - Base configuration template with all available options
- **`test.config.yaml`** - Model comparison configuration for running evaluations
- **`test.config.example.yaml`** - Example test configuration with comments

### Dataset-Specific Configs

#### Bronze Dataset (Small, for testing)
- **`eval_bronze.yaml`** - Bronze dataset with Nomic
- **`eval_bronze_mxbai.yaml`** - Bronze dataset with MxBai
- **`eval_bronze_voyage.yaml`** - Bronze dataset with Voyage

#### Gold Dataset (Full evaluation)
- **`eval_mxbai.yaml`** - Gold dataset with MxBai (default in mxbai.yaml)

### Test Comparison Configs

- **`test_bronze.config.yaml`** - Compare models on bronze dataset
- **`test_bronze_voyage.config.yaml`** - Compare all three models including Voyage

## Usage

1. Copy the configs you need to `../eval_configs/`
2. Edit them to match your requirements:
   - Update API keys (or use .env file)
   - Adjust collection names
   - Select appropriate datasets (bronze/gold)
3. Run evaluations:

```bash
# Single model evaluation
python -m common_embeddings --data-type eval --config common_embeddings/eval_configs/voyage.yaml

# Compare multiple models
python common_embeddings/run_eval_comparison.py common_embeddings/eval_configs/
```

## Notes

- The `eval_configs/` directory is gitignored, so your custom configurations won't be committed
- Always use absolute paths in the configs or paths relative to where you run the command
- API keys should be stored in the `.env` file in the project root for security