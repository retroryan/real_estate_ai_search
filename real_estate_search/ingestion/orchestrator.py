"""
Minimal orchestrator for unified ingestion.
Reuses all existing components from wiki_embed and real_estate_search.
"""

from pathlib import Path
from typing import Optional
import yaml
import structlog

# Import directly from existing modules - no copying needed
from wiki_embed.models import Config
from wiki_embed.pipeline import WikipediaEmbeddingPipeline
from wiki_embed.embedding import create_embedding_model
from wiki_embed.elasticsearch import ElasticsearchStore
from wiki_embed.utils import load_summaries_from_db, configure_from_config

from llama_index.core import Document
from llama_index.core.node_parser import SimpleNodeParser

from ..indexer import PropertyIndexer
from ..config.settings import Settings

logger = structlog.get_logger(__name__)


class UnifiedIngestionPipeline:
    """
    Minimal orchestrator that reuses existing components.
    Total new code: Just this orchestration logic.
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with configuration."""
        # Load wiki_embed style config
        with open(config_path) as f:
            config_dict = yaml.safe_load(f)
        self.wiki_config = Config(**config_dict)
        
        # Load real_estate_search settings
        self.property_settings = Settings.load()
        
        # Initialize components (all existing)
        self.embed_model, self.model_id = create_embedding_model(self.wiki_config)
        self.es_store = ElasticsearchStore(self.wiki_config)
        
        logger.info("Initialized ingestion pipeline", 
                   embedding_model=self.model_id,
                   es_host=self.wiki_config.vector_store.elasticsearch.host)
    
    def ingest_all(self, force_recreate: bool = False) -> dict:
        """
        Orchestrate all ingestion using existing components.
        
        Returns:
            Statistics about ingested data
        """
        stats = {}
        
        # 1. Properties - Use existing PropertyIndexer
        logger.info("Starting property ingestion")
        stats["properties"] = self._ingest_properties(force_recreate)
        
        # 2. Wiki Chunks - Use existing WikipediaEmbeddingPipeline
        logger.info("Starting Wikipedia chunk ingestion")
        stats["wiki_chunks"] = self._ingest_wiki_chunks(force_recreate)
        
        # 3. Wiki Summaries - Minimal new logic
        logger.info("Starting Wikipedia summary ingestion")
        stats["wiki_summaries"] = self._ingest_wiki_summaries(force_recreate)
        
        logger.info("Ingestion complete", stats=stats)
        return stats
    
    def _ingest_properties(self, force_recreate: bool) -> dict:
        """Ingest properties using existing PropertyIndexer."""
        import json
        
        try:
            indexer = PropertyIndexer(self.property_settings)
            
            # Create or recreate index
            indexer.create_index(force=force_recreate)
            
            # Index from JSON files
            property_files = list(Path("real_estate_data").glob("properties_*.json"))
            total = 0
            
            for prop_file in property_files:
                # Load properties from JSON
                with open(prop_file, 'r') as f:
                    properties_data = json.load(f)
                
                # Convert to Property objects
                from ..indexer.models import Property, Address
                properties = []
                for prop_data in properties_data:
                    # Extract property details
                    details = prop_data.get("property_details", {})
                    addr = prop_data.get("address", {})
                    
                    # Map property type format (e.g., "single-family" -> "single_family")
                    prop_type = details.get("property_type", "other")
                    if prop_type == "single-family":
                        prop_type = "single_family"
                    elif prop_type == "multi-family":
                        prop_type = "multi_family"
                    
                    # Create Address object with proper field mapping
                    address_obj = Address(
                        street=addr.get("street", ""),
                        city=addr.get("city", ""),
                        state=addr.get("state", ""),
                        zip_code=addr.get("zip", "00000"),  # Map "zip" to "zip_code"
                        coordinates=prop_data.get("coordinates")
                    )
                    
                    # Create Property object (adapting to expected format)
                    property_obj = Property(
                        listing_id=prop_data.get("listing_id"),
                        mls_number=prop_data.get("mls_number"),
                        status=prop_data.get("status", "active"),
                        property_type=prop_type,
                        price=prop_data.get("listing_price", 0),
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
                    properties.append(property_obj)
                
                # Index properties  
                results = indexer.index_properties(properties)
                # results is an IndexStats object with success/failed/total fields
                indexed_count = results.success
                total += indexed_count
                logger.info(f"Indexed {indexed_count} properties from {prop_file.name}")
            
            return {"indexed": total, "status": "success"}
            
        except Exception as e:
            logger.error(f"Property ingestion failed: {e}")
            return {"indexed": 0, "status": "failed", "error": str(e)}
    
    def _ingest_wiki_chunks(self, force_recreate: bool) -> dict:
        """Ingest wiki chunks using existing WikipediaEmbeddingPipeline."""
        try:
            # Configure wiki_embed globally
            configure_from_config(self.wiki_config)
            
            # Use existing pipeline entirely
            pipeline = WikipediaEmbeddingPipeline(self.wiki_config)
            count = pipeline.create_embeddings(force_recreate=force_recreate)
            
            return {"indexed": count, "status": "success"}
            
        except Exception as e:
            logger.error(f"Wiki chunk ingestion failed: {e}")
            return {"indexed": 0, "status": "failed", "error": str(e)}
    
    def _ingest_wiki_summaries(self, force_recreate: bool) -> dict:
        """
        Ingest Wikipedia summaries with embeddings.
        This is the only new ingestion logic needed.
        """
        try:
            # Create index name following wiki_embed pattern
            index_name = f"wiki_summaries_{self.model_id}"
            
            # Create or recreate index
            if force_recreate:
                self.es_store.delete_collection(index_name)
            
            self.es_store.create_collection(
                index_name,
                metadata={
                    "type": "summaries",
                    "model": self.model_id,
                    "created_by": "real_estate_search.ingestion"
                }
            )
            
            # Load summaries from database
            summaries = load_summaries_from_db(self.wiki_config.data.wikipedia_db)
            
            if not summaries:
                logger.warning("No summaries found in database")
                return {"indexed": 0, "status": "no_data"}
            
            # Convert to LlamaIndex Documents
            documents = []
            for summary in summaries:
                # Create searchable text
                text = f"{summary.title}\n{summary.short_summary}"
                if summary.key_topics:
                    text += f"\n{summary.key_topics}"
                
                # Create document with metadata
                doc = Document(
                    text=text,
                    metadata={
                        "page_id": summary.page_id,
                        "title": summary.title,
                        "city": summary.best_city,
                        "county": summary.best_county,
                        "state": summary.best_state,
                        "confidence": summary.overall_confidence
                    }
                )
                documents.append(doc)
            
            # Parse into nodes (following wiki_embed pattern)
            parser = SimpleNodeParser.from_defaults(
                chunk_size=self.wiki_config.chunking.chunk_size,
                chunk_overlap=self.wiki_config.chunking.chunk_overlap
            )
            nodes = parser.get_nodes_from_documents(documents)
            
            # Batch embed and index
            self.es_store.current_index = index_name
            batch_size = 100
            total_indexed = 0
            
            for i in range(0, len(nodes), batch_size):
                batch = nodes[i:i+batch_size]
                
                # Generate embeddings
                texts = [node.text for node in batch]
                embeddings = self.embed_model.get_text_embedding_batch(texts)
                
                # Prepare for indexing
                ids = [f"summary_{node.metadata['page_id']}_{i+j}" 
                       for j, node in enumerate(batch)]
                metadatas = [node.metadata for node in batch]
                
                # Index batch
                self.es_store.add_embeddings(
                    embeddings=embeddings,
                    texts=texts,
                    metadatas=metadatas,
                    ids=ids
                )
                
                total_indexed += len(batch)
                logger.info(f"Indexed {total_indexed}/{len(nodes)} summary nodes")
            
            return {"indexed": total_indexed, "summaries": len(summaries), "status": "success"}
            
        except Exception as e:
            logger.error(f"Wiki summary ingestion failed: {e}")
            return {"indexed": 0, "status": "failed", "error": str(e)}