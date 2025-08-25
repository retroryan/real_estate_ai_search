"""Wikipedia data source implementation"""

from typing import List, Dict, Any, Optional
import logging
import json

from api_client import APIClientFactory, WikipediaAPIClient
from core.interfaces import IWikipediaDataSource


class WikipediaFileDataSource(IWikipediaDataSource):
    """API-based Wikipedia data source"""
    
    def __init__(self, api_factory: APIClientFactory):
        """
        Initialize Wikipedia data source
        
        Args:
            api_factory: Factory for creating API clients
        """
        self.api_factory = api_factory
        self.wikipedia_client = api_factory.create_wikipedia_client()
        self.system_client = api_factory.create_system_client()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def exists(self) -> bool:
        """Check if data source exists"""
        try:
            health_status = self.system_client.check_readiness()
            return health_status.get('status') == 'ready'
        except Exception as e:
            self.logger.warning(f"API health check failed: {e}")
            return False
    
    def load(self) -> Dict[str, Any]:
        """Load all Wikipedia data"""
        return {
            "articles": self.load_articles(),
            "summaries": self.load_summaries()
        }
    
    def load_articles(self) -> List[Dict[str, Any]]:
        """
        Load Wikipedia articles from API
        
        Returns:
            List of article dictionaries
        """
        try:
            all_articles = []
            page = 1
            page_size = 100
            
            while True:
                api_response = self.wikipedia_client.get_all_articles(
                    page=page,
                    page_size=page_size
                )
                
                if not api_response.articles:
                    break
                    
                # Transform API response (Pydantic models) to dictionary format
                for article_model in api_response.articles:
                    article_dict = article_model.model_dump()
                    
                    # Map API fields to expected database column equivalents
                    if hasattr(article_model, 'enrichment_metadata'):
                        metadata = article_model.enrichment_metadata
                        if metadata:
                            article_dict['latitude'] = metadata.location_info.latitude if metadata.location_info else None
                            article_dict['longitude'] = metadata.location_info.longitude if metadata.location_info else None
                            article_dict['relevance_score'] = getattr(metadata, 'confidence_score', 0.0)
                    
                    # Ensure compatibility with expected fields
                    article_dict.setdefault('page_id', article_model.page_id)
                    article_dict.setdefault('title', article_model.title)
                    article_dict.setdefault('url', article_model.url)
                    article_dict.setdefault('full_text', article_model.content)
                    article_dict.setdefault('depth', 0)
                    article_dict.setdefault('relevance_score', 0.0)
                    article_dict.setdefault('latitude', None)
                    article_dict.setdefault('longitude', None)
                    article_dict.setdefault('created_at', article_model.created_at)
                    
                    all_articles.append(article_dict)
                
                self.logger.info(f"Loaded {len(api_response.articles)} Wikipedia articles from page {page}")
                
                # Check if we have more pages
                if len(api_response.articles) < page_size:
                    break
                page += 1
            
            self.logger.info(f"Total Wikipedia articles loaded: {len(all_articles)}")
            return all_articles
            
        except Exception as e:
            self.logger.error(f"Failed to load articles from API: {e}")
            return []
    
    def load_summaries(self) -> List[Dict[str, Any]]:
        """
        Load Wikipedia summaries from API
        
        Returns:
            List of summary dictionaries
        """
        try:
            all_summaries = []
            page = 1
            page_size = 100
            
            while True:
                api_response = self.wikipedia_client.get_all_summaries(
                    page=page,
                    page_size=page_size
                )
                
                if not api_response.summaries:
                    break
                    
                # Transform API response (Pydantic models) to dictionary format
                for summary_model in api_response.summaries:
                    summary_dict = summary_model.model_dump()
                    
                    # Map API confidence scores to expected database column equivalents
                    summary_dict['overall_confidence'] = getattr(summary_model, 'confidence_score', 0.0)
                    
                    # Handle topic extraction and key topics formatting
                    if hasattr(summary_model, 'key_topics') and summary_model.key_topics:
                        # Ensure key_topics is serializable
                        if isinstance(summary_model.key_topics, list):
                            summary_dict['key_topics'] = summary_model.key_topics
                        else:
                            summary_dict['key_topics'] = [summary_model.key_topics]
                    else:
                        summary_dict['key_topics'] = []
                    
                    # Ensure compatibility with expected fields
                    summary_dict.setdefault('page_id', summary_model.page_id)
                    summary_dict.setdefault('article_id', getattr(summary_model, 'article_id', summary_model.page_id))
                    summary_dict.setdefault('summary', summary_model.summary_text)
                    summary_dict.setdefault('best_city', getattr(summary_model, 'best_city', ''))
                    summary_dict.setdefault('best_state', getattr(summary_model, 'best_state', ''))
                    summary_dict.setdefault('created_at', summary_model.created_at)
                    
                    # Add article metadata for compatibility
                    summary_dict.setdefault('article_title', getattr(summary_model, 'article_title', ''))
                    summary_dict.setdefault('article_url', getattr(summary_model, 'article_url', ''))
                    
                    all_summaries.append(summary_dict)
                
                self.logger.info(f"Loaded {len(api_response.summaries)} Wikipedia summaries from page {page}")
                
                # Check if we have more pages
                if len(api_response.summaries) < page_size:
                    break
                page += 1
            
            self.logger.info(f"Total Wikipedia summaries loaded: {len(all_summaries)}")
            return all_summaries
            
        except Exception as e:
            self.logger.error(f"Failed to load summaries from API: {e}")
            return []
    
    def get_html_file(self, page_id: int) -> Optional[str]:
        """
        Get API endpoint for Wikipedia page content (legacy method for compatibility)
        
        Args:
            page_id: Wikipedia page ID
            
        Returns:
            API endpoint URL if page exists, None otherwise
        """
        try:
            article = self.get_article_by_page_id(page_id)
            if article:
                base_url = self.api_factory.config.base_url
                return f"{base_url}/wikipedia/articles/{page_id}"
            return None
        except Exception:
            return None
    
    def list_html_files(self) -> List[str]:
        """
        List all Wikipedia article API endpoints (legacy method for compatibility)
        
        Returns:
            List of API endpoint URLs
        """
        try:
            articles = self.load_articles()
            base_url = self.api_factory.config.base_url
            return [f"{base_url}/wikipedia/articles/{article['page_id']}" for article in articles]
        except Exception:
            return []
    
    def get_article_by_page_id(self, page_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific article by page ID
        
        Args:
            page_id: Wikipedia page ID
            
        Returns:
            Article dictionary if found, None otherwise
        """
        try:
            article_model = self.wikipedia_client.get_article(page_id)
            if article_model:
                article_dict = article_model.model_dump()
                
                # Ensure compatibility with expected fields
                article_dict.setdefault('page_id', article_model.page_id)
                article_dict.setdefault('title', article_model.title)
                article_dict.setdefault('url', article_model.url)
                article_dict.setdefault('full_text', article_model.content)
                article_dict.setdefault('depth', 0)
                article_dict.setdefault('relevance_score', 0.0)
                article_dict.setdefault('latitude', None)
                article_dict.setdefault('longitude', None)
                article_dict.setdefault('created_at', article_model.created_at)
                
                return article_dict
            return None
            
        except Exception as e:
            self.logger.error(f"API error getting article {page_id}: {e}")
            return None
    
    def get_summary_by_page_id(self, page_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific summary by page ID
        
        Args:
            page_id: Wikipedia page ID
            
        Returns:
            Summary dictionary if found, None otherwise
        """
        try:
            summary_model = self.wikipedia_client.get_summary(page_id)
            if summary_model:
                summary_dict = summary_model.model_dump()
                
                # Map API confidence scores to expected database column equivalents
                summary_dict['overall_confidence'] = getattr(summary_model, 'confidence_score', 0.0)
                
                # Handle topic extraction and key topics formatting
                if hasattr(summary_model, 'key_topics') and summary_model.key_topics:
                    if isinstance(summary_model.key_topics, list):
                        summary_dict['key_topics'] = summary_model.key_topics
                    else:
                        summary_dict['key_topics'] = [summary_model.key_topics]
                else:
                    summary_dict['key_topics'] = []
                
                # Ensure compatibility with expected fields
                summary_dict.setdefault('page_id', summary_model.page_id)
                summary_dict.setdefault('article_id', getattr(summary_model, 'article_id', summary_model.page_id))
                summary_dict.setdefault('summary', summary_model.summary_text)
                summary_dict.setdefault('best_city', getattr(summary_model, 'best_city', ''))
                summary_dict.setdefault('best_state', getattr(summary_model, 'best_state', ''))
                summary_dict.setdefault('created_at', summary_model.created_at)
                
                # Add article metadata for compatibility
                summary_dict.setdefault('article_title', getattr(summary_model, 'article_title', ''))
                summary_dict.setdefault('article_url', getattr(summary_model, 'article_url', ''))
                
                return summary_dict
            return None
            
        except Exception as e:
            self.logger.error(f"API error getting summary {page_id}: {e}")
            return None