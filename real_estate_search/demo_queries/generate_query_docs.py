#!/usr/bin/env python3
"""
Generate markdown documentation for all demo query JSON files.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List

# Demo descriptions mapping
DEMO_DESCRIPTIONS = {
    1: "Basic Property Search - Multi-match query with fuzzy matching",
    2: "Property Filter Search - Bool query with multiple filters",
    3: "Geographic Distance Search - Geo-distance filter and sorting",
    4: "Neighborhood Statistics - Aggregations for property analytics",
    5: "Price Distribution Analysis - Histogram aggregations by property type",
    6: "Semantic Similarity Search - Vector similarity using embeddings",
    7: "Multi-Entity Combined Search - Cross-index search",
    8: "Wikipedia Article Search - Full-text search with location filters",
    9: "Wikipedia Full-Text Search - HTML content search",
    10: "Property Relationships - Denormalized index single query",
    11: "Natural Language Semantic Search - AI embeddings for semantic understanding",
    12: "Natural Language Examples - Multiple semantic search examples",
    13: "Semantic vs Keyword Comparison - Comparing search approaches",
    14: "Rich Real Estate Listing - Complete property data from single query",
    15: "Hybrid Search with RRF - Combining vector and text search",
    16: "Location Understanding - DSPy for location entity extraction",
    17: "Location-Aware: Waterfront Luxury - Premium waterfront properties",
    18: "Location-Aware: Family Schools - Family-friendly with good schools",
    19: "Location-Aware: Urban Modern - Modern city properties",
    20: "Location-Aware: Recreation Mountain - Mountain recreation properties",
    21: "Location-Aware: Historic Urban - Historic city properties",
    22: "Location-Aware: Beach Proximity - Properties near beaches",
    23: "Location-Aware: Investment Market - Investment opportunities",
    24: "Location-Aware: Luxury Urban Views - Luxury with city views",
    25: "Location-Aware: Suburban Architecture - Architectural suburban homes",
    26: "Location-Aware: Neighborhood Character - Community-focused properties",
    27: "Location-Aware Search Showcase - Multiple location-aware searches"
}


def analyze_query_structure(query: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the structure of an Elasticsearch query."""
    analysis = {
        "query_type": None,
        "filters": [],
        "must_clauses": [],
        "should_clauses": [],
        "aggregations": {},
        "sort": [],
        "features": set()
    }
    
    # Identify main query type
    if "query" in query:
        q = query["query"]
        if "bool" in q:
            analysis["query_type"] = "bool"
            bool_query = q["bool"]
            
            if "filter" in bool_query:
                analysis["filters"] = bool_query["filter"]
                analysis["features"].add("filtering")
            
            if "must" in bool_query:
                analysis["must_clauses"] = bool_query["must"]
                analysis["features"].add("required_matching")
            
            if "should" in bool_query:
                analysis["should_clauses"] = bool_query["should"]
                analysis["features"].add("optional_matching")
        
        elif "multi_match" in q:
            analysis["query_type"] = "multi_match"
            analysis["features"].add("multi_field_search")
            if q["multi_match"].get("fuzziness"):
                analysis["features"].add("fuzzy_matching")
        
        elif "match" in q:
            analysis["query_type"] = "match"
            analysis["features"].add("text_search")
        
        elif "term" in q:
            analysis["query_type"] = "term"
            analysis["features"].add("exact_matching")
        
        elif "knn" in q:
            analysis["query_type"] = "knn"
            analysis["features"].add("vector_search")
        
        elif "geo_distance" in q:
            analysis["query_type"] = "geo_distance"
            analysis["features"].add("geospatial_search")
    
    # Check for aggregations
    if "aggs" in query or "aggregations" in query:
        analysis["features"].add("aggregations")
        analysis["aggregations"] = query.get("aggs", query.get("aggregations", {}))
    
    # Check for sorting
    if "sort" in query:
        analysis["features"].add("custom_sorting")
        analysis["sort"] = query["sort"]
    
    # Check for highlighting
    if "highlight" in query:
        analysis["features"].add("highlighting")
    
    # Check for source filtering
    if "_source" in query:
        analysis["features"].add("source_filtering")
    
    return analysis


