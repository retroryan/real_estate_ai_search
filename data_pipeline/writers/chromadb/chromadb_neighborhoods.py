"""
Neighborhood-specific ChromaDB writer implementation.

This module provides a ChromaDB writer specifically for neighborhood embeddings,
with neighborhood-specific metadata handling and collection management.
"""

import logging
from typing import Any, Dict, List

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col

from .chromadb_base import BaseChromaDBWriter
from .chromadb_config import NeighborhoodChromaConfig

logger = logging.getLogger(__name__)


class NeighborhoodChromadbWriter(BaseChromaDBWriter):
    """
    ChromaDB writer for neighborhood embeddings.
    
    Handles neighborhood-specific metadata and collection configuration
    for optimal neighborhood search and retrieval.
    """
    
    def __init__(self, config: NeighborhoodChromaConfig, spark: SparkSession):
        """
        Initialize the neighborhood ChromaDB writer.
        
        Args:
            config: Neighborhood ChromaDB configuration
            spark: SparkSession instance
        """
        super().__init__(config)
        self.config: NeighborhoodChromaConfig = config
        self.spark = spark
        self.logger = logging.getLogger(__name__)
    
    def _get_collection_metadata(self) -> Dict[str, Any]:
        """
        Get neighborhood collection metadata.
        
        Returns:
            Collection metadata dictionary
        """
        return {
            "entity_type": "neighborhood",
            "description": "Neighborhood embeddings for location-based semantic search",
            "metadata_fields": self.config.metadata_fields,
            "searchable_fields": self.config.searchable_fields,
            "source": "neighborhood_pipeline"
        }
    
    def _prepare_metadata(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare neighborhood-specific metadata.
        
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
                # Handle normalized name fields
                if field == "neighborhood_name" and value is None:
                    # Try alternate field names
                    value = row.get("neighborhood_name_normalized") or row.get("name")
                
                # Convert value to ChromaDB-compatible format
                converted_value = self._convert_metadata_value(value)
                if converted_value is not None:
                    metadata[field] = converted_value
        
        # Use normalized location fields if available
        if "city_normalized" in row and row["city_normalized"] is not None:
            metadata["city"] = str(row["city_normalized"])
        elif "city" not in metadata and "city" in row:
            metadata["city"] = str(row["city"])
        
        if "state_normalized" in row and row["state_normalized"] is not None:
            metadata["state"] = str(row["state_normalized"])
        elif "state" not in metadata and "state" in row:
            metadata["state"] = str(row["state"])
        
        # Ensure numeric fields are properly typed
        numeric_fields = ["population", "median_income", "median_age"]
        for field in numeric_fields:
            if field in metadata and metadata[field] is not None:
                try:
                    if field == "population":
                        metadata[field] = int(metadata[field])
                    else:
                        metadata[field] = float(metadata[field])
                except (ValueError, TypeError):
                    self.logger.debug(f"Could not convert {field} to numeric: {metadata[field]}")
        
        # Add demographic insights
        if "demographic_completeness" in row:
            metadata["demographic_completeness"] = float(row["demographic_completeness"])
        
        # Add boundary information
        if "has_valid_boundary" in row:
            metadata["has_boundary"] = bool(row["has_valid_boundary"])
        
        if "boundary_point_count" in row and row["boundary_point_count"] is not None:
            metadata["boundary_points"] = int(row["boundary_point_count"])
        
        # Add quality indicators
        if "neighborhood_quality_score" in row:
            metadata["quality_score"] = float(row["neighborhood_quality_score"])
        
        if "neighborhood_validation_status" in row:
            metadata["validation_status"] = str(row["neighborhood_validation_status"])
        
        # Add score fields if available
        if "walk_score" in row and row["walk_score"] is not None:
            metadata["walk_score"] = int(row["walk_score"])
        
        if "transit_score" in row and row["transit_score"] is not None:
            metadata["transit_score"] = int(row["transit_score"])
        
        return metadata
    
    def _generate_id(self, row: Dict[str, Any], index: int) -> str:
        """
        Generate neighborhood-specific ID.
        
        Args:
            row: DataFrame row as dictionary
            index: Row index
            
        Returns:
            Unique identifier string
        """
        if "neighborhood_id" in row and row["neighborhood_id"] is not None:
            return f"neighborhood_{row['neighborhood_id']}"
        elif "id" in row and row["id"] is not None:
            return f"neighborhood_{row['id']}"
        return f"neighborhood_{index}"
    
    def write(self, df: DataFrame, metadata: Dict[str, Any]) -> bool:
        """
        Write neighborhood embeddings to ChromaDB.
        
        Args:
            df: Neighborhood DataFrame with embeddings
            metadata: Additional metadata about the data being written
            
        Returns:
            True if write was successful, False otherwise
        """
        try:
            # Filter to records with embeddings
            df_with_embeddings = df.filter(col("embeddings").isNotNull())
            total_count = df_with_embeddings.count()
            
            if total_count == 0:
                self.logger.warning("No neighborhood records with embeddings to write")
                return True
            
            self.logger.info(f"Writing {total_count} neighborhood embeddings to ChromaDB")
            
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
                f"Neighborhood ChromaDB write completed: "
                f"{success_count} successful, {error_count} errors"
            )
            
            # Verify collection
            final_count = self.collection.count()
            self.logger.info(f"Collection '{self.config.collection_name}' now has {final_count} embeddings")
            
            return error_count == 0
            
        except Exception as e:
            self.logger.error(f"Failed to write neighborhood embeddings: {e}")
            return False
    
    def get_writer_name(self) -> str:
        """
        Get the name of this writer.
        
        Returns:
            String identifier for this writer
        """
        return "chromadb_neighborhoods"
    
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
                "entity_type": "neighborhood",
                "metadata_fields": self.config.metadata_fields,
                "searchable_fields": self.config.searchable_fields
            }
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {}