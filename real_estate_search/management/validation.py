"""
Validation module for checking index integrity and embeddings.
"""

import logging
from typing import List, Dict, Tuple
from elasticsearch import Elasticsearch

from ..indexer.enums import IndexName
from ..infrastructure.elasticsearch_client import ElasticsearchClient
from .models import ValidationStatus, EmbeddingValidationResult
from .index_operations import IndexOperations


class ValidationService:
    """Service for validating indices and embeddings."""
    
    def __init__(self, es_client: ElasticsearchClient, index_operations: IndexOperations):
        """
        Initialize validation service.
        
        Args:
            es_client: Enhanced Elasticsearch client
            index_operations: Index operations handler
        """
        self.es_client = es_client
        self.index_operations = index_operations
        self.logger = logging.getLogger(__name__)
    
    def validate_indices(self) -> Tuple[bool, List[ValidationStatus]]:
        """
        Validate that all indices exist with correct mappings.
        
        Returns:
            Tuple of (all_valid, list of validation statuses)
        """
        self.logger.info("Validating Elasticsearch indices...")
        
        try:
            statuses = self.index_operations.list_indices()
            
            all_valid = all(
                status.exists and status.mapping_valid 
                for status in statuses
            )
            
            if all_valid:
                self.logger.info("All indices validation passed")
            else:
                self.logger.warning("Some indices failed validation")
            
            return all_valid, statuses
            
        except Exception as e:
            self.logger.error(f"Failed to validate indices: {str(e)}")
            raise
    
    def validate_embeddings(self) -> Tuple[bool, List[EmbeddingValidationResult], float]:
        """
        Validate that embeddings have been properly generated.
        
        Returns:
            Tuple of (overall_valid, results, overall_percentage)
        """
        self.logger.info("Validating vector embeddings across all entity types...")
        
        entity_indices = {
            "properties": IndexName.PROPERTIES,
            "neighborhoods": IndexName.NEIGHBORHOODS,
            "wikipedia": IndexName.WIKIPEDIA
        }
        
        results = []
        total_docs = 0
        total_with_embeddings = 0
        overall_valid = True
        
        for entity_type, index_name in entity_indices.items():
            result = self._validate_entity_embeddings(entity_type, index_name)
            results.append(result)
            
            total_docs += result.total_docs
            total_with_embeddings += result.docs_with_embeddings
            
            if result.percentage < 80:
                overall_valid = False
        
        overall_percentage = (total_with_embeddings / total_docs * 100) if total_docs > 0 else 0
        
        if overall_percentage < 95:
            overall_valid = False
        
        return overall_valid, results, overall_percentage
    
    def _validate_entity_embeddings(self, entity_type: str, index_name: str) -> EmbeddingValidationResult:
        """
        Validate embeddings for a specific entity type.
        
        Args:
            entity_type: Type of entity
            index_name: Name of the index
            
        Returns:
            Embedding validation result
        """
        try:
            # Check if index exists
            if not self.es_client.client.indices.exists(index=index_name):
                return EmbeddingValidationResult(
                    entity_type=entity_type,
                    index_name=index_name,
                    total_docs=0,
                    docs_with_embeddings=0,
                    percentage=0.0,
                    status="✗"
                )
            
            # Get total document count
            total_count_result = self.es_client.client.count(index=index_name)
            total_count = total_count_result['count']
            
            # Count documents with embeddings
            embedding_count = self._count_documents_with_embeddings(index_name)
            
            # Calculate percentage
            percentage = (embedding_count / total_count * 100) if total_count > 0 else 0
            
            # Get sample embedding metadata
            dimension, model = self._get_embedding_metadata(index_name)
            
            # Determine status
            if percentage >= 95:
                status = "✓"
            elif percentage >= 80:
                status = "⚠"
            else:
                status = "✗"
            
            return EmbeddingValidationResult(
                entity_type=entity_type,
                index_name=index_name,
                total_docs=total_count,
                docs_with_embeddings=embedding_count,
                percentage=percentage,
                embedding_dimension=dimension,
                embedding_model=model,
                status=status
            )
            
        except Exception as e:
            self.logger.error(f"Error validating embeddings for {entity_type}: {e}")
            return EmbeddingValidationResult(
                entity_type=entity_type,
                index_name=index_name,
                total_docs=0,
                docs_with_embeddings=0,
                percentage=0.0,
                status="✗"
            )
    
    def _count_documents_with_embeddings(self, index_name: str) -> int:
        """
        Count documents that have embedding fields.
        
        Args:
            index_name: Name of the index
            
        Returns:
            Count of documents with embeddings
        """
        embedding_query = {
            "query": {
                "bool": {
                    "must": [
                        {"exists": {"field": "embedding"}},
                        {"exists": {"field": "embedding_model"}},
                        {"exists": {"field": "embedding_dimension"}}
                    ]
                }
            }
        }
        
        result = self.es_client.client.count(
            index=index_name,
            body=embedding_query
        )
        return result['count']
    
    def _get_embedding_metadata(self, index_name: str) -> Tuple[int, str]:
        """
        Get embedding dimension and model from a sample document.
        
        Args:
            index_name: Name of the index
            
        Returns:
            Tuple of (dimension, model)
        """
        sample_query = {
            "query": {
                "bool": {
                    "must": [{"exists": {"field": "embedding"}}]
                }
            },
            "size": 1,
            "_source": ["embedding_dimension", "embedding_model"]
        }
        
        result = self.es_client.client.search(
            index=index_name,
            body=sample_query
        )
        
        if result['hits']['hits']:
            hit = result['hits']['hits'][0]['_source']
            dimension = hit.get('embedding_dimension')
            model = hit.get('embedding_model')
            return dimension, model
        
        return None, None