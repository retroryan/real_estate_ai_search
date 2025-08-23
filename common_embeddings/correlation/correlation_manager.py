"""
Correlation Manager for matching embeddings with source data.

Provides comprehensive correlation capabilities including identifier extraction,
source data loading, bulk correlation, and multi-chunk document handling.
"""

import os
import json
import sqlite3
from typing import Dict, Any, List, Optional, Set, Tuple, Union
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid

from ..models.enums import EntityType, SourceType
from ..storage.query_manager import QueryManager
from ..utils.correlation import CorrelationValidator, ChunkReconstructor
from ..utils.logging import get_logger, PerformanceLogger
from ..models.exceptions import StorageError
from .models import (
    CorrelationResult, 
    EnrichedEntity, 
    CorrelationReport, 
    SourceDataCache,
    BulkCorrelationRequest
)

logger = get_logger(__name__)


class CorrelationManager:
    """
    Advanced correlation manager for matching embeddings with source data.
    
    Handles identifier extraction, source data lookup, bulk correlation,
    and multi-chunk document reconstruction.
    """
    
    def __init__(self, query_manager: QueryManager, data_root_path: str = None):
        """
        Initialize correlation manager.
        
        Args:
            query_manager: QueryManager for ChromaDB operations
            data_root_path: Root path for source data files
        """
        self.query_manager = query_manager
        self.data_root_path = data_root_path or "/Users/ryanknight/projects/temporal/real_estate_ai_search"
        
        # Initialize components
        self.validator = CorrelationValidator()
        self.reconstructor = ChunkReconstructor()
        
        # Cache for source data
        self._source_caches: Dict[str, SourceDataCache] = {}
        
        logger.info(f"Initialized CorrelationManager with data root: {self.data_root_path}")
    
    def correlate_embedding(
        self,
        embedding_id: str,
        collection_name: str,
        use_cache: bool = True
    ) -> CorrelationResult:
        """
        Correlate a single embedding with its source data.
        
        Args:
            embedding_id: ID of embedding to correlate
            collection_name: Collection containing the embedding
            use_cache: Whether to use source data caching
            
        Returns:
            CorrelationResult with correlation status and data
        """
        logger.debug(f"Correlating embedding '{embedding_id}' from collection '{collection_name}'")
        
        start_time = datetime.now()
        
        try:
            # Get embedding metadata from ChromaDB
            embedding_metadata = self._get_embedding_metadata(embedding_id, collection_name)
            if not embedding_metadata:
                return CorrelationResult(
                    embedding_id=embedding_id,
                    entity_type=EntityType.PROPERTY,  # Default fallback
                    is_correlated=False,
                    correlation_method="metadata_lookup",
                    confidence_score=0.0,
                    embedding_metadata={},
                    error_message=f"Embedding '{embedding_id}' not found in collection '{collection_name}'"
                )
            
            # Extract entity information
            entity_type = EntityType(embedding_metadata.get('entity_type', EntityType.PROPERTY.value))
            source_type = SourceType(embedding_metadata.get('source_type', SourceType.PROPERTY_JSON.value))
            
            # Extract identifier for correlation
            identifier = self._extract_identifier(embedding_metadata, entity_type)
            if not identifier:
                return CorrelationResult(
                    embedding_id=embedding_id,
                    entity_type=entity_type,
                    is_correlated=False,
                    correlation_method="identifier_extraction",
                    confidence_score=0.0,
                    embedding_metadata=embedding_metadata,
                    error_message=f"Could not extract identifier for entity type {entity_type.value}"
                )
            
            # Load source data
            source_data = self._load_source_data(identifier, entity_type, source_type, use_cache)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if source_data:
                logger.debug(f"Successfully correlated embedding '{embedding_id}' with identifier '{identifier}'")
                return CorrelationResult(
                    embedding_id=embedding_id,
                    entity_type=entity_type,
                    is_correlated=True,
                    correlation_method="identifier_lookup",
                    confidence_score=1.0,
                    embedding_metadata=embedding_metadata,
                    source_data=source_data,
                    identifier_used=identifier,
                    source_file=embedding_metadata.get('source_file'),
                    processing_time_ms=processing_time
                )
            else:
                return CorrelationResult(
                    embedding_id=embedding_id,
                    entity_type=entity_type,
                    is_correlated=False,
                    correlation_method="identifier_lookup",
                    confidence_score=0.0,
                    embedding_metadata=embedding_metadata,
                    identifier_used=identifier,
                    error_message=f"Source data not found for identifier '{identifier}'",
                    processing_time_ms=processing_time
                )
                
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"Correlation failed for embedding '{embedding_id}': {e}")
            return CorrelationResult(
                embedding_id=embedding_id,
                entity_type=EntityType.PROPERTY,  # Default fallback
                is_correlated=False,
                correlation_method="error",
                confidence_score=0.0,
                embedding_metadata=embedding_metadata if 'embedding_metadata' in locals() else {},
                error_message=str(e),
                processing_time_ms=processing_time
            )
    
    def bulk_correlate(
        self,
        request: BulkCorrelationRequest
    ) -> Tuple[List[EnrichedEntity], CorrelationReport]:
        """
        Perform bulk correlation across multiple collections.
        
        Args:
            request: Configuration for bulk correlation
            
        Returns:
            Tuple of (enriched_entities, correlation_report)
        """
        logger.info(f"Starting bulk correlation for {len(request.collection_names)} collections")
        
        # Initialize report
        report = CorrelationReport(
            report_id=str(uuid.uuid4()),
            collection_names=request.collection_names,
            entity_types=request.entity_types or [],
            started_at=datetime.now()
        )
        
        enriched_entities = []
        
        try:
            with PerformanceLogger(f"Bulk correlation of {len(request.collection_names)} collections") as perf:
                # Process each collection
                for collection_name in request.collection_names:
                    collection_entities = self._process_collection(
                        collection_name, 
                        request, 
                        report
                    )
                    enriched_entities.extend(collection_entities)
                
                # Update cache statistics in report
                for cache_key, cache in self._source_caches.items():
                    report.cache_statistics[cache_key] = {
                        'hit_rate': cache.hit_rate,
                        'total_entities': cache.total_entities,
                        'cache_hits': cache.cache_hits,
                        'cache_misses': cache.cache_misses
                    }
                
                perf.add_metric("total_entities", len(enriched_entities))
                perf.add_metric("success_rate", report.success_rate)
                
        except Exception as e:
            logger.error(f"Bulk correlation failed: {e}")
            report.add_error(f"bulk_processing_error: {str(e)}")
        
        # Complete the report
        report.total_embeddings = report.successful_correlations + report.failed_correlations
        report.complete_report()
        
        logger.info(f"Bulk correlation completed: {report.get_summary()}")
        return enriched_entities, report
    
    def _process_collection(
        self,
        collection_name: str,
        request: BulkCorrelationRequest,
        report: CorrelationReport
    ) -> List[EnrichedEntity]:
        """Process a single collection for bulk correlation."""
        
        logger.info(f"Processing collection: {collection_name}")
        
        try:
            # Get all embeddings from collection with metadata filter
            metadata_filter = None
            if request.entity_types:
                entity_values = [et.value for et in request.entity_types]
                if len(entity_values) == 1:
                    metadata_filter = {"entity_type": {"$eq": entity_values[0]}}
                else:
                    metadata_filter = {"entity_type": {"$in": entity_values}}
            
            # Get embeddings metadata
            embeddings_metadata = self.query_manager.metadata_only_search(
                collection_name=collection_name,
                metadata_filter=metadata_filter or {}
            )
            
            if not embeddings_metadata:
                logger.warning(f"No embeddings found in collection '{collection_name}'")
                return []
            
            logger.info(f"Found {len(embeddings_metadata)} embeddings in collection '{collection_name}'")
            
            # Group embeddings by entity for reconstruction
            entity_groups = self._group_embeddings_by_entity(embeddings_metadata)
            
            enriched_entities = []
            
            # Process each entity group
            for entity_id, embedding_group in entity_groups.items():
                try:
                    enriched_entity = self._create_enriched_entity(
                        entity_id,
                        embedding_group,
                        request.use_cache
                    )
                    
                    if enriched_entity:
                        enriched_entities.append(enriched_entity)
                        report.add_success()
                        
                        # Update entity type counts
                        entity_type_str = enriched_entity.entity_type.value
                        report.entities_by_type[entity_type_str] = report.entities_by_type.get(entity_type_str, 0) + 1
                        
                        # Check completeness
                        if not enriched_entity.is_complete:
                            report.incomplete_entities += 1
                    else:
                        report.add_error("enrichment_failed")
                        
                except Exception as e:
                    logger.error(f"Failed to process entity '{entity_id}': {e}")
                    report.add_error(f"entity_processing_error")
            
            return enriched_entities
            
        except Exception as e:
            logger.error(f"Failed to process collection '{collection_name}': {e}")
            report.add_error("collection_processing_error")
            return []
    
    def _group_embeddings_by_entity(
        self,
        embeddings_metadata: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group embeddings by their primary entity identifier."""
        
        entity_groups = {}
        
        for metadata in embeddings_metadata:
            # Extract entity identifier
            entity_type = EntityType(metadata.get('entity_type', EntityType.PROPERTY.value))
            identifier = self._extract_identifier(metadata, entity_type)
            
            if identifier:
                if identifier not in entity_groups:
                    entity_groups[identifier] = []
                entity_groups[identifier].append(metadata)
            else:
                logger.warning(f"Could not extract identifier from metadata: {metadata}")
        
        logger.info(f"Grouped {len(embeddings_metadata)} embeddings into {len(entity_groups)} entities")
        return entity_groups
    
    def _create_enriched_entity(
        self,
        entity_id: str,
        embedding_group: List[Dict[str, Any]],
        use_cache: bool = True
    ) -> Optional[EnrichedEntity]:
        """Create an enriched entity from a group of embeddings."""
        
        if not embedding_group:
            return None
        
        # Get entity information from first embedding
        first_metadata = embedding_group[0]
        entity_type = EntityType(first_metadata.get('entity_type', EntityType.PROPERTY.value))
        source_type = SourceType(first_metadata.get('source_type', SourceType.PROPERTY_JSON.value))
        
        # Load source data
        source_data = self._load_source_data(entity_id, entity_type, source_type, use_cache)
        if not source_data:
            logger.warning(f"No source data found for entity '{entity_id}'")
            return None
        
        # Extract embedding IDs
        embedding_ids = [meta.get('embedding_id', 'unknown') for meta in embedding_group]
        
        # Reconstruct text if multi-chunk
        chunk_groups = self.reconstructor.group_chunks_by_parent(embedding_group)
        reconstructed_text = None
        is_complete = True
        chunk_count = len(embedding_group)
        
        if len(chunk_groups) > 0:
            # Use the first chunk group (should only be one for same entity)
            chunk_group = chunk_groups[0]
            reconstructed_text = chunk_group.get_reconstructed_text()
            is_complete = chunk_group.is_complete
        
        # Collect source files
        source_files = {meta.get('source_file', '') for meta in embedding_group if meta.get('source_file')}
        source_files.discard('')  # Remove empty strings
        
        # Create enriched entity
        enriched_entity = EnrichedEntity(
            entity_id=entity_id,
            entity_type=entity_type,
            source_type=source_type,
            source_data=source_data,
            embedding_ids=embedding_ids,
            total_embeddings=len(embedding_ids),
            chunk_count=chunk_count,
            is_complete=is_complete,
            reconstructed_text=reconstructed_text,
            text_length=len(reconstructed_text) if reconstructed_text else None,
            source_files=source_files
        )
        
        logger.debug(f"Created enriched entity '{entity_id}' with {len(embedding_ids)} embeddings")
        return enriched_entity
    
    def _get_embedding_metadata(
        self,
        embedding_id: str,
        collection_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific embedding from ChromaDB."""
        
        try:
            # Use the query manager to get metadata
            results = self.query_manager.metadata_only_search(
                collection_name=collection_name,
                metadata_filter={"embedding_id": {"$eq": embedding_id}},
                limit=1
            )
            
            if results and len(results) > 0:
                return results[0]
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to get metadata for embedding '{embedding_id}': {e}")
            return None
    
    def _extract_identifier(
        self,
        metadata: Dict[str, Any],
        entity_type: EntityType
    ) -> Optional[str]:
        """Extract the appropriate identifier for correlation based on entity type."""
        
        if entity_type == EntityType.PROPERTY:
            return metadata.get('listing_id')
            
        elif entity_type == EntityType.NEIGHBORHOOD:
            return metadata.get('neighborhood_id')
            
        elif entity_type in [EntityType.WIKIPEDIA_ARTICLE, EntityType.WIKIPEDIA_SUMMARY]:
            return str(metadata.get('page_id')) if metadata.get('page_id') is not None else None
            
        else:
            # Fallback to embedding_id
            return metadata.get('embedding_id')
    
    def _load_source_data(
        self,
        identifier: str,
        entity_type: EntityType,
        source_type: SourceType,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Load source data for the given identifier and entity type."""
        
        # Check cache first
        cache_key = f"{entity_type.value}_{source_type.value}"
        if use_cache and cache_key in self._source_caches:
            cached_data = self._source_caches[cache_key].get_entity(identifier)
            if cached_data is not None:
                return cached_data
        
        # Load data based on entity type
        if entity_type == EntityType.PROPERTY:
            return self._load_property_data(identifier, use_cache, cache_key)
            
        elif entity_type == EntityType.NEIGHBORHOOD:
            return self._load_neighborhood_data(identifier, use_cache, cache_key)
            
        elif entity_type in [EntityType.WIKIPEDIA_ARTICLE, EntityType.WIKIPEDIA_SUMMARY]:
            return self._load_wikipedia_data(identifier, use_cache, cache_key)
            
        else:
            logger.warning(f"Unsupported entity type for source data loading: {entity_type}")
            return None
    
    def _load_property_data(
        self,
        listing_id: str,
        use_cache: bool,
        cache_key: str
    ) -> Optional[Dict[str, Any]]:
        """Load property data from JSON files."""
        
        # Check cache first
        if use_cache and cache_key in self._source_caches:
            cached_data = self._source_caches[cache_key].get_entity(listing_id)
            if cached_data is not None:
                return cached_data
        
        # Initialize cache if needed
        if use_cache and cache_key not in self._source_caches:
            self._source_caches[cache_key] = SourceDataCache(
                entity_type=EntityType.PROPERTY,
                source_type=SourceType.PROPERTY_JSON
            )
        
        # Load property JSON files
        property_files = [
            "real_estate_data/properties_sf.json",
            "real_estate_data/properties_pc.json"
        ]
        
        for file_path in property_files:
            full_path = os.path.join(self.data_root_path, file_path)
            
            if not os.path.exists(full_path):
                continue
            
            # Check if already loaded in cache
            if use_cache and full_path in self._source_caches[cache_key].file_paths:
                continue
                
            try:
                with open(full_path, 'r') as f:
                    properties = json.load(f)
                    
                for prop in properties:
                    prop_listing_id = prop.get('listing_id')
                    if prop_listing_id:
                        if use_cache:
                            self._source_caches[cache_key].add_entity(prop_listing_id, prop)
                        
                        # Check if this is the one we're looking for
                        if prop_listing_id == listing_id:
                            if use_cache:
                                self._source_caches[cache_key].file_paths.add(full_path)
                            return prop
                
                if use_cache:
                    self._source_caches[cache_key].file_paths.add(full_path)
                    
            except Exception as e:
                logger.error(f"Failed to load property file '{full_path}': {e}")
        
        return None
    
    def _load_neighborhood_data(
        self,
        neighborhood_id: str,
        use_cache: bool,
        cache_key: str
    ) -> Optional[Dict[str, Any]]:
        """Load neighborhood data from JSON files."""
        
        # Check cache first
        if use_cache and cache_key in self._source_caches:
            cached_data = self._source_caches[cache_key].get_entity(neighborhood_id)
            if cached_data is not None:
                return cached_data
        
        # Initialize cache if needed
        if use_cache and cache_key not in self._source_caches:
            self._source_caches[cache_key] = SourceDataCache(
                entity_type=EntityType.NEIGHBORHOOD,
                source_type=SourceType.NEIGHBORHOOD_JSON
            )
        
        # Load neighborhood JSON files
        neighborhood_files = [
            "real_estate_data/neighborhoods_sf.json",
            "real_estate_data/neighborhoods_pc.json"
        ]
        
        for file_path in neighborhood_files:
            full_path = os.path.join(self.data_root_path, file_path)
            
            if not os.path.exists(full_path):
                continue
                
            # Check if already loaded in cache
            if use_cache and full_path in self._source_caches[cache_key].file_paths:
                continue
                
            try:
                with open(full_path, 'r') as f:
                    neighborhoods = json.load(f)
                    
                for neighborhood in neighborhoods:
                    neighborhood_id_val = neighborhood.get('neighborhood_id')
                    if neighborhood_id_val:
                        if use_cache:
                            self._source_caches[cache_key].add_entity(neighborhood_id_val, neighborhood)
                        
                        # Check if this is the one we're looking for
                        if neighborhood_id_val == neighborhood_id:
                            if use_cache:
                                self._source_caches[cache_key].file_paths.add(full_path)
                            return neighborhood
                
                if use_cache:
                    self._source_caches[cache_key].file_paths.add(full_path)
                    
            except Exception as e:
                logger.error(f"Failed to load neighborhood file '{full_path}': {e}")
        
        return None
    
    def _load_wikipedia_data(
        self,
        page_id: str,
        use_cache: bool,
        cache_key: str
    ) -> Optional[Dict[str, Any]]:
        """Load Wikipedia data from SQLite database."""
        
        # Convert page_id to integer
        try:
            page_id_int = int(page_id)
        except ValueError:
            logger.error(f"Invalid page_id for Wikipedia data: {page_id}")
            return None
        
        # Check cache first
        if use_cache and cache_key in self._source_caches:
            cached_data = self._source_caches[cache_key].get_entity(page_id)
            if cached_data is not None:
                return cached_data
        
        # Initialize cache if needed
        if use_cache and cache_key not in self._source_caches:
            self._source_caches[cache_key] = SourceDataCache(
                entity_type=EntityType.WIKIPEDIA_ARTICLE,
                source_type=SourceType.WIKIPEDIA_DB
            )
        
        # Load from Wikipedia database
        db_path = os.path.join(self.data_root_path, "data/wikipedia/wikipedia.db")
        
        if not os.path.exists(db_path):
            logger.error(f"Wikipedia database not found: {db_path}")
            return None
        
        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Query for article data
                cursor = conn.execute("""
                    SELECT a.*, ps.summary, ps.key_topics, ps.best_city, ps.best_state, ps.overall_confidence
                    FROM articles a
                    LEFT JOIN page_summaries ps ON a.page_id = ps.page_id
                    WHERE a.page_id = ?
                """, (page_id_int,))
                
                row = cursor.fetchone()
                
                if row:
                    # Convert row to dictionary
                    article_data = dict(row)
                    
                    if use_cache:
                        self._source_caches[cache_key].add_entity(page_id, article_data)
                    
                    return article_data
                else:
                    logger.warning(f"Wikipedia article not found for page_id: {page_id}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to load Wikipedia data for page_id {page_id}: {e}")
            return None
    
    def clear_caches(self) -> None:
        """Clear all source data caches."""
        self._source_caches.clear()
        logger.info("Cleared all source data caches")
    
    def get_cache_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all source data caches."""
        
        stats = {}
        for cache_key, cache in self._source_caches.items():
            stats[cache_key] = {
                'total_entities': cache.total_entities,
                'cache_hits': cache.cache_hits,
                'cache_misses': cache.cache_misses,
                'hit_rate': cache.hit_rate,
                'files_loaded': len(cache.file_paths),
                'created_at': cache.created_at.isoformat(),
                'last_accessed': cache.last_accessed.isoformat()
            }
        
        return stats