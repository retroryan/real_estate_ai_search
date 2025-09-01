"""Elasticsearch writer with type-safe data transformation.

Following best practices:
- No isinstance or hasattr checks
- No runtime type checking
- Pure Pydantic validation
- Direct field access only
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date
import logging
import os
import json
from pydantic import BaseModel, Field, ConfigDict, field_serializer, field_validator
from squack_pipeline_v2.core.connection import DuckDBConnectionManager, DuckDBConnectionManager as ConnectionManager
from squack_pipeline_v2.core.logging import log_stage
from squack_pipeline_v2.core.settings import PipelineSettings

logger = logging.getLogger(__name__)


# ============================================================================
# ELASTICSEARCH DOCUMENT MODELS
# ============================================================================

class GeoPoint(BaseModel):
    """Elasticsearch geo_point structure."""
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class ParkingInfo(BaseModel):
    """Parking information structure."""
    spaces: int = Field(ge=0, default=0)
    type: str = Field(default="none")


class AddressInfo(BaseModel):
    """Address information structure matching ES template."""
    street: str = ""
    city: str
    state: str  # Changed from state_code
    zip_code: str = ""
    location: GeoPoint


class PropertyDocument(BaseModel):
    """Property document for Elasticsearch."""
    
    model_config = ConfigDict(frozen=True)
    
    listing_id: str
    neighborhood_id: str = ""
    price: float
    bedrooms: int
    bathrooms: float
    square_feet: int
    property_type: str
    year_built: int = 0
    lot_size: int = 0
    address: AddressInfo
    price_per_sqft: float = 0.0
    parking: ParkingInfo
    description: str = ""
    features: List[str] = Field(default_factory=list)
    amenities: List[str] = Field(default_factory=list)  # Required by ES queries
    status: str = "active"  # Required by ES queries
    search_tags: List[str] = Field(default_factory=list)  # Required by ES queries
    listing_date: str = ""
    days_on_market: int = 0
    virtual_tour_url: str = ""
    images: List[str] = Field(default_factory=list)
    embedding: List[float] = Field(default_factory=list)
    embedding_model: str = ""
    embedding_dimension: int = 0
    embedded_at: datetime = Field(default_factory=datetime.now)
    indexed_at: datetime = Field(default_factory=datetime.now)


class NeighborhoodDocument(BaseModel):
    """Neighborhood document for Elasticsearch."""
    
    model_config = ConfigDict(frozen=True)
    
    neighborhood_id: str
    name: str
    city: str
    state: str  # Changed from state_code
    population: int
    walkability_score: float = 0.0
    school_rating: float = 0.0
    overall_livability_score: float = 0.0
    location: GeoPoint  # Using standard geo_point
    description: str = ""
    amenities: List[str] = Field(default_factory=list)
    lifestyle_tags: List[str] = Field(default_factory=list)
    demographics: Dict[str, Any] = Field(default_factory=dict)
    embedding: List[float] = Field(default_factory=list)
    embedding_model: str = ""
    embedding_dimension: int = 0
    embedded_at: datetime = Field(default_factory=datetime.now)
    indexed_at: datetime = Field(default_factory=datetime.now)


class WikipediaDocument(BaseModel):
    """Wikipedia document for Elasticsearch."""
    
    model_config = ConfigDict(frozen=True)
    
    page_id: str
    title: str
    url: str = ""
    article_filename: str = ""
    long_summary: str = ""
    short_summary: str = ""
    full_content: str = ""
    content_length: int = 0
    content_loaded: bool = False
    content_loaded_at: datetime = Field(default_factory=datetime.now)
    location: List[float] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    key_topics: List[str] = Field(default_factory=list)
    relevance_score: float = 0.0
    article_quality_score: float = 0.0
    article_quality: str = ""
    city: str = ""
    state: str = ""
    last_updated: datetime = Field(default_factory=datetime.now)
    embedding: List[float] = Field(default_factory=list)
    embedding_model: str = ""
    embedding_dimension: int = 0
    embedded_at: datetime = Field(default_factory=datetime.now)
    indexed_at: datetime = Field(default_factory=datetime.now)


# ============================================================================
# DUCKDB RECORD MODELS (Input from database)
# ============================================================================

class PropertyInput(BaseModel):
    """Property input from DuckDB - matches exact types returned."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Core fields from gold_properties (types after Gold layer processing)
    listing_id: str
    neighborhood_id: Optional[str] = None
    price: float  # Gold layer casts to float
    bedrooms: int
    bathrooms: float
    square_feet: int
    property_type: str
    year_built: int = 0
    lot_size: int = 0
    
    # Complex fields
    address: Dict[str, Any] = Field(default_factory=dict)
    price_per_sqft: float = 0.0  # Gold layer casts to float
    parking: Dict[str, Any] = Field(default_factory=dict)
    
    # Text fields
    description: str = ""
    features: List[str] = Field(default_factory=list)
    amenities: List[str] = Field(default_factory=list)  # From Gold layer
    status: str = "active"  # From Gold layer
    search_tags: List[str] = Field(default_factory=list)  # From Gold layer
    
    # Date fields - DuckDB returns date objects
    listing_date: Optional[date] = None
    days_on_market: int = 0
    
    # URLs and media
    virtual_tour_url: str = ""
    images: List[str] = Field(default_factory=list)
    
    # Embedding fields from Gold layer (medallion architecture)
    embedding_vector: Tuple[float, ...] = tuple()  # DuckDB returns tuple, not list!
    embedding_generated_at: Optional[datetime] = None


