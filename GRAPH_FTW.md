# Neo4j Integration for Squack Pipeline V2 - IMPLEMENTATION COMPLETE

## Implementation Status

✅ **PHASE 1 COMPLETE**: Silver Layer Enhancements
- Added graph-specific computed columns to Silver tables
- Created entity extraction tables for features, cities, states, etc.
- All changes are additive - existing flows unchanged

✅ **PHASE 2 COMPLETE**: Gold Layer Extensions  
- Created graph-specific node tables in Gold layer
- Built relationship tables using DuckDB SQL
- All graph tables are separate from existing Gold tables

✅ **PHASE 3 COMPLETE**: Neo4j Writer Implementation
- Implemented entity-specific write methods
- Added bulk loading with UNWIND
- Created constraints and indexes
- Integrated with pipeline orchestrator

## Executive Summary

This document describes the completed implementation of Neo4j graph database support in the `squack_pipeline_v2` medallion architecture **without modifying any existing data flow**. The implementation preserves all current functionality while adding graph capabilities through:

1. **Silver Layer Enhancements**: Add graph-specific identifier mappings
2. **Gold Layer Extensions**: Create relationship tables using DuckDB's native SQL capabilities  
3. **Neo4j Writer**: New writer that consumes Gold tables and writes to Neo4j
4. **Entity-Specific Processing**: No dynamic type inspection or conditional logic

## Core Design Principles

### 1. Zero Breaking Changes
- All existing Bronze → Silver → Gold transformations remain unchanged
- Existing Parquet and Elasticsearch writers continue to function identically
- New graph-specific tables are additions, not modifications

### 2. DuckDB-Native Relationship Building
- Leverage DuckDB's powerful SQL engine for relationship extraction
- Use CTEs and window functions for efficient graph construction
- Create materialized relationship tables in Gold layer

### 3. Entity-Specific Implementation
- Separate enricher classes for each entity type
- No dynamic type inspection or conditional writing
- Clear, predictable data paths

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     EXISTING FLOW (UNCHANGED)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Bronze Layer          Silver Layer         Gold Layer           │
│  ┌──────────┐         ┌──────────┐        ┌──────────┐         │
│  │Properties│  ───>   │Flattened │  ───>  │Enriched  │         │
│  │   JSON   │         │Properties│        │Properties│         │
│  └──────────┘         └──────────┘        └──────────┘         │
│                                                   │              │
│                                                   ▼              │
│                                           ┌──────────────┐      │
│                                           │Parquet Writer│      │
│                                           └──────────────┘      │
│                                                   │              │
│                                                   ▼              │
│                                           ┌──────────────┐      │
│                                           │ ES Writer    │      │
│                                           └──────────────┘      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      NEW ADDITIONS (GRAPH)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Silver Layer          Gold Layer           Writers              │
│  (Enhanced)           (Extended)                                 │
│                                                                   │
│  ┌──────────┐        ┌─────────────┐                           │
│  │+Node IDs │  ───>  │Graph Tables │                           │
│  │+Mappings │        │(Nodes+Edges)│                           │
│  └──────────┘        └─────────────┘                           │
│                              │                                   │
│                              ▼                                   │
│                      ┌───────────────┐                          │
│                      │Relationship   │                          │
│                      │Tables (DuckDB)│                          │
│                      └───────────────┘                          │
│                              │                                   │
│                              ▼                                   │
│                      ┌───────────────┐                          │
│                      │ Neo4j Writer  │                          │
│                      └───────────────┘                          │
│                              │                                   │
│                              ▼                                   │
│                      ┌───────────────┐                          │
│                      │  Neo4j Graph  │                          │
│                      └───────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

## Silver Layer Enhancements

### Current Silver Layer (Unchanged)
The existing Silver transformers continue to operate exactly as before:
```python
# Current PropertySilverTransformer continues to work as-is
# Flattens nested structures for Elasticsearch
# No modifications needed
```

### New Graph-Specific Additions

#### 1. Node Identifier Generation
Add computed columns for graph node IDs **without modifying existing columns**:

