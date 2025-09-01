"""Neighborhood Silver layer transformation using DuckDB Relation API."""

from squack_pipeline_v2.silver.base import SilverTransformer
from squack_pipeline_v2.core.logging import log_stage
from squack_pipeline_v2.utils.state_utils import StateStandardizer
from datetime import datetime


class NeighborhoodSilverTransformer(SilverTransformer):
    """Transformer for neighborhood data into Silver layer using Relation API.
    
    Silver layer principles:
    - Flatten key metrics for analysis
    - Standardize location data
    - Clean and validate fields
    - Prepare for downstream consumption
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
        # Use StateStandardizer for consistent state matching
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
            
            CONCAT_WS(' | ',
                COALESCE(n.description, ''),
                COALESCE(n.name, ''),
                CONCAT('Population: ', COALESCE(n.demographics.population, 0))
            ) as embedding_text
        """)
        
        # Get embedding text data directly from DuckDB without pandas conversion
        embedding_rows = transformed.project("neighborhood_id, embedding_text").fetchall()
        
        # Extract data into separate lists
        neighborhood_ids = [row[0] for row in embedding_rows]
        texts = [row[1] for row in embedding_rows]
        
        # Generate embeddings using List[str] interface
        embedding_response = self.embedding_provider.generate_embeddings(texts)
        
        # Create temporary table with embeddings
        current_timestamp = datetime.now()
        
        # Build VALUES clause for embedding data
        values_clause = []
        for nid, text, embedding in zip(neighborhood_ids, texts, embedding_response.embeddings):
            # Escape single quotes in text
            escaped_text = text.replace("'", "''") if text else ''
            # Format embedding vector as array literal
            embedding_str = '[' + ','.join(str(v) for v in embedding) + ']'
            values_clause.append(f"('{nid}', '{escaped_text}', {embedding_str}::DOUBLE[], TIMESTAMP '{current_timestamp}')")
        
        # Create embedding table
        conn.execute(f"""
            CREATE TABLE embedding_data AS
            SELECT * FROM (
                VALUES {','.join(values_clause)}
            ) AS t(neighborhood_id, embedding_text, embedding_vector, embedding_generated_at)
        """)
        
        # Join embeddings and create final table
        final_result = (transformed
            .join(conn.table('embedding_data'), 'neighborhood_id', how='left')
            .project("""
                neighborhood_id,
                name,
                city,
                state,
                county,
                city_id,
                county_id,
                state_id,
                location,
                population,
                walkability_score,
                school_rating,
                demographics,
                description,
                amenities,
                lifestyle_tags,
                wikipedia_page_id,
                embedding_data.embedding_text,
                embedding_data.embedding_vector,
                embedding_data.embedding_generated_at
            """))
        
        final_result.create(output_table)
        
        # Clean up temporary table
        conn.execute("DROP TABLE IF EXISTS embedding_data")
        
        self.logger.info(f"Transformed neighborhoods from {input_table} to {output_table}")