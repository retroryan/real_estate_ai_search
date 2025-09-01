"""Neighborhood Silver layer transformation using DuckDB Relation API."""

from squack_pipeline_v2.silver.base import SilverTransformer
from squack_pipeline_v2.core.logging import log_stage


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
        """)
        
        # Project to standardized columns using Relation API
        transformed = filtered.project("""
            neighborhood_id,
            name,
            city,
            state,
            
            CASE 
                WHEN coordinates.longitude IS NOT NULL AND coordinates.latitude IS NOT NULL
                THEN LIST_VALUE(coordinates.longitude, coordinates.latitude)
                ELSE NULL
            END as location,
            
            demographics.population as population,
            characteristics.walkability_score as walkability_score,
            characteristics.school_rating as school_rating,
            
            demographics,
            description,
            amenities,
            lifestyle_tags,
            wikipedia_correlations,
            CONCAT_WS(' | ',
                COALESCE(description, ''),
                COALESCE(name, ''),
                CONCAT('Population: ', COALESCE(demographics.population, 0))
            ) as embedding_text
        """)
        
        if self.embedding_provider:
            # Get embedding text data using Relation API
            embedding_data = transformed.project("neighborhood_id, embedding_text").df()
            
            # Generate embeddings
            if len(embedding_data) > 0:
                embedding_response = self.embedding_provider.generate_embeddings(embedding_data['embedding_text'].tolist())
                from datetime import datetime
                embedding_data['embedding_vector'] = embedding_response.embeddings
                embedding_data['embedding_generated_at'] = datetime.now()
                conn.register('embedding_data', embedding_data)
                
                # Join embeddings using Relation API and create table
                final_result = (transformed
                    .join(conn.table('embedding_data'), 'neighborhood_id', how='left')
                    .project("""
                        neighborhood_id,
                        name,
                        city,
                        state,
                        location,
                        population,
                        walkability_score,
                        school_rating,
                        demographics,
                        description,
                        amenities,
                        lifestyle_tags,
                        wikipedia_correlations,
                        embedding_data.embedding_text,
                        embedding_data.embedding_vector,
                        embedding_data.embedding_generated_at
                    """))
                
                final_result.create(output_table)
                conn.unregister('embedding_data')
            else:
                # No embeddings generated - add NULL columns
                no_embeddings = transformed.project("""
                    *,
                    CAST(NULL AS DOUBLE[1024]) as embedding_vector,
                    CAST(NULL AS TIMESTAMP) as embedding_generated_at
                """)
                no_embeddings.create(output_table)
        else:
            # No embedding provider - add NULL embedding columns
            no_embeddings = transformed.project("""
                *,
                CAST(NULL AS DOUBLE[1024]) as embedding_vector,
                CAST(NULL AS TIMESTAMP) as embedding_generated_at
            """)
            no_embeddings.create(output_table)
        
        self.logger.info(f"Transformed neighborhoods from {input_table} to {output_table}")