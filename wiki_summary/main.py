#!/usr/bin/env python3
"""
Wikipedia summarization pipeline with integrated relevance filtering.
High-quality DSPy implementation with full Pydantic type safety.
"""

import argparse
import logging
import os
import sqlite3
import sys
from pathlib import Path
from typing import List, Optional

# Setup project paths (assumes running from wiki_summary/)
current_dir = Path(__file__).parent
project_root = current_dir.parent

sys.path.insert(0, str(project_root))
sys.path.insert(0, str(current_dir))

# Load environment variables from .env file in current directory
from dotenv import load_dotenv
load_dotenv(Path(".env"))

# Import pipeline components
import dspy
from config import PipelineConfig, ProcessingResults, ProcessingStats
from summarize.extract_agent import WikipediaExtractAgent
from summarize.models import WikipediaPage, HtmlExtractedData, PageSummary
from summarize.html_parser import extract_location_hints
from shared.llm_utils import setup_llm
from wiki_summary.evaluation import RealEstateRelevanceFilter, RelevanceScore, EnhancedLocationData
from wiki_summary.services import LocationManager, FlaggedContentService
from wiki_summary.exceptions import (
    ProcessingException, LLMException, DatabaseException, 
    FileReadException, HTMLParsingException, ConfigurationException
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class WikipediaSummarizationPipeline:
    """
    High-quality Wikipedia summarization pipeline with integrated relevance filtering.
    Uses Pydantic models for type safety and DSPy for LLM interactions.
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """Initialize pipeline with type-safe configuration."""
        self.config = config or PipelineConfig()
        
        logger.info("Initializing Wikipedia summarization pipeline...")
        
        # Setup LLM with configuration
        self.llm = setup_llm(
            model=self.config.llm.model,
            temperature=self.config.llm.temperature,
            max_tokens=self.config.llm.max_tokens
        )
        
        # Initialize agents
        self.extract_agent = WikipediaExtractAgent(
            use_chain_of_thought=True,
            use_cache=self.config.llm.cache_enabled
        )
        
        # Initialize relevance filter
        self.relevance_filter = RealEstateRelevanceFilter()
        
        # Initialize location manager for fixing mismatches
        self.location_manager = LocationManager(str(self.config.database.path))
        
        # Initialize flagged content service for immediate writes
        self.flagged_content_service = FlaggedContentService(str(self.config.database.path))
        
        logger.info("Pipeline initialization complete")
        logger.info(f"Configuration: {self.config.llm.model}, cache={self.config.llm.cache_enabled}")
    
    def process_articles(self, 
                        limit: Optional[int] = None,
                        article_id: Optional[int] = None,
                        location_id: Optional[int] = None) -> ProcessingResults:
        """
        Process Wikipedia articles with relevance filtering.
        Always creates a flagged content report in the database.
        
        Args:
            limit: Maximum number of articles to process
            article_id: Specific article ID to process
            location_id: Process articles for a specific location ID
            
        Returns:
            ProcessingResults with type-safe statistics and data
        """
        if article_id is not None:
            logger.info(f"Processing specific article ID: {article_id}")
        elif location_id is not None:
            logger.info(f"Processing articles for location ID: {location_id}")
        elif limit is None:
            logger.info("Starting article processing (no limit)")
        else:
            limit = limit or self.config.processing.batch_size
            logger.info(f"Starting article processing (limit={limit})")
        
        # Get articles from database
        articles = self._get_articles_from_db(limit, article_id, location_id)
        logger.info(f"Retrieved {len(articles)} articles from database")
        
        if not articles:
            logger.warning("No articles found matching criteria")
            return ProcessingResults(stats=ProcessingStats())
        
        # Initialize results tracking
        processed_summaries = []
        relevance_evaluations = []
        stats = ProcessingStats(total_articles=len(articles))
        
        # Process each article
        for i, article_data in enumerate(articles, 1):
            logger.info(f"Processing article {i}/{len(articles)}: {article_data['title']}")
            logger.debug(f"  Current location: {article_data.get('city', 'unknown')}, {article_data.get('state', 'unknown')} "
                        f"(county: {article_data.get('county', 'unknown')}, type: {article_data.get('location_type', 'unknown')})")
            
            try:
                # Step 1: Generate summary with DSPy agent
                summary = self._process_article_with_agent(article_data)
                
                if summary:
                    # Step 2: Check for location issues (may remove article)
                    fix_result = self.location_manager.process_location_fix(article_data, summary)
                    
                    # Skip if article was removed
                    if fix_result and fix_result.success and fix_result.new_location_id == -1:
                        logger.info(f"  ✓ Removed out-of-scope article: {fix_result.article_title}")
                        stats.flagged_articles += 1
                        continue
                    
                    # Step 3: Save summary for valid articles
                    self._save_summary_to_db(summary)
                    
                    # Step 4: Evaluate relevance
                    relevance = self._evaluate_article_relevance_from_summary(article_data, summary)
                    
                    # Update stats and save evaluation
                    processed_summaries.append(summary)
                    relevance_evaluations.append(relevance)
                    self.flagged_content_service.save_evaluation_immediately(relevance)
                    
                    if fix_result and fix_result.success:
                        logger.info(f"  ✓ Fixed location for {fix_result.article_title}")
                    
                    if relevance.is_relevant:
                        stats.relevant_articles += 1
                        stats.processed_summaries += 1
                        logger.info(f"  ✓ Relevant article (score: {relevance.overall_score:.2f})")
                    else:
                        stats.flagged_articles += 1
                        logger.info(f"  → Flagged as non-relevant (score: {relevance.overall_score:.2f})")
                        
                else:
                    # Fallback: evaluate based on raw data without summary
                    relevance = self._evaluate_article_relevance(article_data)
                    relevance_evaluations.append(relevance)
                    self.flagged_content_service.save_evaluation_immediately(relevance)
                    
                    stats.flagged_articles += 1
                    logger.warning(f"  → Summary generation failed, flagged article")
                    
            except DatabaseException:
                # Re-raise database errors - these are critical
                raise
            except (LLMException, ProcessingException) as e:
                logger.error(f"Processing error for article {article_data['title']}: {e}")
                stats.errors += 1
            except Exception as e:
                # Log unexpected errors with more context
                logger.error(f"Unexpected error processing article {article_data['title']}: {type(e).__name__}: {e}", exc_info=True)
                stats.errors += 1
        
        # Get final statistics from database (already written during processing)
        flagged_report_stats = self.flagged_content_service.get_stats()
        
        logger.info(f"Processing complete: {stats.success_rate:.1f}% success rate")
        logger.info(f"Flagged content stats: {flagged_report_stats}")
        
        return ProcessingResults(
            stats=stats,
            summaries=processed_summaries,
            relevance_evaluations=relevance_evaluations,
            flagged_report_path=Path("database:flagged_content") if flagged_report_stats else None
        )
    
    def _get_articles_from_db(self, limit: Optional[int], article_id: Optional[int] = None, location_id: Optional[int] = None) -> List[dict]:
        """Retrieve ALL articles from database for relevance evaluation."""
        articles = []
        
        with sqlite3.connect(self.config.database.path) as conn:
            # Query for specific article, location, or ALL articles
            if article_id is not None:
                # Query for specific article by ID
                query = """
                    SELECT 
                        a.id, a.pageid, a.title, a.extract, a.html_file,
                        COALESCE(l.location, '') as city, l.state, l.county,
                        l.country || '/' || l.state || '/' || l.county as path,
                        l.location_type, l.location_id
                    FROM articles a 
                    JOIN locations l ON a.location_id = l.location_id
                    WHERE a.id = ?
                """
                cursor = conn.execute(query, (article_id,))
                logger.info(f"Querying for specific article ID: {article_id}")
            elif location_id is not None:
                # Query for articles by location ID
                base_query = """
                    SELECT 
                        a.id, a.pageid, a.title, a.extract, a.html_file,
                        COALESCE(l.location, '') as city, l.state, l.county,
                        l.country || '/' || l.state || '/' || l.county as path,
                        l.location_type, l.location_id
                    FROM articles a 
                    JOIN locations l ON a.location_id = l.location_id
                    WHERE a.location_id = ?
                """
                
                if limit is None:
                    query = base_query
                    cursor = conn.execute(query, (location_id,))
                else:
                    query = base_query + " LIMIT ?"
                    cursor = conn.execute(query, (location_id, limit))
                logger.info(f"Querying for location ID: {location_id}")
            else:
                # Query for ALL articles to evaluate which ones to keep/flag
                base_query = """
                    SELECT 
                        a.id, a.pageid, a.title, a.extract, a.html_file,
                        COALESCE(l.location, '') as city, l.state, l.county,
                        l.country || '/' || l.state || '/' || l.county as path,
                        l.location_type, l.location_id
                    FROM articles a 
                    JOIN locations l ON a.location_id = l.location_id
                """
                
                if limit is None:
                    query = base_query
                    cursor = conn.execute(query)
                else:
                    query = base_query + " LIMIT ?"
                    cursor = conn.execute(query, (limit,))
            
            for row in cursor:
                # Handle the extended query results
                if len(row) > 8:  # Extended query with location info
                    article_id, pageid, title, extract, html_file, city, state, county, path, location_type, location_id = row
                    logger.debug(f"Article {article_id}: {title} - Location: {city}, {state} (type: {location_type}, loc_id: {location_id})")
                else:
                    article_id, pageid, title, extract, html_file, city, state, county, path = row[:9]
                    location_type = None
                    location_id = None
                
                # Load HTML content if available
                html_content = ""
                if html_file:
                    html_path = Path("data") / "wikipedia" / "pages" / html_file
                    if html_path.exists():
                        try:
                            with open(html_path, 'r', encoding='utf-8') as f:
                                html_content = f.read()
                        except (IOError, OSError) as e:
                            logger.warning(f"Could not read HTML file {html_path}: {e}")
                        except UnicodeDecodeError as e:
                            logger.warning(f"Could not decode HTML file {html_path}: {e}")
                
                articles.append({
                    'id': article_id,
                    'pageid': pageid,
                    'title': title,
                    'extract': extract or "",
                    'html_content': html_content,
                    'city': city,
                    'state': state,
                    'county': county,
                    'path': path,
                    'location_type': location_type,
                    'location_id': location_id
                })
                
                logger.debug(f"Added article: {title} (loc_id: {location_id}, state: {state}, county: {county}, type: {location_type})")
        
        return articles
    
    def _evaluate_article_relevance(self, article_data: dict) -> RelevanceScore:
        """Evaluate article relevance for real estate purposes based on raw data."""
        return self.relevance_filter.evaluate_article(
            title=article_data['title'],
            content=article_data['extract'],
            location_data={
                'article_id': article_data['id'],
                'state': article_data['state'],
                'city': article_data['city']
            }
        )
    
    def _evaluate_article_relevance_from_summary(self, article_data: dict, summary: PageSummary) -> RelevanceScore:
        """Evaluate article relevance based on LLM-generated summary data."""
        # Combine both summaries for comprehensive content analysis
        full_summary = f"{summary.short_summary}\n\n{summary.long_summary}"
        
        # Create Pydantic model for type-safe location data
        location_data = EnhancedLocationData(
            article_id=article_data['id'],
            state=summary.llm_location.state or article_data['state'],
            city=summary.llm_location.city or article_data['city'],
            county=summary.llm_location.county,
            confidence=summary.overall_confidence
        )
        
        # Use LLM-based evaluation only (no keyword matching)
        return self.relevance_filter.evaluate_article_with_llm_data(
            title=article_data['title'],
            summary=full_summary,
            location_data=location_data,
            key_topics=summary.key_topics
        )
    
    def _process_article_with_agent(self, article_data: dict) -> Optional[PageSummary]:
        """Process article with DSPy agent."""
        try:
            # Create WikipediaPage object
            page = WikipediaPage(
                page_id=article_data['pageid'],
                title=article_data['title'],
                html_content=article_data['html_content'],
                location_path=article_data['path']
            )
            
            # Extract HTML location hints if available
            html_extracted = None
            if article_data['html_content']:
                try:
                    hints = extract_location_hints(article_data['html_content'])
                    html_extracted = HtmlExtractedData(
                        city=hints.get('city'),
                        state=hints.get('state'),
                        county=hints.get('county'),
                        coordinates=hints.get('coordinates'),
                        confidence_scores=hints.get('confidence_scores', {})
                    )
                except (KeyError, ValueError, TypeError) as e:
                    logger.debug(f"HTML extraction failed for {article_data['title']}: {e}")
                    # Continue without HTML hints - not critical
            
            # Process with agent (call module directly, not .forward())
            summary = self.extract_agent(page, html_extracted)
            
            # IMPORTANT: Set the article_id from the database (not set by extract_agent)
            summary.article_id = article_data['id']
            
            logger.info(f"  ✓ Summary generated (confidence: {summary.overall_confidence:.2f})")
            return summary
            
        except (KeyError, ValueError) as e:
            logger.error(f"Data validation error for {article_data['title']}: {e}")
            return None
        except Exception as e:
            # Check if it's a DSPy-related error by checking the error message/context
            error_msg = str(e)
            if 'dspy' in error_msg.lower() or 'completions' in error_msg or 'subscriptable' in error_msg:
                logger.error(f"DSPy processing error for {article_data['title']}: {e}")
            else:
                logger.error(f"Unexpected error processing {article_data['title']}: {type(e).__name__}: {e}")
            return None
    
    def _save_summary_to_db(self, summary: PageSummary):
        """Save summary to database."""
        try:
            with sqlite3.connect(self.config.database.path) as conn:
                # Check if page_summaries table exists, create if not
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS page_summaries (
                        page_id INTEGER PRIMARY KEY,
                        article_id INTEGER,
                        title TEXT,
                        short_summary TEXT NOT NULL,
                        long_summary TEXT NOT NULL,
                        key_topics TEXT,
                        best_city TEXT,
                        best_state TEXT,
                        overall_confidence REAL,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (page_id) REFERENCES articles(pageid)
                    )
                """)
                
                # Insert or replace summary
                conn.execute("""
                    INSERT OR REPLACE INTO page_summaries 
                    (page_id, article_id, title, short_summary, long_summary, key_topics, best_city, best_county, best_state, overall_confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    summary.page_id,
                    summary.article_id or 0,  # Provide default if None
                    summary.title,
                    summary.short_summary,
                    summary.long_summary,
                    ', '.join(summary.key_topics),
                    summary.llm_location.city,
                    summary.llm_location.county,
                    summary.llm_location.state,
                    summary.overall_confidence
                ))
                
                logger.debug(f"Saved summary for page {summary.page_id}")
                
        except sqlite3.Error as e:
            logger.error(f"Database error saving summary for page {summary.page_id}: {e}")
            raise DatabaseException(f"Failed to save summary: {e}") from e
    


def main():
    """Main entry point for Wikipedia summarization pipeline."""
    parser = argparse.ArgumentParser(
        description="Wikipedia Summarization Pipeline with Relevance Filtering"
    )
    
    parser.add_argument('--limit', type=int, default=None,
                       help='Maximum articles to process (default: no limit)')
    parser.add_argument('--force-reprocess', action='store_true',
                       help='Force reprocessing of all articles (clear cache and regenerate)')
    parser.add_argument('--article-id', type=int, default=None,
                       help='Process a specific article by its database ID')
    parser.add_argument('--location-id', type=int, default=None,
                       help='Process articles for a specific location ID')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging for debugging')
    
    args = parser.parse_args()
    
    # Configure logging level based on verbose flag
    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%H:%M:%S',
            force=True
        )
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
        # Also set debug for all wiki_summary modules
        logging.getLogger('wiki_summary').setLevel(logging.DEBUG)
    
    # Handle force reprocessing
    if args.force_reprocess:
        logger.info("Force reprocessing requested - clearing cache and summaries")
        # Clear the cache directory
        import shutil
        cache_dir = Path(".cache/summaries")
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            logger.info(f"Cleared cache directory: {cache_dir}")
        
        # Clear existing summaries from database
        from config import PipelineConfig
        config = PipelineConfig()
        with sqlite3.connect(config.database.path) as conn:
            conn.execute("DELETE FROM page_summaries")
            conn.execute("DELETE FROM flagged_content")
            conn.commit()
            logger.info("Cleared existing summaries and flagged content from database")
        
        # IMPORTANT: Disable DSPy caching for true reprocessing
        import dspy
        dspy.configure_cache(
            enable_disk_cache=False,
            enable_memory_cache=False,
        )
        logger.info("Disabled DSPy caching for fresh LLM calls")
    
    # Initialize pipeline
    try:
        pipeline = WikipediaSummarizationPipeline()
    except ConfigurationException as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to initialize pipeline: {type(e).__name__}: {e}", exc_info=True)
        sys.exit(1)
    
    try:
        # Process articles
        results = pipeline.process_articles(
            limit=args.limit,
            article_id=args.article_id,
            location_id=args.location_id
        )
        
        # Display results using Pydantic model
        print(f"\n=== Processing Results ===")
        print(results.summary_text())
        
        if results.flagged_report_path:
            print(f"\nFlagged content report: Stored in database table 'flagged_content'")
        
        if results.summaries:
            print(f"\nSample short summaries:")
            for summary in results.summaries[:3]:
                print(f"- {summary.title}: {summary.short_summary[:100]}...")
                print(f"  (Short: {len(summary.short_summary.split())} words, Long: {len(summary.long_summary.split())} words)")
    
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        sys.exit(0)
    except DatabaseException as e:
        logger.error(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline error: {type(e).__name__}: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()