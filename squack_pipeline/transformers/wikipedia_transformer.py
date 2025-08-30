"""Wikipedia transformer for Elasticsearch format compatibility.

This transformer handles Wikipedia data from the Gold tier, which already has:
- Most fields in their final form (Wikipedia is mostly flat)
- Location array created [lon, lat]
- page_id renamed from pageid
- Entity type field added

The transformer now performs minimal operations, mainly:
- Converting Decimal types to float for Elasticsearch
- Ensuring arrays are properly formatted
- Ensuring page_id is a string for Elasticsearch
- Mapping html_file to article_filename for enrichment workflow
- Adding content_loaded field for enrichment status tracking
"""

from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, List, Optional

from squack_pipeline.transformers.base_embedding_transformer import BaseEmbeddingTransformer
from squack_pipeline.models.transformer_models import TransformedWikipedia


class WikipediaTransformer(BaseEmbeddingTransformer):
    """Transform Wikipedia Gold tier data for Elasticsearch.
    
    Gold tier data already has most fields in their final form, so this
    transformer mainly handles type conversions and ensures compatibility
    with Elasticsearch mappings.
    """
    
    def __init__(self):
        """Initialize Wikipedia transformer with embedding capabilities."""
        super().__init__()  # Initialize embedding service from parent
    
    def transform(self, wikipedia_data: Dict[str, Any]) -> TransformedWikipedia:
        """
        Transform Gold tier Wikipedia data to Elasticsearch format.
        
        Gold tier already provides:
        - page_id field (renamed from pageid)
        - Location array [lon, lat] for geo_point when coordinates exist
        - Entity type field
        - All core fields in correct format
        
        This transformer:
        - Ensures page_id is a string (critical for Elasticsearch)
        - Converts Decimal types to float
        - Ensures arrays are properly formatted
        - Maps html_file to article_filename for enrichment workflow
        - Sets content_loaded to False for enrichment status tracking
        - Passes through all fields with minimal changes
        
        Args:
            wikipedia_data: Wikipedia data from Gold tier (DuckDB)
            
        Returns:
            TransformedWikipedia model ready for Elasticsearch indexing
        """
        # CRITICAL: page_id must be string for Elasticsearch
        page_id = wikipedia_data.get('page_id')
        page_id_str = str(page_id) if page_id is not None else None
        
        # Process infobox data
        infobox_data = None
        if 'infobox_data' in wikipedia_data:
            infobox_data = self._convert_nested_decimals(wikipedia_data['infobox_data'])
        
        # Generate embeddings if service is available
        embedding = None
        embedding_model = None
        embedding_dimension = None
        if self.embedding_service:
            # Use extract for embeddings (full content is too large)
            wikipedia_text = self._create_wikipedia_text(wikipedia_data)
            embedding = self.generate_embedding(wikipedia_text)
            if embedding:
                embedding_model = self.service_config.model_name if self.service_config else None
                embedding_dimension = len(embedding)
        
        # Create the transformed Wikipedia model
        transformed = TransformedWikipedia(
            # Core identifiers - ensure strings
            id=str(wikipedia_data.get('id')) if wikipedia_data.get('id') is not None else None,
            page_id=page_id_str,
            location_id=str(wikipedia_data.get('location_id')) if wikipedia_data.get('location_id') is not None else None,
            title=wikipedia_data.get('title'),
            
            # URLs and files
            url=wikipedia_data.get('url'),
            html_file=wikipedia_data.get('html_file'),
            article_filename=wikipedia_data.get('html_file'),  # Map html_file to article_filename
            
            # Content
            extract=wikipedia_data.get('extract'),
            extract_length=self._to_int(wikipedia_data.get('extract_length')),
            
            # Content enrichment tracking
            content_loaded=False,  # Default to not loaded
            
            # Arrays
            categories=self._ensure_array(wikipedia_data.get('categories')),
            
            # Coordinates
            latitude=self._to_float(wikipedia_data.get('latitude')),
            longitude=self._to_float(wikipedia_data.get('longitude')),
            location=wikipedia_data.get('location'),
            
            # Relevance
            relevance_score=self._to_float(wikipedia_data.get('relevance_score')),
            relevance_category=wikipedia_data.get('relevance_category'),
            
            # Metadata
            depth=self._to_int(wikipedia_data.get('depth')),
            crawled_at=wikipedia_data.get('crawled_at'),
            file_hash=wikipedia_data.get('file_hash'),
            image_url=wikipedia_data.get('image_url'),
            links_count=self._to_int(wikipedia_data.get('links_count')),
            infobox_data=infobox_data,
            
            # Processing metadata
            entity_type=wikipedia_data.get('entity_type', 'wikipedia'),
            gold_processed_at=wikipedia_data.get('gold_processed_at'),
            processing_version=wikipedia_data.get('processing_version'),
            
            # Embeddings
            embedding=embedding,
            embedding_model=embedding_model,
            embedding_dimension=embedding_dimension
        )
        
        return transformed
    
    def _convert_nested_decimals(self, obj: Any) -> Any:
        """
        Recursively convert Decimal types in nested structures.
        
        Args:
            obj: Object to convert (dict, list, or value)
            
        Returns:
            Object with Decimals converted to float
        """
        if isinstance(obj, dict):
            return {k: self._convert_nested_decimals(v) for k, v in obj.items() if v is not None}
        elif isinstance(obj, list):
            return [self._convert_nested_decimals(item) for item in obj]
        elif isinstance(obj, Decimal):
            return float(obj)
        else:
            return obj
    
    def _ensure_array(self, value: Any) -> List[Any]:
        """
        Ensure value is an array.
        
        Args:
            value: Value to convert to array
            
        Returns:
            Array representation of value
        """
        if value is None:
            return []
        if isinstance(value, list):
            # Convert any Decimals in the list
            return [self._convert_nested_decimals(item) for item in value]
        if isinstance(value, str):
            # Handle comma-separated strings (common for categories)
            if ',' in value:
                return [item.strip() for item in value.split(',') if item.strip()]
            return [value] if value else []
        return []
    
    def _to_float(self, value: Any) -> Optional[float]:
        """
        Convert value to float, handling Decimal types and NaN.
        
        Args:
            value: Value to convert
            
        Returns:
            Float value or None (None if NaN, inf, or invalid)
        """
        if value is None:
            return None
        if isinstance(value, Decimal):
            result = float(value)
        else:
            try:
                result = float(value)
            except (ValueError, TypeError):
                return None
        
        # Check for NaN and infinity - return None to avoid Elasticsearch issues
        import math
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    
    def _to_int(self, value: Any) -> Optional[int]:
        """
        Convert value to integer.
        
        Args:
            value: Value to convert
            
        Returns:
            Integer value or None
        """
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def _to_datetime(self, value: Any) -> Optional[str]:
        """
        Convert value to ISO datetime string for Elasticsearch.
        
        Args:
            value: Value to convert
            
        Returns:
            ISO datetime string or None
        """
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, str):
            # Return as-is if already a string (Gold tier timestamps)
            return value
        return None
    
    def _create_wikipedia_text(self, wikipedia_data: Dict[str, Any]) -> str:
        """Create searchable text from Wikipedia data for embedding generation.
        
        For Wikipedia articles, we use the short_summary field which is more
        suitable for embeddings than the full content (which can be very large).
        Falls back to title if summary is not available.
        
        Args:
            wikipedia_data: Wikipedia data dictionary
            
        Returns:
            Text suitable for embedding (summary or title)
        """
        # Prefer short_summary for embeddings (concise and focused)
        short_summary = wikipedia_data.get('short_summary')
        if short_summary:
            return short_summary
        
        # Fall back to long_summary if short is not available
        long_summary = wikipedia_data.get('long_summary')
        if long_summary:
            # Truncate if too long (embeddings have token limits)
            return long_summary[:2000]
        
        # Last resort: use title and categories
        text_parts = []
        
        title = wikipedia_data.get('title')
        if title:
            text_parts.append(title)
        
        # Add categories for context
        categories = wikipedia_data.get('categories')
        if categories:
            if isinstance(categories, list):
                text_parts.append(" ".join(categories[:10]))  # Limit categories
            elif isinstance(categories, str):
                text_parts.append(categories)
        
        # Add key topics if available
        key_topics = wikipedia_data.get('key_topics')
        if key_topics:
            if isinstance(key_topics, list):
                text_parts.append(" ".join(key_topics))
            elif isinstance(key_topics, str):
                text_parts.append(key_topics)
        
        return " ".join(filter(None, text_parts)) or wikipedia_data.get('title', '')