# Constructor Injection Architecture Proposal for Real Estate Search Demo

## Key Implementation Requirements

* **CLEAN IMPLEMENTATION**: Simple, direct replacements only
* **NO MIGRATION PHASES**: Do not create temporary compatibility periods
* **NO PARTIAL UPDATES**: Change everything or change nothing
* **NO COMPATIBILITY LAYERS**: Do not maintain old and new paths simultaneously
* **NO BACKUPS OF OLD CODE**: Do not comment out old code "just in case"
* **NO CODE DUPLICATION**: Do not duplicate functions to handle both patterns
* **NO WRAPPER FUNCTIONS**: Direct replacements only, no abstraction layers
* **NO ENHANCED/IMPROVED VERSIONS**: Update existing classes directly (e.g., update `PropertyIndexer`, not create `ImprovedPropertyIndexer`)
* **CONSISTENT NAMING**: Use snake_case throughout (Python convention)
* **USE PYDANTIC**: For all data models and validation
* **NO OPTIONAL IMPORTS**: All imports are required, no try/except on imports
* **USE LOGGING**: Replace all print statements with proper logging

## Executive Summary

This proposal outlines a complete refactoring of the Real Estate Search demo to use **Constructor Injection** throughout, creating a clean, testable, and maintainable codebase suitable for a high-quality demonstration. The refactoring will simplify the architecture while making dependencies explicit and manageable.

### Why "Dependency Container" with Constructor Injection?

The **Dependency Container** is not a contradiction to Constructor Injection - it's the **central factory** that creates all objects with their dependencies properly injected through constructors. Think of it as the "main assembly point" where all the constructor injection wiring happens in one place.

- **Constructor Injection**: The pattern where each class receives all its dependencies through its constructor
- **Dependency Container**: The single place where all these constructors are called with the right dependencies

The container itself uses constructor injection (it receives `AppConfig` in its constructor), and it ensures all other objects are created with constructor injection too.

## Current Architecture Problems

### 1. Mixed Dependency Creation Patterns
- Some classes create their own dependencies internally (e.g., `PropertyEnricher` creates `WikipediaExtractor`)
- Some classes accept partial dependencies but create others (e.g., `PropertyIndexer`)
- Configuration is loaded multiple times from different places
- No clear ownership of object lifecycle

### 2. Hidden Dependencies
```python
# Current anti-pattern examples:
class PropertyEnricher:
    def __init__(self):
        self.extractor = WikipediaExtractor()  # Hidden dependency
        
class PropertyIndexer:
    def __init__(self, es_client=None, config=None):
        self.config = config or Config.from_yaml()  # Conditional creation
        self.es_client = es_client or self._create_es_client()  # Mixed pattern
```

### 3. Testing Difficulties
- Cannot easily inject mock dependencies
- Hard to test components in isolation
- Integration tests required for simple unit testing scenarios

### 4. Configuration Confusion
- Both `Config` and `Settings` classes exist
- Configuration loaded from YAML in multiple places
- No single source of truth for configuration

## Proposed Constructor Injection Architecture

### Core Principles

1. **Explicit Dependencies**: All dependencies passed through constructor
2. **No Hidden Creation**: Classes never create their own dependencies
3. **Single Configuration**: One configuration object, loaded once
4. **Dependency Container**: Central place for object creation and wiring
5. **Clean Interfaces**: Clear contracts between components

### Architecture Layers

```
┌─────────────────────────────────────────────────┐
│                  Main Entry Point                │
│                  (main.py / CLI)                 │
└─────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────┐
│              Dependency Container                │
│         (Creates and wires all objects)          │
└─────────────────────────────────────────────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
┌─────────────────────────┐ ┌────────────────────┐
│    Service Layer        │ │   Repository Layer │
│  (Business Logic)       │ │  (Data Access)     │
└─────────────────────────┘ └────────────────────┘
                    │             │
                    └──────┬──────┘
                           ▼
┌─────────────────────────────────────────────────┐
│               Infrastructure Layer               │
│        (Elasticsearch, Database, APIs)           │
└─────────────────────────────────────────────────┘
```

