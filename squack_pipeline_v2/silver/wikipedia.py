"""Wikipedia Silver layer transformation using DuckDB Relation API.

WIKIPEDIA EMBEDDING GENERATION DETAILS:
=======================================

This module transforms Wikipedia articles into the Silver layer with semantic embeddings
for content-based search and location-relevant knowledge retrieval.

IMPORTANT UPDATE (2024): This module now uses AI-generated summaries from the page_summaries
table instead of the basic Wikipedia extract field. This provides 3-4x more semantic content
for superior embedding quality.

EMBEDDING TEXT COMPOSITION FOR WIKIPEDIA:
-----------------------------------------
The embedding_text field combines the most comprehensive Wikipedia content:

1. **title** (Primary): Article title providing the main subject/topic
   Critical for identifying what the article is about (e.g., "Golden Gate Bridge")

2. **long_summary** (Content): AI-generated comprehensive summary from page_summaries table
   - Replaces the old 'extract' field (which was just Wikipedia's first paragraph)
   - Contains detailed information about history, significance, geographic context, and key facts
   - Average ~985 characters, max ~1873 characters (well within token limits)
   - Provides 3-4x more content than the old extract field (~200-300 chars)

FIELD CONCATENATION STRATEGY:
----------------------------
- Format: "title | long_summary" using pipe delimiter
- TRIM applied to remove leading/trailing whitespace
- Pipe separator creates semantic boundary between title and content

WHY WE SWITCHED FROM EXTRACT TO LONG_SUMMARY:
--------------------------------------------
- **3-4x More Content**: Long summary (~985 chars avg) vs extract (~250 chars avg)
- **AI-Enhanced**: Summaries are AI-generated with structured, comprehensive information
- **Better Context**: Includes historical details, geographic context, demographics, and significance
- **Optimal for Embeddings**: ~250-468 tokens fits comfortably in all provider limits (8k-16k)
- **Richer Semantics**: More detailed content creates better vector representations for search

FIELDS EXCLUDED FROM WIKIPEDIA EMBEDDINGS:
------------------------------------------
- **extract**: REMOVED - Replaced by long_summary which provides 3-4x more content
- **short_summary**: Not used for embeddings (kept for display/UI purposes)
- **URL**: Technical metadata, not semantic content
- **Categories**: Better for structured filtering than semantic search
- **Full HTML content**: Too large and contains formatting/navigation elements
- **Infobox data**: Structured data better for faceted search
- **Location fields**: Geographic data handled separately
- **Links count**: Statistical metadata not relevant for content similarity
- **Crawl metadata**: Technical tracking information

WIKIPEDIA-SPECIFIC CONSIDERATIONS:
----------------------------------
- Articles are already well-structured with clear titles
- Long summary is AI-generated from full Wikipedia content (not just first paragraph)
- Both short_summary and long_summary come from page_summaries table
- No need for complex field combinations as with properties/neighborhoods
- Focus on comprehensive encyclopedic content rather than metadata

LOCATION ENRICHMENT:
-------------------
This transformer also standardizes location data:
- Standardizes state names to abbreviations using StateStandardizer
- Preserves latitude/longitude for geo-queries
- Maintains city/county/state hierarchy for location-based filtering

EMBEDDING GENERATION PROCESS:
----------------------------
1. SQL projection creates embedding_text with CONCAT_WS using long_summary
2. Page IDs and texts extracted from DuckDB
3. Texts sent to embedding provider API
4. Vectors stored as DOUBLE[] arrays with timestamps
5. Embeddings joined back via page_id

TOKENIZATION APPROACH:
---------------------
- No LlamaIndex text splitting or chunking
- Long summary provides comprehensive AI-generated content
- Provider APIs handle tokenization:
  * Token limits not an issue (max ~468 tokens vs 8k-16k limits)
  * Model-specific tokenizers used internally
- Clean text without HTML/wiki markup sent directly
"""

from squack_pipeline_v2.silver.base import SilverTransformer
from squack_pipeline_v2.core.logging import log_stage
from squack_pipeline_v2.utils import StateStandardizer
from datetime import datetime


