"""
Article export module for Wikipedia documents.

This module handles exporting Wikipedia articles from Elasticsearch to local
HTML files, including batch processing and file system operations.
"""

from pathlib import Path
from typing import List, Dict, Optional
from elasticsearch import Elasticsearch
from .models import (
    ArticleExport,
    ArticleExportResult,
    SearchResult
)
from ...models.wikipedia import WikipediaArticle


class WikipediaArticleExporter:
    """Exporter for Wikipedia articles from Elasticsearch."""
    
    def __init__(
        self,
        es_client: Elasticsearch,
        output_directory: str = "real_estate_search/out_html"
    ):
        """Initialize the article exporter.
        
        Args:
            es_client: Elasticsearch client instance
            output_directory: Directory for saving exported articles
        """
        self.es_client = es_client
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(parents=True, exist_ok=True)
    
    def export_articles(
        self,
        page_ids: List[str],
        max_articles: int = 10,
        index: str = "wikipedia"
    ) -> ArticleExportResult:
        """Export Wikipedia articles to HTML files.
        
        Args:
            page_ids: List of Wikipedia page IDs to export
            max_articles: Maximum number of articles to export
            index: Elasticsearch index name
            
        Returns:
            ArticleExportResult with export details
        """
        exported_articles = []
        failed_exports = []
        total_size_kb = 0.0
        
        # Limit to max_articles
        page_ids_to_export = page_ids[:max_articles]
        
        print(f"\n📥 Exporting Wikipedia articles to {self.output_directory}/")
        print("-" * 60)
        
        for page_id in page_ids_to_export:
            export = self._export_single_article(page_id, index)
            
            if export:
                exported_articles.append(export)
                total_size_kb += export.file_size_kb
                print(f"✅ Exported: {export.title[:50]} ({export.file_size_kb:.1f} KB)")
            else:
                failed_exports.append(page_id)
                print(f"❌ Failed to export article with ID: {page_id}")
        
        print(f"\n✅ Successfully exported {len(exported_articles)} articles")
        
        return ArticleExportResult(
            exported_articles=exported_articles,
            failed_exports=failed_exports,
            output_directory=str(self.output_directory),
            total_size_kb=total_size_kb
        )
    
    def _export_single_article(
        self,
        page_id: str,
        index: str
    ) -> Optional[ArticleExport]:
        """Export a single Wikipedia article.
        
        Args:
            page_id: Wikipedia page ID
            index: Elasticsearch index name
            
        Returns:
            ArticleExport if successful, None otherwise
        """
        try:
            # Fetch document from Elasticsearch
            result = self.es_client.get(
                index=index,
                id=page_id,
                _source=['title', 'full_content', 'url', 'content_length']
            )
            
            if not result or '_source' not in result:
                return None
            
            doc = result['_source']
            
            # Extract document fields
            title = doc.get('title', 'Unknown')
            full_content = doc.get('full_content', '')
            url = doc.get('url', '')
            content_length = doc.get('content_length', 0)
            
            if not full_content:
                return None
            
            # Generate filename
            filename = self._generate_filename(title, page_id)
            filepath = self.output_directory / filename
            
            # Create HTML content
            html_content = self._create_html_content(
                title=title,
                content=full_content,
                url=url,
                content_length=content_length,
                page_id=page_id
            )
            
            # Save to file
            filepath.write_text(html_content, encoding='utf-8')
            file_size_kb = filepath.stat().st_size / 1024
            
            return ArticleExport(
                page_id=page_id,
                title=title,
                filename=filename,
                filepath=str(filepath),
                file_size_kb=file_size_kb,
                content_length=content_length,
                url=url
            )
            
        except Exception as e:
            print(f"   Error exporting article {page_id}: {str(e)}")
            return None
    
    def _generate_filename(self, title: str, page_id: str) -> str:
        """Generate a safe filename for the article.
        
        Args:
            title: Article title
            page_id: Wikipedia page ID
            
        Returns:
            Safe filename string
        """
        # Clean title for filename
        safe_title = "".join(
            c for c in title 
            if c.isalnum() or c in (' ', '-', '_')
        ).rstrip()
        safe_title = safe_title.replace(' ', '_')[:100]
        
        return f"wikipedia_{safe_title}_{page_id}.html"
    
    def _create_html_content(
        self,
        title: str,
        content: str,
        url: str,
        content_length: int,
        page_id: str
    ) -> str:
        """Create HTML content for the exported article.
        
        Args:
            title: Article title
            content: Full article content
            url: Wikipedia URL
            content_length: Content character count
            page_id: Wikipedia page ID
            
        Returns:
            Complete HTML document string
        """
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Wikipedia</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{
            border-bottom: 3px solid #a2a9b1;
            padding-bottom: 10px;
        }}
        .metadata {{
            background: #f8f9fa;
            border: 1px solid #a2a9b1;
            border-radius: 4px;
            padding: 10px;
            margin-bottom: 20px;
            font-size: 0.9em;
        }}
        .content {{
            background: white;
            padding: 20px;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="metadata">
        <p><strong>Source:</strong> Elasticsearch Index</p>
        <p><strong>Original URL:</strong> <a href="{url}" target="_blank">{url}</a></p>
        <p><strong>Content Size:</strong> {content_length:,} characters</p>
        <p><strong>Page ID:</strong> {page_id}</p>
    </div>
    <div class="content">
        {content}
    </div>
</body>
</html>"""
    
    def get_unique_page_ids_from_results(
        self,
        search_results: List[SearchResult]
    ) -> List[str]:
        """Extract unique page IDs from search results.
        
        Args:
            search_results: List of SearchResult objects
            
        Returns:
            List of unique page IDs
        """
        unique_ids = set()
        
        for result in search_results:
            for hit in result.hits[:3]:
                if hit.document.page_id:
                    unique_ids.add(str(hit.document.page_id))
        
        return list(unique_ids)
    
    def create_export_mapping(
        self,
        export_result: ArticleExportResult
    ) -> Dict[str, str]:
        """Create mapping of page_id to filename.
        
        Args:
            export_result: ArticleExportResult
            
        Returns:
            Dictionary mapping page_id to filename
        """
        return {
            article.page_id: article.filename
            for article in export_result.exported_articles
        }