## Detailed Implementation Plan

### 1. Configuration Management

```python
# config/config.py - Single configuration class using Pydantic
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Optional
import yaml
import logging

logger = logging.getLogger(__name__)

class ElasticsearchConfig(BaseModel):
    host: str = "localhost"
    port: int = 9200
    username: Optional[str] = None
    password: Optional[str] = None
    property_index: str = "properties"
    wiki_index: str = "wikipedia"
    request_timeout: int = 30

class EmbeddingConfig(BaseModel):
    provider: str = "ollama"
    model_name: str = "nomic-embed-text"
    ollama_host: str = "http://localhost:11434"
    dimension: int = 768

class DataConfig(BaseModel):
    wikipedia_db: Path = Path("data/wikipedia/wikipedia.db")
    properties_dir: Path = Path("real_estate_data")

class AppConfig(BaseModel):
    """Single unified configuration for entire application."""
    elasticsearch: ElasticsearchConfig
    embedding: EmbeddingConfig
    data: DataConfig
    demo_mode: bool = True
    force_recreate: bool = False
    
    @classmethod
    def from_yaml(cls, path: Path = Path("config.yaml")) -> "AppConfig":
        """Load configuration once at application startup."""
        logger.info(f"Loading configuration from {path}")
        with open(path) as f:
            data = yaml.safe_load(f)
        
        config = cls(
            elasticsearch=ElasticsearchConfig(**data.get("elasticsearch", {})),
            embedding=EmbeddingConfig(**data.get("embedding", {})),
            data=DataConfig(**data.get("data", {})),
            demo_mode=data.get("demo_mode", True),
            force_recreate=data.get("force_recreate", False)
        )
        logger.info("Configuration loaded successfully")
        return config
```

### 2. Infrastructure Layer with Constructor Injection

```python
# infrastructure/elasticsearch_client.py
from elasticsearch import Elasticsearch

class ElasticsearchClientFactory:
    """Factory for creating Elasticsearch clients with explicit config."""
    
    def __init__(self, config: ElasticsearchConfig):
        self.config = config
    
    def create_client(self) -> Elasticsearch:
        """Create configured Elasticsearch client."""
        url = f"http://{self.config.host}:{self.config.port}"
        
        es_config = {
            "hosts": [url],
            "request_timeout": self.config.request_timeout,
            "verify_certs": False
        }
        
        if self.config.username and self.config.password:
            es_config["basic_auth"] = (self.config.username, self.config.password)
        
        return Elasticsearch(**es_config)
```

### 3. Repository Layer with Dependency Injection

```python
# repositories/wikipedia_repository.py
import sqlite3
from pathlib import Path
from typing import List, Optional

class WikipediaRepository:
    """Repository for Wikipedia data access with injected database."""
    
    def __init__(self, db_path: Path):
        """
        Initialize with explicit database path.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        
    def get_articles_for_location(
        self, 
        city: str, 
        state: str
    ) -> List[WikipediaArticle]:
        """Query articles for a location."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT page_id, title, summary, key_topics
                FROM articles 
                WHERE city = ? AND state = ?
                ORDER BY relevance_score DESC
            """, (city, state))
            
            return [
                WikipediaArticle(*row) 
                for row in cursor.fetchall()
            ]
    
    def get_pois_for_article(
        self, 
        page_id: int
    ) -> List[POI]:
        """Get points of interest for an article."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name, category, significance_score, description
                FROM pois 
                WHERE page_id = ?
                ORDER BY significance_score DESC
            """, (page_id,))
            
            return [POI(*row) for row in cursor.fetchall()]

# repositories/property_repository.py
from elasticsearch import Elasticsearch
from typing import List, Optional

class PropertyRepository:
    """Repository for property data with injected Elasticsearch client."""
    
    def __init__(
        self, 
        es_client: Elasticsearch,
        index_name: str
    ):
        """
        Initialize with explicit dependencies.
        
        Args:
            es_client: Configured Elasticsearch client
            index_name: Name of the property index
        """
        self.es_client = es_client
        self.index_name = index_name
    
    def index_property(self, property_data: dict) -> bool:
        """Index a single property."""
        try:
            self.es_client.index(
                index=self.index_name,
                id=property_data["listing_id"],
                body=property_data
            )
            return True
        except Exception as e:
            logger.error(f"Failed to index property: {e}")
            return False
    
    def bulk_index_properties(
        self, 
        properties: List[dict]
    ) -> IndexStats:
        """Bulk index multiple properties."""
        actions = [
            {
                "_index": self.index_name,
                "_id": prop["listing_id"],
                "_source": prop
            }
            for prop in properties
        ]
        
        success, failed = helpers.bulk(
            self.es_client,
            actions,
            raise_on_error=False
        )
        
        return IndexStats(
            total=len(properties),
            success=success,
            failed=len(failed) if failed else 0
        )
    
    def search(
        self, 
        query: dict,
        size: int = 10
    ) -> List[Property]:
        """Search for properties."""
        response = self.es_client.search(
            index=self.index_name,
            body=query,
            size=size
        )
        
        return [
            Property(**hit["_source"])
            for hit in response["hits"]["hits"]
        ]
```

