"""
Wikipedia data loader for HTML articles.

Simplified version of wiki_embed/utils/wiki_utils.py load_wikipedia_articles.
"""

import re
from pathlib import Path
from typing import List, Optional
from llama_index.core import Document

from ..utils.logging import get_logger
from ..models.interfaces import IDataLoader


logger = get_logger(__name__)


class WikipediaLoader(IDataLoader):
    """
    Loads Wikipedia articles from HTML files.
    
    Simplified version of wiki_embed patterns for demo purposes.
    """
    
    def __init__(self, data_dir: Path, max_articles: Optional[int] = None):
        """
        Initialize Wikipedia loader.
        
        Args:
            data_dir: Directory containing wikipedia/pages/ subdirectory
            max_articles: Maximum articles to load (None for all)
        """
        self.data_dir = data_dir
        self.max_articles = max_articles
        self.pages_dir = data_dir / "wikipedia" / "pages"
        
    def load_all(self) -> List[Document]:
        """
        Load Wikipedia articles from HTML files.
        
        Returns:
            List of Document objects
        """
        documents = []
        
        if not self.pages_dir.exists():
            logger.warning(f"Wikipedia pages directory not found: {self.pages_dir}")
            return documents
        
        # Load HTML files
        html_files = list(self.pages_dir.glob("*.html"))
        logger.info(f"Found {len(html_files)} Wikipedia HTML files")
        
        if self.max_articles:
            html_files = html_files[:self.max_articles]
            logger.info(f"Loading only first {self.max_articles} articles")
        
        for html_file in html_files:
            try:
                document = self._process_html_file(html_file)
                if document:
                    documents.append(document)
            except Exception as e:
                logger.error(f"Error processing {html_file.name}: {e}")
                continue
        
        logger.info(f"Successfully loaded {len(documents)} Wikipedia articles")
        return documents
    
    def _process_html_file(self, html_file: Path) -> Optional[Document]:
        """
        Process a single HTML file into a Document.
        
        Args:
            html_file: Path to HTML file
            
        Returns:
            Document object or None if processing fails
        """
        # Extract page_id from filename (e.g., "107778_a18e0a44.html" -> "107778")
        page_id = html_file.stem.split('_')[0]
        
        # Read HTML content
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Simple text extraction (basic version without BeautifulSoup)
        # In production, use wiki_embed's clean_wikipedia_text function
        text = self._clean_html_text(html_content)
        
        # Create document
        return Document(
            text=text,
            metadata={
                "page_id": page_id,
                "source_file": str(html_file),
                "title": html_file.stem  # Simplified title
            }
        )
    
    def _clean_html_text(self, html_content: str, max_length: int = 10000) -> str:
        """
        Basic HTML cleanup for demo purposes.
        
        Args:
            html_content: Raw HTML content
            max_length: Maximum text length
            
        Returns:
            Clean text suitable for embedding
        """
        # Remove HTML tags
        text = re.sub('<[^<]+?>', '', html_content)
        
        # Clean whitespace
        text = ' '.join(text.split())
        
        # Remove common Wikipedia artifacts
        text = re.sub(r'\\[edit\\]', '', text)
        text = re.sub(r'\\[\\d+\\]', '', text)
        
        # Limit length
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text.strip()
    
    # IDataLoader interface implementation
    def load_documents(self):
        """Load documents generator (interface compliance)."""
        documents = self.load_all()
        for doc in documents:
            yield doc
    
    def get_source_type(self) -> str:
        """Get source type identifier."""
        return "wikipedia_html"
    
    def validate_source(self) -> bool:
        """Validate data source exists."""
        return self.pages_dir.exists() and any(self.pages_dir.glob("*.html"))