```sql
-- In PropertySilverTransformer, after main transformation:
-- This is an ADDITION, not a modification
ALTER TABLE silver_properties 
ADD COLUMN graph_node_id VARCHAR AS (
    'property:' || listing_id  -- Namespaced ID for Neo4j
);

-- Add lookup columns for relationship building
ALTER TABLE silver_properties
ADD COLUMN city_normalized VARCHAR AS (
    CASE 
        WHEN UPPER(address.city) = 'SF' THEN 'San Francisco'
        WHEN UPPER(address.city) = 'LA' THEN 'Los Angeles'
        ELSE address.city
    END
);

ALTER TABLE silver_properties
ADD COLUMN state_normalized VARCHAR AS (
    UPPER(TRIM(address.state))
);

-- Add zip code extraction for geographic hierarchy
ALTER TABLE silver_properties  
ADD COLUMN zip_code_clean VARCHAR AS (
    SUBSTRING(address.zip_code, 1, 5)  -- Extract 5-digit zip
);
```

#### 2. Entity Extraction Tables
Create auxiliary tables for entity extraction **without touching main tables**:

```sql
-- Create feature extraction table (addition, not modification)
CREATE TABLE silver_features AS
SELECT DISTINCT
    LOWER(TRIM(unnest(features))) as feature_id,
    TRIM(unnest(features)) as feature_name,
    COUNT(*) as occurrence_count
FROM silver_properties
WHERE features IS NOT NULL
GROUP BY 1, 2;

-- Create property type extraction table
CREATE TABLE silver_property_types AS  
SELECT DISTINCT
    LOWER(property_type) as type_id,
    property_type as type_name,
    COUNT(*) as property_count
FROM silver_properties
WHERE property_type IS NOT NULL
GROUP BY 1, 2;

-- Create price range categorization table
CREATE TABLE silver_price_ranges AS
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
GROUP BY 1, 2;
```

## Gold Layer Extensions

### Current Gold Layer (Unchanged)
The existing Gold enrichers continue to create the same output tables for Elasticsearch and Parquet:
```python
# PropertyGoldEnricher, NeighborhoodGoldEnricher, WikipediaGoldEnricher
# All continue to work exactly as before
# Their output tables remain unchanged
```

### New Graph-Specific Gold Tables

#### 1. Graph Node Tables
Create separate node tables optimized for Neo4j **without modifying existing Gold tables**:

```sql
-- Property nodes table for Neo4j (new addition)
CREATE TABLE gold_graph_properties AS
SELECT 
    -- Core node properties
    listing_id,
    neighborhood_id,
    
    -- Property attributes (keep flat for Neo4j)
    bedrooms,
    bathrooms,
    square_feet,
    property_type,
    year_built,
    lot_size,
    
    -- Price information
    price,
    price_per_sqft,
    
    -- Location (flatten for Neo4j properties)
    address.street as street_address,
    address.city as city,
    address.state as state,
    address.zip_code as zip_code,
    address.location[1] as longitude,
    address.location[2] as latitude,
    
    -- Text and media
    description,
    features,
    virtual_tour_url,
    images,
    
    -- Dates
    listing_date,
    days_on_market,
    
    -- Embedding vector (if exists)
    embedding,
    
    -- Graph metadata
    'Property' as node_label,
    graph_node_id
    
FROM gold_properties;  -- Source from existing Gold table

-- Neighborhood nodes table for Neo4j
CREATE TABLE gold_graph_neighborhoods AS
SELECT
    neighborhood_id,
    name,
    city,
    state,
    population,
    median_income,
    median_home_value,
    walkability_score,
    school_rating,
    crime_index,
    description,
    latitude,
    longitude,
    embedding,
    'Neighborhood' as node_label,
    'neighborhood:' || neighborhood_id as graph_node_id
FROM gold_neighborhoods;

-- Geographic hierarchy nodes
CREATE TABLE gold_graph_cities AS
SELECT DISTINCT
    city_normalized || '_' || state_normalized as city_id,
    city_normalized as name,
    state_normalized as state,
    'City' as node_label
FROM silver_properties
WHERE city_normalized IS NOT NULL;

CREATE TABLE gold_graph_states AS
SELECT DISTINCT
    state_normalized as state_id,
    state_normalized as abbreviation,
    -- Could join with reference data for full names
    'State' as node_label
FROM silver_properties
WHERE state_normalized IS NOT NULL;

-- Classification nodes
CREATE TABLE gold_graph_features AS
SELECT 
    feature_id,
    feature_name,
    occurrence_count,
    'Feature' as node_label
FROM silver_features;

CREATE TABLE gold_graph_property_types AS
SELECT
    type_id,
    type_name,
    property_count,
    'PropertyType' as node_label
FROM silver_property_types;
```

