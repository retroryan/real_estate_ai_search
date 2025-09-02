# Real Estate AI Search - Working Demo Guide

This guide lists all working demos with their natural language queries and demo numbers. Use this as a quick reference to test the search functionality.

## How to Run Demos

Run a demo using either method:
```bash
# Using es-manager.sh script
./es-manager.sh demo [NUMBER]

# Using Python directly
python -m real_estate_search.management demo [NUMBER]
```

## Working Demos with Natural Language Queries

### ✅ Core Search Demos (1-14)

| Demo # | Query Type | Natural Language Query | Results Found |
|--------|------------|------------------------|---------------|
| **1** | Basic Property Search | `"family home with pool"` | 94 results |
| **2** | Property Filter Search | (Filtered search with criteria) | 9 results |
| **3** | Geo-Distance Search | (Location-based: 37.7,-122.4, 5km radius) | 80 results |
| **4** | Neighborhood Statistics | (Aggregation query) | 220 results |
| **5** | Price Distribution | (Price range analysis) | 161 results |
| **6** | Semantic Similarity | Finding properties similar to specific address | 220 results |
| **7** | Multi-Entity Search | `"historic downtown"` | 85 results |
| **8** | Wikipedia Search | (Wikipedia location & topic search) | 105 results |
| **9** | Wikipedia Full-Text | (Full-text Wikipedia search) | 1863 results |
| **10** | Property Relationships | (Denormalized index query) | 0 results ⚠️ |
| **11** | Natural Language Semantic | `"modern home with mountain views and open floor plan"` | 10 results |
| **12** | Natural Language Examples | Multiple queries: <br>• `"cozy family home near good schools and parks"`<br>• `"modern downtown condo with city views"`<br>• `"spacious property with home office and fast internet"`<br>• `"eco-friendly house with solar panels and energy efficiency"` | Various |
| **13** | Semantic vs Keyword | (Comparison demo) | 123 results |
| **14** | Rich Property Listing | (Single property with full details) | N/A |

### ✅ Hybrid & Location-Aware Demos (15-27)

| Demo # | Query Type | Natural Language Query | Results Found | Status |
|--------|------------|------------------------|---------------|---------|
| **15** | Hybrid Search (RRF) | `"modern kitchen with stainless steel appliances"` | 94 results | ✅ Working |
| **16** | Location Understanding | Multiple location extraction tests | 6 results | ✅ Working |
| **17** | Waterfront Luxury | `"Luxury waterfront condo in San Francisco"` | 70 results | ✅ Working |
| **18** | Family Schools | `"Family home near good schools in San Jose California"` | 0 results | ❌ No data |
| **19** | Urban Modern | `"Modern apartment in Oakland"` | 40 results | ✅ Working |
| **20** | Recreation Mountain | `"Investment property in Salinas California"` | 0 results | ❌ No data |
| **21** | Historic Urban | `"Historic home in San Francisco CA"` | 0 results | ❌ No data |
| **22** | Beach Proximity | `"Affordable house in Oakland California"` | 0 results | ❌ No data |
| **23** | Investment Market | `"Condo with amenities in San Jose"` | 40 results | ✅ Working |
| **24** | Luxury Urban Views | `"Single family home in San Francisco Bay Area"` | 137 results | ✅ Working |
| **25** | Suburban Architecture | `"Townhouse in Oakland under 800k"` | 40 results | ✅ Working |
| **26** | Neighborhood Character | `"Modern condo with parking in San Francisco California"` | 0 results | ❌ No data |
| **27** | Location Showcase | (Multiple location-aware queries) | Various | ✅ Working |

## Best Working Queries

### 🌟 Top Natural Language Queries with Good Results

1. **Demo 1**: `"family home with pool"` - Basic search that finds family homes with pools
2. **Demo 7**: `"historic downtown"` - Multi-entity search across properties and Wikipedia
3. **Demo 11**: `"modern home with mountain views and open floor plan"` - Semantic search understanding
4. **Demo 15**: `"modern kitchen with stainless steel appliances"` - Hybrid search combining text and vector
5. **Demo 17**: `"Luxury waterfront condo in San Francisco"` - Location-aware luxury search
6. **Demo 19**: `"Modern apartment in Oakland"` - Location-specific modern property search
7. **Demo 23**: `"Condo with amenities in San Jose"` - Amenity-focused location search
8. **Demo 24**: `"Single family home in San Francisco Bay Area"` - Regional area search
9. **Demo 25**: `"Townhouse in Oakland under 800k"` - Price-constrained location search

### 🎯 Most Reliable Demos

**For Quick Testing:**
- Demo 1: Simple natural language property search
- Demo 15: Hybrid search with modern features
- Demo 19: Location-aware search in Oakland
- Demo 24: Bay Area property search

**For Feature Demonstration:**
- Demo 11: Shows semantic understanding
- Demo 13: Compares semantic vs keyword search
- Demo 16: Demonstrates location extraction
- Demo 17: Shows luxury property filtering with location

## Notes

- Demos with 0 results may need more data loaded for those specific locations/criteria
- Demo 10 (Property Relationships) appears to need the denormalized index to be built
- Demo 12 runs multiple example queries in sequence
- Demo 27 runs multiple location-aware demos as a showcase

## Quick Test Commands

```bash
# Test basic search
./es-manager.sh demo 1

# Test hybrid search
./es-manager.sh demo 15

# Test location-aware search
./es-manager.sh demo 19

# Run the showcase (multiple demos)
./es-manager.sh demo 27
```

## Troubleshooting

If demos return 0 results:
1. Check that Elasticsearch is running: `./es-manager.sh health`
2. Verify data is loaded: `./es-manager.sh stats`
3. Rebuild indices if needed: `./es-manager.sh rebuild`

For location-aware demos (17-26), ensure:
- DSPy is configured properly
- Location extraction service is working
- Properties exist in the specified cities (San Francisco, Oakland, San Jose, Salinas)