"""Demo runner module using Pydantic models"""

import sys
import os
import importlib.util
from pathlib import Path
from typing import Optional, List, Dict, Any
from neo4j import Driver
from pydantic import BaseModel, Field
from graph_real_estate.utils.models import DemoConfig
from graph_real_estate.utils.database import run_query
from graph_real_estate.utils.demo_registry import DEMO_REGISTRY, DemoType, DemoEntryPoint
from graph_real_estate.demos.models import (
    RelationshipCount,
    GeographicHierarchy, 
    FeatureCount,
    PriceAnalysis,
    PropertyType,
    WikipediaStats,
    NeighborhoodWikipedia,
    SimilarityNetwork,
    PropertyFeatures
)


class PropertySample(BaseModel):
    """Sample property data model"""
    street: Optional[str] = Field(None, description="Street address")
    listing_price: Optional[float] = Field(None, description="Listing price")
    bedrooms: Optional[int] = Field(None, description="Number of bedrooms")
    bathrooms: Optional[float] = Field(None, description="Number of bathrooms")
    neighborhood: Optional[str] = Field(None, description="Neighborhood name")
    city: Optional[str] = Field(None, description="City name")


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
        """Run the configured demo using the type-safe registry"""
        demo_def = DEMO_REGISTRY.get(self.config.demo_number)
        
        if not demo_def:
            raise ValueError(f"Demo {self.config.demo_number} not found in registry. Available demos: 1-7")
        
        print(f"\n{'='*60}")
        print(f"DEMO {self.config.demo_number}: {demo_def.title}")
        print(f"{'='*60}\n")
        
        if demo_def.demo_type == DemoType.SIMPLE:
            # Run simple demo queries for demo 1
            simple_runner = SimpleDemoRunner(self.driver, self.config)
            simple_runner.run_demo()
        elif demo_def.demo_type == DemoType.MODULE:
            # Run the demo from a module file
            if not demo_def.file_name:
                raise ValueError(f"Demo {self.config.demo_number} is type MODULE but has no file_name")
            if not demo_def.entry_point:
                raise ValueError(f"Demo {self.config.demo_number} is type MODULE but has no entry_point")
            
            demo_path = self.demos_dir / demo_def.file_name
            if not demo_path.exists():
                raise FileNotFoundError(f"Demo file not found: {demo_path}")
            
            # Execute the demo module with the specified entry point
            self._execute_demo_module(demo_path, demo_def.file_name, demo_def.entry_point)
    
    def _execute_demo_module(self, demo_path: Path, demo_file: str, entry_point: str) -> None:
        """
        Execute a demo module dynamically with type-safe entry point
        
        Args:
            demo_path: Path to the demo file
            demo_file: Name of the demo file
            entry_point: The entry point function name to call
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
                
                # Call the specified entry point function
                # entry_point is already a string value when use_enum_values=True
                entry_func = getattr(demo_module, entry_point, None)
                if entry_func and callable(entry_func):
                    entry_func()
                else:
                    raise AttributeError(
                        f"Demo module {demo_file} does not have callable function '{entry_point}'"
                    )
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
        
        print("🚀 NEO4J FEATURES DEMONSTRATED:")
        print("   • Node Labels & Properties - Property, Neighborhood, City, Feature nodes")
        print("   • Relationship Types - LOCATED_IN, IN_CITY, HAS_FEATURE relationships")
        print("   • Pattern Matching - MATCH patterns for traversing the graph")
        print("   • Aggregation Functions - COUNT, AVG, MIN, MAX for analytics")
        print("   • OPTIONAL MATCH - Handling missing relationships gracefully")
        print("   • Property Filtering - WHERE clauses on node properties")
        print("   • Graph Traversal - Multi-hop relationship navigation\n")
        
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
        RETURN p.street_address, 
               p.listing_price,
               p.bedrooms,
               p.bathrooms,
               n.name as neighborhood_name,
               p.city
        LIMIT 3
        """
        results = run_query(self.driver, query)
        
        # Convert to Pydantic models
        properties = []
        for result in results:
            prop = PropertySample(
                street=result.get('p.street_address'),
                listing_price=result.get('p.listing_price', 0.0),
                bedrooms=result.get('p.bedrooms', 0),
                bathrooms=result.get('p.bathrooms', 0.0),
                neighborhood=result.get('neighborhood_name'),
                city=result.get('p.city')
            )
            properties.append(prop)
        
        # Display properties
        for i, prop in enumerate(properties, 1):
            print(f"\n{i}. {prop.street or 'N/A'}")
            price = prop.listing_price or 0
            bedrooms = prop.bedrooms or 0
            bathrooms = prop.bathrooms or 0
            print(f"   ${price:,.0f} | {bedrooms} bed, {bathrooms} bath")
            print(f"   {prop.neighborhood or 'N/A'}, {prop.city or 'N/A'}")
    
    def _demo_2_relationships(self, run_query):
        """Section 2: Explore graph relationships"""
        print("📊 SECTION 2: GRAPH RELATIONSHIPS\n")
        
        # Count each relationship type
        print("Relationship Types:")
        rel_types = ['LOCATED_IN', 'IN_CITY', 'IN_COUNTY', 'HAS_FEATURE', 'NEAR', 'DESCRIBES']
        relationship_counts = []
        for rel_type in rel_types:
            query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
            result = run_query(self.driver, query)
            count = result[0]['count'] if result else 0
            if count > 0:
                rel_count = RelationshipCount(relationship_type=rel_type, count=count)
                relationship_counts.append(rel_count)
                print(f"  {rel_count.relationship_type}: {rel_count.count:,}")
        
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
        hierarchies = []
        for row in results:
            hierarchy = GeographicHierarchy(
                city=row['city'],
                county=row['county'],
                state=row['state'],
                neighborhoods=row['neighborhoods']
            )
            hierarchies.append(hierarchy)
            print(f"  {hierarchy.city}, {hierarchy.state} → {hierarchy.county} County ({hierarchy.neighborhoods} neighborhoods)")
        
        print("\nTop 5 Popular Features:")
        query = """
        MATCH (f:Feature)<-[:HAS_FEATURE]-(p:Property)
        RETURN f.name as feature, count(p) as properties
        ORDER BY properties DESC
        LIMIT 5
        """
        results = run_query(self.driver, query)
        feature_counts = []
        for row in results:
            feature = FeatureCount(
                feature=row['feature'],
                properties=row['properties']
            )
            feature_counts.append(feature)
            print(f"  {feature.feature}: {feature.properties} properties")
    
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
        price_analyses = []
        for row in results[:3]:
            analysis = PriceAnalysis(
                city=row['city'],
                count=row['count'],
                avg_price=row['avg_price'],
                min_price=row['min_price'],
                max_price=row['max_price']
            )
            price_analyses.append(analysis)
            city_display = analysis.city or "Unknown"
            print(f"  {city_display}: {analysis.count} properties")
            print(f"    Avg: ${analysis.avg_price:,.0f} (${analysis.min_price:,.0f} - ${analysis.max_price:,.0f})")
        
        print("\nProperty Types:")
        query = """
        MATCH (p:Property)
        WHERE p.property_type IS NOT NULL
        RETURN p.property_type as type, count(p) as count
        ORDER BY count DESC
        LIMIT 3
        """
        results = run_query(self.driver, query)
        property_types = []
        for row in results:
            prop_type = PropertyType(
                type=row['type'],
                count=row['count']
            )
            property_types.append(prop_type)
            print(f"  {prop_type.type}: {prop_type.count} properties")
    
    def _demo_4_wikipedia(self, run_query):
        """Section 4: Wikipedia integration"""
        print("📊 SECTION 4: WIKIPEDIA INTEGRATION\n")
        
        query = "MATCH (w:WikipediaArticle) RETURN count(w) as count"
        result = run_query(self.driver, query)
        wiki_count = result[0]['count'] if result else 0
        
        if wiki_count > 0:
            print(f"Total Wikipedia articles: {wiki_count}")
            
            print("\nWikipedia Article Types:")
            query = """
            MATCH (w:WikipediaArticle)
            WHERE w.content_category IS NOT NULL
            RETURN w.content_category as type, count(w) as count
            ORDER BY count DESC
            LIMIT 3
            """
            results = run_query(self.driver, query)
            wiki_stats = []
            for row in results:
                stat = WikipediaStats(
                    article_type=row['type'],
                    count=row['count']
                )
                wiki_stats.append(stat)
                print(f"  {stat.article_type}: {stat.count}")
            
            print("\nTop Neighborhoods with Wikipedia:")
            query = """
            MATCH (n:Neighborhood)<-[:DESCRIBES]-(w:WikipediaArticle)
            RETURN n.name as neighborhood, count(w) as articles
            ORDER BY articles DESC
            LIMIT 3
            """
            results = run_query(self.driver, query)
            neighborhood_wikis = []
            for row in results:
                n_wiki = NeighborhoodWikipedia(
                    neighborhood=row['neighborhood'],
                    articles=row['articles']
                )
                neighborhood_wikis.append(n_wiki)
                print(f"  {n_wiki.neighborhood}: {n_wiki.articles} articles")
        else:
            print("No Wikipedia data found (requires full data pipeline)")
    
    def _demo_5_advanced(self, run_query):
        """Section 5: Advanced analysis"""
        print("📊 SECTION 5: ADVANCED ANALYSIS\n")
        
        print("Property Embedding Status:")
        query = """
        MATCH (p:Property)
        RETURN count(p) as total_properties,
               count(CASE WHEN p.embedding IS NOT NULL THEN 1 END) as properties_with_embeddings
        """
        result = run_query(self.driver, query)
        if result:
            total = result[0]['total_properties']
            with_embeddings = result[0]['properties_with_embeddings']
            print(f"  Total properties: {total}")
            print(f"  Properties with embeddings: {with_embeddings}")
            if with_embeddings > 0:
                print(f"  Coverage: {(with_embeddings/total)*100:.1f}%")
        else:
            print("  No properties found")
        
        print("\nProperties with Most Features:")
        query = """
        MATCH (p:Property)-[:HAS_FEATURE]->(f:Feature)
        WITH p, count(f) as feature_count
        WHERE feature_count >= 5
        RETURN p.street as address, p.listing_price as price, feature_count
        ORDER BY feature_count DESC
        LIMIT 3
        """
        results = run_query(self.driver, query)
        property_features = []
        for row in results:
            prop_feat = PropertyFeatures(
                address=row['address'],
                price=row['price'],
                feature_count=row['feature_count']
            )
            property_features.append(prop_feat)
            print(f"  {prop_feat.address}: {prop_feat.feature_count} features (${prop_feat.price:,.0f})")
        
        if self.config.verbose:
            print("\nNote: Verbose mode enabled - showing additional details")
            print("Run with specific demo numbers (2-7) for specialized analysis")