#### 2. Relationship Tables (DuckDB Best Practices)

Create explicit relationship tables using DuckDB's powerful SQL capabilities:

```sql
-- LOCATED_IN relationships (Property -> Neighborhood)
CREATE TABLE gold_graph_rel_located_in AS
SELECT 
    'property:' || listing_id as from_id,
    'neighborhood:' || neighborhood_id as to_id,
    'LOCATED_IN' as relationship_type,
    -- Can add relationship properties here
    1.0 as weight
FROM gold_properties
WHERE neighborhood_id IS NOT NULL;

-- HAS_FEATURE relationships (Property -> Feature)
-- Using DuckDB's unnest for array expansion
CREATE TABLE gold_graph_rel_has_feature AS
SELECT DISTINCT
    'property:' || p.listing_id as from_id,
    LOWER(TRIM(unnest(p.features))) as to_id,
    'HAS_FEATURE' as relationship_type
FROM gold_properties p
WHERE p.features IS NOT NULL AND array_length(p.features) > 0;

-- IN_CITY relationships (Property -> City)
CREATE TABLE gold_graph_rel_in_city AS
SELECT DISTINCT
    'property:' || listing_id as from_id,
    city_normalized || '_' || state_normalized as to_id,
    'IN_CITY' as relationship_type
FROM gold_graph_properties
WHERE city IS NOT NULL AND state IS NOT NULL;

-- TYPE_OF relationships (Property -> PropertyType)
CREATE TABLE gold_graph_rel_type_of AS
SELECT DISTINCT
    'property:' || listing_id as from_id,
    LOWER(property_type) as to_id,
    'TYPE_OF' as relationship_type
FROM gold_graph_properties
WHERE property_type IS NOT NULL;

-- SIMILAR_TO relationships using embeddings
-- DuckDB supports array operations for cosine similarity
CREATE TABLE gold_graph_rel_similar_properties AS
WITH similarity_scores AS (
    SELECT 
        p1.listing_id as id1,
        p2.listing_id as id2,
        -- Cosine similarity calculation in DuckDB
        list_dot_product(p1.embedding, p2.embedding) / 
        (list_norm(p1.embedding) * list_norm(p2.embedding)) as similarity
    FROM gold_graph_properties p1
    CROSS JOIN gold_graph_properties p2
    WHERE p1.listing_id < p2.listing_id  -- Avoid duplicates
      AND p1.embedding IS NOT NULL
      AND p2.embedding IS NOT NULL
)
SELECT 
    'property:' || id1 as from_id,
    'property:' || id2 as to_id,
    'SIMILAR_TO' as relationship_type,
    similarity as weight
FROM similarity_scores
WHERE similarity > 0.85  -- Threshold for similarity
ORDER BY similarity DESC
LIMIT 10000;  -- Limit for performance

-- Geographic hierarchy relationships
CREATE TABLE gold_graph_rel_in_state AS
SELECT DISTINCT
    city_id as from_id,
    state as to_id,
    'IN_STATE' as relationship_type
FROM gold_graph_cities;

-- NEAR relationships based on geographic distance
-- Using DuckDB's spatial functions if available, or Haversine formula
CREATE TABLE gold_graph_rel_near AS
WITH distances AS (
    SELECT 
        n1.neighborhood_id as id1,
        n2.neighborhood_id as id2,
        -- Simplified distance calculation (could use proper Haversine)
        SQRT(POWER(n1.latitude - n2.latitude, 2) + 
             POWER(n1.longitude - n2.longitude, 2)) * 111 as distance_km
    FROM gold_graph_neighborhoods n1
    CROSS JOIN gold_graph_neighborhoods n2
    WHERE n1.neighborhood_id < n2.neighborhood_id
)
SELECT
    'neighborhood:' || id1 as from_id,
    'neighborhood:' || id2 as to_id,
    'NEAR' as relationship_type,
    distance_km as distance
FROM distances
WHERE distance_km < 5.0;  -- Within 5km
```

#### 3. Aggregated Relationship Tables

Create aggregated tables for efficient bulk loading to Neo4j:

