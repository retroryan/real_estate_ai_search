"""
Query generator for evaluation dataset.

Creates test queries based on selected Wikipedia articles.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Set
from datetime import datetime


class QueryGenerator:
    """Generates test queries for Wikipedia article evaluation."""
    
    def __init__(self, articles: List[Dict[str, Any]]):
        """
        Initialize query generator.
        
        Args:
            articles: List of article dictionaries
        """
        self.articles = articles
        self._build_indexes()
    
    def _build_indexes(self):
        """Build indexes for efficient query generation."""
        self.articles_by_state = {}
        self.articles_by_county = {}
        self.articles_by_category = {}
        self.articles_by_id = {}
        
        for article in self.articles:
            # Index by page_id
            self.articles_by_id[article["page_id"]] = article
            
            # Index by state
            state = article.get("state")
            if state:
                if state not in self.articles_by_state:
                    self.articles_by_state[state] = []
                self.articles_by_state[state].append(article)
            
            # Index by county
            county = article.get("county")
            if county:
                if county not in self.articles_by_county:
                    self.articles_by_county[county] = []
                self.articles_by_county[county].append(article)
            
            # Index by categories
            for category in article.get("categories", []):
                if category not in self.articles_by_category:
                    self.articles_by_category[category] = []
                self.articles_by_category[category].append(article)
    
    def generate_queries(
        self,
        queries_per_category: int = 4,
        categories: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate test queries across different categories.
        
        Args:
            queries_per_category: Number of queries per category
            categories: Query categories to generate
            
        Returns:
            List of query dictionaries
        """
        if categories is None:
            categories = ["geographic", "landmark", "historical", "administrative", "semantic"]
        
        queries = []
        query_id_counter = 1
        
        for category in categories:
            if category == "geographic":
                category_queries = self._generate_geographic_queries(queries_per_category)
            elif category == "landmark":
                category_queries = self._generate_landmark_queries(queries_per_category)
            elif category == "historical":
                category_queries = self._generate_historical_queries(queries_per_category)
            elif category == "administrative":
                category_queries = self._generate_administrative_queries(queries_per_category)
            elif category == "semantic":
                category_queries = self._generate_semantic_queries(queries_per_category)
            else:
                continue
            
            for query_text, expected_ids, relevance_annotations in category_queries:
                query = {
                    "query_id": f"{category[:3]}_{query_id_counter:03d}",
                    "query_text": query_text,
                    "category": category,
                    "expected_results": expected_ids,
                    "relevance_annotations": relevance_annotations
                }
                queries.append(query)
                query_id_counter += 1
        
        return queries
    
    def _generate_geographic_queries(self, n: int) -> List[tuple]:
        """Generate geographic queries."""
        queries = []
        
        # Query 1: Cities in specific counties
        if self.articles_by_county.get("Wasatch County"):
            wasatch_ids = [a["page_id"] for a in self.articles_by_county["Wasatch County"]]
            relevance = self._calculate_geographic_relevance("Wasatch County", county_match=True)
            queries.append((
                "What locations are in Wasatch County, Utah?",
                wasatch_ids[:3],
                relevance
            ))
        
        # Query 2: Coastal areas
        if self.articles_by_category.get("coastal"):
            coastal_ids = [a["page_id"] for a in self.articles_by_category["coastal"]]
            relevance = self._calculate_category_relevance("coastal")
            queries.append((
                "Find coastal areas in California",
                coastal_ids[:3],
                relevance
            ))
        
        # Query 3: Areas near specific locations
        park_city_nearby = self._find_nearby_articles("Park City", state="Utah")
        if park_city_nearby:
            relevance = self._calculate_proximity_relevance("Park City", "Utah")
            queries.append((
                "What places are near Park City, Utah?",
                [a["page_id"] for a in park_city_nearby[:3]],
                relevance
            ))
        
        # Query 4: Peninsula areas
        peninsula_articles = [a for a in self.articles if "peninsula" in a["title"].lower()]
        if peninsula_articles:
            relevance = self._calculate_keyword_relevance("peninsula", title_weight=3)
            queries.append((
                "Show me peninsula regions in the Bay Area",
                [a["page_id"] for a in peninsula_articles[:3]],
                relevance
            ))
        
        return queries[:n]
    
    def _generate_landmark_queries(self, n: int) -> List[tuple]:
        """Generate landmark and recreation queries."""
        queries = []
        
        # Query 1: State parks
        park_articles = self.articles_by_category.get("park", [])
        if park_articles:
            relevance = self._calculate_category_relevance("park")
            queries.append((
                "Find state parks for recreation",
                [a["page_id"] for a in park_articles[:3]],
                relevance
            ))
        
        # Query 2: Mountain areas
        mountain_articles = self.articles_by_category.get("mountain", [])
        if mountain_articles:
            relevance = self._calculate_category_relevance("mountain")
            queries.append((
                "Mountain regions in Utah",
                [a["page_id"] for a in mountain_articles if a.get("state") == "Utah"][:3],
                relevance
            ))
        
        # Query 3: Tourist destinations
        tourist_articles = self.articles_by_category.get("tourist_destination", [])
        if tourist_articles:
            relevance = self._calculate_category_relevance("tourist_destination")
            queries.append((
                "Popular tourist destinations",
                [a["page_id"] for a in tourist_articles[:3]],
                relevance
            ))
        
        # Query 4: Recreation areas
        recreation_articles = self.articles_by_category.get("recreation", [])
        if recreation_articles:
            relevance = self._calculate_category_relevance("recreation")
            queries.append((
                "Outdoor recreation areas with water sports",
                [a["page_id"] for a in recreation_articles[:3]],
                relevance
            ))
        
        return queries[:n]
    
    def _generate_historical_queries(self, n: int) -> List[tuple]:
        """Generate historical queries."""
        queries = []
        
        # Query 1: Historical landmarks
        historical_articles = self.articles_by_category.get("historical", [])
        if historical_articles:
            relevance = self._calculate_category_relevance("historical")
            queries.append((
                "California Historical Landmarks",
                [a["page_id"] for a in historical_articles if a.get("state") == "California"][:3],
                relevance
            ))
        
        # Query 2: Spanish colonial history
        spanish_articles = [a for a in self.articles 
                           if "spanish" in (a.get("summary", "") + a.get("long_summary", "")).lower()]
        if spanish_articles:
            relevance = self._calculate_keyword_relevance("spanish", summary_weight=2)
            queries.append((
                "Spanish colonial history sites",
                [a["page_id"] for a in spanish_articles[:3]],
                relevance
            ))
        
        # Query 3: Land grants
        grant_articles = [a for a in self.articles 
                         if "grant" in (a.get("summary", "") + a.get("long_summary", "")).lower()]
        if grant_articles:
            relevance = self._calculate_keyword_relevance("grant", summary_weight=2)
            queries.append((
                "Historical land grants in California",
                [a["page_id"] for a in grant_articles[:3]],
                relevance
            ))
        
        # Query 4: 1930s projects
        thirties_articles = [a for a in self.articles 
                           if "1930" in (a.get("summary", "") + a.get("long_summary", ""))]
        if thirties_articles:
            relevance = self._calculate_keyword_relevance("1930", summary_weight=1)
            queries.append((
                "Infrastructure projects from the 1930s",
                [a["page_id"] for a in thirties_articles[:3]],
                relevance
            ))
        
        return queries[:n]
    
    def _generate_administrative_queries(self, n: int) -> List[tuple]:
        """Generate administrative queries."""
        queries = []
        
        # Query 1: Counties
        county_articles = self.articles_by_category.get("county", [])
        if county_articles:
            relevance = self._calculate_category_relevance("county")
            queries.append((
                "Counties in Utah",
                [a["page_id"] for a in county_articles if a.get("state") == "Utah"][:3],
                relevance
            ))
        
        # Query 2: School districts
        education_articles = self.articles_by_category.get("education", [])
        if education_articles:
            relevance = self._calculate_category_relevance("education")
            queries.append((
                "School districts and education facilities",
                [a["page_id"] for a in education_articles[:3]],
                relevance
            ))
        
        # Query 3: Census designated places
        census_articles = [a for a in self.articles 
                          if "census" in a.get("summary", "").lower()]
        if census_articles:
            relevance = self._calculate_keyword_relevance("census", summary_weight=2)
            queries.append((
                "Census designated places in Summit County",
                [a["page_id"] for a in census_articles[:3]],
                relevance
            ))
        
        # Query 4: Metropolitan areas
        metro_articles = [a for a in self.articles 
                         if "metropolitan" in (a.get("summary", "") + a.get("long_summary", "")).lower()]
        if metro_articles:
            relevance = self._calculate_keyword_relevance("metropolitan", summary_weight=1)
            queries.append((
                "Metropolitan statistical areas",
                [a["page_id"] for a in metro_articles[:3]],
                relevance
            ))
        
        return queries[:n]
    
    def _generate_semantic_queries(self, n: int) -> List[tuple]:
        """Generate semantic/conceptual queries."""
        queries = []
        
        # Query 1: Family-friendly destinations
        family_articles = [a for a in self.articles 
                          if any(cat in a.get("categories", []) 
                                for cat in ["park", "recreation", "tourist_destination"])]
        if family_articles:
            relevance = self._calculate_semantic_relevance("family", ["park", "recreation"])
            queries.append((
                "Family-friendly outdoor destinations",
                [a["page_id"] for a in family_articles[:3]],
                relevance
            ))
        
        # Query 2: Water activities
        water_articles = [a for a in self.articles 
                         if "water" in (a.get("summary", "") + a.get("key_topics", "")).lower()
                         or "coastal" in a.get("categories", [])]
        if water_articles:
            relevance = self._calculate_semantic_relevance("water", ["coastal", "park"])
            queries.append((
                "Places for water sports and activities",
                [a["page_id"] for a in water_articles[:3]],
                relevance
            ))
        
        # Query 3: Silicon Valley area
        silicon_articles = [a for a in self.articles 
                           if "silicon" in (a.get("summary", "") + a.get("long_summary", "")).lower()]
        if silicon_articles:
            relevance = self._calculate_keyword_relevance("silicon", summary_weight=2)
            queries.append((
                "Technology hub areas in Silicon Valley",
                [a["page_id"] for a in silicon_articles[:3]],
                relevance
            ))
        
        # Query 4: Rural and unincorporated areas
        rural_articles = [a for a in self.articles 
                         if "rural" in (a.get("summary", "") + a.get("long_summary", "")).lower()
                         or "unincorporated" in (a.get("summary", "") + a.get("long_summary", "")).lower()]
        if rural_articles:
            relevance = self._calculate_keyword_relevance("rural", summary_weight=1)
            queries.append((
                "Rural and unincorporated regions",
                [a["page_id"] for a in rural_articles[:3]],
                relevance
            ))
        
        return queries[:n]
    
    def _find_nearby_articles(self, location: str, state: str = None) -> List[Dict[str, Any]]:
        """Find articles near a specific location."""
        nearby = []
        location_lower = location.lower()
        
        for article in self.articles:
            # Check if in same state
            if state and article.get("state") != state:
                continue
            
            # Check if location is mentioned in article
            summary = (article.get("summary", "") + article.get("long_summary", "")).lower()
            if location_lower in summary or location_lower in article.get("title", "").lower():
                nearby.append(article)
        
        return nearby
    
    def _calculate_geographic_relevance(self, location: str, county_match: bool = False) -> Dict[int, int]:
        """Calculate relevance scores for geographic queries."""
        relevance = {}
        
        for article in self.articles:
            page_id = article["page_id"]
            score = 0
            
            if county_match and article.get("county") == location:
                score = 3
            elif location.lower() in article.get("title", "").lower():
                score = 3
            elif location.lower() in (article.get("summary", "") + article.get("long_summary", "")).lower():
                score = 2
            elif article.get("state") and location.lower() in article.get("state", "").lower():
                score = 1
            
            relevance[page_id] = score
        
        return relevance
    
    def _calculate_category_relevance(self, category: str) -> Dict[int, int]:
        """Calculate relevance scores for category queries."""
        relevance = {}
        
        for article in self.articles:
            page_id = article["page_id"]
            if category in article.get("categories", []):
                relevance[page_id] = 3
            elif any(cat for cat in article.get("categories", []) if category in cat):
                relevance[page_id] = 2
            else:
                relevance[page_id] = 0
        
        return relevance
    
    def _calculate_keyword_relevance(self, keyword: str, title_weight: int = 3, summary_weight: int = 2) -> Dict[int, int]:
        """Calculate relevance scores for keyword queries."""
        relevance = {}
        keyword_lower = keyword.lower()
        
        for article in self.articles:
            page_id = article["page_id"]
            score = 0
            
            if keyword_lower in article.get("title", "").lower():
                score = title_weight
            elif keyword_lower in article.get("summary", "").lower():
                score = summary_weight
            elif keyword_lower in article.get("long_summary", "").lower():
                score = 1
            
            relevance[page_id] = score
        
        return relevance
    
    def _calculate_proximity_relevance(self, location: str, state: str) -> Dict[int, int]:
        """Calculate relevance based on proximity to a location."""
        relevance = {}
        location_lower = location.lower()
        
        for article in self.articles:
            page_id = article["page_id"]
            score = 0
            
            # Same state bonus
            if article.get("state") == state:
                score += 1
            
            # Location mentioned
            if location_lower in article.get("title", "").lower():
                score = 3
            elif location_lower in (article.get("summary", "") + article.get("long_summary", "")).lower():
                score = 2
            
            relevance[page_id] = min(score, 3)
        
        return relevance
    
    def _calculate_semantic_relevance(self, concept: str, related_categories: List[str]) -> Dict[int, int]:
        """Calculate relevance for semantic/conceptual queries."""
        relevance = {}
        
        for article in self.articles:
            page_id = article["page_id"]
            score = 0
            
            # Check for related categories
            article_cats = article.get("categories", [])
            matching_cats = sum(1 for cat in related_categories if cat in article_cats)
            
            if matching_cats >= 2:
                score = 3
            elif matching_cats == 1:
                score = 2
            
            # Check for concept in text
            if concept.lower() in (article.get("summary", "") + article.get("long_summary", "")).lower():
                score = max(score, 1)
            
            relevance[page_id] = score
        
        return relevance
    
    def save_to_json(
        self,
        queries: List[Dict[str, Any]],
        output_path: str = "common_embeddings/evaluate_data/evaluate_queries.json"
    ):
        """
        Save queries to JSON file.
        
        Args:
            queries: List of query dictionaries
            output_path: Path to save JSON file
        """
        # Calculate category distribution
        category_counts = {}
        for query in queries:
            cat = query["category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        output_data = {
            "queries": queries,
            "categories": category_counts,
            "metadata": {
                "generation_date": datetime.now().isoformat(),
                "total_queries": len(queries),
                "total_articles": len(self.articles),
                "generation_method": "category-based"
            }
        }
        
        # Ensure directory exists
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write JSON
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"Saved {len(queries)} queries to {output_path}")


def main():
    """Main function to generate test queries."""
    # Load articles
    articles_path = "common_embeddings/evaluate_data/evaluate_articles.json"
    with open(articles_path, 'r') as f:
        data = json.load(f)
    
    articles = data["articles"]
    print(f"Loaded {len(articles)} articles")
    
    # Create query generator
    generator = QueryGenerator(articles)
    
    # Generate queries
    print("\nGenerating test queries...")
    queries = generator.generate_queries(
        queries_per_category=4,
        categories=["geographic", "landmark", "historical", "administrative", "semantic"]
    )
    
    # Print summary
    print(f"\nGenerated {len(queries)} queries:")
    category_counts = {}
    for query in queries:
        cat = query["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    for category, count in category_counts.items():
        print(f"  - {category}: {count}")
    
    # Show sample queries
    print("\nSample queries:")
    for query in queries[:5]:
        print(f"  [{query['query_id']}] {query['query_text']}")
        print(f"    Expected: {query['expected_results'][:3]}")
    
    # Save to JSON
    generator.save_to_json(queries)
    
    print("\nQuery generation complete!")


if __name__ == "__main__":
    main()