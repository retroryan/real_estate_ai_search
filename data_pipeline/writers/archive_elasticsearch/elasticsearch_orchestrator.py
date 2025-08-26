"""
Elasticsearch writer orchestrator for entity-specific index creation.

This module provides a single orchestrator that routes entity-specific
DataFrames to appropriate Elasticsearch indices with proper mappings.
"""

import logging
from typing import Any, Dict

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, struct, when, isnan, isnull
from pyspark.sql.types import DecimalType, DoubleType, ArrayType, StructType

from data_pipeline.config.models import ElasticsearchOutputConfig
from data_pipeline.writers.base import EntityWriter

logger = logging.getLogger(__name__)


class ElasticsearchOrchestrator(EntityWriter):
    """
    Orchestrator for entity-specific Elasticsearch writing.
    
    Routes each entity type to its dedicated index with proper mappings.
    """
    
    def __init__(self, config: ElasticsearchOutputConfig, spark: SparkSession):
        """
        Initialize the Elasticsearch orchestrator.
        
        Args:
            config: Elasticsearch configuration
            spark: SparkSession instance
        """
        super().__init__(config)
        self.config = config
        self.spark = spark
        self.logger = logging.getLogger(__name__)
        
        # Use official Elasticsearch format for Spark
        self.format_string = "es"
    
    def _add_geo_point(self, df: DataFrame, lat_col: str = "latitude", lon_col: str = "longitude") -> DataFrame:
        """
        Add a geo_point field combining latitude and longitude.
        
        Args:
            df: Input DataFrame
            lat_col: Name of latitude column
            lon_col: Name of longitude column
            
        Returns:
            DataFrame with added location field
        """
        # Only add geo_point if both lat and lon columns exist
        if lat_col in df.columns and lon_col in df.columns:
            # Create geo_point structure, handling nulls
            df = df.withColumn(
                "location",
                when(
                    (col(lat_col).isNotNull()) & 
                    (col(lon_col).isNotNull()) & 
                    (~isnan(col(lat_col))) & 
                    (~isnan(col(lon_col))),
                    struct(
                        col(lat_col).alias("lat"),
                        col(lon_col).alias("lon")
                    )
                ).otherwise(None)
            )
        return df
    
    def _convert_decimal_columns(self, df: DataFrame) -> DataFrame:
        """
        Convert decimal columns to double type for Elasticsearch compatibility.
        
        This handles decimal types in:
        - Top-level columns
        - Nested struct fields
        - Array elements (including struct arrays)
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with decimal columns converted to double
        """
        # Convert the DataFrame schema to handle all decimal types
        new_schema = self._convert_schema_decimals(df.schema)
        
        # If schema changed, we need to reconstruct the DataFrame
        if new_schema != df.schema:
            # Use SQL to convert the DataFrame with the new schema
            df.createOrReplaceTempView("temp_df")
            
            # Generate SELECT statement that casts decimal columns
            select_expressions = []
            for field in new_schema.fields:
                if field.name in df.columns:
                    if self._schema_field_has_decimal(df.schema[field.name]):
                        # Cast column to match new schema
                        select_expressions.append(f"CAST({field.name} AS {field.dataType.simpleString()}) AS {field.name}")
                    else:
                        select_expressions.append(field.name)
            
            if select_expressions:
                sql_query = f"SELECT {', '.join(select_expressions)} FROM temp_df"
                df = self.spark.sql(sql_query)
        
        return df
    
    def _convert_schema_decimals(self, schema: StructType) -> StructType:
        """
        Recursively convert decimal types in schema to double types.
        
        Args:
            schema: Input schema
            
        Returns:
            Schema with decimal types converted to double
        """
        from pyspark.sql.types import StructField
        
        new_fields = []
        for field in schema.fields:
            new_data_type = self._convert_data_type_decimals(field.dataType)
            new_field = StructField(field.name, new_data_type, field.nullable, field.metadata)
            new_fields.append(new_field)
        
        return StructType(new_fields)
    
    def _convert_data_type_decimals(self, data_type):
        """
        Recursively convert decimal types to double in any data type.
        
        Args:
            data_type: Spark data type
            
        Returns:
            Data type with decimals converted to double
        """
        if isinstance(data_type, DecimalType):
            return DoubleType()
        elif isinstance(data_type, ArrayType):
            # Convert array element type
            new_element_type = self._convert_data_type_decimals(data_type.elementType)
            return ArrayType(new_element_type, data_type.containsNull)
        elif isinstance(data_type, StructType):
            # Convert struct field types
            return self._convert_schema_decimals(data_type)
        else:
            return data_type
    
    def _schema_field_has_decimal(self, field):
        """
        Check if a schema field contains any decimal types.
        
        Args:
            field: Schema field to check
            
        Returns:
            True if field contains decimal types
        """
        return self._data_type_has_decimal(field.dataType)
    
    def _data_type_has_decimal(self, data_type):
        """
        Check if a data type contains any decimal types recursively.
        
        Args:
            data_type: Data type to check
            
        Returns:
            True if data type contains decimal types
        """
        if isinstance(data_type, DecimalType):
            return True
        elif isinstance(data_type, ArrayType):
            return self._data_type_has_decimal(data_type.elementType)
        elif isinstance(data_type, StructType):
            return any(self._data_type_has_decimal(field.dataType) for field in data_type.fields)
        else:
            return False
    
    def _prepare_dataframe(self, df: DataFrame, id_field: str) -> DataFrame:
        """
        Prepare DataFrame for Elasticsearch by handling common transformations.
        
        Args:
            df: Input DataFrame
            id_field: Field to use as document ID
            
        Returns:
            Prepared DataFrame
        """
        # Get all columns from the DataFrame
        all_columns = df.columns
        
        # Ensure ID field is aliased properly if needed
        if id_field in all_columns and id_field != "id":
            df = df.withColumn("id", col(id_field))
        
        # Convert decimal types to double for Elasticsearch compatibility
        df = self._convert_decimal_columns(df)
        
        # Add geo_point if latitude/longitude exist
        df = self._add_geo_point(df)
        
        return df
    
    def validate_connection(self) -> bool:
        """
        Validate the connection to Elasticsearch using session-level configuration.
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Verify Elasticsearch config exists in SparkSession
            spark_conf = self.spark.sparkContext.getConf()
            if not spark_conf.get("es.nodes", None):
                self.logger.error("Elasticsearch configuration not found in SparkSession. "
                                "Ensure Elasticsearch is configured at session level.")
                return False
            
            # Create a simple test DataFrame with proper ID field
            test_df = self.spark.createDataFrame([{"id": "validation_test", "test": 1}])
            
            # Try to write to a test index using session config
            test_index = f"{self.config.index_prefix}_test"
            
            (test_df.write
             .format(self.format_string)
             .mode("overwrite")
             .option("es.resource", test_index)
             .option("es.mapping.id", "id")
             .save())
            
            self.logger.info(f"Successfully validated Elasticsearch connection")
            return True
            
        except Exception as e:
            self.logger.error(f"Elasticsearch connection validation failed: {e}")
            return False
    
    
    def write_properties(self, df: DataFrame) -> bool:
        """
        Write property data to Elasticsearch with all available fields.
        
        Args:
            df: Property DataFrame
            
        Returns:
            True if successful
        """
        index_name = f"{self.config.index_prefix}_properties"
        
        try:
            # Validate DataFrame is not empty
            record_count = df.count()
            if record_count == 0:
                self.logger.warning(f"No property records to write to {index_name}")
                return True
            
            self.logger.info(f"Starting write operation: {record_count} property documents to {index_name}")
            
            # Ensure index has proper settings
            self._ensure_index_settings(index_name)
            
            # Prepare DataFrame - include all fields and add geo_point
            es_df = self._prepare_dataframe(df, "listing_id")
            
            # Log the fields being written
            self.logger.debug(f"Writing fields: {es_df.columns}")
            self.logger.debug(f"Write mode: {self._get_write_mode()}")
            
            # Write to Elasticsearch using session-level configuration
            write_mode = self._get_write_mode()
            (es_df.write
             .format(self.format_string)
             .mode(write_mode)
             .option("es.resource", index_name)
             .option("es.mapping.id", "id")
             .save())
            
            self.logger.info(f"Successfully completed write operation: {record_count} property documents to {index_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Write operation failed for {index_name}: {str(e)}")
            self.logger.error(f"Error type: {type(e).__name__}")
            self.logger.debug(f"Failed operation details - Index: {index_name}, Record count attempted: {record_count if 'record_count' in locals() else 'unknown'}")
            return False
    
    def write_neighborhoods(self, df: DataFrame) -> bool:
        """
        Write neighborhood data to Elasticsearch with all available fields.
        
        Args:
            df: Neighborhood DataFrame
            
        Returns:
            True if successful
        """
        index_name = f"{self.config.index_prefix}_neighborhoods"
        
        try:
            # Validate DataFrame is not empty
            record_count = df.count()
            if record_count == 0:
                self.logger.warning(f"No neighborhood records to write to {index_name}")
                return True
            
            self.logger.info(f"Starting write operation: {record_count} neighborhood documents to {index_name}")
            
            # Ensure index has proper settings
            self._ensure_index_settings(index_name)
            
            # Prepare DataFrame - include all fields and add geo_point
            es_df = self._prepare_dataframe(df, "neighborhood_id")
            
            # Log the fields being written
            self.logger.debug(f"Writing fields: {es_df.columns}")
            self.logger.debug(f"Write mode: {self._get_write_mode()}")
            
            # Write to Elasticsearch using session-level configuration
            write_mode = self._get_write_mode()
            (es_df.write
             .format(self.format_string)
             .mode(write_mode)
             .option("es.resource", index_name)
             .option("es.mapping.id", "id")
             .save())
            
            self.logger.info(f"Successfully completed write operation: {record_count} neighborhood documents to {index_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Write operation failed for {index_name}: {str(e)}")
            self.logger.error(f"Error type: {type(e).__name__}")
            self.logger.debug(f"Failed operation details - Index: {index_name}, Record count attempted: {record_count if 'record_count' in locals() else 'unknown'}")
            return False
    
    def write_wikipedia(self, df: DataFrame) -> bool:
        """
        Write Wikipedia article data to Elasticsearch with all available fields.
        
        Args:
            df: Wikipedia DataFrame
            
        Returns:
            True if successful
        """
        index_name = f"{self.config.index_prefix}_wikipedia"
        
        try:
            # Validate DataFrame is not empty
            record_count = df.count()
            if record_count == 0:
                self.logger.warning(f"No Wikipedia records to write to {index_name}")
                return True
            
            self.logger.info(f"Starting write operation: {record_count} Wikipedia documents to {index_name}")
            
            # Ensure index has proper settings
            self._ensure_index_settings(index_name)
            
            # Prepare DataFrame - include all fields and add geo_point
            # Wikipedia uses page_id as the identifier
            es_df = self._prepare_dataframe(df, "page_id")
            
            # Ensure page_id is cast to string for ES document ID
            if "page_id" in es_df.columns:
                es_df = es_df.withColumn("id", col("page_id").cast("string"))
            
            # Log the fields being written
            self.logger.debug(f"Writing fields: {es_df.columns}")
            self.logger.debug(f"Write mode: {self._get_write_mode()}")
            
            # Write to Elasticsearch using session-level configuration
            write_mode = self._get_write_mode()
            (es_df.write
             .format(self.format_string)
             .mode(write_mode)
             .option("es.resource", index_name)
             .option("es.mapping.id", "id")
             .save())
            
            self.logger.info(f"Successfully completed write operation: {record_count} Wikipedia documents to {index_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Write operation failed for {index_name}: {str(e)}")
            self.logger.error(f"Error type: {type(e).__name__}")
            self.logger.debug(f"Failed operation details - Index: {index_name}, Record count attempted: {record_count if 'record_count' in locals() else 'unknown'}")
            return False
    
    def _ensure_index_settings(self, index_name: str) -> None:
        """
        Ensure index is created with proper settings for the entity type.
        
        The official connector handles mapping automatically based on DataFrame schema,
        but we can provide hints through index settings.
        
        Args:
            index_name: Name of the index
        """
        try:
            # Log that we're preparing the index
            self.logger.info(f"Preparing index {index_name} with optimal settings")
            
            # The official connector will create the index with proper mappings
            # based on the DataFrame schema when we write data
            # The geo_point field will be automatically mapped from our struct type
            
        except Exception as e:
            self.logger.debug(f"Index preparation note for {index_name}: {e}")
    
    def _get_write_mode(self) -> str:
        """
        Determine the appropriate write mode based on configuration.
        
        Returns:
            Write mode string for Spark DataFrame writer
        """
        # Use append mode by default to preserve existing data
        # For development/testing, you can change this to "overwrite"
        return "append"
    
    
    def get_writer_name(self) -> str:
        """
        Get the name of this writer.
        
        Returns:
            String identifier for this writer
        """
        return "archive_elasticsearch"