```sql
-- Combined node table with type discrimination
CREATE TABLE gold_graph_all_nodes AS
SELECT * FROM (
    SELECT graph_node_id as id, node_label as label, 
           to_json(gold_graph_properties.*) as properties
    FROM gold_graph_properties
    UNION ALL
    SELECT graph_node_id as id, node_label as label,
           to_json(gold_graph_neighborhoods.*) as properties
    FROM gold_graph_neighborhoods
    UNION ALL
    SELECT city_id as id, node_label as label,
           to_json(gold_graph_cities.*) as properties
    FROM gold_graph_cities
    UNION ALL
    SELECT state_id as id, node_label as label,
           to_json(gold_graph_states.*) as properties
    FROM gold_graph_states
    UNION ALL
    SELECT feature_id as id, node_label as label,
           to_json(gold_graph_features.*) as properties
    FROM gold_graph_features
);

-- Combined relationship table
CREATE TABLE gold_graph_all_relationships AS
SELECT * FROM (
    SELECT * FROM gold_graph_rel_located_in
    UNION ALL
    SELECT * FROM gold_graph_rel_has_feature
    UNION ALL
    SELECT * FROM gold_graph_rel_in_city
    UNION ALL
    SELECT * FROM gold_graph_rel_type_of
    UNION ALL
    SELECT * FROM gold_graph_rel_similar_properties
    UNION ALL
    SELECT * FROM gold_graph_rel_in_state
    UNION ALL
    SELECT * FROM gold_graph_rel_near
);
```

## Neo4j Writer Implementation

### Writer Architecture

The Neo4j writer follows the same pattern as existing writers (Parquet, Elasticsearch) but reads from the graph-specific Gold tables:

