"""
Service for indexing properties with constructor injection.
Coordinates property indexing with enrichment.
"""

from typing import List, Dict, Any
import logging

from repositories.property_repository import PropertyRepository
from services.enrichment_service import EnrichmentService
from indexer.models import Property, PropertyDocument, IndexStats
from indexer.mappings import get_property_mappings

logger = logging.getLogger(__name__)


class IndexingService:
    """
    Service for indexing properties with enrichment.
    All dependencies injected through constructor.
    """
    
    def __init__(
        self,
        property_repository: PropertyRepository,
        enrichment_service: EnrichmentService
    ):
        """
        Initialize service with repositories and services.
        
        Args:
            property_repository: Repository for property storage
            enrichment_service: Service for enriching properties
        """
        self.property_repository = property_repository
        self.enrichment_service = enrichment_service
        logger.info("Indexing service initialized")
    
    def create_index(self, force_recreate: bool = False) -> bool:
        """
        Create the property index with mappings.
        
        Args:
            force_recreate: If True, delete existing index first
            
        Returns:
            True if successful
        """
        # Check if index exists
        if self.property_repository.index_exists():
            if not force_recreate:
                logger.info("Index already exists, skipping creation")
                return False
            
            # Delete existing index
            logger.info("Deleting existing index for recreation")
            self.property_repository.delete_index()
        
        # Get mappings
        mappings = get_property_mappings()
        
        # Create index
        success = self.property_repository.create_index(mappings)
        
        if success:
            logger.info("Property index created successfully")
        else:
            logger.error("Failed to create property index")
        
        return success
    
    def index_property(self, property_obj: Property) -> bool:
        """
        Index a single property with enrichment.
        
        Args:
            property_obj: Property object to index
            
        Returns:
            True if successful
        """
        # Convert to document format
        property_doc = PropertyDocument.from_property(property_obj)
        property_dict = property_doc.model_dump(exclude_none=True, mode='json')
        
        # Enrich with Wikipedia data
        enriched = self.enrichment_service.enrich_property(property_dict)
        
        # Index the enriched document
        success = self.property_repository.index_property(enriched)
        
        if success:
            logger.debug(f"Indexed property {property_obj.listing_id}")
        else:
            logger.error(f"Failed to index property {property_obj.listing_id}")
        
        return success
    
    def index_properties(self, properties: List[Property]) -> IndexStats:
        """
        Bulk index multiple properties with enrichment.
        
        Args:
            properties: List of Property objects to index
            
        Returns:
            IndexStats with results
        """
        if not properties:
            logger.warning("No properties to index")
            return IndexStats(total=0)
        
        logger.info(f"Starting bulk indexing of {len(properties)} properties")
        
        # Convert to document format
        property_docs = []
        conversion_errors = []
        for prop in properties:
            try:
                doc = PropertyDocument.from_property(prop)
                property_dict = doc.model_dump(exclude_none=True, mode='json')
                property_docs.append(property_dict)
            except Exception as e:
                logger.error(f"Failed to convert property {prop.listing_id}: {e}")
                conversion_errors.append({'listing_id': prop.listing_id, 'error': str(e)})
        
        # Enrich all properties
        logger.info("Enriching properties with Wikipedia data")
        enriched_docs = self.enrichment_service.enrich_properties(property_docs)
        
        # Bulk index
        logger.info("Bulk indexing enriched properties")
        stats = self.property_repository.bulk_index_properties(enriched_docs)
        
        # Add conversion errors to stats if any
        if conversion_errors:
            stats.failed += len(conversion_errors)
            stats.errors.extend(conversion_errors)
        
        logger.info(
            f"Indexing complete: {stats.success}/{stats.total} successful, "
            f"{stats.failed} failed (including {len(conversion_errors)} conversion errors)"
        )
        
        return stats
    
    def update_property(self, listing_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing property.
        
        Args:
            listing_id: Property listing ID
            updates: Fields to update
            
        Returns:
            True if successful
        """
        # Check if enrichment is needed for the updates
        if any(field in updates for field in ['address', 'neighborhood']):
            # Get existing property
            existing = self.property_repository.get_property_by_id(listing_id)
            if existing:
                # Merge updates
                existing.update(updates)
                # Re-enrich
                enriched = self.enrichment_service.enrich_property(existing)
                # Update with enriched data
                return self.property_repository.update_property(listing_id, enriched)
        
        # Direct update without enrichment
        return self.property_repository.update_property(listing_id, updates)
    
    def delete_property(self, listing_id: str) -> bool:
        """
        Delete a property from the index.
        
        Args:
            listing_id: Property listing ID
            
        Returns:
            True if successful
        """
        return self.property_repository.delete_property(listing_id)
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the property index.
        
        Returns:
            Index statistics
        """
        stats = self.property_repository.get_index_stats()
        
        # Add enrichment coverage stats
        if 'error' not in stats:
            # Query for enrichment coverage
            enrichment_stats = self._get_enrichment_coverage()
            stats['enrichment_coverage'] = enrichment_stats
        
        return stats
    
    def _get_enrichment_coverage(self) -> Dict[str, Any]:
        """
        Get statistics about Wikipedia enrichment coverage.
        
        Returns:
            Enrichment coverage statistics
        """
        aggs = {
            "has_location_context": {
                "filter": {"exists": {"field": "location_context.wikipedia_page_id"}}
            },
            "has_neighborhood_context": {
                "filter": {"exists": {"field": "neighborhood_context.wikipedia_page_id"}}
            },
            "has_pois": {
                "filter": {"exists": {"field": "nearby_poi"}}
            }
        }
        
        results = self.property_repository.get_aggregations(aggs)
        
        total_count = self.property_repository.count()
        
        return {
            "total_properties": total_count,
            "with_location_context": results.get("has_location_context", {}).get("doc_count", 0),
            "with_neighborhood_context": results.get("has_neighborhood_context", {}).get("doc_count", 0),
            "with_pois": results.get("has_pois", {}).get("doc_count", 0)
        }
    
    def refresh_index(self) -> bool:
        """
        Refresh the index to make recent changes searchable.
        
        Returns:
            True if successful
        """
        return self.property_repository.refresh_index()