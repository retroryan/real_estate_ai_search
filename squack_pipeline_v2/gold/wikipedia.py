"""Wikipedia Gold layer enrichment - produces fields matching Elasticsearch template exactly."""

from squack_pipeline_v2.gold.base import GoldEnricher
from squack_pipeline_v2.core.logging import log_stage


class WikipediaGoldEnricher(GoldEnricher):
    """Enricher for Wikipedia data into Gold layer.
    
    Produces fields matching Elasticsearch template exactly:
    - Maps html_file → article_filename (for enrich-wikipedia command)
    - Sets content_loaded=false (for enrichment workflow)
    - Creates proper summaries from extract
    - Maps all fields to match ES template names
    """
    
    def _get_entity_type(self) -> str:
        """Return entity type."""
        return "wikipedia"
    
    def _apply_enrichments(self, input_table: str, output_table: str) -> None:
        """Apply Wikipedia enrichments to produce fields matching ES template exactly.
        
        Args:
            input_table: Silver Wikipedia table
            output_table: Gold Wikipedia table  
        """
        query = f"""
        CREATE TABLE {output_table} AS
        SELECT 
            -- Core identifiers (ES template fields)
            page_id,
            title,
            url,
            
            -- CRITICAL: Map html_file to article_filename (for enrich-wikipedia workflow)
            html_file as article_filename,
            
            -- Content fields matching ES template names exactly
            extract as long_summary,
            CASE 
                WHEN LENGTH(extract) > 500 
                THEN SUBSTRING(extract, 1, 500) || '...'
                ELSE extract
            END as short_summary,
            extract as full_content,  -- Initially same as extract, enriched later
            LENGTH(extract) as content_length,
            
            -- CRITICAL: Set content_loaded=false (for enrich-wikipedia to find documents needing enrichment)
            false as content_loaded,
            crawled_at as content_loaded_at,
            
            -- Location as geo_point array [lon, lat] for ES
            CASE 
                WHEN longitude IS NOT NULL AND latitude IS NOT NULL
                THEN LIST_VALUE(longitude, latitude)
                ELSE NULL
            END as location,
            
            -- Categories and topics
            categories,
            CAST(NULL AS VARCHAR[]) as key_topics,
            
            -- Quality and relevance scoring
            relevance_score,
            relevance_score as article_quality_score,
            CASE 
                WHEN relevance_score >= 0.8 THEN 'high'
                WHEN relevance_score >= 0.5 THEN 'medium' 
                ELSE 'low'
            END as article_quality,
            
            -- Location context (set null, can be enriched later)
            CAST(NULL AS VARCHAR) as best_city,
            CAST(NULL AS VARCHAR) as best_state,
            
            -- Metadata
            crawled_at as last_updated,
            
            -- Create embedding text combining key searchable fields
            COALESCE(title, '') || ' | ' ||
            COALESCE(extract, '') as embedding_text
            
        FROM {input_table}
        WHERE page_id IS NOT NULL
        AND title IS NOT NULL
        """
        
        self.connection_manager.execute(query)
        self.enrichments_applied.append("field_mapping_to_es_template")
        self.enrichments_applied.append("article_filename_mapping")
        self.enrichments_applied.append("content_loaded_false")
        self.enrichments_applied.append("location_geo_point")
        self.enrichments_applied.append("content_summaries")