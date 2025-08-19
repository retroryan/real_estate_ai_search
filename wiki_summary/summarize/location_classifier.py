"""
DSPy Chain-of-Thought module for flexible location classification.
Classifies Wikipedia articles by geographic entity type without constraints.
"""

import dspy
import logging
from typing import Optional
from wiki_summary.summarize.signatures import ExtractLocationClassification
from wiki_summary.exceptions import LLMException

logger = logging.getLogger(__name__)


class LocationClassificationCoT(dspy.Module):
    """DSPy Chain-of-Thought module for flexible location classification."""
    
    def __init__(self, use_chain_of_thought: bool = True):
        """Initialize the location classifier.
        
        Args:
            use_chain_of_thought: Whether to use CoT reasoning (recommended)
        """
        super().__init__()
        
        if use_chain_of_thought:
            self.classify = dspy.ChainOfThought(ExtractLocationClassification)
        else:
            self.classify = dspy.Predict(ExtractLocationClassification)
    
    def forward(self, 
                page_title: str, 
                page_content: str, 
                html_hints: Optional[str] = None) -> dspy.Prediction:
        """Classify a Wikipedia article's location type.
        
        Args:
            page_title: Title of the Wikipedia page
            page_content: Article content (first 4000 chars recommended)
            html_hints: Optional HTML-extracted location hints
            
        Returns:
            DSPy Prediction with location classification fields
        """
        # Truncate content if too long
        if len(page_content) > 4000:
            page_content = page_content[:4000]
        
        # Run classification with enhanced logging
        logger.debug(f"Starting location classification for: {page_title}")
        logger.debug(f"Content length: {len(page_content)}, HTML hints: {bool(html_hints)}")
        
        try:
            result = self.classify(
                page_title=page_title,
                page_content=page_content,
                html_hints=html_hints or "No HTML hints available"
            )
            logger.debug(f"Location classification successful for: {page_title}")
            
            # Validate result has expected fields
            expected_fields = ['location_name', 'location_type', 'state', 'county']
            missing_fields = [field for field in expected_fields if not hasattr(result, field)]
            if missing_fields:
                logger.warning(f"Classification result missing fields for {page_title}: {missing_fields}")
                
            return result
            
        except dspy.DSPyException as e:
            logger.error(f"DSPy classification failed for {page_title}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in classification for {page_title}: {type(e).__name__}: {e}")
            raise


class LocationClassificationBatch(dspy.Module):
    """Batch processor for multiple location classifications."""
    
    def __init__(self):
        super().__init__()
        self.classifier = LocationClassificationCoT(use_chain_of_thought=True)
    
    def forward(self, articles: list) -> list:
        """Process multiple articles.
        
        Args:
            articles: List of dicts with 'title' and 'content' keys
            
        Returns:
            List of classification results
        """
        results = []
        for article in articles:
            try:
                result = self.classifier(
                    page_title=article.get('title', ''),
                    page_content=article.get('content', ''),
                    html_hints=article.get('html_hints')
                )
                results.append(result)
            except dspy.DSPyException as e:
                # Log DSPy error but continue processing batch
                logger.error(f"DSPy error classifying {article.get('title')}: {e}")
                results.append(None)
            except (KeyError, ValueError) as e:
                # Log data error but continue processing batch
                logger.warning(f"Data error classifying {article.get('title')}: {e}")
                results.append(None)
        
        return results