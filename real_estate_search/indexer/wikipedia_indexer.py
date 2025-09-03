"""
Wikipedia Indexer Module for Elasticsearch.

This module handles the enrichment and indexing of Wikipedia articles,
including HTML processing, pipeline management, and bulk operations.

Pipeline Processing Flow:
========================
1. Query Phase: Find Wikipedia documents needing enrichment
2. Load Phase: Read HTML content from disk
3. Transform Phase: Process through Elasticsearch ingest pipeline
4. Index Phase: Bulk update documents with processed content

Elasticsearch Ingest Pipeline Details:
======================================
The wikipedia_ingest_pipeline performs the following operations on each document:

1. HTML Strip Processor:
   - Removes all HTML tags from the full_content field
   - Preserves text content while removing markup
   - Handles nested tags and special HTML entities

2. Trim Processor:
   - Removes leading and trailing whitespace
   - Ensures clean text for indexing

3. Script Processor:
   - Sets content_loaded = true
   - Records content_loaded_at timestamp
   - Calculates content_length for the processed text

The pipeline is applied during bulk indexing, processing documents
server-side for optimal performance.
"""

import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Generator

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk, BulkIndexError
from pydantic import BaseModel, Field


class WikipediaDocument(BaseModel):
    """Represents a Wikipedia document in Elasticsearch."""
    id: str
    page_id: str
    title: str
    article_filename: Optional[str] = None
    content_loaded: bool = False
    full_content: Optional[str] = None
    
    @classmethod
    def from_es_hit(cls, hit: Dict[str, Any]) -> 'WikipediaDocument':
        """Create a WikipediaDocument from an Elasticsearch hit."""
        source = hit['_source']
        return cls(
            id=hit['_id'],
            page_id=source.get('page_id', ''),
            title=source.get('title', ''),
            article_filename=source.get('article_filename'),
            content_loaded=source.get('content_loaded', False),
            full_content=source.get('full_content')
        )


class WikipediaEnrichmentConfig(BaseModel):
    """Configuration for Wikipedia enrichment process."""
    batch_size: int = Field(default=50, ge=1, le=500, description="Batch size for bulk operations")
    max_documents: Optional[int] = Field(default=None, ge=1, description="Maximum documents to process")
    dry_run: bool = Field(default=False, description="Perform dry run without updating")
    data_dir: str = Field(default="data/wikipedia/pages", description="Data directory path")
    pipeline_name: str = Field(default="wikipedia_ingest_pipeline", description="Ingest pipeline name")
    index_name: str = Field(default="wikipedia", description="Wikipedia index name")
    scroll_timeout: str = Field(default="5m", description="Scroll timeout for queries")


class WikipediaEnrichmentResult(BaseModel):
    """Results from Wikipedia enrichment operation."""
    total_documents_scanned: int = Field(default=0, description="Total documents scanned")
    documents_needing_enrichment: int = Field(default=0, description="Documents needing enrichment")
    documents_enriched: int = Field(default=0, description="Successfully enriched documents")
    documents_failed: int = Field(default=0, description="Failed document count")
    files_not_found: List[str] = Field(default_factory=list, description="List of missing files")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    execution_time_ms: int = Field(default=0, description="Execution time in milliseconds")
    dry_run: bool = Field(default=False, description="Whether this was a dry run")


