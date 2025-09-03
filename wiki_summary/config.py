"""
Pydantic configuration models for Wikipedia summarization pipeline.
Provides type-safe configuration with validation and environment variable loading.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseModel):
    """Configuration for language model settings."""
    model: str = Field(default="openrouter/openai/gpt-oss-120b", description="LLM model identifier")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=2000, ge=100, le=50000, description="Maximum output tokens")  # Increased for dual summaries
    cache_enabled: bool = Field(default=True, description="Enable response caching")


class DatabaseConfig(BaseModel):
    """Configuration for database connections."""
    path: Path = Field(default=Path("data/wikipedia/wikipedia.db"), description="Path to SQLite database")
    
    @field_validator('path')
    @classmethod
    def validate_path(cls, v: Path) -> Path:
        """Ensure path is absolute and parent directory exists."""
        if not v.is_absolute():
            # Always resolve relative to current directory (assumes running from wiki_summary/)
            v = Path.cwd() / v
        v = v.resolve()  # Resolve any .. or . in the path
        v.parent.mkdir(parents=True, exist_ok=True)
        return v


class ProcessingConfig(BaseModel):
    """Configuration for processing pipeline."""
    batch_size: int = Field(default=10, ge=1, le=100, description="Batch size for processing")
    min_relevance_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum relevance threshold")
    cache_dir: Path = Field(default=Path(".cache/summaries"), description="Directory for caching")
    create_reports: bool = Field(default=True, description="Generate flagged content reports")
    
    @field_validator('cache_dir')
    @classmethod
    def validate_cache_dir(cls, v: Path) -> Path:
        """Ensure cache directory exists."""
        if not v.is_absolute():
            # Check if we're in wiki_summary directory
            current_dir = Path.cwd()
            if current_dir.name == 'wiki_summary':
                # Cache should be in wiki_summary directory
                v = current_dir / v
            else:
                # Use current directory otherwise
                v = current_dir / v
        v.mkdir(parents=True, exist_ok=True)
        return v


class PipelineConfig(BaseSettings):
    """Complete pipeline configuration with environment variable support."""
    model_config = SettingsConfigDict(
        env_file=".env",  # Always load from current directory (wiki_summary/)
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra environment variables
    )
    
    llm: LLMConfig = Field(default_factory=LLMConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)  
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    
    # Environment overrides
    llm_model: Optional[str] = Field(default=None, alias="LLM_MODEL")
    llm_temperature: Optional[float] = Field(default=None, alias="LLM_TEMPERATURE")
    llm_max_tokens: Optional[int] = Field(default=None, alias="LLM_MAX_TOKENS")
    database_path: Optional[str] = Field(default=None, alias="DATABASE_PATH")
    cache_enabled: Optional[bool] = Field(default=None, alias="CACHE_ENABLED")
    batch_size: Optional[int] = Field(default=None, alias="BATCH_SIZE")
    
    # API Keys
    openrouter_api_key: Optional[str] = Field(default=None, alias="OPENROUTER_API_KEY")
    
    def model_post_init(self, __context) -> None:
        """Apply environment overrides after initialization."""
        if self.llm_model:
            self.llm.model = self.llm_model
        if self.llm_temperature is not None:
            self.llm.temperature = self.llm_temperature
        if self.llm_max_tokens is not None:
            self.llm.max_tokens = self.llm_max_tokens
        if self.database_path:
            self.database.path = Path(self.database_path)
        if self.cache_enabled is not None:
            self.llm.cache_enabled = self.cache_enabled
        if self.batch_size is not None:
            self.processing.batch_size = self.batch_size


class ProcessingStats(BaseModel):
    """Statistics for processing run."""
    total_articles: int = Field(default=0, description="Total articles found")
    relevant_articles: int = Field(default=0, description="Articles meeting relevance threshold")
    processed_summaries: int = Field(default=0, description="Successfully processed summaries")
    flagged_articles: int = Field(default=0, description="Articles flagged as non-relevant")
    errors: int = Field(default=0, description="Processing errors encountered")
    
    @property
    def success_rate(self) -> float:
        """Calculate processing success rate."""
        if self.total_articles == 0:
            return 0.0
        return (self.processed_summaries / self.total_articles) * 100
    
    @property
    def relevance_rate(self) -> float:
        """Calculate relevance rate."""
        if self.total_articles == 0:
            return 0.0
        return (self.relevant_articles / self.total_articles) * 100


class ProcessingResults(BaseModel):
    """Complete results from processing pipeline."""
    stats: ProcessingStats
    summaries: list = Field(default_factory=list, description="Generated summaries")
    relevance_evaluations: list = Field(default_factory=list, description="Relevance evaluations")
    flagged_report_path: Optional[Path] = Field(default=None, description="Path to flagged content report")
    
    def summary_text(self) -> str:
        """Generate human-readable summary."""
        return (
            f"Processed {self.stats.processed_summaries}/{self.stats.total_articles} articles "
            f"({self.stats.success_rate:.1f}% success rate)\n"
            f"Relevant: {self.stats.relevant_articles} ({self.stats.relevance_rate:.1f}%)\n"
            f"Flagged: {self.stats.flagged_articles}\n"
            f"Errors: {self.stats.errors}"
        )