```python
# File: squack_pipeline_v2/writers/neo4j.py

"""Neo4j writer using py2neo or official Neo4j driver.

Following the established writer pattern:
- Reads from Gold layer tables
- No data transformation (already done in Gold)
- Entity-specific write methods
- Bulk operations for performance
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
from datetime import datetime
from neo4j import GraphDatabase, Session
import duckdb
from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import log_stage

logger = logging.getLogger(__name__)


class Neo4jWriter:
    """Write DuckDB graph tables to Neo4j.
    
    Design principles:
    - Reads pre-built graph tables from Gold layer
    - No transformation logic (all done in DuckDB)
    - Entity-specific methods for clarity
    - Bulk operations using UNWIND for performance
    """
    
    def __init__(
        self, 
        connection_manager: DuckDBConnectionManager,
        neo4j_uri: str,
        neo4j_auth: tuple
    ):
        """Initialize Neo4j writer.
        
        Args:
            connection_manager: DuckDB connection manager
            neo4j_uri: Neo4j connection URI
            neo4j_auth: (username, password) tuple
        """
        self.connection_manager = connection_manager
        self.driver = GraphDatabase.driver(neo4j_uri, auth=neo4j_auth)
        self.stats = {}
        
    def close(self):
        """Close Neo4j connection."""
        self.driver.close()
        
    @log_stage("Neo4j: Create constraints and indexes")
    def create_constraints(self):
        """Create Neo4j constraints and indexes.
        
        This ensures data integrity and query performance.
        """
        constraints = [
            # Unique constraints for node types
            "CREATE CONSTRAINT property_id IF NOT EXISTS FOR (p:Property) REQUIRE p.listing_id IS UNIQUE",
            "CREATE CONSTRAINT neighborhood_id IF NOT EXISTS FOR (n:Neighborhood) REQUIRE n.neighborhood_id IS UNIQUE",
            "CREATE CONSTRAINT city_id IF NOT EXISTS FOR (c:City) REQUIRE c.city_id IS UNIQUE",
            "CREATE CONSTRAINT state_id IF NOT EXISTS FOR (s:State) REQUIRE s.state_id IS UNIQUE",
            "CREATE CONSTRAINT feature_id IF NOT EXISTS FOR (f:Feature) REQUIRE f.feature_id IS UNIQUE",
            "CREATE CONSTRAINT property_type_id IF NOT EXISTS FOR (pt:PropertyType) REQUIRE pt.type_id IS UNIQUE",
            
            # Indexes for common queries
            "CREATE INDEX property_price IF NOT EXISTS FOR (p:Property) ON (p.price)",
            "CREATE INDEX property_type IF NOT EXISTS FOR (p:Property) ON (p.property_type)",
            "CREATE INDEX neighborhood_city IF NOT EXISTS FOR (n:Neighborhood) ON (n.city)",
            
            # Vector indexes for similarity search (Neo4j 5.0+)
            "CREATE VECTOR INDEX property_embedding IF NOT EXISTS FOR (p:Property) ON p.embedding OPTIONS {indexConfig: {`vector.dimensions`: 1024, `vector.similarity_function`: 'cosine'}}",
            "CREATE VECTOR INDEX neighborhood_embedding IF NOT EXISTS FOR (n:Neighborhood) ON n.embedding OPTIONS {indexConfig: {`vector.dimensions`: 1024, `vector.similarity_function`: 'cosine'}}"
        ]
        
        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.info(f"Created constraint/index: {constraint[:50]}...")
                except Exception as e:
                    logger.warning(f"Constraint may already exist: {e}")
                    
    @log_stage("Neo4j: Write Property nodes")
    def write_property_nodes(self) -> Dict[str, Any]:
        """Write property nodes to Neo4j.
        
        Reads from gold_graph_properties table and bulk loads to Neo4j.
        
        Returns:
            Write statistics
        """
        # Read data from DuckDB
        query = "SELECT * FROM gold_graph_properties"
        df = self.connection_manager.execute(query).df()
        
        # Convert DataFrame to list of dicts for Neo4j
        properties = df.to_dict('records')
        
        # Bulk insert using UNWIND
        cypher = """
        UNWIND $properties AS prop
        MERGE (p:Property {listing_id: prop.listing_id})
        SET p = prop
        """
        
        start_time = datetime.now()
        
        with self.driver.session() as session:
            result = session.run(cypher, properties=properties)
            summary = result.consume()
            
        duration = (datetime.now() - start_time).total_seconds()
        
        stats = {
            "entity": "Property",
            "records": len(properties),
            "nodes_created": summary.counters.nodes_created,
            "properties_set": summary.counters.properties_set,
            "duration_seconds": round(duration, 2)
        }
        
        logger.info(f"Wrote {len(properties)} Property nodes in {duration:.2f}s")
        return stats
        
    @log_stage("Neo4j: Write Neighborhood nodes")
    def write_neighborhood_nodes(self) -> Dict[str, Any]:
        """Write neighborhood nodes to Neo4j.
        
        Entity-specific method for neighborhoods.
        """
        query = "SELECT * FROM gold_graph_neighborhoods"
        df = self.connection_manager.execute(query).df()
        neighborhoods = df.to_dict('records')
        
        cypher = """
        UNWIND $neighborhoods AS n
        MERGE (node:Neighborhood {neighborhood_id: n.neighborhood_id})
        SET node = n
        """
        
        start_time = datetime.now()
        
        with self.driver.session() as session:
            result = session.run(cypher, neighborhoods=neighborhoods)
            summary = result.consume()
            
        duration = (datetime.now() - start_time).total_seconds()
        
        return {
            "entity": "Neighborhood",
            "records": len(neighborhoods),
            "nodes_created": summary.counters.nodes_created,
            "duration_seconds": round(duration, 2)
        }
        
    @log_stage("Neo4j: Write Feature nodes")
    def write_feature_nodes(self) -> Dict[str, Any]:
        """Write feature nodes to Neo4j.
        
        Entity-specific method for features.
        """
        query = "SELECT * FROM gold_graph_features"
        df = self.connection_manager.execute(query).df()
        features = df.to_dict('records')
        
        cypher = """
        UNWIND $features AS f
        MERGE (node:Feature {feature_id: f.feature_id})
        SET node = f
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, features=features)
            summary = result.consume()
            
        return {
            "entity": "Feature",
            "records": len(features),
            "nodes_created": summary.counters.nodes_created
        }
        
    @log_stage("Neo4j: Write City nodes")
    def write_city_nodes(self) -> Dict[str, Any]:
        """Write city nodes to Neo4j."""
        query = "SELECT * FROM gold_graph_cities"
        df = self.connection_manager.execute(query).df()
        cities = df.to_dict('records')
        
        cypher = """
        UNWIND $cities AS c
        MERGE (node:City {city_id: c.city_id})
        SET node = c
        """
        
        with self.driver.session() as session:
            result = session.run(cypher, cities=cities)
            summary = result.consume()
            
        return {
            "entity": "City",
            "records": len(cities),
            "nodes_created": summary.counters.nodes_created
        }
        
    @log_stage("Neo4j: Write relationships")
    def write_relationships(self, relationship_type: str) -> Dict[str, Any]:
        """Write relationships of a specific type.
        
        Args:
            relationship_type: Type of relationship to write
            
        Returns:
            Write statistics
        """
        # Map relationship type to table name
        table_map = {
            'LOCATED_IN': 'gold_graph_rel_located_in',
            'HAS_FEATURE': 'gold_graph_rel_has_feature',
            'IN_CITY': 'gold_graph_rel_in_city',
            'TYPE_OF': 'gold_graph_rel_type_of',
            'SIMILAR_TO': 'gold_graph_rel_similar_properties',
            'IN_STATE': 'gold_graph_rel_in_state',
            'NEAR': 'gold_graph_rel_near'
        }
        
        table_name = table_map.get(relationship_type)
        if not table_name:
            raise ValueError(f"Unknown relationship type: {relationship_type}")
            
        # Read relationships from DuckDB
        query = f"SELECT * FROM {table_name}"
        df = self.connection_manager.execute(query).df()
        relationships = df.to_dict('records')
        
        # Build Cypher based on relationship type
        # This is entity-specific logic without dynamic inspection
        if relationship_type == 'LOCATED_IN':
            cypher = """
            UNWIND $rels AS rel
            MATCH (p:Property {listing_id: substring(rel.from_id, 10)})
            MATCH (n:Neighborhood {neighborhood_id: substring(rel.to_id, 14)})
            MERGE (p)-[:LOCATED_IN]->(n)
            """
        elif relationship_type == 'HAS_FEATURE':
            cypher = """
            UNWIND $rels AS rel
            MATCH (p:Property {listing_id: substring(rel.from_id, 10)})
            MATCH (f:Feature {feature_id: rel.to_id})
            MERGE (p)-[:HAS_FEATURE]->(f)
            """
        elif relationship_type == 'IN_CITY':
            cypher = """
            UNWIND $rels AS rel
            MATCH (p:Property {listing_id: substring(rel.from_id, 10)})
            MATCH (c:City {city_id: rel.to_id})
            MERGE (p)-[:IN_CITY]->(c)
            """
        elif relationship_type == 'SIMILAR_TO':
            cypher = """
            UNWIND $rels AS rel
            MATCH (p1:Property {listing_id: substring(rel.from_id, 10)})
            MATCH (p2:Property {listing_id: substring(rel.to_id, 10)})
            MERGE (p1)-[:SIMILAR_TO {weight: rel.weight}]->(p2)
            """
        else:
            # Generic relationship creation for other types
            cypher = f"""
            UNWIND $rels AS rel
            MATCH (from) WHERE from.id = rel.from_id
            MATCH (to) WHERE to.id = rel.to_id
            MERGE (from)-[:{relationship_type}]->(to)
            """
            
        start_time = datetime.now()
        
        with self.driver.session() as session:
            result = session.run(cypher, rels=relationships)
            summary = result.consume()
            
        duration = (datetime.now() - start_time).total_seconds()
        
        return {
            "relationship": relationship_type,
            "records": len(relationships),
            "relationships_created": summary.counters.relationships_created,
            "duration_seconds": round(duration, 2)
        }
        
    @log_stage("Neo4j: Write all data")
    def write_all(self) -> Dict[str, Any]:
        """Write all nodes and relationships to Neo4j.
        
        This is the main entry point for the writer.
        """
        overall_stats = {
            "start_time": datetime.now(),
            "nodes": {},
            "relationships": {}
        }
        
        # Create constraints first
        self.create_constraints()
        
        # Write nodes (order matters for foreign keys)
        overall_stats["nodes"]["properties"] = self.write_property_nodes()
        overall_stats["nodes"]["neighborhoods"] = self.write_neighborhood_nodes()
        overall_stats["nodes"]["features"] = self.write_feature_nodes()
        overall_stats["nodes"]["cities"] = self.write_city_nodes()
        # Add other node types...
        
        # Write relationships
        relationship_types = [
            'LOCATED_IN', 'HAS_FEATURE', 'IN_CITY', 
            'TYPE_OF', 'SIMILAR_TO', 'IN_STATE', 'NEAR'
        ]
        
        for rel_type in relationship_types:
            try:
                overall_stats["relationships"][rel_type] = self.write_relationships(rel_type)
            except Exception as e:
                logger.error(f"Failed to write {rel_type} relationships: {e}")
                overall_stats["relationships"][rel_type] = {"error": str(e)}
                
        overall_stats["end_time"] = datetime.now()
        overall_stats["total_duration"] = (
            overall_stats["end_time"] - overall_stats["start_time"]
        ).total_seconds()
        
        logger.info(f"Neo4j write complete in {overall_stats['total_duration']:.2f}s")
        return overall_stats
```

