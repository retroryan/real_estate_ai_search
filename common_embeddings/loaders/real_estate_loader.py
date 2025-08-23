"""
Real estate data loader for properties and neighborhoods.

Adapted from real_estate_embed/pipeline.py _load_documents method.
"""

import json
from pathlib import Path
from typing import List, Tuple
from llama_index.core import Document

from ..utils.logging import get_logger
from ..models.interfaces import IDataLoader
from ..models.enums import EntityType


logger = get_logger(__name__)


class RealEstateLoader(IDataLoader):
    """
    Loads real estate data from JSON files.
    
    Follows patterns from real_estate_embed/pipeline.py.
    """
    
    def __init__(self, data_dir: Path):
        """
        Initialize real estate loader.
        
        Args:
            data_dir: Directory containing properties_*.json and neighborhoods_*.json
        """
        self.data_dir = data_dir
        self.property_documents = []
        self.neighborhood_documents = []
    
    def load_all(self) -> Tuple[List[Document], List[Document]]:
        """
        Load both properties and neighborhoods.
        
        Returns:
            Tuple of (property_documents, neighborhood_documents)
        """
        self._load_neighborhoods()
        self._load_properties()
        
        logger.info(f"Loaded {len(self.property_documents)} properties and {len(self.neighborhood_documents)} neighborhoods")
        return self.property_documents, self.neighborhood_documents
    
    def _load_neighborhoods(self) -> None:
        """Load neighborhoods from JSON files."""
        for neighborhoods_file in self.data_dir.glob("neighborhoods_*.json"):
            logger.info(f"Loading neighborhoods from {neighborhoods_file.name}")
            with open(neighborhoods_file, 'r') as f:
                neighborhoods = json.load(f)
                for n in neighborhoods:
                    # Create readable text from neighborhood data
                    text = f"{n['name']} neighborhood in {n['city']}, {n['state']}. "
                    text += f"Median price: ${n.get('median_home_price', 'N/A')}. "
                    
                    if 'description' in n:
                        text += n['description']
                    
                    if 'demographics' in n:
                        demo = n['demographics']
                        text += f" Population: {demo.get('population', 'N/A')}."
                        if 'median_age' in demo:
                            text += f" Median age: {demo['median_age']}."
                    
                    if 'amenities' in n:
                        text += f" Amenities: {', '.join(n['amenities'])}."
                    
                    # Create document with metadata
                    self.neighborhood_documents.append(Document(
                        text=text,
                        metadata={
                            "neighborhood_id": n.get('neighborhood_id', n['name']),
                            "neighborhood_name": n['name'],
                            "city": n['city'],
                            "state": n['state'],
                            "source_file": str(neighborhoods_file)
                        }
                    ))
    
    def _load_properties(self) -> None:
        """Load properties from JSON files."""
        for properties_file in self.data_dir.glob("properties_*.json"):
            logger.info(f"Loading properties from {properties_file.name}")
            with open(properties_file, 'r') as f:
                properties = json.load(f)
                for p in properties:
                    # Create readable text from property data
                    address = p.get('address', {})
                    text = f"{p.get('property_type', 'Property')} at "
                    text += f"{address.get('street', '')}, {address.get('city', '')}, {address.get('state', '')}. "
                    text += f"Price: ${p.get('price', 'N/A')}. "
                    text += f"{p.get('bedrooms', 0)} beds, {p.get('bathrooms', 0)} baths. "
                    text += f"{p.get('square_feet', 0)} sq ft. "
                    
                    if 'description' in p:
                        text += p['description']
                    
                    if 'features' in p:
                        text += f" Features: {', '.join(p['features'])}."
                    
                    # Create document with metadata
                    self.property_documents.append(Document(
                        text=text,
                        metadata={
                            "listing_id": p.get('listing_id', str(p.get('price', ''))),
                            "property_type": p.get('property_type', 'unknown'),
                            "neighborhood_id": p.get('neighborhood_id', ''),
                            "price": p.get('price', 0),
                            "source_file": str(properties_file)
                        }
                    ))
    
    # IDataLoader interface implementation (simplified for this demo)
    def load_documents(self):
        """Load documents generator (interface compliance)."""
        property_docs, neighborhood_docs = self.load_all()
        for doc in property_docs + neighborhood_docs:
            yield doc
    
    def get_source_type(self) -> str:
        """Get source type identifier."""
        return "real_estate_json"
    
    def validate_source(self) -> bool:
        """Validate data source exists."""
        return self.data_dir.exists() and any(self.data_dir.glob("*.json"))