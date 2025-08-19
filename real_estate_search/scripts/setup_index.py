#!/usr/bin/env python3
"""
Script to set up property search index and load data.
This script creates or updates the Elasticsearch index and loads property data from JSON files.
"""

import sys
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add parent to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

import structlog
from pydantic import ValidationError
from datetime import datetime

from real_estate_search.config.settings import Settings
from real_estate_search.indexer.property_indexer import PropertyIndexer, PropertyIndexerError
from real_estate_search.indexer.models import Property, Address, GeoLocation, Neighborhood, Parking
from real_estate_search.indexer.enums import PropertyType, PropertyStatus, ParkingType


class PropertyDataLoader:
    """Load property data from JSON files."""
    
    def __init__(self, data_dir: Path):
        """
        Initialize the data loader.
        
        Args:
            data_dir: Directory containing property JSON files.
        """
        self.data_dir = data_dir
        self.logger = structlog.get_logger(__name__).bind(component="PropertyDataLoader")
    
    def load_properties(self) -> List[Property]:
        """
        Load all properties from JSON files in the data directory.
        
        Returns:
            List of Property models.
        """
        properties = []
        neighborhood_map = self._load_neighborhoods()
        
        # Load properties from all properties_*.json files
        property_files = list(self.data_dir.glob("properties_*.json"))
        
        for prop_file in property_files:
            self.logger.debug(f"Loading properties from {prop_file.name}")
            
            try:
                import json
                with open(prop_file) as f:
                    data = json.load(f)
                
                # Handle both array and object formats
                if isinstance(data, list):
                    property_list = data
                elif isinstance(data, dict) and 'properties' in data:
                    property_list = data['properties']
                else:
                    self.logger.warning(f"Unknown format in {prop_file.name}")
                    continue
                
                # Convert each property
                for prop_data in property_list:
                    property_model = self._convert_to_property(prop_data, neighborhood_map)
                    if property_model:
                        properties.append(property_model)
                
                self.logger.debug(f"Loaded {len(property_list)} from {prop_file.name}")
                
            except Exception as e:
                self.logger.error("Failed to load properties", file=prop_file.name, error=str(e))
        
        return properties
    
    def _load_neighborhoods(self) -> Dict[str, Neighborhood]:
        """
        Load neighborhood data from JSON files.
        
        Returns:
            Dictionary mapping neighborhood IDs to Neighborhood models.
        """
        neighborhood_map = {}
        hood_files = list(self.data_dir.glob("neighborhoods_*.json"))
        
        for hood_file in hood_files:
            self.logger.debug(f"Loading neighborhoods from {hood_file.name}")
            
            try:
                import json
                with open(hood_file) as f:
                    data = json.load(f)
                
                # Handle both array and object formats
                if isinstance(data, list):
                    neighborhood_list = data
                elif isinstance(data, dict) and 'neighborhoods' in data:
                    neighborhood_list = data['neighborhoods']
                else:
                    continue
                
                # Create neighborhood models
                for hood_data in neighborhood_list:
                    hood_id = hood_data.get('id') or hood_data.get('neighborhood_id')
                    if not hood_id:
                        continue
                    
                    # Extract ratings if available
                    ratings = hood_data.get('ratings', {})
                    
                    neighborhood = Neighborhood(
                        id=hood_id,
                        name=hood_data.get('name', ''),
                        walkability_score=ratings.get('walkability') or hood_data.get('walkability_score'),
                        school_rating=ratings.get('schools') or hood_data.get('school_rating')
                    )
                    
                    neighborhood_map[hood_id] = neighborhood
                
                self.logger.debug(
                    f"Loaded {len(neighborhood_list)} neighborhoods from {hood_file.name}"
                )
                
            except Exception as e:
                self.logger.error("Failed to load neighborhoods", file=hood_file.name, error=str(e))
        
        return neighborhood_map
    
    def _convert_to_property(
        self,
        data: Dict[str, Any],
        neighborhood_map: Dict[str, Neighborhood]
    ) -> Optional[Property]:
        """
        Convert raw JSON data to a Property model.
        
        Args:
            data: Raw property data dictionary.
            neighborhood_map: Mapping of neighborhood IDs to models.
            
        Returns:
            Validated Property model or None if validation fails.
        """
        try:
            # Convert address
            address_data = data.get('address', {})
            
            # Handle coordinates/location conversion
            # Coordinates might be at the top level or in address
            coordinates = data.get('coordinates') or address_data.get('coordinates')
            location = None
            if coordinates:
                if isinstance(coordinates, dict):
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
            
            # Get neighborhood if available
            neighborhood = None
            neighborhood_id = data.get('neighborhood_id')
            if neighborhood_id and neighborhood_id in neighborhood_map:
                neighborhood = neighborhood_map[neighborhood_id]
            
            # Convert parking if available
            parking = None
            parking_data = data.get('parking')
            if parking_data:
                parking_type = parking_data.get('type')
                if parking_type and isinstance(parking_type, str):
                    try:
                        parking_type = ParkingType(parking_type.lower())
                    except ValueError:
                        parking_type = None
                
                parking = Parking(
                    spaces=parking_data.get('spaces', 0),
                    type=parking_type
                )
            
            # Convert property type
            property_type_str = data.get('property_type')
            if not property_type_str:
                # Try to get from nested property_details
                property_details = data.get('property_details', {})
                property_type_str = property_details.get('property_type', 'other')
            
            # Convert hyphenated to underscored format
            property_type_str = property_type_str.lower().replace('-', '_')
            try:
                property_type = PropertyType(property_type_str)
            except ValueError:
                property_type = PropertyType.OTHER
            
            # Convert status
            status = data.get('status', 'active').lower()
            try:
                status = PropertyStatus(status)
            except ValueError:
                status = PropertyStatus.ACTIVE
            
            # Convert listing date
            listing_date = data.get('listing_date')
            if listing_date:
                if isinstance(listing_date, str):
                    try:
                        listing_date = datetime.fromisoformat(listing_date.replace('Z', '+00:00'))
                    except:
                        listing_date = None
            
            # Extract property details (can be nested or flat)
            property_details = data.get('property_details', {})
            
            # Create Property model
            property_model = Property(
                listing_id=data.get('listing_id', ''),
                property_type=property_type,
                price=data.get('price') or property_details.get('price') or 100000,  # Default to 100k if price is 0 or missing
                bedrooms=property_details.get('bedrooms', data.get('bedrooms', 0)),
                bathrooms=property_details.get('bathrooms', data.get('bathrooms', 0)),
                address=address,
                square_feet=property_details.get('square_feet', data.get('square_feet')),
                year_built=property_details.get('year_built', data.get('year_built')),
                lot_size=property_details.get('lot_size', data.get('lot_size')),
                neighborhood=neighborhood,
                description=data.get('description'),
                features=data.get('features', []),
                amenities=data.get('amenities', []),
                status=status,
                listing_date=listing_date,
                hoa_fee=data.get('hoa_fee') or property_details.get('hoa_fee'),
                parking=parking,
                virtual_tour_url=data.get('virtual_tour_url'),
                images=data.get('images', []),
                mls_number=data.get('mls_number'),
                tax_assessed_value=data.get('tax_assessed_value'),
                annual_tax=data.get('annual_tax')
            )
            
            return property_model
            
        except ValidationError as e:
            self.logger.warning(
                "Failed to validate property",
                listing_id=data.get('listing_id'),
                errors=e.errors()
            )
            return None
        except Exception as e:
            import traceback
            self.logger.error(
                "Failed to convert property",
                listing_id=data.get('listing_id'),
                error=str(e),
                traceback=traceback.format_exc()
            )
            return None