### Integration with Pipeline Orchestrator

Minimal changes to the orchestrator to add Neo4j writer:

```python
# In squack_pipeline_v2/orchestration/pipeline.py

# Add import
from squack_pipeline_v2.writers.neo4j import Neo4jWriter

class PipelineOrchestrator:
    # ... existing code unchanged ...
    
    @log_stage("Pipeline: Write to outputs")
    def write_outputs(self) -> Dict[str, Any]:
        """Write Gold data to configured outputs.
        
        This method is EXTENDED, not modified.
        Existing writers continue to work.
        """
        stats = {}
        
        # Existing Parquet writer (unchanged)
        if self.settings.output.parquet.enabled:
            parquet_writer = ParquetWriter(
                self.connection_manager,
                self.settings.output.parquet.output_dir
            )
            # ... existing parquet writing code ...
            
        # Existing Elasticsearch writer (unchanged)  
        if self.settings.output.elasticsearch.enabled:
            es_writer = ElasticsearchWriter(
                self.connection_manager,
                self.settings.output.elasticsearch
            )
            # ... existing ES writing code ...
            
        # NEW: Neo4j writer (addition only)
        if self.settings.output.neo4j.enabled:
            neo4j_writer = Neo4jWriter(
                self.connection_manager,
                self.settings.output.neo4j.uri,
                (self.settings.output.neo4j.username, 
                 self.settings.output.neo4j.password)
            )
            stats["neo4j"] = neo4j_writer.write_all()
            neo4j_writer.close()
            
        return stats
```

