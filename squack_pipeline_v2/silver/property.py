"""Property Silver layer transformation using DuckDB Relation API."""

from squack_pipeline_v2.silver.base import SilverTransformer
from squack_pipeline_v2.core.logging import log_stage
from datetime import datetime


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
        
        Following DuckDB best practices:
        - Use Relation API throughout
        - Single CREATE TABLE operation
        - No column duplication
        
        Args:
            input_table: Bronze input table
            output_table: Silver output table
        """
        conn = self.connection_manager.get_connection()
        
        # Use Relation API to create base transformation
        bronze = conn.table(input_table)
        
        # Apply filters using Relation API
        filtered = bronze.filter("""
            listing_id IS NOT NULL 
            AND listing_price > 0
            AND property_details.square_feet > 0
        """)
        
        # Project to standardized columns using Relation API
        transformed = filtered.project("""
            listing_id,
            neighborhood_id,
            property_details.bedrooms as bedrooms,
            property_details.bathrooms as bathrooms,
            property_details.square_feet as square_feet,
            property_details.property_type as property_type,
            property_details.year_built as year_built,
            CAST(ROUND(COALESCE(property_details.lot_size * 43560, 0)) AS INTEGER) as lot_size,
            property_details.garage_spaces as garage_spaces,
            listing_price as price,
            price_per_sqft,
            struct_pack(
                street := address.street,
                city := address.city,
                state := address.state,
                zip_code := address.zip,
                location := LIST_VALUE(coordinates.longitude, coordinates.latitude)
            ) as address,
            description,
            features,
            listing_date,
            days_on_market,
            virtual_tour_url,
            images,
            price_history,
            market_trends,
            buyer_persona,
            viewing_statistics,
            buyer_demographics,
            nearby_amenities,
            future_enhancements,
            CONCAT_WS(' ', 
                COALESCE(description, ''),
                COALESCE(property_details.property_type, ''),
                CONCAT(COALESCE(property_details.bedrooms, 0), ' bedrooms'),
                CONCAT(COALESCE(property_details.bathrooms, 0), ' bathrooms'),
                CONCAT(COALESCE(property_details.square_feet, 0), ' sqft')
            ) as embedding_text
        """)
        
        # Get embedding text data directly from DuckDB without pandas conversion
        embedding_rows = transformed.project("listing_id, embedding_text").fetchall()
        
        # Extract data into separate lists
        listing_ids = [row[0] for row in embedding_rows]
        texts = [row[1] for row in embedding_rows]
        
        # Generate embeddings using List[str] interface
        embedding_response = self.embedding_provider.generate_embeddings(texts)
        
        # Create temporary table with embeddings
        current_timestamp = datetime.now()
        
        # Build VALUES clause for embedding data
        values_clause = []
        for lid, text, embedding in zip(listing_ids, texts, embedding_response.embeddings):
            # Escape single quotes in text
            escaped_text = text.replace("'", "''") if text else ''
            # Format embedding vector as array literal
            embedding_str = '[' + ','.join(str(v) for v in embedding) + ']'
            values_clause.append(f"('{lid}', '{escaped_text}', {embedding_str}::DOUBLE[], TIMESTAMP '{current_timestamp}')")
        
        # Create embedding table
        conn.execute(f"""
            CREATE TABLE embedding_data AS
            SELECT * FROM (
                VALUES {','.join(values_clause)}
            ) AS t(listing_id, embedding_text, embedding_vector, embedding_generated_at)
        """)
        
        # Join embeddings and create final table
        final_result = (transformed
            .join(conn.table('embedding_data'), 'listing_id', how='left')
            .project("""
                listing_id,
                neighborhood_id,
                bedrooms,
                bathrooms,
                square_feet,
                property_type,
                year_built,
                lot_size,
                garage_spaces,
                price,
                price_per_sqft,
                address,
                description,
                features,
                listing_date,
                days_on_market,
                virtual_tour_url,
                images,
                price_history,
                market_trends,
                buyer_persona,
                viewing_statistics,
                buyer_demographics,
                nearby_amenities,
                future_enhancements,
                embedding_data.embedding_text,
                embedding_data.embedding_vector,
                embedding_data.embedding_generated_at
            """))
        
        final_result.create(output_table)
        
        # Clean up temporary table
        conn.execute("DROP TABLE IF EXISTS embedding_data")
        
        self.logger.info(f"Transformed properties from {input_table} to {output_table}")