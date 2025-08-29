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
"""

from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, List, Optional

from squack_pipeline.utils.logging import PipelineLogger


class WikipediaTransformer:
    """Transform Wikipedia Gold tier data for Elasticsearch.
    
    Gold tier data already has most fields in their final form, so this
    transformer mainly handles type conversions and ensures compatibility
    with Elasticsearch mappings.
    """
    
    def __init__(self):
        """Initialize Wikipedia transformer."""
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
    
    def transform(self, wikipedia_data: Dict[str, Any]) -> Dict[str, Any]:
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
        - Passes through all fields with minimal changes
        
        Args:
            wikipedia_data: Wikipedia data from Gold tier (DuckDB)
            
        Returns:
            Document ready for Elasticsearch indexing
        """
        # Start with a copy to avoid modifying original
        doc = {}
        
        # Core Wikipedia fields (pass through)
        # CRITICAL: page_id must be string for Elasticsearch
        page_id = wikipedia_data.get('page_id')
        doc['id'] = wikipedia_data.get('id')
        doc['page_id'] = str(page_id) if page_id is not None else None
        doc['location_id'] = wikipedia_data.get('location_id')
        doc['title'] = wikipedia_data.get('title')
        doc['url'] = wikipedia_data.get('url')
        doc['extract'] = wikipedia_data.get('extract')
        doc['extract_length'] = self._to_int(wikipedia_data.get('extract_length'))
        
        # Arrays - ensure proper format
        doc['categories'] = self._ensure_array(wikipedia_data.get('categories'))
        
        # Coordinates
        doc['latitude'] = self._to_float(wikipedia_data.get('latitude'))
        doc['longitude'] = self._to_float(wikipedia_data.get('longitude'))
        
        # Location array (already created in Gold as [lon, lat])
        if 'location' in wikipedia_data:
            doc['location'] = wikipedia_data['location']
        
        # Relevance fields
        doc['relevance_score'] = self._to_float(wikipedia_data.get('relevance_score'))
        doc['relevance_category'] = wikipedia_data.get('relevance_category')
        
        # Metadata fields
        doc['depth'] = self._to_int(wikipedia_data.get('depth'))
        doc['crawled_at'] = self._to_datetime(wikipedia_data.get('crawled_at'))
        doc['html_file'] = wikipedia_data.get('html_file')
        doc['file_hash'] = wikipedia_data.get('file_hash')
        doc['image_url'] = wikipedia_data.get('image_url')
        doc['links_count'] = self._to_int(wikipedia_data.get('links_count'))
        
        # Infobox data (if present)
        if 'infobox_data' in wikipedia_data:
            doc['infobox_data'] = self._convert_nested_decimals(wikipedia_data['infobox_data'])
        
        # Gold tier metadata
        doc['entity_type'] = wikipedia_data.get('entity_type', 'wikipedia')
        doc['gold_processed_at'] = self._to_datetime(wikipedia_data.get('gold_processed_at'))
        doc['processing_version'] = wikipedia_data.get('processing_version')
        
        # Handle embeddings if present
        if 'embedding' in wikipedia_data and wikipedia_data['embedding']:
            doc['embedding'] = wikipedia_data['embedding']
            doc['embedding_model'] = wikipedia_data.get('embedding_model')
            doc['embedding_dimension'] = self._to_int(wikipedia_data.get('embedding_dimension'))
        
        # Remove None values for cleaner Elasticsearch documents
        doc = {k: v for k, v in doc.items() if v is not None}
        
        return doc
    
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
        Convert value to float, handling Decimal types.
        
        Args:
            value: Value to convert
            
        Returns:
            Float value or None
        """
        if value is None:
            return None
        if isinstance(value, Decimal):
            return float(value)
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
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