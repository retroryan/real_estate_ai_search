"""
Property relationships writer for denormalized index.

This module builds denormalized property relationship documents
by joining data from properties, neighborhoods, and Wikipedia indices.
"""

import logging
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col, collect_list, struct, when, isnan, isnull, 
    array, lit, coalesce, first
)
from pyspark.sql.types import ArrayType, StructType, StringType

logger = logging.getLogger(__name__)


class WikipediaArticleSummary(BaseModel):
    """Summary of a Wikipedia article for embedding."""
    page_id: str
    title: str
    url: Optional[str] = None
    summary: Optional[str] = None
    best_city: Optional[str] = None
    best_state: Optional[str] = None
    relationship_type: str
    confidence: float
    relevance_score: Optional[float] = None


class NeighborhoodData(BaseModel):
    """Neighborhood data for embedding."""
    neighborhood_id: str
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    population: Optional[int] = None
    median_income: Optional[int] = None
    walkability_score: Optional[int] = None
    school_rating: Optional[float] = None
    description: Optional[str] = None
    amenities: List[str] = Field(default_factory=list)
    demographics: Optional[Dict[str, Any]] = None


class PropertyRelationshipDocument(BaseModel):
    """Denormalized property relationship document."""
    # Property fields
    listing_id: str
    property_type: Optional[str] = None
    price: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    square_feet: Optional[int] = None
    year_built: Optional[int] = None
    lot_size: Optional[int] = None
    address: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    features: List[str] = Field(default_factory=list)
    amenities: List[str] = Field(default_factory=list)
    status: Optional[str] = None
    listing_date: Optional[str] = None
    last_updated: Optional[str] = None
    days_on_market: Optional[int] = None
    price_per_sqft: Optional[float] = None
    hoa_fee: Optional[float] = None
    parking: Optional[Dict[str, Any]] = None
    virtual_tour_url: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    mls_number: Optional[str] = None
    tax_assessed_value: Optional[int] = None
    annual_tax: Optional[float] = None
    
    # Embedded neighborhood
    neighborhood: Optional[NeighborhoodData] = None
    
    # Embedded Wikipedia articles
    wikipedia_articles: List[WikipediaArticleSummary] = Field(default_factory=list)
    
    # Search and metadata fields
    enriched_search_text: Optional[str] = None
    embedding: Optional[List[float]] = None
    embedding_model: Optional[str] = None
    embedding_dimension: Optional[int] = None
    embedded_at: Optional[str] = None
    relationship_updated: Optional[str] = None
    data_version: Optional[str] = None


