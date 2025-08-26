"""
DataFrame transformations for Elasticsearch compatibility.

This module provides clean, testable functions for transforming DataFrames
to be compatible with Elasticsearch requirements.
"""

import logging
from typing import List

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, struct, when, isnan, isnull, expr, transform
from pyspark.sql.types import DecimalType, DoubleType, ArrayType, StructType

from data_pipeline.writers.elasticsearch.models import SchemaTransformation

logger = logging.getLogger(__name__)


class DataFrameTransformer:
    """
    Handles DataFrame transformations for Elasticsearch compatibility.
    
    Uses a simple, functional approach that's easy to test and debug.
    """
    
    def __init__(self, spark: SparkSession):
        """Initialize transformer with Spark session."""
        self.spark = spark
        self.logger = logging.getLogger(__name__)
    
    def transform_for_elasticsearch(
        self, 
        df: DataFrame, 
        transform_config: SchemaTransformation,
        id_field: str
    ) -> DataFrame:
        """
        Apply all necessary transformations for Elasticsearch compatibility.
        
        Args:
            df: Input DataFrame
            transform_config: Transformation configuration
            id_field: Field to use as document ID
            
        Returns:
            Transformed DataFrame ready for Elasticsearch
        """
        self.logger.debug(f"Starting DataFrame transformation for ES with {df.count()} records")
        
        # 1. Set up document ID field
        if id_field in df.columns and id_field != "id":
            df = df.withColumn("id", col(id_field))
        
        # 2. Convert decimal types if needed
        if transform_config.convert_decimals:
            df = self._convert_decimal_types_simple(df)
        
        # 3. Add geo_point if requested and fields exist
        if transform_config.add_geo_point:
            df = self._add_geo_point_field(
                df, 
                transform_config.latitude_field, 
                transform_config.longitude_field
            )
        
        # 4. Exclude specified fields
        if transform_config.excluded_fields:
            available_columns = set(df.columns)
            keep_columns = available_columns - transform_config.excluded_fields
            df = df.select(*sorted(keep_columns))
        
        self.logger.debug(f"Transformation complete. Final columns: {df.columns}")
        return df
    
    def _convert_decimal_types_simple(self, df: DataFrame) -> DataFrame:
        """
        Convert decimal columns to double using a robust approach.
        
        Handles both simple and complex nested decimal types.
        """
        decimal_columns = self._find_decimal_columns(df)
        
        if not decimal_columns:
            return df
        
        self.logger.debug(f"Found columns with decimal types: {decimal_columns}")
        
        # Separate simple and complex columns
        simple_columns = []
        complex_columns = []
        
        for col_name in decimal_columns:
            field = [f for f in df.schema.fields if f.name == col_name][0]
            if isinstance(field.dataType, DecimalType):
                # Direct decimal column - can cast directly
                simple_columns.append(col_name)
            else:
                # Complex nested structure with decimals
                complex_columns.append(col_name)
        
        # Handle simple columns with direct casting
        for col_name in simple_columns:
            df = df.withColumn(col_name, col(col_name).cast(DoubleType()))
            self.logger.debug(f"Converted simple decimal column: {col_name}")
        
        # Handle complex columns by creating ES-compatible versions
        if complex_columns:
            self.logger.debug(f"Converting complex decimal columns for ES compatibility: {complex_columns}")
            df = self._convert_complex_decimals_for_es(df, complex_columns)
        
        return df
    
    def _find_decimal_columns(self, df: DataFrame) -> List[str]:
        """
        Find all columns that contain decimal types (including nested ones).
        
        This includes:
        - Direct decimal columns
        - Arrays with decimal elements  
        - Structs with decimal fields
        - Complex nested combinations
        """
        decimal_columns = []
        
        for field in df.schema.fields:
            if self._field_has_decimals(field):
                decimal_columns.append(field.name)
        
        return decimal_columns
    
    def _field_has_decimals(self, field) -> bool:
        """Check if a field contains decimal types anywhere in its structure."""
        return self._data_type_has_decimals(field.dataType)
    
    def _data_type_has_decimals(self, data_type) -> bool:
        """Recursively check if a data type contains decimals."""
        if isinstance(data_type, DecimalType):
            return True
        elif isinstance(data_type, ArrayType):
            return self._data_type_has_decimals(data_type.elementType)
        elif isinstance(data_type, StructType):
            return any(self._data_type_has_decimals(field.dataType) for field in data_type.fields)
        else:
            return False
    
    def _convert_complex_decimals_for_es(self, df: DataFrame, complex_columns: List[str]) -> DataFrame:
        """
        Convert complex decimal columns to ES-compatible types without modifying source data.
        
        This creates transformed versions of complex columns that Elasticsearch can handle,
        while preserving the original data structure for other writers (like Neo4j).
        """
        
        for col_name in complex_columns:
            try:
                field = [f for f in df.schema.fields if f.name == col_name][0]
                
                if isinstance(field.dataType, ArrayType):
                    element_type = field.dataType.elementType
                    
                    if isinstance(element_type, StructType):
                        # Handle array of structs with decimal fields (like price_history)
                        df = self._convert_struct_array_decimals(df, col_name, element_type)
                    elif isinstance(element_type, DecimalType):
                        # Handle array of decimals
                        df = df.withColumn(col_name, expr(f"TRANSFORM({col_name}, x -> CAST(x AS DOUBLE))"))
                
                elif isinstance(field.dataType, StructType):
                    # Handle struct with decimal fields
                    df = self._convert_struct_decimals(df, col_name, field.dataType)
                
                self.logger.debug(f"Successfully converted complex column: {col_name}")
                
            except Exception as e:
                self.logger.warning(f"Could not convert complex column {col_name}: {e}")
                # Remove problematic column as fallback
                df = df.drop(col_name)
        
        return df
    
    def _convert_struct_array_decimals(self, df: DataFrame, col_name: str, struct_type: StructType) -> DataFrame:
        """Convert decimal fields within an array of structs."""
        
        # Build struct fields with decimal conversions
        struct_fields = []
        for struct_field in struct_type.fields:
            field_ref = f"x.{struct_field.name}"
            if isinstance(struct_field.dataType, DecimalType):
                struct_fields.append(f"CAST({field_ref} AS DOUBLE) AS {struct_field.name}")
            else:
                struct_fields.append(f"{field_ref} AS {struct_field.name}")
        
        # Use SQL expression for complex transformation
        struct_expr = f"STRUCT({', '.join(struct_fields)})"
        transform_expr = f"TRANSFORM({col_name}, x -> {struct_expr})"
        
        return df.withColumn(col_name, expr(transform_expr))
    
    def _convert_struct_decimals(self, df: DataFrame, col_name: str, struct_type: StructType) -> DataFrame:
        """Convert decimal fields within a struct."""
        
        # Build new struct with converted fields
        struct_fields = []
        for struct_field in struct_type.fields:
            field_col = col(f"{col_name}.{struct_field.name}")
            if isinstance(struct_field.dataType, DecimalType):
                struct_fields.append(field_col.cast("double").alias(struct_field.name))
            else:
                struct_fields.append(field_col.alias(struct_field.name))
        
        return df.withColumn(col_name, struct(*struct_fields))
    
    def _add_geo_point_field(
        self, 
        df: DataFrame, 
        lat_col: str = "latitude", 
        lon_col: str = "longitude"
    ) -> DataFrame:
        """
        Add a geo_point field from latitude and longitude columns.
        
        Args:
            df: Input DataFrame
            lat_col: Name of latitude column
            lon_col: Name of longitude column
            
        Returns:
            DataFrame with location field added if lat/lon exist
        """
        if lat_col not in df.columns or lon_col not in df.columns:
            self.logger.debug(f"Geo columns {lat_col}/{lon_col} not found, skipping geo_point")
            return df
        
        self.logger.debug(f"Adding geo_point field from {lat_col}/{lon_col}")
        
        # Create geo_point structure with null handling
        df = df.withColumn(
            "location",
            when(
                (col(lat_col).isNotNull()) & 
                (col(lon_col).isNotNull()) & 
                (~isnan(col(lat_col))) & 
                (~isnan(col(lon_col))),
                struct(
                    col(lat_col).alias("lat"),
                    col(lon_col).alias("lon")
                )
            ).otherwise(None)
        )
        
        return df
    
    def get_transformation_summary(self, df: DataFrame) -> dict:
        """
        Get summary information about a DataFrame for logging.
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            Dictionary with summary information
        """
        try:
            return {
                "column_count": len(df.columns),
                "columns": df.columns,
                "record_count": df.count(),
                "has_geo_fields": "latitude" in df.columns and "longitude" in df.columns,
                "has_id_field": "id" in df.columns,
            }
        except Exception as e:
            self.logger.warning(f"Could not generate transformation summary: {e}")
            return {"error": str(e)}


