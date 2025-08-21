"""Enhanced data loader for real estate JSON files with Wikipedia integration"""
import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import ValidationError

from src.models import Property, Neighborhood, City, Feature

def load_json_file(file_path: Path) -> List[Dict[str, Any]]:
    """Load JSON data from file"""
    with open(file_path, 'r') as f:
        return json.load(f)

def load_property_data() -> Dict[str, List[Property]]:
    """Load and validate all property data files"""
    # Navigate to the real_estate_data folder from graph-real-estate
    base_path = Path(__file__).parent.parent.parent.parent / 'real_estate_data'
    
    # Load raw JSON data
    sf_raw = load_json_file(base_path / 'properties_sf.json')
    pc_raw = load_json_file(base_path / 'properties_pc.json')
    
    # Convert to Pydantic models with city/state added
    sf_properties = []
    for prop_data in sf_raw:
        prop_data['city'] = 'San Francisco'
        prop_data['state'] = 'California'
        try:
            sf_properties.append(Property(**prop_data))
        except ValidationError as e:
            print(f"Validation error for SF property {prop_data.get('listing_id')}: {e}")
    
    pc_properties = []
    for prop_data in pc_raw:
        prop_data['city'] = 'Park City'
        prop_data['state'] = 'Utah'
        try:
            pc_properties.append(Property(**prop_data))
        except ValidationError as e:
            print(f"Validation error for PC property {prop_data.get('listing_id')}: {e}")
    
    return {
        'sf': sf_properties,
        'pc': pc_properties,
        'all': sf_properties + pc_properties
    }

def validate_property_data(properties: List[Property]) -> bool:
    """Validate properties using Pydantic models"""
    # Since we're using Pydantic, validation happens automatically
    # This function now just reports statistics
    valid_count = len(properties)
    print(f"All {valid_count} properties validated successfully")
    
    # Check for missing optional fields
    missing_coords = sum(1 for p in properties if not p.coordinates)
    missing_details = sum(1 for p in properties if not p.property_details)
    
    if missing_coords:
        print(f"  Warning: {missing_coords} properties missing coordinates")
    if missing_details:
        print(f"  Warning: {missing_details} properties missing property details")
    
    return True

def get_unique_neighborhoods(properties: List[Property]) -> List[Neighborhood]:
    """Extract unique neighborhoods from properties"""
    neighborhoods = {}
    for prop in properties:
        if prop.neighborhood_id not in neighborhoods:
            neighborhoods[prop.neighborhood_id] = Neighborhood(
                id=prop.neighborhood_id,
                name=prop.neighborhood_id.replace('_', ' ').title(),
                city=prop.city or 'Unknown',
                state=prop.state or 'Unknown'
            )
    return list(neighborhoods.values())

def get_unique_features(properties: List[Property]) -> List[Feature]:
    """Extract all unique features from properties"""
    features_dict = {}
    for prop in properties:
        if prop.features:
            for feature_name in prop.features:
                if feature_name not in features_dict:
                    # Categorize features based on keywords
                    category = categorize_feature(feature_name)
                    features_dict[feature_name] = Feature(
                        name=feature_name,
                        category=category
                    )
    return list(features_dict.values())

def categorize_feature(feature_name: str) -> str:
    """Categorize a feature based on its name"""
    feature_lower = feature_name.lower()
    
    if any(word in feature_lower for word in ['view', 'vista', 'panoramic']):
        return 'View'
    elif any(word in feature_lower for word in ['kitchen', 'appliance', 'granite', 'marble']):
        return 'Kitchen'
    elif any(word in feature_lower for word in ['pool', 'spa', 'jacuzzi', 'hot tub']):
        return 'Recreation'
    elif any(word in feature_lower for word in ['garage', 'parking', 'carport']):
        return 'Parking'
    elif any(word in feature_lower for word in ['garden', 'yard', 'landscap', 'patio', 'deck']):
        return 'Outdoor'
    elif any(word in feature_lower for word in ['smart', 'security', 'alarm', 'camera']):
        return 'Technology'
    elif any(word in feature_lower for word in ['fireplace', 'ceiling', 'floor', 'window']):
        return 'Interior'
    else:
        return 'Other'

def get_unique_cities(properties: List[Property]) -> List[City]:
    """Extract unique cities from properties"""
    cities = {}
    for prop in properties:
        if prop.city and prop.city not in cities:
            cities[prop.city] = City(
                name=prop.city,
                state=prop.state or 'Unknown'
            )
    return list(cities.values())


def load_enhanced_property_data() -> Dict[str, Any]:
    """Load enhanced property data with features from JSON files"""
    base_path = Path(__file__).parent.parent.parent.parent / 'real_estate_data'
    
    # Load neighborhood data with lifestyle information
    neighborhoods_data = {}
    
    # Try to load SF neighborhoods
    try:
        sf_neighborhoods = load_json_file(base_path / 'neighborhoods_sf.json')
        for n in sf_neighborhoods:
            neighborhoods_data[n['neighborhood_id']] = n
        print(f"Loaded {len(sf_neighborhoods)} SF neighborhoods")
    except Exception as e:
        print(f"Warning: Could not load SF neighborhood data: {e}")
    
    # Try to load PC neighborhoods
    try:
        pc_neighborhoods = load_json_file(base_path / 'neighborhoods_pc.json')
        for n in pc_neighborhoods:
            neighborhoods_data[n['neighborhood_id']] = n
        print(f"Loaded {len(pc_neighborhoods)} PC neighborhoods")
    except Exception as e:
        print(f"Warning: Could not load PC neighborhood data: {e}")
    
    print(f"Total neighborhoods loaded: {len(neighborhoods_data)}")
    return neighborhoods_data


def load_wikipedia_data() -> Optional[pd.DataFrame]:
    """Load Wikipedia data directly from neighborhood JSON files"""
    try:
        # Load enhanced neighborhood data (which includes graph_metadata)
        neighborhoods_data = load_enhanced_property_data()
        
        wiki_relationships = []
        
        for neighborhood_id, neighborhood in neighborhoods_data.items():
            graph_metadata = neighborhood.get('graph_metadata', {})
            
            # Extract primary Wikipedia article
            primary_article = graph_metadata.get('primary_wiki_article')
            if primary_article and primary_article.get('page_id'):
                wiki_relationships.append({
                    'neighborhood_id': neighborhood_id,
                    'page_id': primary_article['page_id'],
                    'title': primary_article['title'],
                    'url': primary_article['url'],
                    'relationship_type': 'primary',
                    'confidence_score': primary_article.get('confidence', 0.5),
                    'summary': f"Primary Wikipedia article for {neighborhood['name']} neighborhood, providing comprehensive information about local history, demographics, notable landmarks, and cultural significance. This serves as the authoritative source for understanding the area's character and development."
                })
            
            # Extract related Wikipedia articles
            related_articles = graph_metadata.get('related_wiki_articles', [])
            for related in related_articles:
                if related.get('page_id'):
                    wiki_relationships.append({
                        'neighborhood_id': neighborhood_id,
                        'page_id': related['page_id'],
                        'title': related['title'],
                        'url': related['url'],
                        'relationship_type': related.get('relationship', 'related'),
                        'confidence_score': related.get('confidence', 0.5),
                        'summary': f"Related Wikipedia article for {neighborhood['name']}"
                    })
        
        if wiki_relationships:
            wiki_df = pd.DataFrame(wiki_relationships)
            print(f"Loaded {len(wiki_relationships)} Wikipedia relationships from JSON files")
            return wiki_df
        else:
            print("No Wikipedia relationships found in JSON files")
            return None
            
    except Exception as e:
        print(f"Error loading Wikipedia data from JSON: {e}")
        return None