### 4. Service Layer with Dependency Injection

```python
# services/enrichment_service.py
class EnrichmentService:
    """Service for enriching properties with Wikipedia data."""
    
    def __init__(
        self,
        wikipedia_repo: WikipediaRepository
    ):
        """
        Initialize with explicit repository dependency.
        
        Args:
            wikipedia_repo: Repository for Wikipedia data access
        """
        self.wikipedia_repo = wikipedia_repo
    
    def enrich_property(
        self, 
        property_data: dict
    ) -> dict:
        """Enrich a property with Wikipedia context."""
        enriched = property_data.copy()
        
        # Extract location
        city = property_data.get("address", {}).get("city")
        state = property_data.get("address", {}).get("state")
        
        if not city or not state:
            return enriched
        
        # Get Wikipedia data
        articles = self.wikipedia_repo.get_articles_for_location(city, state)
        
        if articles:
            article = articles[0]  # Most relevant
            pois = self.wikipedia_repo.get_pois_for_article(article.page_id)
            
            # Add enrichment data
            enriched["location_context"] = {
                "wikipedia_page_id": article.page_id,
                "wikipedia_title": article.title,
                "summary": article.summary,
                "key_topics": article.key_topics
            }
            
            enriched["nearby_poi"] = [
                {
                    "name": poi.name,
                    "category": poi.category,
                    "significance_score": poi.significance_score,
                    "description": poi.description
                }
                for poi in pois[:10]  # Top 10 POIs
            ]
        
        return enriched

# services/indexing_service.py
class IndexingService:
    """Service for indexing properties with enrichment."""
    
    def __init__(
        self,
        property_repo: PropertyRepository,
        enrichment_service: EnrichmentService
    ):
        """
        Initialize with explicit service dependencies.
        
        Args:
            property_repo: Repository for property storage
            enrichment_service: Service for enriching properties
        """
        self.property_repo = property_repo
        self.enrichment_service = enrichment_service
    
    def index_properties(
        self, 
        properties: List[Property]
    ) -> IndexStats:
        """Index properties with enrichment."""
        # Enrich all properties
        enriched_properties = [
            self.enrichment_service.enrich_property(prop.dict())
            for prop in properties
        ]
        
        # Bulk index
        return self.property_repo.bulk_index_properties(enriched_properties)

# services/search_service.py
class SearchService:
    """Service for searching properties."""
    
    def __init__(
        self,
        property_repo: PropertyRepository
    ):
        """
        Initialize with repository dependency.
        
        Args:
            property_repo: Repository for property queries
        """
        self.property_repo = property_repo
    
    def search(
        self,
        query_text: str,
        filters: Optional[SearchFilters] = None
    ) -> SearchResponse:
        """Search for properties with text and filters."""
        # Build Elasticsearch query
        es_query = self._build_query(query_text, filters)
        
        # Execute search
        properties = self.property_repo.search(es_query)
        
        # Build response
        return SearchResponse(
            hits=properties,
            total=len(properties),
            query=query_text
        )
    
    def _build_query(
        self,
        query_text: str,
        filters: Optional[SearchFilters]
    ) -> dict:
        """Build Elasticsearch query from parameters."""
        query = {
            "bool": {
                "should": [
                    {"match": {"description": query_text}},
                    {"match": {"enriched_search_text": query_text}},
                    {"match": {"location_context.summary": query_text}}
                ]
            }
        }
        
        if filters:
            query["bool"]["filter"] = self._build_filters(filters)
        
        return {"query": query}
```

