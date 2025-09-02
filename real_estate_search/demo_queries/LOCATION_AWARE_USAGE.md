# Location-Aware Hybrid Search - Usage Guide

## Overview

The Location-Aware Hybrid Search system combines natural language location understanding with semantic and text-based search capabilities. It uses DSPy for intelligent location extraction and Elasticsearch's native RRF (Reciprocal Rank Fusion) for superior search results.

## Quick Start

### Basic Usage

```python
from elasticsearch import Elasticsearch
from real_estate_search.demo_queries.hybrid_search import HybridSearchEngine

# Initialize Elasticsearch client
es_client = Elasticsearch([{'host': 'localhost', 'port': 9200}])

# Create hybrid search engine
engine = HybridSearchEngine(es_client)

# Search with location
result = engine.search_with_location("luxury condo in Miami Beach", size=10)

# Access results
for property_result in result.results:
    print(f"Property: {property_result.listing_id}")
    print(f"Score: {property_result.hybrid_score}")
    print(f"Data: {property_result.property_data}")
```

### Demo Functions

Use the pre-built demo functions for specific search patterns:

```python
from real_estate_search.demo_queries import (
    demo_location_aware_waterfront_luxury,
    demo_location_aware_family_schools,
    demo_location_aware_urban_modern
)

# Run individual demos
result1 = demo_location_aware_waterfront_luxury(es_client)
result2 = demo_location_aware_family_schools(es_client)
result3 = demo_location_aware_urban_modern(es_client)

# Display results
print(result1.display())
```

### Showcase Multiple Examples

```python
from real_estate_search.demo_queries import demo_location_aware_search_showcase

# Run 5 curated examples
results = demo_location_aware_search_showcase(es_client, show_all_examples=False)

# Run all 10 examples
all_results = demo_location_aware_search_showcase(es_client, show_all_examples=True)
```

## Supported Location Patterns

### 1. City-Based Searches
```python
"luxury condo in Miami Beach"
"family home in Palo Alto California" 
"modern apartment in Seattle"
```

### 2. Neighborhood Searches
```python
"historic brownstone in Brooklyn New York"
"loft in SoHo Manhattan"
"modern apartment downtown Seattle"
```

### 3. Proximity-Based Searches
```python
"beach house walking distance to ocean in Malibu"
"family home near good schools in Palo Alto"
```

### 4. State and Region Searches
```python
"ski cabin in Park City Utah"
"investment property in Austin Texas"
"ranch style home in suburban Denver Colorado"
```

## Search Intelligence Features

### Location Understanding
- **City Extraction**: "Miami Beach", "San Francisco", "Park City"
- **State Recognition**: "California", "Utah", "Texas", "New York"
- **Neighborhood Detection**: "SoHo", "Brooklyn", "downtown"
- **ZIP Code Parsing**: "94102", "84060", "10001"

### Property Features
- **Architecture**: "modern", "historic", "ranch style", "brownstone"
- **Property Types**: "condo", "house", "loft", "cabin", "penthouse"
- **Lifestyle Features**: "luxury", "waterfront", "ski access", "city views"
- **Amenities**: "pool", "garage", "exposed brick", "good schools"

### Hybrid Search Components
- **Text Search**: Multi-field keyword matching with BM25 scoring
- **Vector Search**: 1024-dimensional semantic embeddings using Voyage-3
- **Location Filtering**: Geographic constraints from extracted location intent
- **RRF Fusion**: Native Elasticsearch fusion with rank_constant=60

## Rich Console Output

The demos include rich console formatting with:

### Visual Elements
- 🌍 Location-aware search headers
- 🏙️ City indicators
- 🗺️ State indicators  
- 🏘️ Neighborhood markers
- 🎯 Hybrid score bars
- 📊 Performance metrics

### Tables and Panels
- Property details with location information
- Hybrid scores with visual indicators
- Search intelligence features
- Performance metrics panels

## Performance

### Typical Response Times
- **Simple queries**: 50-150ms
- **Complex location queries**: 100-300ms
- **Multi-constraint searches**: 150-400ms

### Optimization Features
- Native Elasticsearch RRF (no manual fusion overhead)
- Cleaned query text for better embedding generation
- Location filters applied to both text and vector search
- Efficient DSPy caching for repeated location patterns

## Error Handling

The system gracefully handles:
- **No location detected**: Falls back to standard hybrid search
- **Invalid locations**: Continues search without location filtering
- **Missing property data**: Displays available fields with fallbacks
- **API failures**: Provides informative error messages

## Customization

### Custom Search Parameters

```python
from real_estate_search.demo_queries.hybrid_search import HybridSearchParams
from real_estate_search.demo_queries.location_understanding import LocationIntent

# Create custom search with specific parameters
params = HybridSearchParams(
    query_text="luxury penthouse with city views",
    size=15,
    rank_constant=80,  # Higher values favor lower-ranked results
    rank_window_size=150,  # Larger window for fusion
    text_boost=1.2,
    vector_boost=0.8,
    location_intent=LocationIntent(
        city="San Francisco",
        has_location=True,
        cleaned_query="luxury penthouse with city views",
        confidence=0.95
    )
)

result = engine.search(params)
```

### Integration with Management Commands

```bash
# Run location-aware demos via management command
python -m real_estate_search.management demo <demo_number>

# List available demos including location-aware ones
python -m real_estate_search.management demo --list
```

## Best Practices

### 1. Query Construction
- Include specific locations for best results
- Combine location with property features
- Use natural language patterns

### 2. Performance
- Use appropriate result sizes (5-20 for demos)
- Consider caching for repeated location patterns
- Monitor DSPy token usage for cost management

### 3. Error Handling
- Always check `has_location` in LocationIntent
- Validate result counts before display
- Handle missing property fields gracefully

### 4. Display
- Use rich console formatting for better UX
- Show hybrid scores for relevance understanding
- Include location extraction details for transparency