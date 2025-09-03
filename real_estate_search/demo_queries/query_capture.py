"""
Query capture utility for saving Elasticsearch queries to JSON files.
This module provides a wrapper for the Elasticsearch client that intercepts
and saves all queries executed during demo runs.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime
from elasticsearch import Elasticsearch
import logging

logger = logging.getLogger(__name__)


class QueryCaptureClient:
    """
    Wrapper for Elasticsearch client that captures queries to JSON files.
    
    This class intercepts all search operations and saves the queries
    to JSON files for documentation and debugging purposes.
    """
    
    def __init__(self, es_client: Elasticsearch, demo_number: int, output_dir: Optional[Path] = None):
        """
        Initialize the query capture client.
        
        Args:
            es_client: The actual Elasticsearch client
            demo_number: The demo number being executed
            output_dir: Directory to save JSON files (defaults to demo_queries_json)
        """
        self.es_client = es_client
        self.demo_number = demo_number
        self.query_counter = 0
        
        # Set output directory
        if output_dir is None:
            # Get the path relative to this file
            module_dir = Path(__file__).parent
            output_dir = module_dir / "demo_queries_json"
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Store all captured queries for this demo
        self.captured_queries: List[Dict[str, Any]] = []
    
    def search(self, **kwargs) -> Dict[str, Any]:
        """
        Intercept search calls and save the query to a JSON file.
        
        Args:
            **kwargs: All arguments passed to the search method
            
        Returns:
            The response from the actual Elasticsearch client
        """
        # Increment query counter
        self.query_counter += 1
        
        # Extract the query body
        body = kwargs.get('body', {})
        index = kwargs.get('index', '')
        
        # Create the query info object
        query_info = {
            "demo_number": self.demo_number,
            "query_number": self.query_counter,
            "timestamp": datetime.now().isoformat(),
            "index": index,
            "query": body
        }
        
        # Add any other search parameters
        for key in ['size', 'from', 'scroll', 'sort', 'track_total_hits', 'timeout']:
            if key in kwargs:
                query_info[key] = kwargs[key]
        
        # Save to JSON file
        filename = f"demo_{self.demo_number}_query_{self.query_counter}.json"
        filepath = self.output_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(query_info, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"Saved query to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save query to {filepath}: {e}")
        
        # Store the query in memory as well
        self.captured_queries.append(query_info)
        
        # Execute the actual search
        return self.es_client.search(**kwargs)
    
    def msearch(self, **kwargs) -> Dict[str, Any]:
        """
        Intercept multi-search calls and save queries to JSON files.
        
        Args:
            **kwargs: All arguments passed to the msearch method
            
        Returns:
            The response from the actual Elasticsearch client
        """
        # Increment query counter
        self.query_counter += 1
        
        # Extract the body (list of queries)
        body = kwargs.get('body', [])
        index = kwargs.get('index', '')
        
        # Create the query info object
        query_info = {
            "demo_number": self.demo_number,
            "query_number": self.query_counter,
            "query_type": "msearch",
            "timestamp": datetime.now().isoformat(),
            "index": index,
            "queries": body
        }
        
        # Save to JSON file
        filename = f"demo_{self.demo_number}_query_{self.query_counter}_msearch.json"
        filepath = self.output_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(query_info, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"Saved msearch query to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save msearch query to {filepath}: {e}")
        
        # Store the query in memory as well
        self.captured_queries.append(query_info)
        
        # Execute the actual multi-search
        return self.es_client.msearch(**kwargs)
    
    def count(self, **kwargs) -> Dict[str, Any]:
        """
        Intercept count calls and save the query to a JSON file.
        
        Args:
            **kwargs: All arguments passed to the count method
            
        Returns:
            The response from the actual Elasticsearch client
        """
        # Increment query counter
        self.query_counter += 1
        
        # Extract the query body
        body = kwargs.get('body', {})
        index = kwargs.get('index', '')
        
        # Create the query info object
        query_info = {
            "demo_number": self.demo_number,
            "query_number": self.query_counter,
            "query_type": "count",
            "timestamp": datetime.now().isoformat(),
            "index": index,
            "query": body
        }
        
        # Save to JSON file
        filename = f"demo_{self.demo_number}_query_{self.query_counter}_count.json"
        filepath = self.output_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(query_info, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"Saved count query to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save count query to {filepath}: {e}")
        
        # Store the query in memory as well
        self.captured_queries.append(query_info)
        
        # Execute the actual count
        return self.es_client.count(**kwargs)
    
    def get(self, **kwargs) -> Dict[str, Any]:
        """
        Intercept get calls and save the request to a JSON file.
        
        Args:
            **kwargs: All arguments passed to the get method
            
        Returns:
            The response from the actual Elasticsearch client
        """
        # Increment query counter
        self.query_counter += 1
        
        # Extract the parameters
        index = kwargs.get('index', '')
        id = kwargs.get('id', '')
        
        # Create the query info object
        query_info = {
            "demo_number": self.demo_number,
            "query_number": self.query_counter,
            "query_type": "get",
            "timestamp": datetime.now().isoformat(),
            "index": index,
            "id": id
        }
        
        # Add any other parameters
        for key in ['_source', 'routing', 'preference']:
            if key in kwargs:
                query_info[key] = kwargs[key]
        
        # Save to JSON file
        filename = f"demo_{self.demo_number}_query_{self.query_counter}_get.json"
        filepath = self.output_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(query_info, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"Saved get request to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save get request to {filepath}: {e}")
        
        # Store the query in memory as well
        self.captured_queries.append(query_info)
        
        # Execute the actual get
        return self.es_client.get(**kwargs)
    
    def save_summary(self):
        """
        Save a summary of all queries executed for this demo.
        """
        if not self.captured_queries:
            return
        
        summary = {
            "demo_number": self.demo_number,
            "total_queries": len(self.captured_queries),
            "timestamp": datetime.now().isoformat(),
            "queries": self.captured_queries
        }
        
        # Save summary file
        summary_filename = f"demo_{self.demo_number}_summary.json"
        summary_filepath = self.output_dir / summary_filename
        
        try:
            with open(summary_filepath, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"Saved query summary to {summary_filepath}")
        except Exception as e:
            logger.error(f"Failed to save query summary to {summary_filepath}: {e}")
    
    def __getattr__(self, name):
        """
        Pass through any other method calls to the underlying ES client.
        
        Args:
            name: Method name
            
        Returns:
            The method from the underlying Elasticsearch client
        """
        return getattr(self.es_client, name)


def wrap_es_client_for_demo(es_client: Elasticsearch, demo_number: int) -> QueryCaptureClient:
    """
    Convenience function to wrap an Elasticsearch client for query capture.
    
    Args:
        es_client: The Elasticsearch client to wrap
        demo_number: The demo number being executed
        
    Returns:
        A QueryCaptureClient that will save all queries to JSON files
    """
    return QueryCaptureClient(es_client, demo_number)