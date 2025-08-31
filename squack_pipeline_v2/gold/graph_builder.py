"""Graph-specific Gold layer builder.

This module creates graph node and relationship tables in the Gold layer
using DuckDB's native SQL capabilities. All changes are additive.
"""

from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from squack_pipeline_v2.core.connection import DuckDBConnectionManager, TableIdentifier
from squack_pipeline_v2.core.logging import PipelineLogger, log_stage


class NodeTableDefinition(BaseModel):
    """Definition for a graph node table."""
    
    model_config = ConfigDict(frozen=True)
    
    table_name: str = Field(description="Name of the node table")
    node_label: str = Field(description="Neo4j node label")
    source_table: str = Field(description="Source Gold table")
    query: str = Field(description="SQL query to create the node table")
    key_field: str = Field(description="Primary key field for the node")


class RelationshipTableDefinition(BaseModel):
    """Definition for a graph relationship table."""
    
    model_config = ConfigDict(frozen=True)
    
    table_name: str = Field(description="Name of the relationship table")
    relationship_type: str = Field(description="Neo4j relationship type")
    source_tables: List[str] = Field(description="Source tables for the relationship")
    query: str = Field(description="SQL query to create the relationship table")


class GraphBuildMetadata(BaseModel):
    """Metadata for graph building process."""
    
    model_config = ConfigDict(frozen=False)
    
    node_tables: List[str] = Field(default_factory=list, description="Node tables created")
    relationship_tables: List[str] = Field(default_factory=list, description="Relationship tables created")
    total_nodes: int = Field(default=0, description="Total number of nodes")
    total_relationships: int = Field(default=0, description="Total number of relationships")
    build_time_seconds: float = Field(default=0.0, description="Time taken to build graph tables")


