#!/usr/bin/env python3
"""
THE ONLY SETUP SCRIPT
Single clear flow: load → enrich → index
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import Config
from indexer.property_indexer import PropertyIndexer
from indexer.models import Property, Address, Neighborhood, GeoLocation
from indexer.enums import PropertyType, PropertyStatus


def load_test_properties() -> List[Property]:
    """Load fixed 3 test properties."""
    return [
        Property(
            listing_id="test-001",
            property_type=PropertyType.SINGLE_FAMILY,
            price=500000,
            bedrooms=3,
            bathrooms=2,
            address=Address(street="123 Test St", city="Park City", state="UT", zip_code="84060")
        ),
        Property(
            listing_id="test-002", 
            property_type=PropertyType.CONDO,
            price=750000,
            bedrooms=2,
            bathrooms=2,
            address=Address(street="456 Test Ave", city="San Francisco", state="CA", zip_code="94102")
        ),
        Property(
            listing_id="test-003",
            property_type=PropertyType.TOWNHOUSE,
            price=650000,
            bedrooms=3,
            bathrooms=3,
            address=Address(street="789 Test Blvd", city="Park City", state="UT", zip_code="84060")
        )
    ]


def load_all_properties() -> List[Property]:
    """Load real data from JSON files."""
    data_dir = Path("/Users/ryanknight/projects/temporal/real_estate_ai_search/real_estate_data")
    properties = []
    
    # Load neighborhoods first
    neighborhoods = {}
    for hood_file in data_dir.glob("neighborhoods_*.json"):
        with open(hood_file) as f:
            hood_data = json.load(f)
            for hood in hood_data:
                hood_id = hood.get('neighborhood_id')
                if hood_id:
                    characteristics = hood.get('characteristics', {})
                    neighborhoods[hood_id] = Neighborhood(
                        id=hood_id,
                        name=hood.get('name', ''),
                        walkability_score=characteristics.get('walkability_score'),
                        school_rating=characteristics.get('school_rating')
                    )
    
    # Load properties
    for prop_file in data_dir.glob("properties_*.json"):
        with open(prop_file) as f:
            prop_data = json.load(f)
            
            # Handle different JSON formats
            if isinstance(prop_data, list):
                property_list = prop_data
            elif isinstance(prop_data, dict) and 'properties' in prop_data:
                property_list = prop_data['properties']
            else:
                continue
            
            for data in property_list:
                try:
                    # Convert address
                    address_data = data.get('address', {})
                    coordinates = data.get('coordinates') or address_data.get('coordinates')
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
                    
                    # Get neighborhood
                    neighborhood = None
                    neighborhood_id = data.get('neighborhood_id')
                    if neighborhood_id and neighborhood_id in neighborhoods:
                        neighborhood = neighborhoods[neighborhood_id]
                    
                    # Convert property type
                    property_type_str = data.get('property_type', 'other').lower().replace('-', '_')
                    try:
                        property_type = PropertyType(property_type_str)
                    except ValueError:
                        property_type = PropertyType.OTHER
                    
                    # Convert status
                    status_str = data.get('status', 'active').lower()
                    try:
                        status = PropertyStatus(status_str)
                    except ValueError:
                        status = PropertyStatus.ACTIVE
                    
                    # Extract property details
                    property_details = data.get('property_details', {})
                    
                    property_obj = Property(
                        listing_id=data.get('listing_id', ''),
                        property_type=property_type,
                        price=data.get('listing_price') or data.get('price') or property_details.get('price') or 100000,
                        bedrooms=property_details.get('bedrooms', data.get('bedrooms', 0)),
                        bathrooms=property_details.get('bathrooms', data.get('bathrooms', 0)),
                        address=address,
                        square_feet=property_details.get('square_feet', data.get('square_feet')),
                        year_built=property_details.get('year_built', data.get('year_built')),
                        neighborhood=neighborhood,
                        description=data.get('description'),
                        features=data.get('features', []),
                        amenities=data.get('amenities', []),
                        status=status
                    )
                    properties.append(property_obj)
                    
                except Exception as e:
                    print(f"Skipping invalid property {data.get('listing_id', 'unknown')}: {e}")
    
    return properties


def main():
    """Main entry point for the setup script."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--recreate', action='store_true', help='Recreate index')
    parser.add_argument('--test-data', action='store_true', help='Use test data')
    args = parser.parse_args()
    
    # Load config
    config = Config.from_yaml()
    
    # Create indexer
    indexer = PropertyIndexer(config=config)
    
    # Create index (optional recreate)
    if args.recreate or not indexer.es_client.indices.exists(index=indexer.index_name):
        indexer.create_index(force_recreate=args.recreate)
        print("✅ Index created")
    
    # Load data
    if args.test_data:
        properties = load_test_properties()  # Fixed 3 test properties
        print(f"📄 Loaded {len(properties)} test properties")
    else:
        properties = load_all_properties()   # Real data from JSON files
        print(f"📄 Loaded {len(properties)} properties")
    
    # Index data - ONE WAY ONLY
    stats = indexer.index_properties(properties)
    
    # Report results
    print(f"✅ Indexed {stats.success}/{stats.total} properties")
    if stats.failed:
        print(f"❌ Failed: {stats.failed}")
        for error in stats.errors[:5]:
            print(f"  - {error}")


if __name__ == "__main__":
    main()