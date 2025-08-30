"""Elasticsearch writer with type-safe data transformation.

Following best practices:
- No isinstance or hasattr checks
- No runtime type checking
- Pure Pydantic validation
- Direct field access only
"""

from typing import Dict, Any, List
from datetime import datetime
from decimal import Decimal
import logging
import os
import json
from pydantic import BaseModel, Field, ConfigDict, field_serializer
from squack_pipeline_v2.core.connection import DuckDBConnectionManager as ConnectionManager
from squack_pipeline_v2.core.logging import log_stage
from squack_pipeline_v2.core.settings import ElasticsearchConfig

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
    neighborhood_id: str  # CRITICAL: Added missing field
    price: float
    bedrooms: int
    bathrooms: float
    square_feet: float
    property_type: str
    year_built: int = 0
    lot_size: float = 0.0
    address: AddressInfo  # Changed to nested object
    price_per_sqft: float = 0.0
    price_category: str = ""
    market_heat_score: float = 0.0
    parking: ParkingInfo
    description: str = ""
    features: List[str] = Field(default_factory=list)
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
    median_income: float
    median_home_price: float
    walkability_score: float = 0.0
    school_score: float = 0.0
    overall_livability_score: float = 0.0
    location: GeoPoint  # Using standard geo_point
    description: str = ""
    amenities: List[str] = Field(default_factory=list)
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
    best_city: str = ""
    best_state: str = ""
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
    """Property input from DuckDB with proper type handling."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    listing_id: str
    neighborhood_id: str  # CRITICAL: Added missing field
    price: Decimal
    bedrooms: int
    bathrooms: Decimal
    square_feet: Decimal
    property_type: str
    year_built: int = 0
    lot_size: Decimal = Decimal("0")
    address: Dict[str, Any]  # Address object from Gold layer
    price_per_sqft: Decimal = Decimal("0")
    price_category: str = ""
    market_heat_score: Decimal = Decimal("0")
    parking: Dict[str, Any] = Field(default_factory=dict)  # Parking object from Gold
    description: str = ""
    features: List[str] = Field(default_factory=list)
    listing_date: str = ""
    days_on_market: int = 0
    virtual_tour_url: str = ""
    images: List[str] = Field(default_factory=list)
    embedding: List[float] = Field(default_factory=list)
    embedding_model: str = ""
    embedding_dimension: int = 0
    embedded_at: datetime = Field(default_factory=datetime.now)
    
    @field_serializer('price', 'bathrooms', 'square_feet', 'lot_size', 'price_per_sqft', 'market_heat_score')
    def serialize_decimal(self, value: Decimal) -> float:
        """Convert Decimal to float for serialization."""
        return float(value)


class NeighborhoodInput(BaseModel):
    """Neighborhood input from DuckDB with proper type handling."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    neighborhood_id: str
    name: str
    city: str
    state: str  # Changed from state_code - comes from address.state in Silver
    population: int
    median_income: Decimal
    median_home_price: Decimal
    walkability_score: Decimal = Decimal("0")
    school_score: Decimal = Decimal("0")
    overall_livability_score: Decimal = Decimal("0")
    center_latitude: Decimal = Decimal("0")
    center_longitude: Decimal = Decimal("0")
    description: str = ""
    amenities: List[str] = Field(default_factory=list)
    demographics: Dict[str, Any] = Field(default_factory=dict)
    embedding: List[float] = Field(default_factory=list)
    embedding_model: str = ""
    embedding_dimension: int = 0
    embedded_at: datetime = Field(default_factory=datetime.now)
    
    @field_serializer('median_income', 'median_home_price', 'walkability_score',
                      'school_score', 'overall_livability_score', 
                      'center_latitude', 'center_longitude')
    def serialize_decimal(self, value: Decimal) -> float:
        """Convert Decimal to float for serialization."""
        return float(value)


