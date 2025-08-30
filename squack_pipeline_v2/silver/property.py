"""Property Silver layer transformation - flatten for Elasticsearch structure."""

from squack_pipeline_v2.silver.base import SilverTransformer
from squack_pipeline_v2.core.logging import log_stage


class PropertySilverTransformer(SilverTransformer):
    """Transformer for property data into Silver layer.
    
    CORRECTED to match actual Elasticsearch template structure:
    - Flatten property_details to top-level fields (bedrooms, bathrooms, etc.)
    - Keep address as nested object but prepare for location inside
    - Clean and validate data
    - NO denormalization - flatten to ES structure
    """
    
    def _get_entity_type(self) -> str:
        """Return entity type."""
        return "property"
    
    def _apply_transformations(self, input_table: str, output_table: str) -> None:
        """Apply property flattening to match Elasticsearch template.
        
        Flattens nested structures to match the ES mapping template exactly.
        
        Args:
            input_table: Bronze input table
            output_table: Silver output table
        """
        query = f"""
        CREATE TABLE {output_table} AS
        SELECT 
            -- Core identifiers
            listing_id,
            neighborhood_id,
            
            -- Flatten property_details to top level (as ES template expects)
            property_details.bedrooms as bedrooms,
            property_details.bathrooms as bathrooms,
            property_details.square_feet as square_feet,
            property_details.property_type as property_type,
            property_details.year_built as year_built,
            property_details.lot_size as lot_size,
            property_details.garage_spaces as garage_spaces,
            
            -- Price fields (at top level)
            listing_price as price,  -- Rename to match ES template
            price_per_sqft,
            
            -- Address as object (ES template expects this structure)
            struct_pack(
                street := address.street,
                city := address.city,
                state := address.state,
                zip_code := address.zip,
                location := LIST_VALUE(coordinates.longitude, coordinates.latitude)  -- geo_point inside address
            ) as address,
            
            -- Text fields
            description,
            features,
            
            -- Dates and metadata
            listing_date,
            days_on_market,
            virtual_tour_url,
            images,
            
            -- Keep complex nested data for advanced search features
            price_history,
            market_trends,
            buyer_persona,
            viewing_statistics,
            buyer_demographics,
            nearby_amenities,
            future_enhancements
            
        FROM {input_table}
        WHERE 
            listing_id IS NOT NULL 
            AND listing_price > 0
            AND property_details.square_feet > 0
        """
        
        self.connection_manager.execute(query)