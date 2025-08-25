"""Demo runner module using Pydantic models"""

import sys
import os
import importlib.util
from pathlib import Path
from typing import Optional, List, Dict, Any
from neo4j import Driver
from pydantic import BaseModel, Field
from .models import DemoConfig
from .database import run_query


class PropertySample(BaseModel):
    """Sample property data model"""
    address: Optional[str] = Field(None, description="Property address")
    price: float = Field(0.0, description="Listing price")
    beds: int = Field(0, description="Number of bedrooms")
    baths: float = Field(0.0, description="Number of bathrooms")
    neighborhood: str = Field("N/A", description="Neighborhood name")
    city: str = Field("N/A", description="City name")


class RelationshipCount(BaseModel):
    """Relationship count model"""
    relationship_type: str = Field(..., description="Type of relationship")
    count: int = Field(0, description="Count of relationships")


class GeographicHierarchy(BaseModel):
    """Geographic hierarchy model"""
    city: str = Field(..., description="City name")
    county: str = Field(..., description="County name")
    state: str = Field(..., description="State name")
    neighborhoods: int = Field(0, description="Number of neighborhoods")


class FeatureCount(BaseModel):
    """Feature count model"""
    feature: str = Field(..., description="Feature name")
    properties: int = Field(0, description="Number of properties with feature")


class PriceAnalysis(BaseModel):
    """Price analysis model"""
    city: str = Field(..., description="City name")
    count: int = Field(0, description="Number of properties")
    avg_price: float = Field(0.0, description="Average price")
    min_price: float = Field(0.0, description="Minimum price")
    max_price: float = Field(0.0, description="Maximum price")


