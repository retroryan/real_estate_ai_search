"""
Test configuration models for model comparison.

Clean, simple Pydantic models for parsing test.config.yaml.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional
from pathlib import Path
import yaml
import logging

logger = logging.getLogger(__name__)


class ModelConfig(BaseModel):
    """Configuration for a single model to evaluate."""
    
    name: str = Field(description="Model display name")
    provider: str = Field(description="Provider (ollama, openai, etc.)")
    collection_name: Optional[str] = Field(None, description="ChromaDB collection name (auto-generated if not provided)")
    
    def generate_collection_name(self, prefix: str = "gold") -> str:
        """Generate collection name if not provided."""
        if self.collection_name:
            return self.collection_name
        # Auto-generate: {prefix}_{provider}_{model_name}
        model_clean = self.name.replace("-", "_").replace(".", "_")
        return f"{prefix}_{self.provider}_{model_clean}"


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
    base_config: Optional[str] = Field(None, description="Path to base eval config for embeddings")
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    models: List[ModelConfig] = Field(description="Models to compare")
    comparison: ComparisonConfig = Field(default_factory=ComparisonConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
    
    @validator('models')
    def validate_models(cls, v):
        """Validate that we have at least 2 models to compare."""
        if len(v) < 2:
            raise ValueError("At least 2 models required for comparison")
        return v


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
        
        logger.info(f"Loaded test config with {len(config.models)} models for comparison")
        
        # Generate collection names for models that don't have them
        for model in config.models:
            if not model.collection_name:
                model.collection_name = model.generate_collection_name()
                logger.info(f"Generated collection name for {model.name}: {model.collection_name}")
        
        return config
        
    except Exception as e:
        logger.error(f"Failed to load test config from {config_path}: {e}")
        raise