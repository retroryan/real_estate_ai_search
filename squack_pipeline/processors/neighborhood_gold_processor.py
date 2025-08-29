"""Neighborhood-specific Gold tier processor for minimal transformation.

This processor handles the transformation of neighborhood data from Silver to Gold tier,
passing through nested structures with minimal changes for Elasticsearch.

Tier: Gold (Silver → Gold)
Entity: Neighborhood
Purpose: Minimal transformation for Elasticsearch indexing
"""

from typing import Dict, Any

from squack_pipeline.config.schemas import MedallionTier
from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.processors.base import TransformationProcessor
from squack_pipeline.utils.logging import log_execution_time


class NeighborhoodGoldProcessor(TransformationProcessor):
    """Processor for Neighborhood entities in Gold tier.
    
    Transforms neighborhood data from Silver to Gold tier by:
    - Passing through nested structures unchanged
    - Creating location array [lon, lat] for Elasticsearch geo_point
    - Adding entity_type for multi-index queries
    
    NO reconstruction of nested objects - they're already nested.
    """
    
    def __init__(self, settings: PipelineSettings):
        """Initialize Neighborhood Gold processor.
        
        Args:
            settings: Pipeline configuration settings
        """
        super().__init__(settings)
        self.set_tier(MedallionTier.GOLD)
        self.entity_type = "neighborhood"
        self.entity_prefix = "neighborhoods"  # For table naming
        self.metrics: Dict[str, Any] = {
            "records_processed": 0,
            "records_transformed": 0
        }
    
    def process(self, input_table: str) -> str:
        """Process data using entity-specific table naming."""
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
        
        # Generate entity-specific output table name
        import time
        timestamp = int(time.time())
        output_table = f"{self.entity_prefix}_{self.tier.value}_{timestamp}"
        
        # Get transformation query
        transformation_query = self.get_transformation_query(input_table)
        
        # Create output table from transformation
        self.create_table_from_query(output_table, transformation_query)
        
        # Update metrics
        input_count = self.count_records(input_table)
        output_count = self.count_records(output_table)
        
        self.logger.info(
            f"Transformed {input_count} records to {output_count} records "
            f"in {output_table}"
        )
        
        return output_table
    
    @log_execution_time
    def get_transformation_query(self, input_table: str) -> str:
        """Get SQL transformation query for Neighborhood Gold tier processing.
        
        Minimal transformation for Elasticsearch:
        - Pass through all nested structures (coordinates, characteristics, demographics)
        - Create location array for geo_point mapping
        - Add entity type for multi-index identification
        
        Args:
            input_table: Name of the Silver neighborhoods table
            
        Returns:
            SQL query string for transformation
        """
        return f"""
        SELECT 
            -- Core fields
            neighborhood_id,
            name,
            city,
            county,
            state,
            
            -- Pass through nested structures unchanged
            coordinates,  -- Already a STRUCT
            characteristics,  -- Already a STRUCT
            demographics,  -- Already a STRUCT
            wikipedia_correlations,  -- Already a STRUCT/JSON
            
            -- Denormalized fields from Silver (pass through)
            walkability_score,
            transit_score,
            school_rating,
            safety_rating,
            population,
            median_household_income,
            
            -- Create location array for Elasticsearch geo_point
            CASE 
                WHEN coordinates.longitude IS NOT NULL AND coordinates.latitude IS NOT NULL
                THEN LIST_VALUE(coordinates.longitude, coordinates.latitude)
                ELSE NULL
            END as location,
            
            -- Pass through arrays unchanged
            amenities,
            lifestyle_tags,
            
            -- Pass through other fields
            median_home_price,
            price_trend,
            description,
            
            -- Add Gold tier metadata
            CURRENT_TIMESTAMP as gold_processed_at,
            'neighborhood_gold_processor_v1.0' as processing_version,
            'neighborhood' as entity_type
            
        FROM {input_table}
        WHERE neighborhood_id IS NOT NULL
        """
    
    def validate_input(self, table_name: str) -> bool:
        """Validate Silver neighborhood data before Gold processing.
        
        Args:
            table_name: Name of the Silver neighborhoods table
            
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
            
            # Check required nested structures exist
            schema = self.get_table_schema(table_name)
            required_nested = ['coordinates', 'characteristics', 'demographics']
            
            for field in required_nested:
                if field not in schema:
                    self.logger.error(f"Required nested field {field} missing")
                    return False
                if 'STRUCT' not in schema[field].upper():
                    self.logger.error(f"Field {field} is not a STRUCT")
                    return False
            
            self.logger.success(f"Input validation passed for {table_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Input validation failed: {e}")
            return False
    
    def validate_output(self, table_name: str) -> bool:
        """Validate Gold neighborhood data after transformation.
        
        Args:
            table_name: Name of the Gold neighborhoods table
            
        Returns:
            True if validation passes, False otherwise
        """
        if not self.connection:
            return False
        
        try:
            total_records = self.count_records(table_name)
            if total_records == 0:
                self.logger.error("No records in Gold output")
                return False
            
            # Check that nested structures are still preserved
            schema = self.get_table_schema(table_name)
            
            # Verify nested structures
            nested_fields = ['coordinates', 'characteristics', 'demographics']
            for field in nested_fields:
                if field not in schema:
                    self.logger.error(f"Nested structure {field} missing in Gold output")
                    return False
            
            # Verify computed fields exist
            computed_fields = ['location', 'entity_type']
            for field in computed_fields:
                if field not in schema:
                    self.logger.error(f"Computed field {field} missing in Gold output")
                    return False
            
            self.metrics['records_processed'] = total_records
            self.metrics['records_transformed'] = total_records
            
            self.logger.success(f"Gold output validation passed for {table_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Output validation failed: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get Neighborhood Gold processing metrics.
        
        Returns:
            Dictionary containing:
            - records_processed: Total records processed
            - records_transformed: Records successfully transformed
        """
        return self.metrics.copy()