class WikipediaSilverTransformer(SilverTransformer):
    """Transformer for Wikipedia data into Silver layer using Relation API.
    
    Silver layer principles:
    - Standardize field names (pageid → page_id)
    - Validate data quality
    - Clean text fields
    - Standardize location data
    - Generate semantic embeddings for content search
    - NO business logic or enrichment (that's Gold layer)
    """
    
    def _get_entity_type(self) -> str:
        """Return entity type."""
        return "wikipedia"
    
    
    @log_stage("Silver: Wikipedia Transformation")
    def _apply_transformations(self, input_table: str, output_table: str) -> None:
        """Apply Wikipedia transformations using DuckDB Relation API with efficient batching.
        
        Following DuckDB best practices:
        - Use Relation API throughout
        - Batch embedding operations to prevent memory issues
        - Use multi-row INSERT with parameterized queries for bulk inserts
        - Single CREATE TABLE operation at the end
        - Parameterized queries with ? placeholders (safe from injection)
        - Proper progress tracking and logging
        
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
        transformed = filtered.project(f"""
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
            -- EMBEDDING TEXT GENERATION FOR WIKIPEDIA:
            -- UPDATE: Now uses long_summary from page_summaries table (not extract)
            -- Combine title and long_summary with pipe delimiter
            -- Long summary is AI-generated, providing 3-4x more content than old extract field
            -- Average ~985 chars vs ~250 chars for extract = superior embeddings
            CONCAT_WS(' | ', TRIM(title), TRIM(long_summary)) as embedding_text
        """)
        
        # First, create the transformed data without embeddings
        # This ensures we have all the data ready even if embedding fails
        transformed.create('transformed_wiki_temp')
        
        # Get total count for progress tracking
        total_count = conn.execute("SELECT COUNT(*) FROM transformed_wiki_temp").fetchone()[0]
        self.logger.info(f"Processing {total_count} Wikipedia articles for embeddings")
        
        # Create embedding table structure using DuckDB's native types
        # No primary key constraint to handle potential duplicates in batch processing
        conn.execute("""
            CREATE TABLE embedding_data (
                page_id BIGINT,
                embedding_text TEXT,
                embedding_vector DOUBLE[],
                embedding_generated_at TIMESTAMP
            )
        """)
        
        # Process embeddings in batches to prevent memory issues
        # Use configurable batch size from settings, default to 100 if not set
        BATCH_SIZE = getattr(self.settings.processing, 'embedding_batch_size', 100)
        processed = 0
        current_timestamp = datetime.now()
        
        # Use DuckDB's OFFSET/LIMIT for efficient batching
        while processed < total_count:
            # Extract batch of data for embedding generation
            batch_query = f"""
                SELECT page_id, embedding_text 
                FROM transformed_wiki_temp 
                ORDER BY page_id 
                LIMIT {BATCH_SIZE} 
                OFFSET {processed}
            """
            
            batch_rows = conn.execute(batch_query).fetchall()
            
            if not batch_rows:
                break  # No more data
            
            # Extract page IDs and texts for this batch
            batch_page_ids = [row[0] for row in batch_rows]
            batch_texts = [row[1] for row in batch_rows if row[1]]  # Filter out None texts
            
            # Log progress
            self.logger.info(f"Generating embeddings for batch {processed // BATCH_SIZE + 1} "
                           f"({processed + len(batch_rows)}/{total_count} articles)")
            
            # Generate embeddings for this batch
            if batch_texts:
                try:
                    embedding_response = self.embedding_provider.generate_embeddings(batch_texts)
                    
                    # Prepare batch data for insertion
                    insert_data = []
                    flat_params = []
                    text_idx = 0
                    
                    # Match embeddings back to page IDs (handling None texts)
                    for page_id, text in batch_rows:
                        if text:  # If we have text, use the embedding
                            embedding_vector = embedding_response.embeddings[text_idx]
                            text_idx += 1
                        else:  # No text, use NULL embedding
                            embedding_vector = None
                        
                        insert_data.append('(?, ?, ?, ?)')
                        flat_params.extend([page_id, text, embedding_vector, current_timestamp])
                    
                    # Use single INSERT with multiple VALUES for best performance
                    # This is more efficient than executemany according to DuckDB docs
                    if insert_data:
                        query = f"INSERT INTO embedding_data VALUES {', '.join(insert_data)}"
                        conn.execute(query, flat_params)
                    
                except Exception as e:
                    self.logger.error(f"Error generating embeddings for batch: {e}")
                    # Continue with next batch even if one fails
                    # This ensures partial success rather than complete failure
            
            processed += len(batch_rows)
        
        self.logger.info(f"Successfully generated embeddings for {processed} articles")
        
        # Now join the embeddings back to the transformed data
        # Using DuckDB's efficient join operations
        final_result = conn.execute(f"""
            CREATE TABLE {output_table} AS
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
                COALESCE(e.embedding_text, t.embedding_text) as embedding_text,
                e.embedding_vector,
                e.embedding_generated_at
            FROM transformed_wiki_temp t
            LEFT JOIN embedding_data e ON t.page_id = e.page_id
            ORDER BY t.page_id
        """)
        
        # Clean up temporary tables
        conn.execute("DROP TABLE IF EXISTS transformed_wiki_temp")
        conn.execute("DROP TABLE IF EXISTS embedding_data")
        
        # Verify the output
        output_count = conn.execute(f"SELECT COUNT(*) FROM {output_table}").fetchone()[0]
        embedding_count = conn.execute(f"SELECT COUNT(*) FROM {output_table} WHERE embedding_vector IS NOT NULL").fetchone()[0]
        
        self.logger.info(f"Transformed {output_count} Wikipedia articles from {input_table} to {output_table}")
        self.logger.info(f"Successfully embedded {embedding_count}/{output_count} articles ({embedding_count*100/output_count:.1f}%)")