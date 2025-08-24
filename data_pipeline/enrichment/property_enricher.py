"""
Property-specific data enrichment engine.

This module provides enrichment capabilities specifically for property data,
including price calculations, address normalization, and quality scoring.
"""

import logging
import uuid
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from pyspark.sql import DataFrame, SparkSession

from .base_enricher import BaseEnricher, BaseEnrichmentConfig
from pyspark.sql.functions import (
    broadcast,
    coalesce,
    col,
    concat,
    current_timestamp,
    expr,
    lit,
    lower,
    trim,
    udf,
    upper,
    when,
)
from pyspark.sql.types import StringType

logger = logging.getLogger(__name__)


class PropertyEnrichmentConfig(BaseEnrichmentConfig):
    """Configuration for property enrichment operations."""
    
    enable_price_calculations: bool = Field(
        default=True,
        description="Calculate derived price fields like price_per_sqft"
    )
    
    enable_address_normalization: bool = Field(
        default=True,
        description="Normalize address and location fields"
    )
    
    enable_quality_scoring: bool = Field(
        default=True,
        description="Calculate property data quality scores"
    )
    
    enable_correlation_ids: bool = Field(
        default=True,
        description="Generate correlation IDs for tracking"
    )
    
    min_quality_score: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Minimum acceptable quality score for properties"
    )
    
    city_abbreviations: Dict[str, str] = Field(
        default_factory=lambda: {
            "SF": "San Francisco",
            "PC": "Park City",
            "NYC": "New York City",
            "LA": "Los Angeles",
        },
        description="City abbreviation mappings"
    )
    
    state_abbreviations: Dict[str, str] = Field(
        default_factory=lambda: {
            "CA": "California",
            "UT": "Utah",
            "NY": "New York",
            "TX": "Texas",
            "FL": "Florida",
        },
        description="State abbreviation mappings"
    )
    
    enable_location_enhancement: bool = Field(
        default=True,
        description="Enable location hierarchy enhancement using reference data"
    )
    
    enable_neighborhood_linking: bool = Field(
        default=True,
        description="Link properties to neighborhoods via neighborhood_id"
    )