class NeighborhoodInput(BaseModel):
    """Neighborhood input from DuckDB - matches exact types returned."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    neighborhood_id: str
    name: str
    city: str
    state: str
    population: Optional[int] = 0
    walkability_score: float = 0.0
    school_rating: float = 0.0
    overall_livability_score: float = 0.0
    center_latitude: float = 0.0
    center_longitude: float = 0.0
    description: str = ""
    amenities: List[str] = Field(default_factory=list)
    lifestyle_tags: List[str] = Field(default_factory=list)
    demographics: Dict[str, Any] = Field(default_factory=dict)
    
    # Embedding fields from Gold layer (medallion architecture)
    embedding_vector: Tuple[float, ...] = tuple()  # DuckDB returns tuple!
    embedding_generated_at: Optional[datetime] = None


class WikipediaInput(BaseModel):
    """Wikipedia input from DuckDB - matches exact types returned."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Core fields from gold_wikipedia
    page_id: int
    title: str
    url: str = ""
    article_filename: Optional[str] = ""
    long_summary: str = ""
    short_summary: str = ""
    full_content: str = ""
    content_length: int = 0
    content_loaded: bool = False
    content_loaded_at: Optional[datetime] = None  # Can be None
    
    # Categories is JSON string from DB (can be NULL)
    categories: Optional[str] = None
    
    # key_topics is always a list (empty if no topics)
    key_topics: List[str] = Field(default_factory=list)
    relevance_score: float = 0.0
    article_quality_score: float = 0.0
    article_quality: str = ""
    city: Optional[str] = None  # Can be None
    state: Optional[str] = None  # Can be None
    last_updated: Optional[datetime] = None
    
    # Embedding fields from Gold layer (medallion architecture)
    embedding_vector: Tuple[float, ...] = tuple()  # DuckDB returns tuple!
    embedding_generated_at: Optional[datetime] = None
    
    def parse_categories(self) -> List[str]:
        """Parse categories from JSON string."""
        if not self.categories:
            return []
        try:
            parsed = json.loads(self.categories)
            return list(parsed) if parsed else []
        except (json.JSONDecodeError, TypeError, ValueError):
            # Fallback to comma-separated
            return [c.strip() for c in self.categories.split(',') if c.strip()]


# ============================================================================
# TRANSFORMERS
# ============================================================================