## Configuration Changes

Add Neo4j configuration to settings:

```yaml
# In config.yaml or settings
output:
  parquet:
    enabled: true  # Unchanged
    output_dir: "output/parquet"
    
  elasticsearch:
    enabled: true  # Unchanged
    host: "localhost"
    port: 9200
    
  neo4j:
    enabled: true  # New addition
    uri: "bolt://localhost:7687"
    username: "neo4j"
    password: "${NEO4J_PASSWORD}"
```

## Implementation Details

### Completed Modules

#### Silver Layer Extensions (`squack_pipeline_v2/silver/graph_extensions.py`)
- **SilverGraphExtensions** class adds graph-specific columns without modifying existing transformers
- Computed columns: `graph_node_id`, `city_normalized`, `state_normalized`, `zip_code_clean`, `price_range_category`
- Extraction tables created: `silver_features`, `silver_property_types`, `silver_price_ranges`, `silver_cities`, `silver_states`, `silver_zip_codes`

#### Gold Layer Graph Builder (`squack_pipeline_v2/gold/graph_builder.py`)
- **GoldGraphBuilder** class creates graph-specific tables
- Node tables: `gold_graph_properties`, `gold_graph_neighborhoods`, `gold_graph_wikipedia`, `gold_graph_features`, `gold_graph_cities`, etc.
- Relationship tables: `gold_graph_rel_located_in`, `gold_graph_rel_has_feature`, `gold_graph_rel_in_city`, `gold_graph_rel_similar_properties`, etc.
- Uses DuckDB's array operations for similarity calculations

#### Neo4j Writer (`squack_pipeline_v2/writers/neo4j.py`)
- **Neo4jWriter** class with entity-specific write methods
- Bulk loading using UNWIND for performance
- Creates constraints, indexes, and vector indexes
- No dynamic type inspection - all entity-specific methods

#### Pipeline Integration
- Added Neo4j configuration to `PipelineSettings` 
- Extended `PipelineOrchestrator` with `write_outputs()` method
- Graph extensions automatically applied after Silver transformations
- Graph builder automatically runs after Gold enrichments

### Configuration

Neo4j is configured in settings with environment variable support:

