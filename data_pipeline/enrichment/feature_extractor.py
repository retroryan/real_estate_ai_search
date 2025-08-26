"""
Feature extraction from property data.

Clean, Pydantic-based feature extractor for property features.
"""

import logging
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    collect_set, explode, lower, trim, col, lit,
    count, concat, regexp_replace
)

from data_pipeline.models.graph_models import FeatureNode, FeatureCategory
from data_pipeline.enrichment.id_generator import generate_feature_id

logger = logging.getLogger(__name__)


class FeatureExtractor(BaseModel):
    """Extract and categorize features from property data."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    spark: SparkSession
    feature_categories: Dict[str, FeatureCategory] = {
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
        "water view": FeatureCategory.VIEW
    }
    
    def __init__(self, spark: SparkSession, **kwargs):
        """
        Initialize the feature extractor.
        
        Args:
            spark: Active SparkSession
        """
        super().__init__(spark=spark, **kwargs)
    
    def extract(self, properties_df: DataFrame) -> DataFrame:
        """
        Extract unique features from properties.
        
        Args:
            properties_df: DataFrame containing properties with features column
            
        Returns:
            DataFrame of FeatureNode records
        """
        logger.info("Extracting features from properties")
        
        # Explode features array to get individual features
        features_df = properties_df.select(
            explode(col("features")).alias("feature")
        ).select(
            trim(lower(col("feature"))).alias("feature")
        ).filter(
            col("feature").isNotNull()
        ).distinct()
        
        # Count occurrences of each feature
        feature_counts = properties_df.select(
            explode(col("features")).alias("feature")
        ).select(
            trim(lower(col("feature"))).alias("feature")
        ).groupBy("feature").agg(
            count("*").alias("count")
        )
        
        # Join counts with distinct features
        features_with_counts = features_df.join(
            feature_counts,
            features_df["feature"] == feature_counts["feature"],
            "left"
        ).select(
            features_df["feature"],
            feature_counts["count"]
        )
        
        # Create FeatureNode records
        feature_nodes = []
        try:
            for row in features_with_counts.collect():
                feature_name = row["feature"]
                
                # Determine category
                category = self._categorize_feature(feature_name)
                
                feature_node = FeatureNode(
                    id=generate_feature_id(feature_name),
                    name=feature_name,
                    category=category,
                    description=f"Property feature: {feature_name}",
                    count=row["count"] or 1
                )
                feature_nodes.append(feature_node.model_dump())
                
        except Exception as e:
            logger.error(f"Error creating feature nodes: {e}")
        
        if feature_nodes:
            logger.info(f"Created {len(feature_nodes)} feature nodes")
            return self.spark.createDataFrame(feature_nodes, schema=FeatureNode.spark_schema())
        else:
            logger.warning("No features extracted")
            return self.spark.createDataFrame([], FeatureNode.spark_schema())
    
    def _categorize_feature(self, feature: str) -> FeatureCategory:
        """
        Categorize a feature based on keywords.
        
        Args:
            feature: Feature name to categorize
            
        Returns:
            FeatureCategory enum value
        """
        feature_lower = feature.lower()
        
        # Check for exact matches or partial matches
        for keyword, category in self.feature_categories.items():
            if keyword in feature_lower:
                return category
        
        # Default to OTHER if no match
        return FeatureCategory.OTHER