class PropertyTransformer:
    """Transform property records to documents."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize with settings."""
        self.settings = settings
        self.embedding_model = settings.get_model_name()
        if not self.embedding_model or self.embedding_model == "unknown":
            raise ValueError(f"Invalid embedding configuration: provider={settings.embedding.provider}")
    
    def transform(self, record: Dict[str, Any]) -> PropertyDocument:
        """Transform a property record to document."""
        # Parse input with proper type handling
        input_data = PropertyInput(**record)
        
        # Extract address data and create geo point from location array
        address_data = input_data.address or {}
        location_array = address_data.get('location', [0, 0])
        
        # Create geo point from location array [lon, lat]
        location = GeoPoint(
            lat=float(location_array[1]) if len(location_array) > 1 else 0.0,
            lon=float(location_array[0]) if len(location_array) > 0 else 0.0
        )
        
        # Create address info with corrected field names
        address = AddressInfo(
            street=address_data.get('street', ''),
            city=address_data.get('city', ''),
            state=address_data.get('state', ''),  # Using 'state' not 'state_code'
            zip_code=address_data.get('zip_code', ''),
            location=location
        )
        
        # Create parking info from parking object
        parking_data = input_data.parking or {}
        parking = ParkingInfo(
            spaces=parking_data.get('spaces', 0),
            type=parking_data.get('type', 'none')
        )
        
        # Convert date to ISO string for ES
        listing_date_str = ""
        if input_data.listing_date:
            listing_date_str = input_data.listing_date.isoformat()
        
        # Convert tuple embedding to list for ES
        embedding_list = list(input_data.embedding_vector) if input_data.embedding_vector else []
        
        # Create document - types already correct from Gold layer
        return PropertyDocument(
            listing_id=input_data.listing_id,
            neighborhood_id=input_data.neighborhood_id or "",
            price=input_data.price,  # Already float from Gold layer
            bedrooms=input_data.bedrooms,
            bathrooms=input_data.bathrooms,
            square_feet=input_data.square_feet,
            property_type=input_data.property_type,
            year_built=input_data.year_built,
            lot_size=input_data.lot_size,
            address=address,
            price_per_sqft=input_data.price_per_sqft,  # Already float from Gold layer
            parking=parking,
            description=input_data.description,
            features=input_data.features,  # Already list from Gold layer
            amenities=input_data.amenities,  # From Gold layer
            status=input_data.status,  # From Gold layer
            search_tags=input_data.search_tags,  # From Gold layer
            listing_date=listing_date_str,  # date -> string for ES
            days_on_market=input_data.days_on_market,
            virtual_tour_url=input_data.virtual_tour_url,
            images=input_data.images,
            embedding=embedding_list,  # tuple -> list for ES
            embedding_model=self.embedding_model,
            embedding_dimension=len(embedding_list) if embedding_list else 0,
            embedded_at=input_data.embedding_generated_at or datetime.now()
        )


class NeighborhoodTransformer:
    """Transform neighborhood records to documents."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize with settings."""
        self.settings = settings
        self.embedding_model = settings.get_model_name()
        if not self.embedding_model or self.embedding_model == "unknown":
            raise ValueError(f"Invalid embedding configuration: provider={settings.embedding.provider}")
    
    def transform(self, record: Dict[str, Any]) -> NeighborhoodDocument:
        """Transform a neighborhood record to document."""
        # Parse input with proper type handling
        input_data = NeighborhoodInput(**record)
        
        # Create geo point from center coordinates
        location = GeoPoint(
            lat=input_data.center_latitude,
            lon=input_data.center_longitude
        )
        
        # Convert tuple embedding to list for ES
        embedding_list = list(input_data.embedding_vector) if input_data.embedding_vector else []
        
        # Create document - types already correct from Gold layer
        return NeighborhoodDocument(
            neighborhood_id=input_data.neighborhood_id,
            name=input_data.name,
            city=input_data.city,
            state=input_data.state,
            population=input_data.population or 0,
            walkability_score=input_data.walkability_score,
            school_rating=input_data.school_rating,
            overall_livability_score=input_data.overall_livability_score,
            location=location,
            description=input_data.description,
            amenities=input_data.amenities,  # Already list from Gold layer
            lifestyle_tags=input_data.lifestyle_tags,  # Already list from Gold layer
            demographics=input_data.demographics,
            embedding=embedding_list,  # tuple -> list for ES
            embedding_model=self.embedding_model,
            embedding_dimension=len(embedding_list) if embedding_list else 0,
            embedded_at=input_data.embedding_generated_at or datetime.now()
        )


