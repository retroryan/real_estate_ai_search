"""
Field mapping transformations for standardizing field names between pipeline stages.

This module provides a FieldMapper class that transforms DataFrame columns to match
the expected field names in Elasticsearch document models. It uses a JSON configuration
file to define deterministic mappings between source and destination field names.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, lit, array, struct, when, coalesce
from pyspark.sql.types import StringType, IntegerType, FloatType, ArrayType, StructType, StructField
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class FieldMappingConfig(BaseModel):
    """Configuration for field mappings."""
    field_mappings: Dict[str, str] = Field(default_factory=dict, description="Direct field name mappings")
    nested_object_mappings: Dict[str, Dict[str, str]] = Field(default_factory=dict, description="Nested object field mappings")
    type_conversions: Dict[str, str] = Field(default_factory=dict, description="Field type conversions")
    list_fields: List[str] = Field(default_factory=list, description="Fields that should be treated as lists")
    required_fields: List[str] = Field(default_factory=list, description="Required fields for validation")

    @field_validator('type_conversions')
    @classmethod
    def validate_type_conversions(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Validate that type conversions are supported."""
        valid_types = {'string', 'int', 'float', 'boolean', 'array'}
        for field, type_name in v.items():
            if type_name not in valid_types:
                raise ValueError(f"Unsupported type conversion '{type_name}' for field '{field}'")
        return v


class MappingConfiguration(BaseModel):
    """Complete mapping configuration for all entity types."""
    property_mappings: FieldMappingConfig
    neighborhood_mappings: FieldMappingConfig
    wikipedia_mappings: FieldMappingConfig
    wikipedia_enrichment_mappings: Dict[str, Dict[str, str]] = Field(default_factory=dict, description="Wikipedia enrichment field mappings")


class FieldMappingResult(BaseModel):
    """Result of field mapping operation."""
    dataframe: Optional[Any] = Field(None, description="Transformed DataFrame")  # Using Any to avoid Spark dependency
    mapped_fields: List[str] = Field(default_factory=list, description="List of fields that were mapped")
    missing_required_fields: List[str] = Field(default_factory=list, description="Required fields that were missing")
    unmapped_fields: List[str] = Field(default_factory=list, description="Source fields that weren't mapped")
    warnings: List[str] = Field(default_factory=list, description="Transformation warnings")

    class Config:
        arbitrary_types_allowed = True