class WikipediaInput(BaseModel):
    """Wikipedia input from DuckDB with proper type handling."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    page_id: int
    title: str
    url: str = ""
    article_filename: str = ""
    long_summary: str = ""
    short_summary: str = ""
    full_content: str = ""
    content_length: int = 0
    content_loaded: bool = False
    content_loaded_at: datetime = Field(default_factory=datetime.now)
    categories: str = ""  # JSON string from DB
    key_topics: List[str] = Field(default_factory=list)
    relevance_score: Decimal = Decimal("0")
    article_quality_score: Decimal = Decimal("0")
    article_quality: str = ""
    best_city: str = ""
    best_state: str = ""
    last_updated: datetime = Field(default_factory=datetime.now)
    embedding: List[float] = Field(default_factory=list)
    embedding_model: str = ""
    embedding_dimension: int = 0
    embedded_at: datetime = Field(default_factory=datetime.now)
    
    @field_serializer('relevance_score', 'article_quality_score')
    def serialize_decimal(self, value: Decimal) -> float:
        """Convert Decimal to float for serialization."""
        return float(value)
    
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
    
    @staticmethod
    def transform(record: Dict[str, Any]) -> PropertyDocument:
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
        
        # Create document with all required fields
        return PropertyDocument(
            listing_id=input_data.listing_id,
            neighborhood_id=input_data.neighborhood_id,  # CRITICAL: Include neighborhood_id
            price=float(input_data.price),
            bedrooms=input_data.bedrooms,
            bathrooms=float(input_data.bathrooms),
            square_feet=float(input_data.square_feet),
            property_type=input_data.property_type,
            year_built=input_data.year_built,
            lot_size=float(input_data.lot_size),
            address=address,  # Nested address object
            price_per_sqft=float(input_data.price_per_sqft),
            price_category=input_data.price_category,
            market_heat_score=float(input_data.market_heat_score),
            parking=parking,
            description=input_data.description,
            features=input_data.features,
            listing_date=input_data.listing_date,
            days_on_market=input_data.days_on_market,
            virtual_tour_url=input_data.virtual_tour_url,
            images=input_data.images,
            embedding=input_data.embedding,
            embedding_model=input_data.embedding_model,
            embedding_dimension=input_data.embedding_dimension,
            embedded_at=input_data.embedded_at
        )


class NeighborhoodTransformer:
    """Transform neighborhood records to documents."""
    
    @staticmethod
    def transform(record: Dict[str, Any]) -> NeighborhoodDocument:
        """Transform a neighborhood record to document."""
        # Parse input with proper type handling
        input_data = NeighborhoodInput(**record)
        
        # Create geo point from center coordinates
        location = GeoPoint(
            lat=float(input_data.center_latitude),
            lon=float(input_data.center_longitude)
        )
        
        # Create document with corrected field names
        return NeighborhoodDocument(
            neighborhood_id=input_data.neighborhood_id,
            name=input_data.name,
            city=input_data.city,
            state=input_data.state,  # Using 'state' not 'state_code'
            population=input_data.population,
            median_income=float(input_data.median_income),
            median_home_price=float(input_data.median_home_price),
            walkability_score=float(input_data.walkability_score),
            school_score=float(input_data.school_score),
            overall_livability_score=float(input_data.overall_livability_score),
            location=location,  # Standard geo_point
            description=input_data.description,
            amenities=input_data.amenities,
            demographics=input_data.demographics,
            embedding=input_data.embedding,
            embedding_model=input_data.embedding_model,
            embedding_dimension=input_data.embedding_dimension,
            embedded_at=input_data.embedded_at
        )


class WikipediaTransformer:
    """Transform Wikipedia records to documents."""
    
    @staticmethod
    def transform(record: Dict[str, Any]) -> WikipediaDocument:
        """Transform a Wikipedia record to document."""
        # Parse input with proper type handling
        input_data = WikipediaInput(**record)
        
        # Create document with explicit conversions
        return WikipediaDocument(
            page_id=str(input_data.page_id),
            title=input_data.title,
            url=input_data.url,
            article_filename=input_data.article_filename,
            long_summary=input_data.long_summary,
            short_summary=input_data.short_summary,
            full_content=input_data.full_content,
            content_length=input_data.content_length,
            content_loaded=input_data.content_loaded,
            content_loaded_at=input_data.content_loaded_at,
            categories=input_data.parse_categories(),
            key_topics=input_data.key_topics,
            relevance_score=float(input_data.relevance_score),
            article_quality_score=float(input_data.article_quality_score),
            article_quality=input_data.article_quality,
            best_city=input_data.best_city,
            best_state=input_data.best_state,
            last_updated=input_data.last_updated,
            embedding=input_data.embedding,
            embedding_model=input_data.embedding_model,
            embedding_dimension=input_data.embedding_dimension,
            embedded_at=input_data.embedded_at
        )


# ============================================================================
# ELASTICSEARCH WRITER
# ============================================================================

class ElasticsearchWriter:
    """Elasticsearch writer with type-safe transformation."""
    
    def __init__(
        self,
        connection_manager: ConnectionManager,
        elasticsearch_config: ElasticsearchConfig
    ):
        """Initialize Elasticsearch writer."""
        self.connection_manager = connection_manager
        self.config = elasticsearch_config
        self.documents_indexed = 0
        self.es_client = self._create_client()
        
        # Initialize transformers
        self.property_transformer = PropertyTransformer()
        self.neighborhood_transformer = NeighborhoodTransformer()
        self.wikipedia_transformer = WikipediaTransformer()
        
        # Verify connection
        if not self.es_client.ping():
            raise ConnectionError("Failed to connect to Elasticsearch")
    
    def _create_client(self):
        """Create Elasticsearch client."""
        from elasticsearch import Elasticsearch
        
        es_user = os.getenv("ELASTICSEARCH_USERNAME")
        es_password = os.getenv("ELASTICSEARCH_PASSWORD")
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
        embeddings_table = "embeddings_properties"
        has_embeddings = self.connection_manager.table_exists(embeddings_table)
        
        if has_embeddings:
            query = f"""
            SELECT 
                p.*,
                e.embedding,
                e.model_name as embedding_model,
                e.dimension as embedding_dimension,
                e.generated_at as embedded_at
            FROM {table_name} p
            LEFT JOIN {embeddings_table} e
                ON p.listing_id = e.listing_id
            """
        else:
            query = f"SELECT * FROM {table_name}"
        
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
        embeddings_table = "embeddings_neighborhoods"
        has_embeddings = self.connection_manager.table_exists(embeddings_table)
        
        if has_embeddings:
            query = f"""
            SELECT 
                n.*,
                e.embedding,
                e.model_name as embedding_model,
                e.dimension as embedding_dimension,
                e.generated_at as embedded_at
            FROM {table_name} n
            LEFT JOIN {embeddings_table} e
                ON n.neighborhood_id = e.neighborhood_id
            """
        else:
            query = f"SELECT * FROM {table_name}"
        
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
        embeddings_table = "embeddings_wikipedia"
        has_embeddings = self.connection_manager.table_exists(embeddings_table)
        
        if has_embeddings:
            query = f"""
            SELECT 
                w.*,
                e.embedding,
                e.model_name as embedding_model,
                e.dimension as embedding_dimension,
                e.generated_at as embedded_at
            FROM {table_name} w
            LEFT JOIN {embeddings_table} e
                ON w.page_id = e.page_id
            """
        else:
            query = f"SELECT * FROM {table_name}"
        
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
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM ({query}) t"
        total_records = self.connection_manager.execute(count_query).fetchone()[0]
        
        logger.info(f"Indexing {total_records} documents to {index_name}")
        
        indexed = 0
        errors = 0
        validation_errors = 0
        
        offset = 0
        start_time = datetime.now()
        
        while offset < total_records:
            # Fetch batch from DuckDB
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
                    logger.debug(f"Validation error for {id_field}={record.get(id_field, 'unknown')}: {e}")
                    validation_errors += 1
            
            # Bulk index
            if actions:
                try:
                    success, failed = bulk(
                        self.es_client,
                        actions,
                        raise_on_error=False,
                        raise_on_exception=False
                    )
                    indexed += success
                    if failed:
                        errors += len(failed)
                        for failure in failed[:3]:
                            logger.warning(f"Indexing failure: {failure}")
                        
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