class PropertyEnricher(BaseEnricher):
    """
    Enriches property data with calculated fields, normalized values,
    and quality metrics specific to real estate listings.
    """
    
    def __init__(self, spark: SparkSession, config: Optional[PropertyEnrichmentConfig] = None, 
                 location_broadcast: Optional[Any] = None):
        """
        Initialize the property enricher.
        
        Args:
            spark: Active SparkSession
            config: Property enrichment configuration
            location_broadcast: Broadcast variable containing location reference data
        """
        super().__init__(spark, config, location_broadcast)
        
        # Create broadcast variables for location lookups
        if self.config.enable_address_normalization:
            self._create_location_broadcasts()
        
        # Override location enricher initialization with property-specific config
        if self.location_broadcast and self.config.enable_location_enhancement:
            from .location_enricher import LocationEnricher, LocationEnrichmentConfig
            location_config = LocationEnrichmentConfig(
                enable_hierarchy_resolution=True,
                enable_neighborhood_linking=self.config.enable_neighborhood_linking
            )
            self.location_enricher = LocationEnricher(spark, location_broadcast, location_config)
    
    def _get_default_config(self) -> PropertyEnrichmentConfig:
        """Get the default configuration for property enricher."""
        return PropertyEnrichmentConfig()
    
    def set_location_data(self, location_broadcast: Any):
        """
        Set location broadcast data and create LocationEnricher after initialization.
        
        Args:
            location_broadcast: Broadcast variable containing location reference data
        """
        super().set_location_data(location_broadcast)
        
        if self.location_broadcast and self.config.enable_location_enhancement:
            from .location_enricher import LocationEnricher, LocationEnrichmentConfig
            location_config = LocationEnrichmentConfig(
                enable_hierarchy_resolution=True,
                enable_neighborhood_linking=self.config.enable_neighborhood_linking
            )
            self.location_enricher = LocationEnricher(self.spark, location_broadcast, location_config)
            logger.info("LocationEnricher initialized with broadcast data")
    
    
    def _create_location_broadcasts(self):
        """Create broadcast variables for location normalization."""
        # City mappings
        city_data = [(k, v) for k, v in self.config.city_abbreviations.items()]
        self.city_lookup_df = self.spark.createDataFrame(
            city_data, ["city_abbr", "city_full"]
        )
        
        # State mappings
        state_data = [(k, v) for k, v in self.config.state_abbreviations.items()]
        self.state_lookup_df = self.spark.createDataFrame(
            state_data, ["state_abbr", "state_full"]
        )
    
    def enrich(self, df: DataFrame) -> DataFrame:
        """
        Apply property-specific enrichments.
        
        Args:
            df: Property DataFrame to enrich
            
        Returns:
            Enriched property DataFrame
        """
        logger.info("Starting property enrichment process")
        
        initial_count = df.count()
        enriched_df = df
        
        # Add correlation IDs if configured
        if self.config.enable_correlation_ids:
            enriched_df = self.add_correlation_ids(enriched_df, "property_correlation_id")
            logger.info("Added correlation IDs to properties")
        
        # Normalize addresses and locations
        if self.config.enable_address_normalization:
            enriched_df = self._normalize_addresses(enriched_df)
            logger.info("Normalized property addresses")
        
        # Enhance with location hierarchy and neighborhood linking
        if self.location_enricher and self.config.enable_location_enhancement:
            enriched_df = self._enhance_with_location_data(enriched_df)
            logger.info("Enhanced properties with location hierarchy")

        # Extract property details if nested
        if "property_details.square_feet" in enriched_df.columns:
            enriched_df = enriched_df.withColumn("square_feet", col("property_details.square_feet"))
            enriched_df = enriched_df.withColumn("bedrooms", col("property_details.bedrooms"))
            enriched_df = enriched_df.withColumn("bathrooms", col("property_details.bathrooms"))
            enriched_df = enriched_df.withColumn("year_built", col("property_details.year_built"))
            enriched_df = enriched_df.withColumn("lot_size", col("property_details.lot_size"))
            enriched_df = enriched_df.withColumn("stories", col("property_details.stories"))
            enriched_df = enriched_df.withColumn("garage_spaces", col("property_details.garage_spaces"))
            logger.info("Extracted property details from nested structure")
        else:
            logger.warning(f"Property details not found in nested structure: {col('property_details.listing_id')}")

        enriched_df.show(10, truncate=False)

        # Calculate price-related fields
        if self.config.enable_price_calculations:
            enriched_df = self._calculate_price_fields(enriched_df)
            logger.info("Calculated price-related fields")
        
        # Calculate quality scores
        if self.config.enable_quality_scoring:
            enriched_df = self._calculate_quality_scores(enriched_df)
            logger.info("Calculated property quality scores")
        
        # Extract coordinates if present
        if "coordinates.latitude" in enriched_df.columns:
            enriched_df = enriched_df.withColumn("latitude", col("coordinates.latitude"))
            enriched_df = enriched_df.withColumn("longitude", col("coordinates.longitude"))
        

        
        # Categorize price ranges
        enriched_df = self.categorize_price_range(enriched_df)
        logger.info("Categorized properties into price ranges")
        
        # Categorize features
        enriched_df = self.categorize_features(enriched_df)
        logger.info("Categorized property features")
        
        # Normalize property types
        enriched_df = self.normalize_property_type(enriched_df)
        logger.info("Normalized property types")
        
        # Add processing timestamp
        enriched_df = self.add_processing_timestamp(enriched_df)
        
        # Validate enrichment
        return self.validate_enrichment(enriched_df, initial_count, "Property")
    
    
    def _normalize_addresses(self, df: DataFrame) -> DataFrame:
        """
        Normalize property addresses and location fields.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with normalized address fields
        """
        # Extract city, state, county, and zip_code from nested address structure
        df_with_location = df.withColumn("city", col("address.city"))\
            .withColumn("state", col("address.state"))\
            .withColumn("county", col("address.county"))\
            .withColumn("zip_code", col("address.zip"))
        
        # Normalize cities
        df_with_city = df_with_location.join(
            broadcast(self.city_lookup_df),
            upper(trim(col("city"))) == upper(self.city_lookup_df.city_abbr),
            "left"
        ).withColumn(
            "city_normalized",
            coalesce(col("city_full"), col("city"))
        ).drop("city_abbr", "city_full")
        
        # Normalize states
        df_with_state = df_with_city.join(
            broadcast(self.state_lookup_df),
            upper(trim(col("state"))) == upper(self.state_lookup_df.state_abbr),
            "left"
        ).withColumn(
            "state_normalized",
            coalesce(col("state_full"), col("state"))
        ).drop("state_abbr", "state_full")
        
        # Normalize street address (extract from nested structure)
        df_with_address = df_with_state.withColumn(
            "address_normalized",
            when(col("address.street").isNotNull(),
                 trim(lower(col("address.street"))))
            .otherwise(lit(None))
        )
        
        return df_with_address
    
    def _calculate_price_fields(self, df: DataFrame) -> DataFrame:
        """
        Calculate price-related derived fields.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with calculated price fields
        """
        # Extract property details fields if nested, or use direct fields
        if "property_details.square_feet" in df.columns:
            df = df.withColumn("square_feet", col("property_details.square_feet"))
            df = df.withColumn("bedrooms", col("property_details.bedrooms"))
            df = df.withColumn("bathrooms", col("property_details.bathrooms"))
        
        # Handle both 'price' and 'listing_price' field names
        price_col = "listing_price" if "listing_price" in df.columns else "price"
        
        # Price per square foot (handle if price_per_sqft already exists in source data)
        if "price_per_sqft" not in df.columns:
            df_with_price_sqft = df.withColumn(
                "price_per_sqft",
                when(
                    (col("square_feet") > 0) & col(price_col).isNotNull(),
                    (col(price_col) / col("square_feet")).cast("decimal(10,2)")
                ).otherwise(lit(None))
            )
        else:
            df_with_price_sqft = df
        
        return df_with_price_sqft
    
    def _calculate_quality_scores(self, df: DataFrame) -> DataFrame:
        """
        Calculate property data quality scores.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with quality scores
        """

        # Extract property details if nested
        if "property_details.square_feet" in df.columns:
            df = df.withColumn("square_feet", col("property_details.square_feet"))
            df = df.withColumn("bedrooms", col("property_details.bedrooms"))
            df = df.withColumn("bathrooms", col("property_details.bathrooms"))
            df = df.withColumn("year_built", col("property_details.year_built"))
            df = df.withColumn("property_type", col("property_details.property_type"))
        
        # Handle both 'price' and 'listing_price' field names
        price_col = "listing_price" if "listing_price" in df.columns else "price"
        
        # Property-specific quality score calculation
        quality_expr = (
            # Essential fields (50% weight)
            (when(col("listing_id").isNotNull(), 0.1).otherwise(0.0)) +
            (when(col(price_col).isNotNull() & (col(price_col) > 0), 0.15).otherwise(0.0)) +
            (when(col("bedrooms").isNotNull() & (col("bedrooms") >= 0), 0.1).otherwise(0.0)) +
            (when(col("bathrooms").isNotNull() & (col("bathrooms") >= 0), 0.05).otherwise(0.0)) +
            (when(col("square_feet").isNotNull() & (col("square_feet") > 0), 0.1).otherwise(0.0)) +
            
            # Location fields (25% weight)
            (when(col("address").isNotNull(), 0.05).otherwise(0.0)) +
            (when(col("city").isNotNull(), 0.1).otherwise(0.0)) +
            (when(col("state").isNotNull(), 0.05).otherwise(0.0)) +
            (when(col("zip_code").isNotNull(), 0.05).otherwise(0.0)) +
            
            # Description and features (15% weight)
            (when(col("description").isNotNull() & (col("description") != ""), 0.1).otherwise(0.0)) +
            (when(col("features").isNotNull() & (expr("size(features)") > 0), 0.05).otherwise(0.0)) +
            
            # Additional valuable fields (10% weight)
            (when(col("property_type").isNotNull(), 0.05).otherwise(0.0)) +
            (when(col("year_built").isNotNull() & (col("year_built") > 1800), 0.05).otherwise(0.0))
        )
        
        # Apply quality score
        df_with_quality = df.withColumn(
            "property_quality_score",
            quality_expr.cast("decimal(3,2)")
        )
        
        # Add validation status
        df_with_validation = df_with_quality.withColumn(
            "property_validation_status",
            when(
                col("property_quality_score") >= self.config.min_quality_score,
                lit("validated")
            ).when(
                col("property_quality_score") < self.config.min_quality_score,
                lit("low_quality")
            ).otherwise(lit("pending"))
        )
        
        return df_with_validation
    
    def _enhance_with_location_data(self, df: DataFrame) -> DataFrame:
        """
        Enhance properties with location hierarchy and neighborhood linking.
        
        Args:
            df: Property DataFrame to enhance
            
        Returns:
            DataFrame with location enhancements
        """
        try:
            # Extract city, state, and county from address if not already extracted
            if "city" not in df.columns:
                df = df.withColumn("city", col("address.city"))
            if "state" not in df.columns:
                df = df.withColumn("state", col("address.state"))
            if "county" not in df.columns and "address.county" in df.columns:
                df = df.withColumn("county", col("address.county"))
            
            # Enhance with hierarchy (adds county information)
            enhanced_df = self.location_enricher.enhance_with_hierarchy(df, "city", "state")
            
            # Keep both county and county_resolved if available
            # county comes from source data, county_resolved from location enrichment
            if "county_resolved" in enhanced_df.columns and "county" not in enhanced_df.columns:
                enhanced_df = enhanced_df.withColumnRenamed("county_resolved", "county")
            
            # Add neighborhood linking if enabled
            if self.config.enable_neighborhood_linking:
                # For properties, we'll try to match against neighborhoods in the same city/state
                # This is a simplified approach - in reality you might want more sophisticated matching
                enhanced_df = self.location_enricher.link_to_neighborhood(
                    enhanced_df, "city", "city", "state"  # Using city as neighborhood for now
                )
            
            # Standardize location names
            enhanced_df = self.location_enricher.standardize_location_names(
                enhanced_df, "city", "state"
            )
            
            # Normalize state names from abbreviations to full names
            enhanced_df = self.location_enricher.normalize_state_names(enhanced_df, "state")
            
            return enhanced_df
            
        except Exception as e:
            logger.error(f"Failed to enhance with location data: {e}")
            # Return original DataFrame if enhancement fails
            return df
    
    def get_enrichment_statistics(self, df: DataFrame) -> Dict:
        """
        Calculate statistics about the enrichment process.
        
        Args:
            df: Enriched DataFrame
            
        Returns:
            Dictionary of enrichment statistics
        """
        stats = {}
        
        total = df.count()
        stats["total_properties"] = total
        
        # Price calculations
        if "price_per_sqft" in df.columns:
            with_price_sqft = df.filter(col("price_per_sqft").isNotNull()).count()
            stats["properties_with_price_per_sqft"] = with_price_sqft
            
            avg_price_sqft = df.filter(col("price_per_sqft").isNotNull()) \
                              .select(expr("avg(price_per_sqft)")).collect()[0][0]
            stats["avg_price_per_sqft"] = float(avg_price_sqft) if avg_price_sqft else 0
        
        # Address normalization
        if "city_normalized" in df.columns:
            with_normalized_city = df.filter(col("city_normalized").isNotNull()).count()
            stats["properties_with_normalized_city"] = with_normalized_city
        
        # Quality scores
        if "property_quality_score" in df.columns:
            quality_stats = df.select(
                expr("avg(property_quality_score) as avg_quality"),
                expr("min(property_quality_score) as min_quality"),
                expr("max(property_quality_score) as max_quality"),
                expr("count(case when property_validation_status = 'validated' then 1 end) as validated"),
                expr("count(case when property_validation_status = 'low_quality' then 1 end) as low_quality")
            ).collect()[0]
            
            stats["avg_quality_score"] = float(quality_stats["avg_quality"]) if quality_stats["avg_quality"] else 0
            stats["min_quality_score"] = float(quality_stats["min_quality"]) if quality_stats["min_quality"] else 0
            stats["max_quality_score"] = float(quality_stats["max_quality"]) if quality_stats["max_quality"] else 0
            stats["validated_properties"] = quality_stats["validated"]
            stats["low_quality_properties"] = quality_stats["low_quality"]
        
        # Price categories
        if "price_category" in df.columns:
            category_counts = df.groupBy("price_category").count().collect()
            stats["price_categories"] = {row["price_category"]: row["count"] for row in category_counts}
        
        return stats
    
    def categorize_price_range(self, df: DataFrame) -> DataFrame:
        """
        Categorize properties into price ranges for graph relationships.
        
        Args:
            df: Property DataFrame
            
        Returns:
            DataFrame with price_range_id column
        """
        from pyspark.sql.functions import when
        
        # Handle both 'price' and 'listing_price' field names
        price_col = "listing_price" if "listing_price" in df.columns else "price"
        
        # Define price range thresholds and IDs
        df_with_range = df.withColumn(
            "price_range_id",
            when(col(price_col) < 500000, lit("range_0_500k"))
            .when(col(price_col) < 1000000, lit("range_500k_1m"))
            .when(col(price_col) < 2000000, lit("range_1m_2m"))
            .when(col(price_col) < 3000000, lit("range_2m_3m"))
            .when(col(price_col) < 5000000, lit("range_3m_5m"))
            .otherwise(lit("range_5m_plus"))
        )
        
        return df_with_range
    
    def categorize_features(self, df: DataFrame) -> DataFrame:
        """
        Categorize property features into types for better organization.
        
        Args:
            df: Property DataFrame with features array
            
        Returns:
            DataFrame with feature_categories column
        """
        if "features" not in df.columns:
            logger.warning("No 'features' column found in DataFrame")
            return df
        
        # Create feature_ids by normalizing feature names
        df_with_ids = df.withColumn(
            "feature_ids",
            expr("""
                transform(
                    features,
                    x -> concat('feature_', lower(regexp_replace(x, '[^a-zA-Z0-9]', '_')))
                )
            """)
        )
        
        # Simple categorization using SQL expressions instead of UDF
        # This is more efficient and cleaner
        df_with_categories = df_with_ids.withColumn(
            "feature_categories",
            expr("""
                transform(
                    features,
                    feature -> CASE
                        WHEN lower(feature) RLIKE 'pool|hot tub|gym|sauna|spa|clubhouse|tennis' THEN 'amenity'
                        WHEN lower(feature) RLIKE 'view|vista|panoramic' THEN 'view'
                        WHEN lower(feature) RLIKE 'garage|parking|carport|ev charging' THEN 'parking'
                        WHEN lower(feature) RLIKE 'garden|patio|deck|balcony|yard|terrace|bbq' THEN 'outdoor'
                        WHEN lower(feature) RLIKE 'smart|security|automation' THEN 'smart'
                        WHEN lower(feature) RLIKE 'wine cellar|theater|chef|walk-in|library' THEN 'luxury'
                        WHEN lower(feature) RLIKE 'solar|energy efficient|leed|green' THEN 'environmental'
                        ELSE 'other'
                    END
                )
            """)
        ).withColumn(
            "feature_categories_distinct",
            expr("array_distinct(feature_categories)")
        )
        
        return df_with_categories
    
    def normalize_property_type(self, df: DataFrame) -> DataFrame:
        """
        Normalize property types to standard enum values.
        
        Args:
            df: Property DataFrame
            
        Returns:
            DataFrame with normalized property_type
        """
        from pyspark.sql.functions import regexp_replace, lower, trim
        
        # Extract property type from nested structure if needed
        if "property_details.property_type" in df.columns:
            df = df.withColumn("property_type", col("property_details.property_type"))
        
        # Normalize property type if it exists
        if "property_type" in df.columns:
            type_col = "property_type"
            
            # Create normalized type
            df_normalized = df.withColumn(
                "property_type_normalized",
                lower(trim(col(type_col)))
            )
            
            # Map variations to standard types
            df_normalized = df_normalized.withColumn(
                "property_type_normalized",
                when(col("property_type_normalized").isin("single-family", "single_family", "single family", "sfh"), 
                     lit("single_family"))
                .when(col("property_type_normalized").isin("condo", "condominium"), 
                      lit("condo"))
                .when(col("property_type_normalized").isin("townhouse", "townhome", "town_house"), 
                      lit("townhome"))
                .when(col("property_type_normalized").isin("multi-family", "multi_family", "multifamily", "mfh"), 
                      lit("multi_family"))
                .when(col("property_type_normalized").isNull(), 
                      lit("unknown"))
                .otherwise(lit("other"))
            )
            
            # Create property_type_id for relationships
            df_normalized = df_normalized.withColumn(
                "property_type_id",
                concat(lit("type_"), col("property_type_normalized"))
            )
            
            return df_normalized
        else:
            logger.warning("No property type column found in DataFrame")
            return df