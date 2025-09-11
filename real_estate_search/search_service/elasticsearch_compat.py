"""
Elasticsearch compatibility layer for testing environments.
"""

try:
    from elasticsearch import Elasticsearch
    from elasticsearch.exceptions import TransportError, NotFoundError, RequestError
    ELASTICSEARCH_AVAILABLE = True
except ImportError:
    # Create mock classes for testing environments
    class Elasticsearch:
        def __init__(self, *args, **kwargs):
            pass
        
        def search(self, *args, **kwargs):
            return {"hits": {"total": {"value": 0}, "hits": []}}
        
        def get(self, *args, **kwargs):
            return {"_source": {}}
        
        def index(self, *args, **kwargs):
            return {"_id": "test"}
    
    class TransportError(Exception):
        pass
    
    class NotFoundError(Exception):
        pass
    
    class RequestError(Exception):
        pass
    
    ELASTICSEARCH_AVAILABLE = False

__all__ = ['Elasticsearch', 'TransportError', 'NotFoundError', 'RequestError', 'ELASTICSEARCH_AVAILABLE']