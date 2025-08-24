"""
Correlation service for matching embeddings with source data.

Provides methods to correlate data from loaders with embeddings from ChromaDB,
using metadata identifiers (listing_id, neighborhood_id, page_id) for matching.
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

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
        collection_name: str,
        include_vectors: bool = False
    ) -> List[EnrichedProperty]:
        """
        Correlate properties with their embeddings from ChromaDB.
        
        Directly populates embedding fields on the property models.
        
        Args:
            properties: List of properties to correlate
            collection_name: ChromaDB collection to retrieve embeddings from
            include_vectors: Whether to include embedding vectors
            
        Returns:
            List of EnrichedProperty objects with populated embedding fields
        """
        logger.info(f"Correlating {len(properties)} properties with collection '{collection_name}'")
        
        if not properties:
            return []
        
        # Extract listing IDs for bulk retrieval
        listing_ids = [prop.listing_id for prop in properties]
        
        # Bulk retrieve embeddings from ChromaDB
        embeddings_map = self.embedding_service.get_embeddings_by_ids(
            collection_name=collection_name,
            entity_ids=listing_ids,
            include_vectors=include_vectors
        )
        
        # Populate embedding fields on each property
        successful_correlations = 0
        for prop in properties:
            embeddings = embeddings_map.get(prop.listing_id, [])
            
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
        collection_name: str,
        include_vectors: bool = False
    ) -> List[EnrichedNeighborhood]:
        """
        Correlate neighborhoods with their embeddings from ChromaDB.
        
        Directly populates embedding fields on the neighborhood models.
        
        Args:
            neighborhoods: List of neighborhoods to correlate
            collection_name: ChromaDB collection to retrieve embeddings from
            include_vectors: Whether to include embedding vectors
            
        Returns:
            List of EnrichedNeighborhood objects with populated embedding fields
        """
        logger.info(f"Correlating {len(neighborhoods)} neighborhoods with collection '{collection_name}'")
        
        if not neighborhoods:
            return []
        
        # Extract neighborhood IDs for bulk retrieval
        neighborhood_ids = [n.neighborhood_id for n in neighborhoods]
        
        # Bulk retrieve embeddings from ChromaDB
        embeddings_map = self.embedding_service.get_embeddings_by_ids(
            collection_name=collection_name,
            entity_ids=neighborhood_ids,
            include_vectors=include_vectors
        )
        
        # Populate embedding fields on each neighborhood
        successful_correlations = 0
        for neighborhood in neighborhoods:
            embeddings = embeddings_map.get(neighborhood.neighborhood_id, [])
            
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
        collection_name: str,
        include_vectors: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Correlate Wikipedia articles with their embeddings from ChromaDB.
        
        Handles multi-chunk documents by grouping embeddings by page_id.
        
        Args:
            wikipedia_data: List of Wikipedia article dictionaries
            collection_name: ChromaDB collection to retrieve embeddings from
            include_vectors: Whether to include embedding vectors
            
        Returns:
            List of dictionaries with correlated data and embedding fields
        """
        logger.info(f"Correlating {len(wikipedia_data)} Wikipedia articles with collection '{collection_name}'")
        
        if not wikipedia_data:
            return []
        
        # Extract page IDs for bulk retrieval (convert to string for ChromaDB)
        page_ids = [str(article.get('page_id', '')) for article in wikipedia_data if article.get('page_id')]
        
        # Bulk retrieve embeddings from ChromaDB
        embeddings_map = self.embedding_service.get_embeddings_by_ids(
            collection_name=collection_name,
            entity_ids=page_ids,
            include_vectors=include_vectors
        )
        
        # Correlate each article with its embeddings
        results = []
        for article in wikipedia_data:
            page_id = str(article.get('page_id', ''))
            if not page_id:
                logger.warning(f"Wikipedia article missing page_id: {article.get('title', 'Unknown')}")
                continue
            
            embeddings = embeddings_map.get(page_id, [])
            
            # Sort multi-chunk embeddings by chunk_index
            if embeddings:
                embeddings.sort(key=lambda e: e.chunk_index or 0)
            
            # Create result dictionary combining source data with embedding fields
            result = dict(article)  # Copy all original fields
            result.update({
                'embeddings': [embedding.__dict__ for embedding in embeddings] if embeddings else None,
                'has_embeddings': len(embeddings) > 0,
                'embedding_count': len(embeddings),
                'correlation_confidence': 1.0 if embeddings else 0.0
            })
            results.append(result)
        
        successful_correlations = sum(1 for r in results if r['has_embeddings'])
        logger.info(f"Successfully correlated {successful_correlations}/{len(results)} Wikipedia articles")
        
        # Log multi-chunk statistics
        multi_chunk_articles = sum(1 for r in results if r['embedding_count'] > 1)
        if multi_chunk_articles:
            logger.info(f"Found {multi_chunk_articles} articles with multiple chunks")
        
        return results
    
