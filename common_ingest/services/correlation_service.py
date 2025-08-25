"""
Correlation service for matching embeddings with source data.

Provides methods to correlate data from loaders with embeddings from ChromaDB,
using metadata identifiers (listing_id, neighborhood_id, page_id) for matching.
"""

import logging
from typing import List, Dict, Optional, Any

from property_finder_models import EnrichedProperty, EnrichedNeighborhood, EmbeddingData

from .embedding_service import EmbeddingService
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class CorrelationService:
    """
    Service for correlating source data with embeddings from ChromaDB.
    
    Matches data to embeddings using metadata identifiers and returns
    enriched data with correlated embeddings.
    """
    
    def __init__(self, embedding_service: EmbeddingService):
        """
        Initialize correlation service with embedding service dependency.
        
        Args:
            embedding_service: Service for retrieving embeddings from ChromaDB
        """
        self.embedding_service = embedding_service
        logger.info("Initialized CorrelationService")
    
    def correlate_properties_with_embeddings(
        self,
        properties: List[EnrichedProperty],
        collection_name: Optional[str] = None,
        include_vectors: bool = False
    ) -> List[EnrichedProperty]:
        """
        Correlate properties with their embeddings using fast bulk-loaded lookup.
        
        Uses O(1) in-memory lookup from pre-loaded embeddings map.
        
        Args:
            properties: List of properties to correlate
            collection_name: Optional ChromaDB collection name (auto-discovers if not provided)
            include_vectors: Whether to include embedding vectors
            
        Returns:
            List of EnrichedProperty objects with populated embedding fields
        """
        if not properties:
            return []
        
        logger.info(f"Correlating {len(properties)} properties")
        
        # Bulk load all property embeddings (uses cache after first load)
        embeddings_map = self.embedding_service.bulk_load_property_embeddings(
            collection_name=collection_name
        )
        
        if not embeddings_map:
            logger.warning("No property embeddings available for correlation")
            # Return properties without embeddings
            for prop in properties:
                prop.embeddings = None
                prop.embedding_count = 0
                prop.has_embeddings = False
                prop.correlation_confidence = 0.0
            return properties
        
        # Fast O(1) correlation using in-memory lookup
        successful_correlations = 0
        for prop in properties:
            # Direct dictionary lookup - no database query needed!
            embeddings = embeddings_map.get(prop.listing_id, [])
            
            # Filter out vectors if not requested
            if not include_vectors and embeddings:
                for emb in embeddings:
                    emb.vector = None
            
            # Directly populate the embedding fields
            prop.embeddings = embeddings if embeddings else None
            prop.embedding_count = len(embeddings)
            prop.has_embeddings = len(embeddings) > 0
            prop.correlation_confidence = 1.0 if embeddings else 0.0
            
            if prop.has_embeddings:
                successful_correlations += 1
        
        logger.info(f"Successfully correlated {successful_correlations}/{len(properties)} properties")
        
        return properties
    
    def correlate_neighborhoods_with_embeddings(
        self,
        neighborhoods: List[EnrichedNeighborhood],
        collection_name: Optional[str] = None,
        include_vectors: bool = False
    ) -> List[EnrichedNeighborhood]:
        """
        Correlate neighborhoods with their embeddings using fast bulk-loaded lookup.
        
        Uses O(1) in-memory lookup from pre-loaded embeddings map.
        
        Args:
            neighborhoods: List of neighborhoods to correlate
            collection_name: Optional ChromaDB collection name (auto-discovers if not provided)
            include_vectors: Whether to include embedding vectors
            
        Returns:
            List of EnrichedNeighborhood objects with populated embedding fields
        """
        if not neighborhoods:
            return []
        
        logger.info(f"Correlating {len(neighborhoods)} neighborhoods")
        
        # Bulk load all neighborhood embeddings (uses cache after first load)
        embeddings_map = self.embedding_service.bulk_load_neighborhood_embeddings(
            collection_name=collection_name
        )
        
        if not embeddings_map:
            logger.warning("No neighborhood embeddings available for correlation")
            # Return neighborhoods without embeddings
            for neighborhood in neighborhoods:
                neighborhood.embeddings = None
                neighborhood.embedding_count = 0
                neighborhood.has_embeddings = False
                neighborhood.correlation_confidence = 0.0
            return neighborhoods
        
        # Fast O(1) correlation using in-memory lookup
        successful_correlations = 0
        for neighborhood in neighborhoods:
            # Direct dictionary lookup - no database query needed!
            embeddings = embeddings_map.get(neighborhood.neighborhood_id, [])
            
            # Filter out vectors if not requested
            if not include_vectors and embeddings:
                for emb in embeddings:
                    emb.vector = None
            
            # Directly populate the embedding fields
            neighborhood.embeddings = embeddings if embeddings else None
            neighborhood.embedding_count = len(embeddings)
            neighborhood.has_embeddings = len(embeddings) > 0
            neighborhood.correlation_confidence = 1.0 if embeddings else 0.0
            
            if neighborhood.has_embeddings:
                successful_correlations += 1
        
        logger.info(f"Successfully correlated {successful_correlations}/{len(neighborhoods)} neighborhoods")
        
        return neighborhoods
    
    def correlate_wikipedia_with_embeddings(
        self,
        wikipedia_data: List[Dict[str, Any]],
        collection_name: Optional[str] = None,
        include_vectors: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Correlate Wikipedia articles with their embeddings using fast bulk-loaded lookup.
        
        Uses O(1) in-memory lookup with proper multi-chunk handling.
        Chunks are automatically sorted by chunk_index (flat field).
        
        Args:
            wikipedia_data: List of Wikipedia article dictionaries
            collection_name: Optional ChromaDB collection name (auto-discovers if not provided)
            include_vectors: Whether to include embedding vectors
            
        Returns:
            List of dictionaries with correlated data and embedding fields
        """
        if not wikipedia_data:
            return []
        
        logger.info(f"Correlating {len(wikipedia_data)} Wikipedia articles")
        
        # Bulk load all Wikipedia embeddings (uses cache after first load)
        embeddings_map = self.embedding_service.bulk_load_wikipedia_embeddings(
            collection_name=collection_name
        )
        
        if not embeddings_map:
            logger.warning("No Wikipedia embeddings available for correlation")
            # Return articles without embeddings
            results = []
            for article in wikipedia_data:
                result = dict(article)
                result.update({
                    'embeddings': None,
                    'has_embeddings': False,
                    'embedding_count': 0,
                    'correlation_confidence': 0.0
                })
                results.append(result)
            return results
        
        # Fast O(1) correlation using in-memory lookup
        results = []
        successful_correlations = 0
        
        for article in wikipedia_data:
            page_id = article.get('page_id')
            if page_id is None:
                logger.warning(f"Wikipedia article missing page_id: {article.get('title', 'Unknown')}")
                result = dict(article)
                result.update({
                    'embeddings': None,
                    'has_embeddings': False,
                    'embedding_count': 0,
                    'correlation_confidence': 0.0
                })
                results.append(result)
                continue
            
            # Ensure page_id is int for lookup
            try:
                page_id = int(page_id)
            except (ValueError, TypeError):
                logger.warning(f"Invalid page_id: {page_id}")
                result = dict(article)
                result.update({
                    'embeddings': None,
                    'has_embeddings': False,
                    'embedding_count': 0,
                    'correlation_confidence': 0.0
                })
                results.append(result)
                continue
            
            # Direct dictionary lookup - no database query needed!
            # Embeddings are already sorted by chunk_index from bulk load
            embeddings = embeddings_map.get(page_id, [])
            
            # Filter out vectors if not requested
            if not include_vectors and embeddings:
                for emb in embeddings:
                    emb.vector = None
            
            # Create result dictionary combining source data with embedding fields
            result = dict(article)  # Copy all original fields
            result.update({
                'embeddings': [embedding.__dict__ for embedding in embeddings] if embeddings else None,
                'has_embeddings': len(embeddings) > 0,
                'embedding_count': len(embeddings),
                'correlation_confidence': 1.0 if embeddings else 0.0
            })
            results.append(result)
            
            if embeddings:
                successful_correlations += 1
        
        logger.info(f"Successfully correlated {successful_correlations}/{len(results)} Wikipedia articles")
        
        # Log multi-chunk statistics
        multi_chunk_articles = sum(1 for r in results if r['embedding_count'] > 1)
        if multi_chunk_articles:
            logger.info(f"Found {multi_chunk_articles} articles with multiple chunks")
        
        return results
    
