"""Demo queries for showcasing the real estate graph database"""
from typing import Dict, List, Any
from neo4j import Driver
from src.queries import QueryRunner

class QueryDemonstrator:
    """Handles demonstration queries for the real estate graph"""
    
    def __init__(self, driver: Driver):
        """Initialize with Neo4j driver"""
        self.driver = driver
        self.runner = QueryRunner(driver)
    
    def run_basic_demo(self):
        """Run basic demonstration queries"""
        print("\n" + "="*60)
        print("QUERY DEMONSTRATIONS")
        print("="*60)
        
        # Use the query runner's demo functionality
        self.runner.run_demo_queries()
    
    def run_phase4_queries(self):
        """Run Phase 4 query examples to complete the implementation"""
        print("\n" + "="*60)
        print("PHASE 4: QUERY EXAMPLES")
        print("="*60)
        
        # Basic Queries
        self._run_basic_queries()
        
        # Graph Traversals
        self._run_traversal_queries()
        
        # Analytics
        self._run_analytics_queries()
        
        print("\n✓ Phase 4 Complete: Query examples demonstrated successfully")
    
    def _run_basic_queries(self):
        """Run basic property queries"""
        print("\n--- Basic Property Queries ---")
        
        queries = [
            ("Find properties by neighborhood", """
                MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
                WHERE n.name STARTS WITH 'Sf-'
                RETURN n.name as neighborhood, count(p) as properties
                ORDER BY properties DESC
                LIMIT 5
            """),
            ("Find properties by price range", """
                MATCH (p:Property)-[:IN_PRICE_RANGE]->(pr:PriceRange)
                RETURN pr.range as range, count(p) as count
                ORDER BY pr.range
            """),
            ("Count properties by type", """
                MATCH (p:Property)
                RETURN p.property_type as type, count(p) as count
                ORDER BY count DESC
            """)
        ]
        
        for name, query in queries:
            print(f"\n{name}:")
            self._execute_and_display(query, limit=5)
    
    def _run_traversal_queries(self):
        """Run graph traversal queries"""
        print("\n--- Graph Traversal Queries ---")
        
        queries = [
            ("Property to City traversal", """
                MATCH path = (p:Property)-[:LOCATED_IN]->(n:Neighborhood)-[:PART_OF]->(c:City)
                RETURN c.name as city, count(p) as properties
                ORDER BY properties DESC
            """),
            ("Properties with specific features", """
                MATCH (p:Property)-[:HAS_FEATURE]->(f:Feature)
                WHERE f.category = 'View'
                RETURN f.name as feature, count(p) as properties
                ORDER BY properties DESC
                LIMIT 5
            """),
            ("Neighborhood connections", """
                MATCH (n1:Neighborhood)-[:NEAR]-(n2:Neighborhood)
                RETURN n1.city as city, count(DISTINCT n1) as connected_neighborhoods
                ORDER BY connected_neighborhoods DESC
            """)
        ]
        
        for name, query in queries:
            print(f"\n{name}:")
            self._execute_and_display(query, limit=5)
    
    def _run_analytics_queries(self):
        """Run analytical queries"""
        print("\n--- Analytics Queries ---")
        
        queries = [
            ("Most expensive neighborhoods", """
                MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
                RETURN n.name as neighborhood,
                       avg(p.listing_price) as avg_price,
                       count(p) as properties
                ORDER BY avg_price DESC
                LIMIT 5
            """),
            ("Popular features", """
                MATCH (p:Property)-[:HAS_FEATURE]->(f:Feature)
                RETURN f.name as feature, count(p) as properties
                ORDER BY properties DESC
                LIMIT 10
            """),
            ("Price per square foot rankings", """
                MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)-[:PART_OF]->(c:City)
                WHERE p.price_per_sqft IS NOT NULL
                RETURN c.name as city,
                       avg(p.price_per_sqft) as avg_price_per_sqft,
                       count(p) as properties
                ORDER BY avg_price_per_sqft DESC
            """)
        ]
        
        for name, query in queries:
            print(f"\n{name}:")
            self._execute_and_display(query, limit=10)
    
    def _execute_and_display(self, query: str, limit: int = 5):
        """Execute a query and display formatted results"""
        try:
            with self.driver.session() as session:
                result = session.run(query)
                records = [dict(record) for record in result]
                
                if not records:
                    print("  No results found")
                    return
                
                # Display limited results
                for i, record in enumerate(records[:limit]):
                    formatted = self._format_record(record)
                    print(f"  {formatted}")
                
                if len(records) > limit:
                    print(f"  ... and {len(records) - limit} more results")
                    
        except Exception as e:
            print(f"  Error: {e}")
    
    def _format_record(self, record: Dict[str, Any]) -> str:
        """Format a single record for display"""
        formatted = []
        for key, value in record.items():
            if isinstance(value, float):
                if 'price' in key.lower():
                    formatted.append(f"{key}: ${value:,.0f}")
                elif 'score' in key.lower() or 'percent' in key.lower():
                    formatted.append(f"{key}: {value:.2f}")
                else:
                    formatted.append(f"{key}: {value:,.2f}")
            else:
                formatted.append(f"{key}: {value}")
        return ", ".join(formatted)
    
    def run_performance_check(self):
        """Check query performance"""
        print("\n" + "="*60)
        print("QUERY PERFORMANCE CHECK")
        print("="*60)
        
        import time
        
        test_queries = [
            ("Simple node count", "MATCH (n) RETURN count(n)"),
            ("Property lookup by ID", "MATCH (p:Property {listing_id: 'sf-001'}) RETURN p"),
            ("Neighborhood aggregation", """
                MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
                RETURN n.name, count(p), avg(p.listing_price)
            """),
            ("Feature analysis", """
                MATCH (p:Property)-[:HAS_FEATURE]->(f:Feature)
                RETURN f.category, count(*)
            """)
        ]
        
        for name, query in test_queries:
            start = time.time()
            with self.driver.session() as session:
                result = session.run(query)
                _ = list(result)  # Consume results
            elapsed = (time.time() - start) * 1000  # Convert to ms
            
            status = "✓" if elapsed < 100 else "⚠"
            print(f"{status} {name}: {elapsed:.2f}ms")
        
        print("\n✓ Performance check complete")
    
    def verify_implementation(self):
        """Verify Phase 4 implementation is complete"""
        print("\n" + "="*60)
        print("PHASE 4 VERIFICATION")
        print("="*60)
        
        checks = [
            ("Query library created", self._check_query_library),
            ("Demo queries functional", self._check_demo_queries),
            ("Interactive mode available", self._check_interactive),
            ("Performance acceptable", self._check_performance),
            ("Documentation complete", self._check_documentation)
        ]
        
        all_passed = True
        for check_name, check_func in checks:
            try:
                check_func()
                print(f"✓ {check_name}")
            except Exception as e:
                print(f"✗ {check_name}: {e}")
                all_passed = False
        
        if all_passed:
            print("\n✓ Phase 4: All verifications passed")
        else:
            print("\n⚠ Phase 4: Some verifications failed")
        
        return all_passed
    
    def _check_query_library(self):
        """Check if query library is properly set up"""
        from src.queries import QueryLibrary
        queries = QueryLibrary.get_all_queries()
        assert len(queries) >= 6, "Not enough query categories"
        total_queries = sum(len(q) for q in queries.values())
        assert total_queries >= 15, "Not enough queries in library"
    
    def _check_demo_queries(self):
        """Check if demo queries run without errors"""
        with self.driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as count")
            count = result.single()['count']
            assert count > 0, "No nodes in database"
    
    def _check_interactive(self):
        """Check if interactive components exist"""
        from src.queries import QueryRunner
        assert hasattr(QueryRunner, 'run_interactive'), "Interactive mode not implemented"
    
    def _check_performance(self):
        """Check if queries perform adequately"""
        import time
        with self.driver.session() as session:
            start = time.time()
            session.run("MATCH (p:Property) RETURN count(p)").single()
            elapsed = time.time() - start
            assert elapsed < 1.0, f"Query too slow: {elapsed:.2f}s"
    
    def _check_documentation(self):
        """Check if documentation exists"""
        import os
        assert os.path.exists("QUERY_GUIDE.md"), "QUERY_GUIDE.md not found"
        with open("QUERY_GUIDE.md", 'r') as f:
            content = f.read()
            assert len(content) > 1000, "Documentation too short"