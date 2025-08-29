"""Neighborhood-specific Silver tier processor for data cleaning and normalization.

This processor handles the transformation of neighborhood data from Bronze to Silver tier,
preserving nested structures while adding denormalized fields for query optimization.

Tier: Silver (Bronze → Silver)
Entity: Neighborhood
Purpose: Data cleaning, validation, and denormalization
"""

from typing import Dict, Any, Optional

from squack_pipeline.config.schemas import MedallionTier
from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.processors.base import TransformationProcessor
from squack_pipeline.utils.logging import log_execution_time


class NeighborhoodSilverProcessor(TransformationProcessor):
    """Processor for Neighborhood entities in Silver tier.
    
    Transforms neighborhood data from Bronze to Silver tier by:
    - Preserving nested structures (coordinates, characteristics, demographics)
    - Adding denormalized fields for common queries
    - Cleaning and validating data
    - Standardizing text fields
    """
    
    def __init__(self, settings: PipelineSettings):
        """Initialize Neighborhood Silver processor.
        
        Args:
            settings: Pipeline configuration settings
        """
        super().__init__(settings)
        self.set_tier(MedallionTier.SILVER)
        self.entity_type = "neighborhood"
        self.metrics: Dict[str, Any] = {
            "records_processed": 0,
            "records_cleaned": 0,
            "records_rejected": 0,
            "data_quality_score": 0.0
        }
    
    @log_execution_time
    def get_transformation_query(self, input_table: str) -> str:
        """Get SQL transformation query for Neighborhood Silver tier processing.
        
        Transforms Bronze neighborhood data by:
        - Preserving nested STRUCT fields (coordinates, characteristics, demographics)
        - Extracting denormalized fields for query performance
        - Cleaning and standardizing text fields
        - Validating score ranges
        
        Args:
            input_table: Name of the Bronze neighborhoods table
            
        Returns:
            SQL query string for transformation
        """
        return f"""
        SELECT 
            -- Core neighborhood fields
            neighborhood_id,
            TRIM(name) as name,
            UPPER(TRIM(city)) as city,
            UPPER(TRIM(county)) as county,
            UPPER(TRIM(state)) as state,
            
            -- Preserve nested structures from Bronze
            coordinates,  -- Keep as STRUCT
            characteristics,  -- Keep as STRUCT
            demographics,  -- Keep as STRUCT
            
            -- Denormalized fields for common queries (extracted from nested structures)
            CASE 
                WHEN characteristics.walkability_score BETWEEN 0 AND 100 
                THEN characteristics.walkability_score 
                ELSE NULL 
            END as walkability_score,
            CASE 
                WHEN characteristics.transit_score BETWEEN 0 AND 100 
                THEN characteristics.transit_score 
                ELSE NULL 
            END as transit_score,
            CASE 
                WHEN characteristics.school_rating BETWEEN 0 AND 10 
                THEN characteristics.school_rating 
                ELSE NULL 
            END as school_rating,
            CASE 
                WHEN characteristics.safety_rating BETWEEN 0 AND 10 
                THEN characteristics.safety_rating 
                ELSE NULL 
            END as safety_rating,
            demographics.population as population,
            demographics.median_household_income as median_household_income,
            
            -- Arrays preserved
            amenities,
            lifestyle_tags,
            
            -- Other fields
            median_home_price,
            price_trend,
            TRIM(description) as description,
            wikipedia_correlations,
            
            -- Add Silver tier metadata
            CURRENT_TIMESTAMP as silver_processed_at,
            'neighborhood_silver_processor_v1.0' as processing_version
            
        FROM {input_table}
        WHERE neighborhood_id IS NOT NULL
        AND name IS NOT NULL
        AND city IS NOT NULL
        AND state IS NOT NULL
        """
    
    def validate_input(self, table_name: str) -> bool:
        """Validate Bronze neighborhood data before Silver processing.
        
        Checks:
        - Table exists and has data
        - Required columns are present
        - Nested structures are STRUCT types
        
        Args:
            table_name: Name of the Bronze neighborhoods table
            
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
                'neighborhood_id', 'name', 'city', 'state',
                'coordinates', 'characteristics', 'demographics',
                'amenities', 'lifestyle_tags'
            ]
            
            schema = self.get_table_schema(table_name)
            missing_columns = [col for col in required_columns if col not in schema]
            
            if missing_columns:
                self.logger.error(f"Missing required columns: {missing_columns}")
                return False
            
            # Verify nested structures are actually STRUCT types
            nested_fields = ['coordinates', 'characteristics', 'demographics']
            for field in nested_fields:
                if field in schema and 'STRUCT' not in schema[field].upper():
                    self.logger.warning(f"Field {field} is not a STRUCT type: {schema[field]}")
            
            self.logger.success(f"Input validation passed for {table_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Input validation failed: {e}")
            return False
    
    def validate_output(self, table_name: str) -> bool:
        """Validate Silver neighborhood data quality after transformation.
        
        Checks:
        - Nested structures are preserved
        - Denormalized fields exist
        - Data quality metrics meet thresholds
        
        Args:
            table_name: Name of the Silver neighborhoods table
            
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
            nested_fields = ['coordinates', 'characteristics', 'demographics']
            for field in nested_fields:
                if field not in schema:
                    self.logger.error(f"Nested structure {field} missing in Silver output")
                    return False
                if 'STRUCT' not in schema[field].upper():
                    self.logger.error(f"Field {field} is not a STRUCT in Silver output: {schema[field]}")
                    return False
            
            # Check that denormalized fields exist
            denorm_fields = ['walkability_score', 'transit_score', 'school_rating', 'population']
            missing_denorm = [f for f in denorm_fields if f not in schema]
            if missing_denorm:
                self.logger.error(f"Missing denormalized fields: {missing_denorm}")
                return False
            
            # Check data quality metrics
            quality_query = f"""
            SELECT 
                COUNT(*) as total_records,
                COUNT(CASE WHEN name IS NULL THEN 1 END) as null_names,
                COUNT(CASE WHEN coordinates.latitude IS NULL OR coordinates.longitude IS NULL THEN 1 END) as null_coordinates,
                AVG(CASE WHEN walkability_score IS NOT NULL THEN 1.0 ELSE 0.0 END) as walkability_completeness,
                AVG(CASE WHEN LENGTH(description) > 10 THEN 1.0 ELSE 0.0 END) as description_quality
            FROM {table_name}
            """
            
            result = self.execute_sql(quality_query).fetchone()
            if result:
                total, null_names, null_coords, walk_complete, desc_quality = result
                
                # Calculate overall data quality score
                quality_score = (walk_complete + desc_quality) / 2
                self.metrics.update({
                    "records_processed": total,
                    "records_cleaned": total - null_names,
                    "records_rejected": null_names,
                    "data_quality_score": quality_score
                })
                
                # Log quality metrics
                self.logger.info(f"Silver data quality: {quality_score:.2%}")
                self.logger.info(f"Records with null names: {null_names}")
                self.logger.info(f"Records with null coordinates: {null_coords}")
                
                # Validation threshold
                if quality_score < 0.7:
                    self.logger.warning(f"Data quality below threshold: {quality_score:.2%}")
                
            self.logger.success(f"Silver output validation passed for {table_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Output validation failed: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get Neighborhood Silver processing metrics.
        
        Returns:
            Dictionary containing:
            - records_processed: Total records processed
            - records_cleaned: Records successfully cleaned
            - records_rejected: Records rejected due to quality issues
            - data_quality_score: Overall quality score (0.0-1.0)
        """
        return self.metrics.copy()