class PropertyRelationshipBuilder:
    """
    Builds denormalized property relationship documents.
    
    This class joins properties with neighborhoods and Wikipedia articles
    to create comprehensive relationship documents for single-query retrieval.
    """
    
    def __init__(self, spark: SparkSession):
        """
        Initialize the relationship builder.
        
        Args:
            spark: SparkSession instance
        """
        self.spark = spark
        self.logger = logging.getLogger(__name__)
    
    def build_relationships(
        self,
        properties_df: DataFrame,
        neighborhoods_df: DataFrame,
        wikipedia_df: DataFrame,
        max_wikipedia_articles: int = 5
    ) -> DataFrame:
        """
        Build denormalized property relationship documents.
        
        Args:
            properties_df: Properties DataFrame
            neighborhoods_df: Neighborhoods DataFrame
            wikipedia_df: Wikipedia DataFrame
            max_wikipedia_articles: Maximum Wikipedia articles per property
            
        Returns:
            DataFrame with denormalized property relationships
        """
        self.logger.info("Building property relationships...")
        
        # Step 1: Join properties with neighborhoods
        self.logger.debug("Joining properties with neighborhoods...")
        properties_with_neighborhoods = self._join_properties_neighborhoods(
            properties_df, 
            neighborhoods_df
        )
        
        # Step 2: Extract Wikipedia correlations
        self.logger.debug("Extracting Wikipedia correlations...")
        properties_with_wiki_refs = self._extract_wikipedia_correlations(
            properties_with_neighborhoods,
            neighborhoods_df
        )
        
        # Step 3: Join with Wikipedia articles
        self.logger.debug("Joining with Wikipedia articles...")
        properties_with_wikipedia = self._join_wikipedia_articles(
            properties_with_wiki_refs,
            wikipedia_df,
            max_wikipedia_articles
        )
        
        # Step 4: Format final structure
        self.logger.debug("Formatting final document structure...")
        final_df = self._format_final_structure(properties_with_wikipedia)
        
        record_count = final_df.count()
        self.logger.info(f"Built {record_count} property relationship documents")
        
        return final_df
    
    def _join_properties_neighborhoods(
        self, 
        properties_df: DataFrame,
        neighborhoods_df: DataFrame
    ) -> DataFrame:
        """
        Join properties with neighborhoods.
        
        Args:
            properties_df: Properties DataFrame
            neighborhoods_df: Neighborhoods DataFrame
            
        Returns:
            Joined DataFrame
        """
        # Select neighborhood fields to embed
        neighborhood_fields = [
            "neighborhood_id",
            "name",
            "city",
            "state",
            "population",
            "median_income",
            "walkability_score",
            "school_rating",
            "description",
            "amenities",
            "demographics"
        ]
        
        # Filter to available columns
        available_fields = [f for f in neighborhood_fields if f in neighborhoods_df.columns]
        
        # Create neighborhood struct
        neighborhood_struct = struct(*[col(f).alias(f) for f in available_fields])
        neighborhoods_for_join = neighborhoods_df.select(
            col("neighborhood_id").alias("nbh_id"),
            neighborhood_struct.alias("neighborhood")
        )
        
        # Join with properties
        joined_df = properties_df.join(
            neighborhoods_for_join,
            properties_df.neighborhood_id == neighborhoods_for_join.nbh_id,
            "left"
        ).drop("nbh_id")
        
        return joined_df
    
    def _extract_wikipedia_correlations(
        self,
        properties_df: DataFrame,
        neighborhoods_df: DataFrame
    ) -> DataFrame:
        """
        Extract Wikipedia correlations from neighborhoods.
        
        Args:
            properties_df: Properties with neighborhoods DataFrame
            neighborhoods_df: Original neighborhoods DataFrame with correlations
            
        Returns:
            Properties DataFrame with Wikipedia correlation data
        """
        # Check if wikipedia_correlations exists
        if "wikipedia_correlations" not in neighborhoods_df.columns:
            self.logger.warning("No wikipedia_correlations field found in neighborhoods")
            return properties_df.withColumn("wikipedia_page_ids", array())
        
        # Extract Wikipedia page IDs from correlations
        wiki_corr_df = neighborhoods_df.select(
            col("neighborhood_id").alias("nbh_id"),
            col("wikipedia_correlations")
        )
        
        # Join to add correlations
        with_correlations = properties_df.join(
            wiki_corr_df,
            properties_df.neighborhood_id == wiki_corr_df.nbh_id,
            "left"
        ).drop("nbh_id")
        
        return with_correlations
    
    def _join_wikipedia_articles(
        self,
        properties_df: DataFrame,
        wikipedia_df: DataFrame,
        max_articles: int
    ) -> DataFrame:
        """
        Join properties with Wikipedia articles.
        
        Args:
            properties_df: Properties DataFrame with Wikipedia references
            wikipedia_df: Wikipedia DataFrame
            max_articles: Maximum articles per property
            
        Returns:
            Properties with Wikipedia articles
        """
        from pyspark.sql.functions import explode, expr, size, slice
        
        # Check if we have wikipedia_correlations to work with
        if "wikipedia_correlations" not in properties_df.columns:
            self.logger.warning("No wikipedia_correlations found, adding empty wikipedia_articles")
            return properties_df.withColumn("wikipedia_articles", array())
        
        # Extract Wikipedia page IDs from correlations
        # Handle both primary and related articles
        with_page_ids = properties_df.withColumn(
            "wiki_page_ids",
            when(col("wikipedia_correlations").isNotNull(),
                 # Extract primary article page_id and related articles page_ids
                 array(
                     col("wikipedia_correlations.primary_wiki_article.page_id"),
                     *[col(f"wikipedia_correlations.related_wiki_articles[{i}].page_id") 
                       for i in range(3)]  # Get up to 3 related articles
                 )
            ).otherwise(array())
        ).withColumn(
            # Remove nulls from the array
            "wiki_page_ids",
            expr("filter(wiki_page_ids, x -> x is not null)")
        )
        
        # Create Wikipedia article summaries to join
        wiki_summaries = wikipedia_df.select(
            col("page_id"),
            struct(
                col("page_id").cast("string").alias("page_id"),
                col("title"),
                col("url"),
                coalesce(col("summary"), col("content")).alias("summary"),
                col("best_city"),
                col("best_state"),
                lit("neighborhood_related").alias("relationship_type"),
                lit(0.8).alias("confidence"),
                col("relevance_score")
            ).alias("article_summary")
        )
        
        # Explode page IDs for joining
        exploded = with_page_ids.select(
            "*",
            explode(
                when(size("wiki_page_ids") > 0, col("wiki_page_ids"))
                .otherwise(array(lit(None)))
            ).alias("wiki_page_id")
        )
        
        # Join with Wikipedia data
        joined = exploded.join(
            wiki_summaries,
            exploded.wiki_page_id == wiki_summaries.page_id,
            "left"
        )
        
        # Collect Wikipedia articles per property (limit to max_articles)
        with_wiki_articles = joined.groupBy(
            *[c for c in properties_df.columns]
        ).agg(
            slice(
                collect_list(
                    when(col("article_summary").isNotNull(), col("article_summary"))
                ),
                1, max_articles
            ).alias("wikipedia_articles")
        )
        
        # Handle properties without any Wikipedia articles
        final = with_wiki_articles.withColumn(
            "wikipedia_articles",
            when(col("wikipedia_articles").isNull(), array())
            .otherwise(col("wikipedia_articles"))
        )
        
        return final
    
    def _format_final_structure(self, df: DataFrame) -> DataFrame:
        """
        Format the final denormalized document structure.
        
        Args:
            df: DataFrame with all joined data
            
        Returns:
            Formatted DataFrame ready for Elasticsearch
        """
        # Select and rename fields as needed
        final_df = df.select(
            # Property fields
            col("listing_id"),
            col("property_type"),
            col("price"),
            col("bedrooms"),
            col("bathrooms"),
            col("square_feet"),
            col("year_built"),
            col("lot_size"),
            col("address"),
            col("description"),
            col("features"),
            col("amenities"),
            col("status"),
            col("listing_date"),
            col("last_updated"),
            col("days_on_market"),
            col("price_per_sqft"),
            col("hoa_fee"),
            col("parking"),
            col("virtual_tour_url"),
            col("images"),
            col("mls_number"),
            col("tax_assessed_value"),
            col("annual_tax"),
            
            # Neighborhood (already structured)
            col("neighborhood"),
            
            # Wikipedia articles (already structured)
            col("wikipedia_articles"),
            
            # Embedding and metadata
            col("enriched_search_text"),
            col("embedding"),
            col("embedding_model"),
            col("embedding_dimension"),
            col("embedded_at"),
            
            # Add relationship metadata
            lit(None).alias("relationship_updated"),
            lit("1.0.0").alias("data_version")
        )
        
        return final_df