class DemoRunner:
    """Run demonstration scripts for the graph database"""
    
    def __init__(self, driver: Driver, config: DemoConfig):
        """
        Initialize demo runner
        
        Args:
            driver: Neo4j driver instance
            config: Demo configuration
        """
        self.driver = driver
        self.config = config
        self.demos_dir = Path(__file__).parent.parent / "demos"
    
    def run_demo(self) -> None:
        """Run the configured demo"""
        if self.config.demo_number == 1:
            # Run simple demo queries for demo 1
            simple_runner = SimpleDemoRunner(self.driver, self.config)
            simple_runner.run_demo()
        else:
            # Run the existing demo files for demos 2-6
            self._run_demo_file()
    
    def _run_demo_file(self) -> None:
        """Run a demo file from the demos directory"""
        # Map demo numbers to files (shifted by 1 since demo 1 is now SimpleDemoRunner)
        demo_map = {
            2: ("demo_1_hybrid_search_simple.py", "Hybrid Search Simple"),
            3: ("demo_1_hybrid_search.py", "Hybrid Search Advanced"),
            4: ("demo_2_graph_analysis.py", "Graph Analysis"),
            5: ("demo_3_market_intelligence.py", "Market Intelligence"),
        }
        
        if self.config.demo_number not in demo_map:
            # Check for additional demos
            if self.config.demo_number == 6:
                demo_file = "demo_4_wikipedia_enhanced.py"
                demo_title = "Wikipedia Enhanced"
            elif self.config.demo_number == 7:
                demo_file = "demo_5_pure_vector_search.py"
                demo_title = "Pure Vector Search"
            else:
                raise ValueError(f"Demo {self.config.demo_number} not found. Available demos: 1-7")
            demo_path = self.demos_dir / demo_file
        else:
            demo_file, demo_title = demo_map[self.config.demo_number]
            demo_path = self.demos_dir / demo_file
        
        if not demo_path.exists():
            raise FileNotFoundError(f"Demo file not found: {demo_path}")
        
        print(f"\n{'='*60}")
        print(f"DEMO {self.config.demo_number}: {demo_title}")
        print(f"{'='*60}\n")
        
        # Execute the demo module
        self._execute_demo_module(demo_path, demo_file)
    
    def _execute_demo_module(self, demo_path: Path, demo_file: str) -> None:
        """
        Execute a demo module dynamically
        
        Args:
            demo_path: Path to the demo file
            demo_file: Name of the demo file
        """
        # Add the parent directory to sys.path temporarily
        parent_dir = str(demo_path.parent.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        try:
            # Import the demo module dynamically
            spec = importlib.util.spec_from_file_location(
                f"demo_{self.config.demo_number}",
                demo_path
            )
            
            if spec and spec.loader:
                demo_module = importlib.util.module_from_spec(spec)
                
                # Execute the module
                spec.loader.exec_module(demo_module)
                
                # Call the main function if it exists
                if hasattr(demo_module, 'main'):
                    demo_module.main()
                elif hasattr(demo_module, 'run'):
                    demo_module.run()
                elif hasattr(demo_module, 'run_demo'):
                    demo_module.run_demo()
                else:
                    # Module runs on import (many of the existing demos do this)
                    print(f"✓ Demo {self.config.demo_number} executed")
            else:
                raise ImportError(f"Could not load demo module: {demo_file}")
                
        except Exception as e:
            print(f"\n❌ Error running demo {self.config.demo_number}: {e}")
            if self.config.verbose:
                import traceback
                traceback.print_exc()
            raise
        finally:
            # Clean up sys.path
            if parent_dir in sys.path:
                sys.path.remove(parent_dir)


class SimpleDemoRunner:
    """Simple demo runner for basic graph queries (Demo 1)"""
    
    def __init__(self, driver: Driver, config: DemoConfig):
        """
        Initialize simple demo runner
        
        Args:
            driver: Neo4j driver instance
            config: Demo configuration
        """
        self.driver = driver
        self.config = config
    
    def run_demo(self) -> None:
        """Run simple demo queries"""
        print(f"\n{'='*60}")
        print(f"DEMO 1: Basic Graph Queries")
        print(f"{'='*60}\n")
        print("Running basic Neo4j graph queries without external dependencies\n")
        
        # Run all 5 basic demos
        self._demo_1_basic_search(run_query)
        print("\n" + "-"*50 + "\n")
        self._demo_2_relationships(run_query)
        print("\n" + "-"*50 + "\n")
        self._demo_3_analytics(run_query)
        print("\n" + "-"*50 + "\n")
        self._demo_4_wikipedia(run_query)
        print("\n" + "-"*50 + "\n")
        self._demo_5_advanced(run_query)
    
    def _demo_1_basic_search(self, run_query):
        """Section 1: Basic graph search queries"""
        print("📊 SECTION 1: DATABASE OVERVIEW\n")
        
        # Total counts
        query = "MATCH (n) RETURN count(n) as count"
        result = run_query(self.driver, query)
        total_nodes = result[0]['count'] if result else 0
        
        query = "MATCH ()-[r]->() RETURN count(r) as count"
        result = run_query(self.driver, query)
        total_rels = result[0]['count'] if result else 0
        
        print(f"Total nodes: {total_nodes:,}")
        print(f"Total relationships: {total_rels:,}")
        
        # Node breakdown
        print("\nEntity Counts:")
        for label in ['Property', 'Neighborhood', 'City', 'County', 'State', 'Feature', 'Wikipedia']:
            query = f"MATCH (n:{label}) RETURN count(n) as count"
            result = run_query(self.driver, query)
            count = result[0]['count'] if result else 0
            if count > 0:
                print(f"  {label}: {count:,}")
        
        # Sample properties
        print("\nSample Properties:")
        query = """
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        RETURN p.address as address, 
               p.listing_price as price,
               p.bedrooms as beds,
               p.bathrooms as baths,
               n.name as neighborhood,
               p.city as city
        LIMIT 3
        """
        results = run_query(self.driver, query)
        
        # Convert to Pydantic models
        properties = []
        for result in results:
            prop = PropertySample(
                address=result.get('address'),
                price=result.get('price', 0.0),
                beds=result.get('beds', 0),
                baths=result.get('baths', 0.0),
                neighborhood=result.get('neighborhood', 'N/A'),
                city=result.get('city', 'N/A')
            )
            properties.append(prop)
        
        # Display properties
        for i, prop in enumerate(properties, 1):
            print(f"\n{i}. {prop.address or 'N/A'}")
            print(f"   ${prop.price:,.0f} | {prop.beds} bed, {prop.baths} bath")
            print(f"   {prop.neighborhood}, {prop.city}")
    
    def _demo_2_relationships(self, run_query):
        """Section 2: Explore graph relationships"""
        print("📊 SECTION 2: GRAPH RELATIONSHIPS\n")
        
        # Count each relationship type
        print("Relationship Types:")
        rel_types = ['LOCATED_IN', 'IN_CITY', 'IN_COUNTY', 'HAS_FEATURE', 'SIMILAR_TO', 'NEAR', 'DESCRIBES']
        for rel_type in rel_types:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
            result = run_query(self.driver, query)
            count = result[0]['count'] if result else 0
            if count > 0:
                print(f"  {rel_type}: {count:,}")
        
        print("\nGeographic Hierarchy:")
        query = """
        MATCH (c:City)-[:IN_COUNTY]->(co:County)
        OPTIONAL MATCH (c)<-[:IN_CITY]-(n:Neighborhood)
        RETURN c.name as city, co.name as county, c.state as state, 
               count(DISTINCT n) as neighborhoods
        ORDER BY neighborhoods DESC
        LIMIT 3
        """
        results = run_query(self.driver, query)
        for row in results:
            print(f"  {row['city']}, {row['state']} → {row['county']} County ({row['neighborhoods']} neighborhoods)")
        
        print("\nTop 5 Popular Features:")
        query = """
        MATCH (f:Feature)<-[:HAS_FEATURE]-(p:Property)
        RETURN f.name as feature, count(p) as properties
        ORDER BY properties DESC
        LIMIT 5
        """
        results = run_query(self.driver, query)
        for row in results:
            print(f"  {row['feature']}: {row['properties']} properties")
    
    def _demo_3_analytics(self, run_query):
        """Section 3: Analytics queries"""
        print("📊 SECTION 3: ANALYTICS\n")
        
        print("Price Analysis by City:")
        query = """
        MATCH (p:Property)
        WHERE p.listing_price > 0
        RETURN p.city as city,
               count(p) as count,
               avg(p.listing_price) as avg_price,
               min(p.listing_price) as min_price,
               max(p.listing_price) as max_price
        ORDER BY avg_price DESC
        """
        results = run_query(self.driver, query)
        for row in results[:3]:
            print(f"  {row['city']}: {row['count']} properties")
            print(f"    Avg: ${row['avg_price']:,.0f} (${row['min_price']:,.0f} - ${row['max_price']:,.0f})")
        
        print("\nProperty Types:")
        query = """
        MATCH (p:Property)
        WHERE p.property_type IS NOT NULL
        RETURN p.property_type as type, count(p) as count
        ORDER BY count DESC
        LIMIT 3
        """
        results = run_query(self.driver, query)
        for row in results:
            print(f"  {row['type']}: {row['count']} properties")
    
    def _demo_4_wikipedia(self, run_query):
        """Section 4: Wikipedia integration"""
        print("📊 SECTION 4: WIKIPEDIA INTEGRATION\n")
        
        query = "MATCH (w:Wikipedia) RETURN count(w) as count"
        result = run_query(self.driver, query)
        wiki_count = result[0]['count'] if result else 0
        
        if wiki_count > 0:
            print(f"Total Wikipedia articles: {wiki_count}")
            
            print("\nWikipedia Article Types:")
            query = """
            MATCH (w:Wikipedia)
            WHERE w.relationship_type IS NOT NULL
            RETURN w.relationship_type as type, count(w) as count
            ORDER BY count DESC
            LIMIT 3
            """
            results = run_query(self.driver, query)
            for row in results:
                print(f"  {row['type']}: {row['count']}")
            
            print("\nTop Neighborhoods with Wikipedia:")
            query = """
            MATCH (n:Neighborhood)<-[:DESCRIBES]-(w:Wikipedia)
            RETURN n.name as neighborhood, count(w) as articles
            ORDER BY articles DESC
            LIMIT 3
            """
            results = run_query(self.driver, query)
            for row in results:
                print(f"  {row['neighborhood']}: {row['articles']} articles")
        else:
            print("No Wikipedia data found (requires full data pipeline)")
    
    def _demo_5_advanced(self, run_query):
        """Section 5: Advanced analysis"""
        print("📊 SECTION 5: ADVANCED ANALYSIS\n")
        
        print("Property Similarity Network:")
        query = """
        MATCH (p:Property)-[s:SIMILAR_TO]-(other:Property)
        WHERE s.score > 0.8
        RETURN count(DISTINCT p) as similar_properties,
               count(s)/2 as similarity_relationships
        """
        result = run_query(self.driver, query)
        if result and result[0]['similar_properties']:
            row = result[0]
            print(f"  Properties with high similarity: {row['similar_properties']}")
            print(f"  Similarity pairs (score > 0.8): {row['similarity_relationships']}")
        else:
            print("  No similarity relationships found")
        
        print("\nProperties with Most Features:")
        query = """
        MATCH (p:Property)-[:HAS_FEATURE]->(f:Feature)
        WITH p, count(f) as feature_count
        WHERE feature_count >= 5
        RETURN p.address as address, p.listing_price as price, feature_count
        ORDER BY feature_count DESC
        LIMIT 3
        """
        results = run_query(self.driver, query)
        for row in results:
            print(f"  {row['address']}: {row['feature_count']} features (${row['price']:,.0f})")
        
        if self.config.verbose:
            print("\nNote: Verbose mode enabled - showing additional details")
            print("Run with specific demo numbers (2-7) for specialized analysis")