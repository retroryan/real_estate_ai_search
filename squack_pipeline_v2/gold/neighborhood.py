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
        
        # Use DuckDB Relation API for type-safe, lazy-evaluated operations
        silver_neighborhoods = conn.table(input_table).set_alias("n")
        
        # Project enriched columns using Relation API
        enriched = silver_neighborhoods.project("""
            -- Core identifiers
            n.neighborhood_id,
            n.name,
            n.city,
            n.state,
            
            -- Geographic hierarchy
            n.county,
            n.city_id as location_city_id,
            n.county_id as location_county_id,
            n.state_id as location_state_id,
            
            -- Location as geo_point
            n.location,
            
            -- Extract coordinates for business use
            CASE 
                WHEN n.location IS NOT NULL AND array_length(n.location) >= 2
                THEN n.location[2]  -- latitude
                ELSE 0.0
            END as center_latitude,
            
            CASE 
                WHEN n.location IS NOT NULL AND array_length(n.location) >= 1
                THEN n.location[1]  -- longitude
                ELSE 0.0
            END as center_longitude,
            
            -- Basic metrics
            n.population,
            
            -- Population density categories
            CASE 
                WHEN n.population >= 50000 THEN 'high_density'
                WHEN n.population >= 20000 THEN 'medium_density'
                WHEN n.population >= 5000 THEN 'low_density'
                ELSE 'rural'
            END AS density_category,
            
            -- Quality of life scores
            n.walkability_score,
            n.school_rating,
            
            -- Composite livability score with explicit type casting
            CAST((
                COALESCE(CAST(n.walkability_score AS FLOAT), 0.0) * 0.5 +
                COALESCE(CAST(n.school_rating AS FLOAT), 0.0) * 10 * 0.5
            ) AS FLOAT) as overall_livability_score,
            
            -- Lifestyle categories for marketing
            CASE 
                WHEN n.walkability_score >= 70 AND n.school_rating >= 8 THEN 'family_friendly_urban'
                WHEN n.walkability_score >= 70 THEN 'urban_lifestyle'
                WHEN n.school_rating >= 8 THEN 'family_oriented'
                ELSE 'standard_community'
            END AS lifestyle_category,
            
            -- Investment attractiveness score
            CAST((
                -- Population factor (30%)
                CASE WHEN n.population > 10000 THEN 30.0 ELSE CAST(n.population AS FLOAT) / 10000.0 * 30.0 END +
                -- Quality of life (50%)
                (COALESCE(CAST(n.walkability_score AS FLOAT), 0.0) / 100.0 * 25.0 + 
                 COALESCE(CAST(n.school_rating AS FLOAT), 0.0) / 10.0 * 25.0) +
                -- Location desirability (20%)
                CASE 
                    WHEN UPPER(n.city) IN ('SAN FRANCISCO', 'OAKLAND', 'BERKELEY') THEN 20.0
                    WHEN UPPER(n.city) IN ('PALO ALTO', 'MOUNTAIN VIEW', 'SUNNYVALE') THEN 18.0
                    ELSE 10.0
                END
            ) AS FLOAT) as investment_attractiveness_score,
            
            -- Nested objects and extracted fields
            n.demographics,
            n.wikipedia_page_id,
            n.wikipedia_correlations,
            
            -- Text and arrays
            n.description,
            n.amenities,
            n.lifestyle_tags,
            
            -- Historical data (simple annual records)
            n.historical_data,
            
            -- Embedding text
            n.embedding_text,
            
            -- Business facets for search and filtering
            ARRAY[
                density_category, 
                lifestyle_category,
                CASE WHEN investment_attractiveness_score >= 70 THEN 'high_investment' ELSE 'moderate_investment' END
            ] AS business_facets,
            
            -- Market analysis metadata
            CURRENT_TIMESTAMP as gold_processed_at,
            'neighborhood_gold_v3_business_ready' as processing_version,
            
            -- Data completeness score for ranking
            CASE 
                WHEN n.demographics IS NOT NULL 
                     AND n.description IS NOT NULL 
                     AND LENGTH(n.description) > 20
                     AND n.amenities IS NOT NULL 
                THEN 1.0
                WHEN n.description IS NOT NULL
                THEN 0.7
                ELSE 0.3
            END AS data_completeness_score,
            
            -- Embeddings
            n.embedding_vector,
            n.embedding_generated_at
        """)
        
        # Apply filters (use column names without alias after projection)
        filtered = enriched.filter("""
            neighborhood_id IS NOT NULL
            AND name IS NOT NULL
        """)
        
        # Create view using Relation API
        filtered.create_view(output_table)
        
        # Track enrichments applied
        self.enrichments_applied.extend([
            "economic_analysis",
            "demographic_segmentation",
            "livability_scoring",
            "investment_attractiveness", 
            "lifestyle_categorization",
            "market_facets",
            "data_quality_scoring",
            "geographic_hierarchy_from_silver"
        ])
        
        self.logger.info(f"Created Gold view {output_table} with {len(self.enrichments_applied)} enrichments")