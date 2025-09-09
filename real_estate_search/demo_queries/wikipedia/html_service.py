"""
HTML service module for generating Wikipedia search reports.

This module handles HTML report generation, including transforming search
results to HTML format and managing browser opening.
"""

import subprocess
import platform
from pathlib import Path
from typing import List, Dict, Optional
from .models import (
    SearchResult,
    SearchStatistics,
    HtmlReportData,
    ArticleExportResult
)
from ...html_generators import WikipediaHTMLGenerator


class WikipediaHtmlService:
    """Service for generating HTML reports from Wikipedia search results."""
    
    def __init__(self, output_directory: str = "real_estate_search/out_html"):
        """Initialize the HTML service.
        
        Args:
            output_directory: Directory for saving HTML reports
        """
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(parents=True, exist_ok=True)
        self.html_generator = WikipediaHTMLGenerator()
    
    def generate_report(
        self,
        search_results: List[SearchResult],
        statistics: SearchStatistics,
        exported_articles: Dict[str, str] = None,
        title: str = "Wikipedia Full-Text Search Results",
        description: str = "Comprehensive full-text search across enriched Wikipedia articles"
    ) -> Optional[str]:
        """Generate HTML report from search results.
        
        Args:
            search_results: List of SearchResult objects
            statistics: Search statistics
            exported_articles: Mapping of page_id to filename
            title: Report title
            description: Report description
            
        Returns:
            Path to generated HTML file or None if failed
        """
        try:
            # Transform search results for HTML generation
            query_results = self._transform_results_for_html(
                search_results,
                exported_articles or {}
            )
            
            # Generate HTML using the existing generator
            html_path = self.html_generator.generate_from_demo_results(
                title=title,
                description=description,
                query_results=query_results
            )
            
            print(f"\n📄 HTML results saved to: {html_path}")
            print(f"   Open in browser: file://{html_path.absolute()}")
            
            return str(html_path)
            
        except Exception as e:
            print(f"\n⚠️  Could not generate HTML output: {str(e)}")
            return None
    
    def _transform_results_for_html(
        self,
        search_results: List[SearchResult],
        exported_articles: Dict[str, str]
    ) -> List[Dict]:
        """Transform SearchResult objects to format expected by HTML generator.
        
        Args:
            search_results: List of SearchResult objects
            exported_articles: Mapping of page_id to filename
            
        Returns:
            List of dictionaries formatted for HTML generation
        """
        transformed = []
        
        for result in search_results:
            # Create query result dictionary
            query_result = {
                "query": result.query.title,
                "description": result.query.description,
                "total_results": result.total_hits,
                "top_results": []
            }
            
            # Process hits
            for hit in result.hits[:3]:
                doc = hit.document
                page_id = str(doc.page_id) if doc.page_id else ""
                
                hit_data = {
                    "page_id": page_id,
                    "title": doc.title,
                    "score": hit.score,
                    "city": doc.city or "Unknown",
                    "categories": doc.categories,
                    "content_length": doc.content_length,
                    "has_full_content": doc.content_length is not None,
                    "url": doc.url or "",
                    "highlights": [],
                    "local_html_file": exported_articles.get(page_id)
                }
                
                # Extract highlights
                if 'full_content' in hit.highlights:
                    for fragment in hit.highlights['full_content'][:2]:
                        clean_fragment = ' '.join(fragment.split())
                        hit_data["highlights"].append(clean_fragment)
                
                query_result["top_results"].append(hit_data)
            
            transformed.append(query_result)
        
        return transformed
    
    def open_in_browser(self, html_path: str) -> bool:
        """Open HTML file in the default browser.
        
        Args:
            html_path: Path to HTML file
            
        Returns:
            True if successfully opened, False otherwise
        """
        try:
            system = platform.system()
            
            if system == 'Darwin':  # macOS
                subprocess.run(['open', html_path], check=False)
            elif system == 'Linux':
                subprocess.run(['xdg-open', html_path], check=False)
            elif system == 'Windows':
                subprocess.run(['start', html_path], shell=True, check=False)
            else:
                return False
            
            print(f"\n📂 HTML report opened in browser: {html_path}")
            return True
            
        except Exception as e:
            print(f"\n📂 HTML report saved to: {html_path}")
            print(f"   (Unable to auto-open: {e})")
            return False
    
    def create_summary_html(
        self,
        statistics: SearchStatistics,
        export_result: Optional[ArticleExportResult] = None
    ) -> str:
        """Create HTML summary section.
        
        Args:
            statistics: Search statistics
            export_result: Optional export results
            
        Returns:
            HTML string for summary section
        """
        html = ["<div class='summary'>"]
        html.append("<h2>Search Summary</h2>")
        html.append("<table class='stats-table'>")
        
        # Add statistics rows
        html.append(f"<tr><td>Queries Executed:</td><td>{statistics.total_queries}</td></tr>")
        html.append(f"<tr><td>Successful Queries:</td><td>{statistics.successful_queries}</td></tr>")
        html.append(f"<tr><td>Total Documents Found:</td><td>{statistics.total_documents_found}</td></tr>")
        html.append(f"<tr><td>Average Results per Query:</td><td>{statistics.average_results_per_query:.1f}</td></tr>")
        
        if export_result:
            html.append(f"<tr><td>Articles Exported:</td><td>{len(export_result.exported_articles)}</td></tr>")
            html.append(f"<tr><td>Total Export Size:</td><td>{export_result.total_size_kb:.1f} KB</td></tr>")
        
        html.append("</table>")
        
        # Add top documents section
        if statistics.top_documents:
            html.append("<h3>Top Scoring Documents</h3>")
            html.append("<ol class='top-docs'>")
            
            for doc in statistics.top_documents[:5]:
                html.append(f"<li>{doc.title} (Score: {doc.score:.2f})</li>")
            
            html.append("</ol>")
        
        html.append("</div>")
        return '\n'.join(html)