def main():
    """Main entry point for the setup script."""
    parser = argparse.ArgumentParser(
        description="Setup property search index and load data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("real_estate_data"),
        help="Directory containing property JSON files"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recreate index even if it exists"
    )
    
    parser.add_argument(
        "--skip-load",
        action="store_true",
        help="Skip loading data (only create index)"
    )
    
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate data without indexing"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Path to environment file"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = "DEBUG" if args.verbose or args.validate_only else "INFO"
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logger = structlog.get_logger(__name__)
    
    # Print banner
    print("\n" + "="*70)
    print("                    Property Search Index Setup")
    print("="*70 + "\n")
    
    try:
        # Step 1: Load settings
        print("[Step 1/7] Loading configuration...")
        settings = Settings.load()
        logger.info(
            "Configuration loaded",
            elasticsearch_host=f"{settings.elasticsearch.host}:{settings.elasticsearch.port}",
            index_alias=settings.index.alias,
            auth_enabled=settings.elasticsearch.has_auth
        )
        
        # Step 2: Check data directory
        print("[Step 2/7] Checking data directory...")
        if not args.data_dir.exists():
            logger.error(f"❌ Data directory does not exist: {args.data_dir}")
            sys.exit(1)
        
        # List available files
        property_files = list(args.data_dir.glob("properties_*.json"))
        neighborhood_files = list(args.data_dir.glob("neighborhoods_*.json"))
        
        logger.info(
            f"Found data files",
            property_files=len(property_files),
            neighborhood_files=len(neighborhood_files),
            directory=str(args.data_dir)
        )
        
        if args.verbose:
            for pf in property_files:
                logger.debug(f"  📄 Property file: {pf.name}")
            for nf in neighborhood_files:
                logger.debug(f"  📄 Neighborhood file: {nf.name}")
        
        # Step 3: Load property data
        print("[Step 3/7] Loading property data...")
        loader = PropertyDataLoader(args.data_dir)
        
        start_load = time.time()
        properties = loader.load_properties()
        load_time = time.time() - start_load
        
        if not properties:
            logger.warning("❌ No properties found to index")
            if not args.skip_load:
                sys.exit(1)
        else:
            # Analyze loaded data
            cities = {}
            property_types = {}
            price_ranges = {"<500k": 0, "500k-1M": 0, "1M-2M": 0, ">2M": 0}
            
            for prop in properties:
                # Count by city
                city = prop.address.city
                cities[city] = cities.get(city, 0) + 1
                
                # Count by type
                ptype = prop.property_type.value if hasattr(prop.property_type, 'value') else str(prop.property_type)
                property_types[ptype] = property_types.get(ptype, 0) + 1
                
                # Count by price range
                if prop.price < 500000:
                    price_ranges["<500k"] += 1
                elif prop.price < 1000000:
                    price_ranges["500k-1M"] += 1
                elif prop.price < 2000000:
                    price_ranges["1M-2M"] += 1
                else:
                    price_ranges[">2M"] += 1
            
            logger.info(
                f"✅ Loaded {len(properties)} properties",
                load_time=f"{load_time:.2f}s",
                properties_per_second=f"{len(properties)/load_time:.0f}" if load_time > 0 else "N/A"
            )
            
            logger.info("Properties by city:", **cities)
            logger.info("Properties by type:", **property_types)
            logger.info("Properties by price range:", **price_ranges)
        
        # Validate only mode
        if args.validate_only:
            print(f"\n✅ Validation complete: {len(properties)} valid properties")
            sys.exit(0)
        
        # Step 4: Connect to Elasticsearch
        print("[Step 4/7] Connecting to Elasticsearch...")
        indexer = PropertyIndexer(settings)
        
        # Test connection
        if indexer.es.ping():
            info = indexer.es.info()
            logger.info(
                "✅ Connected to Elasticsearch",
                cluster_name=info['cluster_name'],
                version=info['version']['number'],
                number_of_nodes=info.get('number_of_nodes', 'N/A')
            )
        else:
            logger.error("❌ Failed to connect to Elasticsearch")
            sys.exit(1)
        
        # Step 5: Create or update index
        print("[Step 5/7] Setting up index...")
        if args.force:
            logger.info("⚠️  Force recreate flag set - will delete existing index if it exists")
        
        created = indexer.create_index(force=args.force)
        
        if created:
            logger.info(
                "✅ Index created successfully",
                index_pattern=f"{settings.index.name}_v*",
                alias=settings.index.alias,
                shards=settings.index.shards,
                replicas=settings.index.replicas
            )
        else:
            logger.info(f"ℹ️  Using existing index (alias: {settings.index.alias})")
        
        # Get index details
        mapping = indexer.es.indices.get_mapping(index=settings.index.alias)
        index_name = list(mapping.keys())[0]
        field_count = len(mapping[index_name]['mappings']['properties'])
        logger.info(f"Index '{index_name}' has {field_count} mapped fields")
        
        # Step 6: Index properties
        if not args.skip_load and properties:
            print(f"[Step 6/7] Indexing {len(properties)} properties...")
            
            start_index = time.time()
            stats = indexer.index_properties(properties)
            index_time = time.time() - start_index
            
            if stats.success == stats.total:
                logger.info(
                    f"✅ Successfully indexed all {stats.success} properties",
                    duration=f"{index_time:.2f}s",
                    docs_per_second=f"{stats.success/index_time:.1f}" if index_time > 0 else "N/A"
                )
            else:
                logger.warning(
                    f"⚠️  Partially successful: indexed {stats.success}/{stats.total} properties",
                    failed=stats.failed,
                    duration=f"{index_time:.2f}s"
                )
                
                if stats.failed > 0:
                    logger.error(f"Failed to index {stats.failed} documents:")
                    for i, error in enumerate(stats.errors[:5]):
                        logger.error(f"  [{i+1}] {error.get('listing_id', 'unknown')}: {error.get('error', 'unknown error')}")
                    if len(stats.errors) > 5:
                        logger.error(f"  ... and {len(stats.errors) - 5} more errors")
                
                if stats.failed == stats.total:
                    logger.error("❌ All documents failed to index")
                    sys.exit(1)
        elif args.skip_load:
            print("[Step 6/7] Skipping data load (--skip-load flag)")
        
        # Step 7: Verify final state
        print("[Step 7/7] Verifying index...")
        
        # Refresh index to ensure all documents are searchable
        indexer.es.indices.refresh(index=settings.index.alias)
        
        # Get document count
        count_response = indexer.es.count(index=settings.index.alias)
        total_docs = count_response['count']
        
        # Get index statistics
        stats_response = indexer.es.indices.stats(index=settings.index.alias)
        index_stats = list(stats_response['indices'].values())[0]
        size_in_bytes = index_stats['total']['store']['size_in_bytes']
        size_in_mb = size_in_bytes / (1024 * 1024)
        
        # Test search functionality
        test_response = indexer.es.search(
            index=settings.index.alias,
            body={
                "query": {"match_all": {}},
                "size": 1,
                "aggs": {
                    "cities": {"terms": {"field": "address.city.keyword", "size": 5}},
                    "avg_price": {"avg": {"field": "price"}}
                }
            }
        )
        
        search_works = test_response['hits']['total']['value'] > 0
        
        if search_works:
            logger.info("✅ Search functionality verified")
            
            # Show aggregation results if available
            if 'aggregations' in test_response:
                if 'avg_price' in test_response['aggregations']:
                    avg_price = test_response['aggregations']['avg_price']['value']
                    logger.info(f"Average property price: ${avg_price:,.0f}")
                
                if 'cities' in test_response['aggregations']:
                    city_buckets = test_response['aggregations']['cities']['buckets']
                    if city_buckets:
                        logger.info("Top cities by property count:")
                        for bucket in city_buckets[:3]:
                            logger.info(f"  - {bucket['key']}: {bucket['doc_count']} properties")
        else:
            logger.warning("⚠️  Search test returned no results")
        
        # Close connection
        indexer.close()
        
        # Final summary
        print("\n" + "="*70)
        print("                        Setup Complete!")
        print("="*70)
        print(f"✅ Elasticsearch:  Connected to {settings.elasticsearch.host}:{settings.elasticsearch.port}")
        print(f"✅ Index:          {settings.index.alias} ({'created' if created else 'existing'})")
        print(f"✅ Documents:      {total_docs} properties indexed")
        print(f"✅ Index Size:     {size_in_mb:.2f} MB")
        print(f"✅ Search Status:  {'Ready' if search_works else 'Needs verification'}")
        print("="*70)
        print("\nYou can now run search queries against the index!")
        print("Try: python scripts/test_system.py")
        print()
        
    except PropertyIndexerError as e:
        logger.error(f"❌ Indexer error: {e}", code=e.error_code)
        print("\n" + "="*70)
        print("                        Setup Failed")
        print("="*70)
        print(f"❌ Error: {str(e)}")
        print("="*70 + "\n")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"❌ Unexpected error: {e}")
        print("\n" + "="*70)
        print("                        Setup Failed")
        print("="*70)
        print(f"❌ Error: {str(e)}")
        print("="*70 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()