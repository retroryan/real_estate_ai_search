"""
Real data sampling utilities for integration tests.

Loads and samples actual data from real estate JSON files and Wikipedia SQLite database
for use in ChromaDB integration tests.
"""

import os
import json
import sqlite3
import random
from typing import List, Dict, Any, Optional
from pathlib import Path

from ...models.enums import EntityType, SourceType
from ...utils.logging import get_logger
from ..models import DataSample, ValidationError

logger = get_logger(__name__)


class RealDataSampler:
    """
    Utility for sampling real data from project datasets.
    
    Provides methods to load and sample properties, neighborhoods, and Wikipedia articles
    with consistent data structures for testing.
    """
    
    def __init__(self, data_root_path: str = None):
        """
        Initialize real data sampler.
        
        Args:
            data_root_path: Root path to project data files
        """
        self.data_root_path = data_root_path or "."
        self.validation_errors: List[ValidationError] = []
        
        # Data caches
        self._properties_cache: Optional[List[Dict[str, Any]]] = None
        self._neighborhoods_cache: Optional[List[Dict[str, Any]]] = None
        self._wikipedia_articles_cache: Optional[List[Dict[str, Any]]] = None
        
        logger.info(f"Initialized RealDataSampler with data root: {self.data_root_path}")
    
    def load_property_samples(
        self,
        max_count: int = 50,
        include_edge_cases: bool = True,
        seed: Optional[int] = None
    ) -> List[DataSample]:
        """
        Load real estate property samples for testing.
        
        Args:
            max_count: Maximum number of properties to sample
            include_edge_cases: Whether to include edge case properties
            seed: Random seed for reproducible sampling
            
        Returns:
            List of DataSample objects for properties
        """
        logger.info(f"Loading {max_count} property samples (include_edge_cases={include_edge_cases})")
        
        if seed is not None:
            random.seed(seed)
        
        # Load property data if not cached
        if self._properties_cache is None:
            self._properties_cache = self._load_properties_from_files()
        
        if not self._properties_cache:
            logger.error("No properties loaded from data files")
            return []
        
        # Select samples with edge cases
        samples = []
        available_properties = self._properties_cache.copy()
        
        # Include specific edge cases if requested
        if include_edge_cases:
            edge_case_ids = ["prop-oak-125", "prop-coal-137"]  # From our analysis
            for prop in available_properties:
                if prop.get('listing_id') in edge_case_ids:
                    samples.append(self._create_property_sample(prop, is_edge_case=True))
                    if len(samples) >= max_count:
                        break
            
            # Remove edge cases from available pool
            available_properties = [
                p for p in available_properties 
                if p.get('listing_id') not in edge_case_ids
            ]
        
        # Add random samples to reach max_count
        remaining_count = max_count - len(samples)
        if remaining_count > 0:
            random_properties = random.sample(
                available_properties, 
                min(remaining_count, len(available_properties))
            )
            
            for prop in random_properties:
                samples.append(self._create_property_sample(prop))
        
        logger.info(f"Created {len(samples)} property samples")
        return samples
    
    def load_neighborhood_samples(
        self,
        max_count: int = 10,
        include_edge_cases: bool = True,
        seed: Optional[int] = None
    ) -> List[DataSample]:
        """
        Load neighborhood samples for testing.
        
        Args:
            max_count: Maximum number of neighborhoods to sample
            include_edge_cases: Whether to include edge case neighborhoods
            seed: Random seed for reproducible sampling
            
        Returns:
            List of DataSample objects for neighborhoods
        """
        logger.info(f"Loading {max_count} neighborhood samples (include_edge_cases={include_edge_cases})")
        
        if seed is not None:
            random.seed(seed)
        
        # Load neighborhood data if not cached
        if self._neighborhoods_cache is None:
            self._neighborhoods_cache = self._load_neighborhoods_from_files()
        
        if not self._neighborhoods_cache:
            logger.error("No neighborhoods loaded from data files")
            return []
        
        samples = []
        available_neighborhoods = self._neighborhoods_cache.copy()
        
        # Include specific edge cases if requested
        if include_edge_cases:
            edge_case_ids = ["sf-pac-heights-001", "pc-old-town-001"]  # From our analysis
            for neighborhood in available_neighborhoods:
                if neighborhood.get('neighborhood_id') in edge_case_ids:
                    samples.append(self._create_neighborhood_sample(neighborhood, is_edge_case=True))
                    if len(samples) >= max_count:
                        break
            
            # Remove edge cases from available pool
            available_neighborhoods = [
                n for n in available_neighborhoods 
                if n.get('neighborhood_id') not in edge_case_ids
            ]
        
        # Add random samples to reach max_count
        remaining_count = max_count - len(samples)
        if remaining_count > 0:
            random_neighborhoods = random.sample(
                available_neighborhoods, 
                min(remaining_count, len(available_neighborhoods))
            )
            
            for neighborhood in random_neighborhoods:
                samples.append(self._create_neighborhood_sample(neighborhood))
        
        logger.info(f"Created {len(samples)} neighborhood samples")
        return samples
    
    def load_wikipedia_samples(
        self,
        max_count: int = 25,
        include_edge_cases: bool = True,
        seed: Optional[int] = None
    ) -> List[DataSample]:
        """
        Load Wikipedia article samples for testing.
        
        Args:
            max_count: Maximum number of Wikipedia articles to sample
            include_edge_cases: Whether to include edge case articles
            seed: Random seed for reproducible sampling
            
        Returns:
            List of DataSample objects for Wikipedia articles
        """
        logger.info(f"Loading {max_count} Wikipedia samples (include_edge_cases={include_edge_cases})")
        
        if seed is not None:
            random.seed(seed)
        
        # Load Wikipedia data if not cached
        if self._wikipedia_articles_cache is None:
            self._wikipedia_articles_cache = self._load_wikipedia_from_database()
        
        if not self._wikipedia_articles_cache:
            logger.error("No Wikipedia articles loaded from database")
            return []
        
        samples = []
        available_articles = self._wikipedia_articles_cache.copy()
        
        # Include specific edge cases if requested  
        if include_edge_cases:
            edge_case_ids = [49728, 45186, 31920]  # San Francisco, Orem UT, UCSF from our analysis
            for article in available_articles:
                if article.get('page_id') in edge_case_ids:
                    samples.append(self._create_wikipedia_sample(article, is_edge_case=True))
                    if len(samples) >= max_count:
                        break
            
            # Remove edge cases from available pool
            available_articles = [
                a for a in available_articles 
                if a.get('page_id') not in edge_case_ids
            ]
        
        # Add random samples to reach max_count
        remaining_count = max_count - len(samples)
        if remaining_count > 0:
            random_articles = random.sample(
                available_articles, 
                min(remaining_count, len(available_articles))
            )
            
            for article in random_articles:
                samples.append(self._create_wikipedia_sample(article))
        
        logger.info(f"Created {len(samples)} Wikipedia samples")
        return samples
    
    def get_validation_errors(self) -> List[ValidationError]:
        """Get list of validation errors encountered during sampling."""
        return self.validation_errors.copy()
    
    def clear_caches(self) -> None:
        """Clear all data caches."""
        self._properties_cache = None
        self._neighborhoods_cache = None
        self._wikipedia_articles_cache = None
        logger.info("Cleared all data caches")
    
    # Private methods for data loading
    
    def _load_properties_from_files(self) -> List[Dict[str, Any]]:
        """Load properties from JSON files."""
        properties = []
        
        property_files = [
            "real_estate_data/properties_sf.json",
            "real_estate_data/properties_pc.json"
        ]
        
        for file_path in property_files:
            full_path = os.path.join(self.data_root_path, file_path)
            
            if not os.path.exists(full_path):
                error = ValidationError(
                    error_type="missing_data_file",
                    error_message=f"Property file not found: {full_path}",
                    is_critical=True
                )
                self.validation_errors.append(error)
                continue
            
            try:
                with open(full_path, 'r') as f:
                    file_properties = json.load(f)
                    
                # Add source file to each property
                for prop in file_properties:
                    prop['source_file'] = file_path
                    
                properties.extend(file_properties)
                logger.info(f"Loaded {len(file_properties)} properties from {file_path}")
                
            except Exception as e:
                error = ValidationError(
                    error_type="data_loading_error",
                    error_message=f"Failed to load properties from {full_path}: {e}",
                    context={"file_path": full_path, "error": str(e)},
                    is_critical=True
                )
                self.validation_errors.append(error)
        
        logger.info(f"Total properties loaded: {len(properties)}")
        return properties
    
    def _load_neighborhoods_from_files(self) -> List[Dict[str, Any]]:
        """Load neighborhoods from JSON files."""
        neighborhoods = []
        
        neighborhood_files = [
            "real_estate_data/neighborhoods_sf.json",
            "real_estate_data/neighborhoods_pc.json"
        ]
        
        for file_path in neighborhood_files:
            full_path = os.path.join(self.data_root_path, file_path)
            
            if not os.path.exists(full_path):
                error = ValidationError(
                    error_type="missing_data_file",
                    error_message=f"Neighborhood file not found: {full_path}",
                    is_critical=True
                )
                self.validation_errors.append(error)
                continue
            
            try:
                with open(full_path, 'r') as f:
                    file_neighborhoods = json.load(f)
                    
                # Add source file to each neighborhood
                for neighborhood in file_neighborhoods:
                    neighborhood['source_file'] = file_path
                    
                neighborhoods.extend(file_neighborhoods)
                logger.info(f"Loaded {len(file_neighborhoods)} neighborhoods from {file_path}")
                
            except Exception as e:
                error = ValidationError(
                    error_type="data_loading_error",
                    error_message=f"Failed to load neighborhoods from {full_path}: {e}",
                    context={"file_path": full_path, "error": str(e)},
                    is_critical=True
                )
                self.validation_errors.append(error)
        
        logger.info(f"Total neighborhoods loaded: {len(neighborhoods)}")
        return neighborhoods
    
    def _load_wikipedia_from_database(self) -> List[Dict[str, Any]]:
        """Load Wikipedia articles from SQLite database."""
        articles = []
        
        db_path = os.path.join(self.data_root_path, "data/wikipedia/wikipedia.db")
        
        if not os.path.exists(db_path):
            error = ValidationError(
                error_type="missing_data_file",
                error_message=f"Wikipedia database not found: {db_path}",
                is_critical=True
            )
            self.validation_errors.append(error)
            return articles
        
        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Query for articles with summaries
                cursor = conn.execute("""
                    SELECT 
                        a.pageid as page_id,
                        a.title,
                        a.extract,
                        a.latitude,
                        a.longitude,
                        a.relevance_score,
                        ps.short_summary,
                        ps.long_summary,
                        ps.key_topics,
                        ps.best_city,
                        ps.best_state,
                        ps.overall_confidence
                    FROM articles a
                    LEFT JOIN page_summaries ps ON a.pageid = ps.page_id
                    WHERE a.extract IS NOT NULL
                    ORDER BY a.relevance_score DESC
                    LIMIT 200
                """)
                
                for row in cursor.fetchall():
                    article_data = dict(row)
                    article_data['source_file'] = "data/wikipedia/wikipedia.db"
                    articles.append(article_data)
                
                logger.info(f"Loaded {len(articles)} Wikipedia articles from database")
                
        except Exception as e:
            error = ValidationError(
                error_type="data_loading_error", 
                error_message=f"Failed to load Wikipedia data from {db_path}: {e}",
                context={"db_path": db_path, "error": str(e)},
                is_critical=True
            )
            self.validation_errors.append(error)
        
        return articles
    
    # Private methods for creating samples
    
    def _create_property_sample(
        self,
        property_data: Dict[str, Any],
        is_edge_case: bool = False
    ) -> DataSample:
        """Create a DataSample from property data."""
        
        # Generate text content for embedding
        text_parts = []
        
        # Address
        if 'address' in property_data:
            addr = property_data['address']
            text_parts.append(f"{addr.get('street', '')}, {addr.get('city', '')}, {addr.get('state', '')}")
        
        # Property details
        if 'property_details' in property_data:
            details = property_data['property_details']
            text_parts.append(
                f"{details.get('bedrooms', 0)} bedroom, {details.get('bathrooms', 0)} bathroom "
                f"{details.get('property_type', 'property')} with {details.get('square_feet', 0)} sq ft"
            )
        
        # Price
        if 'listing_price' in property_data:
            text_parts.append(f"Listed at ${property_data['listing_price']:,}")
        
        # Description
        if 'description' in property_data:
            text_parts.append(property_data['description'])
        
        # Features
        if 'features' in property_data and property_data['features']:
            text_parts.append(f"Features: {', '.join(property_data['features'])}")
        
        text_content = ". ".join(text_parts)
        
        # Create metadata with correlation fields
        metadata = {
            'embedding_id': f"test_prop_{property_data.get('listing_id', 'unknown')}",
            'entity_type': EntityType.PROPERTY.value,
            'source_type': SourceType.PROPERTY_JSON.value,
            'listing_id': property_data.get('listing_id'),
            'source_file': property_data.get('source_file', ''),
            'text_hash': str(hash(text_content))
        }
        
        # Add additional fields for testing
        if 'coordinates' in property_data:
            metadata['latitude'] = property_data['coordinates'].get('latitude')
            metadata['longitude'] = property_data['coordinates'].get('longitude')
        
        if 'neighborhood_id' in property_data:
            metadata['neighborhood_id'] = property_data['neighborhood_id']
        
        return DataSample(
            entity_id=property_data.get('listing_id', 'unknown'),
            entity_type=EntityType.PROPERTY,
            source_type=SourceType.PROPERTY_JSON,
            text_content=text_content,
            metadata=metadata,
            expected_chunks=1,  # Properties typically don't need chunking
            is_edge_case=is_edge_case,
            has_coordinates='coordinates' in property_data,
            has_rich_metadata=len(property_data.get('features', [])) > 3
        )
    
    def _create_neighborhood_sample(
        self,
        neighborhood_data: Dict[str, Any],
        is_edge_case: bool = False
    ) -> DataSample:
        """Create a DataSample from neighborhood data."""
        
        # Generate text content for embedding
        text_parts = []
        
        # Name and location
        text_parts.append(f"{neighborhood_data.get('name', 'Unknown')} neighborhood in {neighborhood_data.get('city', '')}, {neighborhood_data.get('state', '')}")
        
        # Description
        if 'description' in neighborhood_data:
            text_parts.append(neighborhood_data['description'])
        
        # Amenities
        if 'amenities' in neighborhood_data and neighborhood_data['amenities']:
            text_parts.append(f"Amenities include: {', '.join(neighborhood_data['amenities'])}")
        
        # Lifestyle tags
        if 'lifestyle_tags' in neighborhood_data and neighborhood_data['lifestyle_tags']:
            text_parts.append(f"Lifestyle: {', '.join(neighborhood_data['lifestyle_tags'])}")
        
        # Characteristics
        if 'characteristics' in neighborhood_data:
            chars = neighborhood_data['characteristics']
            char_text = f"Walkability: {chars.get('walkability_score', 'N/A')}/10, Transit: {chars.get('transit_score', 'N/A')}/10"
            text_parts.append(char_text)
        
        text_content = ". ".join(text_parts)
        
        # Determine if this will need chunking (long descriptions)
        expected_chunks = 2 if len(text_content) > 800 else 1
        
        # Create metadata with correlation fields
        metadata = {
            'embedding_id': f"test_neighborhood_{neighborhood_data.get('neighborhood_id', 'unknown')}",
            'entity_type': EntityType.NEIGHBORHOOD.value,
            'source_type': SourceType.NEIGHBORHOOD_JSON.value,
            'neighborhood_id': neighborhood_data.get('neighborhood_id'),
            'neighborhood_name': neighborhood_data.get('name'),
            'source_file': neighborhood_data.get('source_file', ''),
            'text_hash': str(hash(text_content))
        }
        
        # Add additional fields for testing
        if 'coordinates' in neighborhood_data:
            metadata['latitude'] = neighborhood_data['coordinates'].get('latitude')
            metadata['longitude'] = neighborhood_data['coordinates'].get('longitude')
        
        return DataSample(
            entity_id=neighborhood_data.get('neighborhood_id', 'unknown'),
            entity_type=EntityType.NEIGHBORHOOD,
            source_type=SourceType.NEIGHBORHOOD_JSON,
            text_content=text_content,
            metadata=metadata,
            expected_chunks=expected_chunks,
            is_edge_case=is_edge_case,
            has_coordinates='coordinates' in neighborhood_data,
            has_rich_metadata=len(neighborhood_data.get('amenities', [])) > 5
        )
    
    def _create_wikipedia_sample(
        self,
        article_data: Dict[str, Any],
        is_edge_case: bool = False
    ) -> DataSample:
        """Create a DataSample from Wikipedia article data."""
        
        # Use extract or summary as text content
        text_content = ""
        
        if article_data.get('long_summary'):
            text_content = article_data['long_summary']
        elif article_data.get('short_summary'):
            text_content = article_data['short_summary']
        elif article_data.get('extract'):
            text_content = article_data['extract']
        else:
            text_content = f"Wikipedia article: {article_data.get('title', 'Unknown')}"
        
        # Determine chunking needs based on content length
        expected_chunks = max(1, len(text_content) // 1000)  # Rough estimate
        
        # Create metadata with correlation fields
        metadata = {
            'embedding_id': f"test_wiki_{article_data.get('page_id', 'unknown')}",
            'entity_type': EntityType.WIKIPEDIA_ARTICLE.value,
            'source_type': SourceType.WIKIPEDIA_DB.value,
            'page_id': article_data.get('page_id'),
            'title': article_data.get('title'),
            'source_file': article_data.get('source_file', ''),
            'text_hash': str(hash(text_content))
        }
        
        # Add additional fields for testing
        if article_data.get('latitude') is not None:
            metadata['latitude'] = article_data['latitude']
        if article_data.get('longitude') is not None:
            metadata['longitude'] = article_data['longitude']
        
        if article_data.get('best_city'):
            metadata['best_city'] = article_data['best_city']
        if article_data.get('best_state'):
            metadata['best_state'] = article_data['best_state']
        
        if article_data.get('overall_confidence'):
            metadata['confidence_score'] = article_data['overall_confidence']
        
        return DataSample(
            entity_id=str(article_data.get('page_id', 'unknown')),
            entity_type=EntityType.WIKIPEDIA_ARTICLE,
            source_type=SourceType.WIKIPEDIA_DB,
            text_content=text_content,
            metadata=metadata,
            expected_chunks=expected_chunks,
            is_edge_case=is_edge_case,
            has_coordinates=(article_data.get('latitude') is not None and article_data.get('longitude') is not None),
            has_rich_metadata=bool(article_data.get('key_topics') or article_data.get('best_city'))
        )