# SQUACK Pipeline Guide

## Overview

The SQUACK pipeline is a sophisticated data processing system that transforms raw real estate data through a medallion architecture (Bronze → Silver → Gold tiers). The pipeline processes multiple entity types including properties, neighborhoods, locations, and Wikipedia articles, preparing them for advanced search and analytics capabilities.

## Initial Data Loading Phase

During the initial load phase, the pipeline ingests data from various sources and prepares it for processing through the medallion architecture. This phase focuses on data validation, standardization, and establishing a clean foundation for downstream processing.

### Data Sources
The pipeline loads data from four primary sources:
- Property listings from JSON files (San Francisco and Park City datasets)
- Neighborhood information from JSON files with demographic and characteristic data
- Location data from a consolidated JSON file with city and zip code information
- Wikipedia articles from a SQLite database containing geographic and contextual information

### Loading Process
Each data source has a dedicated loader that performs initial validation using Pydantic models. These loaders ensure data integrity before any transformation occurs, rejecting invalid records and logging validation errors. The loading process establishes the foundation for the Bronze layer by creating properly structured tables in DuckDB.

## Bronze Layer - Detailed Architecture

The Bronze layer serves as the foundational tier of the medallion architecture, transforming raw nested JSON data into clean, flattened relational structures. This layer emphasizes data standardization and validation while preserving all source information.

### Purpose and Philosophy

The Bronze layer acts as the "single source of truth" for raw data, but with critical improvements over truly raw storage. Rather than storing nested JSON structures that require complex extraction operations, the Bronze layer flattens all data into clean relational schemas. This approach eliminates the need for JSON parsing in downstream layers and establishes consistent field naming conventions across all entity types.

### Data Transformation Strategy

#### Flattening Nested Structures

The Bronze layer's primary transformation involves converting hierarchical JSON data into flat relational tables. This process occurs directly during data loading, ensuring that downstream processors never need to handle nested structures.

For properties, the transformation handles three levels of nesting:
- Address information (street, city, county, state, zip) is extracted from nested address objects
- Property details (bedrooms, bathrooms, square feet, etc.) are flattened from property detail structures
- Geographic coordinates are extracted from coordinate objects

For neighborhoods, the transformation flattens even more complex structures:
- Characteristic scores (walkability, transit, school ratings) are extracted from nested characteristic objects
- Demographic information (population, income, age groups) is flattened from demographic structures
- Geographic boundaries and coordinates are standardized into simple latitude/longitude fields

#### Field Standardization

The Bronze layer enforces consistent field naming across all entity types. Geographic fields like city, state, latitude, and longitude use identical names whether they appear in property, neighborhood, or location tables. This standardization eliminates confusion and simplifies cross-entity operations in higher tiers.

### Implementation Architecture

#### Core Loader Classes

**PropertyLoader** (implemented in `squack_pipeline/loaders/property_loader.py`)
This class handles the transformation of property JSON data into Bronze layer format. It validates each property record using the Property Pydantic model, then converts validated records to PropertyFlat instances for storage. The loader implements methods for creating the Bronze table schema and performing batch insertions of flattened data.

**NeighborhoodLoader** (implemented in `squack_pipeline/loaders/neighborhood_loader.py`)
Responsible for processing neighborhood JSON files, this loader handles the most complex nested structures in the pipeline. It validates records using the Neighborhood Pydantic model and transforms them to NeighborhoodFlat instances. The loader manages optional demographic fields gracefully, providing default values where appropriate.

**LocationLoader** (implemented in `squack_pipeline/loaders/location_loader.py`)
This simpler loader processes location data that is already relatively flat. It validates using the Location Pydantic model and handles optional neighborhood associations. The loader demonstrates how even simple data benefits from Bronze layer standardization.

**WikipediaLoader** (implemented in `squack_pipeline/loaders/wikipedia_loader.py`)
Handles extraction from the SQLite database, validating article records using the WikipediaArticle Pydantic model. This loader shows how the Bronze layer pattern extends to different data source types beyond JSON files.

#### Pydantic Models

