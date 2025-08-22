"""Neighborhood loader with Wikipedia correlation and enrichment"""
import json
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime
from collections import defaultdict
import re

from src.loaders.base import BaseLoader
from src.loaders.config import GraphLoadingConfig
from src.models.neighborhood import (
    Neighborhood, NeighborhoodCharacteristics, NeighborhoodDemographics,
    WikipediaMetadata, GraphMetadata, NeighborhoodCorrelation,
    NeighborhoodLoadResult, NeighborhoodStats
)
from src.models.wikipedia import WikipediaArticle
from src.utils.geographic import GeographicUtils


class NeighborhoodLoader(BaseLoader):
    """Load neighborhoods and correlate with Wikipedia knowledge"""
    
    def __init__(self, geographic_index: Optional[Dict] = None):
        """Initialize neighborhood loader"""
        super().__init__()
        
        # Load batch size configuration
        self.batch_config = GraphLoadingConfig.from_yaml()
        
        self.geographic_index = geographic_index or {}
        self.neighborhoods: List[Neighborhood] = []
        self.correlations: List[NeighborhoodCorrelation] = []
        self.load_result = NeighborhoodLoadResult()
        
        # Paths to neighborhood JSON files
        self.sf_path = self.base_path / 'real_estate_data' / 'neighborhoods_sf.json'
        self.pc_path = self.base_path / 'real_estate_data' / 'neighborhoods_pc.json'
        
    def load(self) -> NeighborhoodLoadResult:
        """Main loading method"""
        self.logger.info("=" * 60)
        self.logger.info("NEIGHBORHOOD LOADING AND CORRELATION")
        self.logger.info("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # Load neighborhood data from JSON
            self.neighborhoods = self._load_neighborhoods_from_json()
            self.load_result.neighborhoods_loaded = len(self.neighborhoods)
            
            # Create constraints and indexes
            self._create_constraints_and_indexes()
            
            # Create neighborhood nodes
            nodes_created = self._create_neighborhood_nodes()
            self.load_result.nodes_created = nodes_created
            
            # Create geographic relationships
            self._create_geographic_relationships()
            
            # Correlate with Wikipedia articles
            self._correlate_wikipedia_articles()
            
            # Note: Wikipedia->Property relationships are created in PropertyLoader after properties exist
            
            # Enrich neighborhoods with Wikipedia data
            self._enrich_neighborhoods()
            
            # Verify the integration
            stats = self._verify_integration()
            
            # Calculate duration
            self.load_result.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            self.logger.info("=" * 60)
            self.logger.info("✅ NEIGHBORHOOD LOADING COMPLETE")
            self.logger.info(f"  Neighborhoods loaded: {self.load_result.neighborhoods_loaded}")
            self.logger.info(f"  Nodes created: {self.load_result.nodes_created}")
            self.logger.info(f"  Wikipedia correlations: {self.load_result.wikipedia_correlations}")
            self.logger.info(f"  Average knowledge score: {self.load_result.avg_knowledge_score:.2f}")
            self.logger.info(f"  Duration: {self.load_result.duration_seconds:.1f}s")
            self.logger.info("=" * 60)
            
            return self.load_result
            
        except Exception as e:
            self.logger.error(f"Failed to load neighborhoods: {e}")
            self.load_result.add_error(str(e))
            import traceback
            traceback.print_exc()
            return self.load_result
    
    def _load_neighborhoods_from_json(self) -> List[Neighborhood]:
        """Load and parse neighborhood data from JSON files"""
        self.logger.info("Loading neighborhood data from JSON files...")
        
        neighborhoods = []
        
        for city_name, path in [('San Francisco', self.sf_path), ('Park City', self.pc_path)]:
            if not path.exists():
                self.load_result.add_warning(f"Neighborhood file not found: {path}")
                continue
            
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                
                for item in data:
                    try:
                        # Parse graph metadata if present
                        if 'graph_metadata' in item and item['graph_metadata']:
                            graph_meta_data = item['graph_metadata']
                            
                            # Parse primary Wikipedia article
                            primary_wiki = None
                            if 'primary_wiki_article' in graph_meta_data:
                                primary_data = graph_meta_data['primary_wiki_article']
                                if primary_data and primary_data.get('page_id'):
                                    primary_wiki = WikipediaMetadata(
                                        page_id=primary_data['page_id'],
                                        title=primary_data.get('title', ''),
                                        url=primary_data.get('url'),
                                        confidence=primary_data.get('confidence', 0.5),
                                        relationship='primary'
                                    )
                            
                            # Parse related Wikipedia articles
                            related_wiki = []
                            for related in graph_meta_data.get('related_wiki_articles', []):
                                if related and related.get('page_id'):
                                    related_wiki.append(WikipediaMetadata(
                                        page_id=related['page_id'],
                                        title=related.get('title', ''),
                                        url=related.get('url'),
                                        confidence=related.get('confidence', 0.5),
                                        relationship=related.get('relationship', 'related')
                                    ))
                            
                            # Create GraphMetadata
                            graph_metadata = GraphMetadata(
                                primary_wiki_article=primary_wiki,
                                related_wiki_articles=related_wiki,
                                parent_geography=graph_meta_data.get('parent_geography'),
                                generated_by=graph_meta_data.get('generated_by'),
                                source=graph_meta_data.get('source')
                            )
                        else:
                            graph_metadata = None
                        
                        # Parse characteristics if present
                        characteristics = None
                        if 'characteristics' in item and item['characteristics']:
                            characteristics = NeighborhoodCharacteristics(**item['characteristics'])
                        
                        # Parse demographics if present
                        demographics = None
                        if 'demographics' in item and item['demographics']:
                            demographics = NeighborhoodDemographics(**item['demographics'])
                        
                        # Create Neighborhood model
                        neighborhood = Neighborhood(
                            neighborhood_id=item['neighborhood_id'],
                            name=item['name'],
                            city=item.get('city', city_name),
                            county=item['county'],
                            state=item['state'],
                            coordinates=item.get('coordinates'),
                            description=item.get('description'),
                            characteristics=characteristics,
                            amenities=item.get('amenities', []),
                            lifestyle_tags=item.get('lifestyle_tags', []),
                            median_home_price=item.get('median_home_price'),
                            price_trend=item.get('price_trend'),
                            demographics=demographics,
                            graph_metadata=graph_metadata
                        )
                        
                        # Calculate initial knowledge score
                        neighborhood.calculate_knowledge_score()
                        
                        # Count Wikipedia articles
                        if graph_metadata:
                            neighborhood.wikipedia_count = len(graph_metadata.get_all_wiki_page_ids())
                        
                        neighborhoods.append(neighborhood)
                        
                    except Exception as e:
                        self.logger.warning(f"Failed to parse neighborhood {item.get('neighborhood_id')}: {e}")
                        self.load_result.add_warning(f"Failed to parse neighborhood: {e}")
                
                self.logger.info(f"  Loaded {len([n for n in neighborhoods if n.city == city_name])} {city_name} neighborhoods")
                
            except Exception as e:
                self.logger.error(f"Error loading {path}: {e}")
                self.load_result.add_error(f"Error loading {path.name}: {e}")
        
        self.logger.info(f"Total neighborhoods loaded: {len(neighborhoods)}")
        return neighborhoods
    
    def _create_constraints_and_indexes(self):
        """Create neighborhood-specific constraints and indexes"""
        self.logger.info("Creating neighborhood constraints and indexes...")
        
        constraints = [
            ("Neighborhood.neighborhood_id",
             "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Neighborhood) REQUIRE n.neighborhood_id IS UNIQUE"),
        ]
        
        for name, query in constraints:
            self.create_constraint(name, query)
        
        indexes = [
            ("Neighborhood.city",
             "CREATE INDEX IF NOT EXISTS FOR (n:Neighborhood) ON (n.city)"),
            ("Neighborhood.county",
             "CREATE INDEX IF NOT EXISTS FOR (n:Neighborhood) ON (n.county)"),
            ("Neighborhood.knowledge_score",
             "CREATE INDEX IF NOT EXISTS FOR (n:Neighborhood) ON (n.knowledge_score)"),
        ]
        
        for name, query in indexes:
            self.create_index(name, query)
    
    def _create_neighborhood_nodes(self) -> int:
        """Create neighborhood nodes with ALL available data"""
        self.logger.info(f"Creating {len(self.neighborhoods)} neighborhood nodes with complete data...")
        
        batch_data = []
        for neighborhood in self.neighborhoods:
            # Prepare comprehensive node data
            node_data = {
                'neighborhood_id': neighborhood.neighborhood_id,
                'name': neighborhood.name,
                'city': neighborhood.city,
                'county': neighborhood.county,
                'state': neighborhood.state,
                
                # Rich description (previously missing!)
                'description': neighborhood.description or '',
                
                # Lifestyle and character
                'lifestyle_tags': neighborhood.lifestyle_tags,
                'amenities': neighborhood.amenities,
                
                # All characteristics scores
                'walkability_score': neighborhood.characteristics.walkability_score if neighborhood.characteristics else None,
                'transit_score': neighborhood.characteristics.transit_score if neighborhood.characteristics else None,
                'school_rating': neighborhood.characteristics.school_rating if neighborhood.characteristics else None,
                'safety_rating': neighborhood.characteristics.safety_rating if neighborhood.characteristics else None,
                'nightlife_score': neighborhood.characteristics.nightlife_score if neighborhood.characteristics else None,
                'family_friendly_score': neighborhood.characteristics.family_friendly_score if neighborhood.characteristics else None,
                
                # Demographics
                'vibe': neighborhood.demographics.vibe if neighborhood.demographics else '',
                'primary_age_group': neighborhood.demographics.primary_age_group if neighborhood.demographics else '',
                'population': neighborhood.demographics.population if neighborhood.demographics else None,
                'median_household_income': neighborhood.demographics.median_household_income if neighborhood.demographics else None,
                
                # Market data
                'median_home_price': neighborhood.median_home_price,
                'price_trend': neighborhood.price_trend,
                
                # Calculated scores
                'knowledge_score': neighborhood.knowledge_score,
                'wikipedia_count': neighborhood.wikipedia_count,
                
                # Coordinates for spatial queries
                'latitude': neighborhood.coordinates.get('latitude') if neighborhood.coordinates else None,
                'longitude': neighborhood.coordinates.get('longitude') if neighborhood.coordinates else None
            }
            
            batch_data.append(node_data)
        
        query = """
        WITH item
        MERGE (n:Neighborhood:Location {neighborhood_id: item.neighborhood_id})
        SET n += item,  // Set all properties at once
            n.last_updated = datetime()
        """
        
        created = self.batch_execute(query, batch_data, batch_size=self.batch_config.neighborhood_batch_size)
        self.logger.info(f"Created {created} neighborhood nodes")
        return created
    
    def _create_geographic_relationships(self):
        """Create relationships between neighborhoods and geographic entities"""
        self.logger.info("Creating geographic relationships...")
        
        # Prepare batches for relationships
        city_batch = []
        county_batch = []
        
        for neighborhood in self.neighborhoods:
            # Get state code
            state_code = GeographicUtils.get_state_code(neighborhood.state)
            if not state_code:
                continue
            
            # City relationship
            city_id = GeographicUtils.normalize_city_id(neighborhood.city, state_code)
            city_batch.append({
                'neighborhood_id': neighborhood.neighborhood_id,
                'city_id': city_id
            })
            
            # County relationship
            county_id = GeographicUtils.normalize_county_id(neighborhood.county, state_code)
            county_batch.append({
                'neighborhood_id': neighborhood.neighborhood_id,
                'county_id': county_id
            })
        
        # Create city relationships
        if city_batch:
            query = """
            WITH item
            MATCH (n:Neighborhood {neighborhood_id: item.neighborhood_id})
            MATCH (c:City {city_id: item.city_id})
            MERGE (n)-[:IN_CITY]->(c)
            """
            count = self.batch_execute(query, city_batch, batch_size=self.batch_config.default_batch_size)
            self.load_result.city_relationships = count
            self.logger.info(f"  Created {count} neighborhood-city relationships")
        
        # Create county relationships
        if county_batch:
            query = """
            WITH item
            MATCH (n:Neighborhood {neighborhood_id: item.neighborhood_id})
            MATCH (c:County {county_id: item.county_id})
            MERGE (n)-[:IN_COUNTY]->(c)
            """
            count = self.batch_execute(query, county_batch, batch_size=self.batch_config.default_batch_size)
            self.load_result.county_relationships = count
            self.logger.info(f"  Created {count} neighborhood-county relationships")
    
    def _correlate_wikipedia_articles(self):
        """Correlate neighborhoods with Wikipedia articles using multiple methods"""
        self.logger.info("Correlating neighborhoods with Wikipedia articles...")
        
        # Method 1: Direct page_id matching from metadata
        direct_count = self._correlate_direct_wikipedia()
        self.load_result.direct_correlations = direct_count
        
        # Method 2: Geographic proximity matching
        geographic_count = self._correlate_geographic_wikipedia()
        self.load_result.geographic_correlations = geographic_count
        
        # Method 3: Name matching
        name_count = self._correlate_name_based_wikipedia()
        self.load_result.name_match_correlations = name_count
        
        total = direct_count + geographic_count + name_count
        self.load_result.wikipedia_correlations = total
        
        self.logger.info(f"  Total Wikipedia correlations: {total}")
        self.logger.info(f"    - Direct (from metadata): {direct_count}")
        self.logger.info(f"    - Geographic proximity: {geographic_count}")
        self.logger.info(f"    - Name matching: {name_count}")
    
    def _correlate_direct_wikipedia(self) -> int:
        """Correlate using direct page_id from metadata"""
        batch_data = []
        
        for neighborhood in self.neighborhoods:
            if not neighborhood.graph_metadata:
                continue
            
            # Primary Wikipedia article
            if neighborhood.graph_metadata.primary_wiki_article:
                wiki = neighborhood.graph_metadata.primary_wiki_article
                batch_data.append({
                    'neighborhood_id': neighborhood.neighborhood_id,
                    'page_id': wiki.page_id,
                    'confidence': wiki.confidence,
                    'relationship_type': 'primary'
                })
                
                self.correlations.append(NeighborhoodCorrelation(
                    neighborhood_id=neighborhood.neighborhood_id,
                    page_id=wiki.page_id,
                    correlation_method='direct',
                    confidence=wiki.confidence,
                    relationship_type='primary'
                ))
            
            # Related Wikipedia articles
            for wiki in neighborhood.graph_metadata.related_wiki_articles:
                batch_data.append({
                    'neighborhood_id': neighborhood.neighborhood_id,
                    'page_id': wiki.page_id,
                    'confidence': wiki.confidence,
                    'relationship_type': wiki.relationship
                })
                
                self.correlations.append(NeighborhoodCorrelation(
                    neighborhood_id=neighborhood.neighborhood_id,
                    page_id=wiki.page_id,
                    correlation_method='direct',
                    confidence=wiki.confidence,
                    relationship_type=wiki.relationship
                ))
        
        if batch_data:
            query = """
            WITH item
            MATCH (n:Neighborhood {neighborhood_id: item.neighborhood_id})
            MATCH (w:WikipediaArticle {page_id: item.page_id})
            MERGE (w)-[:DESCRIBES {
                confidence: item.confidence,
                relationship_type: item.relationship_type,
                correlation_method: 'direct'
            }]->(n)
            """
            count = self.batch_execute(query, batch_data, batch_size=self.batch_config.default_batch_size)
            return count
        
        return 0
    
    def _correlate_geographic_wikipedia(self) -> int:
        """Correlate Wikipedia articles based on geographic proximity"""
        query = """
        MATCH (n:Neighborhood)
        WHERE NOT EXISTS((n)<-[:DESCRIBES]-(:WikipediaArticle))
        MATCH (w:WikipediaArticle)
        WHERE w.best_city = n.city
        AND w.best_state = n.state
        AND w.location_type IN ['neighborhood', 'district', 'area', 'community']
        WITH n, w, w.overall_confidence * 0.7 as correlation_confidence
        WHERE correlation_confidence > 0.3
        CREATE (w)-[:DESCRIBES {
            confidence: correlation_confidence,
            relationship_type: 'geographic',
            correlation_method: 'geographic'
        }]->(n)
        RETURN count(*) as count
        """
        
        result = self.execute_query(query)
        return result[0]['count'] if result else 0
    
    def _correlate_name_based_wikipedia(self) -> int:
        """Correlate Wikipedia articles based on name similarity"""
        query = """
        MATCH (n:Neighborhood)
        WHERE NOT EXISTS((n)<-[:DESCRIBES]-(:WikipediaArticle))
        MATCH (w:WikipediaArticle)
        WHERE w.best_city = n.city
        AND (
            toLower(w.title) CONTAINS toLower(n.name)
            OR toLower(n.name) CONTAINS toLower(w.title)
        )
        WITH n, w, 
             CASE 
                WHEN toLower(w.title) = toLower(n.name) THEN 0.9
                WHEN toLower(w.title) CONTAINS toLower(n.name) THEN 0.7
                ELSE 0.5
             END * w.overall_confidence as correlation_confidence
        WHERE correlation_confidence > 0.3
        CREATE (w)-[:DESCRIBES {
            confidence: correlation_confidence,
            relationship_type: 'name_match',
            correlation_method: 'name_match'
        }]->(n)
        RETURN count(*) as count
        """
        
        result = self.execute_query(query)
        return result[0]['count'] if result else 0
    
    def _create_wikipedia_property_relationships(self) -> None:
        """Create direct RELEVANT_TO relationships between Wikipedia articles and properties"""
        self.logger.info("Creating Wikipedia→Property relationships...")
        
        total_created = 0
        
        # For each neighborhood with Wikipedia metadata
        for neighborhood in self.neighborhoods:
            if not neighborhood.graph_metadata:
                continue
            
            # Get all Wikipedia page IDs for this neighborhood
            wiki_page_ids = []
            
            # Add primary Wikipedia article
            if neighborhood.graph_metadata.primary_wiki_article:
                wiki_page_ids.append({
                    'page_id': neighborhood.graph_metadata.primary_wiki_article.page_id,
                    'confidence': neighborhood.graph_metadata.primary_wiki_article.confidence,
                    'rel_type': 'primary'
                })
            
            # Add related Wikipedia articles
            for wiki in neighborhood.graph_metadata.related_wiki_articles:
                wiki_page_ids.append({
                    'page_id': wiki.page_id,
                    'confidence': wiki.confidence,
                    'rel_type': wiki.relationship
                })
            
            # Create relationships for each Wikipedia article to all properties in neighborhood
            for wiki_info in wiki_page_ids:
                query = """
                MATCH (w:WikipediaArticle {page_id: $page_id})
                MATCH (p:Property {neighborhood_id: $neighborhood_id})
                MERGE (w)-[r:RELEVANT_TO]->(p)
                SET r.confidence = $confidence,
                    r.relationship_type = $rel_type,
                    r.neighborhood_context = true,
                    r.created_at = datetime()
                RETURN count(r) as created
                """
                
                result = self.execute_query(query, {
                    'page_id': wiki_info['page_id'],
                    'neighborhood_id': neighborhood.neighborhood_id,
                    'confidence': wiki_info['confidence'],
                    'rel_type': wiki_info['rel_type']
                })
                
                if result:
                    created = result[0]['created']
                    total_created += created
        
        self.load_result.wikipedia_property_relationships = total_created
        self.logger.info(f"  Created {total_created} Wikipedia→Property relationships")
    
    def _enrich_neighborhoods(self):
        """Enrich neighborhoods with aggregated Wikipedia data"""
        self.logger.info("Enriching neighborhoods with Wikipedia knowledge...")
        
        # Query to aggregate topics from Wikipedia articles
        query = """
        MATCH (n:Neighborhood)<-[:DESCRIBES]-(w:WikipediaArticle)
        WHERE size(w.key_topics) > 0
        WITH n, collect(DISTINCT w.key_topics) as all_topics,
             avg(w.overall_confidence) as avg_confidence,
             count(w) as wiki_count
        UNWIND all_topics as topic_list
        UNWIND topic_list as topic
        WITH n, collect(DISTINCT topic) as unique_topics, avg_confidence, wiki_count
        SET n.aggregated_topics = unique_topics,
            n.avg_wiki_confidence = avg_confidence,
            n.enriched_wiki_count = wiki_count,
            n.enriched = true
        RETURN count(n) as enriched_count, avg(size(unique_topics)) as avg_topics
        """
        
        result = self.execute_query(query)
        if result:
            self.load_result.neighborhoods_enriched = result[0]['enriched_count']
            avg_topics = result[0]['avg_topics'] or 0
            self.load_result.total_topics_extracted = int(avg_topics * self.load_result.neighborhoods_enriched)
            self.logger.info(f"  Enriched {self.load_result.neighborhoods_enriched} neighborhoods")
            self.logger.info(f"  Average topics per neighborhood: {avg_topics:.1f}")
        
        # Update knowledge scores based on enrichment
        query = """
        MATCH (n:Neighborhood)
        OPTIONAL MATCH (n)<-[r:DESCRIBES]-(w:WikipediaArticle)
        WITH n, count(w) as wiki_count, avg(r.confidence) as avg_confidence
        SET n.final_knowledge_score = CASE
            WHEN wiki_count = 0 THEN n.knowledge_score
            WHEN wiki_count = 1 THEN n.knowledge_score * 0.5 + avg_confidence * 0.5
            ELSE n.knowledge_score * 0.3 + avg_confidence * 0.7
        END
        RETURN avg(n.final_knowledge_score) as avg_score
        """
        
        result = self.execute_query(query)
        if result:
            self.load_result.avg_knowledge_score = result[0]['avg_score'] or 0.0
    
    def _verify_integration(self) -> NeighborhoodStats:
        """Verify neighborhood integration"""
        self.logger.info("Verifying neighborhood integration...")
        
        stats = NeighborhoodStats()
        
        # Count neighborhoods
        stats.total_neighborhoods = self.count_nodes("Neighborhood")
        
        # Count neighborhoods with Wikipedia
        query = "MATCH (n:Neighborhood)<-[:DESCRIBES]-() RETURN count(DISTINCT n) as count"
        result = self.execute_query(query)
        stats.neighborhoods_with_wikipedia = result[0]['count'] if result else 0
        
        # Count neighborhoods with characteristics
        query = "MATCH (n:Neighborhood) WHERE n.walkability_score IS NOT NULL RETURN count(n) as count"
        result = self.execute_query(query)
        stats.neighborhoods_with_characteristics = result[0]['count'] if result else 0
        
        # Geographic distribution
        query = "MATCH (n:Neighborhood) RETURN count(DISTINCT n.city) as cities, count(DISTINCT n.county) as counties"
        result = self.execute_query(query)
        if result:
            stats.cities_represented = result[0]['cities']
            stats.counties_represented = result[0]['counties']
        
        # Wikipedia coverage
        query = """
        MATCH (n:Neighborhood)
        OPTIONAL MATCH (n)<-[:DESCRIBES]-(w:WikipediaArticle)
        RETURN avg(n.knowledge_score) as avg_score,
               count(CASE WHEN n.knowledge_score > 0.7 THEN 1 END) as high_knowledge,
               avg(n.wikipedia_count) as avg_wiki_articles
        """
        result = self.execute_query(query)
        if result:
            stats.avg_knowledge_score = result[0]['avg_score'] or 0.0
            stats.high_knowledge_neighborhoods = result[0]['high_knowledge'] or 0
            stats.avg_wikipedia_articles_per_neighborhood = result[0]['avg_wiki_articles'] or 0.0
        
        self.logger.info(f"  Total neighborhoods: {stats.total_neighborhoods}")
        self.logger.info(f"  With Wikipedia: {stats.neighborhoods_with_wikipedia}")
        self.logger.info(f"  With characteristics: {stats.neighborhoods_with_characteristics}")
        self.logger.info(f"  Average knowledge score: {stats.avg_knowledge_score:.2f}")
        
        return stats
    
    def get_neighborhoods(self) -> List[Neighborhood]:
        """Get loaded neighborhoods"""
        return self.neighborhoods
    
    def get_load_result(self) -> NeighborhoodLoadResult:
        """Get detailed load result"""
        return self.load_result