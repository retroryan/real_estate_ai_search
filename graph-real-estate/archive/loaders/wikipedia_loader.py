"""Wikipedia knowledge loader with constructor injection"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import json

from core.query_executor import QueryExecutor
from core.config import WikipediaConfig
from data_sources import WikipediaFileDataSource
from models.wikipedia import WikipediaArticle, WikipediaLoadResult


class WikipediaLoader:
    """Load Wikipedia knowledge layer with injected dependencies"""
    
    def __init__(
        self,
        query_executor: QueryExecutor,
        config: WikipediaConfig,
        data_source: WikipediaFileDataSource
    ):
        """
        Initialize Wikipedia loader with dependencies
        
        Args:
            query_executor: Database query executor
            config: Wikipedia configuration
            data_source: Wikipedia data source
        """
        self.query_executor = query_executor
        self.config = config
        self.data_source = data_source
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Load result tracking
        self.load_result = WikipediaLoadResult()
    
    def load(self) -> WikipediaLoadResult:
        """
        Main loading method
        
        Returns:
            WikipediaLoadResult with statistics
        """
        self.logger.info("=" * 60)
        self.logger.info("WIKIPEDIA KNOWLEDGE LAYER LOADING")
        self.logger.info("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # Create constraints and indexes
            self._create_constraints_and_indexes()
            
            # Load Wikipedia articles
            articles = self._load_wikipedia_articles()
            
            # Load Wikipedia summaries and enrich articles
            self._load_wikipedia_summaries(articles)
            
            # Create Wikipedia article nodes
            nodes_created = self._create_wikipedia_nodes(articles)
            self.load_result.articles_loaded = nodes_created
            
            # Extract and create topic nodes
            self._extract_and_create_topics(articles)
            
            # Calculate duration
            self.load_result.duration_seconds = (datetime.now() - start_time).total_seconds()
            self.load_result.success = True
            
            self.logger.info("=" * 60)
            self.logger.info("✅ WIKIPEDIA KNOWLEDGE LAYER COMPLETE")
            self.logger.info(f"  Articles loaded: {self.load_result.articles_loaded}")
            self.logger.info(f"  Topics extracted: {self.load_result.topics_extracted}")
            self.logger.info(f"  Duration: {self.load_result.duration_seconds:.1f}s")
            self.logger.info("=" * 60)
            
            return self.load_result
            
        except Exception as e:
            self.logger.error(f"Failed to load Wikipedia data: {e}")
            self.load_result.add_error(str(e))
            self.load_result.success = False
            import traceback
            traceback.print_exc()
            return self.load_result
    
    def _create_constraints_and_indexes(self) -> None:
        """Create Wikipedia-specific constraints and indexes"""
        self.logger.info("Creating Wikipedia constraints and indexes...")
        
        # Constraints
        constraints = [
            ("WikipediaArticle.page_id",
             "CREATE CONSTRAINT IF NOT EXISTS FOR (w:WikipediaArticle) REQUIRE w.page_id IS UNIQUE"),
            ("Topic.topic_id",
             "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Topic) REQUIRE t.topic_id IS UNIQUE"),
        ]
        
        for name, query in constraints:
            self.query_executor.create_constraint(name, query)
        
        # Indexes
        indexes = [
            ("WikipediaArticle.title",
             "CREATE INDEX IF NOT EXISTS FOR (w:WikipediaArticle) ON (w.title)"),
            ("WikipediaArticle.best_city",
             "CREATE INDEX IF NOT EXISTS FOR (w:WikipediaArticle) ON (w.best_city)"),
            ("WikipediaArticle.best_state",
             "CREATE INDEX IF NOT EXISTS FOR (w:WikipediaArticle) ON (w.best_state)"),
            ("Topic.name",
             "CREATE INDEX IF NOT EXISTS FOR (t:Topic) ON (t.name)"),
            ("Topic.category",
             "CREATE INDEX IF NOT EXISTS FOR (t:Topic) ON (t.category)"),
        ]
        
        for name, query in indexes:
            self.query_executor.create_index(name, query)
    
    def _load_wikipedia_articles(self) -> List[WikipediaArticle]:
        """Load Wikipedia articles from data source"""
        self.logger.info("Loading Wikipedia articles...")
        
        articles = []
        raw_articles = self.data_source.load_articles()
        
        # Apply limit if configured
        if self.config.max_articles:
            raw_articles = raw_articles[:self.config.max_articles]
        
        for article_data in raw_articles:
            try:
                # Create WikipediaArticle model
                article = WikipediaArticle(**article_data)
                articles.append(article)
                
            except Exception as e:
                self.logger.warning(f"Failed to parse article {article_data.get('page_id', 'unknown')}: {e}")
                self.load_result.add_warning(f"Failed to parse article: {e}")
        
        self.logger.info(f"  Loaded {len(articles)} Wikipedia articles")
        return articles
    
    def _load_wikipedia_summaries(self, articles: List[WikipediaArticle]) -> None:
        """Load and merge Wikipedia summaries into articles"""
        self.logger.info("Loading Wikipedia summaries...")
        
        summaries = self.data_source.load_summaries()
        summary_map = {s['page_id']: s for s in summaries}
        
        enriched_count = 0
        for article in articles:
            if article.page_id in summary_map:
                summary = summary_map[article.page_id]
                
                # Enrich article with summary data
                article.summary = summary.get('summary')
                article.key_topics = summary.get('key_topics', [])
                article.best_city = summary.get('best_city')
                article.best_state = summary.get('best_state')
                article.overall_confidence = summary.get('overall_confidence', 0.0)
                
                enriched_count += 1
        
        self.logger.info(f"  Enriched {enriched_count} articles with summaries")
        self.load_result.summaries_loaded = enriched_count
    
    def _create_wikipedia_nodes(self, articles: List[WikipediaArticle]) -> int:
        """Create Wikipedia article nodes in database"""
        self.logger.info(f"Creating {len(articles)} Wikipedia article nodes...")
        
        batch_data = []
        for article in articles:
            batch_data.append({
                'page_id': article.page_id,
                'title': article.title,
                'url': article.url,
                'summary': article.summary or '',
                'full_text': article.full_text[:5000] if article.full_text else '',  # Truncate for storage
                'key_topics': article.key_topics or [],
                'best_city': article.best_city,
                'best_state': article.best_state,
                'overall_confidence': article.overall_confidence or 0.0,
                'depth': article.depth,
                'relevance_score': article.relevance_score,
                'latitude': article.latitude,
                'longitude': article.longitude
            })
        
        query = """
        WITH item
        MERGE (w:WikipediaArticle {page_id: item.page_id})
        SET w.title = item.title,
            w.url = item.url,
            w.summary = item.summary,
            w.full_text = item.full_text,
            w.key_topics = item.key_topics,
            w.best_city = item.best_city,
            w.best_state = item.best_state,
            w.overall_confidence = item.overall_confidence,
            w.depth = item.depth,
            w.relevance_score = item.relevance_score,
            w.latitude = item.latitude,
            w.longitude = item.longitude,
            w.created_at = datetime()
        """
        
        created = self.query_executor.batch_execute(query, batch_data)
        self.logger.info(f"  Created {created} Wikipedia article nodes")
        return created
    
    def _extract_and_create_topics(self, articles: List[WikipediaArticle]) -> None:
        """Extract topics from articles and create topic nodes"""
        self.logger.info("Extracting and creating topic nodes...")
        
        # Collect all unique topics
        topic_set = set()
        topic_details = {}
        
        for article in articles:
            if article.key_topics:
                for topic in article.key_topics:
                    if isinstance(topic, str):
                        topic_name = topic
                        topic_category = self._categorize_topic(topic)
                    elif isinstance(topic, dict):
                        topic_name = topic.get('name', topic.get('topic', ''))
                        topic_category = topic.get('category', self._categorize_topic(topic_name))
                    else:
                        continue
                    
                    if topic_name:
                        topic_id = topic_name.lower().replace(' ', '_').replace('-', '_')
                        topic_set.add(topic_id)
                        topic_details[topic_id] = {
                            'name': topic_name,
                            'category': topic_category
                        }
        
        # Create topic nodes
        if topic_set:
            batch_data = []
            for topic_id, details in topic_details.items():
                batch_data.append({
                    'topic_id': topic_id,
                    'name': details['name'],
                    'category': details['category']
                })
            
            query = """
            WITH item
            MERGE (t:Topic {topic_id: item.topic_id})
            SET t.name = item.name,
                t.category = item.category,
                t.created_at = datetime()
            """
            
            created = self.query_executor.batch_execute(query, batch_data)
            self.load_result.topics_extracted = created
            self.logger.info(f"  Created {created} topic nodes")
            
            # Create article->topic relationships
            self._create_article_topic_relationships(articles, topic_details)
    
    def _categorize_topic(self, topic_name: str) -> str:
        """Categorize a topic based on its name"""
        topic_lower = topic_name.lower()
        
        if any(word in topic_lower for word in ['park', 'trail', 'recreation', 'ski', 'resort', 'golf']):
            return 'Recreation'
        elif any(word in topic_lower for word in ['museum', 'art', 'culture', 'theater', 'music']):
            return 'Culture'
        elif any(word in topic_lower for word in ['history', 'historic', 'heritage', 'founded']):
            return 'History'
        elif any(word in topic_lower for word in ['business', 'economy', 'industry', 'tech']):
            return 'Business'
        elif any(word in topic_lower for word in ['school', 'university', 'college', 'education']):
            return 'Education'
        elif any(word in topic_lower for word in ['neighborhood', 'district', 'area', 'zone']):
            return 'Geography'
        elif any(word in topic_lower for word in ['transport', 'transit', 'airport', 'station']):
            return 'Transportation'
        else:
            return 'General'
    
    def _create_article_topic_relationships(self, articles: List[WikipediaArticle], topic_details: Dict[str, Dict[str, str]]) -> None:
        """Create relationships between articles and topics"""
        self.logger.info("Creating article->topic relationships...")
        
        relationships = []
        
        for article in articles:
            if article.key_topics:
                for topic in article.key_topics:
                    if isinstance(topic, str):
                        topic_name = topic
                    elif isinstance(topic, dict):
                        topic_name = topic.get('name', topic.get('topic', ''))
                    else:
                        continue
                    
                    if topic_name:
                        topic_id = topic_name.lower().replace(' ', '_').replace('-', '_')
                        if topic_id in topic_details:
                            relationships.append({
                                'page_id': article.page_id,
                                'topic_id': topic_id
                            })
        
        if relationships:
            batch_query = """
            UNWIND $batch AS rel
            MATCH (w:WikipediaArticle {page_id: rel.page_id})
            MATCH (t:Topic {topic_id: rel.topic_id})
            MERGE (w)-[r:HAS_TOPIC]->(t)
            SET r.created_at = datetime()
            """
            
            batch_size = 500
            total_created = 0
            for i in range(0, len(relationships), batch_size):
                batch = relationships[i:i + batch_size]
                self.query_executor.execute_write(batch_query, {'batch': batch})
                total_created += len(batch)
            
            self.logger.info(f"  Created {total_created} article->topic relationships")