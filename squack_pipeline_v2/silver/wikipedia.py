"""Wikipedia Silver layer transformation using DuckDB Relation API."""

from squack_pipeline_v2.silver.base import SilverTransformer
from squack_pipeline_v2.core.logging import log_stage
from squack_pipeline_v2.utils import StateStandardizer


class WikipediaSilverTransformer(SilverTransformer):
    """Transformer for Wikipedia data into Silver layer using Relation API.
    
    Silver layer principles:
    - Standardize field names (pageid → page_id)
    - Validate data quality
    - Clean text fields
    - Standardize location data
    - NO business logic or enrichment (that's Gold layer)
    """
    
    def _get_entity_type(self) -> str:
        """Return entity type."""
        return "wikipedia"
    
    
    @log_stage("Silver: Wikipedia Transformation")
    def _apply_transformations(self, input_table: str, output_table: str) -> None:
        """Apply Wikipedia transformations using DuckDB Relation API.
        
        Following DuckDB best practices:
        - Use Relation API throughout
        - Single CREATE TABLE operation
        - No column duplication
        - Standardize state names to abbreviations
        
        Args:
            input_table: Bronze input table
            output_table: Silver output table
        """
        conn = self.connection_manager.get_connection()
        
        # Get state transformation SQL for use in project
        state_case_sql = StateStandardizer.get_sql_case_statement('best_state', 'state')
        
        # Use Relation API following DuckDB best practices
        bronze = conn.table(input_table)
        
        # Apply filter using Relation API
        filtered = bronze.filter("pageid IS NOT NULL")
        
        # Project to standardized columns using Relation API
        # Note: We need to include the state CASE statement in the project
        transformed = filtered.project(f"""
            id,
            pageid as page_id,
            location_id,
            
            TRIM(title) as title,
            url,
            TRIM(extract) as extract,
            categories,
            
            latitude,
            longitude,
            
            best_city as city,
            best_county as county,
            {state_case_sql},
            
            relevance_score,
            depth,
            crawled_at,
            html_file,
            file_hash,
            image_url,
            links_count,
            infobox_data,
            CONCAT_WS(' | ', TRIM(title), TRIM(extract)) as embedding_text
        """)
        
        if self.embedding_provider:
            # Get embedding text data using Relation API
            embedding_data = transformed.project("page_id, embedding_text").df()
            
            # Generate embeddings
            if len(embedding_data) > 0:
                embedding_response = self.embedding_provider.generate_embeddings(embedding_data['embedding_text'].tolist())
                from datetime import datetime
                embedding_data['embedding_vector'] = embedding_response.embeddings
                embedding_data['embedding_generated_at'] = datetime.now()
                conn.register('embedding_data', embedding_data)
                
                # Join embeddings using Relation API and create table
                final_result = (transformed
                    .join(conn.table('embedding_data'), 'page_id', how='left')
                    .project("""
                        id,
                        page_id,
                        location_id,
                        title,
                        url,
                        extract,
                        categories,
                        latitude,
                        longitude,
                        city,
                        county,
                        state,
                        relevance_score,
                        depth,
                        crawled_at,
                        html_file,
                        file_hash,
                        image_url,
                        links_count,
                        infobox_data,
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
        
        self.logger.info(f"Transformed Wikipedia articles from {input_table} to {output_table}")