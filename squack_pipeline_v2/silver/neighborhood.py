"""Neighborhood Silver layer transformation using DuckDB Relation API.

NEIGHBORHOOD EMBEDDING GENERATION DETAILS:
==========================================

This module transforms neighborhood data into the Silver layer with semantic embeddings
that capture the essence of each neighborhood for similarity search and matching.

EMBEDDING TEXT COMPOSITION FOR NEIGHBORHOODS:
---------------------------------------------
The embedding_text field combines key neighborhood characteristics using pipe delimiter:

1. **description** (Primary): Comprehensive neighborhood description containing
   details about the area's character, history, lifestyle, attractions, and ambiance.
   This narrative text provides the richest semantic content about the neighborhood.

2. **name**: Neighborhood name for identity and recognition
   Important for matching searches that reference specific neighborhood names.

3. **population**: Demographic size indicator formatted as "Population: X"
   Provides scale context that affects neighborhood character and amenities.

FIELD SELECTION RATIONALE:
--------------------------
- **Description First**: Contains the most comprehensive semantic information
- **Name for Identity**: Essential for name-based searches and disambiguation
- **Population for Scale**: Indicates urban vs suburban character

DELIMITER CHOICE (PIPE |):
-------------------------
- Pipe delimiter used instead of space to create clearer semantic boundaries
- Format: "description | name | Population: X"
- Helps embedding model distinguish between different information types

FIELDS EXCLUDED FROM NEIGHBORHOOD EMBEDDINGS:
---------------------------------------------
- **City/State/County**: Geographic hierarchy handled separately via joins
- **Coordinates**: Geo-location handled via dedicated location fields
- **Scores (walkability, school)**: Numeric metrics better for structured filters
- **Demographics struct**: Complex nested data not suitable for text embedding
- **Amenities/Lifestyle tags**: Could be included but kept separate for faceted search

ENRICHMENT WITH LOCATION DATA:
------------------------------
This transformer also performs a LEFT JOIN with silver_locations table to:
- Add standardized county information
- Include geographic hierarchy IDs (city_id, county_id, state_id)
- Ensure consistent location standardization across the pipeline

EMBEDDING GENERATION PROCESS:
-----------------------------
1. SQL projection creates embedding_text using CONCAT_WS with pipe delimiter (lines 97-101)
2. Neighborhood IDs and texts extracted from DuckDB (lines 105-110)
3. Texts sent to embedding provider in batches (line 112)
4. Vectors stored as DOUBLE[] arrays with generation timestamp (lines 114-132)
5. Embeddings joined back via neighborhood_id (lines 135-160)

TOKENIZATION NOTES:
------------------
- No LlamaIndex usage - direct API embedding generation
- Provider handles tokenization internally:
  * Voyage AI: Proprietary tokenizer for voyage-3 model
  * OpenAI: tiktoken (cl100k_base) for text-embedding-3 models
  * Ollama: Model-specific tokenizers
- Text sent as-is without pre-chunking or preprocessing
"""

from squack_pipeline_v2.silver.base import SilverTransformer
from squack_pipeline_v2.core.logging import log_stage
from squack_pipeline_v2.utils.simple_historical import generate_neighborhood_historical
from datetime import datetime
import json