class WikipediaTransformer:
    """Transform Wikipedia records to documents."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize with settings."""
        self.settings = settings
        self.embedding_model = settings.get_model_name()
        if not self.embedding_model or self.embedding_model == "unknown":
            raise ValueError(f"Invalid embedding configuration: provider={settings.embedding.provider}")
    
    def transform(self, record: Dict[str, Any]) -> WikipediaDocument:
        """Transform a Wikipedia record to document."""
        # Parse input with proper type handling
        input_data = WikipediaInput(**record)
        
        # Convert tuple embedding to list for ES
        embedding_list = list(input_data.embedding_vector) if input_data.embedding_vector else []
        
        # Create document with explicit conversions
        return WikipediaDocument(
            page_id=str(input_data.page_id),  # int -> string for ES
            title=input_data.title,
            url=input_data.url,
            article_filename=input_data.article_filename or "",
            long_summary=input_data.long_summary,
            short_summary=input_data.short_summary,
            full_content=input_data.full_content,
            content_length=input_data.content_length,
            content_loaded=input_data.content_loaded,
            content_loaded_at=input_data.content_loaded_at or datetime.now(),
            categories=input_data.parse_categories(),
            key_topics=input_data.key_topics,  # Always a list now
            relevance_score=input_data.relevance_score,  # already float
            article_quality_score=input_data.article_quality_score,  # already float
            article_quality=input_data.article_quality,
            city=input_data.city if input_data.city else "",  # Keep value if exists
            state=input_data.state if input_data.state else "",  # Keep value if exists
            last_updated=input_data.last_updated or datetime.now(),
            embedding=embedding_list,  # tuple -> list for ES
            embedding_model=self.embedding_model,
            embedding_dimension=len(embedding_list) if embedding_list else 0,
            embedded_at=input_data.embedding_generated_at or datetime.now()
        )


# ============================================================================
# ELASTICSEARCH WRITER
# ============================================================================

