"""Silver tier processor for data cleaning and normalization."""

from typing import Dict, Any

from squack_pipeline.config.schemas import MedallionTier
from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.processors.base import TransformationProcessor
from squack_pipeline.utils.logging import log_execution_time


class SilverProcessor(TransformationProcessor):
    """Processor for Silver tier - data cleaning and normalization."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize Silver processor."""
        super().__init__(settings)
        self.set_tier(MedallionTier.SILVER)
        self.metrics = {
            "records_processed": 0,
            "records_cleaned": 0,
            "records_rejected": 0,
            "data_quality_score": 0.0
        }
    
    @log_execution_time
    def get_transformation_query(self, input_table: str) -> str:
        """Get SQL transformation query for Silver tier processing."""
        return f"""
        SELECT 
            -- Core property fields with validation and cleaning
            TRIM(listing_id) as listing_id,
            COALESCE(TRIM(neighborhood_id), 'unknown') as neighborhood_id,
            
            -- Address standardization
            STRUCT_PACK(
                street := TRIM(address.street),
                city := UPPER(TRIM(address.city)),
                county := UPPER(TRIM(address.county)),
                state := UPPER(TRIM(address.state)),
                zip := REGEXP_REPLACE(TRIM(address.zip), '[^0-9-]', '', 'g')
            ) as address,
            
            -- Coordinates validation (ensure within reasonable bounds)
            STRUCT_PACK(
                latitude := CASE 
                    WHEN coordinates.latitude BETWEEN -90 AND 90 
                    THEN coordinates.latitude 
                    ELSE NULL 
                END,
                longitude := CASE 
                    WHEN coordinates.longitude BETWEEN -180 AND 180 
                    THEN coordinates.longitude 
                    ELSE NULL 
                END
            ) as coordinates,
            
            -- Property details cleaning and validation
            STRUCT_PACK(
                square_feet := CASE 
                    WHEN property_details.square_feet > 0 
                    THEN property_details.square_feet 
                    ELSE NULL 
                END,
                bedrooms := CASE 
                    WHEN property_details.bedrooms >= 0 
                    THEN property_details.bedrooms 
                    ELSE 0 
                END,
                bathrooms := CASE 
                    WHEN property_details.bathrooms >= 0 
                    THEN property_details.bathrooms 
                    ELSE 0 
                END,
                property_type := LOWER(TRIM(property_details.property_type)),
                year_built := CASE 
                    WHEN property_details.year_built BETWEEN 1800 AND 2100 
                    THEN property_details.year_built 
                    ELSE NULL 
                END,
                lot_size := CASE 
                    WHEN property_details.lot_size >= 0 
                    THEN property_details.lot_size 
                    ELSE NULL 
                END,
                stories := CASE 
                    WHEN property_details.stories >= 1 
                    THEN property_details.stories 
                    ELSE 1 
                END,
                garage_spaces := CASE 
                    WHEN property_details.garage_spaces >= 0 
                    THEN property_details.garage_spaces 
                    ELSE 0 
                END
            ) as property_details,
            
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
            
            -- Price history validation
            price_history,
            
            -- Add Silver tier metadata
            CURRENT_TIMESTAMP as silver_processed_at,
            'silver_processor_v1.0' as processing_version
            
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
        """Validate input data for Silver processing."""
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
                'listing_id', 'listing_price', 'property_details', 
                'address', 'coordinates', 'description'
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
        """Validate Silver tier output data quality."""
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
        """Get Silver processing metrics."""
        return self.metrics.copy()