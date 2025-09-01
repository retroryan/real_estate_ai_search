"""Neighborhood Gold layer enrichment using DuckDB views."""

from squack_pipeline_v2.gold.base import GoldEnricher
from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import log_stage


class NeighborhoodGoldEnricher(GoldEnricher):
    """Enricher for neighborhood data into Gold layer using views.
    
    Gold layer principles (Medallion Architecture):
    - Business-ready aggregated demographics
    - Investment attractiveness scoring
    - Livability and lifestyle metrics
    - Market positioning and trends
    """
    
    def _get_entity_type(self) -> str:
        """Return entity type."""
        return "neighborhood"
    
    @log_stage("Gold: Neighborhood View Creation")
    def _create_enriched_view(self, input_table: str, output_table: str) -> None:
        """Create Gold view with enrichments.
        
        Gold layer enrichments:
        - Investment attractiveness scores
        - Livability rankings and categories
        - Demographic analysis and segments
        - Market positioning for businesses
        
        Args:
            input_table: Silver neighborhoods table
            output_table: Gold neighborhoods view name
        """
        # Get connection
        conn = self.connection_manager.get_connection()
        
        # Create Gold view with business-ready enrichments
        safe_input = DuckDBConnectionManager.safe_identifier(input_table)
        safe_output = DuckDBConnectionManager.safe_identifier(output_table)
        
        query = f"""
        CREATE OR REPLACE VIEW {safe_output} AS
            SELECT 
                -- Core identifiers (unchanged)
                neighborhood_id,
                name,
                city,
                state,
                
                -- Location as geo_point (from Silver)
                location,
                
                -- GOLD ENRICHMENT: Extract coordinates for business use
                CASE 
                    WHEN location IS NOT NULL AND array_length(location) >= 2
                    THEN location[2]  -- latitude
                    ELSE 0.0
                END as center_latitude,
                
                CASE 
                    WHEN location IS NOT NULL AND array_length(location) >= 1
                    THEN location[1]  -- longitude
                    ELSE 0.0
                END as center_longitude,
                
                -- Basic metrics (from Silver)
                population,
                
                -- GOLD ENRICHMENT: Population density categories
                CASE 
                    WHEN population >= 50000 THEN 'high_density'
                    WHEN population >= 20000 THEN 'medium_density'
                    WHEN population >= 5000 THEN 'low_density'
                    ELSE 'rural'
                END AS density_category,
                
                -- Quality of life scores (from Silver)
                walkability_score,
                school_rating,
                
                -- GOLD ENRICHMENT: Composite livability score
                CAST((
                    COALESCE(walkability_score, 0.0) * 0.5 +
                    COALESCE(school_rating, 0.0) * 10 * 0.5
                ) AS FLOAT) as overall_livability_score,
                
                -- GOLD ENRICHMENT: Lifestyle categories for marketing
                CASE 
                    WHEN walkability_score >= 70 AND school_rating >= 8 THEN 'family_friendly_urban'
                    WHEN walkability_score >= 70 THEN 'urban_lifestyle'
                    WHEN school_rating >= 8 THEN 'family_oriented'
                    ELSE 'standard_community'
                END AS lifestyle_category,
                
                -- GOLD ENRICHMENT: Investment attractiveness score
                CAST((
                    -- Population factor (30%)  
                    CASE WHEN population > 10000 THEN 30 ELSE population / 10000 * 30 END +
                    -- Quality of life (50%)
                    (COALESCE(walkability_score, 0) / 100 * 25 + COALESCE(school_rating, 0) / 10 * 25) +
                    -- Location desirability (20%)
                    CASE 
                        WHEN UPPER(city) IN ('SAN FRANCISCO', 'OAKLAND', 'BERKELEY') THEN 20
                        WHEN UPPER(city) IN ('PALO ALTO', 'MOUNTAIN VIEW', 'SUNNYVALE') THEN 18
                        ELSE 10
                    END
                ) AS FLOAT) as investment_attractiveness_score,
                
                -- Nested objects (preserved from Silver)
                demographics,
                wikipedia_correlations,
                
                -- Text and arrays
                description,
                amenities,
                lifestyle_tags,
                
                -- Embedding text from Silver
                embedding_text,
                
                -- GOLD ENRICHMENT: Business facets for search and filtering
                ARRAY[
                    density_category, 
                    lifestyle_category,
                    CASE WHEN investment_attractiveness_score >= 70 THEN 'high_investment' ELSE 'moderate_investment' END
                ] AS business_facets,
                
                -- GOLD ENRICHMENT: Market analysis metadata
                CURRENT_TIMESTAMP as gold_processed_at,
                'neighborhood_gold_v3_business_ready' as processing_version,
                
                -- GOLD ENRICHMENT: Data completeness score for ranking
                CASE 
                    WHEN demographics IS NOT NULL 
                         AND description IS NOT NULL 
                         AND LENGTH(description) > 20
                         AND amenities IS NOT NULL 
                    THEN 1.0
                    WHEN description IS NOT NULL
                    THEN 0.7
                    ELSE 0.3
                END AS data_completeness_score,
                
                -- Embeddings from Silver
                embedding_vector,
                embedding_generated_at
                
            FROM {safe_input}
            WHERE neighborhood_id IS NOT NULL
            AND name IS NOT NULL
        """
        
        # Execute the CREATE VIEW statement
        conn.execute(query)
        
        # Track enrichments applied
        self.enrichments_applied.extend([
            "economic_analysis",
            "demographic_segmentation",
            "livability_scoring",
            "investment_attractiveness",
            "lifestyle_categorization",
            "market_facets",
            "data_quality_scoring"
        ])
        
        self.logger.info(f"Created Gold view {output_table} with {len(self.enrichments_applied)} enrichments")