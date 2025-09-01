"""Property Gold layer enrichment using DuckDB views."""

from squack_pipeline_v2.gold.base import GoldEnricher
from squack_pipeline_v2.core.connection import DuckDBConnectionManager
from squack_pipeline_v2.core.logging import log_stage


class PropertyGoldEnricher(GoldEnricher):
    """Enricher for property data into Gold layer using views.
    
    Gold layer principles (Medallion Architecture):
    - Business-ready data with computed metrics
    - Aggregated features for analytics
    - Enriched with derived insights
    - Ready for downstream consumption (Elasticsearch, ML models)
    """
    
    def _get_entity_type(self) -> str:
        """Return entity type."""
        return "property"
    
    @log_stage("Gold: Property View Creation")
    def _create_enriched_view(self, input_table: str, output_table: str) -> None:
        """Create Gold view with enrichments.
        
        Gold layer enrichments:
        - Business metrics (price per bedroom, value ratings)
        - Market positioning (luxury/affordable categories)
        - Investment insights (cap rates, appreciation potential)  
        - Search optimization (embedding text, facets)
        
        Args:
            input_table: Silver properties table
            output_table: Gold properties view name
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
                s.listing_id,
                s.neighborhood_id,
                
                -- Basic property details (from Silver)
                s.bedrooms,
                s.bathrooms,
                s.square_feet,
                s.property_type,
                s.year_built,
                s.lot_size,
                
                -- Price fields (keep price_per_sqft as it's used in ES queries)
                CAST(s.price AS FLOAT) AS price,
                CAST(s.price_per_sqft AS FLOAT) AS price_per_sqft,
                
                -- Address and location (from Silver)
                s.address,
                
                -- GOLD ENRICHMENT: Structured parking object
                struct_pack(
                    spaces := COALESCE(s.garage_spaces, 0),
                    type := CASE 
                        WHEN s.garage_spaces > 2 THEN 'multi_car_garage'
                        WHEN s.garage_spaces > 0 THEN 'single_garage' 
                        ELSE 'street_parking' 
                    END
                ) as parking,
                
                -- Text and media
                s.description,
                
                -- GOLD ENRICHMENT: Enriched description combining property and neighborhood Wikipedia context
                s.description || 
                COALESCE(
                    ' Located in ' || n.name || '. ' || 
                    (SELECT w.extract 
                     FROM silver_wikipedia w
                     WHERE w.page_id = TRY_CAST(n.wikipedia_correlations['primary_wiki_article']['page_id'] AS BIGINT)
                     LIMIT 1),
                    ''
                ) AS enriched_description,
                
                s.features,
                s.virtual_tour_url,
                s.images,
                
                -- Dates and metadata
                s.listing_date,
                s.days_on_market,
                
                -- Status field (required by ES queries) - all properties are active
                'active' AS status,
                
                -- Amenities field (required by ES queries) - use features as amenities
                s.features AS amenities,
                
                -- Search tags (required by ES queries) - generate from property attributes
                LIST_VALUE(
                    s.property_type,
                    CASE WHEN s.bedrooms = 1 THEN 'studio' 
                         WHEN s.bedrooms = 2 THEN 'two-bedroom'
                         WHEN s.bedrooms = 3 THEN 'three-bedroom'
                         WHEN s.bedrooms >= 4 THEN 'family-home'
                         ELSE 'property' END,
                    CASE WHEN s.price < 500000 THEN 'affordable'
                         WHEN s.price < 1000000 THEN 'mid-range'
                         ELSE 'luxury' END
                ) AS search_tags,
                
                -- Embedding text and vectors from Silver
                s.embedding_text,
                
                -- GOLD ENRICHMENT: Business metadata
                CURRENT_TIMESTAMP as gold_processed_at,
                'property_gold_v3_business_ready' as processing_version,
                
                -- Embeddings from Silver table (medallion architecture)
                s.embedding_vector,
                s.embedding_generated_at
                
            FROM {safe_input} s
            LEFT JOIN silver_neighborhoods n ON s.neighborhood_id = n.neighborhood_id
            WHERE s.listing_id IS NOT NULL
            AND s.price > 0
            AND s.square_feet > 0
        """
        
        # Execute the CREATE VIEW statement
        conn.execute(query)
        
        # Track enrichments applied
        self.enrichments_applied.extend([
            "status_field",
            "amenities_field",
            "search_tags_field",
            "enriched_description"
        ])
        
        self.logger.info(f"Created Gold view {output_table} with {len(self.enrichments_applied)} enrichments")