class GoldGraphBuilder:
    """Builds graph-specific tables in the Gold layer.
    
    This class creates separate node and relationship tables optimized for Neo4j
    without modifying existing Gold tables.
    """
    
    def __init__(self, connection_manager: DuckDBConnectionManager):
        """Initialize graph builder.
        
        Args:
            connection_manager: DuckDB connection manager
        """
        self.connection_manager = connection_manager
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
    
    @log_stage("Graph Builder: Property nodes")
    def build_property_nodes(self) -> str:
        """Build property node table for Neo4j.
        
        Returns:
            Name of the created table
        """
        table_name = "gold_graph_properties"
        
        # Drop if exists
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Check if embedding column exists
        check_embedding = """
        SELECT COUNT(*) 
        FROM information_schema.columns 
        WHERE table_name = 'gold_properties' 
        AND column_name = 'embedding'
        """
        has_embedding = self.connection_manager.execute(check_embedding).fetchone()[0] > 0
        
        # Build query with or without embeddings
        embedding_select = "embedding," if has_embedding else "NULL::FLOAT[] as embedding,"
        
        # Create property nodes table
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT 
            listing_id,
            neighborhood_id,
            
            bedrooms,
            bathrooms,
            square_feet,
            property_type,
            year_built,
            lot_size,
            
            price,
            price_per_sqft,
            
            address.street as street_address,
            address.city as city,
            address.state as state,
            address.zip_code as zip_code,
            address.location[1] as longitude,
            address.location[2] as latitude,
            
            description,
            features,
            virtual_tour_url,
            images,
            
            listing_date,
            days_on_market,
            
            {embedding_select}
            
            'Property' as node_label,
            'property:' || listing_id as graph_node_id
            
        FROM gold_properties
        WHERE listing_id IS NOT NULL
        """
        
        self.connection_manager.execute(query)
        
        # Get count
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} property nodes")
        
        return table_name
    
    @log_stage("Graph Builder: Neighborhood nodes")
    def build_neighborhood_nodes(self) -> str:
        """Build neighborhood node table for Neo4j.
        
        Returns:
            Name of the created table
        """
        table_name = "gold_graph_neighborhoods"
        
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Check if embedding column exists
        check_embedding = """
        SELECT COUNT(*) 
        FROM information_schema.columns 
        WHERE table_name = 'gold_neighborhoods' 
        AND column_name = 'embedding'
        """
        has_embedding = self.connection_manager.execute(check_embedding).fetchone()[0] > 0
        
        embedding_select = "embedding," if has_embedding else "NULL::FLOAT[] as embedding,"
        
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT
            neighborhood_id,
            name,
            city,
            state,
            population,
            median_income,
            median_home_price as median_home_value,
            walkability_score,
            school_score as school_rating,
            NULL::FLOAT as crime_index,  -- Not available in current schema
            description,
            center_latitude as latitude,
            center_longitude as longitude,
            {embedding_select}
            'Neighborhood' as node_label,
            'neighborhood:' || neighborhood_id as graph_node_id
        FROM gold_neighborhoods
        WHERE neighborhood_id IS NOT NULL
        """
        
        self.connection_manager.execute(query)
        
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} neighborhood nodes")
        
        return table_name
    
    @log_stage("Graph Builder: Wikipedia nodes")
    def build_wikipedia_nodes(self) -> str:
        """Build Wikipedia node table for Neo4j.
        
        Returns:
            Name of the created table
        """
        table_name = "gold_graph_wikipedia"
        
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Check if embedding column exists
        check_embedding = """
        SELECT COUNT(*) 
        FROM information_schema.columns 
        WHERE table_name = 'gold_wikipedia' 
        AND column_name = 'embedding'
        """
        has_embedding = self.connection_manager.execute(check_embedding).fetchone()[0] > 0
        
        embedding_select = "embedding," if has_embedding else "NULL::FLOAT[] as embedding,"
        
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT
            page_id,
            title,
            full_content as content,
            categories,
            {embedding_select}
            'WikipediaArticle' as node_label,
            'wikipedia:' || page_id as graph_node_id
        FROM gold_wikipedia
        WHERE page_id IS NOT NULL
        """
        
        self.connection_manager.execute(query)
        
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} Wikipedia nodes")
        
        return table_name
    
    @log_stage("Graph Builder: Classification nodes")
    def build_classification_nodes(self) -> List[str]:
        """Build classification node tables (features, property types, etc.).
        
        Returns:
            List of tables created
        """
        tables = []
        
        # Features
        table_name = "gold_graph_features"
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT 
            feature_id,
            feature_name,
            occurrence_count,
            'Feature' as node_label,
            feature_id as graph_node_id
        FROM silver_features
        """
        
        self.connection_manager.execute(query)
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} feature nodes")
        tables.append(table_name)
        
        # Property Types
        table_name = "gold_graph_property_types"
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT
            type_id,
            type_name,
            property_count,
            'PropertyType' as node_label,
            type_id as graph_node_id
        FROM silver_property_types
        """
        
        self.connection_manager.execute(query)
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} property type nodes")
        tables.append(table_name)
        
        # Price Ranges
        table_name = "gold_graph_price_ranges"
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT
            range_id,
            range_label,
            min_price,
            max_price,
            property_count,
            'PriceRange' as node_label,
            range_id as graph_node_id
        FROM silver_price_ranges
        """
        
        self.connection_manager.execute(query)
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} price range nodes")
        tables.append(table_name)
        
        return tables
    
    @log_stage("Graph Builder: Geographic nodes")
    def build_geographic_nodes(self) -> List[str]:
        """Build geographic hierarchy node tables.
        
        Returns:
            List of tables created
        """
        tables = []
        
        # Cities
        table_name = "gold_graph_cities"
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT DISTINCT
            city_id,
            name,
            state,
            'City' as node_label,
            city_id as graph_node_id
        FROM silver_cities
        """
        
        self.connection_manager.execute(query)
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} city nodes")
        tables.append(table_name)
        
        # States
        table_name = "gold_graph_states"
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT DISTINCT
            state_id,
            abbreviation,
            'State' as node_label,
            state_id as graph_node_id
        FROM silver_states
        """
        
        self.connection_manager.execute(query)
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} state nodes")
        tables.append(table_name)
        
        # Zip Codes
        table_name = "gold_graph_zip_codes"
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT DISTINCT
            zip_code,
            city_normalized,
            state_normalized,
            'ZipCode' as node_label,
            zip_code as graph_node_id
        FROM silver_zip_codes
        """
        
        self.connection_manager.execute(query)
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} zip code nodes")
        tables.append(table_name)
        
        return tables
    
    @log_stage("Graph Builder: LOCATED_IN relationships")
    def build_located_in_relationships(self) -> str:
        """Build LOCATED_IN relationships (Property -> Neighborhood).
        
        Returns:
            Name of the created table
        """
        table_name = "gold_graph_rel_located_in"
        
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT 
            'property:' || listing_id as from_id,
            'neighborhood:' || neighborhood_id as to_id,
            'LOCATED_IN' as relationship_type,
            1.0 as weight
        FROM gold_properties
        WHERE neighborhood_id IS NOT NULL
        """
        
        self.connection_manager.execute(query)
        
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} LOCATED_IN relationships")
        
        return table_name
    
    @log_stage("Graph Builder: HAS_FEATURE relationships")
    def build_has_feature_relationships(self) -> str:
        """Build HAS_FEATURE relationships (Property -> Feature).
        
        Returns:
            Name of the created table
        """
        table_name = "gold_graph_rel_has_feature"
        
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT DISTINCT
            'property:' || p.listing_id as from_id,
            LOWER(TRIM(unnest(p.features))) as to_id,
            'HAS_FEATURE' as relationship_type
        FROM gold_properties p
        WHERE p.features IS NOT NULL AND array_length(p.features) > 0
        """
        
        self.connection_manager.execute(query)
        
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} HAS_FEATURE relationships")
        
        return table_name
    
    @log_stage("Graph Builder: Geographic relationships")
    def build_geographic_relationships(self) -> List[str]:
        """Build geographic hierarchy relationships.
        
        Returns:
            List of tables created
        """
        tables = []
        
        # IN_CITY relationships
        table_name = "gold_graph_rel_in_city"
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT DISTINCT
            'property:' || p.listing_id as from_id,
            p.city_normalized || '_' || p.state_normalized as to_id,
            'IN_CITY' as relationship_type
        FROM silver_properties p
        WHERE p.city_normalized IS NOT NULL AND p.state_normalized IS NOT NULL
        """
        
        self.connection_manager.execute(query)
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} IN_CITY relationships")
        tables.append(table_name)
        
        # IN_STATE relationships
        table_name = "gold_graph_rel_in_state"
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT DISTINCT
            city_id as from_id,
            state as to_id,
            'IN_STATE' as relationship_type
        FROM gold_graph_cities
        """
        
        self.connection_manager.execute(query)
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} IN_STATE relationships")
        tables.append(table_name)
        
        # IN_ZIP_CODE relationships
        table_name = "gold_graph_rel_in_zip_code"
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT DISTINCT
            'property:' || p.listing_id as from_id,
            p.zip_code_clean as to_id,
            'IN_ZIP_CODE' as relationship_type
        FROM silver_properties p
        WHERE p.zip_code_clean IS NOT NULL
        """
        
        self.connection_manager.execute(query)
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} IN_ZIP_CODE relationships")
        tables.append(table_name)
        
        return tables
    
    @log_stage("Graph Builder: Classification relationships")
    def build_classification_relationships(self) -> List[str]:
        """Build classification relationships (TYPE_OF, IN_PRICE_RANGE).
        
        Returns:
            List of tables created
        """
        tables = []
        
        # TYPE_OF relationships
        table_name = "gold_graph_rel_type_of"
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT DISTINCT
            'property:' || listing_id as from_id,
            LOWER(property_type) as to_id,
            'TYPE_OF' as relationship_type
        FROM gold_graph_properties
        WHERE property_type IS NOT NULL
        """
        
        self.connection_manager.execute(query)
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} TYPE_OF relationships")
        tables.append(table_name)
        
        # IN_PRICE_RANGE relationships
        table_name = "gold_graph_rel_in_price_range"
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT DISTINCT
            'property:' || p.listing_id as from_id,
            p.price_range_category as to_id,
            'IN_PRICE_RANGE' as relationship_type
        FROM silver_properties p
        WHERE p.price_range_category IS NOT NULL
        """
        
        self.connection_manager.execute(query)
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} IN_PRICE_RANGE relationships")
        tables.append(table_name)
        
        return tables
    
    @log_stage("Graph Builder: Similarity relationships")
    def build_similarity_relationships(self) -> List[str]:
        """Build similarity relationships using embeddings.
        
        Returns:
            List of tables created
        """
        tables = []
        
        # Check if embeddings exist
        has_embeddings_query = """
        SELECT COUNT(*) > 0 as has_embeddings
        FROM gold_graph_properties
        WHERE embedding IS NOT NULL
        LIMIT 1
        """
        
        has_embeddings = self.connection_manager.execute(has_embeddings_query).fetchone()[0]
        
        if has_embeddings:
            # SIMILAR_TO relationships for properties
            table_name = "gold_graph_rel_similar_properties"
            self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            # Use array operations for cosine similarity
            query = f"""
            CREATE TABLE {table_name} AS
            WITH similarity_scores AS (
                SELECT 
                    p1.listing_id as id1,
                    p2.listing_id as id2,
                    list_dot_product(p1.embedding, p2.embedding) / 
                    (sqrt(list_sum(list_transform(p1.embedding, x -> x * x))) * 
                     sqrt(list_sum(list_transform(p2.embedding, x -> x * x)))) as similarity
                FROM gold_graph_properties p1
                CROSS JOIN gold_graph_properties p2
                WHERE p1.listing_id < p2.listing_id
                  AND p1.embedding IS NOT NULL
                  AND p2.embedding IS NOT NULL
                  AND array_length(p1.embedding) > 0
                  AND array_length(p2.embedding) > 0
            )
            SELECT 
                'property:' || id1 as from_id,
                'property:' || id2 as to_id,
                'SIMILAR_TO' as relationship_type,
                similarity as weight
            FROM similarity_scores
            WHERE similarity > 0.85
            ORDER BY similarity DESC
            LIMIT 10000
            """
            
            self.connection_manager.execute(query)
            count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            self.logger.info(f"Created {table_name}: {count} SIMILAR_TO relationships")
            tables.append(table_name)
        else:
            self.logger.warning("No embeddings found - skipping similarity relationships")
        
        return tables
    
    @log_stage("Graph Builder: Build all")
    def build_all_graph_tables(self) -> GraphBuildMetadata:
        """Build all graph node and relationship tables.
        
        Returns:
            Metadata about the build process
        """
        start_time = datetime.now()
        metadata = GraphBuildMetadata()
        
        # Build node tables
        self.logger.info("Building node tables...")
        
        # Check what tables exist
        if self.connection_manager.table_exists(TableIdentifier(name="gold_properties")):
            metadata.node_tables.append(self.build_property_nodes())
        
        if self.connection_manager.table_exists(TableIdentifier(name="gold_neighborhoods")):
            metadata.node_tables.append(self.build_neighborhood_nodes())
        
        if self.connection_manager.table_exists(TableIdentifier(name="gold_wikipedia")):
            metadata.node_tables.append(self.build_wikipedia_nodes())
        
        # Build classification and geographic nodes from extraction tables
        if self.connection_manager.table_exists(TableIdentifier(name="silver_features")):
            metadata.node_tables.extend(self.build_classification_nodes())
        
        if self.connection_manager.table_exists(TableIdentifier(name="silver_cities")):
            metadata.node_tables.extend(self.build_geographic_nodes())
        
        # Build relationship tables
        self.logger.info("Building relationship tables...")
        
        if self.connection_manager.table_exists(TableIdentifier(name="gold_properties")):
            metadata.relationship_tables.append(self.build_located_in_relationships())
            metadata.relationship_tables.append(self.build_has_feature_relationships())
            metadata.relationship_tables.extend(self.build_geographic_relationships())
            metadata.relationship_tables.extend(self.build_classification_relationships())
            metadata.relationship_tables.extend(self.build_similarity_relationships())
        
        # Calculate totals
        for table in metadata.node_tables:
            count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            metadata.total_nodes += count
        
        for table in metadata.relationship_tables:
            count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            metadata.total_relationships += count
        
        # Calculate build time
        metadata.build_time_seconds = (datetime.now() - start_time).total_seconds()
        
        self.logger.info(
            f"Graph build complete: {metadata.total_nodes} nodes, "
            f"{metadata.total_relationships} relationships in {metadata.build_time_seconds:.2f}s"
        )
        
        return metadata