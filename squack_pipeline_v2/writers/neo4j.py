"""Neo4j writer for graph data following DuckDB best practices.

This writer reads from Gold layer graph tables and writes to Neo4j
using the official Neo4j Python driver. All data transformation is
already done in the Gold layer.

Following DuckDB best practices:
- No pandas usage - uses native DuckDB iteration
- Direct memory-efficient access
- Batch processing for large datasets
"""

from typing import Dict, Any, List, Iterator, Tuple
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from neo4j import GraphDatabase, Driver, Session

from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import PipelineLogger, log_stage


class Neo4jConfig(BaseModel):
    """Configuration for Neo4j connection."""
    
    model_config = ConfigDict(frozen=True)
    
    uri: str = Field(description="Neo4j connection URI")
    username: str = Field(default="neo4j", description="Neo4j username")
    password: str = Field(description="Neo4j password")
    database: str = Field(default="neo4j", description="Database name")


class NodeWriteResult(BaseModel):
    """Result of writing nodes to Neo4j."""
    
    model_config = ConfigDict(frozen=True)
    
    entity_type: str = Field(description="Type of entity written")
    table_name: str = Field(description="Source table name")
    records_read: int = Field(description="Records read from DuckDB")
    nodes_created: int = Field(description="Nodes created in Neo4j")
    properties_set: int = Field(description="Properties set in Neo4j")
    duration_seconds: float = Field(description="Time taken")


class RelationshipWriteResult(BaseModel):
    """Result of writing relationships to Neo4j."""
    
    model_config = ConfigDict(frozen=True)
    
    relationship_type: str = Field(description="Type of relationship")
    table_name: str = Field(description="Source table name")
    records_read: int = Field(description="Records read from DuckDB")
    relationships_created: int = Field(description="Relationships created")
    duration_seconds: float = Field(description="Time taken")


class Neo4jWriteMetadata(BaseModel):
    """Complete metadata for Neo4j write operation."""
    
    model_config = ConfigDict(frozen=False)  # Must be mutable to update fields
    
    start_time: datetime = Field(description="When write started")
    end_time: datetime = Field(default=None, description="When write completed")
    total_duration_seconds: float = Field(default=0.0, description="Total time taken")
    node_results: List[NodeWriteResult] = Field(default_factory=list)
    relationship_results: List[RelationshipWriteResult] = Field(default_factory=list)
    total_nodes: int = Field(default=0, description="Total nodes written")
    total_relationships: int = Field(default=0, description="Total relationships written")
    constraints_created: List[str] = Field(default_factory=list)


