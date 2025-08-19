"""
Integrated location evaluation service that combines:
- Location classification (DSPy)
- Flexible location service (database)
- Relevance evaluation (flagging)
"""

import logging
from typing import Optional, Dict, Tuple
from pathlib import Path

import dspy
from wiki_summary.summarize.location_classifier import LocationClassificationCoT
from wiki_summary.services.flexible_location import (
    LocationClassification,
    FlexibleLocationService
)
from wiki_summary.evaluation.relevance_filter import RealEstateRelevanceFilter
from wiki_summary.models.relevance import RelevanceScore
from wiki_summary.exceptions import LLMException, LocationException

logger = logging.getLogger(__name__)


class IntegratedLocationEvaluator:
    """Integrates location classification, database updates, and relevance evaluation."""
    
    def __init__(self, db_path: str):
        """Initialize all components."""
        self.db_path = Path(db_path)
        
        # Initialize components
        self.classifier = LocationClassificationCoT(use_chain_of_thought=True)
        self.location_service = FlexibleLocationService(str(db_path))
        self.relevance_filter = RealEstateRelevanceFilter()
        
        logger.info("Initialized IntegratedLocationEvaluator")
    
    def process_article(
        self, 
        article_data: Dict,
        page_content: Optional[str] = None,
        html_hints: Optional[str] = None
    ) -> Tuple[LocationClassification, RelevanceScore, int]:
        """
        Process an article through the complete pipeline:
        1. Classify location type
        2. Update database
        3. Evaluate relevance (flag if not Utah/California)
        
        Args:
            article_data: Dict with 'id', 'title', 'pageid', etc.
            page_content: Article text content (optional, will use extract if not provided)
            html_hints: HTML-extracted location hints (optional)
            
        Returns:
            Tuple of (LocationClassification, RelevanceScore, location_id)
        """
        article_id = article_data.get('id', 0)
        title = article_data.get('title', '')
        
        # Use provided content or fall back to extract
        content = page_content or article_data.get('extract', '')
        
        # Step 1: Classify location using DSPy
        logger.info(f"Classifying location for: {title}")
        try:
            classification_result = self.classifier(
                page_title=title,
                page_content=content[:4000],  # Limit content
                html_hints=html_hints
            )
            
            # Convert DSPy result to LocationClassification model
            location_classification = self._dspy_to_classification(
                classification_result,
                article_id
            )
            
        except dspy.DSPyException as e:
            logger.error(f"DSPy classification failed for {title}: {e}")
            raise LLMException(f"Failed to classify location: {e}") from e
        except (ValueError, KeyError) as e:
            logger.warning(f"Data error in classification for {title}: {e}")
            # Create default classification for unknown location
            location_classification = LocationClassification(
                location_name=title,
                location_type="unknown",
                state="unknown",
                county="unknown",
                confidence=0.0,
                is_utah_california=False,
                should_flag=True,
                reasoning=f"Classification failed: {str(e)}"
            )
        
        # Step 2: Update database with location
        location_id = self.location_service.process_classification(
            location_classification,
            article_id
        )
        
        # Step 3: Evaluate relevance (flag if not Utah/California)
        relevance_score = self.relevance_filter.evaluate_with_location_classification(
            location_classification
        )
        
        # Set article_id in relevance score
        relevance_score.article_id = article_id
        
        # Log the result
        if location_classification.should_flag:
            logger.info(f"  ✗ FLAGGED: {title} - {location_classification.state} "
                       f"(not Utah/California)")
        else:
            logger.info(f"  ✓ KEPT: {title} - {location_classification.state} "
                       f"({location_classification.location_type})")
        
        return location_classification, relevance_score, location_id
    
    def _dspy_to_classification(self, dspy_result, article_id: int) -> LocationClassification:
        """Convert DSPy prediction to LocationClassification model."""
        # Extract fields from DSPy result
        return LocationClassification(
            location_name=getattr(dspy_result, 'location_name', 'unknown'),
            location_type=getattr(dspy_result, 'location_type', 'unknown'),
            location_type_category=getattr(dspy_result, 'location_type_category', 'other'),
            state=getattr(dspy_result, 'state', 'unknown'),
            county=getattr(dspy_result, 'county', 'unknown'),
            is_utah_california=getattr(dspy_result, 'is_utah_california', False),
            should_flag=getattr(dspy_result, 'should_flag', True),
            confidence=float(getattr(dspy_result, 'confidence', 0.0)),
            reasoning=getattr(dspy_result, 'reasoning', '')
        )
    
    def generate_report(self) -> Dict:
        """Generate comprehensive report on processing."""
        location_report = self.location_service.generate_report()
        
        # Add flagging statistics
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN relevance_category = 'flagged_for_removal' THEN 1 ELSE 0 END) as flagged,
                    SUM(CASE WHEN relevance_category = 'highly_relevant' THEN 1 ELSE 0 END) as highly_relevant,
                    SUM(CASE WHEN relevance_category = 'marginal_relevance' THEN 1 ELSE 0 END) as marginal
                FROM flagged_content
            """)
            
            row = cursor.fetchone()
            flagging_stats = {
                'total_evaluated': row[0] if row else 0,
                'flagged_for_removal': row[1] if row else 0,
                'highly_relevant': row[2] if row else 0,
                'marginal_relevance': row[3] if row else 0
            }
        
        return {
            'location_report': location_report,
            'flagging_stats': flagging_stats
        }