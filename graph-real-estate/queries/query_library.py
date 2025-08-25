"""Query library for real estate graph database"""
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class Query:
    """Represents a Cypher query with metadata"""
    name: str
    description: str
    cypher: str
    category: str
    
class QueryLibrary:
    """Organized collection of Cypher queries for the real estate graph"""
    
    @staticmethod
    def get_basic_queries() -> List[Query]:
        """Basic property lookup queries"""
        return [
            Query(
                name="properties_by_city",
                description="Count properties by city",
                category="basic",
                cypher="""
                MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)-[:IN_CITY]->(c:City)
                RETURN c.name as city, count(p) as count
                ORDER BY count DESC
                """
            ),
            Query(
                name="property_types",
                description="Distribution of property types",
                category="basic",
                cypher="""
                MATCH (p:Property)
                RETURN p.property_type as type, count(p) as count
                ORDER BY count DESC
                """
            ),
            Query(
                name="total_counts",
                description="Count all node types",
                category="basic",
                cypher="""
                MATCH (n)
                RETURN labels(n)[0] as NodeType, count(n) as Count
                ORDER BY Count DESC
                """
            ),
            Query(
                name="bedroom_distribution",
                description="Properties by bedroom count",
                category="basic",
                cypher="""
                MATCH (p:Property)
                RETURN p.bedrooms as bedrooms, count(p) as count
                ORDER BY bedrooms
                """
            ),
            Query(
                name="enhanced_properties_overview",
                description="Overview of enhanced property features",
                category="basic",
                cypher="""
                MATCH (p:Property)
                RETURN count(p) as total_properties,
                       avg(size(p.features)) as avg_features_per_property,
                       avg(p.price_per_sqft) as avg_price_per_sqft
                """
            ),
            Query(
                name="geographic_hierarchy",
                description="Geographic organization overview",
                category="basic",
                cypher="""
                MATCH (co:County)<-[:IN_COUNTY]-(c:City)<-[:IN_CITY]-(n:Neighborhood)
                RETURN co.name as county, c.name as city, count(n) as neighborhoods
                ORDER BY neighborhoods DESC
                """
            )
        ]
    
    @staticmethod
    def get_neighborhood_queries() -> List[Query]:
        """Neighborhood analytics queries"""
        return [
            Query(
                name="expensive_neighborhoods",
                description="Most expensive neighborhoods by average price",
                category="neighborhood",
                cypher="""
                MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
                WITH n, avg(p.listing_price) as avg_price, count(p) as property_count
                WHERE property_count >= 2
                RETURN n.name as neighborhood,
                       n.city as city,
                       avg_price,
                       property_count
                ORDER BY avg_price DESC
                LIMIT 10
                """
            ),
            Query(
                name="neighborhood_stats",
                description="Comprehensive neighborhood statistics",
                category="neighborhood",
                cypher="""
                MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
                RETURN n.name as neighborhood,
                       count(p) as properties,
                       avg(p.listing_price) as avg_price,
                       avg(p.square_feet) as avg_sqft,
                       avg(p.bedrooms) as avg_bedrooms,
                       min(p.listing_price) as min_price,
                       max(p.listing_price) as max_price
                ORDER BY avg_price DESC
                """
            ),
            Query(
                name="connected_neighborhoods",
                description="Neighborhoods and their connections",
                category="neighborhood",
                cypher="""
                MATCH (n:Neighborhood)
                OPTIONAL MATCH (n)-[:NEAR]-(n2:Neighborhood)
                WITH n, count(n2) as connections
                RETURN n.name as neighborhood, 
                       n.city as city,
                       connections
                ORDER BY connections DESC, n.name
                """
            ),
            Query(
                name="lifestyle_neighborhoods",
                description="Neighborhoods by lifestyle tags",
                category="neighborhood",
                cypher="""
                MATCH (n:Neighborhood)
                WHERE n.lifestyle_tags IS NOT NULL AND size(n.lifestyle_tags) > 0
                UNWIND n.lifestyle_tags as tag
                RETURN tag as lifestyle_tag, 
                       collect(n.name)[0..5] as sample_neighborhoods,
                       count(n) as neighborhood_count
                ORDER BY neighborhood_count DESC
                """
            ),
            Query(
                name="neighborhood_similarities",
                description="Most similar neighborhoods",
                category="neighborhood",
                cypher="""
                MATCH (n1:Neighborhood)-[r:SIMILAR_TO]->(n2:Neighborhood)
                WHERE r.similarity_score > 0.5
                RETURN n1.name as neighborhood1,
                       n1.city as city1,
                       n2.name as neighborhood2,
                       n2.city as city2,
                       r.similarity_score as similarity,
                       r.lifestyle_similarity as lifestyle_match
                ORDER BY r.similarity_score DESC
                LIMIT 10
                """
            )
        ]
    
    @staticmethod
    def get_feature_queries() -> List[Query]:
        """Feature-based search queries"""
        return [
            Query(
                name="popular_features",
                description="Most common property features",
                category="feature",
                cypher="""
                MATCH (p:Property)-[:HAS_FEATURE]->(f:Feature)
                RETURN f.name as feature,
                       f.category as category,
                       count(p) as property_count
                ORDER BY property_count DESC
                LIMIT 20
                """
            ),
            Query(
                name="feature_categories",
                description="Feature distribution by category",
                category="feature",
                cypher="""
                MATCH (p:Property)-[:HAS_FEATURE]->(f:Feature)
                RETURN f.category as category,
                       count(DISTINCT f.name) as unique_features,
                       count(p) as connections
                ORDER BY connections DESC
                """
            ),
            Query(
                name="luxury_features",
                description="Properties with luxury features",
                category="feature",
                cypher="""
                MATCH (p:Property)-[:HAS_FEATURE]->(f:Feature)
                WHERE f.name IN ['Pool', 'Hot Tub', 'Sauna', 'Wine Cellar', 'Home Theater']
                WITH p, collect(DISTINCT f.name) as luxury_features
                WHERE size(luxury_features) >= 2
                RETURN p.address as address,
                       p.listing_price as price,
                       luxury_features
                ORDER BY price DESC
                LIMIT 10
                """
            )
        ]
    
    @staticmethod
    def get_price_queries() -> List[Query]:
        """Price analysis queries"""
        return [
            Query(
                name="price_ranges",
                description="Distribution of properties by price range",
                category="price",
                cypher="""
                MATCH (p:Property)-[:IN_PRICE_RANGE]->(pr:PriceRange)
                RETURN pr.range as price_range, count(p) as count
                ORDER BY pr.range
                """
            ),
            Query(
                name="price_per_sqft",
                description="Price per square foot analysis by city",
                category="price",
                cypher="""
                MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)-[:IN_CITY]->(c:City)
                WHERE p.price_per_sqft IS NOT NULL AND p.price_per_sqft > 0
                RETURN c.name as city,
                       avg(p.price_per_sqft) as avg_price_per_sqft,
                       min(p.price_per_sqft) as min_price_per_sqft,
                       max(p.price_per_sqft) as max_price_per_sqft,
                       count(p) as properties
                ORDER BY avg_price_per_sqft DESC
                """
            ),
            Query(
                name="best_value",
                description="Best value properties (lowest price per sqft)",
                category="price",
                cypher="""
                MATCH (p:Property)
                WHERE p.price_per_sqft IS NOT NULL AND p.square_feet > 1500
                RETURN p.address as address,
                       p.listing_price as price,
                       p.square_feet as sqft,
                       p.price_per_sqft as price_per_sqft
                ORDER BY p.price_per_sqft
                LIMIT 10
                """
            )
        ]
    
    @staticmethod
    def get_similarity_queries() -> List[Query]:
        """Property similarity queries"""
        return [
            Query(
                name="similar_properties",
                description="Most similar property pairs",
                category="similarity",
                cypher="""
                MATCH (p1:Property)-[r:SIMILAR_TO]->(p2:Property)
                WHERE r.score > 0.7
                RETURN p1.address as property1,
                       p1.listing_price as price1,
                       p2.address as property2,
                       p2.listing_price as price2,
                       r.score as similarity_score
                ORDER BY r.score DESC
                LIMIT 10
                """
            ),
            Query(
                name="perfect_matches",
                description="Properties with perfect similarity scores",
                category="similarity",
                cypher="""
                MATCH (p1:Property)-[r:SIMILAR_TO]->(p2:Property)
                WHERE r.score >= 1.0
                RETURN p1.address as property1,
                       p2.address as property2,
                       p1.listing_price as price,
                       p1.bedrooms as bedrooms,
                       p1.square_feet as sqft
                ORDER BY p1.listing_price DESC
                """
            )
        ]
    
    @staticmethod
    def get_advanced_queries() -> List[Query]:
        """Advanced analytical queries"""
        return [
            Query(
                name="market_segments",
                description="Market segmentation analysis",
                category="advanced",
                cypher="""
                MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)-[:IN_CITY]->(c:City)
                WITH c.name as city,
                     CASE 
                       WHEN p.listing_price < 1000000 THEN 'Entry Level'
                       WHEN p.listing_price < 2000000 THEN 'Mid Market'
                       WHEN p.listing_price < 3000000 THEN 'Upper Market'
                       ELSE 'Luxury'
                     END as segment,
                     p
                RETURN city, segment,
                       count(p) as count,
                       avg(p.square_feet) as avg_sqft,
                       avg(p.listing_price) as avg_price
                ORDER BY city, segment
                """
            ),
            Query(
                name="investment_opportunities",
                description="Underpriced properties vs neighborhood average",
                category="advanced",
                cypher="""
                MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
                WITH n, avg(p.listing_price) as neighborhood_avg
                MATCH (p2:Property)-[:LOCATED_IN]->(n)
                WHERE p2.listing_price < neighborhood_avg * 0.85
                RETURN p2.address as address,
                       p2.listing_price as price,
                       neighborhood_avg as neighborhood_avg,
                       (neighborhood_avg - p2.listing_price) as potential_upside
                ORDER BY potential_upside DESC
                LIMIT 10
                """
            ),
            Query(
                name="feature_correlation",
                description="Features that commonly appear together",
                category="advanced",
                cypher="""
                MATCH (f1:Feature)<-[:HAS_FEATURE]-(p:Property)-[:HAS_FEATURE]->(f2:Feature)
                WHERE f1.name < f2.name
                WITH f1.name as feature1, f2.name as feature2, count(p) as cooccurrence
                WHERE cooccurrence >= 5
                RETURN feature1, feature2, cooccurrence
                ORDER BY cooccurrence DESC
                LIMIT 15
                """
            ),
            Query(
                name="lifestyle_property_analysis",
                description="Property analysis by neighborhood lifestyle tags",
                category="advanced",
                cypher="""
                MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
                WHERE n.lifestyle_tags IS NOT NULL AND size(n.lifestyle_tags) > 0
                UNWIND n.lifestyle_tags as lifestyle
                WITH lifestyle, 
                     avg(p.listing_price) as avg_price,
                     avg(p.price_per_sqft) as avg_price_per_sqft,
                     count(p) as property_count
                WHERE property_count >= 10
                RETURN lifestyle,
                       avg_price,
                       avg_price_per_sqft,
                       property_count
                ORDER BY avg_price DESC
                """
            ),
            Query(
                name="comprehensive_property_profile",
                description="Complete property analysis with all enhancements",
                category="advanced", 
                cypher="""
                MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)-[:IN_CITY]->(c:City)
                OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature)
                OPTIONAL MATCH (p)-[sim:SIMILAR_TO]->(similar:Property)
                WHERE p.listing_price > 2000000
                WITH p, n, c,
                     collect(DISTINCT f.name)[0..5] as top_features,
                     n.lifestyle_tags as lifestyle,
                     count(DISTINCT similar) as similar_properties
                RETURN p.address as address,
                       p.listing_price as price,
                       p.price_per_sqft as price_per_sqft,
                       c.name as city,
                       n.name as neighborhood,
                       lifestyle,
                       top_features,
                       similar_properties
                ORDER BY p.listing_price DESC
                LIMIT 10
                """
            )
        ]
    
    @staticmethod
    def get_all_queries() -> Dict[str, List[Query]]:
        """Get all queries organized by category"""
        return {
            "basic": QueryLibrary.get_basic_queries(),
            "neighborhood": QueryLibrary.get_neighborhood_queries(),
            "feature": QueryLibrary.get_feature_queries(),
            "price": QueryLibrary.get_price_queries(),
            "similarity": QueryLibrary.get_similarity_queries(),
            "advanced": QueryLibrary.get_advanced_queries()
        }
    
    @staticmethod
    def get_query_by_name(name: str) -> Query:
        """Get a specific query by name"""
        all_queries = QueryLibrary.get_all_queries()
        for category_queries in all_queries.values():
            for query in category_queries:
                if query.name == name:
                    return query
        raise ValueError(f"Query '{name}' not found")
    
    @staticmethod
    def list_all_queries() -> List[str]:
        """List all available query names"""
        all_queries = QueryLibrary.get_all_queries()
        query_names = []
        for category, queries in all_queries.items():
            for query in queries:
                query_names.append(f"{category}/{query.name}")
        return query_names