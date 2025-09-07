"""Base Elasticsearch writer with common indexing logic."""

import os
import logging
from typing import Dict, Any, List, Callable
from datetime import datetime
from pydantic import BaseModel
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import log_stage
from squack_pipeline_v2.core.settings import PipelineSettings

logger = logging.getLogger(__name__)


class ElasticsearchWriterBase:
    """Base Elasticsearch writer with common functionality."""
    
    def __init__(
        self,
        connection_manager: DuckDBConnectionManager,
        settings: PipelineSettings
    ):
        """Initialize base writer.
        
        Args:
            connection_manager: DuckDB connection manager
            settings: Pipeline settings
        """
        self.connection_manager = connection_manager
        self.settings = settings
        self.config = settings.output.elasticsearch
        self.documents_indexed = 0
        self.es_client = self._create_client()
        
        # Get embedding model from settings
        self.embedding_model = settings.get_model_name()
        if not self.embedding_model or self.embedding_model == "unknown":
            raise ValueError(f"Invalid embedding configuration: provider={settings.embedding.provider}")
        
        # Verify connection
        if not self.es_client.ping():
            raise ConnectionError("Failed to connect to Elasticsearch")
    
    def _create_client(self) -> Elasticsearch:
        """Create Elasticsearch client with proper authentication."""
        es_user = os.getenv("ES_USERNAME")
        es_password = os.getenv("ES_PASSWORD")
        es_url = f"http://{self.config.host}:{self.config.port}"
        
        if es_user and es_password:
            es = Elasticsearch(
                [es_url],
                http_auth=(es_user, es_password),
                request_timeout=self.config.timeout
            )
        else:
            es = Elasticsearch(
                [es_url],
                request_timeout=self.config.timeout
            )
        
        return es
    
    @log_stage("Elasticsearch: Index documents")
    def _index_documents(
        self,
        query: str,
        index_name: str,
        transform: Callable[[Dict[str, Any]], BaseModel],
        id_field: str,
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """Generic document indexing with transformation.
        
        Args:
            query: DuckDB query to fetch data
            index_name: Target Elasticsearch index
            transform: Function to transform row dict to Pydantic model
            id_field: Field to use as document ID
            batch_size: Number of documents per batch
            
        Returns:
            Indexing statistics
        """
        # Execute query once and stream results
        results = self.connection_manager.execute(query)
        
        # Get column names for dict conversion
        columns = [desc[0] for desc in results.description]
        
        logger.info(f"Starting indexing to {index_name}")
        
        indexed = 0
        errors = 0
        validation_errors = 0
        start_time = datetime.now()
        
        while True:
            # Fetch batch using DuckDB's efficient fetchmany
            rows = results.fetchmany(batch_size)
            
            if not rows:
                break
            
            # Convert to dictionaries
            batch_data = [dict(zip(columns, row)) for row in rows]
            
            # Transform and prepare for bulk indexing
            actions = []
            
            for record in batch_data:
                try:
                    # Transform using Pydantic model
                    document = transform(record)
                    
                    # Serialize to dict
                    doc = document.model_dump(exclude_none=True)
                    
                    # Create bulk action
                    action = {
                        "_index": index_name,
                        "_id": doc[id_field],
                        "_source": doc
                    }
                    actions.append(action)
                    
                except Exception as e:
                    logger.error(f"Validation error for {id_field}={record.get(id_field, 'unknown')}: {e}")
                    validation_errors += 1
            
            # Bulk index
            if actions:
                try:
                    result = bulk(
                        self.es_client,
                        actions,
                        raise_on_error=False,
                        raise_on_exception=False,
                        stats_only=False
                    )
                    success_count = result[0]
                    failures = result[1]
                    
                    indexed += success_count
                    if failures:
                        errors += len(failures)
                        for failure in failures[:3]:  # Log first 3 failures
                            logger.error(f"Indexing failure: {failure}")
                        
                except Exception as e:
                    logger.error(f"Bulk indexing error: {e}")
                    errors += len(actions)
            
            if indexed > 0 and indexed % 1000 == 0:
                logger.info(f"Indexed {indexed} documents to {index_name}")
        
        duration = (datetime.now() - start_time).total_seconds()
        self.documents_indexed += indexed
        
        stats = {
            "index": index_name,
            "indexed": indexed,
            "errors": errors,
            "validation_errors": validation_errors,
            "duration_seconds": round(duration, 2),
            "docs_per_second": round(indexed / duration) if duration > 0 else 0
        }
        
        logger.info(f"Completed indexing to {index_name}: {indexed} documents indexed")
        
        return stats