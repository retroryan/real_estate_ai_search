"""Graph-specific Silver layer extensions.

This module adds graph-specific computed columns and extraction tables
WITHOUT modifying existing Silver transformers. All changes are additive.
"""

from typing import List
from pydantic import BaseModel, Field, ConfigDict

from squack_pipeline_v2.core.connection import DuckDBConnectionManager, TableIdentifier
from squack_pipeline_v2.core.logging import PipelineLogger, log_stage


class GraphColumnDefinition(BaseModel):
    """Definition for a graph-specific computed column."""
    
    model_config = ConfigDict(frozen=True)
    
    column_name: str = Field(description="Name of the new column")
    expression: str = Field(description="SQL expression for computing the value")
    description: str = Field(description="Description of the column's purpose")


class ExtractionTableDefinition(BaseModel):
    """Definition for an entity extraction table."""
    
    model_config = ConfigDict(frozen=True)
    
    table_name: str = Field(description="Name of the extraction table")
    source_table: str = Field(description="Source table to extract from")
    query: str = Field(description="SQL query to create the extraction table")
    description: str = Field(description="Description of the table's purpose")


class GraphExtensionMetadata(BaseModel):
    """Metadata for graph extensions applied."""
    
    model_config = ConfigDict(frozen=True)
    
    entity_type: str = Field(description="Type of entity being extended")
    columns_added: List[str] = Field(default_factory=list, description="Graph columns added")
    tables_created: List[str] = Field(default_factory=list, description="Extraction tables created")