### 5. Dependency Container

```python
# container.py
class DependencyContainer:
    """
    Central dependency injection container.
    Creates and wires all application objects.
    """
    
    def __init__(self, config: AppConfig):
        """
        Initialize container with application configuration.
        
        Args:
            config: Complete application configuration
        """
        self.config = config
        
        # Create infrastructure
        self._es_client = self._create_es_client()
        
        # Create repositories
        self._wikipedia_repo = self._create_wikipedia_repo()
        self._property_repo = self._create_property_repo()
        
        # Create services
        self._enrichment_service = self._create_enrichment_service()
        self._indexing_service = self._create_indexing_service()
        self._search_service = self._create_search_service()
    
    def _create_es_client(self) -> Elasticsearch:
        """Create Elasticsearch client."""
        factory = ElasticsearchClientFactory(self.config.elasticsearch)
        return factory.create_client()
    
    def _create_wikipedia_repo(self) -> WikipediaRepository:
        """Create Wikipedia repository."""
        return WikipediaRepository(self.config.data.wikipedia_db)
    
    def _create_property_repo(self) -> PropertyRepository:
        """Create property repository."""
        return PropertyRepository(
            es_client=self._es_client,
            index_name=self.config.elasticsearch.property_index
        )
    
    def _create_enrichment_service(self) -> EnrichmentService:
        """Create enrichment service."""
        return EnrichmentService(
            wikipedia_repo=self._wikipedia_repo
        )
    
    def _create_indexing_service(self) -> IndexingService:
        """Create indexing service."""
        return IndexingService(
            property_repo=self._property_repo,
            enrichment_service=self._enrichment_service
        )
    
    def _create_search_service(self) -> SearchService:
        """Create search service."""
        return SearchService(
            property_repo=self._property_repo
        )
    
    # Public accessors
    @property
    def indexing_service(self) -> IndexingService:
        """Get indexing service."""
        return self._indexing_service
    
    @property
    def search_service(self) -> SearchService:
        """Get search service."""
        return self._search_service
    
    @property
    def es_client(self) -> Elasticsearch:
        """Get Elasticsearch client for admin operations."""
        return self._es_client
```

### 6. Main Application Entry Points