class ElasticsearchWriter:
    """Elasticsearch writer with type-safe transformation."""
    
    def __init__(
        self,
        connection_manager: ConnectionManager,
        settings: PipelineSettings
    ):
        """Initialize Elasticsearch writer.
        
        Args:
            connection_manager: DuckDB connection manager
            settings: Complete pipeline settings
        """
        self.connection_manager = connection_manager
        self.settings = settings
        self.config = settings.output.elasticsearch
        self.documents_indexed = 0
        self.es_client = self._create_client()
        
        # Get embedding model name from settings
        self.embedding_model = settings.get_model_name()
        if not self.embedding_model or self.embedding_model == "unknown":
            raise ValueError(f"Invalid embedding configuration: provider={settings.embedding.provider}, model={self.embedding_model}")
        
        # Initialize transformers with settings
        self.property_transformer = PropertyTransformer(settings)
        self.neighborhood_transformer = NeighborhoodTransformer(settings)
        self.wikipedia_transformer = WikipediaTransformer(settings)
        
        # Verify connection
        if not self.es_client.ping():
            raise ConnectionError("Failed to connect to Elasticsearch")
    
    def _create_client(self):
        """Create Elasticsearch client."""
        from elasticsearch import Elasticsearch
        
        es_user = os.getenv("ES_USERNAME")
        es_password = os.getenv("ES_PASSWORD")
        es_url = f"http://{self.config.host}:{self.config.port}"
        
        if es_user and es_password:
            es = Elasticsearch(
                [es_url],
                http_auth=(es_user, es_password),
                request_timeout=self.config.timeout
            )
        else:
            es = Elasticsearch(
                [es_url],
                request_timeout=self.config.timeout
            )
        
        if not es.ping():
            raise ConnectionError("Failed to connect to Elasticsearch")
        
        return es
    
    @log_stage("Elasticsearch: Index properties")
    def index_properties(
        self,
        table_name: str = "gold_properties",
        index_name: str = "properties",
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """Index properties to Elasticsearch."""
        # Embeddings are now stored directly in Gold tables (medallion architecture)
        conn = self.connection_manager.get_connection()
        query = f"SELECT * FROM {DuckDBConnectionManager.safe_identifier(table_name)}"
        
        return self._index_documents(
            query=query,
            index_name=index_name,
            transformer=self.property_transformer.transform,
            id_field="listing_id",
            batch_size=batch_size
        )
    
    @log_stage("Elasticsearch: Index neighborhoods")
    def index_neighborhoods(
        self,
        table_name: str = "gold_neighborhoods",
        index_name: str = "neighborhoods",
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """Index neighborhoods to Elasticsearch."""
        # Embeddings are now stored directly in Gold tables (medallion architecture)
        conn = self.connection_manager.get_connection()
        query = f"SELECT * FROM {DuckDBConnectionManager.safe_identifier(table_name)}"
        
        return self._index_documents(
            query=query,
            index_name=index_name,
            transformer=self.neighborhood_transformer.transform,
            id_field="neighborhood_id",
            batch_size=batch_size
        )
    
    @log_stage("Elasticsearch: Index Wikipedia")
    def index_wikipedia(
        self,
        table_name: str = "gold_wikipedia",
        index_name: str = "wikipedia",
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """Index Wikipedia articles to Elasticsearch."""
        # Embeddings are now stored directly in Gold tables (medallion architecture)
        conn = self.connection_manager.get_connection()
        query = f"SELECT * FROM {DuckDBConnectionManager.safe_identifier(table_name)}"
        
        return self._index_documents(
            query=query,
            index_name=index_name,
            transformer=self.wikipedia_transformer.transform,
            id_field="page_id",
            batch_size=batch_size
        )
    
    def _index_documents(
        self,
        query: str,
        index_name: str,
        transformer: callable,
        id_field: str,
        batch_size: int
    ) -> Dict[str, Any]:
        """Index documents with type-safe transformation."""
        from elasticsearch.helpers import bulk
        
        # Get total count safely
        count_query = f"SELECT COUNT(*) FROM ({query}) t"
        total_records = self.connection_manager.execute(count_query).fetchone()[0]
        
        logger.info(f"Indexing {total_records} documents to {index_name}")
        
        indexed = 0
        errors = 0
        validation_errors = 0
        
        offset = 0
        start_time = datetime.now()
        
        while offset < total_records:
            # Fetch batch from DuckDB using parameterized query
            batch_query = f"{query} LIMIT {batch_size} OFFSET {offset}"
            results = self.connection_manager.execute(batch_query)
            
            # Get column names and rows
            columns = [desc[0] for desc in results.description]
            rows = results.fetchall()
            
            if not rows:
                break
            
            # Convert to dictionaries
            batch_data = [dict(zip(columns, row)) for row in rows]
            
            # Transform and prepare for bulk indexing
            actions = []
            
            for record in batch_data:
                try:
                    # Transform using specific transformer
                    document = transformer(record)
                    
                    # Serialize to dict
                    doc = document.model_dump(exclude_none=True)
                    
                    # Create bulk action
                    action = {
                        "_index": index_name,
                        "_id": doc[id_field],
                        "_source": doc
                    }
                    actions.append(action)
                    
                except Exception as e:
                    logger.error(f"Validation error for {id_field}={record.get(id_field, 'unknown')}: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    validation_errors += 1
            
            # Bulk index
            if actions:
                try:
                    result = bulk(
                        self.es_client,
                        actions,
                        raise_on_error=False,
                        raise_on_exception=False,
                        stats_only=False
                    )
                    success_count = result[0]
                    failures = result[1]
                    
                    indexed += success_count
                    if failures:
                        errors += len(failures)
                        for failure in failures[:3]:
                            logger.error(f"Indexing failure: {failure}")
                        
                except Exception as e:
                    logger.error(f"Bulk indexing error: {e}")
                    errors += len(actions)
            
            offset += batch_size
            
            if indexed > 0 and indexed % 100 == 0:
                logger.info(f"Indexed {indexed}/{total_records} documents")
        
        duration = (datetime.now() - start_time).total_seconds()
        self.documents_indexed += indexed
        
        stats = {
            "index": index_name,
            "total_records": total_records,
            "indexed": indexed,
            "errors": errors,
            "validation_errors": validation_errors,
            "duration_seconds": round(duration, 2),
            "docs_per_second": round(indexed / duration) if duration > 0 else 0
        }
        
        logger.info(f"Completed indexing to {index_name}: {indexed}/{total_records} documents")
        
        return stats
    
    @log_stage("Elasticsearch: Index all entities")
    def index_all(self) -> Dict[str, Any]:
        """Index all entity types to Elasticsearch."""
        stats = {}
        
        # Define tables to check
        tables = [
            ("gold_properties", "properties", self.index_properties),
            ("gold_neighborhoods", "neighborhoods", self.index_neighborhoods),
            ("gold_wikipedia", "wikipedia", self.index_wikipedia)
        ]
        
        for table_name, index_name, index_method in tables:
            if self.connection_manager.table_exists(table_name):
                stats[index_name] = index_method()
        
        return {
            "total_indexed": self.documents_indexed,
            "entities": stats
        }