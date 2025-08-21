"""Wikipedia knowledge loader with Pydantic models and type safety"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

from src.loaders.base import BaseLoader
from src.models.wikipedia import (
    WikipediaArticle, WikipediaRelationship, 
    WikipediaStats, WikipediaLoadResult
)
from src.utils.geographic import GeographicUtils


class WikipediaKnowledgeLoader(BaseLoader):
    """Load Wikipedia articles with summaries and connect to geographic hierarchy"""
    
    def __init__(self, db_path: Optional[Path] = None, geographic_index: Optional[Dict] = None):
        """Initialize Wikipedia loader"""
        super().__init__()
        
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = self.base_path / 'data' / 'wikipedia' / 'wikipedia.db'
        
        self.geographic_index = geographic_index or {}
        self.articles: List[WikipediaArticle] = []
        self.relationships: List[WikipediaRelationship] = []
        self.load_result = WikipediaLoadResult()
        
    def load(self) -> WikipediaLoadResult:
        """Main loading method"""
        self.logger.info("=" * 60)
        self.logger.info("WIKIPEDIA KNOWLEDGE LAYER INTEGRATION")
        self.logger.info("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # Validate database exists
            if not self.db_path.exists():
                raise FileNotFoundError(f"Wikipedia database not found: {self.db_path}")
            
            # Create constraints and indexes
            self._create_constraints_and_indexes()
            
            # Load articles from database
            self.articles = self._load_articles_from_db()
            self.load_result.articles_loaded = len(self.articles)
            
            # Create Wikipedia nodes
            nodes_created = self._create_wikipedia_nodes()
            self.load_result.nodes_created = nodes_created
            
            # Count extracted topics
            topic_set = set()
            for article in self.articles:
                topic_set.update(article.key_topics)
            self.load_result.topics_extracted = len(topic_set)
            
            # Create geographic relationships
            self._create_geographic_relationships()
            
            # Verify integration
            stats = self._verify_integration()
            
            # Calculate duration
            self.load_result.duration_seconds = (datetime.now() - start_time).total_seconds()
            
            self.logger.info("=" * 60)
            self.logger.info("✅ WIKIPEDIA KNOWLEDGE LAYER COMPLETE")
            self.logger.info(f"  Articles loaded: {self.load_result.articles_loaded}")
            self.logger.info(f"  Nodes created: {self.load_result.nodes_created}")
            self.logger.info(f"  Relationships: {sum(self.load_result.relationships_created.values())}")
            self.logger.info(f"  Duration: {self.load_result.duration_seconds:.1f}s")
            self.logger.info("=" * 60)
            
            return self.load_result
            
        except Exception as e:
            self.logger.error(f"Failed to load Wikipedia knowledge: {e}")
            self.load_result.add_error(str(e))
            import traceback
            traceback.print_exc()
            return self.load_result
    
    def _create_constraints_and_indexes(self) -> None:
        """Create Wikipedia-specific constraints and indexes"""
        self.logger.info("Creating Wikipedia constraints and indexes...")
        
        constraints = [
            ("WikipediaArticle.page_id",
             "CREATE CONSTRAINT IF NOT EXISTS FOR (w:WikipediaArticle) REQUIRE w.page_id IS UNIQUE"),
        ]
        
        for name, query in constraints:
            self.create_constraint(name, query)
        
        indexes = [
            ("WikipediaArticle.confidence",
             "CREATE INDEX IF NOT EXISTS FOR (w:WikipediaArticle) ON (w.overall_confidence)"),
            ("WikipediaArticle.state",
             "CREATE INDEX IF NOT EXISTS FOR (w:WikipediaArticle) ON (w.best_state)"),
            ("WikipediaArticle.city",
             "CREATE INDEX IF NOT EXISTS FOR (w:WikipediaArticle) ON (w.best_city)"),
            ("WikipediaArticle.county",
             "CREATE INDEX IF NOT EXISTS FOR (w:WikipediaArticle) ON (w.best_county)"),
        ]
        
        for name, query in indexes:
            self.create_index(name, query)
    
    def _load_articles_from_db(self) -> List[WikipediaArticle]:
        """Load Wikipedia articles from SQLite database"""
        self.logger.info(f"Loading articles from {self.db_path}")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        
        try:
            query = """
            SELECT 
                ps.page_id,
                ps.title,
                ps.short_summary,
                ps.long_summary,
                ps.key_topics,
                ps.best_city,
                ps.best_county,
                ps.best_state,
                ps.overall_confidence,
                a.url,
                a.latitude,
                a.longitude,
                l.location_type
            FROM page_summaries ps
            LEFT JOIN articles a ON ps.page_id = a.pageid
            LEFT JOIN locations l ON a.location_id = l.location_id
            WHERE ps.overall_confidence > 0.3
            ORDER BY ps.overall_confidence DESC
            """
            
            cursor = conn.cursor()
            cursor.execute(query)
            
            articles = []
            errors = 0
            
            for row in cursor:
                try:
                    # Convert SQLite row to dict
                    article_data = dict(row)
                    
                    # Create Pydantic model
                    article = WikipediaArticle(**article_data)
                    articles.append(article)
                    
                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        self.logger.warning(f"Failed to parse article: {e}")
                    self.load_result.add_warning(f"Failed to parse article {row['title']}: {e}")
            
            self.logger.info(f"Loaded {len(articles)} articles from database")
            if errors > 0:
                self.logger.warning(f"Failed to parse {errors} articles")
            
            return articles
            
        finally:
            conn.close()
    
    def _create_wikipedia_nodes(self) -> int:
        """Create Wikipedia nodes in Neo4j"""
        self.logger.info(f"Creating {len(self.articles)} Wikipedia nodes...")
        
        batch_data = []
        for article in self.articles:
            batch_data.append({
                'page_id': article.page_id,
                'title': article.title,
                'short_summary': article.short_summary,
                'long_summary': article.long_summary,
                'key_topics': article.key_topics,
                'best_city': article.best_city,
                'best_county': article.best_county,
                'best_state': article.best_state,
                'overall_confidence': article.overall_confidence,
                'url': article.url,
                'location_type': article.location_type,
                'latitude': article.latitude,
                'longitude': article.longitude
            })
        
        query = """
        WITH item
        MERGE (w:WikipediaArticle {page_id: item.page_id})
        SET w.title = item.title,
            w.short_summary = item.short_summary,
            w.long_summary = item.long_summary,
            w.key_topics = item.key_topics,
            w.best_city = item.best_city,
            w.best_county = item.best_county,
            w.best_state = item.best_state,
            w.overall_confidence = item.overall_confidence,
            w.url = item.url,
            w.location_type = item.location_type,
            w.latitude = item.latitude,
            w.longitude = item.longitude,
            w.last_updated = datetime()
        """
        
        created = self.batch_execute(query, batch_data, batch_size=100)
        self.logger.info(f"Created {created} Wikipedia nodes")
        return created
    
    def _create_geographic_relationships(self) -> None:
        """Create relationships between Wikipedia articles and geographic entities"""
        self.logger.info("Creating geographic relationships...")
        
        # Prepare relationship batches
        state_batch = []
        county_batch = []
        city_batch = []
        
        for article in self.articles:
            # State relationship
            if article.best_state:
                state_code = GeographicUtils.get_state_code(article.best_state)
                if state_code:
                    state_batch.append({
                        'page_id': article.page_id,
                        'state_code': state_code
                    })
                    
                    self.relationships.append(WikipediaRelationship(
                        page_id=article.page_id,
                        entity_type='state',
                        entity_id=state_code,
                        confidence=article.overall_confidence
                    ))
            
            # County relationship
            if article.best_county and article.best_state:
                state_code = GeographicUtils.get_state_code(article.best_state)
                if state_code:
                    county_id = GeographicUtils.normalize_county_id(article.best_county, state_code)
                    county_batch.append({
                        'page_id': article.page_id,
                        'county_id': county_id
                    })
                    
                    self.relationships.append(WikipediaRelationship(
                        page_id=article.page_id,
                        entity_type='county',
                        entity_id=county_id,
                        confidence=article.overall_confidence
                    ))
            
            # City relationship
            if article.best_city and article.best_state:
                state_code = GeographicUtils.get_state_code(article.best_state)
                if state_code:
                    city_id = GeographicUtils.normalize_city_id(article.best_city, state_code)
                    city_batch.append({
                        'page_id': article.page_id,
                        'city_id': city_id
                    })
                    
                    self.relationships.append(WikipediaRelationship(
                        page_id=article.page_id,
                        entity_type='city',
                        entity_id=city_id,
                        confidence=article.overall_confidence
                    ))
        
        # Create state relationships
        if state_batch:
            query = """
            WITH item
            MATCH (w:WikipediaArticle {page_id: item.page_id})
            MATCH (s:State {state_code: item.state_code})
            MERGE (w)-[:IN_STATE]->(s)
            """
            count = self.batch_execute(query, state_batch, batch_size=200)
            self.load_result.relationships_created['state'] = count
            self.logger.info(f"  Created {count} state relationships")
        
        # Create county relationships
        if county_batch:
            query = """
            WITH item
            MATCH (w:WikipediaArticle {page_id: item.page_id})
            MATCH (c:County {county_id: item.county_id})
            MERGE (w)-[:IN_COUNTY]->(c)
            """
            count = self.batch_execute(query, county_batch, batch_size=200)
            self.load_result.relationships_created['county'] = count
            self.logger.info(f"  Created {count} county relationships")
        
        # Create city relationships
        if city_batch:
            query = """
            WITH item
            MATCH (w:WikipediaArticle {page_id: item.page_id})
            MATCH (city:City {city_id: item.city_id})
            MERGE (w)-[:DESCRIBES_LOCATION_IN]->(city)
            """
            count = self.batch_execute(query, city_batch, batch_size=200)
            self.load_result.relationships_created['city'] = count
            self.logger.info(f"  Created {count} city relationships")
    
    def _verify_integration(self) -> WikipediaStats:
        """Verify Wikipedia integration with geographic hierarchy"""
        self.logger.info("Verifying Wikipedia integration...")
        
        stats = WikipediaStats()
        
        # Count nodes
        stats.total_articles = self.count_nodes("WikipediaArticle")
        
        # Count articles with summaries
        query = "MATCH (w:WikipediaArticle) WHERE w.long_summary <> '' RETURN count(w) as count"
        result = self.execute_query(query)
        stats.articles_with_summaries = result[0]['count'] if result else 0
        
        # Count articles with topics
        query = "MATCH (w:WikipediaArticle) WHERE size(w.key_topics) > 0 RETURN count(w) as count"
        result = self.execute_query(query)
        stats.articles_with_topics = result[0]['count'] if result else 0
        
        # Count geographic connections
        query = "MATCH (w:WikipediaArticle)-[:IN_STATE]->() RETURN count(DISTINCT w) as count"
        result = self.execute_query(query)
        stats.articles_connected_to_states = result[0]['count'] if result else 0
        
        query = "MATCH (w:WikipediaArticle)-[:IN_COUNTY]->() RETURN count(DISTINCT w) as count"
        result = self.execute_query(query)
        stats.articles_connected_to_counties = result[0]['count'] if result else 0
        
        query = "MATCH (w:WikipediaArticle)-[:DESCRIBES_LOCATION_IN]->() RETURN count(DISTINCT w) as count"
        result = self.execute_query(query)
        stats.articles_connected_to_cities = result[0]['count'] if result else 0
        
        # Count high confidence articles
        query = "MATCH (w:WikipediaArticle) WHERE w.overall_confidence > 0.8 RETURN count(w) as count"
        result = self.execute_query(query)
        stats.high_confidence_articles = result[0]['count'] if result else 0
        
        # Calculate average confidence
        query = "MATCH (w:WikipediaArticle) RETURN avg(w.overall_confidence) as avg"
        result = self.execute_query(query)
        stats.avg_confidence = result[0]['avg'] if result else 0.0
        
        self.logger.info(f"  Total articles: {stats.total_articles}")
        self.logger.info(f"  With summaries: {stats.articles_with_summaries}")
        self.logger.info(f"  With topics: {stats.articles_with_topics}")
        self.logger.info(f"  Connected to states: {stats.articles_connected_to_states}")
        self.logger.info(f"  Connected to counties: {stats.articles_connected_to_counties}")
        self.logger.info(f"  Connected to cities: {stats.articles_connected_to_cities}")
        self.logger.info(f"  High confidence (>0.8): {stats.high_confidence_articles}")
        self.logger.info(f"  Average confidence: {stats.avg_confidence:.2f}")
        
        return stats
    
    def get_articles(self) -> List[WikipediaArticle]:
        """Get loaded Wikipedia articles"""
        return self.articles
    
    def get_load_result(self) -> WikipediaLoadResult:
        """Get detailed load result"""
        return self.load_result