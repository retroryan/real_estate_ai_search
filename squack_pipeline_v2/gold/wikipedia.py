"""Wikipedia Gold layer enrichment using DuckDB views."""

from squack_pipeline_v2.gold.base import GoldEnricher
from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import log_stage
from squack_pipeline_v2.utils.gold_enrichment import (
    GoldNeighborhoodEnricher,
    NeighborhoodSearchFacets,
    NeighborhoodQualityBoost
)


class WikipediaGoldEnricher(GoldEnricher):
    """Enricher for Wikipedia data into Gold layer using views.
    
    Gold layer principles (Medallion Architecture):
    - Business-ready article analytics
    - Content quality scoring and categorization
    - Relevance and authority metrics
    - Search optimization for knowledge discovery
    - Neighborhood-based enrichments and faceting
    """
    
    def _get_entity_type(self) -> str:
        """Return entity type."""
        return "wikipedia"
    
    @log_stage("Gold: Wikipedia View Creation")
    def _create_enriched_view(self, input_table: str, output_table: str) -> None:
        """Create Gold view with enrichments.
        
        Gold layer enrichments:
        - Article quality and authority scoring
        - Content categorization and topics
        - Geographic relevance analysis
        - Business-ready search optimization
        - Neighborhood association enrichments
        - Enhanced quality scoring with neighborhood presence
        
        Args:
            input_table: Silver Wikipedia table
            output_table: Gold Wikipedia view name
        """
        # Get connection
        conn = self.connection_manager.get_connection()
        
        # Initialize neighborhood enricher
        neighborhood_enricher = GoldNeighborhoodEnricher()
        
        # Use DuckDB Relation API for type-safe, lazy-evaluated operations
        silver_wikipedia = conn.table(input_table).set_alias("w")
        
        # Project enriched columns using Relation API
        enriched = silver_wikipedia.project(""" 
                -- Core identifiers (unchanged)
                page_id,
                title,
                url,
                
                -- Content fields with business enhancements
                long_summary,
                short_summary,
                
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
                    WHEN LENGTH(long_summary) >= 1000 AND links_count >= 10 THEN 'comprehensive'
                    WHEN LENGTH(long_summary) >= 500 AND links_count >= 5 THEN 'detailed'
                    WHEN LENGTH(long_summary) >= 200 THEN 'basic'
                    ELSE 'stub'
                END AS content_depth_category,
                
                -- GOLD ENRICHMENT: Business authority scoring
                CAST((
                    -- Content length factor (40%)
                    LEAST(LENGTH(long_summary) / 1000.0, 1.0) * 40 +
                    -- Link density factor (30%)
                    LEAST(COALESCE(links_count, 0) / 20.0, 1.0) * 30 +
                    -- Relevance factor (30%)
                    COALESCE(relevance_score, 0) * 30
                ) AS FLOAT) as authority_score,
                
                -- GOLD ENRICHMENT: Content categories for business use
                categories,
                
                -- GOLD ENRICHMENT: Extract key topics from categories (filtered for non-nulls)
                CASE 
                    WHEN categories IS NOT NULL AND LENGTH(categories) > 0
                    THEN list_filter(
                        ARRAY[
                            CASE WHEN categories LIKE '%geography%' OR categories LIKE '%location%' THEN 'geography' END,
                            CASE WHEN categories LIKE '%history%' OR categories LIKE '%historic%' THEN 'history' END,
                            CASE WHEN categories LIKE '%business%' OR categories LIKE '%company%' THEN 'business' END,
                            CASE WHEN categories LIKE '%culture%' OR categories LIKE '%art%' THEN 'culture' END,
                            CASE WHEN categories LIKE '%transport%' OR categories LIKE '%infrastructure%' THEN 'infrastructure' END
                        ],
                        x -> x IS NOT NULL
                    )
                    ELSE CAST([] AS VARCHAR[])
                END as key_topics,
                
                -- Quality and relevance scoring (enhanced)
                relevance_score,
                
                -- GOLD ENRICHMENT: Multi-factor article quality score with neighborhood boost
                CAST((
                    -- Base quality score
                    (
                        COALESCE(relevance_score, 0) * 0.4 +
                        CASE 
                            WHEN LENGTH(long_summary) >= 1000 THEN 0.6
                            WHEN LENGTH(long_summary) >= 500 THEN 0.4
                            WHEN LENGTH(long_summary) >= 200 THEN 0.2
                            ELSE 0.1
                        END * 0.3 +
                        CASE 
                            WHEN COALESCE(links_count, 0) >= 20 THEN 0.6
                            WHEN COALESCE(links_count, 0) >= 10 THEN 0.4
                            WHEN COALESCE(links_count, 0) >= 5 THEN 0.2
                            ELSE 0.1
                        END * 0.3
                    ) +
                    -- Neighborhood boost: +0.1 for having neighborhoods, +0.05 more for multiple
                    CASE 
                        WHEN neighborhood_names IS NOT NULL AND array_length(neighborhood_names) > 1 THEN 0.15
                        WHEN neighborhood_names IS NOT NULL AND array_length(neighborhood_names) >= 1 THEN 0.1
                        ELSE 0.0
                    END
                ) AS FLOAT) as article_quality_score,
                
                -- GOLD ENRICHMENT: Business quality categories
                CASE 
                    WHEN (COALESCE(relevance_score, 0) >= 0.8 AND LENGTH(long_summary) >= 500) THEN 'premium'
                    WHEN (COALESCE(relevance_score, 0) >= 0.6 AND LENGTH(long_summary) >= 200) THEN 'high'
                    WHEN (COALESCE(relevance_score, 0) >= 0.4) THEN 'medium'
                    ELSE 'basic'
                END as article_quality,
                
                -- GOLD ENRICHMENT: Geographic relevance scoring
                CASE 
                    WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1.0
                    WHEN latitude IS NOT NULL OR longitude IS NOT NULL THEN 0.5
                    ELSE 0.0
                END AS geographic_relevance_score,
                
                -- Location fields from Silver
                city,
                state,
                
                -- Metadata
                crawled_at as last_updated,
                
                -- Embedding text from Silver
                embedding_text,
                
                -- GOLD ENRICHMENT: Business search facets with neighborhood filters
                ARRAY[
                    article_quality,
                    content_depth_category,
                    CASE WHEN geographic_relevance_score >= 0.5 THEN 'geo_located' ELSE 'no_location' END,
                    CASE WHEN authority_score >= 70 THEN 'high_authority' ELSE 'standard_authority' END,
                    -- Neighborhood association facets
                    CASE 
                        WHEN neighborhood_names IS NOT NULL AND array_length(neighborhood_names) > 1 THEN 'multi_neighborhood'
                        WHEN neighborhood_names IS NOT NULL AND array_length(neighborhood_names) = 1 THEN 'has_neighborhood'
                        ELSE 'no_neighborhood'
                    END
                ] AS search_facets,
                
                -- GOLD ENRICHMENT: Business intelligence metadata
                CURRENT_TIMESTAMP as gold_processed_at,
                'wikipedia_gold_v4_neighborhood_enhanced' as processing_version,
                
                -- GOLD ENRICHMENT: Neighborhood metadata
                CASE 
                    WHEN neighborhood_names IS NOT NULL 
                        THEN array_length(neighborhood_names)
                    ELSE 0
                END as neighborhood_count,
                
                CASE 
                    WHEN neighborhood_names IS NOT NULL AND array_length(neighborhood_names) > 0
                        THEN true
                    ELSE false
                END as has_neighborhood_association,
                
                -- GOLD ENRICHMENT: Search ranking score with neighborhood component
                CAST((
                    article_quality_score * 0.45 +
                    geographic_relevance_score * 0.25 +
                    CASE WHEN LENGTH(title) BETWEEN 10 AND 100 THEN 0.15 ELSE 0.05 END +
                    -- Neighborhood presence component (15% weight)
                    CASE 
                        WHEN neighborhood_names IS NOT NULL AND array_length(neighborhood_names) > 0 THEN 0.15
                        ELSE 0.0
                    END
                ) AS FLOAT) as search_ranking_score,
                
                -- Embeddings from Silver
                embedding_vector,
                embedding_generated_at,
                
                -- Neighborhood fields from Silver layer
                neighborhood_ids,
                neighborhood_names,
                primary_neighborhood_name
                
        """)
        
        # Apply filters (use column names without alias after projection)
        filtered = enriched.filter("""
            page_id IS NOT NULL
            AND title IS NOT NULL
            AND LENGTH(title) > 0
        """)
        
        # Deduplicate by page_id - keep the record with the highest article_quality_score
        # This handles the duplicate page_ids in the source data
        conn.execute(f"""
            CREATE TABLE {output_table} AS
            WITH ranked AS (
                SELECT *, 
                    ROW_NUMBER() OVER (
                        PARTITION BY page_id 
                        ORDER BY article_quality_score DESC, embedding_generated_at DESC NULLS LAST
                    ) as rn
                FROM ({filtered.sql_query()}) as filtered_data
            )
            SELECT * EXCLUDE (rn)
            FROM ranked
            WHERE rn = 1
        """)
        
        # Track enrichments applied
        self.enrichments_applied.extend([
            "content_quality_analysis",
            "authority_scoring",
            "topic_extraction",
            "geographic_relevance",
            "business_categorization",
            "search_optimization",
            "ranking_algorithms",
            "neighborhood_enrichment",
            "neighborhood_quality_boost",
            "neighborhood_search_facets"
        ])
        
        self.logger.info(f"Created Gold view {output_table} with {len(self.enrichments_applied)} enrichments")