class NeighborhoodSilverTransformer(SilverTransformer):
    """Transformer for neighborhood data into Silver layer using Relation API.
    
    Silver layer principles:
    - Flatten key metrics for analysis
    - Standardize location data
    - Clean and validate fields
    - Prepare for downstream consumption
    - Generate semantic embeddings for neighborhood similarity
    """
    
    def _get_entity_type(self) -> str:
        """Return entity type."""
        return "neighborhood"
    
    
    @log_stage("Silver: Neighborhood Transformation")
    def _apply_transformations(self, input_table: str, output_table: str) -> None:
        """Apply neighborhood transformations using DuckDB Relation API.
        
        Following DuckDB best practices:
        - Use Relation API throughout
        - Single CREATE TABLE operation
        - No column duplication
        
        Args:
            input_table: Bronze input table
            output_table: Silver output table
        """
        conn = self.connection_manager.get_connection()
        
        # Use Relation API to create base transformation
        bronze = conn.table(input_table)
        
        # Apply filters using Relation API
        filtered = bronze.filter("""
            neighborhood_id IS NOT NULL 
            AND name IS NOT NULL
        """).set_alias("n")
        
        # Join with silver_locations to enrich with county data
        locations = conn.table("silver_locations").set_alias("l")
        
        # Join using Relation API to enrich neighborhoods with county data
        enriched = filtered.join(
            locations,
            condition="""
                n.name = l.neighborhood_standardized
                AND n.city = l.city_standardized
                AND n.state = l.state_standardized
            """,
            how="left"
        )
        
        # Project to standardized columns including enriched county data
        transformed = enriched.project("""
            n.neighborhood_id,
            n.name,
            n.city,
            n.state,
            
            -- Enriched geographic hierarchy from locations
            l.county_standardized as county,
            l.city_id,
            l.county_id,
            l.state_id,
            
            CASE 
                WHEN n.coordinates.longitude IS NOT NULL AND n.coordinates.latitude IS NOT NULL
                THEN LIST_VALUE(n.coordinates.longitude, n.coordinates.latitude)
                ELSE NULL
            END as location,
            
            n.demographics.population as population,
            n.characteristics.walkability_score as walkability_score,
            n.characteristics.school_rating as school_rating,
            
            n.demographics,
            n.description,
            n.amenities,
            n.lifestyle_tags,
            
            -- Extract wikipedia page_id from STRUCT in Silver layer (not JSON!)
            n.wikipedia_correlations.primary_wiki_article.page_id as wikipedia_page_id,
            
            -- Pass through full wikipedia_correlations for Gold layer
            n.wikipedia_correlations,
            
            -- EMBEDDING TEXT GENERATION FOR NEIGHBORHOODS:
            -- Concatenate neighborhood characteristics with pipe delimiter
            -- Pipe separator provides clearer semantic boundaries than spaces
            CONCAT_WS(' | ',  -- Pipe-delimited concatenation
                COALESCE(n.description, ''),  -- Primary: Full neighborhood narrative
                COALESCE(n.name, ''),  -- Neighborhood identity for name-based search
                CONCAT('Population: ', COALESCE(n.demographics.population, 0))  -- Scale indicator
            ) as embedding_text
        """)
        
        # STEP 1: Extract text data from DuckDB for embedding generation
        # Get embedding text data directly from DuckDB without pandas conversion
        # Maintains efficient memory usage by avoiding DataFrame intermediaries
        embedding_rows = transformed.project("neighborhood_id, embedding_text").fetchall()
        
        # STEP 2: Prepare data for batch embedding generation
        # Extract data into separate lists for API processing
        neighborhood_ids = [row[0] for row in embedding_rows]  # Unique neighborhood identifiers
        texts = [row[1] for row in embedding_rows]  # Pipe-delimited text for each neighborhood
        
        # STEP 2a: Generate historical data for neighborhoods
        # Generate simple annual historical data (10 years)
        historical_data_map = {}
        for nid in neighborhood_ids:
            # Generate 10 years of annual data with 5% appreciation
            historical_records = generate_neighborhood_historical(nid)
            historical_data_map[nid] = historical_records
        
        # STEP 3: Generate embeddings via external provider API
        # Generate embeddings using List[str] interface
        # Provider performs: tokenization → encoding → dense vector generation
        # No LlamaIndex involvement - direct API embedding generation
        embedding_response = self.embedding_provider.generate_embeddings(texts)
        
        # Create temporary table with embeddings
        current_timestamp = datetime.now()
        
        # Build VALUES clause for embedding data and historical data
        values_clause = []
        for nid, text, embedding in zip(neighborhood_ids, texts, embedding_response.embeddings):
            # Escape single quotes in text
            escaped_text = text.replace("'", "''") if text else ''
            # Format embedding vector as array literal
            embedding_str = '[' + ','.join(str(v) for v in embedding) + ']'
            # Convert historical data to JSON string and escape quotes
            historical_json = json.dumps(historical_data_map[nid]).replace("'", "''")
            values_clause.append(f"('{nid}', '{escaped_text}', {embedding_str}::DOUBLE[], '{historical_json}'::JSON, TIMESTAMP '{current_timestamp}')")
        
        # Create final table with embeddings using CTEs - no temporary tables
        conn.execute(f"""
            CREATE TABLE {output_table} AS
            WITH transformed_data AS (
                {transformed.sql_query()}
            ),
            embedding_data AS (
                SELECT * FROM (
                    VALUES {','.join(values_clause)}
                ) AS t(neighborhood_id, embedding_text, embedding_vector, historical_data, embedding_generated_at)
            )
            SELECT 
                t.neighborhood_id,
                t.name,
                t.city,
                t.state,
                t.county,
                t.city_id,
                t.county_id,
                t.state_id,
                t.location,
                t.population,
                t.walkability_score,
                t.school_rating,
                t.demographics,
                t.description,
                t.amenities,
                t.lifestyle_tags,
                t.wikipedia_page_id,
                t.wikipedia_correlations,
                e.historical_data,
                e.embedding_text,
                e.embedding_vector,
                e.embedding_generated_at
            FROM transformed_data t
            LEFT JOIN embedding_data e ON t.neighborhood_id = e.neighborhood_id
        """)
        
        self.logger.info(f"Transformed neighborhoods from {input_table} to {output_table}")