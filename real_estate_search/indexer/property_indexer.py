"""
Property indexer with Wikipedia enrichment.
"""

import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from datetime import datetime

from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import ApiError

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ..config import AppConfig
from wikipedia.enricher import PropertyEnricher
from wikipedia.extractor import WikipediaExtractor
from indexer.mappings import get_property_mappings
from indexer.models import IndexStats, Property
from .enums import IndexName

logger = logging.getLogger(__name__)


class PropertyIndexer:
    """Indexes properties with Wikipedia enrichment."""
    
    def __init__(
        self,
        es_client: Optional[Elasticsearch] = None,
        index_name: Optional[str] = None,
        config: Optional[AppConfig] = None,
        settings: Optional[Any] = None  # Backward compatibility
    ):
        """Initialize the indexer."""
        # Use config, fallback to loading from yaml
        self.config = config or AppConfig.from_yaml()
        self.es_client = es_client or self._create_es_client()
        self.index_name = index_name or IndexName.PROPERTIES
        self.enricher = PropertyEnricher()
    
    def _create_es_client(self) -> Elasticsearch:
        """Create Elasticsearch client."""
        client_config = self.config.elasticsearch.get_client_config()
        return Elasticsearch(**client_config)
    
    def create_index(self, force_recreate: bool = False) -> bool:
        """Create index with settings for demo."""
        try:
            if self.es_client.indices.exists(index=self.index_name):
                if not force_recreate:
                    return False
                self.es_client.indices.delete(index=self.index_name)
            
            # Get full mappings with settings
            mappings_config = get_property_mappings()
            
            # Create index with comprehensive mappings
            self.es_client.indices.create(
                index=self.index_name,
                body=mappings_config
            )
            return True
            
        except ApiError as e:
            logger.error(f"Error creating index: {e}")
            return False
    
    
    def index_properties(self, properties: List[Property]) -> IndexStats:
        """THE ONLY WAY to index properties."""
        if not properties:
            raise ValueError("No properties to index")
        
        stats = IndexStats(total=len(properties))
        
        # Enrich ALL at once (batch operation)
        enriched_docs = []
        for prop in properties:
            # Get property data
            prop_dict = prop.model_dump(exclude_none=True)
            
            # Enrich with Wikipedia data
            enriched = self.enricher.enrich_property(prop_dict)
            enriched_docs.append(enriched)
        
        # Prepare bulk actions with UNIQUE IDs
        actions = []
        for doc in enriched_docs:
            action = {
                "_index": self.index_name,
                "_id": doc["listing_id"],  # Simple, direct
                "_source": doc
            }
            actions.append(action)
        
        # Bulk index with proper error handling
        try:
            success, failed = helpers.bulk(
                self.es_client,
                actions,
                chunk_size=1000,  # Reasonable batch size
                raise_on_error=False,
                stats_only=False  # Get actual errors
            )
            
            stats.success = success
            stats.failed = len(failed) if failed else 0
            
            # Report results clearly
            if failed:
                for item in failed:
                    logger.error(f"Failed to index: {item}")
                    stats.errors.append(item)
            
        except Exception as e:
            logger.error(f"Bulk indexing error: {e}")
            stats.failed = stats.total
            stats.errors.append({"error": str(e)})
        
        return stats
    
    
    def _clean_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively remove None values and empty collections."""
        cleaned = {}
        
        for key, value in doc.items():
            if value is None:
                continue
            elif isinstance(value, dict):
                cleaned_dict = self._clean_document(value)
                if cleaned_dict:
                    cleaned[key] = cleaned_dict
            elif isinstance(value, list):
                cleaned_list = [
                    self._clean_document(item) if isinstance(item, dict) else item
                    for item in value
                    if item is not None
                ]
                if cleaned_list:
                    cleaned[key] = cleaned_list
            else:
                cleaned[key] = value
        
        return cleaned
    
    def index_properties_from_file(self, file_path: str, batch_size: int = 50) -> IndexStats:
        """Index properties from a JSON file."""
        import json
        from pathlib import Path
        from .models import Property, Address, GeoLocation, Neighborhood
        from ..indexer.enums import PropertyType, PropertyStatus
        
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path) as f:
            data = json.load(f)
        
        # Handle different JSON formats
        if isinstance(data, list):
            property_list = data
        elif isinstance(data, dict) and 'properties' in data:
            property_list = data['properties']
        else:
            raise ValueError(f"Unexpected JSON format in {file_path}")
        
        # Convert to Property objects
        properties = []
        for item in property_list:
            try:
                # Parse address
                address_data = item.get('address', {})
                coordinates = item.get('coordinates') or address_data.get('coordinates')
                location = None
                if coordinates:
                    location = GeoLocation(
                        lat=coordinates.get('latitude', coordinates.get('lat')),
                        lon=coordinates.get('longitude', coordinates.get('lon'))
                    )
                
                address = Address(
                    street=address_data.get('street', ''),
                    city=address_data.get('city', ''),
                    state=address_data.get('state', ''),
                    zip_code=address_data.get('zip', address_data.get('zip_code', '00000')),
                    location=location
                )
                
                # Parse neighborhood if present
                neighborhood = None
                if 'neighborhood' in item and isinstance(item['neighborhood'], dict):
                    neigh_data = item['neighborhood']
                    neighborhood = Neighborhood(
                        id=neigh_data.get('id', ''),
                        name=neigh_data.get('name', ''),
                        walkability_score=neigh_data.get('walkability_score'),
                        school_rating=neigh_data.get('school_rating')
                    )
                
                # Parse property type
                property_type_str = item.get('property_type', 'other').lower().replace('-', '_')
                try:
                    property_type = PropertyType(property_type_str)
                except ValueError:
                    property_type = PropertyType.OTHER
                
                # Parse status
                status_str = item.get('status', 'active').lower()
                try:
                    status = PropertyStatus(status_str)
                except ValueError:
                    status = PropertyStatus.ACTIVE
                
                # Get price from various possible locations
                price = (item.get('listing_price') or 
                        item.get('price') or 
                        item.get('property_details', {}).get('price') or 
                        100000)
                
                # Get other property details
                property_details = item.get('property_details', {})
                
                # Create Property object
                property_obj = Property(
                    listing_id=item.get('listing_id', ''),
                    property_type=property_type,
                    price=price,
                    bedrooms=property_details.get('bedrooms', item.get('bedrooms', 0)),
                    bathrooms=property_details.get('bathrooms', item.get('bathrooms', 0)),
                    square_feet=property_details.get('square_feet', item.get('square_feet')),
                    year_built=property_details.get('year_built', item.get('year_built')),
                    address=address,
                    neighborhood=neighborhood,
                    description=item.get('description'),
                    features=item.get('features', []),
                    amenities=item.get('amenities', []),
                    status=status
                )
                properties.append(property_obj)
                
            except Exception as e:
                logger.warning(f"Skipping invalid property in {file_path}: {e}")
                continue
        
        logger.info(f"Loaded {len(properties)} properties from {file_path}")
        
        # Index in batches
        total_stats = IndexStats(total=len(properties))
        for i in range(0, len(properties), batch_size):
            batch = properties[i:i+batch_size]
            batch_stats = self.index_properties(batch)
            total_stats.success += batch_stats.success
            total_stats.failed += batch_stats.failed
            total_stats.errors.extend(batch_stats.errors)
            logger.info(f"Indexed batch {i//batch_size + 1}: {batch_stats.success} success, {batch_stats.failed} failed")
        
        return total_stats
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the index."""
        try:
            stats = self.es_client.indices.stats(index=self.index_name)
            count = self.es_client.count(index=self.index_name)
            
            # Get Wikipedia coverage stats
            wiki_coverage = self.es_client.search(
                index=self.index_name,
                body={
                    "size": 0,
                    "aggs": {
                        "has_location_context": {
                            "filter": {"exists": {"field": "location_context.wikipedia_page_id"}}
                        },
                        "has_neighborhood_context": {
                            "filter": {"exists": {"field": "neighborhood_context.wikipedia_page_id"}}
                        },
                        "has_pois": {
                            "filter": {"exists": {"field": "nearby_poi"}}
                        },
                        "avg_scores": {
                            "stats": {"field": "location_scores.overall_desirability"}
                        }
                    }
                }
            )
            
            return {
                "index_name": self.index_name,
                "document_count": count["count"],
                "size_in_bytes": stats["indices"][self.index_name]["total"]["store"]["size_in_bytes"],
                "wikipedia_coverage": {
                    "location_context": wiki_coverage["aggregations"]["has_location_context"]["doc_count"],
                    "neighborhood_context": wiki_coverage["aggregations"]["has_neighborhood_context"]["doc_count"],
                    "has_pois": wiki_coverage["aggregations"]["has_pois"]["doc_count"],
                    "avg_desirability": wiki_coverage["aggregations"]["avg_scores"].get("avg", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {"error": str(e)}