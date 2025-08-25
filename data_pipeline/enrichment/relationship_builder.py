"""
Relationship builder for creating graph database relationships.

This module creates relationship DataFrames between entities for the Neo4j graph database,
using the defined Pydantic models from graph_models.py.
"""

import logging
from typing import Dict, Optional

from pydantic import BaseModel, Field
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    abs,
    array_intersect,
    broadcast,
    coalesce,
    col,
    concat,
    count,
    expr,
    least,
    lit,
    lower,
    size,
    when,
)
from data_pipeline.models.graph_models import (
    DescribesRelationship,
    LocatedInRelationship,
    NearRelationship,
    PartOfRelationship,
    RelationshipType,
    SimilarToRelationship,
)
from data_pipeline.models.spark_models import Relationship

logger = logging.getLogger(__name__)


class RelationshipBuilder:
    """
    Builds relationship DataFrames for the graph database.
    
    Creates various types of relationships between entities including
    geographic hierarchy, similarity, and Wikipedia descriptions.
    """
    
    def __init__(self, spark: SparkSession):
        """
        Initialize the relationship builder.
        
        Args:
            spark: Active SparkSession
        """
        self.spark = spark
    
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
        
        # Property to Neighborhood relationships - always enabled if both dataframes exist
        if properties_df and neighborhoods_df:
            relationships["property_located_in"] = self.build_located_in_relationships(
                properties_df, neighborhoods_df
            )
            logger.info(f"Built {relationships['property_located_in'].count()} LOCATED_IN relationships")
        
        # Geographic hierarchy relationships - always enabled if neighborhoods dataframe exists
        if neighborhoods_df:
            relationships["geographic_hierarchy"] = self.build_geographic_hierarchy(
                neighborhoods_df
            )
            logger.info(f"Built {relationships['geographic_hierarchy'].count()} PART_OF relationships")
        
        # Wikipedia DESCRIBES relationships - always enabled if both dataframes exist
        if wikipedia_df and neighborhoods_df:
            relationships["wikipedia_describes"] = self.build_describes_relationships(
                wikipedia_df, neighborhoods_df
            )
            logger.info(f"Built {relationships['wikipedia_describes'].count()} DESCRIBES relationships")
        
        # Similarity relationships - always enabled
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
        neighborhoods_for_join = neighborhoods_df.select(
            col("neighborhood_id"),
            col("city").alias("n_city"),
            col("state").alias("n_state")
        ).alias("n")  # Alias the DataFrame to avoid ambiguity
        
        valid_relationships = props_with_neighborhood.alias("p").join(
            neighborhoods_for_join,
            col("p.to_neighborhood_id") == col("n.neighborhood_id"),
            "inner"
        )
        
        # Create relationship records
        located_in_df = valid_relationships.select(
            col("p.from_id"),
            col("n.neighborhood_id").alias("to_id"),
            lit(RelationshipType.LOCATED_IN.value).alias("relationship_type"),
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
            return self.spark.createDataFrame([], schema=Relationship.spark_schema())
    
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
            col("best_city").isNotNull()
        ).select(
            col("page_id").cast("string").alias("from_id"),
            col("best_city"),
            col("best_state")
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
        # Use listing_price if price doesn't exist, handle nested property_details
        price_col = "listing_price" if "listing_price" in properties_df.columns else "price"
        
        # Extract fields from nested structures if needed
        prep_df = properties_df
        if "property_details.bedrooms" in prep_df.columns:
            prep_df = prep_df.withColumn("bedrooms", col("property_details.bedrooms"))
            prep_df = prep_df.withColumn("bathrooms", col("property_details.bathrooms"))
            prep_df = prep_df.withColumn("square_feet", col("property_details.square_feet"))
        if "address.city" in prep_df.columns:
            prep_df = prep_df.withColumn("city", col("address.city"))
            prep_df = prep_df.withColumn("state", col("address.state"))
        
        # Prepare properties for comparison and alias immediately
        p1 = prep_df.filter(
            col("listing_id").isNotNull() & 
            col(price_col).isNotNull() &
            col("city").isNotNull()
        ).select(
            col("listing_id"),
            col(price_col).alias("price"),
            col("bedrooms"), col("bathrooms"),
            col("square_feet"), col("features"), col("city"), col("state")
        ).alias("p1")
        
        # Create second alias for self-join
        p2 = prep_df.filter(
            col("listing_id").isNotNull() & 
            col(price_col).isNotNull() &
            col("city").isNotNull()
        ).select(
            col("listing_id"),
            col(price_col).alias("price"),
            col("bedrooms"), col("bathrooms"),
            col("square_feet"), col("features"), col("city"), col("state")
        ).alias("p2")
        
        pairs = p1.join(
            p2,
            (p1["listing_id"] < p2["listing_id"]) &
            (p1["city"] == p2["city"]) &
            (p1["state"] == p2["state"]),
            "inner"
        )
        
        # Calculate similarity using column references to avoid ambiguity
        similarity_df = pairs.select(
            p1["listing_id"].alias("from_id"),
            p2["listing_id"].alias("to_id"),
            lit(RelationshipType.SIMILAR_TO.value).alias("relationship_type"),
            
            # Combined similarity calculation using proper column references
            (
                # Price similarity (40% weight)
                when(
                    abs(p1["price"] - p2["price"]) / p1["price"] < 0.2, lit(0.4)
                ).when(
                    abs(p1["price"] - p2["price"]) / p1["price"] < 0.4, lit(0.2)
                ).otherwise(lit(0.0)) +
                
                # Bedroom/bathroom similarity (30% weight)
                when(
                    (p1["bedrooms"] == p2["bedrooms"]) & (abs(p1["bathrooms"] - p2["bathrooms"]) <= 0.5), lit(0.3)
                ).when(
                    abs(p1["bedrooms"] - p2["bedrooms"]) <= 1, lit(0.15)
                ).otherwise(lit(0.0)) +
                
                # Square footage similarity (30% weight)
                when(
                    p1["square_feet"].isNotNull() & p2["square_feet"].isNotNull(),
                    when(
                        abs(p1["square_feet"] - p2["square_feet"]) / p1["square_feet"] < 0.15, lit(0.3)
                    ).when(
                        abs(p1["square_feet"] - p2["square_feet"]) / p1["square_feet"] < 0.3, lit(0.15)
                    ).otherwise(lit(0.0))
                ).otherwise(lit(0.15))
            ).alias("similarity_score"),
            
            # Keep component scores for transparency
            when(
                abs(p1["price"] - p2["price"]) / p1["price"] < 0.2, lit(1.0)
            ).otherwise(lit(0.5)).alias("price_similarity"),
            when(
                p1["square_feet"].isNotNull(),
                abs(p1["square_feet"] - p2["square_feet"]) / p1["square_feet"]
            ).otherwise(lit(None)).alias("size_similarity"),
            lit(None).cast("float").alias("feature_similarity")
        )
        
        # Filter by threshold
        return similarity_df.filter(
            col("similarity_score") >= 0.8
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
        # Prepare neighborhoods for comparison and alias immediately
        n1 = neighborhoods_df.filter(
            col("neighborhood_id").isNotNull()
        ).select(
            "neighborhood_id", "median_home_price", "walkability_score",
            "transit_score", "lifestyle_tags", "state"
        ).alias("n1")
        
        # Create second alias for self-join
        n2 = neighborhoods_df.filter(
            col("neighborhood_id").isNotNull()
        ).select(
            "neighborhood_id", "median_home_price", "walkability_score",
            "transit_score", "lifestyle_tags", "state"
        ).alias("n2")
        
        pairs = n1.join(
            n2,
            (n1["neighborhood_id"] < n2["neighborhood_id"]) &
            (n1["state"] == n2["state"]),
            "inner"
        )
        
        # Calculate similarity using column references to avoid ambiguity
        similarity_df = pairs.select(
            n1["neighborhood_id"].alias("from_id"),
            n2["neighborhood_id"].alias("to_id"),
            lit(RelationshipType.SIMILAR_TO.value).alias("relationship_type"),
            
            # Combined similarity score using proper column references
            (
                # Price similarity (50% weight)
                when(
                    n1["median_home_price"].isNotNull() & n2["median_home_price"].isNotNull(),
                    when(
                        abs(n1["median_home_price"] - n2["median_home_price"]) / n1["median_home_price"] < 0.2, lit(0.5)
                    ).when(
                        abs(n1["median_home_price"] - n2["median_home_price"]) / n1["median_home_price"] < 0.4, lit(0.25)
                    ).otherwise(lit(0.0))
                ).otherwise(lit(0.25)) +
                
                # Walkability similarity (25% weight)
                when(
                    n1["walkability_score"].isNotNull() & n2["walkability_score"].isNotNull(),
                    lit(0.25) * (lit(1.0) - least(abs(n1["walkability_score"] - n2["walkability_score"]) / lit(10.0), lit(1.0)))
                ).otherwise(lit(0.125)) +
                
                # Transit similarity (25% weight)
                when(
                    n1["transit_score"].isNotNull() & n2["transit_score"].isNotNull(),
                    lit(0.25) * (lit(1.0) - least(abs(n1["transit_score"] - n2["transit_score"]) / lit(10.0), lit(1.0)))
                ).otherwise(lit(0.125))
            ).alias("similarity_score"),
            
            # Component scores
            when(
                n1["median_home_price"].isNotNull() & n2["median_home_price"].isNotNull(),
                lit(1.0) - least(abs(n1["median_home_price"] - n2["median_home_price"]) / n1["median_home_price"], lit(1.0))
            ).otherwise(lit(0.5)).alias("price_similarity"),
            lit(None).cast("float").alias("feature_similarity"),
            lit(None).cast("float").alias("size_similarity")
        )
        
        # Filter by threshold
        return similarity_df.filter(
            col("similarity_score") >= 0.8
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