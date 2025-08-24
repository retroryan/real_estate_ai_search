"""
Wikipedia-specific ChromaDB writer implementation.

This module provides a ChromaDB writer specifically for Wikipedia article embeddings,
with article-specific metadata handling and collection management.
"""

import logging
from typing import Any, Dict, List

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col

from .chromadb_base import BaseChromaDBWriter
from .chromadb_config import WikipediaChromaConfig

logger = logging.getLogger(__name__)


class WikipediaChromadbWriter(BaseChromaDBWriter):
    """
    ChromaDB writer for Wikipedia article embeddings.
    
    Handles Wikipedia-specific metadata and collection configuration
    for optimal geographic content search and retrieval.
    """
    
    def __init__(self, config: WikipediaChromaConfig, spark: SparkSession):
        """
        Initialize the Wikipedia ChromaDB writer.
        
        Args:
            config: Wikipedia ChromaDB configuration
            spark: SparkSession instance
        """
        super().__init__(config)
        self.config: WikipediaChromaConfig = config
        self.spark = spark
        self.logger = logging.getLogger(__name__)
    
    def _get_collection_metadata(self) -> Dict[str, Any]:
        """
        Get Wikipedia collection metadata.
        
        Returns:
            Collection metadata dictionary
        """
        return {
            "entity_type": "wikipedia",
            "description": "Wikipedia article embeddings for geographic content search",
            "metadata_fields": self.config.metadata_fields,
            "searchable_fields": self.config.searchable_fields,
            "min_confidence_threshold": self.config.min_confidence_threshold,
            "source": "wikipedia_pipeline"
        }
    
    def _prepare_metadata(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare Wikipedia-specific metadata.
        
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
                
                # Handle location fields with validation
                if field in ["best_city", "best_state"]:
                    # Use validated versions if available
                    validated_field = f"{field.replace('best_', '')}_validated"
                    if validated_field in row and row[validated_field] is not None:
                        value = row[validated_field]
                
                # Convert value to ChromaDB-compatible format
                converted_value = self._convert_metadata_value(value)
                if converted_value is not None:
                    metadata[field] = converted_value
        
        # Ensure numeric fields are properly typed
        numeric_fields = ["page_id", "relevance_score", "confidence_score", 
                         "location_relevance_score", "overall_confidence"]
        for field in numeric_fields:
            if field in metadata and metadata[field] is not None:
                try:
                    if field == "page_id":
                        metadata[field] = int(metadata[field])
                    else:
                        metadata[field] = float(metadata[field])
                except (ValueError, TypeError):
                    self.logger.debug(f"Could not convert {field} to numeric: {metadata[field]}")
        
        # Add location validation flags
        if "has_valid_location" in row:
            metadata["has_valid_location"] = bool(row["has_valid_location"])
        
        if "extraction_reliable" in row:
            metadata["extraction_reliable"] = bool(row["extraction_reliable"])
        
        # Add confidence level if available
        if "confidence_level" in row:
            metadata["confidence_level"] = str(row["confidence_level"])
        
        # Add quality indicators
        if "article_quality_score" in row:
            metadata["quality_score"] = float(row["article_quality_score"])
        
        if "article_validation_status" in row:
            metadata["validation_status"] = str(row["article_validation_status"])
        
        # Add content statistics
        if "embedding_text_length" in row and row["embedding_text_length"] is not None:
            metadata["text_length"] = int(row["embedding_text_length"])
        
        # Add categories if available
        if "categories" in row and row["categories"] is not None:
            # Convert list to string for ChromaDB
            metadata["categories"] = str(row["categories"])
        
        # Add key topics if available
        if "key_topics" in row and row["key_topics"] is not None:
            # Convert list to string for ChromaDB
            metadata["key_topics"] = str(row["key_topics"])
        
        return metadata
    
    def _generate_id(self, row: Dict[str, Any], index: int) -> str:
        """
        Generate Wikipedia-specific ID.
        
        Args:
            row: DataFrame row as dictionary
            index: Row index
            
        Returns:
            Unique identifier string
        """
        if "page_id" in row and row["page_id"] is not None:
            return f"wikipedia_{row['page_id']}"
        elif "article_id" in row and row["article_id"] is not None:
            return f"wikipedia_{row['article_id']}"
        return f"wikipedia_{index}"
    
    def _should_store_article(self, row: Dict[str, Any]) -> bool:
        """
        Determine if an article should be stored based on confidence threshold.
        
        Args:
            row: DataFrame row as dictionary
            
        Returns:
            True if article should be stored, False otherwise
        """
        # Check confidence threshold
        if "confidence_score" in row and row["confidence_score"] is not None:
            if float(row["confidence_score"]) < self.config.min_confidence_threshold:
                return False
        
        # Check if embedding exists
        if row.get("embeddings") is None:
            return False
        
        return True
    
    def write(self, df: DataFrame, metadata: Dict[str, Any]) -> bool:
        """
        Write Wikipedia embeddings to ChromaDB.
        
        Args:
            df: Wikipedia DataFrame with embeddings
            metadata: Additional metadata about the data being written
            
        Returns:
            True if write was successful, False otherwise
        """
        try:
            # Filter to records with embeddings and sufficient confidence
            df_with_embeddings = df.filter(
                col("embeddings").isNotNull()
            )
            
            # Apply confidence threshold if configured
            if self.config.min_confidence_threshold > 0:
                df_with_embeddings = df_with_embeddings.filter(
                    (col("confidence_score").isNull()) | 
                    (col("confidence_score") >= self.config.min_confidence_threshold)
                )
            
            total_count = df_with_embeddings.count()
            
            if total_count == 0:
                self.logger.warning("No Wikipedia articles with valid embeddings to write")
                return True
            
            self.logger.info(f"Writing {total_count} Wikipedia embeddings to ChromaDB")
            
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
            skipped_count = 0
            
            # Collect data for batch processing
            # Note: For large datasets, consider using foreachPartition instead
            data_rows = df_with_embeddings.collect()
            
            for i in range(0, len(data_rows), batch_size):
                batch = data_rows[i:i + batch_size]
                
                # Filter batch based on confidence threshold
                filtered_batch = []
                for row in batch:
                    row_dict = row.asDict()
                    if self._should_store_article(row_dict):
                        filtered_batch.append(row_dict)
                    else:
                        skipped_count += 1
                
                if filtered_batch:
                    if self._write_batch(filtered_batch):
                        success_count += len(filtered_batch)
                    else:
                        error_count += len(filtered_batch)
                        if self.config.max_retries > 0:
                            # Retry logic
                            retry_count = 0
                            while retry_count < self.config.max_retries:
                                self.logger.info(f"Retrying batch (attempt {retry_count + 1})")
                                if self._write_batch(filtered_batch):
                                    success_count += len(filtered_batch)
                                    error_count -= len(filtered_batch)
                                    break
                                retry_count += 1
            
            # Log results
            self.logger.info(
                f"Wikipedia ChromaDB write completed: "
                f"{success_count} successful, {error_count} errors, {skipped_count} skipped"
            )
            
            if skipped_count > 0:
                self.logger.info(
                    f"Skipped {skipped_count} articles below confidence threshold "
                    f"({self.config.min_confidence_threshold})"
                )
            
            # Verify collection
            final_count = self.collection.count()
            self.logger.info(f"Collection '{self.config.collection_name}' now has {final_count} embeddings")
            
            return error_count == 0
            
        except Exception as e:
            self.logger.error(f"Failed to write Wikipedia embeddings: {e}")
            return False
    
    def get_writer_name(self) -> str:
        """
        Get the name of this writer.
        
        Returns:
            String identifier for this writer
        """
        return "chromadb_wikipedia"
    
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
                "entity_type": "wikipedia",
                "metadata_fields": self.config.metadata_fields,
                "searchable_fields": self.config.searchable_fields,
                "min_confidence_threshold": self.config.min_confidence_threshold
            }
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {}