# Field Name Standardization Implementation

## Overview

Phase 3: Field Name Standardization has been successfully implemented to ensure consistent field naming between the data pipeline output and search queries. This implementation provides a robust, configurable field mapping system using Pydantic models.

## Components Implemented

### 1. Directory Structure
```
data_pipeline/
├── transformers/
│   ├── __init__.py
│   └── field_mapper.py
└── config/
    └── field_mappings.json
```

### 2. Core Components

#### FieldMapper Class (`data_pipeline/transformers/field_mapper.py`)
- **Purpose**: Transforms Spark DataFrames to standardize field names
- **Features**:
  - Loads mappings from JSON configuration
  - Applies field name transformations to DataFrames
  - Converts data types as needed
  - Builds nested structures (address, neighborhood, parking objects)
  - Validates required fields
  - Handles list field transformations
  - Applies Wikipedia enrichment mappings

#### Pydantic Models
- `FieldMappingConfig`: Configuration for individual entity mappings
- `MappingConfiguration`: Complete mapping configuration for all entity types
- `FieldMappingResult`: Result object containing transformed DataFrame and mapping metadata

### 3. Configuration File (`data_pipeline/config/field_mappings.json`)
Defines comprehensive mappings for:
- **Property mappings**: Direct field mappings, nested objects (address, neighborhood, parking), type conversions
- **Neighborhood mappings**: Field mappings and type conversions
- **Wikipedia mappings**: Field mappings and type conversions
- **Wikipedia enrichment mappings**: Location context, neighborhood context, and location scores

### 4. Updated Document Builders

#### BaseDocumentBuilder
- Integrated FieldMapper initialization
- Added `apply_field_mapping()` method
- Added `validate_field_mapping_requirements()` method
- Graceful handling when FieldMapper is not available

#### Entity-Specific Builders Updated
- `PropertyDocumentBuilder`
- `NeighborhoodDocumentBuilder`  
- `WikipediaDocumentBuilder`

All builders now:
1. Validate field mapping requirements first
2. Apply field name standardization
3. Validate required fields after mapping
4. Continue with document transformation

### 5. Comprehensive Test Suite

#### Unit Tests (`search_pipeline/tests/test_field_mapper.py`)
- Test Pydantic model validation
- Test FieldMapper initialization and configuration loading
- Test field mapping operations for all entity types
- Test error handling and validation
- Test integration with BaseDocumentBuilder

#### Integration Tests (`data_pipeline/tests/test_field_mapper_integration.py`)
- End-to-end testing with realistic Spark DataFrames
- Complete property transformation testing
- Neighborhood and Wikipedia transformation testing
- Error handling with invalid data
- Configuration loading validation

## Key Features

### 1. Deterministic Mapping
- No dynamic field generation
- All mappings defined in JSON configuration
- Predictable transformations

### 2. Nested Object Creation
- Automatically creates nested address objects with geo-point arrays
- Builds neighborhood and parking objects from flat fields
- Handles Wikipedia enrichment nested structures

### 3. Type Conversions
- String to float conversions for prices and coordinates
- String to int conversions for counts and scores
- List field handling for comma-separated strings

### 4. Field Validation
- Validates required fields before and after transformation
- Reports missing fields and unmapped fields
- Provides detailed warnings and error messages

### 5. Robust Error Handling
- Graceful degradation when FieldMapper unavailable
- Continues processing with warnings for conversion failures
- Detailed logging and error reporting

## Field Mapping Examples

### Direct Field Mappings
```json
"zip": "zip_code",
"listing_price": "price",
"garage_spaces": "parking_spaces"
```

### Nested Object Mappings
```json
"address": {
  "street": "address.street",
  "city": "address.city",
  "latitude": "address.location[1]",
  "longitude": "address.location[0]"
}
```

### Type Conversions
```json
"price": "float",
"bedrooms": "int",
"latitude": "float"
```

## Usage

The field mapper is automatically integrated into the document builders:

```python
from search_pipeline.builders.property_builder import PropertyDocumentBuilder

builder = PropertyDocumentBuilder()
documents = builder.transform(spark_dataframe)
# Field mapping is applied automatically before document creation
```

## Benefits

1. **Consistency**: Ensures field names match between pipeline stages
2. **Maintainability**: Centralized configuration makes changes easy
3. **Validation**: Prevents errors from missing required fields
4. **Flexibility**: JSON configuration allows easy customization
5. **Robustness**: Graceful error handling and detailed logging
6. **Testing**: Comprehensive test coverage ensures reliability

## Impact

This implementation ensures that:
- Spark DataFrame columns are properly mapped to Elasticsearch document field names
- Data types are correctly converted for proper indexing
- Nested structures are created to match Elasticsearch mappings exactly
- The search pipeline receives consistently formatted data
- Field name discrepancies between pipeline stages are eliminated

The field mapping system provides a foundation for reliable data flow from the Spark processing pipeline to the Elasticsearch search system, eliminating field name mismatches that could cause search functionality issues.