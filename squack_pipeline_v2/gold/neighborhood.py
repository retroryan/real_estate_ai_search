"""Neighborhood Gold layer enrichment using DuckDB Relation API."""

from squack_pipeline_v2.gold.base import GoldEnricher
from squack_pipeline_v2.core.logging import log_stage


class NeighborhoodGoldEnricher(GoldEnricher):
    """Enricher for neighborhood data into Gold layer using Relation API.
    
    Gold layer principles (Medallion Architecture):
    - Business-ready aggregated demographics
    - Investment attractiveness scoring
    - Livability and lifestyle metrics
    - Market positioning and trends
    """
    
    def _get_entity_type(self) -> str:
        """Return entity type."""
        return "neighborhood"
    
    @log_stage("Gold: Neighborhood Enrichment")
    def _apply_enrichments(self, input_table: str, output_table: str) -> None:
        """Apply Gold enrichments using DuckDB Relation API.
        
        Gold layer enrichments:
        - Investment attractiveness scores
        - Livability rankings and categories
        - Demographic analysis and segments
        - Market positioning for businesses
        
        Args:
            input_table: Silver neighborhoods table
            output_table: Gold neighborhoods table
        """
        # Get connection for Relation API
        conn = self.connection_manager.get_connection()
        
        # Apply Gold enrichments using SQL within relation
        gold_relation = conn.sql(f"""
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
                COALESCE(population, 0) as population,
                CAST(COALESCE(median_income, 0) AS FLOAT) as median_income,
                
                -- GOLD ENRICHMENT: Derived economic metrics
                CAST(COALESCE(median_income, 0) * 4 AS FLOAT) as estimated_median_home_price,
                
                -- GOLD ENRICHMENT: Income categories for business analysis
                CASE 
                    WHEN median_income >= 120000 THEN 'high_income'
                    WHEN median_income >= 80000 THEN 'upper_middle'
                    WHEN median_income >= 50000 THEN 'middle_income'
                    WHEN median_income >= 30000 THEN 'working_class'
                    ELSE 'low_income'
                END AS income_category,
                
                -- GOLD ENRICHMENT: Population density categories
                CASE 
                    WHEN population >= 50000 THEN 'high_density'
                    WHEN population >= 20000 THEN 'medium_density'
                    WHEN population >= 5000 THEN 'low_density'
                    ELSE 'rural'
                END AS density_category,
                
                -- Quality of life scores (from Silver)
                COALESCE(walkability_score, 0.0) as walkability_score,
                COALESCE(school_rating, 0.0) as school_score,
                
                -- GOLD ENRICHMENT: Composite livability score
                CAST((
                    COALESCE(walkability_score, 0.0) * 0.3 +
                    COALESCE(school_rating, 0.0) * 10 * 0.4 +
                    CASE WHEN median_income > 60000 THEN 50 ELSE median_income / 60000 * 50 END * 0.3
                ) AS FLOAT) as overall_livability_score,
                
                -- GOLD ENRICHMENT: Lifestyle categories for marketing
                CASE 
                    WHEN walkability_score >= 70 AND school_rating >= 8 THEN 'family_friendly_urban'
                    WHEN walkability_score >= 70 THEN 'urban_lifestyle'
                    WHEN school_rating >= 8 THEN 'family_oriented'
                    WHEN median_income >= 100000 THEN 'affluent_suburban'
                    ELSE 'affordable_community'
                END AS lifestyle_category,
                
                -- GOLD ENRICHMENT: Investment attractiveness score
                CAST((
                    -- Income factor (30%)
                    LEAST(median_income / 100000, 1.0) * 30 +
                    -- Population growth proxy (20%)  
                    CASE WHEN population > 10000 THEN 20 ELSE population / 10000 * 20 END +
                    -- Quality of life (30%)
                    (COALESCE(walkability_score, 0) / 100 * 15 + COALESCE(school_rating, 0) / 10 * 15) +
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
                COALESCE(description, '') as description,
                COALESCE(amenities, LIST_VALUE()) as amenities,
                
                -- GOLD ENRICHMENT: Business-ready embedding text
                COALESCE(CAST(name AS VARCHAR), '') || ' | ' ||
                COALESCE(CAST(city AS VARCHAR), '') || ' | ' ||
                COALESCE(CAST(description AS VARCHAR), '') || ' | ' ||
                COALESCE(CAST(amenities AS VARCHAR), '') || ' | ' ||
                COALESCE(CAST(income_category AS VARCHAR), '') || ' | ' ||
                COALESCE(CAST(lifestyle_category AS VARCHAR), '') as embedding_text,
                
                -- GOLD ENRICHMENT: Business facets for search and filtering
                ARRAY[
                    income_category, 
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
                         AND median_income > 0
                    THEN 1.0
                    WHEN median_income > 0 AND description IS NOT NULL
                    THEN 0.7
                    ELSE 0.3
                END AS data_completeness_score,
                
                -- GOLD ENRICHMENT: Embedding infrastructure (medallion architecture)
                CAST(NULL AS DOUBLE[1024]) AS embedding_vector,
                CAST(NULL AS TIMESTAMP) AS embedding_generated_at
                
            FROM {input_table}
            WHERE neighborhood_id IS NOT NULL
            AND name IS NOT NULL
        """)
        
        # Create the Gold table
        gold_relation.create(output_table)
        
        # Track enrichments applied
        self.enrichments_applied.extend([
            "economic_analysis",
            "demographic_segmentation",
            "livability_scoring",
            "investment_attractiveness",
            "lifestyle_categorization",
            "business_embedding_text",
            "market_facets",
            "data_quality_scoring"
        ])
        
        self.logger.info(f"Applied {len(self.enrichments_applied)} Gold enrichments to {output_table}")