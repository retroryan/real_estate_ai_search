"""
Relationship builder for creating graph database relationships.

This module creates relationship DataFrames between entities for the Neo4j graph database,
using the defined Pydantic models from graph_models.py.
"""

import logging
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    array_intersect,
    broadcast,
    coalesce,
    col,
    concat,
    count,
    expr,
    lit,
    lower,
    size,
    when,
)
from pyspark.sql.types import StringType, StructField, StructType

from data_pipeline.graph_models import (
    DescribesRelationship,
    LocatedInRelationship,
    NearRelationship,
    PartOfRelationship,
    RelationshipType,
    SimilarToRelationship,
)

logger = logging.getLogger(__name__)


class RelationshipBuilderConfig(BaseModel):
    """Configuration for relationship building operations."""
    
    enable_property_neighborhood: bool = Field(
        default=True,
        description="Create LOCATED_IN relationships between properties and neighborhoods"
    )
    
    enable_geographic_hierarchy: bool = Field(
        default=True,
        description="Create PART_OF relationships for geographic hierarchy"
    )
    
    enable_wikipedia_describes: bool = Field(
        default=True,
        description="Create DESCRIBES relationships from Wikipedia to entities"
    )
    
    enable_similarity_relationships: bool = Field(
        default=True,
        description="Create SIMILAR_TO relationships between entities"
    )
    
    similarity_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score to create relationship"
    )
    
    max_similar_properties: int = Field(
        default=10,
        description="Maximum similar properties per property"
    )
    
    max_similar_neighborhoods: int = Field(
        default=5,
        description="Maximum similar neighborhoods per neighborhood"
    )


