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
        
        # Build enriched description with neighborhood info
        # Note: Simplified to avoid subquery issues in Relation API
        enriched_description_sql = """
        s.description || 
        COALESCE(
            ' Located in ' || n.name || '.', 
            ''
        ) AS enriched_description
        """
        
        # Use DuckDB Relation API for type-safe, lazy-evaluated operations
        # Build the enriched view step by step
        silver_properties = conn.table(input_table).set_alias("s")
        silver_neighborhoods = conn.table("silver_neighborhoods").set_alias("n")
        
        # Join properties with neighborhoods
        joined = silver_properties.join(
            silver_neighborhoods,
            "s.neighborhood_id = n.neighborhood_id",
            how="left"
        )
        
        # Project enriched columns using Relation API
        enriched = joined.project(f"""
            -- Core identifiers
            s.listing_id,
            s.neighborhood_id,
            
            -- Basic property details
            s.bedrooms,
            s.bathrooms,
            s.square_feet,
            s.property_type,
            s.year_built,
            s.lot_size,
            
            -- Price fields with type casting
            CAST(s.price AS FLOAT) AS price,
            CAST(s.price_per_sqft AS FLOAT) AS price_per_sqft,
            
            -- Address and location
            s.address,
            
            -- Geographic hierarchy via neighborhood
            n.city_id as location_city_id,
            n.county_id as location_county_id,
            n.state_id as location_state_id,
            
            -- Structured parking object
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
            
            -- Enriched description combining property and neighborhood context
            {enriched_description_sql},
            
            s.features,
            s.virtual_tour_url,
            s.images,
            
            -- Dates and metadata
            s.listing_date,
            s.days_on_market,
            
            -- Status field (required by ES queries)
            'active' AS status,
            
            -- Search tags (required by ES queries)
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
            
            -- Embedding text and vectors
            s.embedding_text,
            
            -- Business metadata
            CURRENT_TIMESTAMP as gold_processed_at,
            'property_gold_v3_business_ready' as processing_version,
            
            -- Embeddings
            s.embedding_vector,
            s.embedding_generated_at
        """)
        
        # Apply filters (use column names without alias after projection)
        filtered = enriched.filter("""
            listing_id IS NOT NULL
            AND price > 0
            AND square_feet > 0
        """)
        
        # Create view using Relation API
        filtered.create_view(output_table)
        
        # Track enrichments applied
        self.enrichments_applied.extend([
            "status_field",
            "search_tags_field",
            "enriched_description",
            "geographic_hierarchy_via_neighborhood"
        ])
        
        self.logger.info(f"Created Gold view {output_table} with {len(self.enrichments_applied)} enrichments")