"""
Article selector for evaluation dataset creation.

Randomly selects Wikipedia articles from the database for evaluation.
"""

import json
import sqlite3
import random
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime


class ArticleSelector:
    """Selects Wikipedia articles for evaluation dataset."""
    
    def __init__(self, db_path: str = "data/wikipedia/wikipedia.db"):
        """
        Initialize article selector.
        
        Args:
            db_path: Path to Wikipedia SQLite database
        """
        self.db_path = db_path
        
    def select_random(
        self,
        n: int = 25,
        require_summary: bool = True,
        seed: Optional[int] = 42
    ) -> List[Dict[str, Any]]:
        """
        Select random articles from database.
        
        Args:
            n: Number of articles to select
            require_summary: Only select articles with summaries
            seed: Random seed for reproducibility
            
        Returns:
            List of article dictionaries
        """
        if seed is not None:
            random.seed(seed)
        
        # Connect to database
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build query
        query = """
            SELECT 
                a.pageid,
                a.title,
                a.html_file,
                a.latitude,
                a.longitude,
                ps.short_summary,
                ps.long_summary,
                ps.key_topics,
                ps.best_city,
                ps.best_county,
                ps.best_state,
                ps.overall_confidence
            FROM articles a
        """
        
        if require_summary:
            query += " INNER JOIN page_summaries ps ON a.pageid = ps.page_id"
        else:
            query += " LEFT JOIN page_summaries ps ON a.pageid = ps.page_id"
        
        query += " WHERE a.html_file IS NOT NULL"
        
        # Execute query
        cursor.execute(query)
        all_articles = cursor.fetchall()
        
        # Convert to list of dicts
        articles_list = []
        for row in all_articles:
            article = dict(row)
            articles_list.append(article)
        
        # Close connection
        conn.close()
        
        # Random selection
        if len(articles_list) <= n:
            selected = articles_list
        else:
            selected = random.sample(articles_list, n)
        
        # Format for JSON output
        formatted_articles = []
        for article in selected:
            formatted = {
                "page_id": article["pageid"],
                "title": article["title"],
                "summary": article["short_summary"] or "",
                "long_summary": article["long_summary"] or "",
                "key_topics": article["key_topics"] or "",
                "city": article["best_city"],
                "county": article["best_county"],
                "state": article["best_state"],
                "confidence": article["overall_confidence"],
                "html_file": article["html_file"],
                "latitude": article["latitude"],
                "longitude": article["longitude"],
                "embedding_metadata": {
                    "chunk_strategy": "semantic",
                    "max_chunk_size": 512
                }
            }
            
            # Determine categories based on content
            categories = self._determine_categories(formatted)
            formatted["categories"] = categories
            
            formatted_articles.append(formatted)
        
        return formatted_articles
    
    def _determine_categories(self, article: Dict[str, Any]) -> List[str]:
        """
        Determine article categories based on content.
        
        Args:
            article: Article dictionary
            
        Returns:
            List of category tags
        """
        categories = []
        
        title_lower = article["title"].lower()
        summary_lower = (article["summary"] + " " + article["long_summary"]).lower()
        
        # Geographic categories
        if "county" in title_lower or article["county"]:
            categories.append("county")
        if "city" in title_lower or article["city"]:
            categories.append("city")
        if "park" in summary_lower:
            categories.append("park")
        
        # Feature categories
        if "historical" in summary_lower or "history" in summary_lower:
            categories.append("historical")
        if "landmark" in summary_lower:
            categories.append("landmark")
        if "ski" in summary_lower or "resort" in summary_lower:
            categories.append("recreation")
        if "coast" in summary_lower or "beach" in summary_lower:
            categories.append("coastal")
        if "mountain" in summary_lower:
            categories.append("mountain")
        if "school" in summary_lower or "education" in summary_lower:
            categories.append("education")
        if "tourist" in summary_lower or "tourism" in summary_lower:
            categories.append("tourist_destination")
        
        # State categories
        if article["state"] == "Utah":
            categories.append("utah")
        elif article["state"] == "California":
            categories.append("california")
        
        return categories
    
    def save_to_json(
        self,
        articles: List[Dict[str, Any]],
        output_path: str = "common_embeddings/evaluate_data/evaluate_articles.json"
    ):
        """
        Save selected articles to JSON file.
        
        Args:
            articles: List of article dictionaries
            output_path: Path to save JSON file
        """
        output_data = {
            "articles": articles,
            "metadata": {
                "selection_date": datetime.now().isoformat(),
                "total_selected": len(articles),
                "selection_method": "stratified_random",
                "seed": 42,
                "database_path": self.db_path
            }
        }
        
        # Ensure directory exists
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write JSON
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"Saved {len(articles)} articles to {output_path}")
    
    def load_from_json(self, json_path: str) -> List[Dict[str, Any]]:
        """
        Load articles from JSON file.
        
        Args:
            json_path: Path to JSON file
            
        Returns:
            List of article dictionaries
        """
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        return data["articles"]


def main():
    """Main function to select and save evaluation articles."""
    selector = ArticleSelector()
    
    # Select 50 random articles
    print("Selecting 50 random Wikipedia articles...")
    articles = selector.select_random(n=50, require_summary=True, seed=42)
    
    # Print summary
    print(f"\nSelected {len(articles)} articles:")
    
    # Count by state
    utah_count = sum(1 for a in articles if a["state"] == "Utah")
    california_count = sum(1 for a in articles if a["state"] == "California")
    other_count = len(articles) - utah_count - california_count
    
    print(f"  - Utah: {utah_count}")
    print(f"  - California: {california_count}")
    print(f"  - Other/Unknown: {other_count}")
    
    # Show sample articles
    print("\nFirst 5 articles:")
    for i, article in enumerate(articles[:5], 1):
        print(f"  {i}. {article['title']} ({article['state'] or 'Unknown'})")
    
    # Save to JSON
    selector.save_to_json(articles)
    
    print("\nArticle selection complete!")


if __name__ == "__main__":
    main()