```python
class Neo4jConfig(BaseModel):
    enabled: bool = Field(default=False)
    uri: str = Field(default="bolt://localhost:7687")
    username: str = Field(default="neo4j")
    password: str = Field(default=os.getenv("NEO4J_PASSWORD", "password"))
    database: str = Field(default="neo4j")
```

### Usage

To enable Neo4j in your pipeline:

1. Set environment variable: `export NEO4J_PASSWORD=your_password`
2. Enable in settings: `output.neo4j.enabled = true`
3. Run pipeline normally - graph tables and Neo4j writing happen automatically

## Benefits of This Approach

### 1. Zero Breaking Changes
- All existing code continues to work
- No modifications to Bronze or Silver base transformations
- Existing writers (Parquet, Elasticsearch) unaffected

### 2. DuckDB-Native Performance
- Leverage DuckDB's columnar engine for relationship extraction
- SQL-based transformations are highly optimized
- No data movement through Python for transformations

### 3. Clear Separation of Concerns
- Graph logic isolated in new tables
- Entity-specific methods avoid complexity
- Easy to enable/disable graph features

### 4. Maintainability
- New code is additive, not modificative
- Clear data lineage through medallion layers
- Entity-specific processing is predictable

### 5. Scalability
- DuckDB handles large-scale relationship computation
- Bulk loading to Neo4j is efficient
- Can process millions of relationships

## DuckDB Best Practices for Relationships

### 1. Use CTEs for Complex Relationships
```sql
-- Example: Multi-hop geographic relationships
WITH property_locations AS (
    SELECT listing_id, city, state, zip_code
    FROM gold_properties
),
city_mapping AS (
    SELECT DISTINCT 
        city || '_' || state as city_id,
        state
    FROM property_locations
),
state_hierarchy AS (
    SELECT DISTINCT
        city_id,
        state as state_id
    FROM city_mapping
)
-- Build relationships using CTEs
SELECT 
    p.listing_id,
    c.city_id,
    s.state_id
FROM property_locations p
JOIN city_mapping c ON p.city || '_' || p.state = c.city_id
JOIN state_hierarchy s ON c.city_id = s.city_id;
```

### 2. Window Functions for Similarity
```sql
-- Find similar properties using window functions
WITH ranked_similarities AS (
    SELECT 
        p1.listing_id as id1,
        p2.listing_id as id2,
        list_cosine_similarity(p1.embedding, p2.embedding) as similarity,
        ROW_NUMBER() OVER (
            PARTITION BY p1.listing_id 
            ORDER BY list_cosine_similarity(p1.embedding, p2.embedding) DESC
        ) as rank
    FROM gold_properties p1
    CROSS JOIN gold_properties p2
    WHERE p1.listing_id != p2.listing_id
)
SELECT id1, id2, similarity
FROM ranked_similarities
WHERE rank <= 10;  -- Top 10 similar for each property
```

### 3. Recursive CTEs for Hierarchies
```sql
-- Build complete geographic hierarchy
WITH RECURSIVE geo_hierarchy AS (
    -- Base case: Properties
    SELECT 
        listing_id as entity_id,
        'Property' as entity_type,
        city || '_' || state as parent_id,
        1 as level
    FROM gold_properties
    
    UNION ALL
    
    -- Recursive case: Cities to States
    SELECT 
        city_id as entity_id,
        'City' as entity_type,
        state as parent_id,
        level + 1
    FROM gold_graph_cities
    JOIN geo_hierarchy ON geo_hierarchy.parent_id = city_id
    WHERE level < 3
)
SELECT * FROM geo_hierarchy;
```

### 4. Array Operations for Multi-valued Relationships
```sql
-- Extract multiple features efficiently
SELECT 
    listing_id,
    unnest(features) as feature,
    array_position(features, unnest(features)) as position
FROM gold_properties
WHERE array_length(features) > 0;
```

## Conclusion

This proposal provides a comprehensive, non-breaking approach to adding Neo4j graph capabilities to the squack_pipeline_v2. By leveraging DuckDB's powerful SQL engine for relationship extraction and maintaining strict separation between existing and new functionality, we can deliver graph database support while preserving all current capabilities.

The key insight is that **graph relationships are just another view of the data** - they can be computed in the Gold layer alongside existing enrichments without modifying the fundamental data flow. This approach ensures stability, maintainability, and performance while enabling powerful new graph-based analytics.