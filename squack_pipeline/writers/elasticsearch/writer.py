"""Elasticsearch writer for SQUACK pipeline."""

import time
from decimal import Decimal
from typing import Dict, List, Any, Optional

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk, BulkIndexError

from squack_pipeline.config.settings import ElasticsearchConfig
from squack_pipeline.writers.elasticsearch.models import (
    EntityType,
    WriteResult,
    BulkOperation,
    TransformationConfig,
    IndexMapping,
)
from squack_pipeline.utils.logging import PipelineLogger


class ElasticsearchWriter:
    """Simple Elasticsearch writer using Python client."""
    
    def __init__(self, config: ElasticsearchConfig):
        """
        Initialize Elasticsearch writer.
        
        Args:
            config: Elasticsearch configuration
        """
        self.config = config
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        
        # Initialize Elasticsearch client
        self.client = self._create_client()
        
        # Default transformation config
        self.transform_config = TransformationConfig()
        
        # Entity mappings
        self.mappings = {
            EntityType.PROPERTIES: IndexMapping.for_properties(),
            EntityType.NEIGHBORHOODS: IndexMapping.for_neighborhoods(),
            EntityType.WIKIPEDIA: IndexMapping.for_wikipedia(),
        }
    
    def _create_client(self) -> Elasticsearch:
        """Create Elasticsearch client with configuration."""
        client_config = {
            'hosts': [{'host': self.config.host, 'port': self.config.port, 'scheme': 'http'}],
            'request_timeout': self.config.timeout,
            'max_retries': 3,
            'retry_on_timeout': True,
        }
        
        # Add authentication if configured
        password = self.config.password  # Get from environment variable
        if self.config.username and password:
            client_config['basic_auth'] = (self.config.username, password)
        
        return Elasticsearch(**client_config)
    
    def write_entity(
        self,
        entity_type: EntityType,
        data: List[Dict[str, Any]]
    ) -> WriteResult:
        """
        Write entity data to Elasticsearch.
        
        Args:
            entity_type: Type of entity being written
            data: List of records to write
            
        Returns:
            WriteResult with operation status
        """
        start_time = time.time()
        index_name = f"{self.config.index_prefix}_{entity_type.value}"
        mapping = self.mappings[entity_type]
        
        if not data:
            return WriteResult(
                success=True,
                entity_type=entity_type,
                record_count=0,
                failed_count=0,
                index_name=index_name,
                duration_seconds=0,
            )
        
        self.logger.info(f"Writing {len(data)} {entity_type.value} records to {index_name}")
        
        try:
            # Transform records
            transformed_data = [
                self._transform_record(record, entity_type, mapping)
                for record in data
            ]
            
            # Create bulk operation
            bulk_op = BulkOperation(
                entity_type=entity_type,
                index_name=index_name,
                records=transformed_data,
                id_field=mapping.id_field,
                chunk_size=self.config.bulk_size,
            )
            
            # Execute bulk write
            success_count, failed_items = self._execute_bulk(bulk_op)
            
            duration = time.time() - start_time
            
            result = WriteResult(
                success=failed_items == 0,
                entity_type=entity_type,
                record_count=success_count,
                failed_count=failed_items,
                index_name=index_name,
                duration_seconds=duration,
                error=f"{failed_items} documents failed" if failed_items > 0 else None,
            )
            
            if result.is_successful():
                self.logger.success(
                    f"Successfully wrote {success_count} {entity_type.value} "
                    f"records in {duration:.2f}s"
                )
            else:
                self.logger.warning(
                    f"Partial write: {success_count} succeeded, "
                    f"{failed_items} failed for {entity_type.value}"
                )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to write {entity_type.value}: {str(e)}")
            return WriteResult(
                success=False,
                entity_type=entity_type,
                record_count=0,
                failed_count=len(data),
                index_name=index_name,
                duration_seconds=time.time() - start_time,
                error=str(e),
            )
    
    def _transform_record(
        self,
        record: Dict[str, Any],
        entity_type: EntityType,
        mapping: IndexMapping
    ) -> Dict[str, Any]:
        """
        Transform a record for Elasticsearch compatibility.
        
        Args:
            record: Original record
            entity_type: Type of entity
            mapping: Index mapping configuration
            
        Returns:
            Transformed record
        """
        transformed = {}
        
        for key, value in record.items():
            # Skip excluded fields
            if self.transform_config.should_exclude(key):
                continue
            
            # Skip None values
            if value is None:
                continue
            
            # Convert Decimal to float
            if self.transform_config.convert_decimals and isinstance(value, Decimal):
                transformed[key] = float(value)
            else:
                transformed[key] = value
        
        # Add geo_point if configured
        if self.transform_config.create_geo_points and mapping.geo_fields:
            for geo_field, coords in mapping.geo_fields.items():
                lat_field = coords.get("lat", "latitude")
                lon_field = coords.get("lon", "longitude")
                
                if lat_field in record and lon_field in record:
                    lat = record[lat_field]
                    lon = record[lon_field]
                    
                    # Only create geo_point if both values are valid
                    if lat is not None and lon is not None:
                        try:
                            transformed[geo_field] = {
                                "lat": float(lat),
                                "lon": float(lon),
                            }
                        except (ValueError, TypeError):
                            # Skip invalid coordinates
                            pass
        
        # Ensure ID field is string (required for Wikipedia page_id)
        if mapping.id_field in transformed:
            transformed[mapping.id_field] = str(transformed[mapping.id_field])
        
        return transformed
    
    def _execute_bulk(self, bulk_op: BulkOperation) -> tuple[int, int]:
        """
        Execute bulk write operation.
        
        Args:
            bulk_op: Bulk operation configuration
            
        Returns:
            Tuple of (success_count, failed_count)
        """
        actions = []
        
        for record in bulk_op.records:
            # Get document ID
            doc_id = record.get(bulk_op.id_field)
            if not doc_id:
                self.logger.warning(f"Missing ID field {bulk_op.id_field} in record")
                continue
            
            action = {
                "_index": bulk_op.index_name,
                "_id": str(doc_id),
                "_source": record,
            }
            actions.append(action)
        
        if not actions:
            return 0, 0
        
        try:
            # Execute bulk operation
            success, failed = bulk(
                self.client,
                actions,
                chunk_size=bulk_op.chunk_size,
                raise_on_error=False,
                raise_on_exception=False,
            )
            
            # Process any failed items
            if failed:
                for item in failed:
                    self.logger.debug(f"Failed to index document: {item}")
            
            return success, len(failed)
            
        except BulkIndexError as e:
            # Handle partial failures
            success = len(e.errors) - len([err for err in e.errors if 'error' in err['index']])
            failed = len([err for err in e.errors if 'error' in err['index']])
            
            self.logger.warning(f"Bulk operation partially failed: {failed} errors")
            return success, failed
        
        except Exception as e:
            self.logger.error(f"Bulk operation failed: {str(e)}")
            return 0, len(actions)
    
    def verify_connection(self) -> bool:
        """
        Verify connection to Elasticsearch.
        
        Returns:
            True if connection is successful
        """
        try:
            info = self.client.info()
            self.logger.info(
                f"Connected to Elasticsearch {info['version']['number']} "
                f"at {self.config.host}:{self.config.port}"
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Elasticsearch: {str(e)}")
            return False
    
    def close(self):
        """Close Elasticsearch client connection."""
        if self.client:
            self.client.close()
            self.logger.info("Elasticsearch connection closed")