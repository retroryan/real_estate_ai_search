"""
Pydantic to Spark schema converter.

This module provides a clean, simple converter from Pydantic models to Spark schemas,
properly handling Optional types, nested models, and lists.
"""

import inspect
from decimal import Decimal
from typing import List, Optional, get_args, get_origin, Union
from enum import Enum

from pydantic import BaseModel
from pyspark.sql.types import (
    ArrayType,
    DataType,
    DecimalType,
    DoubleType,
    FloatType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)


def pydantic_to_spark_schema(pydantic_model: type[BaseModel]) -> StructType:
    """
    Converts a Pydantic model to a PySpark StructType.
    
    Properly handles:
    - Optional fields (sets nullable=True)
    - Nested Pydantic models
    - List types
    - Decimal types with proper precision
    
    Args:
        pydantic_model: The Pydantic model class to convert
        
    Returns:
        StructType representing the Spark schema
    """
    fields = []
    
    for field_name, field_info in pydantic_model.model_fields.items():
        field_type = field_info.annotation
        is_nullable = False
        
        # Check for Optional[T] or Union[T, None]
        origin_type = get_origin(field_type)
        
        if origin_type is Union:
            type_args = get_args(field_type)
            # Check if it's Optional (Union with None)
            if type(None) in type_args:
                is_nullable = True
                # Get the non-None type
                non_none_types = [t for t in type_args if t is not type(None)]
                if non_none_types:
                    field_type = non_none_types[0]
        
        # Determine the Spark type
        spark_type = _get_spark_type(field_type, field_info)
        
        # Create the StructField
        fields.append(StructField(field_name, spark_type, nullable=is_nullable))
    
    return StructType(fields)


def _get_spark_type(python_type, field_info=None) -> DataType:
    """
    Maps Python/Pydantic types to Spark DataTypes.
    
    Args:
        python_type: The Python type to convert
        field_info: Optional Pydantic field info for additional metadata
        
    Returns:
        Corresponding Spark DataType
    """
    # Handle Enum types - they become strings when use_enum_values=True
    if inspect.isclass(python_type) and issubclass(python_type, Enum):
        return StringType()
    
    # Handle nested Pydantic models
    if inspect.isclass(python_type) and issubclass(python_type, BaseModel):
        return pydantic_to_spark_schema(python_type)
    
    # Handle List types
    origin = get_origin(python_type)
    if origin is list or origin is List:
        args = get_args(python_type)
        if args:
            inner_type = args[0]
            # Recursively get the element type
            element_type = _get_spark_type(inner_type)
            return ArrayType(element_type, containsNull=True)
        else:
            # Default to string array if no type specified
            return ArrayType(StringType(), containsNull=True)
    
    # Handle Decimal with field metadata
    if python_type is Decimal:
        # Check if field_info has max_digits/decimal_places attributes (from Field)
        if field_info:
            # Pydantic Field stores these in the field itself or in json_schema_extra
            max_digits = 12  # Default
            decimal_places = 2  # Default
            
            # Try to get from Field constraints if available
            if hasattr(field_info, 'max_digits') and field_info.max_digits is not None:
                max_digits = field_info.max_digits
            if hasattr(field_info, 'decimal_places') and field_info.decimal_places is not None:
                decimal_places = field_info.decimal_places
                
            return DecimalType(max_digits, decimal_places)
        return DecimalType(12, 2)  # Default precision
    
    # Basic type mapping
    type_map = {
        str: StringType(),
        int: IntegerType(),
        float: DoubleType(),
        bool: StringType(),  # Spark doesn't have BooleanType in older versions
        bytes: StringType(),
    }
    
    # Return mapped type or default to StringType
    return type_map.get(python_type, StringType())


class SparkModel(BaseModel):
    """
    Base class for Pydantic models that can be converted to Spark schemas.
    
    Provides a class method to get the Spark schema for the model.
    """
    
    @classmethod
    def spark_schema(cls) -> StructType:
        """
        Get the Spark StructType schema for this model.
        
        Returns:
            StructType representing the Spark schema
        """
        return pydantic_to_spark_schema(cls)