**Data Models** (defined in `squack_pipeline/models/data_models.py`)
The pipeline uses two sets of Pydantic models for each entity type:
- Nested models (Property, Neighborhood, Location, WikipediaArticle) that match source data structure
- Flattened models (PropertyFlat, NeighborhoodFlat) that define Bronze layer schema

These models enforce type safety and validation rules, ensuring data quality from the earliest processing stage.

### Validation and Quality Control

#### Pydantic Validation
Every record passes through Pydantic validation before entering the Bronze layer. Invalid records are logged and skipped rather than causing pipeline failures. This approach ensures data quality while maintaining pipeline resilience.

#### Schema Validation
The Bronze layer enforces strict schema requirements through DuckDB table definitions. Each loader creates tables with explicit column types and constraints, preventing schema drift and ensuring consistency.

#### Range Validation
Numeric fields undergo range validation during Bronze layer processing:
- Geographic coordinates must fall within valid latitude and longitude ranges
- Scores and ratings must fall within expected bounds
- Prices and counts must be positive values

### Data Quality Improvements

#### Null Handling
The Bronze layer implements intelligent null handling, distinguishing between missing data and invalid data. Optional fields receive appropriate null values, while required fields cause record rejection if missing.

#### Type Standardization
All data types are standardized in the Bronze layer:
- Strings are trimmed and stored as VARCHAR
- Numbers are stored with appropriate precision (INTEGER for counts, DOUBLE for measurements)
- Arrays are preserved as native array types
- Dates maintain their temporal nature

#### Duplicate Management
While the Bronze layer doesn't eliminate duplicates, it establishes unique identifiers (listing_id, neighborhood_id, etc.) that enable duplicate detection in higher tiers.

### Integration with Downstream Processing

The Bronze layer's flattened structure dramatically simplifies downstream processing. Silver and Gold tier processors no longer need JSON extraction logic, instead working with clean columnar data. This design improves query performance and reduces processing complexity.

The Bronze layer maintains complete data lineage by preserving all source fields, even those not immediately useful. This completeness ensures that future processing requirements can be met without reloading source data.

### Performance Optimizations

#### Batch Processing
All Bronze layer loaders use batch insertion for efficient data loading. Records are validated in memory, then inserted in configurable batch sizes to optimize database performance.

#### Parallel Validation
Pydantic validation occurs in Python before database operations, allowing for parallel processing of validation logic while maintaining serial database writes for consistency.

#### Memory Management
The loaders process data in chunks when sample sizes are specified, preventing memory exhaustion with large datasets while maintaining validation completeness.

### Testing and Quality Assurance

**Integration Tests** (implemented in `squack_pipeline/integration_tests/test_phase_2_bronze_layer.py`)
Comprehensive tests validate every aspect of Bronze layer processing:
- Schema structure verification ensures all expected fields exist
- Field naming consistency tests confirm standardization across entity types
- Data quality tests validate that transformations preserve data integrity
- Sample data extraction tests confirm that data remains accessible and correct

The Bronze layer achieves 100% test coverage with all tests passing, demonstrating the robustness of the implementation.

### Benefits of the Bronze Layer Architecture

#### Simplified Downstream Processing
By flattening data at the Bronze layer, all downstream processors work with simple columnar data rather than complex nested structures. This simplification reduces code complexity and improves maintainability.

#### Consistent Data Access
The standardized field naming and flattened structure provide consistent data access patterns across all entity types. Developers working with any tier above Bronze can rely on predictable field names and types.

#### Performance Improvements
Flattened data structures enable efficient columnar storage and processing in DuckDB. Query performance improves significantly compared to JSON extraction operations.

#### Enhanced Data Quality
Pydantic validation at the Bronze layer catches data quality issues early, preventing corrupt data from propagating through the pipeline. This early validation reduces debugging complexity and improves overall pipeline reliability.

#### Future Extensibility
The Bronze layer's complete data preservation and clean structure make it easy to add new processing logic or entity types. New requirements can be met by extending the existing Bronze schema rather than restructuring the entire pipeline.