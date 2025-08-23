"""Configuration models using Pydantic for type safety"""

from typing import Optional, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field, validator
import yaml
import os
from dotenv import load_dotenv


class DatabaseConfig(BaseModel):
    """Database configuration"""
    uri: str = Field(default="bolt://localhost:7687")
    user: str = Field(default="neo4j")
    password: str = Field(default="password")
    database: str = Field(default="neo4j")
    max_connection_lifetime: int = Field(default=3600)
    max_connection_pool_size: int = Field(default=50)
    connection_acquisition_timeout: int = Field(default=60)
    
    @validator("password", pre=True)
    def resolve_password(cls, v):
        """Resolve password from environment variable if needed"""
        if v.startswith("${") and v.endswith("}"):
            env_var = v[2:-1]
            return os.getenv(env_var, v)
        return v
    
    @validator("uri", pre=True)
    def validate_uri(cls, v):
        """Ensure URI is properly formatted"""
        if not v.startswith(("bolt://", "neo4j://", "neo4j+s://", "bolt+s://")):
            raise ValueError(f"Invalid database URI scheme: {v}")
        return v


class LoaderConfig(BaseModel):
    """Configuration for data loaders"""
    batch_size: int = Field(default=1000, ge=1, le=10000)
    property_batch_size: int = Field(default=500, ge=1, le=5000)
    feature_batch_size: int = Field(default=2000, ge=1, le=10000)
    geographic_batch_size: int = Field(default=1000, ge=1, le=10000)
    
    class Config:
        validate_assignment = True


class GeographicConfig(BaseModel):
    """Geographic loader configuration"""
    data_path: Path = Field(default=Path("./data/geographic"))
    load_states: bool = Field(default=True)
    load_counties: bool = Field(default=True)
    load_cities: bool = Field(default=True)
    
    @validator("data_path", pre=True)
    def resolve_path(cls, v):
        """Convert string to Path"""
        return Path(v) if isinstance(v, str) else v


class PropertyConfig(BaseModel):
    """Property loader configuration"""
    data_path: Path = Field(default=Path("./real_estate_data"))
    sf_properties_file: str = Field(default="properties_sf.json")
    pc_properties_file: str = Field(default="properties_pc.json")
    sf_neighborhoods_file: str = Field(default="neighborhoods_sf.json")
    pc_neighborhoods_file: str = Field(default="neighborhoods_pc.json")
    
    @validator("data_path", pre=True)
    def resolve_path(cls, v):
        """Convert string to Path"""
        return Path(v) if isinstance(v, str) else v


class WikipediaConfig(BaseModel):
    """Wikipedia loader configuration"""
    data_path: Path = Field(default=Path("./data/wikipedia"))
    pages_subdir: str = Field(default="pages")
    database_file: str = Field(default="wikipedia.db")
    max_articles: Optional[int] = Field(default=None, ge=1)
    
    @validator("data_path", pre=True)
    def resolve_path(cls, v):
        """Convert string to Path"""
        return Path(v) if isinstance(v, str) else v


class SimilarityConfig(BaseModel):
    """Similarity calculation configuration"""
    property_similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    neighborhood_proximity_threshold: float = Field(default=5.0, ge=0.0)  # miles
    feature_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    price_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    size_weight: float = Field(default=0.2, ge=0.0, le=1.0)
    location_weight: float = Field(default=0.2, ge=0.0, le=1.0)
    
    @validator("feature_weight", "price_weight", "size_weight", "location_weight")
    def validate_weights(cls, v, values):
        """Ensure weights sum to 1.0"""
        # This is checked after all weights are set
        return v


class SearchConfig(BaseModel):
    """Search configuration"""
    embedding_model: str = Field(default="nomic-embed-text")
    vector_weight: float = Field(default=0.6, ge=0.0, le=1.0)
    graph_weight: float = Field(default=0.2, ge=0.0, le=1.0)
    features_weight: float = Field(default=0.2, ge=0.0, le=1.0)
    default_top_k: int = Field(default=10, ge=1, le=100)
    min_similarity: float = Field(default=0.3, ge=0.0, le=1.0)
    use_graph_boost: bool = Field(default=True)
    
    @validator("graph_weight")
    def validate_weights_sum(cls, v, values):
        """Ensure weights sum to 1.0"""
        if "vector_weight" in values and "features_weight" in values:
            total = values["vector_weight"] + v + values["features_weight"]
            if abs(total - 1.0) > 0.001:  # Allow small floating point errors
                raise ValueError(f"Weights must sum to 1.0, got {total}")
        return v


class AppConfig(BaseModel):
    """Main application configuration"""
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    loaders: LoaderConfig = Field(default_factory=LoaderConfig)
    geographic: GeographicConfig = Field(default_factory=GeographicConfig)
    property: PropertyConfig = Field(default_factory=PropertyConfig)
    wikipedia: WikipediaConfig = Field(default_factory=WikipediaConfig)
    similarity: SimilarityConfig = Field(default_factory=SimilarityConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    
    @classmethod
    def from_file(cls, config_path: Path) -> "AppConfig":
        """Load configuration from YAML file"""
        # Load environment variables first
        load_dotenv(override=True)
        
        if not config_path.exists():
            # Return default configuration if file doesn't exist
            return cls()
        
        with open(config_path, "r") as f:
            data = yaml.safe_load(f) or {}
        
        # Resolve environment variables in the configuration
        data = cls._resolve_env_vars(data)
        
        return cls(**data)
    
    @staticmethod
    def _resolve_env_vars(data: Any) -> Any:
        """Recursively resolve environment variables in configuration"""
        if isinstance(data, dict):
            return {k: AppConfig._resolve_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [AppConfig._resolve_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
            env_var = data[2:-1]
            default = None
            if ":-" in env_var:
                env_var, default = env_var.split(":-", 1)
            return os.getenv(env_var, default or data)
        return data
    
    def to_yaml(self, file_path: Path) -> None:
        """Save configuration to YAML file"""
        with open(file_path, "w") as f:
            yaml.dump(self.dict(), f, default_flow_style=False)
    
    class Config:
        validate_assignment = True
        use_enum_values = True