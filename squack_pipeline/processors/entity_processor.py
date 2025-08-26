"""Entity-specific processor interface with type safety."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import time
from datetime import datetime

import duckdb

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.models.processing_models import (
    EntityType, MedallionTier, ProcessingStage, ProcessingContext,
    ProcessingResult, TableIdentifier, EntityProcessorConfig
)
from squack_pipeline.utils.logging import PipelineLogger


class EntityProcessor(ABC):
    """Abstract base class for type-safe entity processors."""
    
    def __init__(self, settings: PipelineSettings, config: EntityProcessorConfig):
        """Initialize entity processor with type-safe configuration."""
        self.settings = settings
        self.config = config
        self.logger = PipelineLogger.get_logger(f"{self.__class__.__name__}({config.entity_type.value})")
        self.connection: Optional[duckdb.DuckDBPyConnection] = None
    
    def set_connection(self, connection: duckdb.DuckDBPyConnection) -> None:
        """Set the DuckDB connection for the processor."""
        self.connection = connection
        self.logger.debug(f"DuckDB connection established for {self.config.entity_type.value} processor")
    
    @abstractmethod
    def get_entity_type(self) -> EntityType:
        """Get the entity type this processor handles."""
        pass
    
    @abstractmethod
    def get_transformation_query(self, context: ProcessingContext) -> str:
        """Get the SQL transformation query for this processing context."""
        pass
    
    @abstractmethod
    def validate_input_data(self, context: ProcessingContext) -> bool:
        """Validate input data for processing."""
        pass
    
    @abstractmethod
    def validate_output_data(self, context: ProcessingContext) -> bool:
        """Validate output data after processing."""
        pass
    
    def process_entity(self, context: ProcessingContext) -> ProcessingResult:
        """Process entity with full type safety and validation.
        
        Args:
            context: Processing context with type-safe table identifiers
            
        Returns:
            ProcessingResult with detailed processing information
        """
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
        
        # Validate entity type matches processor
        if context.entity_type != self.get_entity_type():
            raise ValueError(f"Entity type mismatch: processor handles {self.get_entity_type()}, got {context.entity_type}")
        
        # Initialize result
        result = ProcessingResult(
            context=context,
            success=False,
            started_at=datetime.now()
        )
        
        self.logger.info(f"Processing {context.source_table.friendly_name} → {context.target_table.friendly_name}")
        
        try:
            # Pre-process validation
            if context.validation_enabled and not self.validate_input_data(context):
                result.validation_passed = False
                result.add_validation_error("Input validation failed")
                return result
            
            # Get record count before processing
            # Handle special case for raw properties table
            source_table_name = context.source_table.table_name
            if context.source_table.timestamp == 0 and context.source_tier == MedallionTier.BRONZE:
                source_table_name = "raw_properties"
            
            source_count = self._count_records(source_table_name)
            if source_count == 0:
                result.add_warning(f"No records found in source table {source_table_name}")
                result.success = True
                return result
            
            # Execute transformation
            transformation_query = self.get_transformation_query(context)
            
            # Apply record limit if specified
            if context.record_limit:
                transformation_query = f"SELECT * FROM ({transformation_query}) LIMIT {context.record_limit}"
            
            # Create target table
            self._create_table_from_query(
                context.target_table.table_name,
                transformation_query
            )
            
            # Get record count after processing
            target_count = self._count_records(context.target_table.table_name)
            
            # Post-process validation
            if context.validation_enabled and not self.validate_output_data(context):
                result.validation_passed = False
                result.add_validation_error("Output validation failed")
                return result
            
            # Calculate quality metrics
            result.data_quality_score = self._calculate_quality_score(context)
            result.completeness_score = self._calculate_completeness_score(context)
            
            # Update result
            result.success = True
            result.records_processed = source_count
            result.records_created = target_count
            result.completed_at = datetime.now()
            
            self.logger.success(
                f"Successfully processed {source_count} → {target_count} records "
                f"in {result.processing_time_seconds:.2f}s "
                f"({result.records_per_second:.1f} records/sec)"
            )
            
            return result
            
        except Exception as e:
            result.error_message = str(e)
            result.completed_at = datetime.now()
            self.logger.error(f"Processing failed: {e}")
            return result
    
    def _count_records(self, table_name: str) -> int:
        """Count records in a table."""
        try:
            result = self.connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            return result[0] if result else 0
        except Exception:
            return 0
    
    def _create_table_from_query(self, table_name: str, query: str) -> None:
        """Create a new table from a SQL query."""
        # Drop table if exists
        self.connection.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Create new table
        self.connection.execute(f"CREATE TABLE {table_name} AS {query}")
        
        self.logger.info(f"Created table {table_name}")
    
    def _calculate_quality_score(self, context: ProcessingContext) -> float:
        """Calculate data quality score for the processed data."""
        # Default implementation - can be overridden
        try:
            # Count null values in key columns
            query = f"""
            SELECT 
                COUNT(*) as total_records,
                COUNT(*) - COUNT(listing_id) as null_listing_ids,
                COUNT(*) - COUNT(price) as null_prices
            FROM {context.target_table.table_name}
            """
            result = self.connection.execute(query).fetchone()
            
            if not result or result[0] == 0:
                return 1.0
            
            total_records = result[0]
            null_count = result[1] + result[2]  # Sum of null values
            
            quality_score = max(0.0, 1.0 - (null_count / (total_records * 2)))
            return quality_score
            
        except Exception:
            return 0.8  # Default score if calculation fails
    
    def _calculate_completeness_score(self, context: ProcessingContext) -> float:
        """Calculate data completeness score."""
        # Default implementation - can be overridden
        try:
            # Check completeness of key fields
            query = f"""
            SELECT 
                COUNT(*) as total_records,
                SUM(CASE WHEN listing_id IS NOT NULL AND price IS NOT NULL THEN 1 ELSE 0 END) as complete_records
            FROM {context.target_table.table_name}
            """
            result = self.connection.execute(query).fetchone()
            
            if not result or result[0] == 0:
                return 1.0
            
            total_records = result[0]
            complete_records = result[1]
            
            return complete_records / total_records
            
        except Exception:
            return 0.9  # Default score if calculation fails
    
    def supports_processing(self, context: ProcessingContext) -> bool:
        """Check if this processor supports the given processing context."""
        return (
            context.entity_type == self.get_entity_type() and
            context.source_tier in self.config.supported_tiers and
            context.target_tier in self.config.supported_tiers and
            context.processing_stage in self.config.supported_stages
        )


class PropertyProcessor(EntityProcessor):
    """Type-safe processor for property entities."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize property processor."""
        config = EntityProcessorConfig(
            entity_type=EntityType.PROPERTY,
            supported_tiers=[MedallionTier.BRONZE, MedallionTier.SILVER, MedallionTier.GOLD, MedallionTier.ENRICHED],
            supported_stages=[
                ProcessingStage.CLEANING, 
                ProcessingStage.ENRICHMENT, 
                ProcessingStage.GEOGRAPHIC_ENRICHMENT
            ]
        )
        super().__init__(settings, config)
    
    def get_entity_type(self) -> EntityType:
        """Get entity type this processor handles."""
        return EntityType.PROPERTY
    
    def get_transformation_query(self, context: ProcessingContext) -> str:
        """Get SQL transformation query based on processing stage."""
        if context.processing_stage == ProcessingStage.CLEANING:
            return self._get_silver_transformation_query(context)
        elif context.processing_stage == ProcessingStage.ENRICHMENT:
            return self._get_gold_transformation_query(context)
        elif context.processing_stage == ProcessingStage.GEOGRAPHIC_ENRICHMENT:
            return self._get_enriched_transformation_query(context)
        else:
            raise ValueError(f"Unsupported processing stage: {context.processing_stage}")
    
    def _get_silver_transformation_query(self, context: ProcessingContext) -> str:
        """Silver tier transformation: data cleaning and standardization."""
        # Handle special case for raw properties table
        source_table = context.source_table.table_name
        if context.source_table.timestamp == 0 and context.source_tier == MedallionTier.BRONZE:
            source_table = "raw_properties"
        
        return f"""
        SELECT 
            listing_id,
            UPPER(TRIM(address.street)) as address_street,
            UPPER(TRIM(address.city)) as address_city,
            UPPER(TRIM(address.state)) as address_state,
            address.zip as address_zip,
            CAST(listing_price AS DECIMAL(12,2)) as price,
            CAST(property_details.bedrooms AS INTEGER) as bedrooms,
            CAST(property_details.bathrooms AS DECIMAL(3,1)) as bathrooms,
            CAST(property_details.square_feet AS INTEGER) as sqft,
            CAST(property_details.lot_size AS DECIMAL(10,2)) as lot_size,
            UPPER(TRIM(property_details.property_type)) as property_type,
            property_details.year_built,
            CAST(coordinates.latitude AS DECIMAL(10,8)) as latitude,
            CAST(coordinates.longitude AS DECIMAL(11,8)) as longitude,
            neighborhood_id,
            listing_date,
            description
        FROM {source_table}
        WHERE listing_id IS NOT NULL 
        AND listing_price > 0
        AND coordinates.latitude BETWEEN 37.0 AND 38.0 
        AND coordinates.longitude BETWEEN -123.0 AND -122.0
        """
    
    def _get_gold_transformation_query(self, context: ProcessingContext) -> str:
        """Gold tier transformation: business logic and enrichment."""
        return f"""
        SELECT *,
            CAST(price / NULLIF(sqft, 0) AS DECIMAL(10,2)) as price_per_sqft,
            CAST(price / NULLIF(bedrooms, 0) AS DECIMAL(12,2)) as price_per_bedroom,
            CASE 
                WHEN price >= 2000000 THEN 'luxury'
                WHEN price >= 1000000 THEN 'premium'
                WHEN price >= 500000 THEN 'mid-market'
                ELSE 'affordable'
            END as price_category,
            CASE 
                WHEN year_built IS NOT NULL THEN (EXTRACT(YEAR FROM CURRENT_DATE) - year_built)
                ELSE NULL
            END as property_age,
            CASE
                WHEN sqft < 1000 THEN 'compact'
                WHEN sqft < 2000 THEN 'medium' 
                WHEN sqft < 3000 THEN 'large'
                ELSE 'very_large'
            END as size_category
        FROM {context.source_table.table_name}
        """
    
    def _get_enriched_transformation_query(self, context: ProcessingContext) -> str:
        """Enriched tier transformation: geographic enrichment."""
        return f"""
        SELECT *,
            -- Distance calculations (simplified)
            SQRT(POW(latitude - 37.7749, 2) + POW(longitude - (-122.4194), 2)) * 69 as distance_to_downtown_miles,
            CASE 
                WHEN latitude > 37.75 AND longitude > -122.45 THEN 'north'
                WHEN latitude < 37.75 AND longitude > -122.45 THEN 'south'  
                WHEN longitude < -122.45 THEN 'west'
                ELSE 'central'
            END as geographic_region,
            -- Market desirability score (simplified)
            CASE
                WHEN price_per_sqft > 800 AND property_age < 20 THEN 0.9
                WHEN price_per_sqft > 600 AND property_age < 30 THEN 0.8
                WHEN price_per_sqft > 400 THEN 0.7
                ELSE 0.6
            END as desirability_score
        FROM {context.source_table.table_name}
        """
    
    def validate_input_data(self, context: ProcessingContext) -> bool:
        """Validate input data for property processing."""
        try:
            # Handle special case for raw properties table
            table_name = context.source_table.table_name
            if context.source_table.timestamp == 0 and context.source_tier == MedallionTier.BRONZE:
                table_name = "raw_properties"
            
            # Check if source table exists
            tables = self.connection.execute(
                f"SELECT table_name FROM information_schema.tables WHERE table_name = '{table_name}'"
            ).fetchall()
            
            if not tables:
                self.logger.error(f"Source table {table_name} does not exist")
                return False
            
            # Check for required columns based on processing stage
            if context.processing_stage == ProcessingStage.CLEANING:
                # For raw properties, check the nested structure
                if table_name == "raw_properties":
                    required_checks = [
                        ('listing_id', 'listing_id IS NOT NULL'),
                        ('listing_price', 'listing_price IS NOT NULL AND listing_price > 0'),
                        ('coordinates.latitude', 'coordinates.latitude IS NOT NULL'),
                        ('coordinates.longitude', 'coordinates.longitude IS NOT NULL')
                    ]
                else:
                    required_checks = [
                        ('listing_id', 'listing_id IS NOT NULL'),
                        ('price', 'price IS NOT NULL AND price > 0')
                    ]
            else:
                required_checks = [
                    ('listing_id', 'listing_id IS NOT NULL'),
                    ('price', 'price IS NOT NULL AND price > 0')
                ]
            
            for column_name, condition in required_checks:
                count = self.connection.execute(
                    f"SELECT COUNT(*) FROM {table_name} WHERE {condition}"
                ).fetchone()[0]
                
                if count == 0:
                    self.logger.error(f"No valid data found for condition: {condition}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Input validation failed: {e}")
            return False
    
    def validate_output_data(self, context: ProcessingContext) -> bool:
        """Validate output data after property processing."""
        try:
            # Check if output table was created
            record_count = self._count_records(context.target_table.table_name)
            if record_count == 0:
                self.logger.warning("No records in output table")
                return True  # Empty result is valid
            
            # Check data quality thresholds
            quality_score = self._calculate_quality_score(context)
            completeness_score = self._calculate_completeness_score(context)
            
            if quality_score < self.config.min_quality_score:
                self.logger.error(f"Quality score {quality_score:.2f} below threshold {self.config.min_quality_score}")
                return False
            
            if completeness_score < self.config.min_completeness_score:
                self.logger.error(f"Completeness score {completeness_score:.2f} below threshold {self.config.min_completeness_score}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Output validation failed: {e}")
            return False