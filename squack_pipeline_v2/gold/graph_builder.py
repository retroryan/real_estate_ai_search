"""Graph-specific Gold layer builder.

This module creates graph node and relationship tables in the Gold layer
using DuckDB's native SQL capabilities. All changes are additive.
"""

from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from squack_pipeline_v2.core.connection import DuckDBConnectionManager
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
        
        # Check if silver_properties table exists with embeddings
        check_embedding = """
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_name = 'silver_properties'
        """
        has_embedding_table = self.connection_manager.execute(check_embedding).fetchone()[0] > 0
        
        # Create property nodes table with embeddings if available
        if has_embedding_table:
            query = f"""
            CREATE TABLE {table_name} AS
            SELECT 
                p.listing_id,
                p.neighborhood_id,
                
                p.bedrooms,
                p.bathrooms,
                p.square_feet,
                p.property_type,
                p.year_built,
                p.lot_size,
                
                p.price as listing_price,
                p.price_per_sqft,
                
                p.address.street as street_address,
                p.address.city as city,
                p.address.state as state,
                p.address.zip_code as zip_code,
                p.address.location[1] as longitude,
                p.address.location[2] as latitude,
                
                p.description,
                p.features,
                p.virtual_tour_url,
                p.images,
                
                p.listing_date,
                p.days_on_market,
                
                s.embedding_vector as embedding,
                
                'Property' as node_label,
                'property:' || p.listing_id as graph_node_id
                
            FROM gold_properties p
            LEFT JOIN silver_properties s ON p.listing_id = s.listing_id
            WHERE p.listing_id IS NOT NULL
            """
        else:
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
                
                price as listing_price,
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
                
                NULL::FLOAT[] as embedding,
                
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
        
        # Check if silver_neighborhoods table exists with embeddings
        check_embedding = """
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_name = 'silver_neighborhoods'
        """
        has_embedding_table = self.connection_manager.execute(check_embedding).fetchone()[0] > 0
        
        if has_embedding_table:
            query = f"""
            CREATE TABLE {table_name} AS
            SELECT
                n.neighborhood_id,
                n.name,
                n.city,
                n.state,
                n.population,
                n.walkability_score,
                n.school_rating,
                NULL::FLOAT as crime_index,  -- Not available in current schema
                n.description,
                n.center_latitude as latitude,
                n.center_longitude as longitude,
                s.embedding_vector as embedding,
                'Neighborhood' as node_label,
                'neighborhood:' || n.neighborhood_id as graph_node_id
            FROM gold_neighborhoods n
            LEFT JOIN silver_neighborhoods s ON n.neighborhood_id = s.neighborhood_id
            WHERE n.neighborhood_id IS NOT NULL
            """
        else:
            query = f"""
            CREATE TABLE {table_name} AS
            SELECT
                neighborhood_id,
                name,
                city,
                state,
                population,
                walkability_score,
                school_rating,
                NULL::FLOAT as crime_index,  -- Not available in current schema
                description,
                center_latitude as latitude,
                center_longitude as longitude,
                NULL::FLOAT[] as embedding,
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
        
        # Always expect silver_wikipedia to exist
        # TODO - add wikipedia short and long summaries to gold_wikipedia
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT
            w.page_id as wikipedia_id,
            w.title,
            w.full_content as content,
            w.categories,
            w.neighborhood_ids,
            w.neighborhood_names,
            w.primary_neighborhood_name,
            w.neighborhood_count,
            s.embedding_vector as embedding,
            'WikipediaArticle' as node_label,
            'wikipedia:' || w.page_id as graph_node_id
        FROM gold_wikipedia w
        LEFT JOIN silver_wikipedia s ON w.page_id = s.page_id
        WHERE w.page_id IS NOT NULL
        """
        
        self.connection_manager.execute(query)
        
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} Wikipedia nodes")
        
        return table_name
    
    
    @log_stage("Graph Builder: County nodes")
    def build_county_nodes(self) -> str:
        """Build county node table from canonical location data.
        
        Returns:
            Name of the created table
        """
        table_name = "gold_graph_counties"
        
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Use canonical location data directly
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT DISTINCT
            county_id,
            county as name,
            state,
            'County' as node_label,
            'county:' || county_id as graph_node_id
        FROM gold_locations
        WHERE county IS NOT NULL 
        AND state IS NOT NULL
        """
        
        self.connection_manager.execute(query)
        
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} county nodes")
        
        return table_name
    
    @log_stage("Graph Builder: Feature nodes")
    def build_feature_nodes(self) -> str:
        """Build feature nodes from property features.
        
        Returns:
            Name of the created table
        """
        table_name = "gold_graph_features"
        
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Extract unique features from properties
        query = f"""
        CREATE TABLE {table_name} AS
        WITH unnested_features AS (
            SELECT DISTINCT TRIM(unnest(features)) as feature_name
            FROM gold_properties
            WHERE features IS NOT NULL AND array_length(features) > 0
        )
        SELECT 
            LOWER(REPLACE(feature_name, ' ', '_')) as feature_id,
            feature_name as name,
            'general' as category,  -- Simple default, can be enriched later
            'Feature' as node_label,
            'feature:' || LOWER(REPLACE(feature_name, ' ', '_')) as graph_node_id
        FROM unnested_features
        WHERE feature_name IS NOT NULL
        """
        
        self.connection_manager.execute(query)
        
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} feature nodes")
        
        return table_name
    
    @log_stage("Graph Builder: City nodes")
    def build_city_nodes(self) -> str:
        """Build city nodes from canonical location data.
        
        Returns:
            Name of the created table
        """
        table_name = "gold_graph_cities"
        
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Use canonical location data directly
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT DISTINCT
            city_id,
            city as name,
            state,
            county,
            'City' as node_label,
            'city:' || city_id as graph_node_id
        FROM gold_locations
        WHERE city IS NOT NULL 
        AND state IS NOT NULL
        AND (location_type = 'city' OR location_type = 'neighborhood')
        """
        
        self.connection_manager.execute(query)
        
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} city nodes")
        
        return table_name
    
    @log_stage("Graph Builder: State nodes")
    def build_state_nodes(self) -> str:
        """Build state nodes from canonical location data.
        
        Returns:
            Name of the created table
        """
        table_name = "gold_graph_states"
        
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Use canonical location data directly
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT DISTINCT
            state_id,
            state as state_code,
            state as state_name,
            'State' as node_label,
            'state:' || LOWER(REPLACE(state, ' ', '_')) as graph_node_id
        FROM gold_locations
        WHERE state IS NOT NULL
        """
        
        self.connection_manager.execute(query)
        
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} state nodes")
        
        return table_name
    
    @log_stage("Graph Builder: ZIP code nodes")
    def build_zip_code_nodes(self) -> str:
        """Build ZIP code nodes from canonical location data.
        
        Returns:
            Name of the created table
        """
        table_name = "gold_graph_zip_codes"
        
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Use canonical location data directly
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT DISTINCT
            zip_code as zip_code_id,
            zip_code,
            city,
            county,
            state,
            zip_code_status,
            'ZipCode' as node_label,
            'zip:' || zip_code as graph_node_id
        FROM gold_locations
        WHERE zip_code IS NOT NULL 
        AND zip_code_status = 'valid'
        """
        
        self.connection_manager.execute(query)
        
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} ZIP code nodes")
        
        return table_name
    
    @log_stage("Graph Builder: Property type nodes")
    def build_property_type_nodes(self) -> str:
        """Build property type nodes from properties.
        
        Returns:
            Name of the created table
        """
        table_name = "gold_graph_property_types"
        
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Extract unique property types
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT 
            LOWER(REPLACE(LOWER(property_type), ' ', '_')) as property_type_id,
            LOWER(property_type) as type_name,
            COUNT(*) as property_count,
            'PropertyType' as node_label,
            'type:' || LOWER(REPLACE(LOWER(property_type), ' ', '_')) as graph_node_id
        FROM gold_properties
        WHERE property_type IS NOT NULL
        GROUP BY LOWER(property_type)
        """
        
        self.connection_manager.execute(query)
        
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} property type nodes")
        
        return table_name
    
    @log_stage("Graph Builder: Price range nodes")
    def build_price_range_nodes(self) -> str:
        """Build price range nodes based on property prices.
        
        Returns:
            Name of the created table
        """
        table_name = "gold_graph_price_ranges"
        
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Create price range buckets
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT 
            'range:' || LOWER(REPLACE(range_label, ' ', '_')) as price_range_id,
            range_label,
            min_price,
            max_price,
            COUNT(*) as property_count,
            'PriceRange' as node_label,
            'range:' || LOWER(REPLACE(range_label, ' ', '_')) as graph_node_id
        FROM (
            SELECT 
                CASE 
                    WHEN price < 500000 THEN 'Under $500K'
                    WHEN price >= 500000 AND price < 750000 THEN '$500K-$750K'
                    WHEN price >= 750000 AND price < 1000000 THEN '$750K-$1M'
                    WHEN price >= 1000000 AND price < 1500000 THEN '$1M-$1.5M'
                    WHEN price >= 1500000 AND price < 2000000 THEN '$1.5M-$2M'
                    ELSE 'Over $2M'
                END as range_label,
                CASE 
                    WHEN price < 500000 THEN 0
                    WHEN price >= 500000 AND price < 750000 THEN 500000
                    WHEN price >= 750000 AND price < 1000000 THEN 750000
                    WHEN price >= 1000000 AND price < 1500000 THEN 1000000
                    WHEN price >= 1500000 AND price < 2000000 THEN 1500000
                    ELSE 2000000
                END as min_price,
                CASE 
                    WHEN price < 500000 THEN 500000
                    WHEN price >= 500000 AND price < 750000 THEN 750000
                    WHEN price >= 750000 AND price < 1000000 THEN 1000000
                    WHEN price >= 1000000 AND price < 1500000 THEN 1500000
                    WHEN price >= 1500000 AND price < 2000000 THEN 2000000
                    ELSE 999999999
                END as max_price,
                listing_id
            FROM gold_properties
            WHERE price IS NOT NULL AND price > 0
        ) price_ranges
        GROUP BY range_label, min_price, max_price
        ORDER BY min_price
        """
        
        self.connection_manager.execute(query)
        
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} price range nodes")
        
        return table_name
    
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
            'feature:' || LOWER(REPLACE(TRIM(unnest(p.features)), ' ', '_')) as to_id,
            'HAS_FEATURE' as relationship_type
        FROM gold_properties p
        WHERE p.features IS NOT NULL AND array_length(p.features) > 0
        """
        
        self.connection_manager.execute(query)
        
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} HAS_FEATURE relationships")
        
        return table_name
    
    @log_stage("Graph Builder: PART_OF relationships")
    def build_part_of_relationships(self) -> str:
        """Build PART_OF relationships (Neighborhood -> City).
        
        Returns:
            Name of the created table
        """
        table_name = "gold_graph_rel_part_of"
        
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT DISTINCT
            'neighborhood:' || neighborhood_id as from_id,
            'city:' || LOWER(REPLACE(city || '_' || state, ' ', '_')) as to_id,
            'PART_OF' as relationship_type
        FROM gold_neighborhoods
        WHERE city IS NOT NULL AND state IS NOT NULL
        """
        
        self.connection_manager.execute(query)
        
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} PART_OF relationships")
        
        return table_name
    
    @log_stage("Graph Builder: IN_COUNTY relationships")
    def build_in_county_relationships(self) -> str:
        """Build IN_COUNTY relationships (Neighborhood -> County).
        
        Returns:
            Name of the created table
        """
        table_name = "gold_graph_rel_in_county"
        
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT DISTINCT
            'neighborhood:' || neighborhood_id as from_id,
            LOWER(REPLACE(wikipedia_correlations.parent_geography.county_wiki.title, ' ', '_')) as to_id,
            'IN_COUNTY' as relationship_type
        FROM gold_neighborhoods
        WHERE wikipedia_correlations.parent_geography.county_wiki.title IS NOT NULL
        """
        
        self.connection_manager.execute(query)
        
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} IN_COUNTY relationships")
        
        return table_name
    
    @log_stage("Graph Builder: DESCRIBES relationships")
    def build_describes_relationships(self) -> str:
        """Build DESCRIBES relationships (Wikipedia -> Neighborhood).
        
        Returns:
            Name of the created table
        """
        table_name = "gold_graph_rel_describes"
        
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Wikipedia articles describe neighborhoods based on neighborhood associations
        query = f"""
        CREATE TABLE {table_name} AS
        WITH wikipedia_neighborhoods AS (
            -- Unnest the neighborhood associations from Wikipedia articles
            SELECT 
                w.page_id,
                unnest(w.neighborhood_ids) as neighborhood_id
            FROM gold_wikipedia w
            WHERE w.neighborhood_ids IS NOT NULL 
                AND array_length(w.neighborhood_ids) > 0
        )
        SELECT DISTINCT
            'wikipedia:' || CAST(wn.page_id AS VARCHAR) as from_id,
            'neighborhood:' || wn.neighborhood_id as to_id,
            'DESCRIBES' as relationship_type,
            1.0 as confidence
        FROM wikipedia_neighborhoods wn
        WHERE wn.page_id IS NOT NULL AND wn.neighborhood_id IS NOT NULL
        """
        
        self.connection_manager.execute(query)
        
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} DESCRIBES relationships")
        
        return table_name
    
    @log_stage("Graph Builder: OF_TYPE relationships")
    def build_of_type_relationships(self) -> str:
        """Build OF_TYPE relationships (Property -> PropertyType).
        
        Returns:
            Name of the created table
        """
        table_name = "gold_graph_rel_of_type"
        
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT DISTINCT
            'property:' || listing_id as from_id,
            'type:' || LOWER(REPLACE(property_type, ' ', '_')) as to_id,
            'OF_TYPE' as relationship_type
        FROM gold_properties
        WHERE property_type IS NOT NULL
        """
        
        self.connection_manager.execute(query)
        
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} OF_TYPE relationships")
        
        return table_name
    
    @log_stage("Graph Builder: IN_PRICE_RANGE relationships")
    def build_in_price_range_relationships(self) -> str:
        """Build IN_PRICE_RANGE relationships (Property -> PriceRange).
        
        Returns:
            Name of the created table
        """
        table_name = "gold_graph_rel_in_price_range"
        
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT DISTINCT
            'property:' || listing_id as from_id,
            'range:' || LOWER(REPLACE(
                CASE 
                    WHEN price < 500000 THEN 'Under $500K'
                    WHEN price >= 500000 AND price < 750000 THEN '$500K-$750K'
                    WHEN price >= 750000 AND price < 1000000 THEN '$750K-$1M'
                    WHEN price >= 1000000 AND price < 1500000 THEN '$1M-$1.5M'
                    WHEN price >= 1500000 AND price < 2000000 THEN '$1.5M-$2M'
                    ELSE 'Over $2M'
                END, ' ', '_'
            )) as to_id,
            'IN_PRICE_RANGE' as relationship_type
        FROM gold_properties
        WHERE price IS NOT NULL AND price > 0
        """
        
        self.connection_manager.execute(query)
        
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} IN_PRICE_RANGE relationships")
        
        return table_name
    
    @log_stage("Graph Builder: IN_ZIP_CODE relationships")
    def build_in_zip_code_relationships(self) -> str:
        """Build IN_ZIP_CODE relationships (Property -> ZipCode).
        
        Returns:
            Name of the created table
        """
        table_name = "gold_graph_rel_in_zip_code"
        
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT DISTINCT
            'property:' || listing_id as from_id,
            'zip:' || address.zip_code as to_id,
            'IN_ZIP_CODE' as relationship_type
        FROM gold_properties
        WHERE address.zip_code IS NOT NULL
        """
        
        self.connection_manager.execute(query)
        
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} IN_ZIP_CODE relationships")
        
        return table_name
    
    @log_stage("Graph Builder: Neighborhood IN_ZIP_CODE relationships")
    def build_neighborhood_in_zip_relationships(self) -> str:
        """Build IN_ZIP_CODE relationships (Neighborhood -> ZipCode).
        
        Returns:
            Name of the created table
        """
        table_name = "gold_graph_rel_neighborhood_in_zip"
        
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Derive neighborhood to ZIP relationships from properties
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT DISTINCT
            'neighborhood:' || p.neighborhood_id as from_id,
            'zip:' || p.address.zip_code as to_id,
            'IN_ZIP_CODE' as relationship_type
        FROM gold_properties p
        WHERE p.neighborhood_id IS NOT NULL 
        AND p.address.zip_code IS NOT NULL
        """
        
        self.connection_manager.execute(query)
        
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} Neighborhood IN_ZIP_CODE relationships")
        
        return table_name
    
    @log_stage("Graph Builder: Geographic hierarchy relationships")
    def build_geographic_hierarchy_relationships(self) -> str:
        """Build geographic hierarchy relationships from location data.
        
        Creates IN_CITY, IN_COUNTY, IN_STATE relationships.
        
        Returns:
            Name of the created table
        """
        table_name = "gold_graph_geographic_hierarchy"
        
        self.connection_manager.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Build hierarchy relationships directly from location data
        query = f"""
        CREATE TABLE {table_name} AS
        SELECT * FROM (
            -- Neighborhood IN_CITY relationships
            SELECT 
                'neighborhood:' || neighborhood_id as from_id,
                'city:' || city_id as to_id,
                'IN_CITY' as relationship_type
            FROM gold_locations
            WHERE location_type = 'neighborhood' 
            AND neighborhood_id IS NOT NULL 
            AND city_id IS NOT NULL
            
            UNION ALL
            
            -- City IN_COUNTY relationships  
            SELECT 
                'city:' || city_id as from_id,
                'county:' || county_id as to_id,
                'IN_COUNTY' as relationship_type
            FROM gold_locations
            WHERE city_id IS NOT NULL 
            AND county_id IS NOT NULL
            
            UNION ALL
            
            -- County IN_STATE relationships
            SELECT 
                'county:' || county_id as from_id,
                'state:' || LOWER(REPLACE(state, ' ', '_')) as to_id,
                'IN_STATE' as relationship_type
            FROM gold_locations
            WHERE county_id IS NOT NULL 
            AND state IS NOT NULL
            
            UNION ALL
            
            -- ZIP IN_CITY relationships
            SELECT DISTINCT
                'zip:' || zip_code as from_id,
                'city:' || city_id as to_id,
                'IN_CITY' as relationship_type
            FROM gold_locations
            WHERE zip_code IS NOT NULL 
            AND city_id IS NOT NULL
            AND zip_code_status = 'valid'
        ) hierarchy
        """
        
        self.connection_manager.execute(query)
        
        count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        self.logger.info(f"Created {table_name}: {count} geographic hierarchy relationships")
        
        return table_name
    
    @log_stage("Graph Builder: Build all")
    def build_all_graph_tables(self) -> GraphBuildMetadata:
        """Build all graph node and relationship tables.
        
        Returns:
            Metadata about the build process
        """
        start_time = datetime.now()
        metadata = GraphBuildMetadata()
        
        # Build all node tables (simplified - no existence checks)
        self.logger.info("Building node tables...")
        
        # Core entity nodes
        metadata.node_tables.append(self.build_property_nodes())
        metadata.node_tables.append(self.build_neighborhood_nodes()) 
        metadata.node_tables.append(self.build_wikipedia_nodes())
        
        # Property-derived nodes
        metadata.node_tables.append(self.build_feature_nodes())
        metadata.node_tables.append(self.build_property_type_nodes())
        metadata.node_tables.append(self.build_price_range_nodes())
        
        # Geographic hierarchy nodes from location data
        metadata.node_tables.append(self.build_zip_code_nodes())
        metadata.node_tables.append(self.build_city_nodes())
        metadata.node_tables.append(self.build_county_nodes())
        metadata.node_tables.append(self.build_state_nodes())
        
        # Build all relationship tables
        self.logger.info("Building relationship tables...")
        
        # Property relationships
        metadata.relationship_tables.append(self.build_located_in_relationships())
        metadata.relationship_tables.append(self.build_has_feature_relationships())
        metadata.relationship_tables.append(self.build_of_type_relationships())
        metadata.relationship_tables.append(self.build_in_price_range_relationships())
        metadata.relationship_tables.append(self.build_in_zip_code_relationships())
        
        # Neighborhood relationships  
        metadata.relationship_tables.append(self.build_part_of_relationships())
        metadata.relationship_tables.append(self.build_in_county_relationships())
        metadata.relationship_tables.append(self.build_neighborhood_in_zip_relationships())
        
        # Wikipedia relationships
        metadata.relationship_tables.append(self.build_describes_relationships())
        
        # Geographic hierarchy relationships from location data
        metadata.relationship_tables.append(self.build_geographic_hierarchy_relationships())
        
        # Calculate totals
        for table in metadata.node_tables:
            try:
                count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                metadata.total_nodes += count
            except Exception as e:
                self.logger.warning(f"Could not count nodes in {table}: {e}")
        
        for table in metadata.relationship_tables:
            try:
                count = self.connection_manager.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                metadata.total_relationships += count
            except Exception as e:
                self.logger.warning(f"Could not count relationships in {table}: {e}")
        
        # Calculate build time
        metadata.build_time_seconds = (datetime.now() - start_time).total_seconds()
        
        self.logger.info(
            f"Graph build complete: {len(metadata.node_tables)} node tables with {metadata.total_nodes} nodes, "
            f"{len(metadata.relationship_tables)} relationship tables with {metadata.total_relationships} relationships "
            f"in {metadata.build_time_seconds:.2f}s"
        )
        
        return metadata