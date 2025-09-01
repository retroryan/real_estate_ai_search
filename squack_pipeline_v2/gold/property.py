"""Property Gold layer enrichment using DuckDB Relation API."""

from squack_pipeline_v2.gold.base import GoldEnricher
from squack_pipeline_v2.core.logging import log_stage


class PropertyGoldEnricher(GoldEnricher):
    """Enricher for property data into Gold layer using Relation API.
    
    Gold layer principles (Medallion Architecture):
    - Business-ready data with computed metrics
    - Aggregated features for analytics
    - Enriched with derived insights
    - Ready for downstream consumption (Elasticsearch, ML models)
    """
    
    def _get_entity_type(self) -> str:
        """Return entity type."""
        return "property"
    
    @log_stage("Gold: Property Enrichment")
    def _apply_enrichments(self, input_table: str, output_table: str) -> None:
        """Apply Gold enrichments using DuckDB Relation API.
        
        Gold layer enrichments:
        - Business metrics (price per bedroom, value ratings)
        - Market positioning (luxury/affordable categories)
        - Investment insights (cap rates, appreciation potential)  
        - Search optimization (embedding text, facets)
        
        Args:
            input_table: Silver properties table
            output_table: Gold properties table
        """
        # Get connection for Relation API
        conn = self.connection_manager.get_connection()
        
        # Apply Gold enrichments using SQL within relation
        gold_relation = conn.sql(f"""
            SELECT 
                -- Core identifiers (unchanged)
                listing_id,
                neighborhood_id,
                
                -- Basic property details (from Silver)
                bedrooms,
                bathrooms,
                square_feet,
                property_type,
                year_built,
                lot_size,
                
                -- Price fields with business calculations
                CAST(price AS FLOAT) AS price,
                CAST(price_per_sqft AS FLOAT) AS price_per_sqft,
                
                -- GOLD ENRICHMENT: Price metrics and ratios
                CASE 
                    WHEN bedrooms > 0 
                    THEN CAST(price / bedrooms AS FLOAT)
                    ELSE CAST(price AS FLOAT)
                END AS price_per_bedroom,
                
                CASE 
                    WHEN bathrooms > 0 
                    THEN CAST(price / bathrooms AS FLOAT)
                    ELSE CAST(price AS FLOAT)
                END AS price_per_bathroom,
                
                -- GOLD ENRICHMENT: Market positioning categories
                CASE 
                    WHEN price < 300000 THEN 'affordable'
                    WHEN price < 800000 THEN 'mid_market'
                    WHEN price < 2000000 THEN 'upscale'
                    ELSE 'luxury'
                END AS market_segment,
                
                -- GOLD ENRICHMENT: Property age categories
                CASE 
                    WHEN year_built >= 2020 THEN 'new_construction'
                    WHEN year_built >= 2010 THEN 'recent'
                    WHEN year_built >= 1990 THEN 'modern'
                    WHEN year_built >= 1950 THEN 'established'
                    ELSE 'historic'
                END AS age_category,
                
                -- GOLD ENRICHMENT: Size categories
                CASE 
                    WHEN square_feet < 800 THEN 'compact'
                    WHEN square_feet < 1500 THEN 'medium'
                    WHEN square_feet < 2500 THEN 'large'
                    ELSE 'spacious'
                END AS size_category,
                
                -- GOLD ENRICHMENT: Investment metrics
                CASE 
                    WHEN price_per_sqft > 0 AND square_feet > 0
                    THEN CAST((price_per_sqft - 500) / 500 * 100 AS FLOAT)
                    ELSE 0.0
                END AS price_premium_pct,
                
                -- Address and location (from Silver)
                address,
                
                -- GOLD ENRICHMENT: Structured parking object
                struct_pack(
                    spaces := COALESCE(garage_spaces, 0),
                    type := CASE 
                        WHEN garage_spaces > 2 THEN 'multi_car_garage'
                        WHEN garage_spaces > 0 THEN 'single_garage' 
                        ELSE 'street_parking' 
                    END
                ) as parking,
                
                -- Text and media
                description,
                COALESCE(features, LIST_VALUE()) AS features,
                virtual_tour_url,
                images,
                
                -- Dates and metadata
                listing_date,
                days_on_market,
                
                -- GOLD ENRICHMENT: Market urgency indicators
                CASE 
                    WHEN days_on_market <= 7 THEN 'hot'
                    WHEN days_on_market <= 30 THEN 'active'
                    WHEN days_on_market <= 90 THEN 'stale'
                    ELSE 'cold'
                END AS market_status,
                
                -- Complex nested data (preserved for advanced analytics)
                price_history,
                market_trends,
                buyer_persona,
                viewing_statistics,
                buyer_demographics,
                nearby_amenities,
                future_enhancements,
                
                -- GOLD ENRICHMENT: Business-ready embedding text
                COALESCE(CAST(description AS VARCHAR), '') || ' | ' ||
                COALESCE(CAST(property_type AS VARCHAR), '') || ' | ' ||
                COALESCE(CAST(features AS VARCHAR), '') || ' | ' ||
                COALESCE(CAST(bedrooms AS VARCHAR), '') || ' bedrooms | ' ||
                COALESCE(CAST(bathrooms AS VARCHAR), '') || ' bathrooms | ' ||
                COALESCE(CAST(square_feet AS VARCHAR), '') || ' sqft' as embedding_text,
                
                -- GOLD ENRICHMENT: Search facets for business use
                ARRAY[property_type, market_segment, age_category, size_category] AS search_facets,
                
                -- GOLD ENRICHMENT: Business metadata
                CURRENT_TIMESTAMP as gold_processed_at,
                'property_gold_v3_business_ready' as processing_version,
                
                -- GOLD ENRICHMENT: Quality score for ranking
                CASE 
                    WHEN description IS NOT NULL AND LENGTH(description) > 50 AND images IS NOT NULL
                    THEN 1.0
                    WHEN description IS NOT NULL AND LENGTH(description) > 20
                    THEN 0.7
                    ELSE 0.3
                END AS listing_quality_score,
                
                -- GOLD ENRICHMENT: Embedding infrastructure (medallion architecture)
                CAST(NULL AS DOUBLE[1024]) AS embedding_vector,
                CAST(NULL AS TIMESTAMP) AS embedding_generated_at
                
            FROM {input_table}
            WHERE listing_id IS NOT NULL
            AND price > 0
            AND square_feet > 0
        """)
        
        # Create the Gold table
        gold_relation.create(output_table)
        
        # Track enrichments applied
        self.enrichments_applied.extend([
            "price_metrics",
            "market_positioning", 
            "investment_analysis",
            "property_categorization",
            "business_embedding_text",
            "search_facets",
            "quality_scoring"
        ])
        
        self.logger.info(f"Applied {len(self.enrichments_applied)} Gold enrichments to {output_table}")