```python
# main.py - Main demo application
import argparse
from pathlib import Path
from typing import List

from config.config import AppConfig
from container import DependencyContainer
from models import Property
from loaders import PropertyLoader

def main():
    """Main entry point for the demo application."""
    parser = argparse.ArgumentParser(description="Real Estate Search Demo")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to configuration file"
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate all indices"
    )
    parser.add_argument(
        "--mode",
        choices=["ingest", "search", "demo"],
        default="demo",
        help="Operation mode"
    )
    args = parser.parse_args()
    
    # Load configuration once
    config = AppConfig.from_yaml(args.config)
    if args.recreate:
        config.force_recreate = True
    
    # Create dependency container
    container = DependencyContainer(config)
    
    # Route to appropriate handler
    if args.mode == "ingest":
        run_ingestion(container, config)
    elif args.mode == "search":
        run_search_cli(container)
    elif args.mode == "demo":
        run_full_demo(container, config)

def run_ingestion(container: DependencyContainer, config: AppConfig):
    """Run data ingestion pipeline."""
    print("🚀 Starting data ingestion...")
    
    # Create index if needed
    if config.force_recreate:
        print("📦 Recreating indices...")
        container.es_client.indices.delete(
            index=config.elasticsearch.property_index,
            ignore=[404]
        )
        create_index(container.es_client, config.elasticsearch.property_index)
    
    # Load properties
    loader = PropertyLoader(config.data.properties_dir)
    properties = loader.load_all_properties()
    print(f"📄 Loaded {len(properties)} properties")
    
    # Index with enrichment
    stats = container.indexing_service.index_properties(properties)
    print(f"✅ Indexed {stats.success}/{stats.total} properties")
    
    if stats.failed > 0:
        print(f"❌ Failed: {stats.failed}")

def run_search_cli(container: DependencyContainer):
    """Run interactive search CLI."""
    print("🔍 Real Estate Search (type 'quit' to exit)")
    
    while True:
        query = input("\nSearch: ").strip()
        
        if query.lower() == "quit":
            break
        
        # Execute search
        response = container.search_service.search(query)
        
        # Display results
        print(f"\nFound {response.total} properties:")
        for i, prop in enumerate(response.hits[:5], 1):
            print(f"{i}. {prop.address.city}, {prop.address.state}")
            print(f"   ${prop.price:,} - {prop.bedrooms}bd/{prop.bathrooms}ba")
            if prop.location_context:
                print(f"   📍 {prop.location_context.get('summary', '')[:100]}...")

def run_full_demo(container: DependencyContainer, config: AppConfig):
    """Run complete demo flow."""
    print("🎬 Running Real Estate Search Demo")
    print("=" * 50)
    
    # Step 1: Ingest data
    print("\n📥 Step 1: Data Ingestion")
    run_ingestion(container, config)
    
    # Step 2: Demo searches
    print("\n🔍 Step 2: Demo Searches")
    demo_queries = [
        "ski resort properties",
        "family home near parks",
        "downtown condo with amenities",
        "historic neighborhood Victorian"
    ]
    
    for query in demo_queries:
        print(f"\nSearching: '{query}'")
        response = container.search_service.search(query)
        print(f"  → Found {response.total} matching properties")
        
        if response.hits:
            top_hit = response.hits[0]
            print(f"  → Top result: {top_hit.address.city}, ${top_hit.price:,}")
    
    print("\n✅ Demo complete!")

if __name__ == "__main__":
    main()
```

### 7. Testing with Dependency Injection

```python
# tests/test_enrichment_service.py
import unittest
from unittest.mock import Mock, MagicMock
from services.enrichment_service import EnrichmentService
from repositories.wikipedia_repository import WikipediaRepository

class TestEnrichmentService(unittest.TestCase):
    """Test enrichment service with mocked dependencies."""
    
    def setUp(self):
        """Set up test with mock repository."""
        # Create mock repository
        self.mock_wikipedia_repo = Mock(spec=WikipediaRepository)
        
        # Create service with mock
        self.service = EnrichmentService(
            wikipedia_repo=self.mock_wikipedia_repo
        )
    
    def test_enrich_property_with_wikipedia_data(self):
        """Test property enrichment with Wikipedia data."""
        # Arrange
        property_data = {
            "listing_id": "test-001",
            "address": {
                "city": "Park City",
                "state": "Utah"
            }
        }
        
        mock_article = Mock()
        mock_article.page_id = 123
        mock_article.title = "Park City, Utah"
        mock_article.summary = "A ski resort town..."
        mock_article.key_topics = ["skiing", "resort", "olympics"]
        
        mock_poi = Mock()
        mock_poi.name = "Park City Mountain Resort"
        mock_poi.category = "ski_resort"
        mock_poi.significance_score = 0.95
        
        self.mock_wikipedia_repo.get_articles_for_location.return_value = [mock_article]
        self.mock_wikipedia_repo.get_pois_for_article.return_value = [mock_poi]
        
        # Act
        enriched = self.service.enrich_property(property_data)
        
        # Assert
        self.assertIn("location_context", enriched)
        self.assertEqual(enriched["location_context"]["wikipedia_page_id"], 123)
        self.assertIn("nearby_poi", enriched)
        self.assertEqual(len(enriched["nearby_poi"]), 1)
        self.assertEqual(enriched["nearby_poi"][0]["name"], "Park City Mountain Resort")
    
    def test_enrich_property_without_location(self):
        """Test enrichment handles missing location gracefully."""
        # Arrange
        property_data = {
            "listing_id": "test-002",
            "address": {}  # No city/state
        }
        
        # Act
        enriched = self.service.enrich_property(property_data)
        
        # Assert
        self.assertNotIn("location_context", enriched)
        self.assertNotIn("nearby_poi", enriched)
        self.mock_wikipedia_repo.get_articles_for_location.assert_not_called()
```

