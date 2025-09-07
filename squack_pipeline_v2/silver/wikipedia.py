"""Wikipedia Silver layer transformation - Clean implementation without temporary tables."""

from typing import Optional
from squack_pipeline_v2.silver.base import SilverTransformer
from squack_pipeline_v2.core.logging import log_stage
from squack_pipeline_v2.utils.table_validation import validate_table_name
from squack_pipeline_v2.utils.state_utils import StateStandardizer
from squack_pipeline_v2.utils.neighborhood_enrichment import (
    NeighborhoodWikipediaEnricher,
    NeighborhoodEnrichmentResult
)
from datetime import datetime


class WikipediaSilverTransformer(SilverTransformer):
    """Transformer for Wikipedia data into Silver layer using DuckDB best practices.
    
    Silver layer principles:
    - Standardize field names (pageid → page_id)
    - Validate data quality
    - Clean text fields
    - Standardize location data
    - Generate semantic embeddings for content search
    - Always include neighborhood fields
    - NO temporary tables - use CTEs only
    """
    
    def _get_entity_type(self) -> str:
        """Return entity type."""
        return "wikipedia"
    
    @log_stage("Silver: Wikipedia Transformation")
    def _apply_transformations(self, input_table: str, output_table: str) -> None:
        """Apply Wikipedia transformations using DuckDB best practices.
        
        Complete cutover implementation:
        - No temporary tables - use CTEs and VALUES
        - Always include neighborhood fields
        - Single CREATE TABLE operation
        - No compatibility checks
        
        Args:
            input_table: Bronze input table
            output_table: Silver output table
        """
        # Validate table names (DuckDB best practice)
        input_table = validate_table_name(input_table)
        output_table = validate_table_name(output_table)
        
        conn = self.connection_manager.get_connection()
        
        # Get state transformation SQL
        state_case_sql = StateStandardizer.get_sql_case_statement('best_state', 'state')
        
        # Build the transformation query
        transformation_sql = f"""
            SELECT
                id,
                pageid as page_id,
                location_id,
                TRIM(title) as title,
                url,
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
                short_summary,
                long_summary,
                CONCAT_WS(' | ', TRIM(title), TRIM(long_summary)) as embedding_text
            FROM {input_table}
            WHERE pageid IS NOT NULL
        """
        
        # Get all data for embedding generation
        wiki_data = conn.execute(transformation_sql).df()
        total_count = len(wiki_data)
        
        if total_count == 0:
            # Create empty table with proper schema
            conn.execute(f"""
                CREATE TABLE {output_table} (
                    id BIGINT,
                    page_id INTEGER,
                    location_id VARCHAR,
                    title VARCHAR,
                    url VARCHAR,
                    categories VARCHAR,
                    latitude DOUBLE,
                    longitude DOUBLE,
                    city VARCHAR,
                    county VARCHAR,
                    state VARCHAR,
                    relevance_score DOUBLE,
                    depth INTEGER,
                    crawled_at TIMESTAMP,
                    html_file VARCHAR,
                    file_hash VARCHAR,
                    image_url VARCHAR,
                    links_count INTEGER,
                    infobox_data VARCHAR,
                    short_summary VARCHAR,
                    long_summary VARCHAR,
                    embedding_text VARCHAR,
                    embedding_vector DOUBLE[],
                    embedding_generated_at TIMESTAMP,
                    neighborhood_ids VARCHAR[],
                    neighborhood_names VARCHAR[],
                    primary_neighborhood_name VARCHAR
                )
            """)
            self.logger.info(f"No data to transform from {input_table}")
            return
        
        self.logger.info(f"Processing {total_count} Wikipedia articles for embeddings")
        
        # Generate embeddings in batches
        embeddings = []
        batch_size = 100
        current_timestamp = datetime.now().isoformat()
        
        for i in range(0, total_count, batch_size):
            batch_end = min(i + batch_size, total_count)
            batch = wiki_data.iloc[i:batch_end]
            
            self.logger.info(f"Generating embeddings for batch {i//batch_size + 1} ({batch_end}/{total_count} articles)")
            
            texts_to_embed = []
            indices_to_embed = []
            
            for idx, row in batch.iterrows():
                # ALWAYS generate embeddings for Wikipedia articles
                # The embedding_text is title + long_summary which should always exist
                text = row.get('embedding_text', '')
                texts_to_embed.append(str(text))
                indices_to_embed.append(idx)
            
            # Always generate embeddings - no conditional needed
            # Wikipedia articles MUST have embeddings for search to work
            try:
                response = self.embedding_provider.generate_embeddings(texts_to_embed)
                for j, idx in enumerate(indices_to_embed):
                    page_id = wiki_data.loc[idx, 'page_id']
                    vector = response.embeddings[j]
                    embeddings.append({
                        'page_id': page_id,
                        'vector': vector,
                        'timestamp': current_timestamp
                    })
            except Exception as e:
                self.logger.error(f"Critical error generating embeddings for batch: {e}")
                raise RuntimeError(f"Failed to generate embeddings for Wikipedia articles: {e}")
        
        self.logger.info(f"Generated {len(embeddings)} embeddings")
        
        # Build embedding VALUES clause
        embedding_rows = []
        for emb in embeddings:
            vector_str = 'ARRAY[' + ','.join(str(v) for v in emb['vector']) + ']::DOUBLE[]'
            embedding_rows.append(f"({emb['page_id']}, {vector_str}, TIMESTAMP '{emb['timestamp']}')")
        
        if embedding_rows:
            embedding_values = ',\n                '.join(embedding_rows)
            embeddings_cte = f"""
                embeddings AS (
                    SELECT 
                        page_id,
                        embedding_vector,
                        embedding_generated_at
                    FROM (VALUES 
                        {embedding_values}
                    ) AS e(page_id, embedding_vector, embedding_generated_at)
                )"""
        else:
            # No embeddings - create empty CTE
            embeddings_cte = """
                embeddings AS (
                    SELECT 
                        NULL::INTEGER as page_id,
                        NULL::DOUBLE[] as embedding_vector,
                        NULL::TIMESTAMP as embedding_generated_at
                    WHERE FALSE
                )"""
        
        # Check if silver_neighborhoods table exists
        table_exists = conn.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_name = 'silver_neighborhoods'
        """).fetchone()[0] > 0
        
        if table_exists:
            neighborhoods_cte = """
                neighborhoods AS (
                    SELECT 
                        wikipedia_page_id as page_id,
                        LIST(DISTINCT neighborhood_id ORDER BY neighborhood_id) as neighborhood_ids,
                        LIST(DISTINCT name ORDER BY name) as neighborhood_names,
                        FIRST(name ORDER BY neighborhood_id) as primary_neighborhood_name
                    FROM silver_neighborhoods
                    WHERE wikipedia_page_id IS NOT NULL
                    GROUP BY wikipedia_page_id
                )"""
        else:
            # Table doesn't exist - create empty CTE
            neighborhoods_cte = """
                neighborhoods AS (
                    SELECT 
                        NULL::INTEGER as page_id,
                        ARRAY[]::VARCHAR[] as neighborhood_ids,
                        ARRAY[]::VARCHAR[] as neighborhood_names,
                        NULL::VARCHAR as primary_neighborhood_name
                    WHERE FALSE
                )"""
        
        # Create final table with all CTEs - no temporary tables
        conn.execute(f"""
            CREATE TABLE {output_table} AS
            WITH transformed_data AS (
                {transformation_sql}
            ),
            {embeddings_cte},
            {neighborhoods_cte}
            SELECT 
                t.id,
                t.page_id,
                t.location_id,
                t.title,
                t.url,
                t.categories,
                t.latitude,
                t.longitude,
                t.city,
                t.county,
                t.state,
                t.relevance_score,
                t.depth,
                t.crawled_at,
                t.html_file,
                t.file_hash,
                t.image_url,
                t.links_count,
                t.infobox_data,
                t.short_summary,
                t.long_summary,
                t.embedding_text,
                e.embedding_vector,
                e.embedding_generated_at,
                COALESCE(n.neighborhood_ids, ARRAY[]::VARCHAR[]) as neighborhood_ids,
                COALESCE(n.neighborhood_names, ARRAY[]::VARCHAR[]) as neighborhood_names,
                n.primary_neighborhood_name
            FROM transformed_data t
            LEFT JOIN embeddings e ON t.page_id = e.page_id
            LEFT JOIN neighborhoods n ON t.page_id = n.page_id
            ORDER BY t.page_id
        """)
        
        # Log statistics
        output_count = conn.execute(f"SELECT COUNT(*) FROM {output_table}").fetchone()[0]
        embedding_count = conn.execute(f"SELECT COUNT(*) FROM {output_table} WHERE embedding_vector IS NOT NULL").fetchone()[0]
        
        # Log neighborhood enrichment stats
        enricher = NeighborhoodWikipediaEnricher(conn)
        stats = enricher.get_enrichment_statistics(output_table)
        if stats.articles_enriched > 0:
            self.logger.info(f"Enriched {stats.articles_enriched} articles with neighborhood data")
        
        self.logger.info(f"Transformed {output_count} Wikipedia articles from {input_table} to {output_table}")
        if output_count > 0:
            self.logger.info(f"Successfully embedded {embedding_count}/{output_count} articles ({embedding_count*100/output_count:.1f}%)")