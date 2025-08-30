"""DuckDB data extraction utilities for native Python types.

This module provides clean extraction of data from DuckDB without 
using pandas DataFrames, avoiding numpy type issues.
"""

from typing import List, Dict, Any
from decimal import Decimal
import duckdb

from squack_pipeline.models.duckdb_models import TableIdentifier
from squack_pipeline.models.extraction_models import (
    ExtractedRecord,
    PropertyExtractedRecord,
    NeighborhoodExtractedRecord,
    WikipediaExtractedRecord,
    ExtractionResult
)
from squack_pipeline.models import EntityType
from squack_pipeline.utils.logging import PipelineLogger


class DuckDBExtractor:
    """Extract data from DuckDB tables as native Python types."""
    
    def __init__(self):
        """Initialize the extractor."""
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
    
    def extract_records(
        self,
        connection: duckdb.DuckDBPyConnection,
        table_name: str,
        entity_type: EntityType = None
    ) -> ExtractionResult:
        """
        Extract all records from a DuckDB table as Pydantic models.
        
        This method uses fetchall() to get native Python types instead of
        pandas DataFrames, avoiding numpy type conversion issues.
        
        Args:
            connection: DuckDB connection
            table_name: Name of the table to extract from
            entity_type: Optional entity type for proper model selection
            
        Returns:
            ExtractionResult with Pydantic models and metrics
        """
        safe_table = TableIdentifier(name=table_name)
        
        # Execute query and get result object
        result = connection.execute(f"SELECT * FROM {safe_table.qualified_name}")
        
        # Get column names from description
        columns = [desc[0] for desc in result.description]
        
        # Fetch all rows as tuples
        rows = result.fetchall()
        
        # Convert to Pydantic models
        records = []
        embeddings_count = 0
        
        # Select appropriate model based on entity type
        model_class = ExtractedRecord
        if entity_type == EntityType.PROPERTY:
            model_class = PropertyExtractedRecord
        elif entity_type == EntityType.NEIGHBORHOOD:
            model_class = NeighborhoodExtractedRecord
        elif entity_type == EntityType.WIKIPEDIA:
            model_class = WikipediaExtractedRecord
        
        for row in rows:
            # Create dictionary from row
            record_dict = dict(zip(columns, row))
            
            # Create Pydantic model (handles Decimal conversion automatically)
            record = model_class(**record_dict)
            
            # Count embeddings
            if record.model_dump().get('embedding'):
                embeddings_count += 1
            
            records.append(record)
        
        self.logger.debug(f"Extracted {len(records)} records from {table_name}, {embeddings_count} with embeddings")
        
        return ExtractionResult(
            records=records,
            embeddings_count=embeddings_count,
            total_count=len(records),
            entity_type=entity_type.value if entity_type else None
        )
    
    def extract_count(
        self,
        connection: duckdb.DuckDBPyConnection,
        table_name: str
    ) -> int:
        """
        Get the count of records in a table.
        
        Args:
            connection: DuckDB connection
            table_name: Name of the table
            
        Returns:
            Number of records in the table
        """
        safe_table = TableIdentifier(name=table_name)
        result = connection.execute(
            f"SELECT COUNT(*) FROM {safe_table.qualified_name}"
        ).fetchone()
        
        return result[0] if result else 0
    
    def extract_sample(
        self,
        connection: duckdb.DuckDBPyConnection,
        table_name: str,
        sample_size: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Extract a sample of records from a table.
        
        Args:
            connection: DuckDB connection
            table_name: Name of the table
            sample_size: Number of records to sample
            
        Returns:
            List of sample records as dictionaries
        """
        safe_table = TableIdentifier(name=table_name)
        
        result = connection.execute(
            f"SELECT * FROM {safe_table.qualified_name} LIMIT {sample_size}"
        )
        
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
        
        records = []
        for row in rows:
            record_dict = dict(zip(columns, row))
            
            # Convert Decimal values
            for key, value in record_dict.items():
                if isinstance(value, Decimal):
                    record_dict[key] = float(value)
            
            records.append(record_dict)
        
        return records