"""Simplified Gold tier processor for data enrichment."""

from typing import Dict, Any

from squack_pipeline.config.schemas import MedallionTier
from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.processors.base import TransformationProcessor
from squack_pipeline.utils.logging import log_execution_time


class GoldProcessor(TransformationProcessor):
    """Simplified processor for Gold tier - basic data enrichment."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize Gold processor."""
        super().__init__(settings)
        self.set_tier(MedallionTier.GOLD)
        self.metrics = {
            "records_processed": 0,
            "records_enriched": 0,
            "features_added": 0,
            "enrichment_completeness": 0.0
        }
    
    @log_execution_time
    def get_transformation_query(self, input_table: str) -> str:
        """Get SQL transformation query for Gold tier enrichment."""
        current_year = 2025
        
        return f"""
        SELECT 
            -- Original Silver tier data
            *,
            
            -- ENRICHMENT: Property Value Analysis
            CASE 
                WHEN property_details.bedrooms > 0 
                THEN ROUND(listing_price / property_details.bedrooms, 2)
                ELSE NULL 
            END as price_per_bedroom,
            
            CASE 
                WHEN property_details.bathrooms > 0 
                THEN ROUND(listing_price / property_details.bathrooms, 2)
                ELSE NULL 
            END as price_per_bathroom,
            
            -- Property value category
            CASE 
                WHEN listing_price >= 1000000 THEN 'luxury'
                WHEN listing_price >= 500000 THEN 'premium'
                WHEN listing_price >= 300000 THEN 'mid_market'
                WHEN listing_price >= 150000 THEN 'affordable'
                ELSE 'budget'
            END as value_category,
            
            -- Property age
            CASE 
                WHEN property_details.year_built IS NOT NULL 
                THEN {current_year} - property_details.year_built
                ELSE NULL 
            END as property_age_years,
            
            -- Size category
            CASE 
                WHEN property_details.square_feet >= 3000 THEN 'large'
                WHEN property_details.square_feet >= 1800 THEN 'medium'
                WHEN property_details.square_feet >= 1000 THEN 'small'
                ELSE 'compact'
            END as size_category,
            
            -- Market status based on days on market
            CASE 
                WHEN days_on_market <= 7 THEN 'new_listing'
                WHEN days_on_market <= 30 THEN 'active'
                WHEN days_on_market <= 90 THEN 'stale'
                ELSE 'long_term'
            END as market_status,
            
            -- Age category
            CASE 
                WHEN property_details.year_built IS NOT NULL THEN
                    CASE 
                        WHEN {current_year} - property_details.year_built <= 5 THEN 'new_construction'
                        WHEN {current_year} - property_details.year_built <= 15 THEN 'modern'
                        WHEN {current_year} - property_details.year_built <= 30 THEN 'established'
                        WHEN {current_year} - property_details.year_built <= 50 THEN 'mature'
                        ELSE 'historic'
                    END
                ELSE 'unknown_age'
            END as age_category,
            
            -- Coordinate validation flag
            CASE 
                WHEN coordinates.latitude IS NOT NULL AND coordinates.longitude IS NOT NULL 
                THEN true 
                ELSE false 
            END as has_valid_coordinates,
            
            -- Simple desirability score (0-100)
            LEAST(100, GREATEST(0, 
                COALESCE(
                    CASE WHEN property_details.bedrooms >= 3 THEN 20 ELSE property_details.bedrooms * 6 END +
                    CASE WHEN property_details.bathrooms >= 2 THEN 20 ELSE property_details.bathrooms * 10 END +
                    CASE WHEN property_details.square_feet >= 2000 THEN 20 ELSE property_details.square_feet / 100 END +
                    CASE WHEN property_details.garage_spaces > 0 THEN 10 ELSE 0 END +
                    CASE WHEN days_on_market <= 30 THEN 15 ELSE GREATEST(0, 15 - days_on_market/10) END
                , 0)
            )) as desirability_score,
            
            -- Description quality score
            CASE 
                WHEN LENGTH(description) >= 200 THEN 100
                WHEN LENGTH(description) >= 100 THEN 75
                WHEN LENGTH(description) >= 50 THEN 50
                ELSE 25
            END as description_quality_score,
            
            -- Gold tier metadata
            CURRENT_TIMESTAMP as gold_processed_at,
            'gold_processor_simple_v1.0' as gold_processing_version
            
        FROM {input_table}
        ORDER BY listing_price DESC
        """
    
    def validate_input(self, table_name: str) -> bool:
        """Validate input data for Gold processing."""
        if not self.connection:
            return False
        
        try:
            # Check table exists and has data
            count = self.count_records(table_name)
            if count == 0:
                self.logger.error(f"Input table {table_name} is empty")
                return False
            
            # Check Silver tier specific requirements
            schema = self.get_table_schema(table_name)
            required_columns = [
                'listing_id', 'listing_price', 'property_details', 
                'silver_processed_at'
            ]
            
            missing_columns = [col for col in required_columns if col not in schema]
            if missing_columns:
                self.logger.error(f"Missing Silver tier columns: {missing_columns}")
                return False
            
            self.logger.success(f"Gold input validation passed for {table_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Gold input validation failed: {e}")
            return False
    
    def validate_output(self, table_name: str) -> bool:
        """Validate Gold tier output with enrichment completeness."""
        if not self.connection:
            return False
        
        try:
            total_records = self.count_records(table_name)
            if total_records == 0:
                self.logger.error("No records in Gold output")
                return False
            
            # Check enrichment completeness
            enrichment_query = f"""
            SELECT 
                COUNT(*) as total_records,
                COUNT(price_per_bedroom) as has_price_per_bedroom,
                COUNT(property_age_years) as has_property_age,
                COUNT(desirability_score) as has_desirability_score,
                AVG(CASE WHEN desirability_score > 0 THEN 1.0 ELSE 0.0 END) as desirability_completeness,
                COUNT(CASE WHEN has_valid_coordinates THEN 1 END) as valid_coordinates_count
            FROM {table_name}
            """
            
            result = self.execute_sql(enrichment_query).fetchone()
            if result:
                (total, has_ppb, has_age, has_desir, 
                 desir_complete, valid_coords) = result
                
                # Calculate enrichment metrics
                enrichment_rate = (has_ppb + has_age + has_desir) / (total * 3) if total > 0 else 0
                self.metrics.update({
                    "records_processed": total,
                    "records_enriched": total,
                    "features_added": 8,  # Number of enrichment features added
                    "enrichment_completeness": enrichment_rate
                })
                
                # Log enrichment metrics
                self.logger.info(f"Enrichment completeness: {enrichment_rate:.2%}")
                self.logger.info(f"Records with price per bedroom: {has_ppb}/{total}")
                self.logger.info(f"Records with valid coordinates: {valid_coords}/{total}")
                self.logger.info(f"Average desirability completeness: {desir_complete:.2%}")
                
                # Validation threshold
                if enrichment_rate < 0.7:
                    self.logger.warning(f"Enrichment completeness below threshold: {enrichment_rate:.2%}")
                
            self.logger.success(f"Gold output validation passed for {table_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Gold output validation failed: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get Gold processing metrics."""
        return self.metrics.copy()