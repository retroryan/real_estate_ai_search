# Property Display Tables Documentation

This document provides a comprehensive inventory of all property table displays found in the `real_estate_search/demo_queries` directory. Each table entry includes a description of its purpose and the specific columns it displays.

## 1. Basic Property Search Results Table
**Location:** `property/display_service.py` - `display_basic_search_results()`
**Purpose:** Displays basic property search results with minimal details and relevance scoring
**Columns:**
- `#` - Row number (1-10)
- `Address` - Full property address
- `Price` - Formatted property price
- `Details` - Property summary (beds/baths/sqft)
- `Score` - Search relevance score

## 2. Filtered Property Search Results Table
**Location:** `property/display_service.py` - `display_filtered_search_results()`
**Purpose:** Shows filtered search results with comprehensive property details in a structured format
**Columns:**
- `#` - Row number (1-15)
- `Address` - Full property address
- `Price` - Formatted property price with dollar sign
- `Beds/Baths` - Bedroom and bathroom count in format "X/Y"
- `Sq Ft` - Square footage with comma formatting
- `Type` - Property type (Single Family, Condo, Townhouse, etc.)

## 3. Geo-Distance Search Results Table
**Location:** `property/display_service.py` - `display_geo_search_results()`
**Purpose:** Displays properties sorted by distance from a central location point
**Columns:**
- `#` - Row number (1-15)
- `Distance` - Distance from search center point
- `Address` - Full property address
- `Price` - Formatted property price
- `Details` - Bedroom and bathroom count

## 4. Natural Language Semantic Search Results Table
**Location:** `semantic/display_service.py` - `display_natural_language_results()`
**Purpose:** Shows properties found through AI-powered natural language understanding
**Columns:**
- `#` - Row number
- `Property` - Street address and city (multi-line)
- `Price` - Formatted property price
- `Beds/Baths` - Bedroom/bathroom count in "X/Y" format
- `Sq Ft` - Square footage or "N/A"
- `Score` - Semantic similarity score (0-1 scale)

## 5. Advanced Semantic Similarity Results Table
**Location:** `advanced/display_service.py` - `display_semantic_results()`
**Purpose:** Displays properties similar to a reference property using AI embeddings
**Columns:**
- `#` - Row number
- `Score` - Similarity score (higher = more similar)
- `Property Details` - Multi-line cell with address, price, type, and size
- `Description` - Property description (truncated to 200 chars)

## 6. Multi-Entity Property Search Table
**Location:** `advanced/display_service.py` - `display_multi_entity_results()`
**Purpose:** Shows properties from multi-entity search across different indices
**Columns:**
- `Score` - Relevance score
- `Address` - Street and city
- `Price` - Formatted price or "N/A"
- `Type` - Property type (title case)

## 7. Location-Aware Hybrid Search Results Table
**Location:** `location_aware_demos.py` - `create_location_results_table()`
**Purpose:** Comprehensive property display with location intelligence and hybrid scoring
**Columns:**
- `#` - Row number (1-5, top results only)
- `Property Details` - Multi-line: property type, beds/baths, square footage, year built
- `Location` - Multi-line: street, city, state, zip, neighborhood
- `Price` - Formatted price with emoji indicator
- `Description` - Property description (truncated at 150 chars)
- `Score` - Hybrid score with star rating visualization

## 8. Neighborhood Statistics Table
**Location:** `aggregation_queries.py` - `display_neighborhood_stats()`
**Purpose:** Statistical analysis of properties grouped by neighborhood
**Columns:**
- `Neighborhood` - Neighborhood identifier/name
- `Properties` - Count of properties in neighborhood
- `Avg Price` - Average property price
- `Price Range` - Min-max price range
- `Avg Beds` - Average number of bedrooms
- `Avg SqFt` - Average square footage
- `$/SqFt` - Average price per square foot

## 9. Rich Property Details Table
**Location:** `rich_listing_demo.py` - `create_property_details_table()`
**Purpose:** Detailed property feature breakdown for individual property display
**Columns:**
- `Feature` - Property attribute name
- `Value` - Corresponding attribute value

**Feature rows include:**
- Bedrooms
- Bathrooms
- Square Feet
- Year Built
- Lot Size
- Price/SqFt
- Days on Market
- Listing Date
- Status
- Parking (if available)

## 10. Rich Property Details Table (Alternative)
**Location:** `rich/display_service.py` - `create_property_details_table()`
**Purpose:** Enhanced property details display with rich formatting
**Columns:**
- `Feature` - Property attribute name
- `Value` - Corresponding attribute value

**Feature rows include:**
- Bedrooms
- Bathrooms
- Square Feet
- Year Built
- Lot Size
- Price/SqFt
- Days on Market
- Listing Date
- Status
- Parking (if available)

## Summary Statistics

### Total Unique Table Types: 10

### Most Common Column Patterns:
1. **Identification:** Row number (#), Property ID
2. **Location:** Address (full or street/city split), Neighborhood
3. **Pricing:** Price (formatted), Price/SqFt, Price Range
4. **Property Specs:** Bedrooms, Bathrooms, Square Feet, Property Type
5. **Scoring:** Search Score, Similarity Score, Hybrid Score
6. **Descriptive:** Description (often truncated), Features, Details

### Display Limits:
- Basic searches: 10-15 results
- Location-aware searches: 5 results (top matches only)
- Aggregation displays: 20 neighborhoods
- Rich listings: 10 features maximum

### Special Formatting Features:
- **Emojis:** Used in location-aware and rich displays for visual enhancement
- **Multi-line cells:** Property details and location information often span multiple lines
- **Score visualizations:** Star ratings, progress bars, and numeric scores
- **Color coding:** Prices (green), locations (blue), scores (cyan/magenta)
- **Truncation:** Descriptions typically limited to 150-250 characters

## Notes

1. All tables use the Rich library for terminal display with enhanced formatting
2. Tables are responsive and adjust to terminal width
3. Most tables include a title describing the search type
4. Column widths are typically specified for consistent formatting
5. Tables often accompany panels showing search statistics and performance metrics