class Neo4jWriter:
    """Write DuckDB graph tables to Neo4j.
    
    This writer handles all node and relationship types defined in the
    graph builder. All data transformation is done in the Gold layer.
    """
    
    def __init__(
        self,
        config: Neo4jConfig,
        connection_manager: DuckDBConnectionManager
    ):
        """Initialize Neo4j writer.
        
        Args:
            config: Neo4j configuration
            connection_manager: DuckDB connection manager
        """
        self.config = config
        self.connection_manager = connection_manager
        self.driver = GraphDatabase.driver(
            config.uri,
            auth=(config.username, config.password)
        )
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
    
    def close(self):
        """Close Neo4j connection."""
        self.driver.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    @log_stage("Neo4j: Create constraints")
    def create_constraints(self) -> List[str]:
        """Create uniqueness constraints for all node types.
        
        Returns:
            List of constraints created
        """
        constraints = []
        
        with self.driver.session() as session:
            # Core entity constraints
            constraints_to_create = [
                ("Property", "listing_id"),
                ("Neighborhood", "neighborhood_id"),
                ("Wikipedia", "wikipedia_id"),
                ("Feature", "feature_id"),
                ("City", "city_id"),
                ("State", "state_id"),
                ("ZipCode", "zip_code_id"),
                ("County", "county_id"),
                ("PropertyType", "property_type_id"),
                ("PriceRange", "price_range_id")
            ]
            
            for label, property_name in constraints_to_create:
                try:
                    query = f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.{property_name} IS UNIQUE"
                    session.run(query)
                    constraints.append(f"{label}.{property_name}")
                    self.logger.info(f"Created constraint for {label}.{property_name}")
                except Exception as e:
                    self.logger.warning(f"Could not create constraint for {label}.{property_name}: {e}")
        
        return constraints
    
    def _get_records_from_table(self, table_name: str) -> List[Dict[str, Any]]:
        """Get all records from a DuckDB table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            List of records as dictionaries
        """
        from decimal import Decimal
        
        conn = self.connection_manager.get_connection()
        safe_table = DuckDBConnectionManager.safe_identifier(table_name)
        
        # Use DuckDB's native iteration - no pandas
        result = conn.execute(f"SELECT * FROM {safe_table}")
        
        # Convert to list of dicts for Neo4j
        columns = [desc[0] for desc in result.description]
        records = []
        for row in result.fetchall():
            # Convert Decimal to float for Neo4j compatibility
            converted_row = []
            for value in row:
                if isinstance(value, Decimal):
                    converted_row.append(float(value))
                else:
                    converted_row.append(value)
            records.append(dict(zip(columns, converted_row)))
        
        return records
    
    # ============= NODE WRITERS =============
    
    @log_stage("Neo4j: Write Property nodes")
    def write_property_nodes(self) -> NodeWriteResult:
        """Write Property nodes to Neo4j."""
        table_name = "gold_graph_properties"
        start_time = datetime.now()
        
        if not self.connection_manager.table_exists(table_name):
            self.logger.warning(f"Table {table_name} does not exist")
            return NodeWriteResult(
                entity_type="Property",
                table_name=table_name,
                records_read=0,
                nodes_created=0,
                properties_set=0,
                duration_seconds=0.0
            )
        
        records = self._get_records_from_table(table_name)
        
        cypher = """
        UNWIND $nodes AS node
        MERGE (p:Property {listing_id: node.listing_id})
        SET p += node
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, nodes=records)
            summary = result.consume()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return NodeWriteResult(
            entity_type="Property",
            table_name=table_name,
            records_read=len(records),
            nodes_created=summary.counters.nodes_created,
            properties_set=summary.counters.properties_set,
            duration_seconds=duration
        )
    
    @log_stage("Neo4j: Write Neighborhood nodes")
    def write_neighborhood_nodes(self) -> NodeWriteResult:
        """Write Neighborhood nodes to Neo4j."""
        table_name = "gold_graph_neighborhoods"
        start_time = datetime.now()
        
        if not self.connection_manager.table_exists(table_name):
            self.logger.warning(f"Table {table_name} does not exist")
            return NodeWriteResult(
                entity_type="Neighborhood",
                table_name=table_name,
                records_read=0,
                nodes_created=0,
                properties_set=0,
                duration_seconds=0.0
            )
        
        records = self._get_records_from_table(table_name)
        
        cypher = """
        UNWIND $nodes AS node
        MERGE (n:Neighborhood {neighborhood_id: node.neighborhood_id})
        SET n += node
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, nodes=records)
            summary = result.consume()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return NodeWriteResult(
            entity_type="Neighborhood",
            table_name=table_name,
            records_read=len(records),
            nodes_created=summary.counters.nodes_created,
            properties_set=summary.counters.properties_set,
            duration_seconds=duration
        )
    
    @log_stage("Neo4j: Write Wikipedia nodes")
    def write_wikipedia_nodes(self) -> NodeWriteResult:
        """Write Wikipedia nodes to Neo4j."""
        table_name = "gold_graph_wikipedia"
        start_time = datetime.now()
        
        if not self.connection_manager.table_exists(table_name):
            self.logger.warning(f"Table {table_name} does not exist")
            return NodeWriteResult(
                entity_type="Wikipedia",
                table_name=table_name,
                records_read=0,
                nodes_created=0,
                properties_set=0,
                duration_seconds=0.0
            )
        
        records = self._get_records_from_table(table_name)
        
        cypher = """
        UNWIND $nodes AS node
        MERGE (w:Wikipedia {wikipedia_id: node.wikipedia_id})
        SET w += node
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, nodes=records)
            summary = result.consume()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return NodeWriteResult(
            entity_type="Wikipedia",
            table_name=table_name,
            records_read=len(records),
            nodes_created=summary.counters.nodes_created,
            properties_set=summary.counters.properties_set,
            duration_seconds=duration
        )
    
    @log_stage("Neo4j: Write Feature nodes")
    def write_feature_nodes(self) -> NodeWriteResult:
        """Write Feature nodes to Neo4j."""
        table_name = "gold_graph_features"
        start_time = datetime.now()
        
        if not self.connection_manager.table_exists(table_name):
            self.logger.warning(f"Table {table_name} does not exist")
            return NodeWriteResult(
                entity_type="Feature",
                table_name=table_name,
                records_read=0,
                nodes_created=0,
                properties_set=0,
                duration_seconds=0.0
            )
        
        records = self._get_records_from_table(table_name)
        
        cypher = """
        UNWIND $nodes AS node
        MERGE (f:Feature {feature_id: node.feature_id})
        SET f += node
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, nodes=records)
            summary = result.consume()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return NodeWriteResult(
            entity_type="Feature",
            table_name=table_name,
            records_read=len(records),
            nodes_created=summary.counters.nodes_created,
            properties_set=summary.counters.properties_set,
            duration_seconds=duration
        )
    
    @log_stage("Neo4j: Write City nodes")
    def write_city_nodes(self) -> NodeWriteResult:
        """Write City nodes to Neo4j."""
        table_name = "gold_graph_cities"
        start_time = datetime.now()
        
        if not self.connection_manager.table_exists(table_name):
            self.logger.warning(f"Table {table_name} does not exist")
            return NodeWriteResult(
                entity_type="City",
                table_name=table_name,
                records_read=0,
                nodes_created=0,
                properties_set=0,
                duration_seconds=0.0
            )
        
        records = self._get_records_from_table(table_name)
        
        cypher = """
        UNWIND $nodes AS node
        MERGE (c:City {city_id: node.city_id})
        SET c += node
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, nodes=records)
            summary = result.consume()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return NodeWriteResult(
            entity_type="City",
            table_name=table_name,
            records_read=len(records),
            nodes_created=summary.counters.nodes_created,
            properties_set=summary.counters.properties_set,
            duration_seconds=duration
        )
    
    @log_stage("Neo4j: Write State nodes")
    def write_state_nodes(self) -> NodeWriteResult:
        """Write State nodes to Neo4j."""
        table_name = "gold_graph_states"
        start_time = datetime.now()
        
        if not self.connection_manager.table_exists(table_name):
            self.logger.warning(f"Table {table_name} does not exist")
            return NodeWriteResult(
                entity_type="State",
                table_name=table_name,
                records_read=0,
                nodes_created=0,
                properties_set=0,
                duration_seconds=0.0
            )
        
        records = self._get_records_from_table(table_name)
        
        cypher = """
        UNWIND $nodes AS node
        MERGE (s:State {state_id: node.state_id})
        SET s += node
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, nodes=records)
            summary = result.consume()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return NodeWriteResult(
            entity_type="State",
            table_name=table_name,
            records_read=len(records),
            nodes_created=summary.counters.nodes_created,
            properties_set=summary.counters.properties_set,
            duration_seconds=duration
        )
    
    @log_stage("Neo4j: Write ZipCode nodes")
    def write_zip_code_nodes(self) -> NodeWriteResult:
        """Write ZipCode nodes to Neo4j."""
        table_name = "gold_graph_zip_codes"
        start_time = datetime.now()
        
        if not self.connection_manager.table_exists(table_name):
            self.logger.warning(f"Table {table_name} does not exist")
            return NodeWriteResult(
                entity_type="ZipCode",
                table_name=table_name,
                records_read=0,
                nodes_created=0,
                properties_set=0,
                duration_seconds=0.0
            )
        
        records = self._get_records_from_table(table_name)
        
        cypher = """
        UNWIND $nodes AS node
        MERGE (z:ZipCode {zip_code_id: node.zip_code_id})
        SET z += node
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, nodes=records)
            summary = result.consume()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return NodeWriteResult(
            entity_type="ZipCode",
            table_name=table_name,
            records_read=len(records),
            nodes_created=summary.counters.nodes_created,
            properties_set=summary.counters.properties_set,
            duration_seconds=duration
        )
    
    @log_stage("Neo4j: Write County nodes")
    def write_county_nodes(self) -> NodeWriteResult:
        """Write County nodes to Neo4j."""
        table_name = "gold_graph_counties"
        start_time = datetime.now()
        
        if not self.connection_manager.table_exists(table_name):
            self.logger.warning(f"Table {table_name} does not exist")
            return NodeWriteResult(
                entity_type="County",
                table_name=table_name,
                records_read=0,
                nodes_created=0,
                properties_set=0,
                duration_seconds=0.0
            )
        
        records = self._get_records_from_table(table_name)
        
        cypher = """
        UNWIND $nodes AS node
        MERGE (c:County {county_id: node.county_id})
        SET c += node
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, nodes=records)
            summary = result.consume()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return NodeWriteResult(
            entity_type="County",
            table_name=table_name,
            records_read=len(records),
            nodes_created=summary.counters.nodes_created,
            properties_set=summary.counters.properties_set,
            duration_seconds=duration
        )
    
    @log_stage("Neo4j: Write PropertyType nodes")
    def write_property_type_nodes(self) -> NodeWriteResult:
        """Write PropertyType nodes to Neo4j."""
        table_name = "gold_graph_property_types"
        start_time = datetime.now()
        
        if not self.connection_manager.table_exists(table_name):
            self.logger.warning(f"Table {table_name} does not exist")
            return NodeWriteResult(
                entity_type="PropertyType",
                table_name=table_name,
                records_read=0,
                nodes_created=0,
                properties_set=0,
                duration_seconds=0.0
            )
        
        records = self._get_records_from_table(table_name)
        
        cypher = """
        UNWIND $nodes AS node
        MERGE (pt:PropertyType {property_type_id: node.property_type_id})
        SET pt += node
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, nodes=records)
            summary = result.consume()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return NodeWriteResult(
            entity_type="PropertyType",
            table_name=table_name,
            records_read=len(records),
            nodes_created=summary.counters.nodes_created,
            properties_set=summary.counters.properties_set,
            duration_seconds=duration
        )
    
    @log_stage("Neo4j: Write PriceRange nodes")
    def write_price_range_nodes(self) -> NodeWriteResult:
        """Write PriceRange nodes to Neo4j."""
        table_name = "gold_graph_price_ranges"
        start_time = datetime.now()
        
        if not self.connection_manager.table_exists(table_name):
            self.logger.warning(f"Table {table_name} does not exist")
            return NodeWriteResult(
                entity_type="PriceRange",
                table_name=table_name,
                records_read=0,
                nodes_created=0,
                properties_set=0,
                duration_seconds=0.0
            )
        
        records = self._get_records_from_table(table_name)
        
        cypher = """
        UNWIND $nodes AS node
        MERGE (pr:PriceRange {price_range_id: node.price_range_id})
        SET pr += node
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, nodes=records)
            summary = result.consume()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return NodeWriteResult(
            entity_type="PriceRange",
            table_name=table_name,
            records_read=len(records),
            nodes_created=summary.counters.nodes_created,
            properties_set=summary.counters.properties_set,
            duration_seconds=duration
        )
    
    # ============= RELATIONSHIP WRITERS =============
    
    @log_stage("Neo4j: Write LOCATED_IN relationships")
    def write_located_in_relationships(self) -> RelationshipWriteResult:
        """Write LOCATED_IN relationships (Property -> Neighborhood)."""
        table_name = "gold_graph_rel_located_in"
        start_time = datetime.now()
        
        if not self.connection_manager.table_exists(table_name):
            self.logger.warning(f"Table {table_name} does not exist")
            return RelationshipWriteResult(
                relationship_type="LOCATED_IN",
                table_name=table_name,
                records_read=0,
                relationships_created=0,
                duration_seconds=0.0
            )
        
        records = self._get_records_from_table(table_name)
        
        cypher = """
        UNWIND $rels AS rel
        MATCH (p:Property {listing_id: REPLACE(rel.from_id, 'property:', '')})
        MATCH (n:Neighborhood {neighborhood_id: REPLACE(rel.to_id, 'neighborhood:', '')})
        MERGE (p)-[:LOCATED_IN]->(n)
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, rels=records)
            summary = result.consume()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return RelationshipWriteResult(
            relationship_type="LOCATED_IN",
            table_name=table_name,
            records_read=len(records),
            relationships_created=summary.counters.relationships_created,
            duration_seconds=duration
        )
    
    @log_stage("Neo4j: Write HAS_FEATURE relationships")
    def write_has_feature_relationships(self) -> RelationshipWriteResult:
        """Write HAS_FEATURE relationships (Property -> Feature)."""
        table_name = "gold_graph_rel_has_feature"
        start_time = datetime.now()
        
        if not self.connection_manager.table_exists(table_name):
            self.logger.warning(f"Table {table_name} does not exist")
            return RelationshipWriteResult(
                relationship_type="HAS_FEATURE",
                table_name=table_name,
                records_read=0,
                relationships_created=0,
                duration_seconds=0.0
            )
        
        records = self._get_records_from_table(table_name)
        
        cypher = """
        UNWIND $rels AS rel
        MATCH (p:Property {listing_id: REPLACE(rel.from_id, 'property:', '')})
        MATCH (f:Feature {feature_id: REPLACE(rel.to_id, 'feature:', '')})
        MERGE (p)-[:HAS_FEATURE]->(f)
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, rels=records)
            summary = result.consume()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return RelationshipWriteResult(
            relationship_type="HAS_FEATURE",
            table_name=table_name,
            records_read=len(records),
            relationships_created=summary.counters.relationships_created,
            duration_seconds=duration
        )
    
    @log_stage("Neo4j: Write PART_OF relationships")
    def write_part_of_relationships(self) -> RelationshipWriteResult:
        """Write PART_OF relationships (Neighborhood -> City)."""
        table_name = "gold_graph_rel_part_of"
        start_time = datetime.now()
        
        if not self.connection_manager.table_exists(table_name):
            self.logger.warning(f"Table {table_name} does not exist")
            return RelationshipWriteResult(
                relationship_type="PART_OF",
                table_name=table_name,
                records_read=0,
                relationships_created=0,
                duration_seconds=0.0
            )
        
        records = self._get_records_from_table(table_name)
        
        cypher = """
        UNWIND $rels AS rel
        MATCH (n:Neighborhood {neighborhood_id: rel.from_id})
        MATCH (c:City {city_id: rel.to_id})
        MERGE (n)-[:PART_OF]->(c)
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, rels=records)
            summary = result.consume()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return RelationshipWriteResult(
            relationship_type="PART_OF",
            table_name=table_name,
            records_read=len(records),
            relationships_created=summary.counters.relationships_created,
            duration_seconds=duration
        )
    
    @log_stage("Neo4j: Write IN_COUNTY relationships")
    def write_in_county_relationships(self) -> RelationshipWriteResult:
        """Write IN_COUNTY relationships (Neighborhood -> County)."""
        table_name = "gold_graph_rel_in_county"
        start_time = datetime.now()
        
        if not self.connection_manager.table_exists(table_name):
            self.logger.warning(f"Table {table_name} does not exist")
            return RelationshipWriteResult(
                relationship_type="IN_COUNTY",
                table_name=table_name,
                records_read=0,
                relationships_created=0,
                duration_seconds=0.0
            )
        
        records = self._get_records_from_table(table_name)
        
        cypher = """
        UNWIND $rels AS rel
        MATCH (n:Neighborhood {neighborhood_id: rel.from_id})
        MATCH (c:County {county_id: rel.to_id})
        MERGE (n)-[:IN_COUNTY]->(c)
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, rels=records)
            summary = result.consume()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return RelationshipWriteResult(
            relationship_type="IN_COUNTY",
            table_name=table_name,
            records_read=len(records),
            relationships_created=summary.counters.relationships_created,
            duration_seconds=duration
        )
    
    @log_stage("Neo4j: Write DESCRIBES relationships")
    def write_describes_relationships(self) -> RelationshipWriteResult:
        """Write DESCRIBES relationships (Wikipedia -> Neighborhood)."""
        table_name = "gold_graph_rel_describes"
        start_time = datetime.now()
        
        if not self.connection_manager.table_exists(table_name):
            self.logger.warning(f"Table {table_name} does not exist")
            return RelationshipWriteResult(
                relationship_type="DESCRIBES",
                table_name=table_name,
                records_read=0,
                relationships_created=0,
                duration_seconds=0.0
            )
        
        records = self._get_records_from_table(table_name)
        
        cypher = """
        UNWIND $rels AS rel
        MATCH (w:Wikipedia {wikipedia_id: rel.from_id})
        MATCH (n:Neighborhood {neighborhood_id: rel.to_id})
        MERGE (w)-[:DESCRIBES]->(n)
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, rels=records)
            summary = result.consume()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return RelationshipWriteResult(
            relationship_type="DESCRIBES",
            table_name=table_name,
            records_read=len(records),
            relationships_created=summary.counters.relationships_created,
            duration_seconds=duration
        )
    
    @log_stage("Neo4j: Write OF_TYPE relationships")
    def write_of_type_relationships(self) -> RelationshipWriteResult:
        """Write OF_TYPE relationships (Property -> PropertyType)."""
        table_name = "gold_graph_rel_of_type"
        start_time = datetime.now()
        
        if not self.connection_manager.table_exists(table_name):
            self.logger.warning(f"Table {table_name} does not exist")
            return RelationshipWriteResult(
                relationship_type="OF_TYPE",
                table_name=table_name,
                records_read=0,
                relationships_created=0,
                duration_seconds=0.0
            )
        
        records = self._get_records_from_table(table_name)
        
        cypher = """
        UNWIND $rels AS rel
        MATCH (p:Property {listing_id: REPLACE(rel.from_id, 'property:', '')})
        MATCH (pt:PropertyType {property_type_id: REPLACE(rel.to_id, 'type:', '')})
        MERGE (p)-[:OF_TYPE]->(pt)
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, rels=records)
            summary = result.consume()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return RelationshipWriteResult(
            relationship_type="OF_TYPE",
            table_name=table_name,
            records_read=len(records),
            relationships_created=summary.counters.relationships_created,
            duration_seconds=duration
        )
    
    @log_stage("Neo4j: Write IN_PRICE_RANGE relationships")
    def write_in_price_range_relationships(self) -> RelationshipWriteResult:
        """Write IN_PRICE_RANGE relationships (Property -> PriceRange)."""
        table_name = "gold_graph_rel_in_price_range"
        start_time = datetime.now()
        
        if not self.connection_manager.table_exists(table_name):
            self.logger.warning(f"Table {table_name} does not exist")
            return RelationshipWriteResult(
                relationship_type="IN_PRICE_RANGE",
                table_name=table_name,
                records_read=0,
                relationships_created=0,
                duration_seconds=0.0
            )
        
        records = self._get_records_from_table(table_name)
        
        cypher = """
        UNWIND $rels AS rel
        MATCH (p:Property {listing_id: REPLACE(rel.from_id, 'property:', '')})
        MATCH (pr:PriceRange {price_range_id: rel.to_id})
        MERGE (p)-[:IN_PRICE_RANGE]->(pr)
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, rels=records)
            summary = result.consume()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return RelationshipWriteResult(
            relationship_type="IN_PRICE_RANGE",
            table_name=table_name,
            records_read=len(records),
            relationships_created=summary.counters.relationships_created,
            duration_seconds=duration
        )
    
    # ============= ORCHESTRATION METHODS =============
    
    @log_stage("Neo4j: Write all nodes")
    def write_all_nodes(self) -> List[NodeWriteResult]:
        """Write all node types to Neo4j.
        
        Returns:
            List of node write results
        """
        results = []
        
        # Write nodes in order (core entities first)
        node_writers = [
            self.write_property_nodes,
            self.write_neighborhood_nodes,
            self.write_wikipedia_nodes,
            self.write_feature_nodes,
            self.write_city_nodes,
            self.write_state_nodes,
            self.write_zip_code_nodes,
            self.write_county_nodes,
            self.write_property_type_nodes,
            self.write_price_range_nodes
        ]
        
        for writer in node_writers:
            result = writer()
            if result.records_read > 0:
                results.append(result)
                self.logger.info(
                    f"Wrote {result.nodes_created} {result.entity_type} nodes "
                    f"from {result.records_read} records"
                )
        
        return results
    
    @log_stage("Neo4j: Write all relationships")
    def write_all_relationships(self) -> List[RelationshipWriteResult]:
        """Write all relationship types to Neo4j.
        
        Returns:
            List of relationship write results
        """
        results = []
        
        # Write relationships
        relationship_writers = [
            self.write_located_in_relationships,
            self.write_has_feature_relationships,
            self.write_part_of_relationships,
            self.write_in_county_relationships,
            self.write_describes_relationships,
            self.write_of_type_relationships,
            self.write_in_price_range_relationships
        ]
        
        for writer in relationship_writers:
            result = writer()
            if result.records_read > 0:
                results.append(result)
                self.logger.info(
                    f"Wrote {result.relationships_created} {result.relationship_type} relationships "
                    f"from {result.records_read} records"
                )
        
        return results
    
    @log_stage("Neo4j: Write all data")
    def write_all(self) -> Neo4jWriteMetadata:
        """Write all nodes and relationships to Neo4j.
        
        Returns:
            Complete write metadata
        """
        metadata = Neo4jWriteMetadata(start_time=datetime.now())
        
        try:
            # Create constraints first
            self.logger.info("Creating constraints...")
            metadata.constraints_created = self.create_constraints()
            
            # Write all nodes
            self.logger.info("Writing nodes...")
            metadata.node_results = self.write_all_nodes()
            metadata.total_nodes = sum(r.nodes_created for r in metadata.node_results)
            
            # Write all relationships
            self.logger.info("Writing relationships...")
            metadata.relationship_results = self.write_all_relationships()
            metadata.total_relationships = sum(r.relationships_created for r in metadata.relationship_results)
            
            # Set completion time
            metadata.end_time = datetime.now()
            metadata.total_duration_seconds = (metadata.end_time - metadata.start_time).total_seconds()
            
            self.logger.info(
                f"Neo4j write complete: {metadata.total_nodes} nodes, "
                f"{metadata.total_relationships} relationships in {metadata.total_duration_seconds:.2f}s"
            )
            
        except Exception as e:
            self.logger.error(f"Error writing to Neo4j: {e}")
            raise
        
        return metadata