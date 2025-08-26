"""
Topic extraction and clustering from Wikipedia articles.

Simple topic grouping without complex clustering algorithms.
"""

import logging
from typing import Dict, List, Optional
from collections import defaultdict
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col,
    explode,
    collect_set,
    count,
    lit,
    lower,
    trim
)

from data_pipeline.models.graph_models import TopicClusterNode
from data_pipeline.enrichment.id_generator import generate_topic_cluster_id

logger = logging.getLogger(__name__)


class TopicExtractor:
    """Extract and group topics from Wikipedia articles."""
    
    def __init__(self, spark: SparkSession):
        """
        Initialize the topic extractor.
        
        Args:
            spark: Active SparkSession
        """
        self.spark = spark
        self.topic_categories = self._initialize_categories()
    
    def _initialize_categories(self) -> Dict[str, str]:
        """Initialize topic category mappings."""
        return {
            # Education topics
            "school": "education",
            "university": "education",
            "college": "education",
            "education": "education",
            "academic": "education",
            "student": "education",
            
            # Transportation topics
            "transit": "transportation",
            "bart": "transportation",
            "muni": "transportation",
            "caltrain": "transportation",
            "highway": "transportation",
            "bridge": "transportation",
            "airport": "transportation",
            
            # Recreation topics
            "park": "recreation",
            "recreation": "recreation",
            "sports": "recreation",
            "beach": "recreation",
            "trail": "recreation",
            "golf": "recreation",
            
            # Culture topics
            "museum": "culture",
            "art": "culture",
            "theater": "culture",
            "music": "culture",
            "festival": "culture",
            "cultural": "culture",
            
            # History topics
            "history": "history",
            "historic": "history",
            "heritage": "history",
            "landmark": "history",
            "monument": "history",
            
            # Business topics
            "business": "business",
            "shopping": "business",
            "restaurant": "business",
            "retail": "business",
            "commerce": "business",
            "downtown": "business",
            
            # Residential topics
            "residential": "residential",
            "neighborhood": "residential",
            "housing": "residential",
            "apartment": "residential",
            "condo": "residential",
            
            # Nature topics
            "nature": "nature",
            "wildlife": "nature",
            "forest": "nature",
            "mountain": "nature",
            "ocean": "nature",
            "bay": "nature",
        }
    
    def categorize_topic(self, topic: str) -> str:
        """
        Categorize a topic based on keywords.
        
        Args:
            topic: Topic string
            
        Returns:
            Topic category
        """
        topic_lower = topic.lower()
        
        for keyword, category in self.topic_categories.items():
            if keyword in topic_lower:
                return category
        
        return "general"
    
    def extract_topic_clusters(self, wikipedia_df: DataFrame) -> DataFrame:
        """
        Extract and group topics into clusters from Wikipedia articles.
        
        Args:
            wikipedia_df: DataFrame with Wikipedia articles containing key_topics
            
        Returns:
            DataFrame of TopicClusterNode records
        """
        logger.info("Extracting topic clusters from Wikipedia articles")
        
        # Explode topics array if it exists
        if "key_topics" not in wikipedia_df.columns:
            logger.warning("No key_topics column found in Wikipedia data")
            return self.spark.createDataFrame([], TopicClusterNode.spark_schema())
        
        # Get all topics
        topics_df = wikipedia_df.select(
            explode(col("key_topics")).alias("topic")
        ).filter(
            col("topic").isNotNull()
        ).withColumn(
            "topic_normalized",
            lower(trim(col("topic")))
        )
        
        # Count topic occurrences
        topic_counts = topics_df.groupBy("topic_normalized").agg(
            count("*").alias("count")
        ).collect()
        
        # Group topics by category
        topic_groups = defaultdict(list)
        for row in topic_counts:
            topic = row["topic_normalized"]
            category = self.categorize_topic(topic)
            topic_groups[category].append(topic)
        
        # Create topic cluster nodes
        cluster_nodes = []
        for category, topics in topic_groups.items():
            cluster_id = generate_topic_cluster_id(category)
            
            # Get top topics (limit to 20 most common)
            top_topics = sorted(topics)[:20]
            
            cluster_node = TopicClusterNode(
                id=cluster_id,
                name=category.title() + " Topics",
                category=category,
                topics=top_topics,
                entity_count=len(topics)
            )
            cluster_nodes.append(cluster_node.model_dump())
        
        # Convert to DataFrame
        if cluster_nodes:
            return self.spark.createDataFrame(cluster_nodes, schema=TopicClusterNode.spark_schema())
        else:
            return self.spark.createDataFrame([], TopicClusterNode.spark_schema())
    
