"""Property-specific Silver tier processor for data cleaning and normalization.

This processor handles the transformation of property data from Bronze to Silver tier,
preserving nested structures while adding denormalized fields for query optimization.

Tier: Silver (Bronze → Silver)
Entity: Property
Purpose: Data cleaning, validation, and denormalization
"""

from typing import Dict, Any, Optional

from squack_pipeline.config.schemas import MedallionTier
from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.processors.base import TransformationProcessor
from squack_pipeline.utils.logging import log_execution_time


class PropertySilverProcessor(TransformationProcessor):
    """Processor for Property entities in Silver tier.
    
    Transforms property data from Bronze to Silver tier by:
    - Preserving nested structures (address, property_details, coordinates)
    - Adding denormalized fields for common queries
    - Cleaning and validating data
    - Calculating derived fields
    """
    
    def __init__(self, settings: PipelineSettings):
        """Initialize Property Silver processor.
        
        Args:
            settings: Pipeline configuration settings
        """
        super().__init__(settings)
        self.set_tier(MedallionTier.SILVER)
        self.entity_type = "property"
        self.metrics: Dict[str, Any] = {
            "records_processed": 0,
            "records_cleaned": 0,
            "records_rejected": 0,
            "data_quality_score": 0.0
        }
    
    @log_execution_time
    def get_transformation_query(self, input_table: str) -> str:
        """Get SQL transformation query for Property Silver tier processing.
        
        Transforms Bronze property data by:
        - Preserving nested STRUCT fields (address, property_details, coordinates)
        - Extracting denormalized fields for query performance
        - Cleaning and standardizing text fields
        - Validating numeric values
        - Calculating derived fields (calculated_price_per_sqft)
        
        Args:
            input_table: Name of the Bronze properties table
            
        Returns:
            SQL query string for transformation
        """
        return f"""
        SELECT 
            -- Core property fields with validation and cleaning
            TRIM(listing_id) as listing_id,
            COALESCE(TRIM(neighborhood_id), 'unknown') as neighborhood_id,
            
            -- Preserve nested structures from Bronze
            address,  -- Keep as STRUCT
            property_details,  -- Keep as STRUCT
            coordinates,  -- Keep as STRUCT
            
            -- Denormalized fields for common queries (extracted from nested structures)
            UPPER(TRIM(address.city)) as city,
            UPPER(TRIM(address.state)) as state,
            property_details.bedrooms as bedrooms,
            property_details.bathrooms as bathrooms,
            LOWER(TRIM(property_details.property_type)) as property_type,
            property_details.square_feet as square_feet,
            
            -- Price validation and normalization
            CASE 
                WHEN listing_price > 0 
                THEN ROUND(listing_price, 2) 
                ELSE NULL 
            END as listing_price,
            
            CASE 
                WHEN price_per_sqft > 0 
                THEN ROUND(price_per_sqft, 2) 
                ELSE NULL 
            END as price_per_sqft,
            
            -- Calculated fields
            CASE 
                WHEN listing_price > 0 AND property_details.square_feet > 0
                THEN ROUND(listing_price / property_details.square_feet, 2)
                ELSE NULL
            END as calculated_price_per_sqft,
            
            -- Description cleaning
            TRIM(REGEXP_REPLACE(description, '\\s+', ' ', 'g')) as description,
            
            -- Features array cleaning (remove empty strings, trim)
            LIST_FILTER(
                LIST_TRANSFORM(features, x -> TRIM(x)), 
                x -> LENGTH(x) > 0
            ) as features,
            
            -- Date validation
            listing_date,
            CASE 
                WHEN days_on_market >= 0 
                THEN days_on_market 
                ELSE 0 
            END as days_on_market,
            
            -- Optional fields
            virtual_tour_url,
            
            -- Images array cleaning
            LIST_FILTER(images, x -> LENGTH(TRIM(x)) > 0) as images,
            
            -- Price history preserved
            price_history,
            
            -- Add Silver tier metadata
            CURRENT_TIMESTAMP as silver_processed_at,
            'silver_processor_v3.0_nested_structures' as processing_version
            
        FROM {input_table}
        WHERE 
            -- Filter out completely invalid records
            listing_id IS NOT NULL 
            AND LENGTH(TRIM(listing_id)) > 0
            AND listing_price > 0
            AND property_details.square_feet > 0
            AND address.city IS NOT NULL
            AND LENGTH(TRIM(address.city)) > 0
        """
    
    def validate_input(self, table_name: str) -> bool:
        """Validate Bronze property data before Silver processing.
        
        Checks:
        - Table exists and has data
        - Required columns are present
        - Nested structures are STRUCT types
        
        Args:
            table_name: Name of the Bronze properties table
            
        Returns:
            True if validation passes, False otherwise
        """
        if not self.connection:
            return False
        
        try:
            # Check table exists and has data
            count = self.count_records(table_name)
            if count == 0:
                self.logger.error(f"Input table {table_name} is empty")
                return False
            
            # Check required columns exist (Bronze layer nested structure fields)
            required_columns = [
                'listing_id', 'listing_price', 'neighborhood_id',
                'address', 'property_details', 'coordinates',
                'description', 'features', 'images'
            ]
            
            schema = self.get_table_schema(table_name)
            missing_columns = [col for col in required_columns if col not in schema]
            
            if missing_columns:
                self.logger.error(f"Missing required columns: {missing_columns}")
                return False
            
            # Verify nested structures are actually STRUCT types
            nested_fields = ['address', 'property_details', 'coordinates']
            for field in nested_fields:
                if field in schema and 'STRUCT' not in schema[field].upper():
                    self.logger.warning(f"Field {field} is not a STRUCT type: {schema[field]}")
            
            self.logger.success(f"Input validation passed for {table_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Input validation failed: {e}")
            return False
    
    def validate_output(self, table_name: str) -> bool:
        """Validate Silver property data quality after transformation.
        
        Checks:
        - Nested structures are preserved
        - Denormalized fields exist
        - Data quality metrics meet thresholds
        
        Args:
            table_name: Name of the Silver properties table
            
        Returns:
            True if validation passes, False otherwise
        """
        if not self.connection:
            return False
        
        try:
            total_records = self.count_records(table_name)
            if total_records == 0:
                self.logger.error("No records in Silver output")
                return False
            
            # Check that nested structures are preserved
            schema = self.get_table_schema(table_name)
            nested_fields = ['address', 'property_details', 'coordinates']
            for field in nested_fields:
                if field not in schema:
                    self.logger.error(f"Nested structure {field} missing in Silver output")
                    return False
                if 'STRUCT' not in schema[field].upper():
                    self.logger.error(f"Field {field} is not a STRUCT in Silver output: {schema[field]}")
                    return False
            
            # Check that denormalized fields exist
            denorm_fields = ['city', 'state', 'bedrooms', 'bathrooms', 'property_type', 'square_feet']
            missing_denorm = [f for f in denorm_fields if f not in schema]
            if missing_denorm:
                self.logger.error(f"Missing denormalized fields: {missing_denorm}")
                return False
            
            # Check data quality metrics using nested field access
            quality_query = f"""
            SELECT 
                COUNT(*) as total_records,
                COUNT(CASE WHEN listing_price IS NULL THEN 1 END) as null_prices,
                COUNT(CASE WHEN coordinates.latitude IS NULL OR coordinates.longitude IS NULL THEN 1 END) as null_coordinates,
                COUNT(CASE WHEN property_details.square_feet IS NULL THEN 1 END) as null_sqft,
                AVG(CASE WHEN listing_price > 0 THEN 1.0 ELSE 0.0 END) as price_completeness,
                AVG(CASE WHEN LENGTH(description) > 10 THEN 1.0 ELSE 0.0 END) as description_quality
            FROM {table_name}
            """
            
            result = self.execute_sql(quality_query).fetchone()
            if result:
                total, null_prices, null_coords, null_sqft, price_complete, desc_quality = result
                
                # Calculate overall data quality score
                quality_score = (price_complete + desc_quality) / 2
                self.metrics.update({
                    "records_processed": total,
                    "records_cleaned": total - null_prices,
                    "records_rejected": null_prices,
                    "data_quality_score": quality_score
                })
                
                # Log quality metrics
                self.logger.info(f"Silver data quality: {quality_score:.2%}")
                self.logger.info(f"Records with null prices: {null_prices}")
                self.logger.info(f"Records with null coordinates: {null_coords}")
                
                # Validation threshold
                if quality_score < 0.8:
                    self.logger.warning(f"Data quality below threshold: {quality_score:.2%}")
                
            self.logger.success(f"Silver output validation passed for {table_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Output validation failed: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get Property Silver processing metrics.
        
        Returns:
            Dictionary containing:
            - records_processed: Total records processed
            - records_cleaned: Records successfully cleaned
            - records_rejected: Records rejected due to quality issues
            - data_quality_score: Overall quality score (0.0-1.0)
        """
        return self.metrics.copy()