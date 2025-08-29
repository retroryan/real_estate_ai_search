"""Wikipedia-specific writer strategy."""

from typing import Dict, Any, Optional
import pandas as pd

from squack_pipeline.writers.strategies.base_writer_strategy import (
    BaseWriterStrategy, WriterConfig
)
from squack_pipeline.models import EntityType
from squack_pipeline.config.entity_config import EntityConfig


class WikipediaWriterStrategy(BaseWriterStrategy):
    """Writer strategy for Wikipedia entities.
    
    Handles Wikipedia-specific transformations including:
    - Managing article chunks and full articles
    - Processing sections and references
    - Handling categories and keywords
    - Optimizing content for search and retrieval
    """
    
    def __init__(self, config: Optional[WriterConfig] = None):
        """Initialize Wikipedia writer strategy.
        
        Args:
            config: Optional writer configuration
        """
        if config is None:
            config = WriterConfig(
                entity_type=EntityType.WIKIPEDIA,
                flatten_nested=False,  # Keep structure for rich content
                include_metadata=True
            )
        super().__init__(config)
    
    def prepare_for_output(
        self,
        data: pd.DataFrame,
        entity_config: Optional[EntityConfig] = None
    ) -> pd.DataFrame:
        """Prepare Wikipedia data for output format.
        
        Args:
            data: Wikipedia DataFrame to prepare
            entity_config: Optional entity-specific configuration
            
        Returns:
            Prepared DataFrame
        """
        # Make a copy to avoid modifying original
        prepared = data.copy()
        
        # Handle format-specific transformations
        if self.config.output_format == "elasticsearch":
            prepared = self._prepare_for_elasticsearch(prepared)
        elif self.config.output_format == "csv":
            prepared = self._prepare_for_csv(prepared)
        elif self.config.output_format == "parquet":
            prepared = self._prepare_for_parquet(prepared)
        
        # Apply common transformations
        if self.config.flatten_nested:
            prepared = self.flatten_nested_structures(prepared)
        
        # Apply field mappings
        prepared = self.apply_field_mappings(prepared)
        
        # Exclude unwanted fields
        prepared = self.exclude_fields(prepared)
        
        # Add metadata
        if self.config.include_metadata:
            prepared = self.add_metadata(prepared)
        
        # Validate
        if not self.validate_output(prepared):
            self.logger.warning("Output validation failed")
        
        return prepared
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single Wikipedia record for output.
        
        Args:
            record: Wikipedia record to transform
            
        Returns:
            Transformed record
        """
        transformed = record.copy()
        
        # Handle chunked vs full articles
        is_chunk = "chunk_index" in transformed
        
        if is_chunk:
            # Process chunk-specific fields
            transformed["is_chunk"] = True
            transformed["document_id"] = f"wiki_{transformed.get('page_id')}_chunk_{transformed.get('chunk_index')}"
            
            # Ensure parent reference
            if "parent_page_id" not in transformed:
                transformed["parent_page_id"] = transformed.get("page_id")
        else:
            # Process full article
            transformed["is_chunk"] = False
            transformed["document_id"] = f"wiki_{transformed.get('page_id')}"
            
            # Truncate content for certain formats
            if self.config.output_format == "csv" and "content" in transformed:
                max_length = 5000
                if len(transformed["content"]) > max_length:
                    transformed["content"] = transformed["content"][:max_length] + "..."
                    transformed["content_truncated"] = True
        
        # Handle sections array
        if "sections" in transformed and isinstance(transformed["sections"], list):
            if self.config.output_format == "csv":
                # Extract section titles for CSV
                section_titles = [s.get("title", "") for s in transformed["sections"] if isinstance(s, dict)]
                transformed["section_titles"] = ", ".join(section_titles)
                transformed["section_count"] = len(transformed["sections"])
                del transformed["sections"]
            elif self.config.output_format == "elasticsearch":
                # Keep structured for Elasticsearch
                transformed["sections"] = [
                    {
                        "title": s.get("title"),
                        "level": s.get("level"),
                        "content_preview": s.get("content", "")[:200] if s.get("content") else None
                    }
                    for s in transformed["sections"]
                    if isinstance(s, dict)
                ]
        
        # Handle arrays
        for field in ["categories", "keywords", "references", "related_articles"]:
            if field in transformed and isinstance(transformed[field], list):
                if self.config.output_format == "csv":
                    # Limit and convert to string for CSV
                    items = transformed[field][:10] if field == "references" else transformed[field]
                    transformed[field] = ", ".join(map(str, items))
                    if field == "references" and len(transformed[field]) > 10:
                        transformed["reference_count"] = len(transformed[field])
                # Keep as array for other formats
        
        # Process relevance scores
        if "relevance_score" in transformed:
            # Normalize to 0-100 scale if needed
            score = transformed["relevance_score"]
            if isinstance(score, (int, float)) and score <= 1.0:
                transformed["relevance_score"] = int(score * 100)
        
        # Handle chunks array for full articles
        if "chunks" in transformed:
            if self.config.output_format in ["csv", "elasticsearch"]:
                # Remove chunks array, keep chunk count
                if isinstance(transformed["chunks"], list):
                    transformed["chunk_count"] = len(transformed["chunks"])
                del transformed["chunks"]
        
        # Apply field mappings
        mappings = self.get_field_mappings()
        for old_name, new_name in mappings.items():
            if old_name in transformed:
                transformed[new_name] = transformed.pop(old_name)
        
        return transformed
    
    def get_field_mappings(self) -> Dict[str, str]:
        """Get Wikipedia-specific field name mappings.
        
        Returns:
            Dictionary of source field to output field mappings
        """
        # Default mappings for Wikipedia entities
        base_mappings = {
            "page_id": "id",
            "last_modified": "modified_date",
            "retrieval_date": "retrieved_date"
        }
        
        # Add format-specific mappings
        if self.config.output_format == "elasticsearch":
            base_mappings.update({
                "document_id": "_id",  # Use computed document ID
                "content": "content_text",
                "summary": "summary_text"
            })
        
        return base_mappings
    
    def _prepare_for_elasticsearch(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare Wikipedia data for Elasticsearch indexing.
        
        Args:
            data: Wikipedia DataFrame
            
        Returns:
            DataFrame prepared for Elasticsearch
        """
        # Optimize text fields for search
        text_fields = ["content", "summary"]
        for field in text_fields:
            if field in data.columns:
                # Ensure strings
                data[field] = data[field].astype(str, errors='ignore')
        
        # Handle chunk indexing
        if "chunk_index" in data.columns:
            # Create unique document IDs for chunks
            data["_id"] = data.apply(
                lambda row: f"wiki_{row.get('page_id')}_chunk_{row.get('chunk_index')}",
                axis=1
            )
        else:
            # Create document IDs for full articles
            data["_id"] = data["page_id"].apply(lambda x: f"wiki_{x}")
        
        # Ensure proper data types
        numeric_fields = [
            "relevance_score", "page_rank", "word_count",
            "section_count", "reference_count", "chunk_index", "chunk_total"
        ]
        for field in numeric_fields:
            if field in data.columns:
                data[field] = pd.to_numeric(data[field], errors='coerce')
        
        # Handle date fields
        date_fields = ["last_modified", "retrieval_date"]
        for field in date_fields:
            if field in data.columns:
                data[field] = pd.to_datetime(data[field], errors='coerce')
        
        return data
    
    def _prepare_for_csv(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare Wikipedia data for CSV export.
        
        Args:
            data: Wikipedia DataFrame
            
        Returns:
            DataFrame prepared for CSV
        """
        # Flatten nested structures for CSV
        self.config.flatten_nested = True
        
        # Truncate long text fields
        text_fields = ["content", "summary"]
        max_lengths = {"content": 5000, "summary": 1000}
        
        for field in text_fields:
            if field in data.columns:
                max_len = max_lengths.get(field, 1000)
                data[field] = data[field].apply(
                    lambda x: (x[:max_len] + "...") if isinstance(x, str) and len(x) > max_len else x
                )
        
        # Convert arrays to strings
        array_fields = ["categories", "keywords", "references", "related_articles"]
        for field in array_fields:
            if field in data.columns:
                data[field] = data[field].apply(
                    lambda x: ', '.join(x[:10]) if isinstance(x, list) else x
                )
        
        # Remove complex nested fields
        complex_fields = ["sections", "chunks"]
        for field in complex_fields:
            if field in data.columns:
                if field == "sections":
                    # Extract count before removing
                    data["section_count"] = data[field].apply(
                        lambda x: len(x) if isinstance(x, list) else 0
                    )
                data = data.drop(columns=[field])
        
        return data
    
    def _prepare_for_parquet(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare Wikipedia data for Parquet export.
        
        Args:
            data: Wikipedia DataFrame
            
        Returns:
            DataFrame prepared for Parquet
        """
        # Parquet handles nested structures and long text well
        
        # Ensure consistent data types
        if "relevance_score" in data.columns:
            data["relevance_score"] = data["relevance_score"].astype('float64', errors='ignore')
        
        if "word_count" in data.columns:
            data["word_count"] = data["word_count"].astype('int64', errors='ignore')
        
        # Handle date fields
        date_fields = ["last_modified", "retrieval_date"]
        for field in date_fields:
            if field in data.columns:
                data[field] = pd.to_datetime(data[field], errors='coerce')
        
        return data
    
    def get_elasticsearch_mapping(self) -> Dict[str, Any]:
        """Get Elasticsearch mapping for Wikipedia entities.
        
        Returns:
            Elasticsearch mapping configuration
        """
        return {
            "properties": {
                "page_id": {"type": "keyword"},
                "document_id": {"type": "keyword"},
                "title": {
                    "type": "text",
                    "analyzer": "standard",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "url": {"type": "keyword"},
                "language": {"type": "keyword"},
                "content_text": {
                    "type": "text",
                    "analyzer": "standard"
                },
                "summary_text": {
                    "type": "text",
                    "analyzer": "standard"
                },
                "categories": {"type": "keyword"},
                "keywords": {"type": "keyword"},
                "sections": {
                    "type": "nested",
                    "properties": {
                        "title": {"type": "text"},
                        "level": {"type": "integer"},
                        "content_preview": {"type": "text"}
                    }
                },
                "references": {"type": "text"},
                "related_articles": {"type": "keyword"},
                "relevance_score": {"type": "float"},
                "page_rank": {"type": "float"},
                "word_count": {"type": "integer"},
                "section_count": {"type": "integer"},
                "reference_count": {"type": "integer"},
                "modified_date": {"type": "date"},
                "retrieved_date": {"type": "date"},
                "location_context": {"type": "keyword"},
                "city_relevance": {"type": "keyword"},
                "is_chunk": {"type": "boolean"},
                "chunk_index": {"type": "integer"},
                "chunk_total": {"type": "integer"},
                "parent_page_id": {"type": "keyword"},
                "_entity_type": {"type": "keyword"},
                "_processed_at": {"type": "long"}
            }
        }