class RelationshipBuilder:
    """
    Builds relationship DataFrames for the graph database.
    
    Creates various types of relationships between entities including
    geographic hierarchy, similarity, and Wikipedia descriptions.
    """
    
    def __init__(self, spark: SparkSession, config: Optional[RelationshipBuilderConfig] = None):
        """
        Initialize the relationship builder.
        
        Args:
            spark: Active SparkSession
            config: Relationship builder configuration
        """
        self.spark = spark
        self.config = config or RelationshipBuilderConfig()
        self.logger = logging.getLogger(__name__)
    
    def build_all_relationships(
        self,
        properties_df: Optional[DataFrame] = None,
        neighborhoods_df: Optional[DataFrame] = None,
        wikipedia_df: Optional[DataFrame] = None
    ) -> Dict[str, DataFrame]:
        """
        Build all configured relationships between entities.
        
        Args:
            properties_df: Property DataFrame
            neighborhoods_df: Neighborhood DataFrame
            wikipedia_df: Wikipedia DataFrame
            
        Returns:
            Dictionary of relationship DataFrames by type
        """
        relationships = {}
        
        # Property to Neighborhood relationships
        if self.config.enable_property_neighborhood and properties_df and neighborhoods_df:
            relationships["property_located_in"] = self.build_located_in_relationships(
                properties_df, neighborhoods_df
            )
            logger.info(f"Built {relationships['property_located_in'].count()} LOCATED_IN relationships")
        
        # Geographic hierarchy relationships
        if self.config.enable_geographic_hierarchy and neighborhoods_df:
            relationships["geographic_hierarchy"] = self.build_geographic_hierarchy(
                neighborhoods_df
            )
            logger.info(f"Built {relationships['geographic_hierarchy'].count()} PART_OF relationships")
        
        # Wikipedia DESCRIBES relationships
        if self.config.enable_wikipedia_describes and wikipedia_df:
            if neighborhoods_df:
                relationships["wikipedia_describes"] = self.build_describes_relationships(
                    wikipedia_df, neighborhoods_df
                )
                logger.info(f"Built {relationships['wikipedia_describes'].count()} DESCRIBES relationships")
        
        # Similarity relationships
        if self.config.enable_similarity_relationships:
            if properties_df:
                relationships["property_similarity"] = self.calculate_property_similarity(
                    properties_df
                )
                logger.info(f"Built {relationships['property_similarity'].count()} property SIMILAR_TO relationships")
            
            if neighborhoods_df:
                relationships["neighborhood_similarity"] = self.calculate_neighborhood_similarity(
                    neighborhoods_df
                )
                logger.info(f"Built {relationships['neighborhood_similarity'].count()} neighborhood SIMILAR_TO relationships")
        
        return relationships
    
    def build_located_in_relationships(
        self,
        properties_df: DataFrame,
        neighborhoods_df: DataFrame
    ) -> DataFrame:
        """
        Build LOCATED_IN relationships between properties and neighborhoods.
        
        Args:
            properties_df: Property DataFrame with neighborhood_id
            neighborhoods_df: Neighborhood DataFrame with neighborhood_id
            
        Returns:
            DataFrame of LocatedInRelationship records
        """
        # Filter to properties with neighborhood_id
        props_with_neighborhood = properties_df.filter(
            col("neighborhood_id").isNotNull()
        ).select(
            col("listing_id").alias("from_id"),
            col("neighborhood_id").alias("to_neighborhood_id"),
            col("city"),
            col("state")
        )
        
        # Join with neighborhoods to validate relationships
        valid_relationships = props_with_neighborhood.join(
            neighborhoods_df.select(
                col("neighborhood_id"),
                col("city").alias("n_city"),
                col("state").alias("n_state")
            ),
            props_with_neighborhood["to_neighborhood_id"] == neighborhoods_df["neighborhood_id"],
            "inner"
        )
        
        # Create relationship records
        located_in_df = valid_relationships.select(
            col("from_id"),
            col("neighborhood_id").alias("to_id"),
            lit(RelationshipType.LOCATED_IN.value).alias("relationship_type"),
            # Calculate confidence based on city/state match
            when(
                (col("city") == col("n_city")) & (col("state") == col("n_state")),
                lit(1.0)
            ).otherwise(lit(0.8)).alias("confidence"),
            lit(None).cast("float").alias("distance_meters")
        )
        
        return located_in_df
    
    def build_geographic_hierarchy(self, neighborhoods_df: DataFrame) -> DataFrame:
        """
        Build PART_OF relationships for geographic hierarchy.
        
        Creates relationships:
        - Neighborhood -> City
        - City -> County
        - County -> State
        
        Args:
            neighborhoods_df: Neighborhood DataFrame with city, county, state
            
        Returns:
            DataFrame of PartOfRelationship records
        """
        relationships = []
        
        # Neighborhood -> City relationships
        if "neighborhood_id" in neighborhoods_df.columns:
            neighborhood_to_city = neighborhoods_df.filter(
                col("neighborhood_id").isNotNull() & 
                col("city").isNotNull()
            ).select(
                col("neighborhood_id").alias("from_id"),
                concat(lower(col("city")), lit("_"), lower(col("state"))).alias("to_id"),
                lit(RelationshipType.PART_OF.value).alias("relationship_type")
            ).distinct()
            relationships.append(neighborhood_to_city)
        
        # City -> County relationships
        city_to_county = neighborhoods_df.filter(
            col("city").isNotNull() & 
            col("county").isNotNull() &
            col("state").isNotNull()
        ).select(
            concat(lower(col("city")), lit("_"), lower(col("state"))).alias("from_id"),
            concat(lower(col("county")), lit("_"), lower(col("state"))).alias("to_id"),
            lit(RelationshipType.PART_OF.value).alias("relationship_type")
        ).distinct()
        relationships.append(city_to_county)
        
        # County -> State relationships
        county_to_state = neighborhoods_df.filter(
            col("county").isNotNull() & 
            col("state").isNotNull()
        ).select(
            concat(lower(col("county")), lit("_"), lower(col("state"))).alias("from_id"),
            lower(col("state")).alias("to_id"),
            lit(RelationshipType.PART_OF.value).alias("relationship_type")
        ).distinct()
        relationships.append(county_to_state)
        
        # Union all relationship types
        if relationships:
            result = relationships[0]
            for df in relationships[1:]:
                result = result.unionByName(df, allowMissingColumns=True)
            return result
        else:
            # Return empty DataFrame with correct schema
            return self.spark.createDataFrame([], StructType([
                StructField("from_id", StringType(), False),
                StructField("to_id", StringType(), False),
                StructField("relationship_type", StringType(), False)
            ]))
    
    def build_describes_relationships(
        self,
        wikipedia_df: DataFrame,
        neighborhoods_df: DataFrame
    ) -> DataFrame:
        """
        Build DESCRIBES relationships from Wikipedia articles to neighborhoods/cities.
        
        Args:
            wikipedia_df: Wikipedia DataFrame with best_city, best_state
            neighborhoods_df: Neighborhood DataFrame
            
        Returns:
            DataFrame of DescribesRelationship records
        """
        # Prepare Wikipedia articles with location data
        wiki_with_location = wikipedia_df.filter(
            col("page_id").isNotNull() &
            (col("best_city").isNotNull() | col("best_county").isNotNull())
        ).select(
            col("page_id").cast("string").alias("from_id"),
            col("best_city"),
            col("best_county"),
            col("best_state"),
            coalesce(col("overall_confidence"), lit(0.5)).alias("confidence")
        )
        
        # Match to neighborhoods by city/state
        neighborhood_matches = wiki_with_location.join(
            neighborhoods_df.select(
                col("neighborhood_id"),
                col("city"),
                col("state")
            ),
            (wiki_with_location["best_city"] == neighborhoods_df["city"]) &
            (wiki_with_location["best_state"] == neighborhoods_df["state"]),
            "inner"
        ).select(
            col("from_id"),
            col("neighborhood_id").alias("to_id"),
            lit(RelationshipType.DESCRIBES.value).alias("relationship_type"),
            col("confidence"),
            lit("location").alias("match_type")
        )
        
        # Also create city-level DESCRIBES relationships
        city_matches = wiki_with_location.select(
            col("from_id"),
            concat(lower(col("best_city")), lit("_"), lower(col("best_state"))).alias("to_id"),
            lit(RelationshipType.DESCRIBES.value).alias("relationship_type"),
            col("confidence"),
            lit("city").alias("match_type")
        ).filter(col("best_city").isNotNull())
        
        # Union neighborhood and city relationships
        describes_df = neighborhood_matches.unionByName(city_matches, allowMissingColumns=True)
        
        return describes_df.distinct()
    
    def calculate_property_similarity(self, properties_df: DataFrame) -> DataFrame:
        """
        Calculate SIMILAR_TO relationships between properties.
        
        Similarity based on price, size, bedrooms, and features.
        
        Args:
            properties_df: Property DataFrame
            
        Returns:
            DataFrame of SimilarToRelationship records
        """
        # Prepare properties for comparison
        props = properties_df.filter(
            col("listing_id").isNotNull() & 
            col("price").isNotNull() &
            col("city").isNotNull()
        ).select(
            "listing_id", "price", "bedrooms", "bathrooms",
            "square_feet", "features", "city", "state"
        )
        
        # Self-join for pairwise comparison (avoiding duplicates)
        p1 = props.alias("p1")
        p2 = props.alias("p2")
        
        pairs = p1.join(
            p2,
            (p1["listing_id"] < p2["listing_id"]) &
            (p1["city"] == p2["city"]) &
            (p1["state"] == p2["state"]),
            "inner"
        )
        
        # Calculate similarity using SQL expression for efficiency
        similarity_df = pairs.select(
            p1["listing_id"].alias("from_id"),
            p2["listing_id"].alias("to_id"),
            lit(RelationshipType.SIMILAR_TO.value).alias("relationship_type"),
            
            # Combined similarity calculation
            expr("""
                -- Price similarity (40% weight)
                CASE 
                    WHEN abs(p1.price - p2.price) / p1.price < 0.2 THEN 0.4
                    WHEN abs(p1.price - p2.price) / p1.price < 0.4 THEN 0.2
                    ELSE 0.0
                END +
                -- Bedroom/bathroom similarity (30% weight)
                CASE
                    WHEN p1.bedrooms = p2.bedrooms AND abs(p1.bathrooms - p2.bathrooms) <= 0.5 THEN 0.3
                    WHEN abs(p1.bedrooms - p2.bedrooms) <= 1 THEN 0.15
                    ELSE 0.0
                END +
                -- Square footage similarity (30% weight)
                CASE
                    WHEN p1.square_feet IS NOT NULL AND p2.square_feet IS NOT NULL THEN
                        CASE
                            WHEN abs(p1.square_feet - p2.square_feet) / p1.square_feet < 0.15 THEN 0.3
                            WHEN abs(p1.square_feet - p2.square_feet) / p1.square_feet < 0.3 THEN 0.15
                            ELSE 0.0
                        END
                    ELSE 0.15
                END
            """).alias("similarity_score"),
            
            # Keep component scores for transparency
            expr("CASE WHEN abs(p1.price - p2.price) / p1.price < 0.2 THEN 1.0 ELSE 0.5 END").alias("price_similarity"),
            expr("CASE WHEN p1.square_feet IS NOT NULL THEN abs(p1.square_feet - p2.square_feet) / p1.square_feet ELSE NULL END").alias("size_similarity"),
            lit(None).cast("float").alias("feature_similarity")
        )
        
        # Filter by threshold
        return similarity_df.filter(
            col("similarity_score") >= self.config.similarity_threshold
        )
    
    def calculate_neighborhood_similarity(self, neighborhoods_df: DataFrame) -> DataFrame:
        """
        Calculate SIMILAR_TO relationships between neighborhoods.
        
        Similarity based on median price, walkability, and lifestyle.
        
        Args:
            neighborhoods_df: Neighborhood DataFrame
            
        Returns:
            DataFrame of SimilarToRelationship records
        """
        # Prepare neighborhoods for comparison
        neighborhoods = neighborhoods_df.filter(
            col("neighborhood_id").isNotNull()
        ).select(
            "neighborhood_id", "median_home_price", "walkability_score",
            "transit_score", "lifestyle_tags", "state"
        )
        
        # Self-join for pairwise comparison
        n1 = neighborhoods.alias("n1")
        n2 = neighborhoods.alias("n2")
        
        pairs = n1.join(
            n2,
            (n1["neighborhood_id"] < n2["neighborhood_id"]) &
            (n1["state"] == n2["state"]),
            "inner"
        )
        
        # Calculate similarity efficiently using SQL
        similarity_df = pairs.select(
            n1["neighborhood_id"].alias("from_id"),
            n2["neighborhood_id"].alias("to_id"),
            lit(RelationshipType.SIMILAR_TO.value).alias("relationship_type"),
            
            # Combined similarity score
            expr("""
                -- Price similarity (50% weight)
                CASE
                    WHEN n1.median_home_price IS NOT NULL AND n2.median_home_price IS NOT NULL THEN
                        CASE
                            WHEN abs(n1.median_home_price - n2.median_home_price) / n1.median_home_price < 0.2 THEN 0.5
                            WHEN abs(n1.median_home_price - n2.median_home_price) / n1.median_home_price < 0.4 THEN 0.25
                            ELSE 0.0
                        END
                    ELSE 0.25
                END +
                -- Walkability similarity (25% weight)
                CASE
                    WHEN n1.walkability_score IS NOT NULL AND n2.walkability_score IS NOT NULL THEN
                        0.25 * (1.0 - least(abs(n1.walkability_score - n2.walkability_score) / 10.0, 1.0))
                    ELSE 0.125
                END +
                -- Transit similarity (25% weight)
                CASE
                    WHEN n1.transit_score IS NOT NULL AND n2.transit_score IS NOT NULL THEN
                        0.25 * (1.0 - least(abs(n1.transit_score - n2.transit_score) / 10.0, 1.0))
                    ELSE 0.125
                END
            """).alias("similarity_score"),
            
            # Component scores
            expr("""
                CASE
                    WHEN n1.median_home_price IS NOT NULL AND n2.median_home_price IS NOT NULL 
                    THEN 1.0 - least(abs(n1.median_home_price - n2.median_home_price) / n1.median_home_price, 1.0)
                    ELSE 0.5
                END
            """).alias("price_similarity"),
            lit(None).cast("float").alias("feature_similarity"),
            lit(None).cast("float").alias("size_similarity")
        )
        
        # Filter by threshold
        return similarity_df.filter(
            col("similarity_score") >= self.config.similarity_threshold
        )
    
    def get_relationship_statistics(self, relationships: Dict[str, DataFrame]) -> Dict:
        """
        Calculate statistics about created relationships.
        
        Args:
            relationships: Dictionary of relationship DataFrames
            
        Returns:
            Dictionary of statistics
        """
        stats = {}
        
        for rel_type, df in relationships.items():
            if df is not None:
                count = df.count()
                stats[rel_type] = {
                    "count": count,
                    "columns": df.columns
                }
                
                # Add specific statistics for similarity relationships
                if "similarity_score" in df.columns:
                    score_stats = df.select(
                        expr("avg(similarity_score) as avg_score"),
                        expr("min(similarity_score) as min_score"),
                        expr("max(similarity_score) as max_score")
                    ).collect()[0]
                    
                    stats[rel_type].update({
                        "avg_similarity": float(score_stats["avg_score"]) if score_stats["avg_score"] else 0,
                        "min_similarity": float(score_stats["min_score"]) if score_stats["min_score"] else 0,
                        "max_similarity": float(score_stats["max_score"]) if score_stats["max_score"] else 0
                    })
        
        return stats