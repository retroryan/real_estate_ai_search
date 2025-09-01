"""Wikipedia Gold layer enrichment using DuckDB Relation API."""

from squack_pipeline_v2.gold.base import GoldEnricher
from squack_pipeline_v2.core.logging import log_stage


class WikipediaGoldEnricher(GoldEnricher):
    """Enricher for Wikipedia data into Gold layer using Relation API.
    
    Gold layer principles (Medallion Architecture):
    - Business-ready article analytics
    - Content quality scoring and categorization
    - Relevance and authority metrics
    - Search optimization for knowledge discovery
    """
    
    def _get_entity_type(self) -> str:
        """Return entity type."""
        return "wikipedia"
    
    @log_stage("Gold: Wikipedia Enrichment")
    def _apply_enrichments(self, input_table: str, output_table: str) -> None:
        """Apply Gold enrichments using DuckDB Relation API.
        
        Gold layer enrichments:
        - Article quality and authority scoring
        - Content categorization and topics
        - Geographic relevance analysis
        - Business-ready search optimization
        
        Args:
            input_table: Silver Wikipedia table
            output_table: Gold Wikipedia table
        """
        # Get connection for Relation API
        conn = self.connection_manager.get_connection()
        
        # Apply Gold enrichments using SQL within relation
        gold_relation = conn.sql(f"""
            SELECT 
                -- Core identifiers (unchanged)
                page_id,
                title,
                url,
                
                -- Content fields with business enhancements
                extract as long_summary,
                
                -- GOLD ENRICHMENT: Dynamic summaries based on content length
                CASE 
                    WHEN LENGTH(extract) > 500 
                    THEN SUBSTRING(extract, 1, 500) || '...'
                    WHEN LENGTH(extract) > 200
                    THEN SUBSTRING(extract, 1, 200) || '...'
                    ELSE extract
                END as short_summary,
                
                extract as full_content,
                LENGTH(extract) as content_length,
                
                -- Business workflow fields
                false as content_loaded,
                crawled_at as content_loaded_at,
                html_file as article_filename,
                
                -- Location as geo_point for business mapping
                CASE 
                    WHEN longitude IS NOT NULL AND latitude IS NOT NULL
                    THEN LIST_VALUE(longitude, latitude)
                    ELSE NULL
                END as location,
                
                -- GOLD ENRICHMENT: Content quality analysis
                CASE 
                    WHEN LENGTH(extract) >= 1000 AND links_count >= 10 THEN 'comprehensive'
                    WHEN LENGTH(extract) >= 500 AND links_count >= 5 THEN 'detailed'
                    WHEN LENGTH(extract) >= 200 THEN 'basic'
                    ELSE 'stub'
                END AS content_depth_category,
                
                -- GOLD ENRICHMENT: Business authority scoring
                CAST((
                    -- Content length factor (40%)
                    LEAST(LENGTH(extract) / 1000.0, 1.0) * 40 +
                    -- Link density factor (30%)
                    LEAST(COALESCE(links_count, 0) / 20.0, 1.0) * 30 +
                    -- Relevance factor (30%)
                    COALESCE(relevance_score, 0) * 30
                ) AS FLOAT) as authority_score,
                
                -- GOLD ENRICHMENT: Content categories for business use
                categories,
                
                -- GOLD ENRICHMENT: Extract key topics from categories
                CASE 
                    WHEN categories IS NOT NULL AND LENGTH(categories) > 0
                    THEN ARRAY[
                        CASE WHEN categories LIKE '%geography%' OR categories LIKE '%location%' THEN 'geography' END,
                        CASE WHEN categories LIKE '%history%' OR categories LIKE '%historic%' THEN 'history' END,
                        CASE WHEN categories LIKE '%business%' OR categories LIKE '%company%' THEN 'business' END,
                        CASE WHEN categories LIKE '%culture%' OR categories LIKE '%art%' THEN 'culture' END,
                        CASE WHEN categories LIKE '%transport%' OR categories LIKE '%infrastructure%' THEN 'infrastructure' END
                    ]
                    ELSE CAST(NULL AS VARCHAR[])
                END as key_topics,
                
                -- Quality and relevance scoring (enhanced)
                COALESCE(relevance_score, 0.0) as relevance_score,
                
                -- GOLD ENRICHMENT: Multi-factor article quality score
                CAST((
                    COALESCE(relevance_score, 0) * 0.4 +
                    CASE 
                        WHEN LENGTH(extract) >= 1000 THEN 0.6
                        WHEN LENGTH(extract) >= 500 THEN 0.4
                        WHEN LENGTH(extract) >= 200 THEN 0.2
                        ELSE 0.1
                    END * 0.3 +
                    CASE 
                        WHEN COALESCE(links_count, 0) >= 20 THEN 0.6
                        WHEN COALESCE(links_count, 0) >= 10 THEN 0.4
                        WHEN COALESCE(links_count, 0) >= 5 THEN 0.2
                        ELSE 0.1
                    END * 0.3
                ) AS FLOAT) as article_quality_score,
                
                -- GOLD ENRICHMENT: Business quality categories
                CASE 
                    WHEN (COALESCE(relevance_score, 0) >= 0.8 AND LENGTH(extract) >= 500) THEN 'premium'
                    WHEN (COALESCE(relevance_score, 0) >= 0.6 AND LENGTH(extract) >= 200) THEN 'high'
                    WHEN (COALESCE(relevance_score, 0) >= 0.4) THEN 'medium'
                    ELSE 'basic'
                END as article_quality,
                
                -- GOLD ENRICHMENT: Geographic relevance scoring
                CASE 
                    WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1.0
                    WHEN latitude IS NOT NULL OR longitude IS NOT NULL THEN 0.5
                    ELSE 0.0
                END AS geographic_relevance_score,
                
                -- Metadata
                crawled_at as last_updated,
                
                -- GOLD ENRICHMENT: Business-ready embedding text
                COALESCE(title, '') || ' | ' ||
                COALESCE(extract, '') || ' | ' ||
                COALESCE(CAST(key_topics AS VARCHAR), '') as embedding_text,
                
                -- GOLD ENRICHMENT: Business search facets
                ARRAY[
                    article_quality,
                    content_depth_category,
                    CASE WHEN geographic_relevance_score >= 0.5 THEN 'geo_located' ELSE 'no_location' END,
                    CASE WHEN authority_score >= 70 THEN 'high_authority' ELSE 'standard_authority' END
                ] AS search_facets,
                
                -- GOLD ENRICHMENT: Business intelligence metadata
                CURRENT_TIMESTAMP as gold_processed_at,
                'wikipedia_gold_v3_business_ready' as processing_version,
                
                -- GOLD ENRICHMENT: Search ranking score
                CAST((
                    article_quality_score * 0.5 +
                    geographic_relevance_score * 0.3 +
                    CASE WHEN LENGTH(title) BETWEEN 10 AND 100 THEN 0.2 ELSE 0.1 END
                ) AS FLOAT) as search_ranking_score,
                
                -- GOLD ENRICHMENT: Embedding infrastructure (medallion architecture)
                CAST(NULL AS DOUBLE[1024]) AS embedding_vector,
                CAST(NULL AS TIMESTAMP) AS embedding_generated_at
                
            FROM {input_table}
            WHERE page_id IS NOT NULL
            AND title IS NOT NULL
            AND LENGTH(title) > 0
        """)
        
        # Create the Gold table
        gold_relation.create(output_table)
        
        # Track enrichments applied
        self.enrichments_applied.extend([
            "content_quality_analysis",
            "authority_scoring",
            "topic_extraction",
            "geographic_relevance",
            "business_categorization",
            "search_optimization",
            "ranking_algorithms",
            "business_embedding_text"
        ])
        
        self.logger.info(f"Applied {len(self.enrichments_applied)} Gold enrichments to {output_table}")