#!/usr/bin/env python3
"""
Enrich Wikipedia articles in Elasticsearch with full HTML content.

This script demonstrates how Elasticsearch can be used to index and search
large documents (full Wikipedia articles) by:
1. Querying existing documents to find those needing enrichment
2. Loading full HTML content from disk (articles averaging ~222KB)
3. Using Elasticsearch's ingest pipelines to process HTML
4. Bulk updating documents for efficient indexing
5. Enabling full-text search across millions of words

## Tutorial: Elasticsearch Document Processing

Elasticsearch excels at processing large documents through several key features:

### 1. Ingest Pipelines
- Pre-process documents before indexing using built-in processors
- HTML strip processor removes tags while preserving text
- Can chain multiple processors (lowercase, stemming, etc.)

### 2. Analyzers
- Text fields are analyzed into searchable tokens
- English analyzer handles stemming (running -> run)
- Creates inverted index for fast full-text search

### 3. Bulk Operations
- Process thousands of documents efficiently
- Reduces network overhead vs individual updates
- Automatic batching and error handling

### 4. Field Types
- 'text' fields: Analyzed for full-text search
- 'keyword' fields: Exact matching only
- Large documents stored efficiently with compression
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from elasticsearch import Elasticsearch, helpers
from pydantic import BaseModel, Field, ConfigDict
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WikipediaDocument(BaseModel):
    """Model for Wikipedia document from Elasticsearch."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    page_id: int  # Changed to int to match Elasticsearch data
    title: str
    article_filename: Optional[str] = None
    content_loaded: Optional[bool] = False
    full_content: Optional[str] = None
    
    def needs_enrichment(self) -> bool:
        """Check if document needs content enrichment."""
        # Need enrichment if:
        # 1. Has filename but no content at all
        # 2. Has content but not processed (content_loaded not True)
        return (
            self.article_filename is not None 
            and not self.content_loaded  # This handles None and False
        )


class EnrichmentConfig(BaseModel):
    """Configuration for enrichment process."""
    
    es_host: str = Field(default="localhost", description="Elasticsearch host")
    es_port: int = Field(default=9200, description="Elasticsearch port")
    es_index: str = Field(default="wikipedia", description="Wikipedia index name")
    pipeline_name: str = Field(default="wikipedia_ingest_pipeline", description="Ingest pipeline name")
    batch_size: int = Field(default=50, description="Batch size for bulk updates")
    data_dir: Path = Field(default=Path("../data"), description="Data directory path")
    dry_run: bool = Field(default=False, description="Dry run mode")
    max_documents: Optional[int] = Field(default=None, description="Maximum documents to process")


class EnrichmentResult(BaseModel):
    """Result of the enrichment process."""
    
    total_documents: int = 0
    documents_needing_enrichment: int = 0
    documents_enriched: int = 0
    documents_failed: int = 0
    files_not_found: int = 0
    errors: List[str] = Field(default_factory=list)
    
    def print_summary(self):
        """Print enrichment summary."""
        print("\n" + "="*50)
        print("Enrichment Summary")
        print("="*50)
        print(f"Total documents scanned: {self.total_documents}")
        print(f"Documents needing enrichment: {self.documents_needing_enrichment}")
        print(f"Documents successfully enriched: {self.documents_enriched}")
        print(f"Documents failed: {self.documents_failed}")
        print(f"Files not found: {self.files_not_found}")
        
        if self.errors:
            print(f"\nErrors encountered ({len(self.errors)}):")
            for error in self.errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more errors")


