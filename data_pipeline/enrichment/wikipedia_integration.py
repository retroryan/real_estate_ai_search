"""
Wikipedia enrichment integration for the data pipeline.

This module provides the WikipediaEnrichmentBuilder class that integrates
Wikipedia data with property and neighborhood entities to create structured
enrichment data for search indexing.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col, lit, when, coalesce, trim, length, split, array,
    array_contains, size, expr, concat, concat_ws,
    broadcast, collect_list, first
)
from pyspark.sql.types import FloatType, StringType

from data_pipeline.models.enrichment import (
    EnrichmentData,
    LocationContext,
    NeighborhoodContext,
    Landmark,
    NearbyPOI,
    WikipediaEnrichmentResult
)

logger = logging.getLogger(__name__)


class WikipediaEnrichmentBuilder(BaseModel):
    """
    Builder class for integrating Wikipedia enrichment data into property documents.
    
    This class joins Wikipedia data with property/neighborhood data based on location,
    builds structured enrichment contexts, and calculates confidence scores.
    """
    
    class Config:
        arbitrary_types_allowed = True
    
    spark: SparkSession = Field(..., description="Spark session")
    
    def __init__(self, spark: SparkSession):
        """Initialize the enrichment builder."""
        super().__init__(spark=spark)
    
    def enrich_properties(
        self, 
        properties_df: DataFrame, 
        wikipedia_df: DataFrame
    ) -> DataFrame:
        """
        Enrich properties with Wikipedia data based on location matching.
        
        Args:
            properties_df: DataFrame with property data
            wikipedia_df: DataFrame with Wikipedia articles
            
        Returns:
            Properties DataFrame with enrichment fields added
        """
        logger.info("Starting Wikipedia enrichment for properties")
        
        # Validate input DataFrames
        self._validate_properties_df(properties_df)
        self._validate_wikipedia_df(wikipedia_df)
        
        # Join Wikipedia data with properties based on location
        enriched_df = self._join_wikipedia_data(properties_df, wikipedia_df)
        
        # Build location context fields
        enriched_df = self._build_location_context_fields(enriched_df)
        
        # Build neighborhood context fields  
        enriched_df = self._build_neighborhood_context_fields(enriched_df)
        
        # Calculate location quality scores
        enriched_df = self._calculate_location_scores(enriched_df)
        
        # Generate enriched search text
        enriched_df = self._generate_enriched_search_text(enriched_df)
        
        logger.info("Completed Wikipedia enrichment for properties")
        return enriched_df
    
    def enrich_neighborhoods(
        self, 
        neighborhoods_df: DataFrame, 
        wikipedia_df: DataFrame
    ) -> DataFrame:
        """
        Enrich neighborhoods with Wikipedia data based on location matching.
        
        Args:
            neighborhoods_df: DataFrame with neighborhood data
            wikipedia_df: DataFrame with Wikipedia articles
            
        Returns:
            Neighborhoods DataFrame with enrichment fields added
        """
        logger.info("Starting Wikipedia enrichment for neighborhoods")
        
        # Similar process to properties but focused on neighborhood-specific enrichment
        enriched_df = self._join_wikipedia_data(neighborhoods_df, wikipedia_df)
        enriched_df = self._build_location_context_fields(enriched_df)
        enriched_df = self._build_neighborhood_context_fields(enriched_df)
        enriched_df = self._calculate_location_scores(enriched_df)
        enriched_df = self._generate_enriched_search_text(enriched_df)
        
        logger.info("Completed Wikipedia enrichment for neighborhoods")
        return enriched_df
    
    def _validate_properties_df(self, df: DataFrame):
        """Validate properties DataFrame has required fields."""
        required_fields = ["listing_id", "city", "state"]
        missing_fields = [field for field in required_fields if field not in df.columns]
        if missing_fields:
            raise ValueError(f"Properties DataFrame missing required fields: {missing_fields}")
    
    def _validate_wikipedia_df(self, df: DataFrame):
        """Validate Wikipedia DataFrame has required fields."""
        required_fields = ["page_id", "title", "best_city", "best_state"]
        missing_fields = [field for field in required_fields if field not in df.columns]
        if missing_fields:
            raise ValueError(f"Wikipedia DataFrame missing required fields: {missing_fields}")
    
    def _join_wikipedia_data(
        self, 
        entities_df: DataFrame, 
        wikipedia_df: DataFrame
    ) -> DataFrame:
        """
        Join entity data with Wikipedia articles based on location matching.
        
        Matches on city/state with fallback to state-only matching.
        """
        # Clean and normalize location fields for joining
        entities_clean = entities_df.withColumn(
            "clean_city", 
            when(col("city").isNotNull(), trim(col("city").cast(StringType())))
            .otherwise(lit(None))
        ).withColumn(
            "clean_state",
            when(col("state").isNotNull(), trim(col("state").cast(StringType())))
            .otherwise(lit(None))
        )
        
        wikipedia_clean = wikipedia_df.withColumn(
            "wiki_clean_city",
            when(col("best_city").isNotNull(), trim(col("best_city").cast(StringType())))
            .otherwise(lit(None))
        ).withColumn(
            "wiki_clean_state", 
            when(col("best_state").isNotNull(), trim(col("best_state").cast(StringType())))
            .otherwise(lit(None))
        )
        
        # Create broadcast variable for Wikipedia data (assuming it's smaller)
        wikipedia_broadcast = broadcast(wikipedia_clean)
        
        # Primary join: exact city and state match
        city_state_join = entities_clean.join(
            wikipedia_broadcast,
            (col("clean_city") == col("wiki_clean_city")) & 
            (col("clean_state") == col("wiki_clean_state")),
            "left_outer"
        )
        
        # Secondary join: state-only match for entities without city matches
        state_only_wikipedia = wikipedia_clean.filter(
            col("wiki_clean_city").isNull() & col("wiki_clean_state").isNotNull()
        )
        
        state_only_join = entities_clean.join(
            broadcast(state_only_wikipedia),
            col("clean_state") == col("wiki_clean_state"),
            "left_outer"
        )
        
        # Combine results, prioritizing city+state matches
        final_df = city_state_join.unionByName(
            state_only_join.filter(col("page_id").isNull()),
            allowMissingColumns=True
        )
        
        # Add match confidence based on match type
        final_df = final_df.withColumn(
            "location_match_confidence",
            when(
                col("wiki_clean_city").isNotNull() & col("wiki_clean_state").isNotNull(),
                lit(0.9)
            ).when(
                col("wiki_clean_state").isNotNull(),
                lit(0.6)
            ).otherwise(lit(0.0))
        )
        
        return final_df
    
    def _build_location_context_fields(self, df: DataFrame) -> DataFrame:
        """
        Build location context enrichment fields from Wikipedia data.
        """
        # Extract Wikipedia metadata
        df = df.withColumn(
            "location_wikipedia_page_id",
            when(col("page_id").isNotNull(), col("page_id").cast(StringType()))
            .otherwise(lit(None))
        ).withColumn(
            "location_wikipedia_title", 
            coalesce(col("title"), lit(None))
        )
        
        # Extract content fields
        df = df.withColumn(
            "location_summary",
            coalesce(col("long_summary"), lit(None))
        ).withColumn(
            "historical_significance", 
            when(
                col("long_summary").isNotNull() & 
                (col("long_summary").rlike("(?i)(historic|history|founded|established|built)")),
                col("long_summary")
            ).otherwise(lit(None))
        )
        
        # Process key topics from string or array
        df = df.withColumn(
            "location_key_topics",
            when(col("key_topics").isNotNull(),
                 when(col("key_topics").rlike(","),
                      split(col("key_topics"), ","))
                 .otherwise(array(col("key_topics"))))
            .otherwise(lit(None))
        )
        
        # Extract features based on content analysis
        df = self._extract_cultural_features(df)
        df = self._extract_recreational_features(df)
        df = self._extract_transportation_features(df)
        
        # Determine location type
        df = df.withColumn(
            "location_type",
            when(col("wiki_clean_city").isNotNull(), lit("city"))
            .when(col("wiki_clean_state").isNotNull(), lit("state"))
            .otherwise(lit("general"))
        )
        
        # Set confidence score
        df = df.withColumn(
            "location_confidence",
            coalesce(col("location_match_confidence"), lit(0.5))
        )
        
        return df
    
    def _extract_cultural_features(self, df: DataFrame) -> DataFrame:
        """Extract cultural features from Wikipedia content."""
        cultural_keywords = [
            "museum", "gallery", "theater", "theatre", "art", "cultural",
            "historic", "monument", "heritage", "architecture", "landmark"
        ]
        
        cultural_pattern = "|".join([f"(?i){kw}" for kw in cultural_keywords])
        
        return df.withColumn(
            "cultural_features",
            when(
                col("long_summary").isNotNull() & 
                col("long_summary").rlike(cultural_pattern),
                split(
                    expr(f"regexp_extract_all(long_summary, '({cultural_pattern})', 1)"),
                    ","
                )
            ).otherwise(lit(None))
        )
    
    def _extract_recreational_features(self, df: DataFrame) -> DataFrame:
        """Extract recreational features from Wikipedia content."""
        recreational_keywords = [
            "park", "recreation", "outdoor", "hiking", "trail", "beach",
            "sports", "golf", "swimming", "boating", "fishing", "camping"
        ]
        
        recreational_pattern = "|".join([f"(?i){kw}" for kw in recreational_keywords])
        
        return df.withColumn(
            "recreational_features", 
            when(
                col("long_summary").isNotNull() & 
                col("long_summary").rlike(recreational_pattern),
                split(
                    expr(f"regexp_extract_all(long_summary, '({recreational_pattern})', 1)"),
                    ","
                )
            ).otherwise(lit(None))
        )
    
    def _extract_transportation_features(self, df: DataFrame) -> DataFrame:
        """Extract transportation features from Wikipedia content."""
        transport_keywords = [
            "airport", "train", "subway", "metro", "bus", "highway", "interstate",
            "transportation", "transit", "rail", "station", "port"
        ]
        
        transport_pattern = "|".join([f"(?i){kw}" for kw in transport_keywords])
        
        return df.withColumn(
            "transportation_features",
            when(
                col("long_summary").isNotNull() & 
                col("long_summary").rlike(transport_pattern),
                split(
                    expr(f"regexp_extract_all(long_summary, '({transport_pattern})', 1)"),
                    ","
                )
            ).otherwise(lit(None))
        )
    
    def _build_neighborhood_context_fields(self, df: DataFrame) -> DataFrame:
        """
        Build neighborhood context enrichment fields from Wikipedia data.
        """
        # For neighborhood context, we use the same Wikipedia data but focus on
        # neighborhood-specific attributes
        
        df = df.withColumn(
            "neighborhood_wikipedia_page_id",
            when(col("page_id").isNotNull(), col("page_id").cast(StringType()))
            .otherwise(lit(None))
        ).withColumn(
            "neighborhood_wikipedia_title",
            coalesce(col("title"), lit(None))
        )
        
        # Extract neighborhood-specific content
        df = df.withColumn(
            "neighborhood_description",
            coalesce(col("long_summary"), lit(None))
        ).withColumn(
            "neighborhood_history",
            when(
                col("long_summary").isNotNull() &
                col("long_summary").rlike("(?i)(history|historical|founded|established)"),
                col("long_summary")
            ).otherwise(lit(None))
        ).withColumn(
            "neighborhood_character",
            when(
                col("long_summary").isNotNull() &
                col("long_summary").rlike("(?i)(character|atmosphere|community|residential)"),
                col("long_summary")
            ).otherwise(lit(None))
        )
        
        # Extract social and cultural attributes
        df = self._extract_notable_residents(df)
        df = self._extract_architectural_styles(df)
        
        # Set neighborhood-specific topics
        df = df.withColumn(
            "neighborhood_key_topics",
            coalesce(col("location_key_topics"), lit(None))
        )
        
        # Calculate derived scores (simplified for now)
        df = df.withColumn(
            "gentrification_index",
            lit(0.5).cast(FloatType())  # Placeholder - would need more complex analysis
        ).withColumn(
            "diversity_score", 
            lit(0.5).cast(FloatType())  # Placeholder - would need demographic data
        )
        
        # Extract establishment year if mentioned
        df = df.withColumn(
            "establishment_year",
            when(
                col("long_summary").isNotNull(),
                expr("regexp_extract(long_summary, '(18|19|20)\\\\d{2}', 0)").cast("int")
            ).otherwise(lit(None))
        )
        
        return df
    
    def _extract_notable_residents(self, df: DataFrame) -> DataFrame:
        """Extract notable residents from Wikipedia content."""
        return df.withColumn(
            "notable_residents",
            when(
                col("long_summary").isNotNull() &
                col("long_summary").rlike("(?i)(resident|born|lived|native)"),
                # This is a simplified extraction - in practice would need NER
                lit(None)
            ).otherwise(lit(None))
        )
    
    def _extract_architectural_styles(self, df: DataFrame) -> DataFrame:
        """Extract architectural styles from Wikipedia content."""
        architecture_keywords = [
            "Victorian", "Colonial", "Modern", "Contemporary", "Art Deco",
            "Craftsman", "Tudor", "Mediterranean", "Ranch", "Bungalow"
        ]
        
        arch_pattern = "|".join([f"(?i){style}" for style in architecture_keywords])
        
        return df.withColumn(
            "architectural_style",
            when(
                col("long_summary").isNotNull() &
                col("long_summary").rlike(arch_pattern),
                split(
                    expr(f"regexp_extract_all(long_summary, '({arch_pattern})', 1)"),
                    ","
                )
            ).otherwise(lit(None))
        )
    
    def _calculate_location_scores(self, df: DataFrame) -> DataFrame:
        """
        Calculate location quality scores based on Wikipedia content.
        """
        # Cultural richness score
        df = df.withColumn(
            "cultural_richness",
            when(
                col("cultural_features").isNotNull() & (size(col("cultural_features")) > 0),
                (size(col("cultural_features")).cast(FloatType()) * 0.2 + 0.3)
            ).when(
                col("long_summary").isNotNull() &
                col("long_summary").rlike("(?i)(cultural|art|museum|historic)"),
                lit(0.6)
            ).otherwise(lit(0.3))
        )
        
        # Historical importance score
        df = df.withColumn(
            "historical_importance",
            when(
                col("historical_significance").isNotNull(),
                lit(0.8)
            ).when(
                col("establishment_year").isNotNull(),
                lit(0.6)
            ).when(
                col("long_summary").isNotNull() &
                col("long_summary").rlike("(?i)(historic|history|heritage)"),
                lit(0.5)
            ).otherwise(lit(0.2))
        )
        
        # Tourist appeal score
        df = df.withColumn(
            "tourist_appeal",
            when(
                col("recreational_features").isNotNull() & (size(col("recreational_features")) > 0),
                (size(col("recreational_features")).cast(FloatType()) * 0.15 + 0.4)
            ).when(
                col("long_summary").isNotNull() &
                col("long_summary").rlike("(?i)(tourist|attraction|visit|destination)"),
                lit(0.7)
            ).otherwise(lit(0.3))
        )
        
        # Local amenities score
        df = df.withColumn(
            "local_amenities",
            when(
                col("transportation_features").isNotNull() & (size(col("transportation_features")) > 0),
                (size(col("transportation_features")).cast(FloatType()) * 0.1 + 0.5)
            ).otherwise(lit(0.4))
        )
        
        # Overall desirability (weighted combination)
        df = df.withColumn(
            "overall_desirability",
            (
                col("cultural_richness") * 0.25 +
                col("historical_importance") * 0.2 +
                col("tourist_appeal") * 0.25 +
                col("local_amenities") * 0.3
            )
        )
        
        return df
    
    def _generate_enriched_search_text(self, df: DataFrame) -> DataFrame:
        """
        Generate combined enriched search text from all Wikipedia enrichment data.
        """
        # Combine all text fields into enriched search text
        text_components = [
            col("location_wikipedia_title"),
            col("location_summary"), 
            col("historical_significance"),
            col("neighborhood_description"),
            col("neighborhood_history"),
            col("neighborhood_character")
        ]
        
        # Join array fields
        array_components = [
            col("location_key_topics"),
            col("cultural_features"),
            col("recreational_features"), 
            col("transportation_features"),
            col("neighborhood_key_topics"),
            col("notable_residents"),
            col("architectural_style")
        ]
        
        # Combine text components
        text_expr = concat_ws(" ", *[
            when(component.isNotNull(), component).otherwise(lit(""))
            for component in text_components
        ])
        
        # Add array components 
        for array_col in array_components:
            text_expr = concat(
                text_expr,
                lit(" "),
                when(
                    array_col.isNotNull() & (size(array_col) > 0),
                    concat_ws(" ", array_col)
                ).otherwise(lit(""))
            )
        
        df = df.withColumn(
            "enriched_search_text",
            when(length(trim(text_expr)) > 0, trim(text_expr))
            .otherwise(lit(None))
        )
        
        return df
    
    def get_enrichment_statistics(self, df: DataFrame) -> Dict[str, Any]:
        """
        Calculate statistics about the enrichment process.
        
        Args:
            df: Enriched DataFrame
            
        Returns:
            Dictionary of enrichment statistics
        """
        total_entities = df.count()
        enriched_entities = df.filter(col("location_wikipedia_page_id").isNotNull()).count()
        
        return {
            "total_entities": total_entities,
            "enriched_entities": enriched_entities,
            "enrichment_rate": enriched_entities / total_entities if total_entities > 0 else 0,
            "average_confidence": df.agg({"location_confidence": "avg"}).collect()[0][0] or 0,
            "high_confidence_enrichments": df.filter(col("location_confidence") >= 0.8).count(),
            "entities_with_cultural_features": df.filter(
                col("cultural_features").isNotNull() & (size(col("cultural_features")) > 0)
            ).count(),
            "entities_with_recreational_features": df.filter(
                col("recreational_features").isNotNull() & (size(col("recreational_features")) > 0)
            ).count(),
        }