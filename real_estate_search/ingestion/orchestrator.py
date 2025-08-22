"""
Ingestion orchestrator with single YAML-based configuration.
Replaces dual-config orchestrator for cleaner architecture.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import structlog
from elasticsearch import Elasticsearch, helpers

from ..config.config import Config
from ..indexer.property_indexer import PropertyIndexer
from ..indexer.models import Property, Address, GeoLocation
from ..wikipedia.enricher import PropertyEnricher

logger = structlog.get_logger(__name__)


class IngestionOrchestrator:
    """
    Clean orchestrator with single YAML-based configuration.
    Coordinates ingestion of properties and Wikipedia data.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize with YAML-based configuration."""
        self.config = config or Config.from_yaml()
        
        # Initialize Elasticsearch client
        self.es_client = self._create_es_client()
        
        # Initialize components
        self.property_indexer = PropertyIndexer(settings=None)  # Will update to use config
        self.property_indexer.es_client = self.es_client
        self.enricher = PropertyEnricher()
        
        logger.info(
            "Initialized unified orchestrator",
            demo_mode=self.config.demo_mode,
            es_host=self.config.elasticsearch.host,
            embedding_model=self.config.embedding.model_name
        )
    
    def _create_es_client(self) -> Elasticsearch:
        """Create Elasticsearch client from unified config."""
        client_config = self.config.get_es_client_config()
        return Elasticsearch(**client_config)
    
    def ingest_all(self) -> Dict[str, Any]:
        """
        Orchestrate all ingestion for demo.
        In demo mode, always drops and recreates indices.
        
        Returns:
            Statistics about ingested data
        """
        if self.config.demo_mode and self.config.force_recreate:
            logger.info("Demo mode: Dropping and recreating all indices")
            self._recreate_all_indices()
        
        stats = {}
        
        # Stage 1: Ingest Wikipedia data
        logger.info("Stage 1: Ingesting Wikipedia data")
        wiki_stats = self._ingest_wikipedia_data()
        stats["wikipedia"] = wiki_stats
        
        # Stage 2: Ingest and enrich properties
        logger.info("Stage 2: Ingesting properties with enrichment")
        property_stats = self._ingest_properties()
        stats["properties"] = property_stats
        
        logger.info("Ingestion complete", stats=stats)
        return stats
    
    def _recreate_all_indices(self):
        """Drop and recreate all indices for clean demo."""
        indices = [
            self.config.elasticsearch.property_index,
            self.config.get_wiki_chunks_index(),
            self.config.get_wiki_summaries_index()
        ]
        
        for index in indices:
            try:
                if self.es_client.indices.exists(index=index):
                    self.es_client.indices.delete(index=index)
                    logger.info(f"Deleted index: {index}")
            except Exception as e:
                logger.warning(f"Could not delete index {index}: {e}")
    
    def _ingest_wikipedia_data(self) -> Dict[str, Any]:
        """
        Ingest Wikipedia chunks and summaries.
        Integrates with wiki_embed module for processing.
        """
        from wiki_embed.pipeline import WikipediaEmbeddingPipeline
        from wiki_embed.models import Config as WikiConfig
        
        stats = {
            "chunks": {"indexed": 0, "status": "pending"},
            "summaries": {"indexed": 0, "status": "pending"}
        }
        
        # Create a compatible config for wiki_embed
        wiki_config_dict = {
            "embedding": {
                "provider": self.config.embedding.provider,
                "model_name": self.config.embedding.model_name,
                "ollama_host": self.config.embedding.ollama_host
            },
            "vector_store": {
                "provider": "elasticsearch",
                "elasticsearch": {
                    "host": self.config.elasticsearch.host,
                    "port": self.config.elasticsearch.port,
                    "index_prefix": self.config.elasticsearch.wiki_chunks_index_prefix
                }
            },
            "data": {
                "wikipedia_db": str(self.config.data.wikipedia_db),
                "wikipedia_pages_dir": str(self.config.data.wikipedia_pages_dir)
            },
            "chunking": {
                "chunk_size": self.config.chunking.chunk_size,
                "chunk_overlap": self.config.chunking.chunk_overlap
            }
        }
        
        wiki_config = WikiConfig(**wiki_config_dict)
        pipeline = WikipediaEmbeddingPipeline(wiki_config)
        
        # Create embeddings for Wikipedia chunks
        chunk_count = pipeline.create_embeddings(force_recreate=self.config.force_recreate)
        stats["chunks"] = {"indexed": chunk_count, "status": "success"}
        
        logger.info(f"Indexed {chunk_count} Wikipedia chunks")
        
        return stats
    
    def _ingest_properties(self) -> Dict[str, Any]:
        """Load and index properties with Wikipedia enrichment."""
        stats = {
            "total": 0,
            "indexed": 0,
            "failed": 0,
            "enriched": 0
        }
        
        try:
            # Ensure property index exists
            if not self.es_client.indices.exists(index=self.config.elasticsearch.property_index):
                self.property_indexer.create_index(force=True)
            
            # Load properties from JSON files
            properties = self._load_properties()
            stats["total"] = len(properties)
            
            if not properties:
                logger.warning("No properties found to index")
                return stats
            
            # Enrich properties with Wikipedia data
            for prop in properties:
                try:
                    enriched = self.enricher.enrich_property(prop)
                    if enriched != prop:  # Check if enrichment added data
                        stats["enriched"] += 1
                except Exception as e:
                    logger.warning(f"Failed to enrich property {prop.listing_id}: {e}")
            
            # Index properties in batches
            batch_size = self.config.elasticsearch.batch_size
            for i in range(0, len(properties), batch_size):
                batch = properties[i:i+batch_size]
                result = self.property_indexer.index_properties(batch)
                stats["indexed"] += result.success
                stats["failed"] += result.failed
                
                logger.info(
                    f"Indexed batch {i//batch_size + 1}",
                    indexed=result.success,
                    failed=result.failed
                )
            
        except Exception as e:
            logger.error(f"Property ingestion failed: {e}")
            stats["status"] = "failed"
            stats["error"] = str(e)
        
        return stats
    
    def _load_properties(self) -> List[Property]:
        """Load properties from JSON files in the configured directory."""
        properties = []
        
        # Find all properties JSON files
        properties_dir = Path(self.config.data.properties_dir)
        if not properties_dir.exists():
            logger.warning(f"Properties directory not found: {properties_dir}")
            return properties
        
        property_files = list(properties_dir.glob("properties_*.json"))
        
        for prop_file in property_files:
            try:
                with open(prop_file, 'r') as f:
                    data = json.load(f)
                
                # Handle different JSON structures
                if isinstance(data, list):
                    properties_data = data
                elif isinstance(data, dict) and 'properties' in data:
                    properties_data = data['properties']
                else:
                    logger.warning(f"Unknown JSON structure in {prop_file}")
                    continue
                
                # Convert to Property objects
                for prop_data in properties_data:
                    try:
                        property_obj = self._parse_property(prop_data)
                        if property_obj:
                            properties.append(property_obj)
                    except Exception as e:
                        logger.warning(f"Failed to parse property: {e}")
                
                logger.info(f"Loaded {len(properties_data)} properties from {prop_file.name}")
                
            except Exception as e:
                logger.error(f"Failed to load properties from {prop_file}: {e}")
        
        return properties
    
    def _parse_property(self, prop_data: dict) -> Optional[Property]:
        """Parse property data into Property model."""
        try:
            # Extract nested data
            details = prop_data.get("property_details", {})
            addr = prop_data.get("address", {})
            
            # Map property type format
            prop_type = details.get("property_type", "other")
            type_mapping = {
                "single-family": "single_family",
                "multi-family": "multi_family",
                "single_family": "single_family",
                "multi_family": "multi_family",
                "condo": "condo",
                "townhouse": "townhouse",
                "land": "land",
                "other": "other"
            }
            prop_type = type_mapping.get(prop_type, "other")
            
            # Create Address object
            coordinates = prop_data.get("coordinates")
            geo_location = None
            if coordinates:
                if isinstance(coordinates, dict):
                    lat = coordinates.get("latitude") or coordinates.get("lat")
                    lon = coordinates.get("longitude") or coordinates.get("lon") or coordinates.get("lng")
                    if lat and lon:
                        geo_location = GeoLocation(lat=lat, lon=lon)
            
            address_obj = Address(
                street=addr.get("street", ""),
                city=addr.get("city", ""),
                state=addr.get("state", ""),
                zip_code=addr.get("zip_code") or addr.get("zip", "00000"),
                coordinates=geo_location
            )
            
            # Create Property object
            property_obj = Property(
                listing_id=prop_data.get("listing_id", ""),
                mls_number=prop_data.get("mls_number"),
                status=prop_data.get("status", "active"),
                property_type=prop_type,
                price=prop_data.get("listing_price", 0) or prop_data.get("price", 0),
                bedrooms=details.get("bedrooms", 0),
                bathrooms=details.get("bathrooms", 0),
                square_feet=details.get("square_feet"),
                lot_size=details.get("lot_size"),
                year_built=details.get("year_built"),
                address=address_obj,
                description=prop_data.get("description"),
                features=prop_data.get("features", []),
                images=prop_data.get("images", []),
                virtual_tour_url=prop_data.get("virtual_tour_url"),
                listing_date=prop_data.get("listing_date"),
                last_updated=prop_data.get("last_updated"),
                listing_agent=prop_data.get("listing_agent", {})
            )
            
            return property_obj
            
        except Exception as e:
            logger.error(f"Failed to parse property: {e}", prop_data=prop_data)
            return None