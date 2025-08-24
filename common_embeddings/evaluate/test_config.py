"""
Test configuration models for model comparison.

Clean, simple Pydantic models for parsing test.config.yaml.
"""

from pydantic import BaseModel, Field
from typing import List
from pathlib import Path
import yaml
import logging

logger = logging.getLogger(__name__)


class ModelConfig(BaseModel):
    """Configuration for a single model to evaluate."""
    
    name: str = Field(description="Model display name")
    provider: str = Field(description="Provider (ollama, openai, etc.)")
    collection_name: str = Field(description="ChromaDB collection name")


class EvaluationConfig(BaseModel):
    """Evaluation settings."""
    
    dataset: str = Field(default="gold", description="Dataset to use: gold or generated")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results to retrieve")


class ComparisonConfig(BaseModel):
    """Comparison settings."""
    
    primary_metric: str = Field(
        default="f1_score",
        description="Metric for determining winner (f1_score, precision, recall, map, mrr)"
    )


class ReportingConfig(BaseModel):
    """Reporting configuration."""
    
    format: str = Field(default="html", description="Report format (html, json, markdown)")
    output_directory: str = Field(
        default="./common_embeddings/evaluate_results/comparisons",
        description="Output directory for reports"
    )


class TestConfig(BaseModel):
    """Root test configuration for model comparison."""
    
    version: str = Field(description="Configuration version")
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    models: List[ModelConfig] = Field(description="Models to compare")
    comparison: ComparisonConfig = Field(default_factory=ComparisonConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
    
    def validate_models(self) -> bool:
        """Validate that we have at least 2 models to compare."""
        if len(self.models) < 2:
            raise ValueError("At least 2 models required for comparison")
        return True


def load_test_config(config_path: str = "common_embeddings/test.config.yaml") -> TestConfig:
    """
    Load test configuration from YAML file.
    
    Reuses the same pattern as load_config_from_yaml for consistency.
    
    Args:
        config_path: Path to test configuration file
        
    Returns:
        TestConfig object with validated settings
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Test config not found: {config_path}")
    
    try:
        with open(config_file, 'r') as f:
            data = yaml.safe_load(f)
        
        if not data:
            raise ValueError("Empty test configuration file")
        
        # Create TestConfig with validation
        config = TestConfig(**data)
        
        # Validate we have enough models
        config.validate_models()
        
        logger.info(f"Loaded test config with {len(config.models)} models for comparison")
        return config
        
    except Exception as e:
        logger.error(f"Failed to load test config from {config_path}: {e}")
        raise