class ComplexSchemaTransformer:
    """
    Handles complex nested schema transformations for advanced use cases.
    
    Separated from the simple transformer to keep the main path clean.
    """
    
    def __init__(self, spark: SparkSession):
        """Initialize complex transformer."""
        self.spark = spark
        self.logger = logging.getLogger(__name__)
    
    def convert_nested_decimal_types(self, df: DataFrame) -> DataFrame:
        """
        Convert decimal types in nested structures (arrays, structs).
        
        This is more complex and should only be used when necessary.
        """
        self.logger.debug("Starting complex nested decimal conversion")
        
        # Create a temporary view for SQL-based transformation
        temp_view = f"temp_df_{id(df)}"
        df.createOrReplaceTempView(temp_view)
        
        try:
            # Build transformation SQL
            select_expressions = []
            
            for field in df.schema.fields:
                if self._field_contains_decimals(field):
                    # Complex transformation for this field
                    expr = self._build_decimal_conversion_expression(field)
                    select_expressions.append(f"{expr} AS {field.name}")
                else:
                    select_expressions.append(field.name)
            
            sql_query = f"SELECT {', '.join(select_expressions)} FROM {temp_view}"
            result_df = self.spark.sql(sql_query)
            
            self.logger.debug("Complex decimal conversion completed")
            return result_df
            
        except Exception as e:
            self.logger.error(f"Complex decimal conversion failed: {e}")
            # Fall back to original DataFrame
            return df
        finally:
            # Clean up temporary view
            self.spark.catalog.dropTempView(temp_view)
    
    def _field_contains_decimals(self, field) -> bool:
        """Check if a field contains decimal types recursively."""
        return self._data_type_has_decimal(field.dataType)
    
    def _data_type_has_decimal(self, data_type) -> bool:
        """Check if a data type contains decimal types."""
        if isinstance(data_type, DecimalType):
            return True
        elif isinstance(data_type, ArrayType):
            return self._data_type_has_decimal(data_type.elementType)
        elif isinstance(data_type, StructType):
            return any(self._data_type_has_decimal(field.dataType) for field in data_type.fields)
        else:
            return False
    
    def _build_decimal_conversion_expression(self, field) -> str:
        """Build SQL expression to convert decimal types in complex structures."""
        # For now, convert the entire field to string and back
        # This is a simplified approach - full implementation would be more complex
        return f"CAST({field.name} AS STRING)"