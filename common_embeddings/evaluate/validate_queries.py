#!/usr/bin/env python3
"""
Validate the accuracy of query-article mappings in the evaluation dataset.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
import sqlite3


class QueryValidator:
    """Validates query-article mappings against actual article content."""
    
    def __init__(self):
        self.articles = {}
        self.queries = {}
        self.db_path = "data/wikipedia/wikipedia.db"
        
    def load_data(self):
        """Load articles and queries from JSON files."""
        # Load articles
        with open("common_embeddings/evaluate_data/evaluate_articles.json", "r") as f:
            data = json.load(f)
            for article in data["articles"]:
                self.articles[article["page_id"]] = article
        
        # Load queries
        with open("common_embeddings/evaluate_data/evaluate_queries.json", "r") as f:
            data = json.load(f)
            self.queries = data["queries"]
    
    def get_article_content(self, page_id: int) -> str:
        """Get full article content from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT title, full_text 
            FROM articles 
            WHERE page_id = ?
        """, (page_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return f"{result[0]}\n{result[1] or ''}"
        return ""
    
    def validate_query(self, query: Dict) -> Dict:
        """Validate a single query against expected articles."""
        query_text = query["query_text"]
        expected_ids = query["expected_results"]
        category = query["category"]
        
        validation = {
            "query_id": query["query_id"],
            "query_text": query_text,
            "category": category,
            "expected_count": len(expected_ids),
            "validations": []
        }
        
        # Check each expected article
        for page_id in expected_ids:
            if page_id not in self.articles:
                validation["validations"].append({
                    "page_id": page_id,
                    "title": "NOT FOUND",
                    "valid": False,
                    "reason": "Article not in evaluation dataset"
                })
                continue
            
            article = self.articles[page_id]
            is_valid, reason = self.check_relevance(query_text, article, category)
            
            validation["validations"].append({
                "page_id": page_id,
                "title": article["title"],
                "valid": is_valid,
                "reason": reason,
                "location": f"{article.get('city', 'N/A')}, {article.get('county', 'N/A')}, {article.get('state', 'N/A')}"
            })
        
        # Calculate accuracy
        valid_count = sum(1 for v in validation["validations"] if v["valid"])
        validation["accuracy"] = valid_count / len(expected_ids) if expected_ids else 0
        
        return validation
    
    def check_relevance(self, query: str, article: Dict, category: str) -> Tuple[bool, str]:
        """Check if an article is relevant to a query."""
        query_lower = query.lower()
        title_lower = article["title"].lower()
        summary_lower = (article.get("summary", "") + " " + article.get("long_summary", "")).lower()
        
        # Category-specific validation
        if category == "geographic":
            return self.validate_geographic(query_lower, article, title_lower, summary_lower)
        elif category == "landmark":
            return self.validate_landmark(query_lower, article, title_lower, summary_lower)
        elif category == "historical":
            return self.validate_historical(query_lower, article, title_lower, summary_lower)
        elif category == "administrative":
            return self.validate_administrative(query_lower, article, title_lower, summary_lower)
        elif category == "semantic":
            return self.validate_semantic(query_lower, article, title_lower, summary_lower)
        
        return False, "Unknown category"
    
    def validate_geographic(self, query: str, article: Dict, title: str, summary: str) -> Tuple[bool, str]:
        """Validate geographic queries."""
        # Check for specific location mentions
        if "wasatch county" in query and article.get("county") == "Wasatch County":
            return True, "Correctly matches Wasatch County location"
        
        if "coastal" in query and ("coast" in summary or "beach" in summary or "ocean" in summary):
            return True, "Article mentions coastal features"
        
        if "park city" in query and ("park city" in summary or article.get("city") == "Park City"):
            return True, "Related to Park City area"
        
        if "peninsula" in query and "peninsula" in title:
            return True, "Peninsula region article"
        
        if "northern california" in query and article.get("state") == "California":
            # Check if it's actually Northern California
            counties = ["San Francisco", "San Mateo", "Santa Clara", "Alameda", "Marin"]
            if any(c in str(article.get("county", "")) for c in counties):
                return True, "Northern California location"
        
        if "southern utah" in query and article.get("state") == "Utah":
            # Check if it's actually Southern Utah
            counties = ["Iron", "Washington", "Kane", "Garfield", "Beaver"]
            if any(c in str(article.get("county", "")) for c in counties):
                return True, "Southern Utah location"
        
        if "bay area" in query and ("bay area" in summary or "san francisco bay" in summary):
            return True, "Bay Area location"
        
        if "mountain" in query and ("mountain" in title or "mountain" in summary or "peak" in summary):
            return True, "Mountain/peak location"
        
        return False, "No clear geographic match"
    
    def validate_landmark(self, query: str, article: Dict, title: str, summary: str) -> Tuple[bool, str]:
        """Validate landmark queries."""
        if "state park" in query and ("state park" in title or "state park" in summary):
            return True, "State park landmark"
        
        if "mountain" in query and article.get("state") == "Utah" and ("mountain" in title or "mountain" in summary):
            return True, "Utah mountain landmark"
        
        if "tourist" in query and ("tourist" in summary or "tourism" in summary or "visitor" in summary):
            return True, "Tourist destination"
        
        if "water sports" in query and ("water" in summary and ("sport" in summary or "boat" in summary or "swim" in summary)):
            return True, "Water sports location"
        
        if "ski" in query and ("ski" in summary or "winter sport" in summary):
            return True, "Ski/winter sports area"
        
        if "national" in query and ("national" in summary or "monument" in summary):
            return True, "National landmark/monument"
        
        if "beach" in query or "coastal" in query:
            if "beach" in summary or "coast" in summary or "ocean" in summary:
                return True, "Beach/coastal recreation area"
        
        if "nature" in query or "wilderness" in query:
            if "preserve" in summary or "wilderness" in summary or "natural" in summary:
                return True, "Nature preserve/wilderness area"
        
        return False, "No clear landmark match"
    
    def validate_historical(self, query: str, article: Dict, title: str, summary: str) -> Tuple[bool, str]:
        """Validate historical queries."""
        if "california historical landmark" in query:
            if "historical landmark" in title or "california historical" in title:
                return True, "California Historical Landmark"
        
        if "spanish colonial" in query and ("spanish" in summary or "colonial" in summary or "mission" in summary):
            return True, "Spanish colonial history"
        
        if "land grant" in query and ("land grant" in summary or "rancho" in summary):
            return True, "Historical land grant"
        
        if "1930s" in query and ("1930" in summary or "depression" in summary):
            return True, "1930s infrastructure/project"
        
        if "gold rush" in query and ("gold" in summary or "mining" in summary or "1849" in summary):
            return True, "Gold Rush era location"
        
        if "native american" in query and ("native" in summary or "indian" in summary or "tribe" in summary):
            return True, "Native American heritage site"
        
        if "mormon" in query and ("mormon" in summary or "lds" in summary or "latter" in summary):
            return True, "Mormon pioneer site"
        
        if "railroad" in query or "railway" in query:
            if "railroad" in summary or "railway" in summary or "train" in summary:
                return True, "Railroad/railway historical site"
        
        return False, "No clear historical match"
    
    def validate_administrative(self, query: str, article: Dict, title: str, summary: str) -> Tuple[bool, str]:
        """Validate administrative queries."""
        if "counties in utah" in query and article.get("state") == "Utah":
            if article.get("county"):
                return True, f"Located in {article['county']}, Utah"
        
        if "counties in california" in query and article.get("state") == "California":
            if article.get("county"):
                return True, f"Located in {article['county']}, California"
        
        if "school district" in query and ("school" in summary or "education" in summary or "district" in summary):
            return True, "Education/school district related"
        
        if "census designated" in query and ("census" in summary or "cdp" in summary or "unincorporated" in summary):
            return True, "Census designated place"
        
        if "metropolitan" in query and ("metropolitan" in summary or "metro area" in summary):
            return True, "Metropolitan statistical area"
        
        if "city government" in query or "municipalities" in query:
            if "city" in article.get("city", "") or "municipal" in summary or "government" in summary:
                return True, "City/municipal government"
        
        if "water management" in query and ("water" in summary and ("district" in summary or "management" in summary)):
            return True, "Water management district"
        
        if "transportation" in query or "transit" in query:
            if "transportation" in summary or "transit" in summary or "highway" in summary:
                return True, "Transportation/transit authority"
        
        return False, "No clear administrative match"
    
    def validate_semantic(self, query: str, article: Dict, title: str, summary: str) -> Tuple[bool, str]:
        """Validate semantic queries."""
        if "family-friendly" in query and "outdoor" in query:
            if ("family" in summary or "visitor" in summary) and ("park" in summary or "recreation" in summary):
                return True, "Family-friendly outdoor destination"
        
        if "water sports" in query and ("water" in summary and ("sport" in summary or "boat" in summary)):
            return True, "Water sports location"
        
        if "silicon valley" in query and ("silicon valley" in summary or "tech" in summary):
            return True, "Silicon Valley/tech hub area"
        
        if "rural" in query and ("rural" in summary or "unincorporated" in summary):
            return True, "Rural/unincorporated region"
        
        if "adventure tourism" in query and ("adventure" in summary or "tourism" in summary or "outdoor" in summary):
            return True, "Adventure tourism destination"
        
        if "wine" in query and ("wine" in summary or "vineyard" in summary or "winery" in summary):
            return True, "Wine country/vineyard region"
        
        if "desert" in query and ("desert" in summary or "arid" in summary):
            return True, "Desert region/landscape"
        
        if "agricultural" in query or "farming" in query:
            if "agricultural" in summary or "farming" in summary or "ranch" in summary:
                return True, "Agricultural/farming region"
        
        return False, "No clear semantic match"
    
    def validate_all(self) -> Dict:
        """Validate all queries and generate report."""
        self.load_data()
        
        results = {
            "total_queries": len(self.queries),
            "total_articles": len(self.articles),
            "category_results": {},
            "query_validations": []
        }
        
        # Group by category
        categories = {}
        for query in self.queries:
            cat = query["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(query)
        
        # Validate each category
        for category, cat_queries in categories.items():
            cat_results = {
                "total": len(cat_queries),
                "validations": [],
                "average_accuracy": 0
            }
            
            for query in cat_queries:
                validation = self.validate_query(query)
                cat_results["validations"].append(validation)
                results["query_validations"].append(validation)
            
            # Calculate category accuracy
            accuracies = [v["accuracy"] for v in cat_results["validations"]]
            cat_results["average_accuracy"] = sum(accuracies) / len(accuracies) if accuracies else 0
            
            results["category_results"][category] = cat_results
        
        # Overall accuracy
        all_accuracies = [v["accuracy"] for v in results["query_validations"]]
        results["overall_accuracy"] = sum(all_accuracies) / len(all_accuracies) if all_accuracies else 0
        
        return results
    
    def print_report(self, results: Dict):
        """Print validation report."""
        print("\n" + "="*80)
        print("QUERY VALIDATION REPORT")
        print("="*80)
        
        print(f"\nOverall Accuracy: {results['overall_accuracy']:.1%}")
        print(f"Total Queries: {results['total_queries']}")
        print(f"Total Articles: {results['total_articles']}")
        
        print("\n" + "-"*80)
        print("CATEGORY BREAKDOWN")
        print("-"*80)
        
        for category, cat_results in results["category_results"].items():
            print(f"\n{category.upper()} ({cat_results['total']} queries)")
            print(f"  Average Accuracy: {cat_results['average_accuracy']:.1%}")
            
            # Show problematic queries
            problematic = [v for v in cat_results["validations"] if v["accuracy"] < 0.5]
            if problematic:
                print(f"  Problematic queries ({len(problematic)}):")
                for val in problematic:
                    print(f"    - {val['query_id']}: \"{val['query_text']}\" (accuracy: {val['accuracy']:.1%})")
        
        print("\n" + "-"*80)
        print("DETAILED VALIDATION ISSUES")
        print("-"*80)
        
        # Show all invalid mappings
        for val in results["query_validations"]:
            invalid = [v for v in val["validations"] if not v["valid"]]
            if invalid:
                print(f"\nQuery: {val['query_id']} - \"{val['query_text']}\"")
                for inv in invalid:
                    print(f"  ✗ {inv['title']} ({inv['page_id']})")
                    print(f"    Location: {inv['location']}")
                    print(f"    Reason: {inv['reason']}")
        
        # Save detailed report
        with open("common_embeddings/evaluate_results/validation_report.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print("\n" + "="*80)
        print("Detailed report saved to: common_embeddings/evaluate_results/validation_report.json")
        print("="*80)


def main():
    """Run validation."""
    validator = QueryValidator()
    results = validator.validate_all()
    validator.print_report(results)


if __name__ == "__main__":
    main()