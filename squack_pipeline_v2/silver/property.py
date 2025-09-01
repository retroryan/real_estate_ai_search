"""Property Silver layer transformation using DuckDB Relation API."""

from squack_pipeline_v2.silver.base import SilverTransformer
from squack_pipeline_v2.core.logging import log_stage


class PropertySilverTransformer(SilverTransformer):
    """Transformer for property data into Silver layer using Relation API.
    
    Silver layer principles:
    - Flatten nested structures for analysis
    - Clean and validate data
    - Standardize field names and formats
    - Prepare data for downstream consumption
    """
    
    def _get_entity_type(self) -> str:
        """Return entity type."""
        return "property"
    
    @log_stage("Silver: Property Transformation")
    def _apply_transformations(self, input_table: str, output_table: str) -> None:
        """Apply property transformations using DuckDB Relation API.
        
        Uses the Relation API for:
        - Lazy evaluation
        - Query optimization
        - Type safety
        
        Args:
            input_table: Bronze input table
            output_table: Silver output table
        """
        # Get connection for Relation API
        conn = self.connection_manager.get_connection()
        
        # Create relation from Bronze table
        bronze_relation = conn.table(input_table)
        
        # Apply transformations using SQL expression
        # Note: Complex transformations still use SQL within the relation
        silver_relation = conn.sql(f"""
            SELECT 
                -- Core identifiers
                listing_id,
                neighborhood_id,
                
                -- Flatten property_details to top level
                property_details.bedrooms as bedrooms,
                property_details.bathrooms as bathrooms,
                property_details.square_feet as square_feet,
                property_details.property_type as property_type,
                property_details.year_built as year_built,
                -- Convert lot_size from acres to square feet
                CAST(ROUND(COALESCE(property_details.lot_size * 43560, 0)) AS INTEGER) as lot_size,
                property_details.garage_spaces as garage_spaces,
                
                -- Price fields
                listing_price as price,
                price_per_sqft,
                
                -- Address as structured object
                struct_pack(
                    street := address.street,
                    city := address.city,
                    state := address.state,
                    zip_code := address.zip,
                    location := LIST_VALUE(coordinates.longitude, coordinates.latitude)
                ) as address,
                
                -- Text fields
                description,
                features,
                
                -- Dates and metadata
                listing_date,
                days_on_market,
                virtual_tour_url,
                images,
                
                -- Keep complex nested data
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
        """)
        
        # Create the output table from the relation
        silver_relation.create(output_table)
        
        self.logger.info(f"Transformed properties from {input_table} to {output_table}")