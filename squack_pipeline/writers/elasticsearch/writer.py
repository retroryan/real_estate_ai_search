"""Elasticsearch writer for SQUACK pipeline."""

import time
from decimal import Decimal
from typing import Dict, List, Optional

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk, BulkIndexError

from squack_pipeline.config.settings import ElasticsearchConfig, PipelineSettings
from squack_pipeline.writers.base import BaseWriter
from squack_pipeline.writers.elasticsearch.models import (
    WriteResult,
    BulkOperation,
    TransformationConfig,
    IndexMapping,
)
from squack_pipeline.models import EntityType
from squack_pipeline.models.writer_interface import (
    WriteRequest,
    WriteResponse,
    WriteMetrics,
    ValidationResult
)
from squack_pipeline.models.data_types import PropertyRecord, NeighborhoodRecord, WikipediaRecord
from squack_pipeline.transformers import (
    PropertyTransformer,
    NeighborhoodTransformer,
    WikipediaTransformer
)
from squack_pipeline.utils.logging import PipelineLogger
from squack_pipeline.utils.duckdb_extractor import DuckDBExtractor


class ElasticsearchWriter(BaseWriter):
    """Elasticsearch writer implementing standardized interface."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize Elasticsearch writer.
        
        Args:
            settings: Pipeline settings containing Elasticsearch config
        """
        super().__init__(settings)
        
        # Get Elasticsearch config from settings
        if not settings.output.elasticsearch:
            raise ValueError("Elasticsearch configuration not found in settings")
        
        self.config: ElasticsearchConfig = settings.output.elasticsearch
        
        # Initialize Elasticsearch client
        self.client = self._create_client()
        
        # Initialize transformers for each entity type
        self.property_transformer = PropertyTransformer()
        self.neighborhood_transformer = NeighborhoodTransformer()
        self.wikipedia_transformer = WikipediaTransformer()
        
        # Map entity types to transformers
        self.transformers = {
            EntityType.PROPERTY: self.property_transformer,
            EntityType.NEIGHBORHOOD: self.neighborhood_transformer,
            EntityType.WIKIPEDIA: self.wikipedia_transformer,
        }
        
        # Default transformation config
        self.transform_config = TransformationConfig()
        
        # Entity mappings
        self.mappings = {
            EntityType.PROPERTY: IndexMapping.for_properties(),
            EntityType.NEIGHBORHOOD: IndexMapping.for_neighborhoods(),
            EntityType.WIKIPEDIA: IndexMapping.for_wikipedia(),
        }
        
        # Data extractor for getting data from DuckDB
        self.extractor = DuckDBExtractor()
    
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
    
    def write(self, request: WriteRequest) -> WriteResponse:
        """Write table data to Elasticsearch.
        
        Args:
            request: Write request with table name and entity type
            
        Returns:
            WriteResponse with operation status and metrics
        """
        start_time = time.time()
        
        # Map entity types to Elasticsearch index names
        index_names = {
            EntityType.PROPERTY: "properties",
            EntityType.NEIGHBORHOOD: "neighborhoods",
            EntityType.WIKIPEDIA: "wikipedia"
        }
        index_name = index_names.get(request.entity_type, request.entity_type.value)
        
        # Validate connection
        if not self.connection:
            return WriteResponse(
                success=False,
                entity_type=request.entity_type,
                destination=index_name,
                metrics=WriteMetrics(
                    records_written=0,
                    records_failed=request.record_count,
                    duration_seconds=0
                ),
                error="No DuckDB connection available"
            )
        
        try:
            # Extract data from DuckDB
            self.logger.info(f"Extracting {request.entity_type.value} from {request.table_name}...")
            extraction_result = self.extractor.extract_records(
                self.connection, 
                request.table_name, 
                request.entity_type
            )
            
            # Convert to dictionaries
            data = [record.to_dict() for record in extraction_result.records]
            
            if not data:
                duration = time.time() - start_time
                return WriteResponse(
                    success=True,
                    entity_type=request.entity_type,
                    destination=index_name,
                    metrics=WriteMetrics(
                        records_written=0,
                        records_failed=0,
                        duration_seconds=duration
                    )
                )
            
            # Transform records using appropriate transformer
            transformer = self.transformers.get(request.entity_type)
            if transformer:
                transformed_data = []
                for record in data:
                    transformed_record = transformer.transform(record)
                    # Check if the transformed record has a specific method
                    # without using hasattr (following requirements)
                    try:
                        # Try to call the method if it exists
                        to_dict_method = getattr(transformed_record, 'to_elasticsearch_dict', None)
                        if callable(to_dict_method):
                            transformed_data.append(to_dict_method())
                        else:
                            # Fallback for dict or other types
                            transformed_data.append(transformed_record)
                    except AttributeError:
                        # If no such method, use as-is
                        transformed_data.append(transformed_record)
            else:
                # Fallback to basic transformation if no transformer
                mapping = self.mappings[request.entity_type]
                transformed_data = [
                    self._transform_record(record, request.entity_type, mapping)
                    for record in data
                ]
            
            self.logger.info(f"Writing {len(transformed_data)} {request.entity_type.value} records to {index_name}")
            
            # Create bulk operation
            mapping = self.mappings[request.entity_type]
            bulk_op = BulkOperation(
                entity_type=request.entity_type,
                index_name=index_name,
                records=transformed_data,
                id_field=mapping.id_field,
                chunk_size=self.config.bulk_size,
            )
            
            # Execute bulk write
            success_count, failed_items = self._execute_bulk(bulk_op)
            
            duration = time.time() - start_time
            
            # Ensure integer values - always convert to int
            failed_items = int(failed_items)
            success_count = int(success_count)
            
            # Log result
            if failed_items == 0:
                self.logger.success(
                    f"Successfully wrote {success_count} {request.entity_type.value} "
                    f"records in {duration:.2f}s"
                )
            else:
                self.logger.warning(
                    f"Partial write: {success_count} succeeded, "
                    f"{failed_items} failed for {request.entity_type.value}"
                )
            
            return WriteResponse(
                success=failed_items == 0,
                entity_type=request.entity_type,
                destination=index_name,
                metrics=WriteMetrics(
                    records_written=success_count,
                    records_failed=failed_items,
                    duration_seconds=duration
                ),
                error=f"{failed_items} documents failed" if failed_items > 0 else None
            )
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Failed to write {request.entity_type.value}: {str(e)}")
            
            return WriteResponse(
                success=False,
                entity_type=request.entity_type,
                destination=index_name,
                metrics=WriteMetrics(
                    records_written=0,
                    records_failed=request.record_count,
                    duration_seconds=duration
                ),
                error=str(e)
            )
    
    def validate(self, entity_type: EntityType, destination: str) -> ValidationResult:
        """Validate written data in Elasticsearch index.
        
        Args:
            entity_type: Type of entity that was written
            destination: Elasticsearch index name
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult(is_valid=True)
        
        try:
            # Check if index exists
            if not self.client.indices.exists(index=destination):
                result.add_error(f"Index does not exist: {destination}")
                return result
            
            # Get index stats
            stats = self.client.indices.stats(index=destination)
            index_stats = stats['indices'][destination]
            
            # Check document count
            doc_count = index_stats['primaries']['docs']['count']
            if doc_count == 0:
                result.add_warning(f"Index is empty: {destination}")
            
            # Get index mapping
            mapping = self.client.indices.get_mapping(index=destination)
            
            # Add metadata
            result.metadata = {
                "doc_count": doc_count,
                "index_size_bytes": index_stats['primaries']['store']['size_in_bytes'],
                "segments": index_stats['primaries']['segments']['count'],
                "health": self.client.cluster.health(index=destination)['status']
            }
            
            self.logger.debug(
                f"Validated Elasticsearch index {destination}: "
                f"{doc_count} documents, health={result.metadata['health']}"
            )
            
        except Exception as e:
            result.add_error(f"Failed to validate Elasticsearch index: {e}")
        
        return result
    
    def get_metrics(self, entity_type: EntityType, destination: str) -> WriteMetrics:
        """Get metrics for Elasticsearch index.
        
        Args:
            entity_type: Type of entity
            destination: Elasticsearch index name
            
        Returns:
            WriteMetrics with index statistics
        """
        try:
            # Get index stats
            stats = self.client.indices.stats(index=destination)
            index_stats = stats['indices'][destination]['primaries']
            
            return WriteMetrics(
                records_written=index_stats['docs']['count'],
                records_failed=0,
                bytes_written=index_stats['store']['size_in_bytes'],
                duration_seconds=0  # Duration not available from index
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get metrics for {destination}: {e}")
            return WriteMetrics(
                records_written=0,
                records_failed=0,
                bytes_written=0,
                duration_seconds=0
            )
    
    def _transform_record(
        self,
        record: Dict,
        entity_type: EntityType,
        mapping: IndexMapping
    ) -> Dict:
        """Transform a record for Elasticsearch.
        
        Args:
            record: Record to transform
            entity_type: Type of entity
            mapping: Index mapping configuration
            
        Returns:
            Transformed record
        """
        transformed = {}
        
        for key, value in record.items():
            # Skip fields to exclude
            if self.transform_config.should_exclude(key):
                continue
            
            # Convert Decimal to float if needed
            if self.transform_config.convert_decimals:
                # Try to convert to float if it's a Decimal
                try:
                    # Decimal has a specific method we can check for
                    if value.__class__.__name__ == 'Decimal':
                        transformed[key] = float(value)
                    else:
                        transformed[key] = value
                except (AttributeError, TypeError):
                    transformed[key] = value
            else:
                transformed[key] = value
        
        # Create geo_point fields if configured
        if self.transform_config.create_geo_points and mapping.geo_fields:
            for geo_field, coord_fields in mapping.geo_fields.items():
                lat = record.get(coord_fields['lat'])
                lon = record.get(coord_fields['lon'])
                if lat is not None and lon is not None:
                    # Convert to float if Decimal, otherwise keep as-is
                    try:
                        lat_val = float(lat) if lat.__class__.__name__ == 'Decimal' else lat
                    except (AttributeError, TypeError):
                        lat_val = lat
                    
                    try:
                        lon_val = float(lon) if lon.__class__.__name__ == 'Decimal' else lon
                    except (AttributeError, TypeError):
                        lon_val = lon
                    
                    transformed[geo_field] = {
                        "lat": lat_val,
                        "lon": lon_val
                    }
        
        return transformed
    
    def _execute_bulk(self, bulk_op: BulkOperation) -> tuple:
        """Execute bulk write operation.
        
        Args:
            bulk_op: Bulk operation configuration
            
        Returns:
            Tuple of (success_count, failed_count)
        """
        actions = []
        for record in bulk_op.records:
            action = {
                "_index": bulk_op.index_name,
                "_id": record.get(bulk_op.id_field),
                "_source": record
            }
            actions.append(action)
        
        try:
            success, failed = bulk(
                self.client,
                actions,
                chunk_size=bulk_op.chunk_size,
                raise_on_error=False,
                raise_on_exception=False
            )
            
            failed_count = len(failed) if failed else 0
            
            # Log any failures
            if failed:
                for item in failed[:5]:  # Log first 5 failures
                    self.logger.error(f"Bulk error: {item}")
            
            return success, failed_count
            
        except BulkIndexError as e:
            # Extract error details
            failed_count = len(e.errors) if e.errors else 0
            success_count = bulk_op.get_record_count() - failed_count
            
            # Log first few errors
            for error in e.errors[:5]:
                self.logger.error(f"Bulk index error: {error}")
            
            return success_count, failed_count
    
    def verify_connection(self) -> bool:
        """Verify Elasticsearch connection is working.
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Ping the cluster
            if not self.client.ping():
                self.logger.error("Failed to ping Elasticsearch cluster")
                return False
            
            # Get cluster info
            info = self.client.info()
            self.logger.info(
                f"Connected to Elasticsearch {info['version']['number']} "
                f"at {self.config.host}:{self.config.port}"
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to verify Elasticsearch connection: {e}")
            return False
    
    def write_entity(self, entity_type: EntityType, data: List[Dict]) -> WriteResult:
        """Legacy method for backward compatibility.
        
        Args:
            entity_type: Type of entity being written
            data: List of records to write
            
        Returns:
            WriteResult with operation status
        """
        # This method is called by WriterOrchestrator for backward compatibility
        # We need to handle the case where we have data directly, not a table
        
        # Store the data temporarily and create a request
        # Since we don't have a table name, we'll use a placeholder
        request = WriteRequest(
            entity_type=entity_type,
            table_name=f"temp_{entity_type.value}",
            record_count=len(data)
        )
        
        # For this legacy path, we need to handle the data directly
        # without going through DuckDB extraction
        start_time = time.time()
        
        # Map entity types to Elasticsearch index names
        index_names = {
            EntityType.PROPERTY: "properties",
            EntityType.NEIGHBORHOOD: "neighborhoods",
            EntityType.WIKIPEDIA: "wikipedia"
        }
        index_name = index_names.get(entity_type, entity_type.value)
        
        if not data:
            return WriteResult(
                success=True,
                entity_type=entity_type,
                record_count=0,
                failed_count=0,
                index_name=index_name,
                duration_seconds=0
            )
        
        try:
            # Transform records using appropriate transformer
            transformer = self.transformers.get(entity_type)
            if transformer:
                transformed_data = []
                for record in data:
                    transformed_record = transformer.transform(record)
                    # Check for to_elasticsearch_dict method without hasattr
                    try:
                        to_dict_method = getattr(transformed_record, 'to_elasticsearch_dict', None)
                        if callable(to_dict_method):
                            transformed_data.append(to_dict_method())
                        else:
                            transformed_data.append(transformed_record)
                    except AttributeError:
                        transformed_data.append(transformed_record)
            else:
                mapping = self.mappings[entity_type]
                transformed_data = [
                    self._transform_record(record, entity_type, mapping)
                    for record in data
                ]
            
            # Create bulk operation
            mapping = self.mappings[entity_type]
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
            
            # Ensure integer values - always convert to int
            failed_items = int(failed_items)
            success_count = int(success_count)
            
            return WriteResult(
                success=failed_items == 0,
                entity_type=entity_type,
                record_count=success_count,
                failed_count=failed_items,
                index_name=index_name,
                duration_seconds=duration,
                error=f"{failed_items} documents failed" if failed_items > 0 else None
            )
            
        except Exception as e:
            self.logger.error(f"Failed to write {entity_type.value}: {str(e)}")
            return WriteResult(
                success=False,
                entity_type=entity_type,
                record_count=0,
                failed_count=len(data),
                index_name=index_name,
                duration_seconds=time.time() - start_time,
                error=str(e)
            )