"""Neighborhood loader with constructor injection"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from src.core.query_executor import QueryExecutor
from src.core.config import PropertyConfig
from src.data_sources import PropertyFileDataSource
from src.models.neighborhood import Neighborhood, NeighborhoodLoadResult


class NeighborhoodLoader:
    """Load neighborhoods with injected dependencies"""
    
    def __init__(
        self,
        query_executor: QueryExecutor,
        config: PropertyConfig,
        data_source: PropertyFileDataSource
    ):
        """
        Initialize neighborhood loader with dependencies
        
        Args:
            query_executor: Database query executor
            config: Property configuration
            data_source: Property data source
        """
        self.query_executor = query_executor
        self.config = config
        self.data_source = data_source
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Load result tracking
        self.load_result = NeighborhoodLoadResult()
    
    def load(self) -> NeighborhoodLoadResult:
        """
        Main loading method
        
        Returns:
            NeighborhoodLoadResult with statistics
        """
        self.logger.info("=" * 60)
        self.logger.info("NEIGHBORHOOD LOADING AND CORRELATION")
        self.logger.info("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # Create constraints and indexes
            self._create_constraints_and_indexes()
            
            # Load neighborhoods from data source
            neighborhoods = self._load_neighborhoods()
            
            # Create neighborhood nodes
            nodes_created = self._create_neighborhood_nodes(neighborhoods)
            self.load_result.neighborhoods_loaded = nodes_created
            
            # Create geographic relationships
            self._create_geographic_relationships()
            
            # Create Wikipedia correlations if available
            self._create_wikipedia_correlations(neighborhoods)
            
            # Calculate duration
            self.load_result.duration_seconds = (datetime.now() - start_time).total_seconds()
            self.load_result.success = True
            
            self.logger.info("=" * 60)
            self.logger.info("✅ NEIGHBORHOOD LOADING COMPLETE")
            self.logger.info(f"  Neighborhoods loaded: {self.load_result.neighborhoods_loaded}")
            self.logger.info(f"  Wikipedia correlations: {self.load_result.wikipedia_correlations}")
            self.logger.info(f"  Avg knowledge score: {self.load_result.avg_knowledge_score:.2f}")
            self.logger.info(f"  Duration: {self.load_result.duration_seconds:.1f}s")
            self.logger.info("=" * 60)
            
            return self.load_result
            
        except Exception as e:
            self.logger.error(f"Failed to load neighborhoods: {e}")
            self.load_result.add_error(str(e))
            self.load_result.success = False
            import traceback
            traceback.print_exc()
            return self.load_result
    
    def _create_constraints_and_indexes(self) -> None:
        """Create neighborhood-specific constraints and indexes"""
        self.logger.info("Creating neighborhood constraints and indexes...")
        
        # Constraints
        constraints = [
            ("Neighborhood.neighborhood_id",
             "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Neighborhood) REQUIRE n.neighborhood_id IS UNIQUE"),
        ]
        
        for name, query in constraints:
            self.query_executor.create_constraint(name, query)
        
        # Indexes
        indexes = [
            ("Neighborhood.name",
             "CREATE INDEX IF NOT EXISTS FOR (n:Neighborhood) ON (n.name)"),
            ("Neighborhood.city",
             "CREATE INDEX IF NOT EXISTS FOR (n:Neighborhood) ON (n.city)"),
            ("Neighborhood.median_price",
             "CREATE INDEX IF NOT EXISTS FOR (n:Neighborhood) ON (n.median_price)"),
        ]
        
        for name, query in indexes:
            self.query_executor.create_index(name, query)
    
    def _load_neighborhoods(self) -> List[Neighborhood]:
        """Load neighborhoods from data source"""
        self.logger.info("Loading neighborhood data...")
        
        neighborhoods = []
        raw_neighborhoods = self.data_source.load_neighborhoods()
        
        for item in raw_neighborhoods:
            try:
                # Validate with Pydantic
                neighborhood = Neighborhood(**item)
                neighborhoods.append(neighborhood)
                
            except Exception as e:
                self.logger.warning(f"Failed to parse neighborhood {item.get('neighborhood_id', 'unknown')}: {e}")
                self.load_result.add_warning(f"Failed to parse neighborhood: {e}")
        
        self.logger.info(f"  Loaded {len(neighborhoods)} neighborhoods")
        return neighborhoods
    
    def _create_neighborhood_nodes(self, neighborhoods: List[Neighborhood]) -> int:
        """Create neighborhood nodes in database"""
        self.logger.info(f"Creating {len(neighborhoods)} neighborhood nodes...")
        
        batch_data = []
        for neighborhood in neighborhoods:
            # Extract location data
            location = neighborhood.coordinates or {}
            
            # Extract demographics data
            demographics = neighborhood.demographics.dict() if neighborhood.demographics else {}
            
            # Extract characteristics if available
            characteristics = neighborhood.characteristics
            
            batch_data.append({
                'neighborhood_id': neighborhood.neighborhood_id,
                'name': neighborhood.name,
                'city': neighborhood.city,
                'state': neighborhood.state,
                'county': neighborhood.county,
                'description': neighborhood.description or '',
                'population': demographics.get('population'),
                'median_household_income': demographics.get('median_household_income'),
                'latitude': location.get('latitude'),
                'longitude': location.get('longitude'),
                'median_price': neighborhood.median_home_price,
                'price_trend': neighborhood.price_trend,
                'walkability_score': characteristics.walkability_score if characteristics else None,
                'transit_score': characteristics.transit_score if characteristics else None,
                'school_rating': characteristics.school_rating if characteristics else None,
                'safety_rating': characteristics.safety_rating if characteristics else None,
                'nightlife_score': characteristics.nightlife_score if characteristics else None,
                'family_friendly_score': characteristics.family_friendly_score if characteristics else None,
                'amenities': neighborhood.amenities or [],
                'lifestyle_tags': neighborhood.lifestyle_tags or [],
                'vibe': demographics.get('vibe', '') if demographics else '',
                'primary_age_group': demographics.get('primary_age_group', '') if demographics else ''
            })
        
        query = """
        WITH item
        MERGE (n:Neighborhood:Location {neighborhood_id: item.neighborhood_id})
        SET n.name = item.name,
            n.city = item.city,
            n.state = item.state,
            n.county = item.county,
            n.description = item.description,
            n.population = item.population,
            n.median_household_income = item.median_household_income,
            n.latitude = item.latitude,
            n.longitude = item.longitude,
            n.median_price = item.median_price,
            n.price_trend = item.price_trend,
            n.walkability_score = item.walkability_score,
            n.transit_score = item.transit_score,
            n.school_rating = item.school_rating,
            n.safety_rating = item.safety_rating,
            n.nightlife_score = item.nightlife_score,
            n.family_friendly_score = item.family_friendly_score,
            n.amenities = item.amenities,
            n.lifestyle_tags = item.lifestyle_tags,
            n.vibe = item.vibe,
            n.primary_age_group = item.primary_age_group,
            n.created_at = datetime()
        """
        
        created = self.query_executor.batch_execute(query, batch_data)
        self.logger.info(f"  Created {created} neighborhood nodes")
        return created
    
    def _create_geographic_relationships(self) -> None:
        """Create relationships to cities and counties"""
        self.logger.info("Creating geographic relationships...")
        
        # Connect to cities
        query = """
        MATCH (n:Neighborhood)
        WHERE n.city IS NOT NULL
        WITH n, toLower(replace(n.city, ' ', '_')) as city_id
        MATCH (c:City)
        WHERE c.city_id = city_id OR toLower(c.city_name) = toLower(n.city)
        MERGE (n)-[r:IN_CITY]->(c)
        SET r.created_at = datetime()
        RETURN count(r) as count
        """
        result = self.query_executor.execute_write(query)
        city_count = result[0]['count'] if result else 0
        self.logger.info(f"  Created {city_count} neighborhood->city relationships")
        
        # Connect to counties
        query = """
        MATCH (n:Neighborhood)
        WHERE n.county IS NOT NULL
        WITH n,
             CASE
                WHEN n.county CONTAINS 'County' THEN toLower(replace(n.county, ' ', '_'))
                ELSE toLower(replace(n.county + ' County', ' ', '_'))
             END as county_id
        MATCH (c:County)
        WHERE c.county_id = county_id
        MERGE (n)-[r:IN_COUNTY]->(c)
        SET r.created_at = datetime()
        RETURN count(r) as count
        """
        result = self.query_executor.execute_write(query)
        county_count = result[0]['count'] if result else 0
        self.logger.info(f"  Created {county_count} neighborhood->county relationships")
    
    def _create_wikipedia_correlations(self, neighborhoods: List[Neighborhood]) -> None:
        """Create correlations between neighborhoods and Wikipedia articles"""
        self.logger.info("Creating Wikipedia correlations...")
        
        total_correlations = 0
        knowledge_scores = []
        
        for neighborhood in neighborhoods:
            if not neighborhood.graph_metadata:
                continue
            
            graph_meta = neighborhood.graph_metadata
            
            # Process primary Wikipedia article
            if graph_meta.primary_wiki_article:
                wiki = graph_meta.primary_wiki_article
                self._create_wikipedia_relationship(
                    neighborhood.neighborhood_id,
                    wiki.page_id,
                    wiki.confidence,
                    'primary'
                )
                total_correlations += 1
            
            # Process related Wikipedia articles
            for wiki in graph_meta.related_wiki_articles or []:
                self._create_wikipedia_relationship(
                    neighborhood.neighborhood_id,
                    wiki.page_id,
                    wiki.confidence,
                    wiki.relationship or 'related'
                )
                total_correlations += 1
            
            # Track knowledge score from neighborhood level
            knowledge_scores.append(neighborhood.knowledge_score)
        
        self.load_result.wikipedia_correlations = total_correlations
        if knowledge_scores:
            self.load_result.avg_knowledge_score = sum(knowledge_scores) / len(knowledge_scores)
        
        self.logger.info(f"  Created {total_correlations} Wikipedia correlations")
    
    def _create_wikipedia_relationship(self, neighborhood_id: str, page_id: int, confidence: float, rel_type: str) -> None:
        """Create a single Wikipedia DESCRIBES relationship"""
        query = """
        MATCH (n:Neighborhood {neighborhood_id: $neighborhood_id})
        MATCH (w:WikipediaArticle {page_id: $page_id})
        MERGE (w)-[r:DESCRIBES]->(n)
        SET r.confidence = $confidence,
            r.relationship_type = $rel_type,
            r.created_at = datetime()
        """
        
        self.query_executor.execute_write(query, {
            'neighborhood_id': neighborhood_id,
            'page_id': page_id,
            'confidence': confidence,
            'rel_type': rel_type
        })