def generate_markdown_for_demo(demo_num: int, query_file: Path) -> str:
    """Generate markdown documentation for a demo query."""
    
    # Load the query JSON
    with open(query_file, 'r') as f:
        query_data = json.load(f)
    
    query = query_data.get("query", {})
    index = query_data.get("index", ["unknown"])
    
    # Analyze query structure
    analysis = analyze_query_structure(query)
    
    # Get demo description
    demo_desc = DEMO_DESCRIPTIONS.get(demo_num, f"Demo {demo_num}")
    
    # Build markdown content
    md = f"""# Demo {demo_num}: {demo_desc}

## Overview
This query demonstrates Elasticsearch features for {demo_desc.lower()}.

## Query Details

**Index:** `{', '.join(index) if isinstance(index, list) else index}`  
**Query Type:** `{analysis['query_type']}`  
**Size:** {query.get('size', 10)} documents

## Features Used
"""
    
    for feature in sorted(analysis['features']):
        feature_name = feature.replace('_', ' ').title()
        md += f"- **{feature_name}**\n"
    
    md += "\n## Query Structure\n\n```json\n"
    md += json.dumps(query, indent=2)
    md += "\n```\n"
    
    # Add specific analysis based on query type
    if analysis['query_type'] == 'bool':
        md += "\n## Bool Query Analysis\n\n"
        
        if analysis['filters']:
            md += "### Filters (Non-scoring)\n"
            md += "These conditions must be met but don't affect relevance scoring:\n"
            for filter_clause in analysis['filters']:
                md += f"- {json.dumps(filter_clause, indent=2)}\n"
        
        if analysis['must_clauses']:
            md += "\n### Must Clauses (Required)\n"
            md += "All these conditions must be satisfied:\n"
            for must_clause in analysis['must_clauses']:
                md += f"- {json.dumps(must_clause, indent=2)}\n"
        
        if analysis['should_clauses']:
            md += "\n### Should Clauses (Optional)\n"
            md += "At least one of these should match for better scoring:\n"
            for should_clause in analysis['should_clauses']:
                md += f"- {json.dumps(should_clause, indent=2)}\n"
    
    elif analysis['query_type'] == 'multi_match':
        md += "\n## Multi-Match Query Analysis\n\n"
        mm_query = query.get("query", {}).get("multi_match", {})
        md += f"**Search Text:** `{mm_query.get('query', '')}`\n\n"
        md += "**Fields Searched:**\n"
        for field in mm_query.get("fields", []):
            if "^" in field:
                field_name, boost = field.split("^")
                md += f"- `{field_name}` (boost: {boost}x)\n"
            else:
                md += f"- `{field}`\n"
    
    elif analysis['query_type'] == 'knn':
        md += "\n## Vector Search Analysis\n\n"
        md += "This query uses k-nearest neighbors (KNN) search to find similar documents based on vector embeddings.\n"
    
    if analysis['aggregations']:
        md += "\n## Aggregations\n\n"
        md += "This query includes aggregations for data analysis:\n"
        md += f"```json\n{json.dumps(analysis['aggregations'], indent=2)}\n```\n"
    
    if analysis['sort']:
        md += "\n## Sorting\n\n"
        md += "Results are sorted by:\n"
        for sort_clause in analysis['sort']:
            md += f"- {json.dumps(sort_clause, indent=2)}\n"
    
    md += "\n## Performance Notes\n\n"
    
    if 'filtering' in analysis['features']:
        md += "- **Filters are cached**: Subsequent identical searches will be faster\n"
    
    if 'vector_search' in analysis['features']:
        md += "- **Vector search**: Uses HNSW algorithm for approximate nearest neighbor search\n"
    
    if 'aggregations' in analysis['features']:
        md += "- **Aggregations**: Computed across all matching documents, not just returned results\n"
    
    if 'fuzzy_matching' in analysis['features']:
        md += "- **Fuzzy matching**: Allows for typos and variations in search terms\n"
    
    return md


def main():
    """Generate documentation for all demo queries."""
    
    # Get the demo_queries_json directory
    json_dir = Path(__file__).parent / "demo_queries_json"
    
    if not json_dir.exists():
        print(f"Directory {json_dir} does not exist!")
        return
    
    # Process each demo
    for demo_num in range(1, 28):
        # Find query files for this demo
        query_files = sorted(json_dir.glob(f"demo_{demo_num}_query_*.json"))
        
        if not query_files:
            print(f"No query files found for demo {demo_num}")
            continue
        
        # Generate documentation for the first query of each demo
        first_query = query_files[0]
        
        # Skip if markdown already exists and is manually created
        md_file = first_query.with_suffix('.md')
        if md_file.exists() and demo_num <= 3:  # Skip our manually created ones
            print(f"Skipping demo {demo_num} (manually created)")
            continue
        
        print(f"Generating documentation for demo {demo_num}...")
        
        try:
            markdown_content = generate_markdown_for_demo(demo_num, first_query)
            
            # Write markdown file
            with open(md_file, 'w') as f:
                f.write(markdown_content)
            
            print(f"  ✓ Created {md_file.name}")
            
        except Exception as e:
            print(f"  ✗ Error processing demo {demo_num}: {e}")
    
    print("\nDocumentation generation complete!")


if __name__ == "__main__":
    main()