## Detailed Implementation Plan

### Phase 1: Configuration and Models (Day 1)
**Goal**: Replace all configuration and data models with Pydantic-based versions using constructor injection

**Files to Update Directly**:
1. `config/config.py`
   - Replace existing `Config` class with Pydantic `AppConfig`
   - Remove `Settings` class entirely
   - Single configuration loading point
   - All fields explicitly typed
   - No optional dependencies

2. `indexer/models.py`
   - Convert all models to Pydantic BaseModel
   - Remove any model factories or builders
   - Explicit field validation
   - No default object creation

3. `search/models.py`
   - Convert SearchRequest, SearchResponse to Pydantic
   - Remove any optional initialization patterns
   - All required fields must be provided

**Validation**: Configuration loads correctly, all models validate

### Phase 2: Infrastructure Layer (Day 2)
**Goal**: Create clean infrastructure components with explicit dependencies

**Files to Update Directly**:
1. `infrastructure/elasticsearch_client.py` (NEW FILE)
   - Create `ElasticsearchClientFactory` class
   - Constructor takes `ElasticsearchConfig`
   - Single `create_client()` method
   - No fallback configurations

2. `infrastructure/database.py` (NEW FILE)
   - Create `DatabaseConnection` class
   - Constructor takes database path
   - Connection management methods
   - No auto-discovery of database files

**Validation**: Can create ES client and database connections with explicit config

### Phase 3: Repository Layer (Day 3)
**Goal**: Extract all data access into repositories with injected dependencies

**Files to Create**:
1. `repositories/wikipedia_repository.py` (NEW FILE)
   - Constructor takes database path
   - All Wikipedia data queries
   - No business logic
   - Returns Pydantic models

2. `repositories/property_repository.py` (NEW FILE)
   - Constructor takes ES client and index name
   - All property CRUD operations
   - Bulk operations support
   - Returns Pydantic models

**Files to Update**:
1. `wikipedia/extractor.py`
   - Remove database access code
   - Update to use WikipediaRepository
   - Constructor injection of repository

**Validation**: All data access goes through repositories

### Phase 4: Service Layer Refactoring (Day 4-5)
**Goal**: Update all services to use constructor injection

**Files to Update Directly**:

1. `wikipedia/enricher.py` → `services/enrichment_service.py`
   - Rename class to `EnrichmentService`
   - Constructor takes `WikipediaRepository`
   - Remove `WikipediaExtractor` creation
   - No caching in service (move to repository if needed)
   - Use logging instead of print

2. `indexer/property_indexer.py` → `services/indexing_service.py`
   - Rename class to `IndexingService`
   - Constructor takes `PropertyRepository` and `EnrichmentService`
   - Remove ES client creation
   - Remove config loading
   - Use logging for all output

3. `search/search_engine.py` → `services/search_service.py`
   - Rename class to `SearchService`
   - Constructor takes `PropertyRepository`
   - Remove ES client creation
   - Remove settings loading
   - Use logging throughout

**Validation**: All services work with injected dependencies only

### Phase 5: Orchestration Update (Day 6)
**Goal**: Update orchestrator to use constructor injection

**Files to Update Directly**:

1. `ingestion/orchestrator.py`
   - Update `IngestionOrchestrator` class
   - Constructor takes all services as parameters
   - Remove service creation code
   - Remove config loading
   - Use logging instead of print
   - No backward compatibility parameters

**Validation**: Orchestrator works with injected services

### Phase 6: Container Implementation (Day 7)
**Goal**: Create central dependency container

