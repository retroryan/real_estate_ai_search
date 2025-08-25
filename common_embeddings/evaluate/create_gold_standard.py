#!/usr/bin/env python3
"""
Create gold standard evaluation datasets by fixing identified issues.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime


def load_current_data():
    """Load current articles and queries."""
    with open("common_embeddings/evaluate_data/evaluate_articles.json", "r") as f:
        articles = json.load(f)
    
    with open("common_embeddings/evaluate_data/evaluate_queries.json", "r") as f:
        queries = json.load(f)
    
    return articles, queries


def fix_query_issues(queries_data):
    """Fix identified issues in query-article mappings."""
    queries = queries_data["queries"]
    
    # Fix geo_005: Remove Bidwell Mansion (605117) - not Northern California
    for q in queries:
        if q["query_id"] == "geo_005":
            # Remove 605117 (Bidwell Mansion - it's in Butte County, which is Central Valley)
            if 605117 in q["expected_results"]:
                q["expected_results"].remove(605117)
            # Update relevance annotations
            q["relevance_annotations"]["605117"] = 0
    
    # Fix geo_006: Southern Utah - remove Northern Utah locations
    for q in queries:
        if q["query_id"] == "geo_006":
            # Remove 17997272 (Deer Creek - Wasatch County is Northern Utah)
            if 17997272 in q["expected_results"]:
                q["expected_results"].remove(17997272)
            # Remove 34482485 (Cedar Mountains - Tooele County is Northern Utah)  
            if 34482485 in q["expected_results"]:
                q["expected_results"].remove(34482485)
            # Keep 34629558 (Black Mountains - Iron/Beaver Counties are Southern Utah)
            q["relevance_annotations"]["17997272"] = 0
            q["relevance_annotations"]["34482485"] = 0
    
    # Fix geo_007: SF Bay Area - remove non-Bay Area
    for q in queries:
        if q["query_id"] == "geo_007":
            # Add 1706289 (Fillmore District is in SF)
            if 1706289 not in q["expected_results"]:
                q["expected_results"].append(1706289)
            q["relevance_annotations"]["1706289"] = 3
    
    # Fix lan_009: State parks - remove counties, keep actual parks
    for q in queries:
        if q["query_id"] == "lan_009":
            # Remove 71083 (Wayne County - not a state park)
            if 71083 in q["expected_results"]:
                q["expected_results"].remove(71083)
            q["relevance_annotations"]["71083"] = 0
            # Keep 17997272 (Deer Creek State Park)
            # Keep 605117 (Bidwell Mansion State Historic Park)
    
    # Fix lan_012: Water sports - remove ski resort without water
    for q in queries:
        if q["query_id"] == "lan_012":
            # Remove 748746 (Snowbird - ski resort, no water sports)
            if 748746 in q["expected_results"]:
                q["expected_results"].remove(748746)
            q["relevance_annotations"]["748746"] = 0
            # Keep 7369514 (has water/ocean access)
    
    # Fix lan_014: National landmarks - focus on national designations
    for q in queries:
        if q["query_id"] == "lan_014":
            # Keep 36842068 as it contains info about historical landmarks
            # Update other relevance scores appropriately
            pass
    
    # Fix his_017: California Historical Landmarks
    for q in queries:
        if q["query_id"] == "his_017":
            # Remove 26974 (SF Peninsula - geographic, not about landmarks)
            if 26974 in q["expected_results"]:
                q["expected_results"].remove(26974)
            q["relevance_annotations"]["26974"] = 0
            # Remove 605117 (Bidwell - it's a state park, not focused on landmark designation)
            if 605117 in q["expected_results"]:
                q["expected_results"].remove(605117)
            q["relevance_annotations"]["605117"] = 0
            # Keep 36842068 (specifically about CA Historical Landmarks)
    
    # Fix his_019: Historical land grants in California
    for q in queries:
        if q["query_id"] == "his_019":
            # Remove Utah locations
            if 71077 in q["expected_results"]:
                q["expected_results"].remove(71077)  # Tooele County, Utah
            if 15862936 in q["expected_results"]:
                q["expected_results"].remove(15862936)  # Ajax, Utah
            q["relevance_annotations"]["71077"] = 0
            q["relevance_annotations"]["15862936"] = 0
            # Keep 26974 if it mentions land grants
    
    # Fix his_020: 1930s infrastructure
    for q in queries:
        if q["query_id"] == "his_020":
            # Keep 17997272 (Deer Creek - 1930s Provo River Project)
            # Remove non-1930s projects
            if 71060 in q["expected_results"]:
                q["expected_results"].remove(71060)  # Iron County - no 1930s connection
            if 605117 in q["expected_results"]:
                q["expected_results"].remove(605117)  # Bidwell - 1865 mansion
            q["relevance_annotations"]["71060"] = 0
            q["relevance_annotations"]["605117"] = 0
    
    # Fix adm_030: City governments - only include actual cities
    for q in queries:
        if q["query_id"] == "adm_030":
            # Remove parks and geographic features
            if 17997272 in q["expected_results"]:
                q["expected_results"].remove(17997272)  # State park
            if 34629558 in q["expected_results"]:
                q["expected_results"].remove(34629558)  # Mountains
            if 71083 in q["expected_results"]:
                q["expected_results"].remove(71083)  # County, not city
            q["relevance_annotations"]["17997272"] = 0
            q["relevance_annotations"]["34629558"] = 0
            q["relevance_annotations"]["71083"] = 0
            # Add actual cities
            actual_cities = [71060, 22770046, 605117]  # Cities with municipal governments
            for city_id in actual_cities:
                if city_id not in q["expected_results"]:
                    q["expected_results"].append(city_id)
                q["relevance_annotations"][str(city_id)] = 3
    
    # Fix sem_033: Family-friendly outdoor - focus on recreational areas
    for q in queries:
        if q["query_id"] == "sem_033":
            # Remove pure historical landmarks without recreation
            if 36842068 in q["expected_results"]:
                q["expected_results"].remove(36842068)  # Historical landmarks list
            q["relevance_annotations"]["36842068"] = 0
            # Keep parks and recreational areas
    
    # Fix sem_034: Water sports
    for q in queries:
        if q["query_id"] == "sem_034":
            # Remove locations without water access
            if 137014 in q["expected_results"]:
                q["expected_results"].remove(137014)  # Enoch, Utah - no water sports
            q["relevance_annotations"]["137014"] = 0
    
    # Fix sem_037: Adventure tourism
    for q in queries:
        if q["query_id"] == "sem_037":
            # Remove regular cities without adventure tourism
            if 107783 in q["expected_results"]:
                q["expected_results"].remove(107783)  # Salinas - agricultural city
            q["relevance_annotations"]["107783"] = 0
            # Add adventure destinations
            adventure_spots = [748746, 7369514]  # Snowbird, coastal areas
            for spot_id in adventure_spots:
                if spot_id not in q["expected_results"]:
                    q["expected_results"].append(spot_id)
                q["relevance_annotations"][str(spot_id)] = 3
    
    return queries_data


def create_gold_standard():
    """Create gold standard files."""
    # Load current data
    articles_data, queries_data = load_current_data()
    
    # Fix query issues
    queries_data = fix_query_issues(queries_data)
    
    # Update metadata
    queries_data["metadata"]["generation_date"] = datetime.now().isoformat()
    queries_data["metadata"]["version"] = "gold_v1"
    queries_data["metadata"]["notes"] = "Gold standard dataset with validated query-article mappings"
    
    articles_data["metadata"]["selection_date"] = datetime.now().isoformat()
    articles_data["metadata"]["version"] = "gold_v1"
    articles_data["metadata"]["notes"] = "Gold standard dataset - 50 curated Wikipedia articles"
    
    # Save gold standard files
    gold_dir = Path("common_embeddings/evaluate_data")
    
    with open(gold_dir / "gold_articles.json", "w") as f:
        json.dump(articles_data, f, indent=2)
    
    with open(gold_dir / "gold_queries.json", "w") as f:
        json.dump(queries_data, f, indent=2)
    
    print("✅ Created gold standard files:")
    print("   - gold_articles.json (50 articles)")
    print("   - gold_queries.json (40 queries with fixed mappings)")
    
    # Calculate statistics
    total_expected = sum(len(q["expected_results"]) for q in queries_data["queries"])
    avg_per_query = total_expected / len(queries_data["queries"])
    
    print(f"\n📊 Statistics:")
    print(f"   - Total expected results: {total_expected}")
    print(f"   - Average per query: {avg_per_query:.1f}")
    
    # Show fixes applied
    print("\n🔧 Fixes applied:")
    print("   - geo_005: Removed Bidwell Mansion (not Northern CA)")
    print("   - geo_006: Removed Northern Utah locations from Southern Utah query")
    print("   - geo_007: Added Fillmore District to Bay Area query")
    print("   - lan_009: Removed counties from state parks query")
    print("   - lan_012: Removed ski resort from water sports query")
    print("   - his_017: Removed geographic articles from historical landmarks")
    print("   - his_019: Removed Utah locations from California land grants")
    print("   - his_020: Kept only actual 1930s infrastructure projects")
    print("   - adm_030: Removed parks/mountains, added actual cities")
    print("   - sem_033: Removed non-recreational historical sites")
    print("   - sem_034: Removed locations without water access")
    print("   - sem_037: Removed non-adventure cities, added adventure spots")


def main():
    """Create gold standard datasets."""
    create_gold_standard()


if __name__ == "__main__":
    main()