"""
Property-specific ChromaDB writer implementation.

This module provides a ChromaDB writer specifically for property embeddings,
with property-specific metadata handling and collection management.
"""

import logging
from typing import Any, Dict, List

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col

from .chromadb_base import BaseChromaDBWriter
from .chromadb_config import PropertyChromaConfig

logger = logging.getLogger(__name__)


class PropertyChromadbWriter(BaseChromaDBWriter):
    """
    ChromaDB writer for property embeddings.
    
    Handles property-specific metadata and collection configuration
    for optimal property search and retrieval.
    """
    
    def __init__(self, config: PropertyChromaConfig, spark: SparkSession):
        """
        Initialize the property ChromaDB writer.
        
        Args:
            config: Property ChromaDB configuration
            spark: SparkSession instance
        """
        super().__init__(config)
        self.config: PropertyChromaConfig = config
        self.spark = spark
        self.logger = logging.getLogger(__name__)
    
    def _get_collection_metadata(self) -> Dict[str, Any]:
        """
        Get property collection metadata.
        
        Returns:
            Collection metadata dictionary
        """
        return {
            "entity_type": "property",
            "description": "Real estate property embeddings for semantic search",
            "metadata_fields": self.config.metadata_fields,
            "searchable_fields": self.config.searchable_fields,
            "source": "property_pipeline"
        }
    
    def _prepare_metadata(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare property-specific metadata.
        
        Args:
            row: DataFrame row as dictionary
            
        Returns:
            Filtered and processed metadata dictionary
        """
        metadata = {}
        
        # Extract configured metadata fields
        for field in self.config.metadata_fields:
            if field in row:
                value = row[field]
                # Convert value to ChromaDB-compatible format
                converted_value = self._convert_metadata_value(value)
                if converted_value is not None:
                    metadata[field] = converted_value
        
        # Add computed fields if not already present
        if "price_per_sqft" in row and row["price_per_sqft"] is not None:
            metadata["price_per_sqft"] = float(row["price_per_sqft"])
        
        # Ensure numeric fields are properly typed
        numeric_fields = ["price", "bedrooms", "bathrooms", "square_feet", "year_built"]
        for field in numeric_fields:
            if field in metadata and metadata[field] is not None:
                try:
                    if field in ["bedrooms", "bathrooms", "year_built"]:
                        metadata[field] = int(metadata[field])
                    else:
                        metadata[field] = float(metadata[field])
                except (ValueError, TypeError):
                    self.logger.debug(f"Could not convert {field} to numeric: {metadata[field]}")
        
        # Add quality indicators
        if "property_quality_score" in row:
            metadata["quality_score"] = float(row["property_quality_score"])
        
        if "property_validation_status" in row:
            metadata["validation_status"] = str(row["property_validation_status"])
        
        return metadata
    
    def _generate_id(self, row: Dict[str, Any], index: int) -> str:
        """
        Generate property-specific ID.
        
        Args:
            row: DataFrame row as dictionary
            index: Row index
            
        Returns:
            Unique identifier string
        """
        if "listing_id" in row and row["listing_id"] is not None:
            return f"property_{row['listing_id']}"
        return f"property_{index}"
    
    def write(self, df: DataFrame, metadata: Dict[str, Any]) -> bool:
        """
        Write property embeddings to ChromaDB.
        
        Args:
            df: Property DataFrame with embeddings
            metadata: Additional metadata about the data being written
            
        Returns:
            True if write was successful, False otherwise
        """
        try:
            # Filter to records with embeddings
            df_with_embeddings = df.filter(col("embeddings").isNotNull())
            total_count = df_with_embeddings.count()
            
            if total_count == 0:
                self.logger.warning("No property records with embeddings to write")
                return True
            
            self.logger.info(f"Writing {total_count} property embeddings to ChromaDB")
            
            # Initialize collection
            collection_metadata = self._get_collection_metadata()
            collection_metadata.update(metadata)
            
            if not self._get_or_create_collection(
                self.config.collection_name,
                collection_metadata
            ):
                return False
            
            # Process in batches
            batch_size = self.config.batch_size
            success_count = 0
            error_count = 0
            
            # Collect data for batch processing
            # Note: For large datasets, consider using foreachPartition instead
            data_rows = df_with_embeddings.collect()
            
            for i in range(0, len(data_rows), batch_size):
                batch = data_rows[i:i + batch_size]
                batch_data = [row.asDict() for row in batch]
                
                if self._write_batch(batch_data):
                    success_count += len(batch_data)
                else:
                    error_count += len(batch_data)
                    if self.config.max_retries > 0:
                        # Retry logic
                        retry_count = 0
                        while retry_count < self.config.max_retries:
                            self.logger.info(f"Retrying batch (attempt {retry_count + 1})")
                            if self._write_batch(batch_data):
                                success_count += len(batch_data)
                                error_count -= len(batch_data)
                                break
                            retry_count += 1
            
            # Log results
            self.logger.info(
                f"Property ChromaDB write completed: "
                f"{success_count} successful, {error_count} errors"
            )
            
            # Verify collection
            final_count = self.collection.count()
            self.logger.info(f"Collection '{self.config.collection_name}' now has {final_count} embeddings")
            
            return error_count == 0
            
        except Exception as e:
            self.logger.error(f"Failed to write property embeddings: {e}")
            return False
    
    def get_writer_name(self) -> str:
        """
        Get the name of this writer.
        
        Returns:
            String identifier for this writer
        """
        return "chromadb_properties"
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the ChromaDB collection.
        
        Returns:
            Dictionary of statistics
        """
        if self.collection is None:
            return {}
        
        try:
            return {
                "collection_name": self.config.collection_name,
                "total_embeddings": self.collection.count(),
                "entity_type": "property",
                "metadata_fields": self.config.metadata_fields,
                "searchable_fields": self.config.searchable_fields
            }
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {}