"""Graph builder controller for real estate data with Wikipedia enhancement"""
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime
from pathlib import Path
from database import get_neo4j_driver, close_neo4j_driver, run_query, clear_database, print_stats
from data_loader import (
    load_property_data, 
    validate_property_data, 
    get_unique_neighborhoods, 
    get_unique_features,
    get_unique_cities,
    load_enhanced_property_data,
    load_wikipedia_data
)
from models import Property, PropertyDetails, Neighborhood, City, Feature, PriceRange, GraphStats


class RealEstateGraphBuilder:
    """Main controller for building the real estate graph database with Wikipedia enhancement"""
    
    def __init__(self):
        """Initialize the graph builder with database connection and data"""
        self.driver = get_neo4j_driver()
        self.data = load_property_data()
        self.stats = GraphStats()
        self.base_path = Path(__file__).parent.parent.parent
        
    def setup_environment(self) -> bool:
        """Environment Setup & Data Preparation with Pydantic validation"""
        print("\n" + "="*60)
        print("ENVIRONMENT SETUP & DATA PREPARATION")
        print("="*60)
        print("Using Pydantic for data validation and type safety")
        
        # Test Neo4j connectivity
        try:
            result = run_query(self.driver, "RETURN 1 as test")
            print("Neo4j connection successful")
        except Exception as e:
            print(f"Neo4j connection failed: {e}")
            return False
        
        # Report loaded data (already validated by Pydantic)
        print(f"\nLoaded {len(self.data['sf'])} SF properties (Pydantic validated)")
        print(f"Loaded {len(self.data['pc'])} Park City properties (Pydantic validated)")
        print(f"Total properties: {len(self.data['all'])}")
        
        # Check for Wikipedia data in JSON files
        try:
            wiki_data = load_wikipedia_data()
            if wiki_data is not None and not wiki_data.empty:
                count = len(wiki_data)
                print(f"Wikipedia data found in JSON files")
                print(f"  - Contains {count} neighborhood-Wikipedia relationships")
            else:
                print("No Wikipedia data found in JSON files - some features will be limited")
        except Exception as e:
            print(f"  - Warning: Could not read Wikipedia data from JSON: {e}")
        
        # Validate data structure
        print("\nValidating data structure with Pydantic...")
        sf_valid = validate_property_data(self.data['sf'])
        pc_valid = validate_property_data(self.data['pc'])
        
        if sf_valid and pc_valid:
            print("\nEnvironment Setup Complete: Ready with Pydantic validation")
            return True
        else:
            print("\nWarning: Environment Setup: Some validation warnings (continuing anyway)")
            return True
    
    def create_schema(self) -> bool:
        """Enhanced Graph Schema Implementation with Wikipedia integration"""
        print("\n" + "="*60)
        print("ENHANCED GRAPH SCHEMA WITH WIKIPEDIA INTEGRATION")
        print("="*60)
        
        # Clear existing data
        print("\nStep 1: Clearing existing data...")
        self._clear_database()
        
        # Create enhanced constraints and indexes
        print("\nStep 2: Creating constraints and indexes...")
        self._create_constraints_and_indexes()
        
        # Create geographic hierarchy (Cities and Counties)
        print("\nStep 3: Creating geographic hierarchy...")
        self._create_geographic_hierarchy()
        
        # Create enhanced neighborhoods
        print("\nStep 4: Creating enhanced neighborhoods...")
        self._create_enhanced_neighborhoods()
        
        # Create price ranges
        print("\nStep 5: Creating price ranges...")
        self._create_price_ranges()
        
        # Load enhanced properties
        print("\nStep 6: Loading enhanced properties...")
        self._create_enhanced_properties()
        
        # Create property types
        print("\nStep 7: Creating property types...")
        self._create_property_types()
        
        # Import Wikipedia data from JSON files
        print("\nStep 8: Importing Wikipedia articles...")
        self._import_wikipedia_articles()
        
        print_stats(self.driver)
        print("\nSchema Creation Complete: Enhanced graph schema with Wikipedia integration")
        return True
    
    def _clear_database(self):
        """Clear all existing data from the database"""
        clear_database(self.driver)
        print("  Database cleared")
    
    def _create_constraints_and_indexes(self):
        """Create all necessary constraints and indexes"""
        constraints = [
            ("property_id", "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Property) REQUIRE p.listing_id IS UNIQUE"),
            ("neighborhood_id", "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Neighborhood) REQUIRE n.neighborhood_id IS UNIQUE"),
            ("city_id", "CREATE CONSTRAINT IF NOT EXISTS FOR (c:City) REQUIRE c.city_id IS UNIQUE"),
            ("county_id", "CREATE CONSTRAINT IF NOT EXISTS FOR (co:County) REQUIRE co.county_id IS UNIQUE"),
            ("wikipedia_id", "CREATE CONSTRAINT IF NOT EXISTS FOR (w:Wikipedia) REQUIRE w.page_id IS UNIQUE"),
            ("feature_name", "CREATE CONSTRAINT IF NOT EXISTS FOR (f:Feature) REQUIRE f.name IS UNIQUE"),
            ("price_range", "CREATE CONSTRAINT IF NOT EXISTS FOR (pr:PriceRange) REQUIRE pr.range IS UNIQUE")
        ]
        
        for name, constraint in constraints:
            try:
                run_query(self.driver, constraint)
                print(f"  Constraint created: {name}")
            except Exception as e:
                print(f"  Warning: Constraint {name} may already exist")
        
        # Create indexes for performance
        indexes = [
            ("property_price", "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.listing_price)"),
            ("property_type", "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.property_type)"),
            ("property_bedrooms", "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.bedrooms)"),
            ("neighborhood_city", "CREATE INDEX IF NOT EXISTS FOR (n:Neighborhood) ON (n.city)"),
            ("neighborhood_walkability", "CREATE INDEX IF NOT EXISTS FOR (n:Neighborhood) ON (n.walkability_score)"),
            ("wikipedia_type", "CREATE INDEX IF NOT EXISTS FOR (w:Wikipedia) ON (w.relationship_type)"),
            ("wikipedia_confidence", "CREATE INDEX IF NOT EXISTS FOR (w:Wikipedia) ON (w.confidence)")
        ]
        
        for name, index in indexes:
            try:
                run_query(self.driver, index)
                print(f"  Index created: {name}")
            except Exception as e:
                print(f"  Warning: Index {name}: {e}")
    
    def _create_geographic_hierarchy(self):
        """Create Cities and Counties with proper relationships"""
        # Get unique cities with enhanced IDs
        cities = get_unique_cities(self.data['all'])
        city_mapping = {}
        
        for city in cities:
            city_id = f"{city.name}_{city.state}".lower().replace(' ', '_')
            city_mapping[city.name] = city_id
            
            query = """
            MERGE (c:City {city_id: $city_id})
            SET c.name = $name, c.state = $state
            """
            run_query(self.driver, query, {
                'city_id': city_id,
                'name': city.name,
                'state': city.state
            })
        
        print(f"  {len(cities)} Cities created")
        
        # Create Counties based on city mappings
        county_mapping = {
            'San Francisco': 'San Francisco',
            'Daly City': 'San Francisco',
            'San Jose': 'Santa Clara',
            'Saratoga': 'Santa Clara',
            'Los Gatos': 'Santa Clara',
            'Park City': 'Summit',
            'Kamas': 'Summit',
            'Oakley': 'Summit',
            'Coalville': 'Summit',
            'Heber City': 'Wasatch'
        }
        
        counties_created = set()
        for city in cities:
            county_name = county_mapping.get(city.name, 'Unknown')
            county_id = f"{county_name}_{city.state}".lower().replace(' ', '_')
            
            if county_id not in counties_created:
                query = """
                MERGE (co:County {county_id: $county_id})
                SET co.name = $name, co.state = $state
                """
                run_query(self.driver, query, {
                    'county_id': county_id,
                    'name': county_name,
                    'state': city.state
                })
                counties_created.add(county_id)
            
            # Link city to county
            city_id = city_mapping[city.name]
            query = """
            MATCH (c:City {city_id: $city_id})
            MATCH (co:County {county_id: $county_id})
            MERGE (c)-[:IN_COUNTY]->(co)
            """
            run_query(self.driver, query, {
                'city_id': city_id,
                'county_id': county_id
            })
        
        print(f"  {len(counties_created)} Counties created and linked")
    
    def _create_enhanced_neighborhoods(self):
        """Create neighborhoods with enhanced attributes"""
        neighborhoods = get_unique_neighborhoods(self.data['all'])
        
        # Load enhanced neighborhood data if available
        enhanced_data = load_enhanced_property_data() if hasattr(self, 'load_enhanced_property_data') else {}
        
        for neighborhood in neighborhoods:
            # Generate lifestyle tags based on characteristics
            lifestyle_tags = self._generate_lifestyle_tags(neighborhood)
            
            # Determine price trend (simplified for now)
            price_trend = 'stable'
            
            # Use neighborhood_id as unique identifier
            neighborhood_id = neighborhood.id
            city_id = f"{neighborhood.city}_{neighborhood.state}".lower().replace(' ', '_')
            
            query = """
            MATCH (c:City {city_id: $city_id})
            MERGE (n:Neighborhood {neighborhood_id: $neighborhood_id})
            SET n.name = $name,
                n.city = $city,
                n.state = $state,
                n.lifestyle_tags = $lifestyle_tags,
                n.price_trend = $price_trend,
                n.created_at = datetime()
            MERGE (n)-[:IN_CITY]->(c)
            """
            
            run_query(self.driver, query, {
                'neighborhood_id': neighborhood_id,
                'name': neighborhood.name,
                'city': neighborhood.city,
                'state': neighborhood.state,
                'city_id': city_id,
                'lifestyle_tags': lifestyle_tags,
                'price_trend': price_trend
            })
        
        print(f"  {len(neighborhoods)} Enhanced neighborhoods created")
    
    def _generate_lifestyle_tags(self, neighborhood) -> List[str]:
        """Generate lifestyle tags based on neighborhood characteristics"""
        tags = []
        
        # Location-based tags
        if neighborhood.city == 'Park City':
            tags.extend(['mountain', 'ski-access', 'outdoor-recreation'])
        elif neighborhood.city in ['San Francisco', 'San Jose']:
            tags.extend(['urban', 'tech-friendly'])
        
        # Name-based tags
        name_lower = neighborhood.name.lower()
        if 'downtown' in name_lower or 'soma' in name_lower:
            tags.append('downtown')
        if 'beach' in name_lower or 'marina' in name_lower:
            tags.append('waterfront')
        if 'heights' in name_lower or 'hill' in name_lower:
            tags.append('elevated')
        if 'park' in name_lower:
            tags.append('park-adjacent')
        
        return list(set(tags))  # Remove duplicates
    
    def _create_price_ranges(self):
        """Create price range nodes"""
        for price_range in PriceRange:
            query = "MERGE (pr:PriceRange {range: $range})"
            run_query(self.driver, query, {'range': price_range.value})
        
        print(f"  {len(PriceRange)} Price ranges created")
    
    def _create_enhanced_properties(self):
        """Create property nodes with enhanced attributes"""
        for prop in self.data['all']:
            # Calculate additional metrics
            price_range = prop.calculate_price_range()
            coords = prop.get_coordinates_dict()
            price_per_sqft = prop.listing_price / prop.get_square_feet() if prop.get_square_feet() > 0 else 0
            
            # Extract features list (if available)
            features = getattr(prop, 'features', [])
            
            query = """
            MATCH (n:Neighborhood {neighborhood_id: $neighborhood_id})
            MATCH (pr:PriceRange {range: $price_range})
            CREATE (p:Property {
                listing_id: $listing_id,
                neighborhood_id: $neighborhood_id,
                address: $address,
                listing_price: $listing_price,
                property_type: $property_type,
                bedrooms: $bedrooms,
                bathrooms: $bathrooms,
                square_feet: $square_feet,
                year_built: $year_built,
                description: $description,
                features: $features,
                latitude: $latitude,
                longitude: $longitude,
                price_per_sqft: $price_per_sqft,
                listing_date: $listing_date,
                city: $city,
                state: $state,
                created_at: datetime()
            })
            CREATE (p)-[:LOCATED_IN]->(n)
            CREATE (p)-[:IN_PRICE_RANGE]->(pr)
            """
            
            params = {
                'neighborhood_id': prop.neighborhood_id,
                'price_range': price_range,
                'listing_id': prop.listing_id,
                'address': prop.get_address_string(),
                'listing_price': prop.listing_price,
                'property_type': prop.get_property_type(),
                'bedrooms': prop.get_bedrooms(),
                'bathrooms': prop.get_bathrooms(),
                'square_feet': prop.get_square_feet(),
                'year_built': prop.get_year_built(),
                'description': prop.description or '',
                'features': features,
                'latitude': coords.get('lat', 0),
                'longitude': coords.get('lng', 0),
                'price_per_sqft': int(price_per_sqft),
                'listing_date': prop.listing_date or '',
                'city': prop.city or '',
                'state': prop.state or ''
            }
            
            run_query(self.driver, query, params)
        
        print(f"  {len(self.data['all'])} Enhanced properties created")
    
    def _create_property_types(self):
        """Create property type nodes and relationships"""
        property_types = set()
        for prop in self.data['all']:
            prop_type = prop.get_property_type()
            if prop_type:
                property_types.add(prop_type)
        
        for pt in property_types:
            query = "MERGE (pt:PropertyType {name: $name})"
            run_query(self.driver, query, {'name': pt})
            
            # Link properties to their types
            query = """
            MATCH (p:Property {property_type: $type})
            MATCH (pt:PropertyType {name: $type})
            MERGE (p)-[:TYPE_OF]->(pt)
            """
            run_query(self.driver, query, {'type': pt})
        
        print(f"  {len(property_types)} Property types created and linked")
    
    def _import_wikipedia_articles(self):
        """Import Wikipedia articles and create relationships to neighborhoods"""
        try:
            # Load Wikipedia data from JSON files
            wiki_df = load_wikipedia_data()
            
            if wiki_df is None or wiki_df.empty:
                print(f"  No Wikipedia data found in JSON files")
                return
            
            # Create Wikipedia nodes
            created_pages = set()
            for _, row in wiki_df.iterrows():
                if row['page_id'] not in created_pages:
                    params = {
                        'page_id': int(row['page_id']),
                        'title': row['title'] or f"Page {row['page_id']}",
                        'summary': (row['summary'][:500] if row['summary'] else "") if pd.notna(row['summary']) else "",
                        'url': row['url'] or "",
                        'confidence': float(row['confidence_score']) if pd.notna(row['confidence_score']) else 0.5,
                        'is_synthetic': float(row['confidence_score']) < 0.5 if pd.notna(row['confidence_score']) else False,
                        'relationship_type': row['relationship_type'] or 'general'
                    }
                    
                    query = """
                    CREATE (w:Wikipedia {
                        page_id: $page_id,
                        title: $title,
                        summary: $summary,
                        url: $url,
                        confidence: $confidence,
                        is_synthetic: $is_synthetic,
                        relationship_type: $relationship_type,
                        last_updated: datetime()
                    })
                    """
                    
                    run_query(self.driver, query, params)
                    created_pages.add(row['page_id'])
            
            print(f"  {len(created_pages)} Wikipedia nodes created")
            
            # Create DESCRIBES relationships
            relationship_count = 0
            for _, row in wiki_df.iterrows():
                params = {
                    'page_id': int(row['page_id']),
                    'neighborhood_id': row['neighborhood_id'],
                    'confidence': float(row['confidence_score']) if pd.notna(row['confidence_score']) else 0.5,
                    'relationship_type': row['relationship_type'] or 'general'
                }
                
                # Try to match and create relationship
                query = """
                MATCH (w:Wikipedia {page_id: $page_id})
                MATCH (n:Neighborhood {neighborhood_id: $neighborhood_id})
                CREATE (w)-[:DESCRIBES {
                    confidence: $confidence,
                    relationship_type: $relationship_type
                }]->(n)
                RETURN w, n
                """
                
                try:
                    result = run_query(self.driver, query, params)
                    if result:
                        relationship_count += 1
                except:
                    pass  # Neighborhood might not exist
            
            print(f"  {relationship_count} Wikipedia DESCRIBES relationships created")
            
        except Exception as e:
            print(f"  Warning: Error importing Wikipedia data: {e}")
    
    def create_relationships(self) -> bool:
        """Create Enhanced Graph Relationships including Wikipedia and similarity"""
        print("\n" + "="*60)
        print("ENHANCED GRAPH RELATIONSHIPS CREATION")
        print("="*60)
        
        # Create feature relationships
        print("\nStep 1: Creating feature relationships...")
        self._create_feature_relationships()
        
        # Create property similarities
        print("\nStep 2: Calculating property similarities...")
        self._create_property_similarities()
        
        # Create neighborhood connections
        print("\nStep 3: Creating neighborhood connections...")
        self._create_neighborhood_connections()
        
        # Create neighborhood similarities (with Wikipedia overlap if available)
        print("\nStep 4: Calculating neighborhood similarities...")
        self._create_neighborhood_similarities()
        
        # Generate enriched descriptions with Wikipedia data from JSON
        print("\nStep 5: Generating enriched property descriptions...")
        self._generate_enriched_descriptions()
        
        print_stats(self.driver)
        print("\nRelationship Creation Complete: Enhanced graph relationships established")
        return True
    
    def _create_feature_relationships(self):
        """Create feature nodes and link to properties"""
        features = get_unique_features(self.data['all'])
        
        # Group features by category for reporting
        categories = {}
        for feature in features:
            query = "MERGE (f:Feature {name: $name}) SET f.category = $category"
            run_query(self.driver, query, {'name': feature.name, 'category': feature.category})
            
            cat = feature.category or 'Other'
            categories[cat] = categories.get(cat, 0) + 1
        
        print(f"  {len(features)} Features created")
        for cat, count in sorted(categories.items()):
            print(f"    - {cat}: {count} features")
        
        # Link properties to features
        feature_links = 0
        for prop in self.data['all']:
            if prop.features:
                for feature_name in prop.features:
                    query = """
                    MATCH (p:Property {listing_id: $listing_id})
                    MATCH (f:Feature {name: $feature})
                    MERGE (p)-[:HAS_FEATURE]->(f)
                    """
                    run_query(self.driver, query, {
                        'listing_id': prop.listing_id,
                        'feature': feature_name
                    })
                    feature_links += 1
        
        print(f"  {feature_links} Property-feature relationships created")
    
    def _create_property_similarities(self):
        """Calculate and create similarity relationships between properties"""
        query = """
        MATCH (p1:Property)-[:LOCATED_IN]->(n:Neighborhood)<-[:LOCATED_IN]-(p2:Property)
        WHERE p1.listing_id < p2.listing_id
        AND abs(p1.listing_price - p2.listing_price) / p1.listing_price < 0.2
        AND p1.property_type = p2.property_type
        AND abs(p1.bedrooms - p2.bedrooms) <= 1
        AND abs(p1.square_feet - p2.square_feet) / p1.square_feet < 0.3
        WITH p1, p2, 
             (1.0 - abs(p1.listing_price - p2.listing_price) / p1.listing_price) * 0.4 +
             (1.0 - abs(p1.square_feet - p2.square_feet) / p1.square_feet) * 0.3 +
             (CASE WHEN p1.bedrooms = p2.bedrooms THEN 0.2 ELSE 0.1 END) +
             (CASE WHEN p1.bathrooms = p2.bathrooms THEN 0.1 ELSE 0.0 END) as similarity_score
        WHERE similarity_score > 0.5
        CREATE (p1)-[:SIMILAR_TO {score: similarity_score}]->(p2)
        CREATE (p2)-[:SIMILAR_TO {score: similarity_score}]->(p1)
        """
        
        run_query(self.driver, query)
        
        # Count similarities created
        query = "MATCH ()-[r:SIMILAR_TO]->() RETURN count(DISTINCT r) as count"
        result = run_query(self.driver, query)
        sim_count = result[0]['count'] if result else 0
        
        print(f"  {sim_count} Property similarity relationships created")
    
    def _create_neighborhood_connections(self):
        """Create connections between neighborhoods in the same city"""
        query = """
        MATCH (n1:Neighborhood)-[:IN_CITY]->(c:City)<-[:IN_CITY]-(n2:Neighborhood)
        WHERE n1.neighborhood_id < n2.neighborhood_id
        MERGE (n1)-[:NEAR]->(n2)
        MERGE (n2)-[:NEAR]->(n1)
        """
        run_query(self.driver, query)
        
        # Count neighborhood connections
        query = "MATCH (n1:Neighborhood)-[r:NEAR]->(n2:Neighborhood) RETURN count(DISTINCT r) as count"
        result = run_query(self.driver, query)
        near_count = result[0]['count'] if result else 0
        
        print(f"  {near_count} Neighborhood connections created")
    
    def _create_neighborhood_similarities(self):
        """Calculate and create similarity relationships between neighborhoods"""
        # Get all neighborhoods with their data
        query = """
        MATCH (n:Neighborhood)
        OPTIONAL MATCH (n)<-[:DESCRIBES]-(w:Wikipedia)
        RETURN n.neighborhood_id as id,
               n.name as name,
               n.lifestyle_tags as tags,
               collect(DISTINCT w.relationship_type) as wiki_types
        """
        
        neighborhoods = run_query(self.driver, query)
        
        similarity_count = 0
        for i, n1 in enumerate(neighborhoods):
            for n2 in neighborhoods[i+1:]:
                # Lifestyle tag similarity
                tags1 = set(n1['tags'] or [])
                tags2 = set(n2['tags'] or [])
                tag_sim = len(tags1 & tags2) / len(tags1 | tags2) if (tags1 | tags2) else 0
                
                # Wikipedia overlap
                wiki1 = set(n1['wiki_types'] or [])
                wiki2 = set(n2['wiki_types'] or [])
                wiki_sim = len(wiki1 & wiki2) / len(wiki1 | wiki2) if (wiki1 | wiki2) else 0
                
                # Overall similarity
                overall_sim = (tag_sim * 0.6 + wiki_sim * 0.4)
                
                # Only create relationship if similarity is significant
                if overall_sim > 0.3:
                    query = """
                    MATCH (n1:Neighborhood {neighborhood_id: $id1})
                    MATCH (n2:Neighborhood {neighborhood_id: $id2})
                    CREATE (n1)-[:SIMILAR_TO {
                        similarity_score: $overall,
                        lifestyle_similarity: $lifestyle,
                        wikipedia_overlap: $wiki
                    }]->(n2)
                    """
                    
                    run_query(self.driver, query, {
                        'id1': n1['id'],
                        'id2': n2['id'],
                        'overall': overall_sim,
                        'lifestyle': tag_sim,
                        'wiki': wiki_sim
                    })
                    similarity_count += 1
        
        print(f"  {similarity_count} Neighborhood similarity relationships created")
    
    def _generate_enriched_descriptions(self):
        """Generate enriched descriptions for properties using Wikipedia context"""
        query = """
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        OPTIONAL MATCH (n)<-[:DESCRIBES]-(w:Wikipedia)
        WHERE w.confidence > 0.3
        WITH p, n, collect(DISTINCT {
            title: w.title,
            type: w.relationship_type
        }) as wiki_articles
        RETURN p.listing_id as listing_id,
               p.description as description,
               n.name as neighborhood,
               wiki_articles
        LIMIT 100
        """
        
        properties = run_query(self.driver, query)
        
        count = 0
        for prop in properties:
            # Build enriched description
            wiki_context = ""
            if prop['wiki_articles']:
                landmarks = [w['title'] for w in prop['wiki_articles'] 
                           if w['type'] in ['landmark', 'park', 'cultural']]
                if landmarks:
                    wiki_context = f" Located near {', '.join(landmarks[:2])}."
            
            enriched = f"{prop['description']}{wiki_context}"
            
            # Update property with enriched description
            update_query = """
            MATCH (p:Property {listing_id: $listing_id})
            SET p.enriched_description = $enriched
            """
            
            run_query(self.driver, update_query, {
                'listing_id': prop['listing_id'],
                'enriched': enriched
            })
            count += 1
        
        print(f"  {count} Property descriptions enriched with Wikipedia context")
    
    def run_sample_queries(self):
        """Run sample queries to demonstrate the enhanced graph"""
        from demos import QueryDemonstrator
        
        demonstrator = QueryDemonstrator(self.driver)
        demonstrator.run_phase4_queries()
    
    def close(self):
        """Close database connection"""
        close_neo4j_driver(self.driver)