class WikipediaIndexer:
    """
    Manages Wikipedia article indexing and enrichment in Elasticsearch.
    
    This class handles:
    - Querying for documents needing enrichment
    - Loading HTML content from disk
    - Processing through Elasticsearch ingest pipeline
    - Bulk updating documents
    - Error handling and reporting
    
    Pipeline Architecture:
    ===================
    The indexer uses Elasticsearch's ingest pipeline feature for efficient
    document processing. The pipeline is applied server-side during bulk
    operations, reducing client-side processing overhead.
    
    Pipeline Definition:
    The wikipedia_ingest_pipeline is defined in:
    elasticsearch/pipelines/wikipedia_ingest.json
    
    Pipeline Processors:
    1. html_strip: Removes HTML tags while preserving text
    2. trim: Cleans whitespace
    3. script: Sets metadata fields (content_loaded, timestamps, length)
    
    Usage Example:
    =============
    ```python
    from elasticsearch import Elasticsearch
    from real_estate_search.indexer import WikipediaIndexer
    
    es = Elasticsearch(['localhost:9200'])
    config = WikipediaEnrichmentConfig(batch_size=100)
    
    indexer = WikipediaIndexer(es, config)
    result = indexer.enrich_documents()
    
    print(f"Enriched {result.documents_enriched} documents")
    ```
    """
    
    def __init__(self, es_client: Elasticsearch, config: WikipediaEnrichmentConfig):
        """
        Initialize the Wikipedia indexer.
        
        Args:
            es_client: Elasticsearch client instance
            config: Configuration for enrichment process
        """
        self.es = es_client
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.result = WikipediaEnrichmentResult()
    
    def query_documents_needing_enrichment(self) -> Generator[WikipediaDocument, None, None]:
        """
        Query Elasticsearch for Wikipedia documents needing enrichment.
        
        Documents need enrichment if they have:
        - article_filename field (indicating source file exists)
        - content_loaded = false or missing (not yet enriched)
        
        Yields:
            WikipediaDocument instances needing enrichment
        """
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"exists": {"field": "article_filename"}}
                    ],
                    "must_not": [
                        {"term": {"content_loaded": True}}
                    ]
                }
            },
            "_source": ["page_id", "title", "article_filename", "content_loaded"],
            "size": 1000
        }
        
        # Use scroll API for large result sets
        response = self.es.search(
            index=self.config.index_name,
            body=query,
            scroll=self.config.scroll_timeout
        )
        
        scroll_id = response['_scroll_id']
        hits = response['hits']['hits']
        
        while hits:
            for hit in hits:
                self.result.total_documents_scanned += 1
                doc = WikipediaDocument.from_es_hit(hit)
                if not doc.content_loaded and doc.article_filename:
                    self.result.documents_needing_enrichment += 1
                    yield doc
                    
                    if (self.config.max_documents and 
                        self.result.documents_needing_enrichment >= self.config.max_documents):
                        return
            
            # Get next batch
            response = self.es.scroll(scroll_id=scroll_id, scroll=self.config.scroll_timeout)
            hits = response['hits']['hits']
        
        # Clear scroll
        self.es.clear_scroll(scroll_id=scroll_id)
    
    def load_html_content(self, doc: WikipediaDocument) -> Optional[str]:
        """
        Load HTML content from disk for a Wikipedia document.
        
        Args:
            doc: WikipediaDocument with article_filename
            
        Returns:
            HTML content as string, or None if file not found
        """
        if not doc.article_filename:
            return None
        
        file_path = Path(self.config.data_dir) / doc.article_filename
        
        if not file_path.exists():
            self.logger.warning(f"File not found: {file_path}")
            self.result.files_not_found.append(str(file_path))
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Error reading {file_path}: {e}")
            self.result.errors.append(f"Read error for {file_path}: {str(e)}")
            return None
    
    def prepare_bulk_actions(self, documents: List[WikipediaDocument]) -> List[Dict[str, Any]]:
        """
        Prepare bulk update actions for Elasticsearch.
        
        This method creates update actions that will be processed through
        the wikipedia_ingest_pipeline. The pipeline will:
        1. Strip HTML tags from full_content
        2. Trim whitespace
        3. Set metadata fields (content_loaded, content_loaded_at, content_length)
        
        Args:
            documents: List of WikipediaDocument instances with HTML content
            
        Returns:
            List of bulk update actions for Elasticsearch
        """
        actions = []
        
        for doc in documents:
            if doc.full_content:
                action = {
                    "_op_type": "update",
                    "_index": self.config.index_name,
                    "_id": doc.id,
                    "doc": {
                        "full_content": doc.full_content
                        # The pipeline will set:
                        # - content_loaded: true
                        # - content_loaded_at: current timestamp
                        # - content_length: length of processed content
                    }
                }
                actions.append(action)
        
        return actions
    
    def process_batch(self, batch: List[WikipediaDocument]) -> int:
        """
        Process a batch of documents through the enrichment pipeline.
        
        Pipeline Processing:
        ===================
        1. Load HTML content from disk
        2. Create bulk update actions
        3. Apply wikipedia_ingest_pipeline during bulk indexing
        4. Pipeline processors execute server-side:
           - HTML stripping
           - Text trimming
           - Metadata setting
        
        Args:
            batch: List of WikipediaDocument instances
            
        Returns:
            Number of successfully processed documents
        """
        # Load HTML content for each document
        for doc in batch:
            html_content = self.load_html_content(doc)
            if html_content:
                doc.full_content = html_content
        
        # Filter documents with content
        docs_with_content = [d for d in batch if d.full_content]
        
        if not docs_with_content:
            return 0
        
        # Prepare bulk actions
        actions = self.prepare_bulk_actions(docs_with_content)
        
        if self.config.dry_run:
            self.logger.info(f"[DRY RUN] Would update {len(actions)} documents")
            return len(actions)
        
        # Execute bulk update with pipeline
        try:
            success, failed = bulk(
                self.es,
                actions,
                pipeline=self.config.pipeline_name,  # Apply wikipedia_ingest_pipeline
                stats_only=True,  # Return counts only, not full responses
                raise_on_error=False  # Continue on partial failures
            )
            
            if failed > 0:
                self.logger.warning(f"Failed to update {failed} documents in batch")
                self.result.documents_failed += failed
            
            self.result.documents_enriched += success
            return success
            
        except BulkIndexError as e:
            self.logger.error(f"Bulk indexing error: {e}")
            self.result.errors.append(f"Bulk error: {str(e)}")
            self.result.documents_failed += len(actions)
            return 0
        except Exception as e:
            self.logger.error(f"Unexpected error during bulk update: {e}")
            self.result.errors.append(f"Unexpected error: {str(e)}")
            self.result.documents_failed += len(actions)
            return 0
    
    def enrich_documents(self) -> WikipediaEnrichmentResult:
        """
        Main entry point for enriching Wikipedia documents.
        
        Complete Enrichment Flow:
        ========================
        1. Query Phase:
           - Find documents with article_filename but no content_loaded
           - Use scroll API for efficient large-scale queries
        
        2. Batch Processing:
           - Process documents in configurable batches
           - Load HTML content from disk
           - Prepare bulk update actions
        
        3. Pipeline Processing:
           - Bulk updates sent to Elasticsearch with pipeline parameter
           - wikipedia_ingest_pipeline processes each document:
             * Strips HTML tags
             * Trims whitespace
             * Sets metadata fields
        
        4. Result Tracking:
           - Track success/failure counts
           - Record execution time
           - Log errors and missing files
        
        Returns:
            WikipediaEnrichmentResult with operation statistics
        """
        start_time = time.time()
        self.result.dry_run = self.config.dry_run
        
        self.logger.info(f"Starting Wikipedia enrichment (dry_run={self.config.dry_run})")
        
        try:
            # Process documents in batches
            batch = []
            for doc in self.query_documents_needing_enrichment():
                batch.append(doc)
                
                if len(batch) >= self.config.batch_size:
                    self.process_batch(batch)
                    batch = []
            
            # Process remaining documents
            if batch:
                self.process_batch(batch)
            
            # Calculate execution time
            self.result.execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Log summary
            self.logger.info(
                f"Enrichment complete: {self.result.documents_enriched} documents enriched, "
                f"{self.result.documents_failed} failed"
            )
            
            return self.result
            
        except Exception as e:
            self.logger.error(f"Enrichment failed: {e}")
            self.result.errors.append(f"Fatal error: {str(e)}")
            self.result.execution_time_ms = int((time.time() - start_time) * 1000)
            return self.result
    
    def verify_pipeline_exists(self) -> bool:
        """
        Verify that the wikipedia_ingest_pipeline exists in Elasticsearch.
        
        Returns:
            True if pipeline exists, False otherwise
        """
        try:
            self.es.ingest.get_pipeline(id=self.config.pipeline_name)
            return True
        except Exception:
            return False
    
    def create_pipeline(self, pipeline_definition: Dict[str, Any]) -> bool:
        """
        Create or update the wikipedia_ingest_pipeline in Elasticsearch.
        
        Args:
            pipeline_definition: Pipeline configuration dict
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.es.ingest.put_pipeline(
                id=self.config.pipeline_name,
                body=pipeline_definition
            )
            self.logger.info(f"Created/updated pipeline: {self.config.pipeline_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create pipeline: {e}")
            return False
    
    def get_pipeline_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get statistics for the wikipedia_ingest_pipeline.
        
        Returns:
            Pipeline statistics dict, or None if error
        """
        try:
            stats = self.es.ingest.stats()
            return stats.get('pipelines', {}).get(self.config.pipeline_name)
        except Exception as e:
            self.logger.error(f"Failed to get pipeline stats: {e}")
            return None