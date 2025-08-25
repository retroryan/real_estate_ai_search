"""
Property indexer service for managing Elasticsearch index.
Async implementation for data loading and index management.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_bulk

from models import Property, Address, GeoLocation, PropertyType
from config.settings import settings

logger = logging.getLogger(__name__)


class PropertyIndexer:
    """Manages property index and data loading."""
    
    def __init__(self, es_client: AsyncElasticsearch):
        """Initialize indexer with Elasticsearch client."""
        self.es = es_client
        self.index_name = settings.elasticsearch.index_name
        
    async def create_index(self, force_recreate: bool = False) -> bool:
        """Create or recreate the property index."""
        try:
            # Check if index exists
            exists = await self.es.indices.exists(index=self.index_name)
            
            if exists and not force_recreate:
                logger.info(f"Index {self.index_name} already exists")
                return True
            
            if exists and force_recreate:
                logger.info(f"Deleting existing index {self.index_name}")
                await self.es.indices.delete(index=self.index_name)
            
            # Create index with mapping
            mapping = self._get_index_mapping()
            await self.es.indices.create(
                index=self.index_name,
                body=mapping
            )
            
            logger.info(f"Created index {self.index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating index: {e}")
            return False
    
    async def load_demo_data(self, data_path: Optional[str] = None) -> int:
        """Load demo property data into the index."""
        if not data_path:
            data_path = settings.demo.sample_data_path
        
        # Check if file exists
        path = Path(data_path)
        if not path.exists():
            logger.warning(f"Demo data file not found: {data_path}")
            # Generate synthetic data instead
            properties = self._generate_synthetic_properties(
                settings.demo.max_demo_properties
            )
        else:
            # Load from file
            with open(path, 'r') as f:
                data = json.load(f)
                properties = [Property(**item) for item in data]
        
        # Index properties
        count = await self.index_properties(properties)
        logger.info(f"Loaded {count} demo properties")
        return count
    
    async def index_properties(self, properties: List[Property]) -> int:
        """Bulk index properties."""
        if not properties:
            return 0
        
        # Prepare bulk operations
        operations = []
        for prop in properties:
            doc = prop.model_dump(mode='json')
            
            # Ensure location is properly formatted for Elasticsearch
            if prop.address.location:
                doc["address"]["location"] = {
                    "lat": prop.address.location.lat,
                    "lon": prop.address.location.lon
                }
            
            operations.append({
                "_index": self.index_name,
                "_id": prop.id,
                "_source": doc
            })
        
        # Execute bulk indexing
        try:
            success, failed = await async_bulk(
                self.es,
                operations,
                refresh=settings.elasticsearch.refresh_on_write
            )
            
            if failed:
                logger.warning(f"Failed to index {len(failed)} properties")
            
            return success
            
        except Exception as e:
            logger.error(f"Bulk indexing error: {e}")
            return 0
    
    async def update_property(self, property_id: str, updates: Dict[str, Any]) -> bool:
        """Update a single property."""
        try:
            await self.es.update(
                index=self.index_name,
                id=property_id,
                body={"doc": updates},
                refresh=settings.elasticsearch.refresh_on_write
            )
            return True
        except NotFoundError:
            logger.warning(f"Property {property_id} not found for update")
            return False
        except Exception as e:
            logger.error(f"Error updating property {property_id}: {e}")
            return False
    
    async def delete_property(self, property_id: str) -> bool:
        """Delete a property from the index."""
        try:
            await self.es.delete(
                index=self.index_name,
                id=property_id,
                refresh=settings.elasticsearch.refresh_on_write
            )
            return True
        except NotFoundError:
            logger.warning(f"Property {property_id} not found for deletion")
            return False
        except Exception as e:
            logger.error(f"Error deleting property {property_id}: {e}")
            return False
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        try:
            # Get index stats
            stats = await self.es.indices.stats(index=self.index_name)
            
            # Get document count
            count_response = await self.es.count(index=self.index_name)
            
            # Get mapping
            mapping = await self.es.indices.get_mapping(index=self.index_name)
            
            return {
                "index_name": self.index_name,
                "document_count": count_response["count"],
                "size_in_bytes": stats["indices"][self.index_name]["total"]["store"]["size_in_bytes"],
                "fields": list(mapping[self.index_name]["mappings"]["properties"].keys())
            }
            
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {
                "index_name": self.index_name,
                "error": str(e)
            }
    
    async def refresh_index(self) -> bool:
        """Refresh the index to make recent changes searchable."""
        try:
            await self.es.indices.refresh(index=self.index_name)
            return True
        except Exception as e:
            logger.error(f"Error refreshing index: {e}")
            return False
    
    def _get_index_mapping(self) -> Dict[str, Any]:
        """Get Elasticsearch index mapping."""
        return {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "property_analyzer": {
                            "type": "standard",
                            "stopwords": "_english_"
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "listing_id": {"type": "keyword"},
                    "property_type": {"type": "keyword"},
                    "price": {"type": "float"},
                    "bedrooms": {"type": "integer"},
                    "bathrooms": {"type": "float"},
                    "square_feet": {"type": "integer"},
                    "lot_size": {"type": "float"},
                    "year_built": {"type": "integer"},
                    "address": {
                        "properties": {
                            "street": {"type": "text"},
                            "city": {
                                "type": "text",
                                "fields": {
                                    "keyword": {"type": "keyword"}
                                }
                            },
                            "state": {"type": "keyword"},
                            "zip_code": {"type": "keyword"},
                            "location": {"type": "geo_point"}
                        }
                    },
                    "description": {
                        "type": "text",
                        "analyzer": "property_analyzer"
                    },
                    "features": {"type": "keyword"},
                    "amenities": {"type": "keyword"},
                    "images": {"type": "keyword"},
                    "listing_date": {"type": "date"},
                    "last_updated": {"type": "date"},
                    "location_quality_score": {"type": "float"},
                    "neighborhood_desirability": {"type": "float"}
                }
            }
        }
    
    def _generate_synthetic_properties(self, count: int) -> List[Property]:
        """Generate synthetic property data for demos."""
        import random
        
        properties = []
        
        # Sample data for generation
        cities = [
            ("Austin", "TX", 30.2672, -97.7431),
            ("Dallas", "TX", 32.7767, -96.7970),
            ("Houston", "TX", 29.7604, -95.3698),
            ("San Antonio", "TX", 29.4241, -98.4936),
            ("Fort Worth", "TX", 32.7555, -97.3308)
        ]
        
        streets = ["Main St", "Oak Ave", "Elm Dr", "Park Rd", "Lake Blvd", 
                  "Hill Ct", "Valley Way", "Ridge Ln", "Forest Path", "River Rd"]
        
        features_pool = [
            "Granite Countertops", "Hardwood Floors", "Stainless Steel Appliances",
            "Walk-in Closet", "Updated Kitchen", "Open Floor Plan", "High Ceilings",
            "Crown Molding", "Energy Efficient", "Smart Home", "Fireplace",
            "Tile Backsplash", "Recessed Lighting", "Double Vanity"
        ]
        
        amenities_pool = [
            "Pool", "Gym", "Garage", "Patio", "Garden", "Balcony",
            "Storage", "Laundry Room", "Home Office", "Guest Room",
            "Security System", "Central AC", "Deck", "Fence"
        ]
        
        for i in range(count):
            city, state, lat, lon = random.choice(cities)
            
            # Randomize location slightly
            lat += random.uniform(-0.1, 0.1)
            lon += random.uniform(-0.1, 0.1)
            
            # Generate property
            bedrooms = random.randint(1, 5)
            bathrooms = random.choice([1, 1.5, 2, 2.5, 3, 3.5, 4])
            square_feet = bedrooms * random.randint(400, 800) + random.randint(200, 600)
            
            # Price based on size and location
            base_price = square_feet * random.uniform(150, 350)
            price = round(base_price, -3)  # Round to nearest thousand
            
            # Select random features and amenities
            num_features = random.randint(3, 8)
            num_amenities = random.randint(2, 6)
            
            prop = Property(
                id=f"demo-prop-{i+1:04d}",
                listing_id=f"MLS{100000 + i}",
                property_type=random.choice(list(PropertyType)),
                price=price,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                square_feet=square_feet,
                lot_size=random.uniform(0.1, 2.0) if random.random() > 0.5 else None,
                year_built=random.randint(1960, 2023),
                address=Address(
                    street=f"{random.randint(100, 9999)} {random.choice(streets)}",
                    city=city,
                    state=state,
                    zip_code=f"{random.randint(10000, 99999)}",
                    location=GeoLocation(lat=lat, lon=lon)
                ),
                description=f"Beautiful {bedrooms} bedroom, {bathrooms} bathroom home in {city}. "
                           f"This property features {square_feet} square feet of living space.",
                features=random.sample(features_pool, num_features),
                amenities=random.sample(amenities_pool, num_amenities),
                listing_date=datetime.now(),
                location_quality_score=random.uniform(60, 95),
                neighborhood_desirability=random.uniform(6, 9.5)
            )
            
            properties.append(prop)
        
        return properties