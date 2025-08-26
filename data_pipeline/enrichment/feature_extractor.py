"""
Feature extraction from property data.

Simple module to extract and categorize property features.
"""

import logging
from typing import Dict, List, Optional
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    collect_set,
    explode,
    lower,
    trim,
    col,
    lit,
    count,
    concat,
    regexp_replace
)

from data_pipeline.models.graph_models import FeatureNode, FeatureCategory
from .base_extractor import BaseExtractor
from .id_generator import generate_feature_id

logger = logging.getLogger(__name__)


class FeatureExtractor(BaseExtractor):
    """Extract and categorize features from property data."""
    
    def _initialize(self) -> None:
        """Initialize feature categories mapping."""
        self.feature_categories = self._initialize_categories()
    
    def _initialize_categories(self) -> Dict[str, FeatureCategory]:
        """Initialize feature category mappings."""
        return {
            # Amenity features
            "pool": FeatureCategory.AMENITY,
            "gym": FeatureCategory.AMENITY,
            "spa": FeatureCategory.AMENITY,
            "sauna": FeatureCategory.AMENITY,
            "tennis": FeatureCategory.AMENITY,
            "concierge": FeatureCategory.AMENITY,
            "doorman": FeatureCategory.AMENITY,
            "community": FeatureCategory.AMENITY,
            
            # Structural features
            "hardwood": FeatureCategory.STRUCTURAL,
            "granite": FeatureCategory.STRUCTURAL,
            "marble": FeatureCategory.STRUCTURAL,
            "vaulted": FeatureCategory.STRUCTURAL,
            "crown": FeatureCategory.STRUCTURAL,
            "basement": FeatureCategory.STRUCTURAL,
            "attic": FeatureCategory.STRUCTURAL,
            "loft": FeatureCategory.STRUCTURAL,
            
            # Location features
            "waterfront": FeatureCategory.LOCATION,
            "corner": FeatureCategory.LOCATION,
            "cul-de-sac": FeatureCategory.LOCATION,
            "gated": FeatureCategory.LOCATION,
            
            # Appliance features
            "stainless": FeatureCategory.APPLIANCE,
            "dishwasher": FeatureCategory.APPLIANCE,
            "microwave": FeatureCategory.APPLIANCE,
            "refrigerator": FeatureCategory.APPLIANCE,
            "washer": FeatureCategory.APPLIANCE,
            "dryer": FeatureCategory.APPLIANCE,
            
            # Outdoor features
            "patio": FeatureCategory.OUTDOOR,
            "deck": FeatureCategory.OUTDOOR,
            "balcony": FeatureCategory.OUTDOOR,
            "garden": FeatureCategory.OUTDOOR,
            "yard": FeatureCategory.OUTDOOR,
            "landscap": FeatureCategory.OUTDOOR,
            
            # Parking features
            "garage": FeatureCategory.PARKING,
            "carport": FeatureCategory.PARKING,
            "driveway": FeatureCategory.PARKING,
            "parking": FeatureCategory.PARKING,
            
            # View features
            "view": FeatureCategory.VIEW,
            "panoramic": FeatureCategory.VIEW,
            "skyline": FeatureCategory.VIEW,
            "ocean": FeatureCategory.VIEW,
            "mountain": FeatureCategory.VIEW,
            "city view": FeatureCategory.VIEW,
            "water view": FeatureCategory.VIEW,
        }
    
    def categorize_feature(self, feature: str) -> FeatureCategory:
        """
        Categorize a feature based on keywords.
        
        Args:
            feature: Feature name
            
        Returns:
            Feature category
        """
        feature_lower = feature.lower()
        
        for keyword, category in self.feature_categories.items():
            if keyword in feature_lower:
                return category
        
        return FeatureCategory.OTHER
    
    def extract(self, properties_df: DataFrame) -> DataFrame:
        """
        Extract unique features from properties.
        
        Args:
            properties_df: DataFrame with properties containing features array
            
        Returns:
            DataFrame of unique features with categories
        """
        logger.info("Extracting features from properties")
        
        # Validate input
        if not self.validate_input_columns(properties_df, ["features"]):
            return self.create_empty_dataframe(FeatureNode)
        
        try:
            # Explode features array to get individual features
            features_df = properties_df.select(
                col("listing_id"),
                explode(col("features")).alias("feature_name")
            ).filter(
                col("feature_name").isNotNull()
            )
            
            # Normalize feature names
            features_df = features_df.withColumn(
                "feature_name_normalized",
                lower(trim(col("feature_name")))
            )
            
            # Count occurrences of each feature
            feature_counts = features_df.groupBy("feature_name_normalized").agg(
                count("*").alias("count"),
                collect_set("feature_name").alias("original_names")
            )
            
            # Create feature nodes
            feature_nodes = []
            for row in feature_counts.collect():
                feature_name = row["feature_name_normalized"]
                original_name = row["original_names"][0] if row["original_names"] else feature_name
                category = self.categorize_feature(feature_name)
                
                feature_node = FeatureNode(
                    id=generate_feature_id(feature_name),
                    name=original_name,
                    category=category,
                    count=row["count"]
                )
                feature_nodes.append(feature_node.model_dump())
            
            # Log statistics
            self.log_extraction_stats("feature", len(feature_nodes))
            
            # Convert to DataFrame
            return self.create_dataframe_from_models(feature_nodes, FeatureNode)
                
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return self.create_empty_dataframe(FeatureNode)
    
