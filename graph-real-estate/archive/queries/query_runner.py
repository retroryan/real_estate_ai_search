"""Query runner for executing and formatting graph queries"""
from typing import List, Dict, Any, Optional
from neo4j import Driver
from tabulate import tabulate
from .query_library import QueryLibrary, Query

class QueryRunner:
    """Executes queries and formats results"""
    
    def __init__(self, driver: Driver):
        """Initialize with Neo4j driver"""
        self.driver = driver
        self.library = QueryLibrary()
    
    def run_query(self, query: Query) -> List[Dict[str, Any]]:
        """Execute a single query and return results"""
        with self.driver.session() as session:
            result = session.run(query.cypher)
            return [dict(record) for record in result]
    
    def run_category(self, category: str) -> Dict[str, List[Dict[str, Any]]]:
        """Run all queries in a category"""
        queries = self.library.get_all_queries().get(category, [])
        results = {}
        
        for query in queries:
            try:
                results[query.name] = self.run_query(query)
            except Exception as e:
                print(f"Error running {query.name}: {e}")
                results[query.name] = []
        
        return results
    
    def format_results(self, results: List[Dict[str, Any]], limit: int = 10) -> str:
        """Format query results as a table"""
        if not results:
            return "No results found"
        
        # Limit results for display
        display_results = results[:limit]
        
        # Format numeric values
        formatted_results = []
        for row in display_results:
            formatted_row = {}
            for key, value in row.items():
                if isinstance(value, float):
                    if 'price' in key.lower() or 'upside' in key.lower():
                        formatted_row[key] = f"${value:,.0f}"
                    elif 'score' in key.lower() or 'percent' in key.lower():
                        formatted_row[key] = f"{value:.2f}"
                    else:
                        formatted_row[key] = f"{value:,.2f}"
                elif isinstance(value, list):
                    formatted_row[key] = ", ".join(str(v) for v in value[:5])
                else:
                    formatted_row[key] = value
            formatted_results.append(formatted_row)
        
        # Create table
        if formatted_results:
            return tabulate(formatted_results, headers="keys", tablefmt="grid")
        return "No results to display"
    
    def run_demo_queries(self):
        """Run a selection of demo queries to showcase the graph"""
        print("\n" + "="*60)
        print("QUERY DEMONSTRATIONS")
        print("="*60)
        
        demo_queries = [
            ("basic", "properties_by_city"),
            ("neighborhood", "expensive_neighborhoods"),
            ("feature", "feature_categories"),
            ("price", "price_ranges"),
            ("similarity", "perfect_matches"),
            ("advanced", "market_segments")
        ]
        
        for category, query_name in demo_queries:
            try:
                query = self.library.get_query_by_name(query_name)
                print(f"\n{query.description}")
                print("-" * 60)
                
                results = self.run_query(query)
                print(self.format_results(results, limit=5))
                
                if len(results) > 5:
                    print(f"... and {len(results) - 5} more results")
                    
            except Exception as e:
                print(f"Error running {query_name}: {e}")
    
    def run_interactive(self):
        """Interactive query runner"""
        print("\n" + "="*60)
        print("INTERACTIVE QUERY RUNNER")
        print("="*60)
        
        categories = list(self.library.get_all_queries().keys())
        
        while True:
            print("\nAvailable categories:")
            for i, cat in enumerate(categories, 1):
                print(f"  {i}. {cat}")
            print("  0. Exit")
            
            try:
                choice = input("\nSelect category (0-{}): ".format(len(categories)))
                if choice == "0":
                    break
                
                category_idx = int(choice) - 1
                if 0 <= category_idx < len(categories):
                    category = categories[category_idx]
                    queries = self.library.get_all_queries()[category]
                    
                    print(f"\nQueries in {category}:")
                    for i, q in enumerate(queries, 1):
                        print(f"  {i}. {q.name}: {q.description}")
                    
                    query_choice = input("\nSelect query (1-{}): ".format(len(queries)))
                    query_idx = int(query_choice) - 1
                    
                    if 0 <= query_idx < len(queries):
                        query = queries[query_idx]
                        print(f"\nRunning: {query.description}")
                        print("-" * 60)
                        
                        results = self.run_query(query)
                        print(self.format_results(results))
                        print(f"\nTotal results: {len(results)}")
                        
            except (ValueError, IndexError) as e:
                print("Invalid selection. Please try again.")
            except Exception as e:
                print(f"Error: {e}")
    
    def export_results(self, category: Optional[str] = None, output_file: str = "query_results.txt"):
        """Export query results to a file"""
        with open(output_file, 'w') as f:
            f.write("REAL ESTATE GRAPH QUERY RESULTS\n")
            f.write("=" * 60 + "\n\n")
            
            if category:
                categories = {category: self.library.get_all_queries().get(category, [])}
            else:
                categories = self.library.get_all_queries()
            
            for cat_name, queries in categories.items():
                f.write(f"\nCATEGORY: {cat_name.upper()}\n")
                f.write("-" * 40 + "\n")
                
                for query in queries:
                    f.write(f"\n{query.name}: {query.description}\n")
                    f.write("-" * 40 + "\n")
                    
                    try:
                        results = self.run_query(query)
                        if results:
                            f.write(self.format_results(results, limit=20))
                        else:
                            f.write("No results found")
                    except Exception as e:
                        f.write(f"Error: {e}")
                    
                    f.write("\n\n")
            
            print(f"Results exported to {output_file}")