class FieldMapper:
    """
    Field mapper for standardizing field names between pipeline stages.
    
    This class transforms Spark DataFrames to ensure field names match what
    the search pipeline expects. It uses a JSON configuration file to define
    mappings between source (Spark) and destination (search document) field names.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the field mapper.
        
        Args:
            config_path: Path to the field mappings JSON config file.
                        If None, uses default path relative to this module.
        """
        self.config_path = config_path or self._get_default_config_path()
        self.mapping_config = self._load_configuration()
        
    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        module_dir = Path(__file__).parent.parent
        return str(module_dir / "config" / "field_mappings.json")
    
    def _load_configuration(self) -> MappingConfiguration:
        """Load the field mapping configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
            
            return MappingConfiguration(**config_data)
            
        except FileNotFoundError:
            logger.error(f"Field mapping configuration file not found: {self.config_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading field mapping configuration: {e}")
            raise
    
    def map_property_fields(self, df: DataFrame) -> FieldMappingResult:
        """
        Map property DataFrame fields to search document field names.
        
        Args:
            df: Property DataFrame with source field names
            
        Returns:
            FieldMappingResult with transformed DataFrame and mapping info
        """
        return self._apply_field_mappings(df, self.mapping_config.property_mappings, "property")
    
    def map_neighborhood_fields(self, df: DataFrame) -> FieldMappingResult:
        """
        Map neighborhood DataFrame fields to search document field names.
        
        Args:
            df: Neighborhood DataFrame with source field names
            
        Returns:
            FieldMappingResult with transformed DataFrame and mapping info
        """
        return self._apply_field_mappings(df, self.mapping_config.neighborhood_mappings, "neighborhood")
    
    def map_wikipedia_fields(self, df: DataFrame) -> FieldMappingResult:
        """
        Map Wikipedia DataFrame fields to search document field names.
        
        Args:
            df: Wikipedia DataFrame with source field names
            
        Returns:
            FieldMappingResult with transformed DataFrame and mapping info
        """
        return self._apply_field_mappings(df, self.mapping_config.wikipedia_mappings, "wikipedia")
    
    def _apply_field_mappings(
        self,
        df: DataFrame,
        config: FieldMappingConfig,
        entity_type: str
    ) -> FieldMappingResult:
        """
        Apply field mappings to a DataFrame.
        
        Args:
            df: Source DataFrame
            config: Field mapping configuration
            entity_type: Type of entity being mapped (for logging)
            
        Returns:
            FieldMappingResult with transformed DataFrame and mapping info
        """
        logger.info(f"Applying field mappings for {entity_type}")
        
        result = FieldMappingResult()
        result.warnings = []
        result.mapped_fields = []
        result.unmapped_fields = []
        
        # Get source columns
        source_columns = set(df.columns)
        
        # Check required fields
        result.missing_required_fields = [
            field for field in config.required_fields 
            if field not in source_columns
        ]
        
        if result.missing_required_fields:
            error_msg = f"Missing required fields for {entity_type}: {result.missing_required_fields}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Start with original DataFrame
        transformed_df = df
        
        try:
            # Apply direct field mappings
            transformed_df = self._apply_direct_mappings(
                transformed_df, config.field_mappings, result
            )
            
            # Apply type conversions
            transformed_df = self._apply_type_conversions(
                transformed_df, config.type_conversions, result
            )
            
            # Apply nested object mappings
            transformed_df = self._apply_nested_mappings(
                transformed_df, config.nested_object_mappings, result
            )
            
            # Handle list fields
            transformed_df = self._handle_list_fields(
                transformed_df, config.list_fields, result
            )
            
            # Apply Wikipedia enrichment mappings if applicable
            if entity_type in ["property", "neighborhood"]:
                transformed_df = self._apply_enrichment_mappings(
                    transformed_df, result
                )
            
            # Identify unmapped fields
            final_columns = set(transformed_df.columns)
            mapped_columns = set(result.mapped_fields)
            result.unmapped_fields = list(source_columns - mapped_columns)
            
            if result.unmapped_fields:
                result.warnings.append(f"Unmapped source fields: {result.unmapped_fields}")
                logger.warning(f"Unmapped fields in {entity_type}: {result.unmapped_fields}")
            
            result.dataframe = transformed_df
            logger.info(f"Successfully mapped {len(result.mapped_fields)} fields for {entity_type}")
            
        except Exception as e:
            logger.error(f"Error applying field mappings for {entity_type}: {e}")
            raise
        
        return result
    
    def _apply_direct_mappings(
        self,
        df: DataFrame,
        field_mappings: Dict[str, str],
        result: FieldMappingResult
    ) -> DataFrame:
        """Apply direct field name mappings."""
        for source_field, target_field in field_mappings.items():
            if source_field in df.columns:
                df = df.withColumnRenamed(source_field, target_field)
                result.mapped_fields.append(source_field)
                logger.debug(f"Mapped field: {source_field} -> {target_field}")
        
        return df
    
    def _apply_type_conversions(
        self,
        df: DataFrame,
        type_conversions: Dict[str, str],
        result: FieldMappingResult
    ) -> DataFrame:
        """Apply type conversions to DataFrame columns."""
        for field_name, target_type in type_conversions.items():
            if field_name in df.columns:
                try:
                    if target_type == "int":
                        df = df.withColumn(field_name, col(field_name).cast(IntegerType()))
                    elif target_type == "float":
                        df = df.withColumn(field_name, col(field_name).cast(FloatType()))
                    elif target_type == "string":
                        df = df.withColumn(field_name, col(field_name).cast(StringType()))
                    elif target_type == "array":
                        # Handle array conversion if the field is a string with delimiters
                        df = df.withColumn(
                            field_name,
                            when(col(field_name).isNotNull(), 
                                 array(col(field_name))).otherwise(array())
                        )
                    
                    logger.debug(f"Applied type conversion: {field_name} -> {target_type}")
                
                except Exception as e:
                    warning = f"Failed to convert {field_name} to {target_type}: {e}"
                    result.warnings.append(warning)
                    logger.warning(warning)
        
        return df
    
    def _apply_nested_mappings(
        self,
        df: DataFrame,
        nested_mappings: Dict[str, Dict[str, str]],
        result: FieldMappingResult
    ) -> DataFrame:
        """Apply nested object field mappings."""
        for object_name, field_map in nested_mappings.items():
            # Check if any of the source fields exist
            available_fields = {src: dst for src, dst in field_map.items() if src in df.columns}
            
            if available_fields:
                if object_name == "address":
                    df = self._create_address_object(df, available_fields, result)
                elif object_name == "neighborhood":
                    df = self._create_neighborhood_object(df, available_fields, result)
                elif object_name == "parking":
                    df = self._create_parking_object(df, available_fields, result)
        
        return df
    
    def _create_address_object(
        self,
        df: DataFrame,
        field_map: Dict[str, str],
        result: FieldMappingResult
    ) -> DataFrame:
        """Create nested address object from flat fields."""
        address_fields = []
        location_fields = []
        
        # Build address struct fields
        for source_field, target_path in field_map.items():
            if source_field in df.columns:
                if target_path.startswith("address.location["):
                    # Handle location array separately
                    if target_path.endswith("[0]"):  # longitude
                        location_fields.append(("longitude", source_field))
                    elif target_path.endswith("[1]"):  # latitude
                        location_fields.append(("latitude", source_field))
                else:
                    # Regular address field
                    field_name = target_path.replace("address.", "")
                    address_fields.append((field_name, source_field))
                    
                result.mapped_fields.append(source_field)
        
        # Create location array if we have coordinates
        if len(location_fields) == 2:
            lon_field = next(field for coord_type, field in location_fields if coord_type == "longitude")
            lat_field = next(field for coord_type, field in location_fields if coord_type == "latitude")
            
            df = df.withColumn(
                "location_array",
                when(
                    col(lon_field).isNotNull() & col(lat_field).isNotNull(),
                    array(col(lon_field).cast(FloatType()), col(lat_field).cast(FloatType()))
                ).otherwise(lit(None))
            )
            address_fields.append(("location", "location_array"))
        
        # Create address struct
        if address_fields:
            struct_fields = []
            for field_name, source_field in address_fields:
                struct_fields.append(col(source_field).alias(field_name))
            
            df = df.withColumn("address", struct(*struct_fields))
        
        return df
    
    def _create_neighborhood_object(
        self,
        df: DataFrame,
        field_map: Dict[str, str],
        result: FieldMappingResult
    ) -> DataFrame:
        """Create nested neighborhood object from flat fields."""
        neighborhood_fields = []
        
        for source_field, target_path in field_map.items():
            if source_field in df.columns:
                field_name = target_path.replace("neighborhood.", "")
                neighborhood_fields.append((field_name, source_field))
                result.mapped_fields.append(source_field)
        
        if neighborhood_fields:
            struct_fields = []
            for field_name, source_field in neighborhood_fields:
                struct_fields.append(col(source_field).alias(field_name))
            
            df = df.withColumn("neighborhood", struct(*struct_fields))
        
        return df
    
    def _create_parking_object(
        self,
        df: DataFrame,
        field_map: Dict[str, str],
        result: FieldMappingResult
    ) -> DataFrame:
        """Create nested parking object from flat fields."""
        parking_fields = []
        
        for source_field, target_path in field_map.items():
            if source_field in df.columns:
                field_name = target_path.replace("parking.", "")
                parking_fields.append((field_name, source_field))
                result.mapped_fields.append(source_field)
        
        if parking_fields:
            struct_fields = []
            for field_name, source_field in parking_fields:
                struct_fields.append(col(source_field).alias(field_name))
            
            df = df.withColumn("parking", struct(*struct_fields))
        
        return df
    
    def _handle_list_fields(
        self,
        df: DataFrame,
        list_fields: List[str],
        result: FieldMappingResult
    ) -> DataFrame:
        """Handle fields that should be treated as arrays."""
        for field_name in list_fields:
            if field_name in df.columns:
                # If field is a string, try to convert to array
                # This handles cases where lists are stored as comma-separated strings
                df = df.withColumn(
                    field_name,
                    when(
                        col(field_name).isNotNull() & (col(field_name) != ""),
                        # Handle both single values and comma-separated strings
                        when(
                            col(field_name).contains(","),
                            # Split comma-separated string
                            array(*[lit(item.strip()) for item in col(field_name).cast(StringType()).split(",")])
                        ).otherwise(
                            # Single value -> array
                            array(col(field_name).cast(StringType()))
                        )
                    ).otherwise(array())  # Empty array for null values
                )
                
                logger.debug(f"Converted {field_name} to array type")
        
        return df
    
    def _apply_enrichment_mappings(
        self,
        df: DataFrame,
        result: FieldMappingResult
    ) -> DataFrame:
        """Apply Wikipedia enrichment field mappings."""
        enrichment_mappings = self.mapping_config.wikipedia_enrichment_mappings
        
        for object_name, field_map in enrichment_mappings.items():
            # Check if any enrichment fields are present
            available_fields = {src: dst for src, dst in field_map.items() if src in df.columns}
            
            if available_fields:
                if object_name == "location_context":
                    df = self._create_location_context_object(df, available_fields, result)
                elif object_name == "neighborhood_context":
                    df = self._create_neighborhood_context_object(df, available_fields, result)
                elif object_name == "location_scores":
                    df = self._create_location_scores_object(df, available_fields, result)
        
        return df
    
    def _create_location_context_object(
        self,
        df: DataFrame,
        field_map: Dict[str, str],
        result: FieldMappingResult
    ) -> DataFrame:
        """Create nested location_context object."""
        struct_fields = []
        
        for source_field, target_path in field_map.items():
            if source_field in df.columns:
                field_name = target_path.replace("location_context.", "")
                struct_fields.append(col(source_field).alias(field_name))
                result.mapped_fields.append(source_field)
        
        if struct_fields:
            df = df.withColumn("location_context", struct(*struct_fields))
        
        return df
    
    def _create_neighborhood_context_object(
        self,
        df: DataFrame,
        field_map: Dict[str, str],
        result: FieldMappingResult
    ) -> DataFrame:
        """Create nested neighborhood_context object."""
        struct_fields = []
        
        for source_field, target_path in field_map.items():
            if source_field in df.columns:
                field_name = target_path.replace("neighborhood_context.", "")
                struct_fields.append(col(source_field).alias(field_name))
                result.mapped_fields.append(source_field)
        
        if struct_fields:
            df = df.withColumn("neighborhood_context", struct(*struct_fields))
        
        return df
    
    def _create_location_scores_object(
        self,
        df: DataFrame,
        field_map: Dict[str, str],
        result: FieldMappingResult
    ) -> DataFrame:
        """Create nested location_scores object."""
        struct_fields = []
        
        for source_field, target_path in field_map.items():
            if source_field in df.columns:
                field_name = target_path.replace("location_scores.", "")
                struct_fields.append(col(source_field).alias(field_name))
                result.mapped_fields.append(source_field)
        
        if struct_fields:
            df = df.withColumn("location_scores", struct(*struct_fields))
        
        return df
    
    def validate_required_fields(
        self,
        df: DataFrame,
        entity_type: str
    ) -> List[str]:
        """
        Validate that required fields are present in the DataFrame.
        
        Args:
            df: DataFrame to validate
            entity_type: Type of entity (property, neighborhood, wikipedia)
            
        Returns:
            List of missing required fields
        """
        config_map = {
            "property": self.mapping_config.property_mappings,
            "neighborhood": self.mapping_config.neighborhood_mappings,
            "wikipedia": self.mapping_config.wikipedia_mappings,
        }
        
        if entity_type not in config_map:
            raise ValueError(f"Unknown entity type: {entity_type}")
        
        config = config_map[entity_type]
        df_columns = set(df.columns)
        
        missing_fields = [
            field for field in config.required_fields
            if field not in df_columns
        ]
        
        return missing_fields