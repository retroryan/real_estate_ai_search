"""
Advanced query manager for ChromaDB with sophisticated search capabilities.

Implements query patterns from existing modules with enhanced features.
"""

from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime

from .enhanced_chromadb import EnhancedChromaDBManager
from ..models import (
    ChromaDBConfig,
    EntityType,
    SourceType,
    CorrelationMapping,
    StorageError,
)
from ..utils.logging import get_logger, PerformanceLogger


logger = get_logger(__name__)


class QueryManager:
    """
    Advanced query manager with similarity search and metadata filtering.
    
    Provides sophisticated query capabilities building on existing patterns.
    """
    
    def __init__(self, config: ChromaDBConfig):
        """
        Initialize query manager.
        
        Args:
            config: ChromaDB configuration
        """
        self.config = config
        self.manager = EnhancedChromaDBManager(config)
        self.store = self.manager.store
        
        logger.info("Initialized advanced query manager")
    
    def similarity_search(
        self,
        query_text: str,
        collection_name: str,
        top_k: int = 5,
        min_similarity: float = 0.0,
        metadata_filter: Optional[Dict[str, Any]] = None,
        include_embeddings: bool = False
    ) -> Dict[str, Any]:
        """
        Perform similarity search with metadata filtering.
        
        Args:
            query_text: Text to search for
            collection_name: Collection to search in
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold
            metadata_filter: ChromaDB where clause for filtering
            include_embeddings: Whether to include embedding vectors
            
        Returns:
            Dictionary with search results and metadata
        """
        logger.info(f"Similarity search in '{collection_name}' for: '{query_text[:50]}...'")
        
        try:
            with PerformanceLogger(f"Similarity search (k={top_k})") as perf:
                # Switch to collection
                self.store.create_collection(collection_name, {}, False)
                
                # Perform search
                results = self.store.query(
                    query_texts=[query_text],
                    n_results=top_k,
                    where=metadata_filter,
                    include=['documents', 'metadatas', 'distances'] + 
                           (['embeddings'] if include_embeddings else [])
                )
                
                # Filter by minimum similarity if specified
                if min_similarity > 0.0:
                    results = self._filter_by_similarity(results, min_similarity)
                
                # Enrich results with correlation information
                enriched_results = self._enrich_search_results(results, collection_name)
                
                perf.add_metric("results_count", len(enriched_results.get('ids', [])))
                
                logger.info(f"Found {len(enriched_results.get('ids', []))} results")
                return enriched_results
                
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            raise StorageError(f"Search failed: {e}")
    
    def multi_collection_search(
        self,
        query_text: str,
        collection_names: List[str],
        top_k_per_collection: int = 3,
        min_similarity: float = 0.0,
        entity_type_filter: Optional[List[EntityType]] = None
    ) -> Dict[str, Any]:
        """
        Search across multiple collections and aggregate results.
        
        Args:
            query_text: Text to search for
            collection_names: List of collections to search
            top_k_per_collection: Results per collection
            min_similarity: Minimum similarity threshold
            entity_type_filter: Filter by entity types
            
        Returns:
            Dictionary with aggregated search results
        """
        logger.info(f"Multi-collection search across {len(collection_names)} collections")
        
        aggregated_results = {
            'query': query_text,
            'collections_searched': [],
            'total_results': 0,
            'results_by_collection': {},
            'combined_results': {
                'ids': [],
                'documents': [],
                'metadatas': [],
                'distances': [],
                'collections': []  # Track which collection each result came from
            }
        }
        
        # Build metadata filter for entity types
        metadata_filter = None
        if entity_type_filter:
            entity_values = [et.value for et in entity_type_filter]
            if len(entity_values) == 1:
                metadata_filter = {"entity_type": {"$eq": entity_values[0]}}
            else:
                metadata_filter = {"entity_type": {"$in": entity_values}}
        
        try:
            for collection_name in collection_names:
                try:
                    # Search in this collection
                    results = self.similarity_search(
                        query_text=query_text,
                        collection_name=collection_name,
                        top_k=top_k_per_collection,
                        min_similarity=min_similarity,
                        metadata_filter=metadata_filter,
                        include_embeddings=False
                    )
                    
                    # Add to aggregated results
                    if results.get('ids'):
                        aggregated_results['collections_searched'].append(collection_name)
                        aggregated_results['results_by_collection'][collection_name] = results
                        
                        # Combine results
                        for i, result_id in enumerate(results['ids']):
                            aggregated_results['combined_results']['ids'].append(result_id)
                            aggregated_results['combined_results']['documents'].append(
                                results['documents'][i] if i < len(results.get('documents', [])) else ''
                            )
                            aggregated_results['combined_results']['metadatas'].append(
                                results['metadatas'][i] if i < len(results.get('metadatas', [])) else {}
                            )
                            aggregated_results['combined_results']['distances'].append(
                                results['distances'][i] if i < len(results.get('distances', [])) else 1.0
                            )
                            aggregated_results['combined_results']['collections'].append(collection_name)
                    
                except Exception as e:
                    logger.warning(f"Search failed in collection '{collection_name}': {e}")
                    continue
            
            # Sort combined results by distance (similarity)
            if aggregated_results['combined_results']['ids']:
                combined_data = list(zip(
                    aggregated_results['combined_results']['ids'],
                    aggregated_results['combined_results']['documents'],
                    aggregated_results['combined_results']['metadatas'],
                    aggregated_results['combined_results']['distances'],
                    aggregated_results['combined_results']['collections']
                ))
                
                # Sort by distance (lower = more similar)
                combined_data.sort(key=lambda x: x[3])
                
                # Unpack sorted data
                (aggregated_results['combined_results']['ids'],
                 aggregated_results['combined_results']['documents'],
                 aggregated_results['combined_results']['metadatas'],
                 aggregated_results['combined_results']['distances'],
                 aggregated_results['combined_results']['collections']) = zip(*combined_data)
                
                aggregated_results['combined_results']['ids'] = list(aggregated_results['combined_results']['ids'])
                aggregated_results['combined_results']['documents'] = list(aggregated_results['combined_results']['documents'])
                aggregated_results['combined_results']['metadatas'] = list(aggregated_results['combined_results']['metadatas'])
                aggregated_results['combined_results']['distances'] = list(aggregated_results['combined_results']['distances'])
                aggregated_results['combined_results']['collections'] = list(aggregated_results['combined_results']['collections'])
            
            aggregated_results['total_results'] = len(aggregated_results['combined_results']['ids'])
            
            logger.info(f"Multi-collection search found {aggregated_results['total_results']} total results")
            return aggregated_results
            
        except Exception as e:
            logger.error(f"Multi-collection search failed: {e}")
            raise StorageError(f"Multi-collection search failed: {e}")
    
    def metadata_only_search(
        self,
        collection_name: str,
        metadata_filter: Dict[str, Any],
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for metadata only without embeddings or text.
        
        Args:
            collection_name: Collection to search
            metadata_filter: ChromaDB where clause
            limit: Maximum results to return
            
        Returns:
            List of metadata dictionaries
        """
        logger.info(f"Metadata-only search in '{collection_name}'")
        
        try:
            # Switch to collection
            self.store.create_collection(collection_name, {}, False)
            
            # Get all data but filter on metadata
            results = self.store.get_all(
                where=metadata_filter,
                limit=limit,
                include_embeddings=False
            )
            
            metadatas = results.get('metadatas', [])
            logger.info(f"Found {len(metadatas)} metadata records")
            
            return metadatas
            
        except Exception as e:
            logger.error(f"Metadata search failed: {e}")
            raise StorageError(f"Metadata search failed: {e}")
    
    def aggregation_query(
        self,
        collection_name: str,
        group_by: str,
        aggregation_type: str = "count"
    ) -> Dict[str, Any]:
        """
        Perform aggregation queries on metadata.
        
        Args:
            collection_name: Collection to analyze
            group_by: Field to group by
            aggregation_type: Type of aggregation (count, unique)
            
        Returns:
            Dictionary with aggregation results
        """
        logger.info(f"Aggregation query on '{collection_name}' grouped by '{group_by}'")
        
        try:
            # Get all metadata
            self.store.create_collection(collection_name, {}, False)
            results = self.store.get_all(include_embeddings=False)
            
            metadatas = results.get('metadatas', [])
            
            # Perform aggregation
            if aggregation_type == "count":
                aggregation_results = self._count_aggregation(metadatas, group_by)
            elif aggregation_type == "unique":
                aggregation_results = self._unique_aggregation(metadatas, group_by)
            else:
                raise ValueError(f"Unsupported aggregation type: {aggregation_type}")
            
            logger.info(f"Aggregation completed with {len(aggregation_results)} groups")
            
            return {
                'collection': collection_name,
                'group_by': group_by,
                'aggregation_type': aggregation_type,
                'total_records': len(metadatas),
                'results': aggregation_results,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Aggregation query failed: {e}")
            raise StorageError(f"Aggregation failed: {e}")
    
    def find_related_chunks(
        self,
        embedding_id: str,
        collection_name: str
    ) -> List[Dict[str, Any]]:
        """
        Find all chunks related to the same parent document.
        
        Args:
            embedding_id: ID of the reference embedding
            collection_name: Collection to search
            
        Returns:
            List of related chunk metadata
        """
        logger.info(f"Finding related chunks for embedding '{embedding_id}'")
        
        try:
            # Get the reference embedding's metadata
            self.store.create_collection(collection_name, {}, False)
            
            # First get all data to find the reference
            all_data = self.store.get_all(include_embeddings=False)
            metadatas = all_data.get('metadatas', [])
            ids = all_data.get('ids', [])
            
            # Find the reference embedding
            reference_meta = None
            for i, meta_id in enumerate(ids):
                if meta_id == embedding_id and i < len(metadatas):
                    reference_meta = metadatas[i]
                    break
            
            if not reference_meta:
                logger.warning(f"Embedding '{embedding_id}' not found in collection")
                return []
            
            # Get parent identifier
            parent_id = (
                reference_meta.get('parent_hash') or
                reference_meta.get('source_doc_id') or
                embedding_id
            )
            
            # Find all chunks with the same parent
            related_chunks = []
            for i, metadata in enumerate(metadatas):
                if not metadata:
                    continue
                
                chunk_parent = (
                    metadata.get('parent_hash') or
                    metadata.get('source_doc_id') or
                    ids[i] if i < len(ids) else 'unknown'
                )
                
                if chunk_parent == parent_id:
                    chunk_data = metadata.copy()
                    chunk_data['embedding_id'] = ids[i] if i < len(ids) else 'unknown'
                    related_chunks.append(chunk_data)
            
            # Sort by chunk index if available
            related_chunks.sort(key=lambda c: c.get('chunk_index', 0))
            
            logger.info(f"Found {len(related_chunks)} related chunks")
            return related_chunks
            
        except Exception as e:
            logger.error(f"Related chunks search failed: {e}")
            raise StorageError(f"Related chunks search failed: {e}")
    
    def _filter_by_similarity(
        self,
        results: Dict[str, Any],
        min_similarity: float
    ) -> Dict[str, Any]:
        """Filter search results by minimum similarity threshold."""
        
        distances = results.get('distances', [[]])
        if not distances or not distances[0]:
            return results
        
        # Convert distances to similarities (1 - distance)
        similarities = [1.0 - d for d in distances[0]]
        
        # Find indices that meet threshold
        valid_indices = [i for i, sim in enumerate(similarities) if sim >= min_similarity]
        
        # Filter all result arrays
        filtered_results = {}
        for key, values in results.items():
            if key == 'distances':
                filtered_results[key] = [[distances[0][i] for i in valid_indices]]
            elif isinstance(values, list) and len(values) > 0 and isinstance(values[0], list):
                filtered_results[key] = [[values[0][i] for i in valid_indices]]
            else:
                filtered_results[key] = values
        
        return filtered_results
    
    def _enrich_search_results(
        self,
        results: Dict[str, Any],
        collection_name: str
    ) -> Dict[str, Any]:
        """Enrich search results with additional correlation information."""
        
        # Add collection name to results
        enriched = results.copy()
        enriched['collection_name'] = collection_name
        enriched['search_timestamp'] = datetime.now().isoformat()
        
        # Add similarity scores (1 - distance)
        if 'distances' in results and results['distances']:
            distances = results['distances'][0] if results['distances'] else []
            enriched['similarities'] = [1.0 - d for d in distances]
        
        # Add entity type distribution
        if 'metadatas' in results and results['metadatas']:
            metadatas = results['metadatas'][0] if results['metadatas'] else []
            entity_types = [meta.get('entity_type', 'unknown') for meta in metadatas if meta]
            entity_distribution = {}
            for et in entity_types:
                entity_distribution[et] = entity_distribution.get(et, 0) + 1
            enriched['entity_distribution'] = entity_distribution
        
        return enriched
    
    def _count_aggregation(self, metadatas: List[Dict[str, Any]], group_by: str) -> Dict[str, int]:
        """Perform count aggregation on metadata field."""
        
        counts = {}
        for metadata in metadatas:
            if not metadata:
                continue
                
            value = metadata.get(group_by, 'unknown')
            # Handle nested values
            if isinstance(value, (list, tuple)):
                value = str(value)
            elif value is None:
                value = 'null'
            else:
                value = str(value)
                
            counts[value] = counts.get(value, 0) + 1
        
        return counts
    
    def _unique_aggregation(self, metadatas: List[Dict[str, Any]], group_by: str) -> Dict[str, List[str]]:
        """Perform unique values aggregation on metadata field."""
        
        unique_values = {}
        for metadata in metadatas:
            if not metadata:
                continue
                
            group_value = metadata.get(group_by, 'unknown')
            group_key = str(group_value) if group_value is not None else 'null'
            
            # Collect unique values from all other fields
            if group_key not in unique_values:
                unique_values[group_key] = set()
            
            for key, value in metadata.items():
                if key != group_by and value is not None:
                    unique_values[group_key].add(str(value))
        
        # Convert sets to lists for JSON serialization
        return {k: list(v) for k, v in unique_values.items()}