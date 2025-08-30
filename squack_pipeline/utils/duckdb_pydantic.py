"""DuckDB to Pydantic conversion utilities."""

from typing import List, Type, TypeVar, Generator, Tuple
import duckdb
from pydantic import BaseModel, ValidationError

from squack_pipeline.utils.logging import PipelineLogger
from squack_pipeline.models.data_types import ValidationResult

T = TypeVar('T', bound=BaseModel)


class DuckDBPydanticConverter:
    """Convert DuckDB query results directly to Pydantic models."""
    
    def __init__(self):
        """Initialize the converter."""
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
    
    def query_to_models(
        self,
        connection: duckdb.DuckDBPyConnection,
        query: str,
        model_class: Type[T],
        batch_size: int = 1000
    ) -> Generator[T, None, None]:
        """
        Execute a query and yield Pydantic model instances.
        
        This avoids isinstance checks by directly validating through Pydantic.
        
        Args:
            connection: DuckDB connection
            query: SQL query to execute
            model_class: Pydantic model class to instantiate
            batch_size: Number of records to fetch at a time
            
        Yields:
            Validated Pydantic model instances
        """
        result = connection.execute(query)
        
        while True:
            # Fetch batch of records as tuples
            batch = result.fetchmany(batch_size)
            if not batch:
                break
            
            # Get column names for dictionary creation
            columns = [desc[0] for desc in result.description]
            
            for row in batch:
                # Create dictionary from row
                row_dict = dict(zip(columns, row))
                
                try:
                    # Let Pydantic handle all type conversion and validation
                    yield model_class(**row_dict)
                except ValidationError as e:
                    self.logger.warning(f"Validation error for row: {e}")
                    continue
    
    def dataframe_to_models(
        self,
        connection: duckdb.DuckDBPyConnection,
        query: str,
        model_class: Type[T]
    ) -> Tuple[List[T], ValidationResult]:
        """
        Execute a query and return a list of Pydantic models with validation results.
        
        Uses DataFrame as intermediate for better performance with large datasets.
        
        Args:
            connection: DuckDB connection
            query: SQL query to execute
            model_class: Pydantic model class to instantiate
            
        Returns:
            Tuple of (validated model instances, validation results)
        """
        # Get result as DataFrame
        df = connection.execute(query).df()
        
        # Convert DataFrame to list of dictionaries
        records = df.to_dict(orient='records')
        
        # Validate all records through Pydantic
        models = []
        validation_result = ValidationResult()
        
        for row_index, record in enumerate(records):
            try:
                # Pydantic handles all type conversion including Decimal to float
                model = model_class(**record)
                models.append(model)
                validation_result.add_success()
            except ValidationError as e:
                validation_result.add_error(e, row_index)
                continue
        
        # Log summary if there were errors
        if validation_result.failed_records > 0:
            self.logger.warning(
                f"Validation completed: {validation_result.successful_records} successful, "
                f"{validation_result.failed_records} failed ({validation_result.success_rate:.1f}% success rate)"
            )
            self.logger.debug(validation_result.get_error_summary())
        
        return models, validation_result
    
    def table_to_models(
        self,
        connection: duckdb.DuckDBPyConnection,
        table_name: str,
        model_class: Type[T],
        limit: int = None
    ) -> Tuple[List[T], ValidationResult]:
        """
        Convert an entire table to Pydantic models with validation results.
        
        Args:
            connection: DuckDB connection
            table_name: Name of the table to read
            model_class: Pydantic model class to instantiate
            limit: Optional limit on number of records
            
        Returns:
            Tuple of (validated model instances, validation results)
        """
        query = f"SELECT * FROM {table_name}"
        if limit:
            query += f" LIMIT {limit}"
        
        return self.dataframe_to_models(connection, query, model_class)


class DuckDBTypeMapper:
    """Map DuckDB types to Pydantic-compatible Python types."""
    
    # DuckDB to Python type mapping for Pydantic models
    TYPE_MAP = {
        'BOOLEAN': 'bool',
        'TINYINT': 'int',
        'SMALLINT': 'int',
        'INTEGER': 'int',
        'BIGINT': 'int',
        'UTINYINT': 'int',
        'USMALLINT': 'int',
        'UINTEGER': 'int',
        'UBIGINT': 'int',
        'FLOAT': 'float',
        'DOUBLE': 'float',
        'DECIMAL': 'float',  # Pydantic will handle Decimal to float conversion
        'VARCHAR': 'str',
        'TEXT': 'str',
        'DATE': 'str',  # Can be datetime.date with proper annotation
        'TIMESTAMP': 'str',  # Can be datetime.datetime with proper annotation
        'TIME': 'str',  # Can be datetime.time with proper annotation
        'INTERVAL': 'str',
        'BLOB': 'bytes',
        'UUID': 'str',
    }
    
    @classmethod
    def get_python_type(cls, duckdb_type: str) -> str:
        """
        Get Python type string for a DuckDB type.
        
        Args:
            duckdb_type: DuckDB type name
            
        Returns:
            Python type string for use in Pydantic model generation
        """
        # Handle parameterized types
        base_type = duckdb_type.split('(')[0].upper()
        
        # Handle array types
        if base_type.endswith('[]'):
            inner_type = cls.get_python_type(base_type[:-2])
            return f'List[{inner_type}]'
        
        # Handle struct types (simplified)
        if base_type == 'STRUCT':
            return 'Dict'
        
        # Handle map types
        if base_type == 'MAP':
            return 'Dict'
        
        return cls.TYPE_MAP.get(base_type, 'str')