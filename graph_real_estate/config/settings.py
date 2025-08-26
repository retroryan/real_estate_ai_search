"""Application settings and configuration management"""
import os
from pathlib import Path
from typing import Optional
from functools import lru_cache
from dotenv import load_dotenv

from graph_real_estate.config.models import (
    GraphRealEstateConfig,
    DatabaseConfig,
    APIConfig,
    EmbeddingConfig,
    VectorIndexConfig,
    SearchConfig,
    VoyageModelConfig,
    OllamaModelConfig,
    OpenAIModelConfig,
    GeminiModelConfig
)

# Load environment variables
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()


class Settings:
    """Application settings manager"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize settings
        
        Args:
            config_path: Path to configuration file. If None, looks for config.yaml
                        in the graph_real_estate directory
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"
        
        self.config_path = config_path
        self._config: Optional[GraphRealEstateConfig] = None
    
    @property
    def config(self) -> GraphRealEstateConfig:
        """Lazy load configuration"""
        if self._config is None:
            self._config = self._load_config()
        return self._config
    
    def _load_config(self) -> GraphRealEstateConfig:
        """Load configuration from file or environment"""
        if self.config_path.exists():
            # Load from YAML file
            config = GraphRealEstateConfig.from_yaml(self.config_path)
        else:
            # Create default configuration with environment overrides
            config = self._create_default_config()
        
        return config
    
    def _create_default_config(self) -> GraphRealEstateConfig:
        """Create default configuration with environment variable overrides"""
        # Database configuration
        database = DatabaseConfig(
            uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            user=os.getenv('NEO4J_USERNAME', 'neo4j'),
            password=os.getenv('NEO4J_PASSWORD', 'password'),
            database=os.getenv('NEO4J_DATABASE', 'neo4j')
        )
        
        # API configuration
        api = APIConfig(
            base_url=os.getenv('API_BASE_URL', 'http://localhost:8000'),
            timeout=int(os.getenv('API_TIMEOUT', '30')),
            api_key=os.getenv('API_KEY'),
            max_retries=int(os.getenv('API_MAX_RETRIES', '3')),
            retry_delay=float(os.getenv('API_RETRY_DELAY', '1.0'))
        )
        
        # Embedding configuration
        provider = os.getenv('EMBEDDING_PROVIDER', 'voyage')
        embedding_config = {
            'provider': provider,
            'batch_size': int(os.getenv('EMBEDDING_BATCH_SIZE', '50')),
            'max_retries': int(os.getenv('EMBEDDING_MAX_RETRIES', '3')),
            'retry_delay': int(os.getenv('EMBEDDING_RETRY_DELAY', '2'))
        }
        
        # Add provider-specific configuration
        if provider == 'voyage':
            embedding_config['voyage'] = VoyageModelConfig(
                model=os.getenv('VOYAGE_MODEL', 'voyage-3'),
                api_key=os.getenv('VOYAGE_API_KEY'),
                dimension=int(os.getenv('VOYAGE_DIMENSION', '1024'))
            )
        elif provider == 'ollama':
            embedding_config['ollama'] = OllamaModelConfig(
                model=os.getenv('OLLAMA_MODEL', 'nomic-embed-text'),
                base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
                dimension=int(os.getenv('OLLAMA_DIMENSION', '768'))
            )
        elif provider == 'openai':
            embedding_config['openai'] = OpenAIModelConfig(
                model=os.getenv('OPENAI_MODEL', 'text-embedding-3-small'),
                api_key=os.getenv('OPENAI_API_KEY'),
                dimension=int(os.getenv('OPENAI_DIMENSION', '1536'))
            )
        elif provider == 'gemini':
            embedding_config['gemini'] = GeminiModelConfig(
                model=os.getenv('GEMINI_MODEL', 'models/embedding-001'),
                api_key=os.getenv('GEMINI_API_KEY'),
                dimension=int(os.getenv('GEMINI_DIMENSION', '768'))
            )
        
        embedding = EmbeddingConfig(**embedding_config)
        
        # Vector index configuration
        vector_index = VectorIndexConfig(
            index_name=os.getenv('VECTOR_INDEX_NAME', 'property_embeddings'),
            vector_dimensions=embedding.get_dimensions(),
            similarity_function=os.getenv('VECTOR_SIMILARITY_FUNCTION', 'cosine'),
            node_label=os.getenv('VECTOR_NODE_LABEL', 'Property'),
            embedding_property=os.getenv('VECTOR_EMBEDDING_PROPERTY', 'embedding'),
            source_property=os.getenv('VECTOR_SOURCE_PROPERTY', 'description')
        )
        
        # Search configuration
        search = SearchConfig(
            default_top_k=int(os.getenv('SEARCH_TOP_K', '10')),
            use_graph_boost=os.getenv('SEARCH_USE_GRAPH_BOOST', 'true').lower() == 'true',
            vector_weight=float(os.getenv('SEARCH_VECTOR_WEIGHT', '0.6')),
            graph_weight=float(os.getenv('SEARCH_GRAPH_WEIGHT', '0.2')),
            features_weight=float(os.getenv('SEARCH_FEATURES_WEIGHT', '0.2')),
            min_similarity=float(os.getenv('SEARCH_MIN_SIMILARITY', '0.01'))
        )
        
        return GraphRealEstateConfig(
            database=database,
            api=api,
            embedding=embedding,
            vector_index=vector_index,
            search=search
        )
    
    @property
    def database(self) -> DatabaseConfig:
        """Get database configuration"""
        return self.config.database
    
    @property
    def api(self) -> APIConfig:
        """Get API configuration"""
        return self.config.api
    
    @property
    def embedding(self) -> EmbeddingConfig:
        """Get embedding configuration"""
        return self.config.embedding
    
    @property
    def vector_index(self) -> VectorIndexConfig:
        """Get vector index configuration"""
        return self.config.vector_index
    
    @property
    def search(self) -> SearchConfig:
        """Get search configuration"""
        return self.config.search
    
    def reload(self) -> None:
        """Reload configuration from file"""
        self._config = None
    
    def save(self, path: Optional[Path] = None) -> None:
        """Save current configuration to file
        
        Args:
            path: Path to save configuration. If None, uses current config_path
        """
        if path is None:
            path = self.config_path
        
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            f.write(self.config.to_yaml())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get global settings instance (cached)"""
    return Settings()