class SilverGraphExtensions:
    """Adds graph-specific extensions to Silver layer tables.
    
    This class is purely additive - it only adds new columns and tables
    without modifying existing structures.
    """
    
    def __init__(self, connection_manager: DuckDBConnectionManager):
        """Initialize graph extensions.
        
        Args:
            connection_manager: DuckDB connection manager
        """
        self.connection_manager = connection_manager
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
    
    @log_stage("Graph Extensions: Property columns")
    def extend_properties(self, table_name: str) -> GraphExtensionMetadata:
        """Add graph-specific columns to properties table.
        
        Args:
            table_name: Silver properties table to extend
            
        Returns:
            Metadata about extensions applied
        """
        metadata = GraphExtensionMetadata(entity_type="property")
        
        # Define graph columns to add
        columns = [
            GraphColumnDefinition(
                column_name="graph_node_id",
                expression="'property:' || listing_id",
                description="Namespaced ID for Neo4j nodes"
            ),
            GraphColumnDefinition(
                column_name="city_normalized",
                expression="""
                    CASE 
                        WHEN UPPER(address.city) = 'SF' THEN 'San Francisco'
                        WHEN UPPER(address.city) = 'LA' THEN 'Los Angeles'
                        WHEN UPPER(address.city) = 'NYC' THEN 'New York'
                        ELSE address.city
                    END
                """,
                description="Normalized city name for relationship building"
            ),
            GraphColumnDefinition(
                column_name="state_normalized",
                expression="UPPER(TRIM(address.state))",
                description="Normalized state abbreviation"
            ),
            GraphColumnDefinition(
                column_name="zip_code_clean",
                expression="SUBSTRING(address.zip_code, 1, 5)",
                description="5-digit zip code for geographic hierarchy"
            ),
            GraphColumnDefinition(
                column_name="price_range_category",
                expression="""
                    CASE 
                        WHEN price < 250000 THEN 'under_250k'
                        WHEN price < 500000 THEN '250k_500k'
                        WHEN price < 750000 THEN '500k_750k'
                        WHEN price < 1000000 THEN '750k_1m'
                        WHEN price < 2000000 THEN '1m_2m'
                        ELSE 'over_2m'
                    END
                """,
                description="Price range category for classification"
            )
        ]
        
        # Recreate table with additional computed columns since DuckDB doesn't support ALTER TABLE ADD COLUMN AS
        temp_table = f"{table_name}_temp"
        
        # Build column expressions
        column_exprs = []
        for col_def in columns:
            column_exprs.append(f"({col_def.expression}) AS {col_def.column_name}")
            metadata.columns_added.append(col_def.column_name)
        
        # Create new table with computed columns
        query = f"""
        CREATE OR REPLACE TABLE {temp_table} AS 
        SELECT 
            *,
            {','.join(column_exprs)}
        FROM {table_name}
        """
        
        try:
            self.connection_manager.execute(query)
            # Replace original table
            self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
            self.connection_manager.execute(f"ALTER TABLE {temp_table} RENAME TO {table_name}")
            
            self.logger.debug(f"Extended {table_name} with {len(metadata.columns_added)} graph columns")
        except Exception as e:
            self.logger.warning(f"Could not extend {table_name}: {e}")
            metadata.columns_added = []
        
        return metadata
    
    @log_stage("Graph Extensions: Neighborhood columns")
    def extend_neighborhoods(self, table_name: str) -> GraphExtensionMetadata:
        """Add graph-specific columns to neighborhoods table.
        
        Args:
            table_name: Silver neighborhoods table to extend
            
        Returns:
            Metadata about extensions applied
        """
        metadata = GraphExtensionMetadata(entity_type="neighborhood")
        
        columns = [
            GraphColumnDefinition(
                column_name="graph_node_id",
                expression="'neighborhood:' || neighborhood_id",
                description="Namespaced ID for Neo4j nodes"
            ),
            GraphColumnDefinition(
                column_name="city_normalized",
                expression="""
                    CASE 
                        WHEN UPPER(city) = 'SF' THEN 'San Francisco'
                        WHEN UPPER(city) = 'LA' THEN 'Los Angeles'
                        WHEN UPPER(city) = 'NYC' THEN 'New York'
                        ELSE city
                    END
                """,
                description="Normalized city name"
            ),
            GraphColumnDefinition(
                column_name="state_normalized",
                expression="UPPER(TRIM(state))",
                description="Normalized state abbreviation"
            )
        ]
        
        # Recreate table with additional computed columns
        temp_table = f"{table_name}_temp"
        
        # Build column expressions
        column_exprs = []
        for col_def in columns:
            column_exprs.append(f"({col_def.expression}) AS {col_def.column_name}")
            metadata.columns_added.append(col_def.column_name)
        
        # Create new table with computed columns
        query = f"""
        CREATE OR REPLACE TABLE {temp_table} AS 
        SELECT 
            *,
            {','.join(column_exprs)}
        FROM {table_name}
        """
        
        try:
            self.connection_manager.execute(query)
            # Replace original table
            self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
            self.connection_manager.execute(f"ALTER TABLE {temp_table} RENAME TO {table_name}")
            
            self.logger.debug(f"Extended {table_name} with {len(metadata.columns_added)} graph columns")
        except Exception as e:
            self.logger.warning(f"Could not extend {table_name}: {e}")
            metadata.columns_added = []
        
        return metadata
    
    @log_stage("Graph Extensions: Wikipedia columns")
    def extend_wikipedia(self, table_name: str) -> GraphExtensionMetadata:
        """Add graph-specific columns to wikipedia table.
        
        Args:
            table_name: Silver wikipedia table to extend
            
        Returns:
            Metadata about extensions applied
        """
        metadata = GraphExtensionMetadata(entity_type="wikipedia")
        
        columns = [
            GraphColumnDefinition(
                column_name="graph_node_id",
                expression="'wikipedia:' || page_id",
                description="Namespaced ID for Neo4j nodes"
            )
        ]
        
        # Recreate table with additional computed columns
        temp_table = f"{table_name}_temp"
        
        # Build column expressions
        column_exprs = []
        for col_def in columns:
            column_exprs.append(f"({col_def.expression}) AS {col_def.column_name}")
            metadata.columns_added.append(col_def.column_name)
        
        # Create new table with computed columns
        query = f"""
        CREATE OR REPLACE TABLE {temp_table} AS 
        SELECT 
            *,
            {','.join(column_exprs)}
        FROM {table_name}
        """
        
        try:
            self.connection_manager.execute(query)
            # Replace original table
            self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
            self.connection_manager.execute(f"ALTER TABLE {temp_table} RENAME TO {table_name}")
            
            self.logger.debug(f"Extended {table_name} with {len(metadata.columns_added)} graph columns")
        except Exception as e:
            self.logger.warning(f"Could not extend {table_name}: {e}")
            metadata.columns_added = []
        
        return metadata
    
    @log_stage("Graph Extensions: Create extraction tables")
    def create_extraction_tables(self) -> List[str]:
        """Create entity extraction tables for graph relationships.
        
        Returns:
            List of tables created
        """
        tables_created = []
        
        # Define extraction tables
        extractions = [
            ExtractionTableDefinition(
                table_name="silver_features",
                source_table="silver_properties",
                query="""
                    CREATE TABLE IF NOT EXISTS silver_features AS
                    WITH feature_list AS (
                        SELECT 
                            listing_id,
                            UNNEST(features) as feature
                        FROM silver_properties
                        WHERE features IS NOT NULL AND ARRAY_LENGTH(features) > 0
                    )
                    SELECT DISTINCT
                        LOWER(TRIM(feature)) as feature_id,
                        TRIM(feature) as feature_name,
                        COUNT(*) as occurrence_count
                    FROM feature_list
                    GROUP BY 1, 2
                """,
                description="Extracted features from properties"
            ),
            ExtractionTableDefinition(
                table_name="silver_property_types",
                source_table="silver_properties",
                query="""
                    CREATE TABLE IF NOT EXISTS silver_property_types AS
                    SELECT DISTINCT
                        LOWER(property_type) as type_id,
                        property_type as type_name,
                        COUNT(*) as property_count
                    FROM silver_properties
                    WHERE property_type IS NOT NULL
                    GROUP BY 1, 2
                """,
                description="Extracted property types"
            ),
            ExtractionTableDefinition(
                table_name="silver_price_ranges",
                source_table="silver_properties",
                query="""
                    CREATE TABLE IF NOT EXISTS silver_price_ranges AS
                    SELECT DISTINCT
                        CASE 
                            WHEN price < 250000 THEN 'under_250k'
                            WHEN price < 500000 THEN '250k_500k'
                            WHEN price < 750000 THEN '500k_750k'
                            WHEN price < 1000000 THEN '750k_1m'
                            WHEN price < 2000000 THEN '1m_2m'
                            ELSE 'over_2m'
                        END as range_id,
                        CASE 
                            WHEN price < 250000 THEN 'Under $250K'
                            WHEN price < 500000 THEN '$250K-$500K'
                            WHEN price < 750000 THEN '$500K-$750K'
                            WHEN price < 1000000 THEN '$750K-$1M'
                            WHEN price < 2000000 THEN '$1M-$2M'
                            ELSE 'Over $2M'
                        END as range_label,
                        MIN(price) as min_price,
                        MAX(price) as max_price,
                        COUNT(*) as property_count
                    FROM silver_properties
                    GROUP BY 1, 2
                """,
                description="Price range categories"
            ),
            ExtractionTableDefinition(
                table_name="silver_cities",
                source_table="silver_properties",
                query="""
                    CREATE TABLE IF NOT EXISTS silver_cities AS
                    SELECT DISTINCT
                        city_normalized || '_' || state_normalized as city_id,
                        city_normalized as name,
                        state_normalized as state
                    FROM silver_properties
                    WHERE city_normalized IS NOT NULL 
                      AND state_normalized IS NOT NULL
                """,
                description="Extracted cities from properties"
            ),
            ExtractionTableDefinition(
                table_name="silver_states",
                source_table="silver_properties",
                query="""
                    CREATE TABLE IF NOT EXISTS silver_states AS
                    SELECT DISTINCT
                        state_normalized as state_id,
                        state_normalized as abbreviation
                    FROM silver_properties
                    WHERE state_normalized IS NOT NULL
                """,
                description="Extracted states from properties"
            ),
            ExtractionTableDefinition(
                table_name="silver_zip_codes",
                source_table="silver_properties",
                query="""
                    CREATE TABLE IF NOT EXISTS silver_zip_codes AS
                    SELECT DISTINCT
                        zip_code_clean as zip_code,
                        city_normalized,
                        state_normalized
                    FROM silver_properties
                    WHERE zip_code_clean IS NOT NULL
                """,
                description="Extracted zip codes from properties"
            )
        ]
        
        # Create each extraction table
        for table_def in extractions:
            try:
                # Drop existing table if it exists
                drop_query = f"DROP TABLE IF EXISTS {table_def.table_name}"
                self.connection_manager.execute(drop_query)
                
                # Create new extraction table
                self.connection_manager.execute(table_def.query)
                tables_created.append(table_def.table_name)
                
                # Log count
                count_query = f"SELECT COUNT(*) FROM {table_def.table_name}"
                count = self.connection_manager.execute(count_query).fetchone()[0]
                self.logger.info(f"Created {table_def.table_name}: {count} records - {table_def.description}")
                
            except Exception as e:
                self.logger.error(f"Failed to create {table_def.table_name}: {e}")
        
        return tables_created
    
    @log_stage("Graph Extensions: Apply all")
    def apply_all_extensions(self) -> dict:
        """Apply all graph extensions to Silver layer.
        
        Returns:
            Summary of all extensions applied
        """
        summary = {
            "properties": None,
            "neighborhoods": None,
            "wikipedia": None,
            "extraction_tables": []
        }
        
        # Extend main entity tables if they exist
        if self.connection_manager.table_exists(TableIdentifier(name="silver_properties")):
            summary["properties"] = self.extend_properties("silver_properties")
        
        if self.connection_manager.table_exists(TableIdentifier(name="silver_neighborhoods")):
            summary["neighborhoods"] = self.extend_neighborhoods("silver_neighborhoods")
        
        if self.connection_manager.table_exists(TableIdentifier(name="silver_wikipedia")):
            summary["wikipedia"] = self.extend_wikipedia("silver_wikipedia")
        
        # Create extraction tables
        summary["extraction_tables"] = self.create_extraction_tables()
        
        self.logger.info(f"Graph extensions complete: {len(summary['extraction_tables'])} extraction tables created")
        
        return summary