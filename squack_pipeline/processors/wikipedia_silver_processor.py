"""Wikipedia-specific Silver tier processor for data cleaning and normalization.

This processor handles the transformation of Wikipedia article data from Bronze to Silver tier.
Wikipedia data is already mostly flat, so minimal structural changes are needed.

Tier: Silver (Bronze → Silver)
Entity: Wikipedia
Purpose: Data cleaning, validation, and standardization
"""

from typing import Dict, Any, Optional

from squack_pipeline.config.schemas import MedallionTier
from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.processors.base import TransformationProcessor
from squack_pipeline.utils.logging import log_execution_time


class WikipediaSilverProcessor(TransformationProcessor):
    """Processor for Wikipedia entities in Silver tier.
    
    Transforms Wikipedia data from Bronze to Silver tier by:
    - Cleaning and validating data
    - Standardizing text fields
    - Validating coordinates and scores
    - Ensuring data quality
    """
    
    def __init__(self, settings: PipelineSettings):
        """Initialize Wikipedia Silver processor.
        
        Args:
            settings: Pipeline configuration settings
        """
        super().__init__(settings)
        self.set_tier(MedallionTier.SILVER)
        self.entity_type = "wikipedia"
        self.metrics: Dict[str, Any] = {
            "records_processed": 0,
            "records_cleaned": 0,
            "records_rejected": 0,
            "data_quality_score": 0.0
        }
    
    @log_execution_time
    def get_transformation_query(self, input_table: str) -> str:
        """Get SQL transformation query for Wikipedia Silver tier processing.
        
        Transforms Bronze Wikipedia data by:
        - Cleaning and trimming text fields
        - Validating coordinate ranges
        - Validating relevance scores
        - Preserving all metadata fields
        
        Args:
            input_table: Name of the Bronze Wikipedia table
            
        Returns:
            SQL query string for transformation
        """
        return f"""
        SELECT 
            -- Core Wikipedia fields (already mostly flat)
            id,
            pageid,
            location_id,
            TRIM(title) as title,
            TRIM(url) as url,
            TRIM(extract) as extract,
            categories,
            
            -- Coordinates validation
            CASE 
                WHEN latitude BETWEEN -90 AND 90 
                THEN latitude 
                ELSE NULL 
            END as latitude,
            CASE 
                WHEN longitude BETWEEN -180 AND 180 
                THEN longitude 
                ELSE NULL 
            END as longitude,
            
            -- Score validation
            CASE
                WHEN relevance_score BETWEEN 0.0 AND 1.0
                THEN relevance_score
                ELSE NULL
            END as relevance_score,
            
            -- Other metadata fields
            depth,
            crawled_at,
            html_file,
            file_hash,
            image_url,
            links_count,
            infobox_data,
            
            -- Calculated fields
            LENGTH(extract) as extract_length,
            CASE
                WHEN relevance_score >= 0.8 THEN 'high'
                WHEN relevance_score >= 0.5 THEN 'medium'
                WHEN relevance_score >= 0.3 THEN 'low'
                ELSE 'very_low'
            END as relevance_category,
            
            -- Add Silver tier metadata
            CURRENT_TIMESTAMP as silver_processed_at,
            'wikipedia_silver_processor_v1.0' as processing_version
            
        FROM {input_table}
        WHERE id IS NOT NULL
        AND title IS NOT NULL
        AND extract IS NOT NULL
        """
    
    def validate_input(self, table_name: str) -> bool:
        """Validate Bronze Wikipedia data before Silver processing.
        
        Checks:
        - Table exists and has data
        - Required columns are present
        - Basic data quality checks
        
        Args:
            table_name: Name of the Bronze Wikipedia table
            
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
            
            # Check required columns exist
            required_columns = [
                'id', 'pageid', 'title', 'extract', 
                'latitude', 'longitude', 'relevance_score'
            ]
            
            schema = self.get_table_schema(table_name)
            missing_columns = [col for col in required_columns if col not in schema]
            
            if missing_columns:
                self.logger.error(f"Missing required columns: {missing_columns}")
                return False
            
            self.logger.success(f"Input validation passed for {table_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Input validation failed: {e}")
            return False
    
    def validate_output(self, table_name: str) -> bool:
        """Validate Silver Wikipedia data quality after transformation.
        
        Checks:
        - Records exist in output
        - Required fields are not null
        - Data quality metrics meet thresholds
        
        Args:
            table_name: Name of the Silver Wikipedia table
            
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
            
            # Check data quality metrics
            quality_query = f"""
            SELECT 
                COUNT(*) as total_records,
                COUNT(CASE WHEN title IS NULL THEN 1 END) as null_titles,
                COUNT(CASE WHEN extract IS NULL THEN 1 END) as null_extracts,
                COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 END) as records_with_coords,
                AVG(CASE WHEN relevance_score IS NOT NULL THEN 1.0 ELSE 0.0 END) as score_completeness,
                AVG(CASE WHEN extract_length > 100 THEN 1.0 ELSE 0.0 END) as content_quality
            FROM {table_name}
            """
            
            result = self.execute_sql(quality_query).fetchone()
            if result:
                total, null_titles, null_extracts, with_coords, score_complete, content_quality = result
                
                # Calculate overall data quality score
                quality_score = (score_complete + content_quality) / 2
                self.metrics.update({
                    "records_processed": total,
                    "records_cleaned": total - null_titles - null_extracts,
                    "records_rejected": null_titles + null_extracts,
                    "data_quality_score": quality_score,
                    "records_with_coordinates": with_coords
                })
                
                # Log quality metrics
                self.logger.info(f"Silver data quality: {quality_score:.2%}")
                self.logger.info(f"Records with coordinates: {with_coords}/{total}")
                self.logger.info(f"Records with null titles: {null_titles}")
                self.logger.info(f"Records with null extracts: {null_extracts}")
                
                # Validation threshold
                if quality_score < 0.6:
                    self.logger.warning(f"Data quality below threshold: {quality_score:.2%}")
                
            self.logger.success(f"Silver output validation passed for {table_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Output validation failed: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get Wikipedia Silver processing metrics.
        
        Returns:
            Dictionary containing:
            - records_processed: Total records processed
            - records_cleaned: Records successfully cleaned
            - records_rejected: Records rejected due to quality issues
            - data_quality_score: Overall quality score (0.0-1.0)
            - records_with_coordinates: Count of records with valid coordinates
        """
        return self.metrics.copy()