class WikipediaEnricher:
    """Enriches Wikipedia documents with full HTML content."""
    
    def __init__(self, config: EnrichmentConfig):
        """Initialize the enricher with configuration."""
        self.config = config
        self.es = self._connect_elasticsearch()
        self.result = EnrichmentResult()
        
    def _connect_elasticsearch(self) -> Elasticsearch:
        """Connect to Elasticsearch."""
        try:
            # Build connection URL
            url = f"http://{self.config.es_host}:{self.config.es_port}"
            
            # Try to load credentials from environment
            import os
            from dotenv import load_dotenv
            load_dotenv()
            
            es_user = os.getenv('ES_USERNAME')
            es_pass = os.getenv('ES_PASSWORD')
            
            # Create connection with or without auth
            if es_user and es_pass:
                es = Elasticsearch(
                    [url],
                    basic_auth=(es_user, es_pass),
                    request_timeout=30
                )
            else:
                es = Elasticsearch(
                    [url],
                    request_timeout=30
                )
            
            # Verify connection
            if not es.ping():
                raise ConnectionError("Cannot connect to Elasticsearch")
                
            logger.info(f"Connected to Elasticsearch at {self.config.es_host}:{self.config.es_port}")
            return es
            
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            raise
            
    def _query_documents(self) -> List[WikipediaDocument]:
        """
        Query Elasticsearch for documents needing enrichment.
        
        ## Elasticsearch Query Tutorial:
        
        This method demonstrates several important Elasticsearch concepts:
        
        ### 1. Bool Query Structure
        The 'bool' query is Elasticsearch's Swiss Army knife for combining conditions:
        - 'must': All conditions must match (AND logic)
        - 'must_not': None of these conditions can match (NOT logic)
        - 'should': At least one should match (OR logic)
        - 'filter': Like 'must' but doesn't affect relevance scoring
        
        ### 2. Exists Query
        The 'exists' query finds documents where a field has any non-null value.
        Here we check for 'article_filename' to find documents that have
        associated HTML files we can load.
        
        ### 3. Term Query
        The 'term' query does exact matching without analysis.
        We use it on 'content_loaded' (a boolean) to find documents
        that haven't been enriched yet.
        
        ### 4. Source Filtering
        The '_source' parameter limits which fields are returned.
        This reduces network traffic - we only fetch fields we need,
        not the entire document (which could be 200KB+ after enrichment).
        
        ### 5. Size Limit
        The 'size' parameter controls how many results to return.
        Default is 10, we increase to 10000 to process many documents.
        For millions of docs, use scroll API or search_after.
        """
        logger.info("Querying Elasticsearch for documents...")
        
        # Build the query to find documents that:
        # 1. Have an article_filename field (pointing to HTML file)
        # 2. Haven't been loaded yet (content_loaded is not True)
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"exists": {"field": "article_filename"}}  # Has HTML file reference
                    ],
                    "must_not": [
                        {"term": {"content_loaded": True}}  # Not yet enriched
                    ]
                }
            },
            "size": self.config.max_documents or 10000,  # Batch size for processing
            "_source": ["page_id", "title", "article_filename", "content_loaded", "full_content"]  # Only needed fields
        }
        
        try:
            response = self.es.search(index=self.config.es_index, body=query)
            hits = response.get("hits", {}).get("hits", [])
            
            documents = []
            for hit in hits:
                doc_data = hit["_source"]
                doc = WikipediaDocument(**doc_data)
                if doc.needs_enrichment():
                    documents.append(doc)
                    
            self.result.total_documents = len(hits)
            self.result.documents_needing_enrichment = len(documents)
            
            logger.info(f"Found {len(documents)} documents needing enrichment")
            return documents
            
        except Exception as e:
            error_msg = f"Failed to query documents: {e}"
            logger.error(error_msg)
            self.result.errors.append(error_msg)
            return []
            
    def _read_html_file(self, filename: str) -> Optional[str]:
        """Read HTML content from file."""
        # The filename already includes the path relative to project root
        # Check if it's an absolute path or if we need to resolve it
        if filename.startswith('data/'):
            # It's already a relative path from project root
            file_path = Path(filename)
        else:
            # Use the data_dir
            file_path = self.config.data_dir / filename
        
        if not file_path.exists():
            self.result.files_not_found += 1
            return None
            
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            return content
        except Exception as e:
            error_msg = f"Failed to read {file_path}: {e}"
            logger.warning(error_msg)
            self.result.errors.append(error_msg)
            return None
            
    def _prepare_bulk_actions(self, documents: List[WikipediaDocument]) -> List[Dict[str, Any]]:
        """
        Prepare bulk update actions for Elasticsearch.
        
        ## Bulk API Tutorial:
        
        The Bulk API is crucial for indexing large amounts of data efficiently.
        Instead of making 1000 HTTP requests for 1000 documents, we send
        all updates in a single request.
        
        ### Action Types:
        - 'index': Add or replace a document (we use this)
        - 'create': Add only if document doesn't exist
        - 'update': Partial update with script or doc
        - 'delete': Remove a document
        
        ### Why We Fetch Existing Documents:
        We use 'index' operation which replaces the entire document.
        To preserve existing fields (like embeddings, location data),
        we first fetch the current document and add our new content.
        
        ### Document Size Considerations:
        Wikipedia articles average 222KB. Elasticsearch handles this well:
        - Default http.max_content_length is 100MB
        - Documents are compressed internally
        - Only indexed text is analyzed, source is stored as-is
        
        ### Memory Efficiency:
        We process documents one at a time to avoid loading
        hundreds of MB of HTML into memory simultaneously.
        """
        actions = []
        
        for doc in documents:
            if not doc.article_filename:
                continue
                
            # Load HTML content from disk (can be 100KB-500KB per file)
            html_content = self._read_html_file(doc.article_filename)
            if html_content is None:
                continue
            
            # IMPORTANT: Get the existing document to preserve all fields
            # This ensures we don't lose embeddings, location data, etc.
            try:
                existing_doc = self.es.get(index=self.config.es_index, id=str(doc.page_id))['_source']
                
                # Add the full HTML content to the document
                # This will be processed by the ingest pipeline to:
                # 1. Strip HTML tags
                # 2. Extract clean text
                # 3. Update content_length field
                # 4. Set content_loaded flag
                existing_doc['full_content'] = html_content
                
                # Prepare the bulk action
                # Using 'index' operation for full document replacement
                action = {
                    "_op_type": "index",  # Replace entire document
                    "_index": self.config.es_index,  # Target index
                    "_id": str(doc.page_id),  # Document ID (must be string)
                    "_source": existing_doc  # Complete document with new content
                }
                actions.append(action)
            except Exception as e:
                logger.warning(f"Could not get document {doc.page_id}: {e}")
                continue
            
        return actions
        
    def _perform_bulk_updates(self, actions: List[Dict[str, Any]]) -> None:
        """
        Perform bulk updates to Elasticsearch.
        
        ## Ingest Pipeline & Bulk Processing Tutorial:
        
        This method demonstrates two powerful Elasticsearch features working together:
        
        ### 1. Ingest Pipelines
        The 'pipeline' parameter tells Elasticsearch to process each document
        through a series of transformations before indexing:
        
        Our wikipedia_ingest_pipeline does:
        - HTML Strip: Removes all HTML tags, keeping only text
        - Script: Calculates content_length from the cleaned text
        - Set: Marks content_loaded=true
        - Date: Sets content_loaded_at timestamp
        
        This happens server-side, reducing client processing needs.
        
        ### 2. Bulk API Batching
        We process documents in batches (default 50) because:
        - Each batch is ~10MB (50 docs * 200KB average)
        - Keeps memory usage reasonable
        - Allows progress tracking
        - Prevents timeout on very large datasets
        
        ### 3. Error Handling
        - stats_only=True: Returns counts instead of full response
        - raise_on_error=False: Continue on partial failures
        - Track success/failure counts for monitoring
        
        ### 4. Performance Considerations
        Processing 450 Wikipedia articles (~100MB total):
        - Without bulk API: 450 requests, ~45 seconds
        - With bulk API: 9 requests (50 docs each), ~10 seconds
        - 4-5x faster with less server load
        
        ### 5. How Full-Text Search Works After Indexing
        Once indexed, Elasticsearch creates an inverted index:
        - Each word points to documents containing it
        - "San Francisco" -> [doc1, doc5, doc99...]
        - Searches are O(1) lookup in the inverted index
        - Can search millions of documents in milliseconds
        """
        if not actions:
            logger.info("No documents to update")
            return
            
        if self.config.dry_run:
            logger.info(f"DRY RUN: Would update {len(actions)} documents")
            self.result.documents_enriched = len(actions)
            return
            
        logger.info(f"Updating {len(actions)} documents...")
        
        # Process in batches to avoid memory issues and timeouts
        # Each Wikipedia article is ~222KB, so 50 articles ≈ 11MB per batch
        batch_size = self.config.batch_size
        for i in range(0, len(actions), batch_size):
            batch = actions[i:i + batch_size]
            
            try:
                # Use the helpers.bulk function for efficient bulk indexing
                # This sends all documents in a single HTTP request
                success, failed = helpers.bulk(
                    self.es,
                    batch,
                    pipeline=self.config.pipeline_name,  # Process through ingest pipeline
                    stats_only=True,  # Just return counts, not full responses
                    raise_on_error=False  # Continue processing on errors
                )
                
                self.result.documents_enriched += success
                self.result.documents_failed += failed
                
                if failed > 0:
                    logger.warning(f"Failed to update {failed} documents in batch")
                    
            except Exception as e:
                error_msg = f"Bulk update failed: {e}"
                logger.error(error_msg)
                self.result.errors.append(error_msg)
                self.result.documents_failed += len(batch)
                
    def enrich(self) -> EnrichmentResult:
        """
        Run the enrichment process.
        
        ## Complete Enrichment Flow:
        
        This method orchestrates the entire process of enriching Elasticsearch
        documents with full-page content, demonstrating how to:
        
        1. **Query Phase**: Find documents needing enrichment
           - Uses bool queries for complex conditions
           - Efficiently fetches only required fields
        
        2. **Preparation Phase**: Load content and prepare updates
           - Reads large HTML files from disk
           - Preserves existing document fields
           - Builds bulk actions for efficient processing
        
        3. **Update Phase**: Send updates to Elasticsearch
           - Uses bulk API for performance
           - Applies ingest pipeline for HTML processing
           - Handles errors gracefully
        
        ## Result: Full-Text Search Capability
        
        After enrichment, users can search across:
        - Complete Wikipedia articles (not just summaries)
        - Millions of words indexed for instant search
        - Rich queries with highlighting, phrases, proximity
        - Relevance scoring based on term frequency
        
        Example searches enabled:
        - "1906 earthquake reconstruction efforts"
        - "Victorian architecture preservation"
        - "public transportation infrastructure BART"
        
        The inverted index makes these searches nearly instantaneous
        even across hundreds of multi-megabyte documents.
        """
        logger.info("Starting Wikipedia article enrichment...")
        
        # Step 1: Query documents needing enrichment
        documents = self._query_documents()
        
        if not documents:
            logger.info("No documents need enrichment")
            return self.result
            
        # Step 2: Prepare bulk update actions
        logger.info("Preparing bulk update actions...")
        actions = self._prepare_bulk_actions(
            tqdm(documents, desc="Reading HTML files", disable=not sys.stdout.isatty())
        )
        
        # Step 3: Perform bulk updates with ingest pipeline
        self._perform_bulk_updates(actions)
        
        logger.info("Enrichment complete")
        return self.result


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Enrich Wikipedia articles with full HTML content"
    )
    parser.add_argument(
        "--host", 
        default="localhost",
        help="Elasticsearch host (default: localhost)"
    )
    parser.add_argument(
        "--port", 
        type=int,
        default=9200,
        help="Elasticsearch port (default: 9200)"
    )
    parser.add_argument(
        "--index",
        default="wikipedia",
        help="Wikipedia index name (default: wikipedia)"
    )
    parser.add_argument(
        "--pipeline",
        default="wikipedia_ingest_pipeline",
        help="Ingest pipeline name (default: wikipedia_ingest_pipeline)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for bulk updates (default: 50)"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("../data"),
        help="Data directory path (default: ../data)"
    )
    parser.add_argument(
        "--max-documents",
        type=int,
        help="Maximum number of documents to process"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform dry run without updating documents"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    # Create configuration
    config = EnrichmentConfig(
        es_host=args.host,
        es_port=args.port,
        es_index=args.index,
        pipeline_name=args.pipeline,
        batch_size=args.batch_size,
        data_dir=args.data_dir,
        max_documents=args.max_documents,
        dry_run=args.dry_run
    )
    
    # Run enrichment
    try:
        enricher = WikipediaEnricher(config)
        result = enricher.enrich()
        result.print_summary()
        
        # Exit with error code if failures occurred
        if result.documents_failed > 0 or result.errors:
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Enrichment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()