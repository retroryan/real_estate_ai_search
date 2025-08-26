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
    explode,
    expr,
    least,
    lit,
    lower,
    size,
    when,
)
from data_pipeline.models.graph_models import (
    DescribesRelationship,
    HasFeatureRelationship,
    InCountyRelationship,
    InPriceRangeRelationship,
    InTopicClusterRelationship,
    LocatedInRelationship,
    NearRelationship,
    OfTypeRelationship,
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
            logger.info("✓ Built LOCATED_IN relationships")
        
        # Geographic hierarchy relationships - always enabled if neighborhoods dataframe exists
        if neighborhoods_df:
            relationships["geographic_hierarchy"] = self.build_geographic_hierarchy(
                neighborhoods_df
            )
            logger.info("✓ Built PART_OF relationships")
        
        # Wikipedia DESCRIBES relationships - always enabled if both dataframes exist
        if wikipedia_df and neighborhoods_df:
            relationships["wikipedia_describes"] = self.build_describes_relationships(
                wikipedia_df, neighborhoods_df
            )
            logger.info("✓ Built DESCRIBES relationships")
        
        # Similarity relationships - always enabled
        if properties_df:
            relationships["property_similarity"] = self.calculate_property_similarity(
                properties_df
            )
            logger.info("✓ Built property SIMILAR_TO relationships")
        
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
            col("listing_price").isNotNull() &
            col("city").isNotNull()
        ).select(
            col("listing_id"),
            col("listing_price").alias("price"),
            col("bedrooms"), col("bathrooms"),
            col("square_feet"), col("features"), col("city"), col("state")
        ).alias("p1")
        
        # Create second alias for self-join
        p2 = prep_df.filter(
            col("listing_id").isNotNull() & 
            col("listing_price").isNotNull() &
            col("city").isNotNull()
        ).select(
            col("listing_id"),
            col("listing_price").alias("price"),
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
    
    def build_has_feature_relationships(
        self,
        properties_df: DataFrame,
        features_df: DataFrame
    ) -> DataFrame:
        """
        Build HAS_FEATURE relationships between properties and features.
        
        Args:
            properties_df: Property DataFrame with features array
            features_df: Feature node DataFrame
            
        Returns:
            DataFrame of HasFeatureRelationship records
        """
        # Extract property-feature pairs
        property_features = properties_df.filter(
            col("listing_id").isNotNull() &
            col("features").isNotNull()
        ).select(
            col("listing_id"),
            explode(col("features")).alias("feature_name")
        )
        
        # Normalize feature names for matching
        property_features = property_features.withColumn(
            "feature_normalized",
            lower(col("feature_name"))
        )
        
        # Join with feature nodes (use "id" field from FeatureNode)
        features_for_join = features_df.select(
            col("id").alias("feature_id"),
            lower(col("name")).alias("feature_normalized")
        )
        
        matched = property_features.join(
            broadcast(features_for_join),
            "feature_normalized",
            "inner"
        )
        
        # Create relationship records
        has_feature_df = matched.select(
            col("listing_id").alias("from_id"),
            col("feature_id").alias("to_id"),
            lit(RelationshipType.HAS_FEATURE.value).alias("relationship_type"),
            lit(False).alias("is_primary"),  # Could enhance with logic to determine primary features
            lit(True).alias("verified")
        ).distinct()
        
        logger.info(f"Created {has_feature_df.count()} HAS_FEATURE relationships")
        return has_feature_df
    
    def build_of_type_relationships(
        self,
        properties_df: DataFrame,
        property_types_df: DataFrame
    ) -> DataFrame:
        """
        Build OF_TYPE relationships between properties and property types.
        
        Args:
            properties_df: Property DataFrame with property_type field
            property_types_df: PropertyType node DataFrame
            
        Returns:
            DataFrame of OfTypeRelationship records
        """
        # Extract property types from properties
        props_with_type = properties_df.filter(
            col("listing_id").isNotNull() &
            col("property_type").isNotNull()
        ).select(
            col("listing_id"),
            col("property_type")
        )
        
        # Join with property type nodes (use "id" field from PropertyTypeNode)
        type_nodes = property_types_df.select(
            col("id").alias("property_type_id"),
            col("name").alias("type_name")
        )
        
        matched = props_with_type.join(
            broadcast(type_nodes),
            props_with_type["property_type"] == type_nodes["type_name"],
            "inner"
        )
        
        # Create relationship records
        of_type_df = matched.select(
            col("listing_id").alias("from_id"),
            col("property_type_id").alias("to_id"),
            lit(RelationshipType.OF_TYPE.value).alias("relationship_type"),
            lit(1.0).alias("confidence"),
            lit(True).alias("is_primary")
        ).distinct()
        
        logger.info(f"Created {of_type_df.count()} OF_TYPE relationships")
        return of_type_df
    
    def build_in_price_range_relationships(
        self,
        properties_df: DataFrame,
        price_ranges_df: DataFrame
    ) -> DataFrame:
        """
        Build IN_PRICE_RANGE relationships between properties and price ranges.
        
        Args:
            properties_df: Property DataFrame with listing_price
            price_ranges_df: PriceRange node DataFrame
            
        Returns:
            DataFrame of InPriceRangeRelationship records
        """
        # Filter properties with valid prices
        props_with_price = properties_df.filter(
            col("listing_id").isNotNull() &
            col("listing_price").isNotNull() &
            (col("listing_price") > 0)
        ).select(
            col("listing_id"),
            col("listing_price")
        )
        
        # Cross join with price ranges to find matching range
        # Note: Using broadcast for small price_ranges_df
        price_ranges = broadcast(price_ranges_df.select(
            col("id").alias("price_range_id"),
            col("min_price"),
            col("max_price")
        ))
        
        # Find matching price range for each property
        matched = props_with_price.crossJoin(price_ranges).filter(
            (col("listing_price") >= col("min_price")) &
            (col("listing_price") < col("max_price"))
        )
        
        # Calculate percentile within range
        in_range_df = matched.select(
            col("listing_id").alias("from_id"),
            col("price_range_id").alias("to_id"),
            lit(RelationshipType.IN_PRICE_RANGE.value).alias("relationship_type"),
            ((col("listing_price") - col("min_price")) / 
             (col("max_price") - col("min_price"))).alias("price_percentile"),
            col("listing_price").alias("actual_price")
        ).distinct()
        
        logger.info(f"Created {in_range_df.count()} IN_PRICE_RANGE relationships")
        return in_range_df
    
    def build_in_county_relationships(
        self,
        entities_df: DataFrame,
        counties_df: DataFrame,
        entity_type: str = "neighborhood"
    ) -> DataFrame:
        """
        Build IN_COUNTY relationships for geographic hierarchy.
        
        Args:
            entities_df: DataFrame with county field (neighborhoods or cities)
            counties_df: County node DataFrame
            entity_type: Type of entity (neighborhood or city)
            
        Returns:
            DataFrame of InCountyRelationship records
        """
        # Determine ID field based on entity type
        id_field = "neighborhood_id" if entity_type == "neighborhood" else "city_id"
        
        # Filter entities with county information
        entities_with_county = entities_df.filter(
            col(id_field).isNotNull() &
            col("county").isNotNull() &
            col("state").isNotNull()
        ).select(
            col(id_field).alias("entity_id"),
            col("county"),
            col("state")
        )
        
        # Join with county nodes (use "id" field from CountyNode)
        county_nodes = counties_df.select(
            col("id").alias("county_id"),
            col("name").alias("county_name"),
            col("state").alias("county_state")
        )
        
        matched = entities_with_county.join(
            broadcast(county_nodes),
            (lower(entities_with_county["county"]) == lower(county_nodes["county_name"])) &
            (lower(entities_with_county["state"]) == lower(county_nodes["county_state"])),
            "inner"
        )
        
        # Create relationship records
        in_county_df = matched.select(
            col("entity_id").alias("from_id"),
            col("county_id").alias("to_id"),
            lit(RelationshipType.IN_COUNTY.value).alias("relationship_type"),
            lit(entity_type).alias("hierarchy_level")
        ).distinct()
        
        logger.info(f"Created {in_county_df.count()} IN_COUNTY relationships for {entity_type}")
        return in_county_df
    
    def build_in_topic_cluster_relationships(
        self,
        entities_df: DataFrame,
        topic_clusters_df: DataFrame,
        entity_type: str,
        topic_field: str = "key_topics"
    ) -> DataFrame:
        """
        Build IN_TOPIC_CLUSTER relationships between entities and topic clusters.
        
        Args:
            entities_df: Entity DataFrame with topics (properties, neighborhoods, or wikipedia)
            topic_clusters_df: TopicCluster node DataFrame
            entity_type: Type of entity (property, neighborhood, wikipedia)
            topic_field: Field containing topics in entity DataFrame
            
        Returns:
            DataFrame of InTopicClusterRelationship records
        """
        # Determine ID field based on entity type
        id_fields = {
            "property": "listing_id",
            "neighborhood": "neighborhood_id",
            "wikipedia": "page_id"
        }
        id_field = id_fields.get(entity_type, "entity_id")
        
        # Filter entities with topics
        entities_with_topics = entities_df.filter(
            col(id_field).isNotNull() &
            col(topic_field).isNotNull() &
            (expr(f"size({topic_field})") > 0)
        ).select(
            col(id_field).alias("entity_id"),
            col(topic_field).alias("entity_topics")
        )
        
        # Get topic clusters (use "id" field from TopicClusterNode)
        clusters = topic_clusters_df.select(
            col("id").alias("topic_cluster_id"),
            col("topics").alias("cluster_topics")
        )
        
        # Cross join to find matching topics
        joined = entities_with_topics.crossJoin(broadcast(clusters))
        
        # Calculate relevance based on topic overlap
        matched = joined.withColumn(
            "common_topics",
            expr("size(array_intersect(entity_topics, cluster_topics))")
        ).filter(
            col("common_topics") > 0
        )
        
        # Calculate relevance score
        in_cluster_df = matched.withColumn(
            "relevance_score",
            col("common_topics") / expr("greatest(size(entity_topics), size(cluster_topics))")
        ).select(
            col("entity_id").alias("from_id"),
            col("topic_cluster_id").alias("to_id"),
            lit(RelationshipType.IN_TOPIC_CLUSTER.value).alias("relationship_type"),
            col("relevance_score"),
            lit(entity_type).alias("extraction_source"),
            when(col("relevance_score") >= 0.5, lit(0.8))
            .when(col("relevance_score") >= 0.3, lit(0.6))
            .otherwise(lit(0.4)).alias("confidence")
        ).distinct()
        
        logger.info(f"Created {in_cluster_df.count()} IN_TOPIC_CLUSTER relationships for {entity_type}")
        return in_cluster_df
    
    def build_extended_relationships(
        self,
        properties_df: Optional[DataFrame] = None,
        neighborhoods_df: Optional[DataFrame] = None,
        wikipedia_df: Optional[DataFrame] = None,
        features_df: Optional[DataFrame] = None,
        property_types_df: Optional[DataFrame] = None,
        price_ranges_df: Optional[DataFrame] = None,
        counties_df: Optional[DataFrame] = None,
        topic_clusters_df: Optional[DataFrame] = None
    ) -> Dict[str, DataFrame]:
        """
        Build extended relationships for new entity types.
        
        Args:
            properties_df: Property DataFrame
            neighborhoods_df: Neighborhood DataFrame
            wikipedia_df: Wikipedia DataFrame
            features_df: Feature node DataFrame
            property_types_df: PropertyType node DataFrame
            price_ranges_df: PriceRange node DataFrame
            counties_df: County node DataFrame
            topic_clusters_df: TopicCluster node DataFrame
            
        Returns:
            Dictionary of relationship DataFrames by type
        """
        relationships = {}
        
        # HAS_FEATURE relationships
        if properties_df is not None and features_df is not None:
            try:
                relationships["has_feature"] = self.build_has_feature_relationships(
                    properties_df, features_df
                )
                logger.info("✓ Built HAS_FEATURE relationships")
            except Exception as e:
                logger.error(f"Failed to build HAS_FEATURE relationships: {e}")
        
        # OF_TYPE relationships
        if properties_df is not None and property_types_df is not None:
            try:
                relationships["of_type"] = self.build_of_type_relationships(
                    properties_df, property_types_df
                )
                logger.info("✓ Built OF_TYPE relationships")
            except Exception as e:
                logger.error(f"Failed to build OF_TYPE relationships: {e}")
        
        # IN_PRICE_RANGE relationships
        if properties_df is not None and price_ranges_df is not None:
            try:
                relationships["in_price_range"] = self.build_in_price_range_relationships(
                    properties_df, price_ranges_df
                )
                logger.info("✓ Built IN_PRICE_RANGE relationships")
            except Exception as e:
                logger.error(f"Failed to build IN_PRICE_RANGE relationships: {e}")
        
        # IN_COUNTY relationships
        if counties_df is not None:
            # Neighborhoods to counties
            if neighborhoods_df is not None:
                try:
                    relationships["neighborhood_in_county"] = self.build_in_county_relationships(
                        neighborhoods_df, counties_df, "neighborhood"
                    )
                    logger.info("✓ Built IN_COUNTY relationships for neighborhoods")
                except Exception as e:
                    logger.error(f"Failed to build IN_COUNTY relationships for neighborhoods: {e}")
        
        # IN_TOPIC_CLUSTER relationships
        if topic_clusters_df is not None:
            # Properties to topic clusters
            if properties_df is not None and "aggregated_topics" in properties_df.columns:
                try:
                    relationships["property_in_topic"] = self.build_in_topic_cluster_relationships(
                        properties_df, topic_clusters_df, "property", "aggregated_topics"
                    )
                    logger.info("✓ Built IN_TOPIC_CLUSTER relationships for properties")
                except Exception as e:
                    logger.error(f"Failed to build IN_TOPIC_CLUSTER for properties: {e}")
            
            # Neighborhoods to topic clusters
            if neighborhoods_df is not None and "aggregated_topics" in neighborhoods_df.columns:
                try:
                    relationships["neighborhood_in_topic"] = self.build_in_topic_cluster_relationships(
                        neighborhoods_df, topic_clusters_df, "neighborhood", "aggregated_topics"
                    )
                    logger.info("✓ Built IN_TOPIC_CLUSTER relationships for neighborhoods")
                except Exception as e:
                    logger.error(f"Failed to build IN_TOPIC_CLUSTER for neighborhoods: {e}")
            
            # Wikipedia articles to topic clusters
            if wikipedia_df is not None:
                try:
                    relationships["wikipedia_in_topic"] = self.build_in_topic_cluster_relationships(
                        wikipedia_df, topic_clusters_df, "wikipedia", "key_topics"
                    )
                    logger.info("✓ Built IN_TOPIC_CLUSTER relationships for Wikipedia articles")
                except Exception as e:
                    logger.error(f"Failed to build IN_TOPIC_CLUSTER for Wikipedia: {e}")
        
        return relationships