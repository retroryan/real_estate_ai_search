"""Wikipedia-specific Gold tier processor for minimal transformation.

This processor handles the transformation of Wikipedia article data from Silver to Gold tier,
with minimal changes for Elasticsearch indexing.

Tier: Gold (Silver → Gold)
Entity: Wikipedia
Purpose: Minimal transformation for Elasticsearch indexing
"""

from typing import Dict, Any

from squack_pipeline.config.schemas import MedallionTier
from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.processors.base import TransformationProcessor
from squack_pipeline.utils.logging import log_execution_time


class WikipediaGoldProcessor(TransformationProcessor):
    """Processor for Wikipedia entities in Gold tier.
    
    Transforms Wikipedia data from Silver to Gold tier by:
    - Passing through all fields with minimal changes
    - Creating location array [lon, lat] for Elasticsearch geo_point
    - Adding entity_type for multi-index queries
    
    Wikipedia data is already mostly flat, so very minimal transformation needed.
    """
    
    def __init__(self, settings: PipelineSettings):
        """Initialize Wikipedia Gold processor.
        
        Args:
            settings: Pipeline configuration settings
        """
        super().__init__(settings)
        self.set_tier(MedallionTier.GOLD)
        self.entity_type = "wikipedia"
        self.entity_prefix = "wikipedia"  # For table naming
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
        """Get SQL transformation query for Wikipedia Gold tier processing.
        
        Minimal transformation for Elasticsearch:
        - Pass through all fields
        - Create location array for geo_point mapping
        - Add entity type for multi-index identification
        
        Args:
            input_table: Name of the Silver Wikipedia table
            
        Returns:
            SQL query string for transformation
        """
        return f"""
        SELECT 
            -- Core Wikipedia fields (pass through)
            id,
            pageid as page_id,  -- Rename for consistency
            location_id,
            title,
            url,
            extract,
            extract_length,
            categories,
            
            -- Coordinates
            latitude,
            longitude,
            
            -- Create location array for Elasticsearch geo_point
            CASE 
                WHEN longitude IS NOT NULL AND latitude IS NOT NULL
                THEN LIST_VALUE(longitude, latitude)
                ELSE NULL
            END as location,
            
            -- Relevance fields
            relevance_score,
            relevance_category,
            
            -- Metadata fields
            depth,
            crawled_at,
            html_file,
            file_hash,
            image_url,
            links_count,
            infobox_data,
            
            -- Add Gold tier metadata
            CURRENT_TIMESTAMP as gold_processed_at,
            'wikipedia_gold_processor_v1.0' as processing_version,
            'wikipedia' as entity_type
            
        FROM {input_table}
        WHERE id IS NOT NULL
        AND title IS NOT NULL
        """
    
    def validate_input(self, table_name: str) -> bool:
        """Validate Silver Wikipedia data before Gold processing.
        
        Args:
            table_name: Name of the Silver Wikipedia table
            
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
            
            # Check required fields exist
            schema = self.get_table_schema(table_name)
            required_fields = ['id', 'title', 'extract']
            
            for field in required_fields:
                if field not in schema:
                    self.logger.error(f"Required field {field} missing")
                    return False
            
            self.logger.success(f"Input validation passed for {table_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Input validation failed: {e}")
            return False
    
    def validate_output(self, table_name: str) -> bool:
        """Validate Gold Wikipedia data after transformation.
        
        Args:
            table_name: Name of the Gold Wikipedia table
            
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
            
            # Check that key fields exist
            schema = self.get_table_schema(table_name)
            
            # Verify core fields
            core_fields = ['id', 'page_id', 'title', 'extract']
            for field in core_fields:
                if field not in schema:
                    self.logger.error(f"Core field {field} missing in Gold output")
                    return False
            
            # Verify computed fields exist
            computed_fields = ['location', 'entity_type']
            for field in computed_fields:
                if field not in schema:
                    self.logger.warning(f"Computed field {field} missing in Gold output")
            
            self.metrics['records_processed'] = total_records
            self.metrics['records_transformed'] = total_records
            
            self.logger.success(f"Gold output validation passed for {table_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Output validation failed: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get Wikipedia Gold processing metrics.
        
        Returns:
            Dictionary containing:
            - records_processed: Total records processed
            - records_transformed: Records successfully transformed
        """
        return self.metrics.copy()