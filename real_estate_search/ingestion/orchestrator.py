"""
Ingestion orchestrator with constructor injection.
Coordinates property data ingestion with enrichment.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import logging

from services.indexing_service import IndexingService
from indexer.models import Property, Address, GeoLocation

logger = logging.getLogger(__name__)


class IngestionOrchestrator:
    """
    Orchestrator for data ingestion with constructor injection.
    All dependencies are injected through the constructor.
    """
    
    def __init__(self, indexing_service: IndexingService, properties_dir: Path):
        """
        Initialize orchestrator with injected dependencies.
        
        Args:
            indexing_service: Service for indexing properties with enrichment
            properties_dir: Directory containing property JSON files
        """
        self.indexing_service = indexing_service
        self.properties_dir = properties_dir
        logger.info(f"Ingestion orchestrator initialized with properties dir: {properties_dir}")
    
    def ingest_all(self, force_recreate: bool = False) -> Dict[str, Any]:
        """
        Orchestrate property ingestion with enrichment.
        
        Args:
            force_recreate: If True, recreate the index before ingestion
            
        Returns:
            Statistics about ingested data
        """
        stats = {
            "total": 0,
            "indexed": 0,
            "failed": 0,
            "properties_files": 0
        }
        
        # Create index if requested
        if force_recreate:
            logger.info("Creating/recreating property index")
            self.indexing_service.create_index(force_recreate=True)
        
        # Load properties from JSON files
        logger.info(f"Loading properties from {self.properties_dir}")
        properties = self._load_properties()
        stats["total"] = len(properties)
        
        if not properties:
            logger.warning("No properties found to index")
            return stats
        
        # Index properties with enrichment
        logger.info(f"Indexing {len(properties)} properties with enrichment")
        index_stats = self.indexing_service.index_properties(properties)
        
        stats["indexed"] = index_stats.success
        stats["failed"] = index_stats.failed
        
        logger.info(
            f"Ingestion complete: {stats['indexed']}/{stats['total']} indexed, "
            f"{stats['failed']} failed"
        )
        
        return stats
    
    def _load_properties(self) -> List[Property]:
        """Load properties from JSON files in the configured directory."""
        properties = []
        
        if not self.properties_dir.exists():
            logger.warning(f"Properties directory not found: {self.properties_dir}")
            return properties
        
        # Find all properties JSON files
        property_files = list(self.properties_dir.glob("properties_*.json"))
        logger.info(f"Found {len(property_files)} property files")
        
        for prop_file in property_files:
            try:
                with open(prop_file, 'r') as f:
                    data = json.load(f)
                
                # Handle different JSON structures
                if isinstance(data, list):
                    properties_data = data
                elif isinstance(data, dict) and 'properties' in data:
                    properties_data = data['properties']
                else:
                    logger.warning(f"Unknown JSON structure in {prop_file}")
                    continue
                
                # Convert to Property objects
                for prop_data in properties_data:
                    try:
                        property_obj = self._parse_property(prop_data)
                        if property_obj:
                            properties.append(property_obj)
                    except Exception as e:
                        logger.warning(f"Failed to parse property: {e}")
                
                logger.info(f"Loaded {len(properties_data)} properties from {prop_file.name}")
                
            except Exception as e:
                logger.error(f"Failed to load properties from {prop_file}: {e}")
        
        logger.info(f"Total properties loaded: {len(properties)}")
        return properties
    
    def _parse_property(self, prop_data: dict) -> Optional[Property]:
        """Parse property data into Property model."""
        try:
            from indexer.enums import PropertyType, PropertyStatus
            
            # Extract nested data
            details = prop_data.get("property_details", {})
            addr_data = prop_data.get("address", {})
            
            # Map property type to enum
            prop_type_str = (details.get("property_type") or 
                           prop_data.get("property_type", "other")).lower()
            prop_type_str = prop_type_str.replace("-", "_")
            
            try:
                property_type = PropertyType(prop_type_str)
            except ValueError:
                property_type = PropertyType.OTHER
            
            # Map status to enum
            status_str = prop_data.get("status", "active").lower()
            try:
                status = PropertyStatus(status_str)
            except ValueError:
                status = PropertyStatus.ACTIVE
            
            # Create GeoLocation if coordinates exist
            location = None
            coordinates = prop_data.get("coordinates") or addr_data.get("coordinates")
            if coordinates and isinstance(coordinates, dict):
                lat = coordinates.get("latitude") or coordinates.get("lat")
                lon = coordinates.get("longitude") or coordinates.get("lon") or coordinates.get("lng")
                if lat and lon:
                    location = GeoLocation(lat=lat, lon=lon)
            
            # Create Address
            address = Address(
                street=addr_data.get("street", "Unknown Street"),
                city=addr_data.get("city", "Unknown City"),
                state=addr_data.get("state", "XX"),
                zip_code=addr_data.get("zip_code") or addr_data.get("zip", "00000"),
                location=location
            )
            
            # Get price from various possible locations
            price = (prop_data.get("listing_price") or 
                    prop_data.get("price") or 
                    details.get("price", 100000))
            
            # Create Property object with all available data
            property_obj = Property(
                listing_id=prop_data.get("listing_id", f"prop_{id(prop_data)}"),
                property_type=property_type,
                price=float(price),
                bedrooms=int(details.get("bedrooms") or prop_data.get("bedrooms", 0)),
                bathrooms=float(details.get("bathrooms") or prop_data.get("bathrooms", 0)),
                address=address,
                square_feet=details.get("square_feet") or prop_data.get("square_feet"),
                year_built=details.get("year_built") or prop_data.get("year_built"),
                lot_size=details.get("lot_size") or prop_data.get("lot_size"),
                description=prop_data.get("description"),
                features=prop_data.get("features", []),
                amenities=prop_data.get("amenities", []),
                status=status,
                images=prop_data.get("images", []),
                virtual_tour_url=prop_data.get("virtual_tour_url"),
                mls_number=prop_data.get("mls_number"),
                hoa_fee=prop_data.get("hoa_fee")
            )
            
            return property_obj
            
        except Exception as e:
            logger.error(f"Failed to parse property: {e}")
            return None