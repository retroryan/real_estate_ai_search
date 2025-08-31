"""Neo4j writer for graph data.

This writer reads from Gold layer graph tables and writes to Neo4j
using the official Neo4j Python driver. All data transformation is
already done in the Gold layer.
"""

from typing import Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from neo4j import GraphDatabase, Driver, Session
import pandas as pd

from squack_pipeline_v2.core.connection import DuckDBConnectionManager, TableIdentifier
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
    
    This writer is entity-specific with no dynamic type inspection.
    All data transformation is done in the Gold layer.
    """
    
    def __init__(
        self,
        connection_manager: DuckDBConnectionManager,
        config: Neo4jConfig
    ):
        """Initialize Neo4j writer.
        
        Args:
            connection_manager: DuckDB connection manager
            config: Neo4j configuration
        """
        self.connection_manager = connection_manager
        self.config = config
        self.driver = GraphDatabase.driver(
            config.uri,
            auth=(config.username, config.password)
        )
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
    
    def close(self):
        """Close Neo4j connection."""
        self.driver.close()
    
    @log_stage("Neo4j: Create constraints")
    def create_constraints(self) -> List[str]:
        """Create Neo4j constraints and indexes.
        
        Returns:
            List of constraints created
        """
        constraints_created = []
        
        constraints = [
            ("property_id", "CREATE CONSTRAINT property_id IF NOT EXISTS FOR (p:Property) REQUIRE p.listing_id IS UNIQUE"),
            ("neighborhood_id", "CREATE CONSTRAINT neighborhood_id IF NOT EXISTS FOR (n:Neighborhood) REQUIRE n.neighborhood_id IS UNIQUE"),
            ("wikipedia_id", "CREATE CONSTRAINT wikipedia_id IF NOT EXISTS FOR (w:WikipediaArticle) REQUIRE w.page_id IS UNIQUE"),
            ("city_id", "CREATE CONSTRAINT city_id IF NOT EXISTS FOR (c:City) REQUIRE c.city_id IS UNIQUE"),
            ("state_id", "CREATE CONSTRAINT state_id IF NOT EXISTS FOR (s:State) REQUIRE s.state_id IS UNIQUE"),
            ("feature_id", "CREATE CONSTRAINT feature_id IF NOT EXISTS FOR (f:Feature) REQUIRE f.feature_id IS UNIQUE"),
            ("property_type_id", "CREATE CONSTRAINT property_type_id IF NOT EXISTS FOR (pt:PropertyType) REQUIRE pt.type_id IS UNIQUE"),
            ("price_range_id", "CREATE CONSTRAINT price_range_id IF NOT EXISTS FOR (pr:PriceRange) REQUIRE pr.range_id IS UNIQUE"),
            ("zip_code_id", "CREATE CONSTRAINT zip_code_id IF NOT EXISTS FOR (z:ZipCode) REQUIRE z.zip_code IS UNIQUE")
        ]
        
        indexes = [
            ("property_price", "CREATE INDEX property_price IF NOT EXISTS FOR (p:Property) ON (p.price)"),
            ("property_type", "CREATE INDEX property_type IF NOT EXISTS FOR (p:Property) ON (p.property_type)"),
            ("property_bedrooms", "CREATE INDEX property_bedrooms IF NOT EXISTS FOR (p:Property) ON (p.bedrooms)"),
            ("neighborhood_city", "CREATE INDEX neighborhood_city IF NOT EXISTS FOR (n:Neighborhood) ON (n.city)"),
            ("neighborhood_state", "CREATE INDEX neighborhood_state IF NOT EXISTS FOR (n:Neighborhood) ON (n.state)")
        ]
        
        # Vector indexes for embeddings
        vector_indexes = [
            ("property_embedding", "CREATE VECTOR INDEX property_embedding IF NOT EXISTS FOR (p:Property) ON p.embedding OPTIONS {indexConfig: {`vector.dimensions`: 1024, `vector.similarity_function`: 'cosine'}}"),
            ("neighborhood_embedding", "CREATE VECTOR INDEX neighborhood_embedding IF NOT EXISTS FOR (n:Neighborhood) ON n.embedding OPTIONS {indexConfig: {`vector.dimensions`: 1024, `vector.similarity_function`: 'cosine'}}"),
            ("wikipedia_embedding", "CREATE VECTOR INDEX wikipedia_embedding IF NOT EXISTS FOR (w:WikipediaArticle) ON w.embedding OPTIONS {indexConfig: {`vector.dimensions`: 1024, `vector.similarity_function`: 'cosine'}}")
        ]
        
        with self.driver.session() as session:
            # Create constraints
            for name, constraint in constraints:
                try:
                    session.run(constraint)
                    constraints_created.append(name)
                    self.logger.debug(f"Created constraint: {name}")
                except Exception as e:
                    self.logger.debug(f"Constraint {name} may already exist: {e}")
            
            # Create indexes
            for name, index in indexes:
                try:
                    session.run(index)
                    self.logger.debug(f"Created index: {name}")
                except Exception as e:
                    self.logger.debug(f"Index {name} may already exist: {e}")
            
            # Create vector indexes
            for name, vector_index in vector_indexes:
                try:
                    session.run(vector_index)
                    self.logger.debug(f"Created vector index: {name}")
                except Exception as e:
                    self.logger.debug(f"Vector index {name} may already exist or Neo4j version doesn't support it: {e}")
        
        return constraints_created
    
    @log_stage("Neo4j: Write Property nodes")
    def write_property_nodes(self) -> NodeWriteResult:
        """Write property nodes to Neo4j.
        
        Returns:
            Write result metadata
        """
        start_time = datetime.now()
        table_name = "gold_graph_properties"
        
        # Check if table exists
        if not self.connection_manager.table_exists(TableIdentifier(name=table_name)):
            self.logger.warning(f"Table {table_name} does not exist")
            return NodeWriteResult(
                entity_type="Property",
                table_name=table_name,
                records_read=0,
                nodes_created=0,
                properties_set=0,
                duration_seconds=0.0
            )
        
        # Read data from DuckDB
        query = f"SELECT * FROM {table_name}"
        df = self.connection_manager.execute(query).df()
        records = df.to_dict('records')
        
        # Bulk insert using UNWIND
        cypher = """
        UNWIND $properties AS prop
        MERGE (p:Property {listing_id: prop.listing_id})
        SET p = prop
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, properties=records)
            summary = result.consume()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        write_result = NodeWriteResult(
            entity_type="Property",
            table_name=table_name,
            records_read=len(records),
            nodes_created=summary.counters.nodes_created,
            properties_set=summary.counters.properties_set,
            duration_seconds=duration
        )
        
        self.logger.info(f"Wrote {len(records)} Property nodes in {duration:.2f}s")
        return write_result
    
    @log_stage("Neo4j: Write Neighborhood nodes")
    def write_neighborhood_nodes(self) -> NodeWriteResult:
        """Write neighborhood nodes to Neo4j.
        
        Returns:
            Write result metadata
        """
        start_time = datetime.now()
        table_name = "gold_graph_neighborhoods"
        
        if not self.connection_manager.table_exists(TableIdentifier(name=table_name)):
            self.logger.warning(f"Table {table_name} does not exist")
            return NodeWriteResult(
                entity_type="Neighborhood",
                table_name=table_name,
                records_read=0,
                nodes_created=0,
                properties_set=0,
                duration_seconds=0.0
            )
        
        query = f"SELECT * FROM {table_name}"
        df = self.connection_manager.execute(query).df()
        records = df.to_dict('records')
        
        cypher = """
        UNWIND $neighborhoods AS n
        MERGE (node:Neighborhood {neighborhood_id: n.neighborhood_id})
        SET node = n
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, neighborhoods=records)
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
        """Write Wikipedia article nodes to Neo4j.
        
        Returns:
            Write result metadata
        """
        start_time = datetime.now()
        table_name = "gold_graph_wikipedia"
        
        if not self.connection_manager.table_exists(TableIdentifier(name=table_name)):
            self.logger.warning(f"Table {table_name} does not exist")
            return NodeWriteResult(
                entity_type="WikipediaArticle",
                table_name=table_name,
                records_read=0,
                nodes_created=0,
                properties_set=0,
                duration_seconds=0.0
            )
        
        query = f"SELECT * FROM {table_name}"
        df = self.connection_manager.execute(query).df()
        records = df.to_dict('records')
        
        cypher = """
        UNWIND $articles AS a
        MERGE (node:WikipediaArticle {page_id: a.page_id})
        SET node = a
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, articles=records)
            summary = result.consume()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return NodeWriteResult(
            entity_type="WikipediaArticle",
            table_name=table_name,
            records_read=len(records),
            nodes_created=summary.counters.nodes_created,
            properties_set=summary.counters.properties_set,
            duration_seconds=duration
        )
    
    @log_stage("Neo4j: Write Feature nodes")
    def write_feature_nodes(self) -> NodeWriteResult:
        """Write feature nodes to Neo4j."""
        start_time = datetime.now()
        table_name = "gold_graph_features"
        
        if not self.connection_manager.table_exists(TableIdentifier(name=table_name)):
            return NodeWriteResult(
                entity_type="Feature",
                table_name=table_name,
                records_read=0,
                nodes_created=0,
                properties_set=0,
                duration_seconds=0.0
            )
        
        query = f"SELECT * FROM {table_name}"
        df = self.connection_manager.execute(query).df()
        records = df.to_dict('records')
        
        cypher = """
        UNWIND $features AS f
        MERGE (node:Feature {feature_id: f.feature_id})
        SET node = f
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, features=records)
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
    
    @log_stage("Neo4j: Write geographic nodes")
    def write_geographic_nodes(self) -> List[NodeWriteResult]:
        """Write geographic hierarchy nodes (City, State, ZipCode).
        
        Returns:
            List of write results
        """
        results = []
        
        # Cities
        table_name = "gold_graph_cities"
        if self.connection_manager.table_exists(TableIdentifier(name=table_name)):
            start_time = datetime.now()
            query = f"SELECT * FROM {table_name}"
            df = self.connection_manager.execute(query).df()
            records = df.to_dict('records')
            
            cypher = """
            UNWIND $cities AS c
            MERGE (node:City {city_id: c.city_id})
            SET node = c
            """
            
            with self.driver.session() as session:
                result = session.run(cypher, cities=records)
                summary = result.consume()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            results.append(NodeWriteResult(
                entity_type="City",
                table_name=table_name,
                records_read=len(records),
                nodes_created=summary.counters.nodes_created,
                properties_set=summary.counters.properties_set,
                duration_seconds=duration
            ))
        
        # States
        table_name = "gold_graph_states"
        if self.connection_manager.table_exists(TableIdentifier(name=table_name)):
            start_time = datetime.now()
            query = f"SELECT * FROM {table_name}"
            df = self.connection_manager.execute(query).df()
            records = df.to_dict('records')
            
            cypher = """
            UNWIND $states AS s
            MERGE (node:State {state_id: s.state_id})
            SET node = s
            """
            
            with self.driver.session() as session:
                result = session.run(cypher, states=records)
                summary = result.consume()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            results.append(NodeWriteResult(
                entity_type="State",
                table_name=table_name,
                records_read=len(records),
                nodes_created=summary.counters.nodes_created,
                properties_set=summary.counters.properties_set,
                duration_seconds=duration
            ))
        
        # Zip Codes
        table_name = "gold_graph_zip_codes"
        if self.connection_manager.table_exists(TableIdentifier(name=table_name)):
            start_time = datetime.now()
            query = f"SELECT * FROM {table_name}"
            df = self.connection_manager.execute(query).df()
            records = df.to_dict('records')
            
            cypher = """
            UNWIND $zips AS z
            MERGE (node:ZipCode {zip_code: z.zip_code})
            SET node = z
            """
            
            with self.driver.session() as session:
                result = session.run(cypher, zips=records)
                summary = result.consume()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            results.append(NodeWriteResult(
                entity_type="ZipCode",
                table_name=table_name,
                records_read=len(records),
                nodes_created=summary.counters.nodes_created,
                properties_set=summary.counters.properties_set,
                duration_seconds=duration
            ))
        
        return results
    
    @log_stage("Neo4j: Write classification nodes")
    def write_classification_nodes(self) -> List[NodeWriteResult]:
        """Write classification nodes (PropertyType, PriceRange).
        
        Returns:
            List of write results
        """
        results = []
        
        # Property Types
        table_name = "gold_graph_property_types"
        if self.connection_manager.table_exists(TableIdentifier(name=table_name)):
            start_time = datetime.now()
            query = f"SELECT * FROM {table_name}"
            df = self.connection_manager.execute(query).df()
            records = df.to_dict('records')
            
            cypher = """
            UNWIND $types AS t
            MERGE (node:PropertyType {type_id: t.type_id})
            SET node = t
            """
            
            with self.driver.session() as session:
                result = session.run(cypher, types=records)
                summary = result.consume()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            results.append(NodeWriteResult(
                entity_type="PropertyType",
                table_name=table_name,
                records_read=len(records),
                nodes_created=summary.counters.nodes_created,
                properties_set=summary.counters.properties_set,
                duration_seconds=duration
            ))
        
        # Price Ranges
        table_name = "gold_graph_price_ranges"
        if self.connection_manager.table_exists(TableIdentifier(name=table_name)):
            start_time = datetime.now()
            query = f"SELECT * FROM {table_name}"
            df = self.connection_manager.execute(query).df()
            records = df.to_dict('records')
            
            cypher = """
            UNWIND $ranges AS r
            MERGE (node:PriceRange {range_id: r.range_id})
            SET node = r
            """
            
            with self.driver.session() as session:
                result = session.run(cypher, ranges=records)
                summary = result.consume()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            results.append(NodeWriteResult(
                entity_type="PriceRange",
                table_name=table_name,
                records_read=len(records),
                nodes_created=summary.counters.nodes_created,
                properties_set=summary.counters.properties_set,
                duration_seconds=duration
            ))
        
        return results
    
    def write_located_in_relationships(self) -> RelationshipWriteResult:
        """Write LOCATED_IN relationships."""
        start_time = datetime.now()
        table_name = "gold_graph_rel_located_in"
        
        if not self.connection_manager.table_exists(TableIdentifier(name=table_name)):
            return RelationshipWriteResult(
                relationship_type="LOCATED_IN",
                table_name=table_name,
                records_read=0,
                relationships_created=0,
                duration_seconds=0.0
            )
        
        query = f"SELECT * FROM {table_name}"
        df = self.connection_manager.execute(query).df()
        records = df.to_dict('records')
        
        cypher = """
        UNWIND $rels AS rel
        MATCH (p:Property {listing_id: substring(rel.from_id, 10)})
        MATCH (n:Neighborhood {neighborhood_id: substring(rel.to_id, 14)})
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
    
    def write_has_feature_relationships(self) -> RelationshipWriteResult:
        """Write HAS_FEATURE relationships."""
        start_time = datetime.now()
        table_name = "gold_graph_rel_has_feature"
        
        if not self.connection_manager.table_exists(TableIdentifier(name=table_name)):
            return RelationshipWriteResult(
                relationship_type="HAS_FEATURE",
                table_name=table_name,
                records_read=0,
                relationships_created=0,
                duration_seconds=0.0
            )
        
        query = f"SELECT * FROM {table_name}"
        df = self.connection_manager.execute(query).df()
        records = df.to_dict('records')
        
        cypher = """
        UNWIND $rels AS rel
        MATCH (p:Property {listing_id: substring(rel.from_id, 10)})
        MATCH (f:Feature {feature_id: rel.to_id})
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
    
    @log_stage("Neo4j: Write all relationships")
    def write_all_relationships(self) -> List[RelationshipWriteResult]:
        """Write all relationships to Neo4j.
        
        Returns:
            List of relationship write results
        """
        results = []
        
        # Define relationship tables and their Cypher queries
        relationships = [
            ("gold_graph_rel_located_in", "LOCATED_IN", self.write_located_in_relationships),
            ("gold_graph_rel_has_feature", "HAS_FEATURE", self.write_has_feature_relationships),
            # Add more specific relationship writers as needed
        ]
        
        # Write each relationship type
        for table_name, rel_type, writer_func in relationships:
            if self.connection_manager.table_exists(TableIdentifier(name=table_name)):
                result = writer_func()
                results.append(result)
                self.logger.info(f"Wrote {result.records_read} {rel_type} relationships")
        
        # Handle generic relationships
        generic_relationships = [
            ("gold_graph_rel_in_city", "IN_CITY"),
            ("gold_graph_rel_in_state", "IN_STATE"),
            ("gold_graph_rel_in_zip_code", "IN_ZIP_CODE"),
            ("gold_graph_rel_type_of", "TYPE_OF"),
            ("gold_graph_rel_in_price_range", "IN_PRICE_RANGE"),
            ("gold_graph_rel_similar_properties", "SIMILAR_TO")
        ]
        
        for table_name, rel_type in generic_relationships:
            if self.connection_manager.table_exists(TableIdentifier(name=table_name)):
                result = self._write_generic_relationship(table_name, rel_type)
                results.append(result)
        
        return results
    
    def _write_generic_relationship(self, table_name: str, relationship_type: str) -> RelationshipWriteResult:
        """Write a generic relationship type.
        
        Args:
            table_name: Source table name
            relationship_type: Type of relationship
            
        Returns:
            Write result
        """
        start_time = datetime.now()
        
        query = f"SELECT * FROM {table_name}"
        df = self.connection_manager.execute(query).df()
        records = df.to_dict('records')
        
        # Generic Cypher that matches nodes by their graph_node_id
        cypher = f"""
        UNWIND $rels AS rel
        MATCH (from {{graph_node_id: rel.from_id}})
        MATCH (to {{graph_node_id: rel.to_id}})
        MERGE (from)-[:{relationship_type}]->(to)
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, rels=records)
            summary = result.consume()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return RelationshipWriteResult(
            relationship_type=relationship_type,
            table_name=table_name,
            records_read=len(records),
            relationships_created=summary.counters.relationships_created,
            duration_seconds=duration
        )
    
    @log_stage("Neo4j: Write all data")
    def write_all(self) -> Neo4jWriteMetadata:
        """Write all nodes and relationships to Neo4j.
        
        Returns:
            Complete write metadata
        """
        start_time = datetime.now()
        metadata = Neo4jWriteMetadata(start_time=start_time)
        
        # Create constraints first
        constraints = self.create_constraints()
        metadata.constraints_created = constraints
        
        # Write nodes in order (no dependencies between node types)
        self.logger.info("Writing nodes to Neo4j...")
        
        # Main entity nodes
        metadata.node_results.append(self.write_property_nodes())
        metadata.node_results.append(self.write_neighborhood_nodes())
        metadata.node_results.append(self.write_wikipedia_nodes())
        
        # Classification nodes
        metadata.node_results.append(self.write_feature_nodes())
        metadata.node_results.extend(self.write_classification_nodes())
        
        # Geographic nodes
        metadata.node_results.extend(self.write_geographic_nodes())
        
        # Calculate total nodes
        metadata.total_nodes = sum(r.nodes_created for r in metadata.node_results)
        
        # Write relationships
        self.logger.info("Writing relationships to Neo4j...")
        metadata.relationship_results = self.write_all_relationships()
        
        # Calculate total relationships
        metadata.total_relationships = sum(r.relationships_created for r in metadata.relationship_results)
        
        # Calculate final metrics
        metadata.end_time = datetime.now()
        metadata.total_duration_seconds = (metadata.end_time - metadata.start_time).total_seconds()
        
        self.logger.info(
            f"Neo4j write complete: {metadata.total_nodes} nodes, "
            f"{metadata.total_relationships} relationships in {metadata.total_duration_seconds:.2f}s"
        )
        
        return metadata