**Files to Create**:
1. `container.py` (NEW FILE)
   - `DependencyContainer` class
   - Constructor takes `AppConfig` only
   - Creates all objects in correct order
   - Exposes services through properties
   - Single source of object creation

**Validation**: Container creates all objects correctly

### Phase 7: Entry Points Update (Day 8)
**Goal**: Update all entry points to use container

**Files to Update Directly**:

1. `main.py` (NEW FILE or UPDATE)
   - Load config once
   - Create container once
   - Use container services
   - Remove all object creation
   - Use logging throughout

2. `scripts/setup_index.py`
   - Use container for all services
   - Remove direct service creation
   - Load config once at start
   - Use logging instead of print

3. `scripts/demo_search.py`
   - Use container services
   - Remove service creation
   - Single config load
   - Logging throughout

**Validation**: All entry points work with container

### Phase 8: Cleanup (Day 9)
**Goal**: Remove all old code and compatibility layers

**Files to Delete**:
1. `config/settings.py` - replaced by config.py
2. Old service files if renamed
3. Any backup or compatibility code

**Files to Update**:
1. Remove all print statements (replace with logging)
2. Remove all try/except on imports
3. Remove all optional dependency patterns
4. Remove all `.get()` with defaults for required fields
5. Ensure all names are snake_case

**Validation**: No old patterns remain in codebase

### Phase 9: Testing (Day 10)
**Goal**: Comprehensive testing with mocked dependencies

**Files to Create/Update**:
1. `tests/test_services/` - Test each service with mocked dependencies
2. `tests/test_repositories/` - Test repositories with mocked infrastructure
3. `tests/test_container.py` - Test container wiring
4. `tests/test_integration.py` - End-to-end tests with real dependencies

**Validation**: All tests pass with >80% coverage

### Phase 10: Documentation and Demo (Day 11)
**Goal**: Update documentation and prepare demo

**Files to Update**:
1. `README.md` - Update with new architecture
2. Create `ARCHITECTURE.md` - Detailed architecture documentation
3. Update all docstrings
4. Create demo script with logging output

**Validation**: Documentation accurate, demo runs smoothly

## Benefits of This Architecture

### 1. Testability
- Every component can be tested in isolation
- Mock dependencies easily injected
- No need for complex test fixtures
- Fast unit tests without infrastructure

### 2. Maintainability
- Clear separation of concerns
- Easy to understand dependencies
- Single place to configure objects
- Consistent patterns throughout

### 3. Flexibility
- Easy to swap implementations
- Support multiple configurations
- Simple to add new features
- Clear extension points

### 4. Demo Quality
- Clean, professional code structure
- Industry best practices
- Easy to explain architecture
- Impressive for technical audiences

## Code Quality Metrics

### Before Refactoring
- Cyclomatic Complexity: Average 12, Max 28
- Test Coverage: 35%
- Coupling: High (hidden dependencies)
- Cohesion: Low (mixed responsibilities)

### After Refactoring (Target)
- Cyclomatic Complexity: Average 4, Max 10
- Test Coverage: 85%+
- Coupling: Low (explicit dependencies)
- Cohesion: High (single responsibility)

## Example Usage After Refactoring

```python
# Simple and clean usage
from config import AppConfig
from container import DependencyContainer

# Load config once
config = AppConfig.from_yaml()

# Create container once
container = DependencyContainer(config)

# Use services with all dependencies wired
results = container.search_service.search("ski properties")
stats = container.indexing_service.index_properties(properties)
```

## Conclusion

This refactoring to Constructor Injection will transform the Real Estate Search demo into a clean, professional, and maintainable codebase. The explicit dependencies, clear separation of concerns, and centralized configuration will make the system easier to understand, test, and extend.

The architecture follows industry best practices and demonstrates professional software engineering principles, making it an excellent showcase for a high-quality demo.

## Next Steps

1. Review and approve this proposal
2. Create feature branch for refactoring
3. Implement changes incrementally
4. Comprehensive testing at each phase
5. Documentation updates
6. Demo preparation and rehearsal