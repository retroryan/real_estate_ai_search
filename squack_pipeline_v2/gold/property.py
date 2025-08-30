"""Property Gold layer enrichment - prepare for EXACT Elasticsearch structure."""

from squack_pipeline_v2.gold.base import GoldEnricher
from squack_pipeline_v2.core.logging import log_stage


class PropertyGoldEnricher(GoldEnricher):
    """Enricher for property data into Gold layer.
    
    CORRECTED to match actual Elasticsearch template:
    - Fields are already flattened in Silver (bedrooms, bathrooms at top level)
    - Create parking object with 'spaces' and 'type' fields
    - Pass through address object with location inside
    - Minimal transformation - data is already in ES structure
    """
    
    def _get_entity_type(self) -> str:
        """Return entity type."""
        return "property"
    
    def _apply_enrichments(self, input_table: str, output_table: str) -> None:
        """Apply minimal Gold enrichments - data already matches ES structure.
        
        Args:
            input_table: Silver properties table
            output_table: Gold properties table
        """
        query = f"""
        CREATE TABLE {output_table} AS
        SELECT 
            -- Pass through all flattened fields from Silver
            listing_id,
            neighborhood_id,
            
            -- Top-level fields already flattened in Silver
            bedrooms,
            bathrooms,
            square_feet,
            property_type,
            year_built,
            lot_size,
            
            -- Price fields (cast to FLOAT for Elasticsearch)
            CAST(price AS FLOAT) AS price,
            CAST(price_per_sqft AS FLOAT) AS price_per_sqft,
            
            -- Address object with location inside (already structured in Silver)
            address,
            
            -- Create parking object to match ES template
            struct_pack(
                spaces := COALESCE(garage_spaces, 0),
                type := CASE 
                    WHEN garage_spaces > 0 THEN 'garage' 
                    ELSE 'none' 
                END
            ) as parking,
            
            -- Text and media
            description,
            COALESCE(features, LIST_VALUE()) AS features,  -- Ensure always a list
            virtual_tour_url,
            images,
            
            -- Dates and metrics
            listing_date,
            days_on_market,
            
            -- Keep complex nested data for enrichment features
            price_history,
            market_trends,
            buyer_persona,
            viewing_statistics,
            buyer_demographics,
            nearby_amenities,
            future_enhancements,
            
            -- Create embedding text by combining key fields
            COALESCE(CAST(description AS VARCHAR), '') || ' | ' ||
            COALESCE(CAST(property_type AS VARCHAR), '') || ' | ' ||
            COALESCE(CAST(features AS VARCHAR), '') as embedding_text,
            
            -- Add Gold metadata
            CURRENT_TIMESTAMP as gold_processed_at,
            'property_gold_v2_corrected' as processing_version
            
        FROM {input_table}
        WHERE listing_id IS NOT NULL
        """
        
        self.connection_manager.execute(query)
        self.enrichments_applied.append("parking_object")
        self.enrichments_applied.append("es_structure_compliance")
        self.enrichments_applied.append("embedding_text")