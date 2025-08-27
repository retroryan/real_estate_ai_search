"""
HTML Results Generator

Clean, modular generator for creating HTML output from search results.
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from jinja2 import Template
import logging

from .models import (
    HTMLSearchResult,
    HTMLQueryResult,
    HTMLDocument,
    HTMLHighlight
)
from .template import HTML_TEMPLATE

logger = logging.getLogger(__name__)


class HTMLResultsGenerator:
    """Generator for creating HTML output from search results."""
    
    def __init__(self, output_dir: Path = None):
        """
        Initialize the HTML generator.
        
        Args:
            output_dir: Directory to save HTML files (default: real_estate_search/out_html)
        """
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "out_html"
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.template = Template(HTML_TEMPLATE)
    
    def generate_from_demo_results(
        self,
        title: str,
        description: str,
        query_results: List[Dict[str, Any]]
    ) -> Path:
        """
        Generate HTML from demo query results.
        
        Args:
            title: Title for the HTML page
            description: Description of the search demo
            query_results: List of query results from the demo
            
        Returns:
            Path to the generated HTML file
        """
        # Convert raw results to Pydantic models
        html_queries = []
        total_docs = 0
        
        for result in query_results:
            # Create HTMLDocument objects for each result
            documents = []
            for doc_data in result.get('top_results', []):
                # Extract highlights if available
                highlights = []
                if 'highlights' in doc_data:
                    for highlight_text in doc_data['highlights']:
                        highlights.append(HTMLHighlight(text=highlight_text))
                
                doc = HTMLDocument(
                    id=str(doc_data.get('page_id', doc_data.get('title', 'unknown'))),
                    title=doc_data.get('title', 'Unknown'),
                    score=doc_data.get('score', 0.0),
                    categories=doc_data.get('categories', []),
                    location=doc_data.get('city'),
                    content_length=doc_data.get('content_length'),
                    highlights=highlights,
                    summary=doc_data.get('summary'),
                    url=doc_data.get('url')  # Add URL for Wikipedia links
                )
                documents.append(doc)
            
            query = HTMLQueryResult(
                query_title=result.get('query', 'Unknown Query'),
                query_description=result.get('description', ''),
                total_results=result.get('total_results', 0),
                documents=documents,
                execution_time_ms=result.get('execution_time_ms')
            )
            html_queries.append(query)
            total_docs += query.total_results
        
        # Create the complete result object
        search_result = HTMLSearchResult(
            title=title,
            description=description,
            queries=html_queries,
            total_documents_found=total_docs
        )
        
        # Generate and save HTML
        return self.generate_html(search_result)
    
    def generate_html(self, search_result: HTMLSearchResult) -> Path:
        """
        Generate HTML file from search results.
        
        Args:
            search_result: The complete search result to render
            
        Returns:
            Path to the generated HTML file
        """
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"wikipedia_search_results_{timestamp}.html"
        filepath = self.output_dir / filename
        
        # Prepare template context
        context = {
            'title': search_result.title,
            'description': search_result.description,
            'total_queries': search_result.total_queries,
            'successful_queries': search_result.successful_queries,
            'total_documents_found': search_result.total_documents_found,
            'average_results': search_result.average_results_per_query,
            'formatted_timestamp': search_result.formatted_timestamp,
            'queries': search_result.queries,
            'top_documents': search_result.get_top_documents(5)
        }
        
        # Render the template
        html_content = self.template.render(**context)
        
        # Save to file
        filepath.write_text(html_content, encoding='utf-8')
        logger.info(f"Generated HTML results at: {filepath}")
        
        return filepath
    
    @staticmethod
    def process_elasticsearch_highlights(hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process Elasticsearch hits to extract clean highlights.
        
        Args:
            hits: Elasticsearch hit objects
            
        Returns:
            Processed results with clean highlights
        """
        results = []
        
        for hit in hits:
            doc = hit['_source']
            result = {
                'page_id': doc.get('page_id'),
                'title': doc.get('title', 'Unknown'),
                'score': hit.get('_score', 0.0),
                'city': doc.get('best_city'),
                'categories': doc.get('categories', []),
                'content_length': doc.get('content_length'),
                'highlights': []
            }
            
            # Process highlights
            if 'highlight' in hit and 'full_content' in hit['highlight']:
                for fragment in hit['highlight']['full_content'][:2]:
                    # Clean up the highlight - convert <em> to ** for emphasis
                    clean_text = fragment.replace('<em>', '**').replace('</em>', '**')
                    # Remove excessive whitespace
                    clean_text = ' '.join(clean_text.split())
                    result['highlights'].append(clean_text)
            
            results.append(result)
        
        return results