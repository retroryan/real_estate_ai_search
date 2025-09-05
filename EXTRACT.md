# Natural Language Search and Location Extraction Flow

## Overview
This document explains how natural language queries are processed and how location information is extracted from search text in the real estate search system.

## The Query Processing Flow

### 1. Query Entry Point
When a user enters a natural language query like "Modern condo in San Francisco", the system starts processing in the **HybridSearchEngine** class.

### 2. Location Understanding Phase
The **LocationUnderstandingModule** takes the raw query text and analyzes it for location information. This module uses DSPy (a declarative language model framework) to intelligently extract location data.

The module looks for:
- City names (like "San Francisco", "San Jose", "Salinas")
- State names or abbreviations (like "California" or "CA")
- Neighborhood names
- ZIP codes (5-digit numbers)

### 3. Location Extraction Process
The **LocationExtractionSignature** class defines the extraction pattern. It instructs the language model to:
- Identify any location terms in the query
- Create a cleaned version of the query with location terms removed
- Provide confidence scores for the extraction

For example:
- Input: "Modern condo in San Francisco"
- Output: City = "San Francisco", Cleaned Query = "Modern condo"

### 4. Location Intent Creation
The extracted information is packaged into a **LocationIntent** object that contains:
- City, state, neighborhood, and ZIP code (if found)
- A cleaned query text without location terms
- A flag indicating whether any location was found
- A confidence score for the extraction

### 5. Filter Building
The **LocationFilterBuilder** class takes the LocationIntent and creates Elasticsearch filters. These filters translate the extracted location information into database queries:
- City names become match queries on the address.city field
- States are converted to abbreviations and become term queries
- Neighborhoods and ZIP codes become exact term filters

### 6. Hybrid Search Execution
The **HybridSearchEngine** combines:
- **Text Search**: Uses the cleaned query to search property descriptions and features
- **Vector Search**: Converts the cleaned query into embeddings for semantic similarity search
- **Location Filters**: Apply the geographic constraints from the extracted location

Both search methods use the same location filters to ensure consistent results.

### 7. Result Fusion
Elasticsearch's **Reciprocal Rank Fusion (RRF)** algorithm combines the text and vector search results into a single ranked list. The location filters ensure only properties in the specified location appear in results.

### 8. Response Assembly
The **HybridSearchResult** class packages the final results with:
- The matching properties
- Combined relevance scores
- The original query and extracted location information
- Execution time and metadata

## Key Components

- **LocationUnderstandingModule**: Uses AI to understand location references in natural language
- **LocationFilterBuilder**: Converts location understanding into database filters
- **HybridSearchEngine**: Orchestrates the entire search process
- **LocationIntent**: Data structure holding extracted location information
- **DSPyConfig**: Configuration for the language model used in extraction

## Example Flow

User Query: "Family home near good schools in Palo Alto California"

1. **LocationUnderstandingModule** extracts:
   - City: "Palo Alto"
   - State: "California"
   - Cleaned Query: "Family home near good schools"

2. **LocationFilterBuilder** creates filters:
   - Match filter for city = "Palo Alto"
   - Term filter for state = "CA"

3. **HybridSearchEngine** searches for:
   - Text: "Family home near good schools" in descriptions
   - Vector: Semantic similarity to "Family home near good schools"
   - Filters: Only properties in Palo Alto, CA

4. Results are combined and ranked, returning family homes in Palo Alto that match the criteria.

## Performance Optimizations

The system applies location filters DURING the search, not after. This is critical for performance:
- Filters reduce the search space before expensive calculations
- Both text and vector searches respect the same geographic boundaries
- Results are cached for faster subsequent queries

## Summary

The natural language search flow intelligently extracts location information from user queries, separates the "where" from the "what", and efficiently searches for properties that match both the location constraints and the property features requested.