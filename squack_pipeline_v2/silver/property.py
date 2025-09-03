"""Property Silver layer transformation using DuckDB Relation API.

PROPERTY EMBEDDING GENERATION DETAILS:
======================================

This module handles the transformation of property listings into the Silver layer,
with a critical focus on generating semantic embeddings for each property.

EMBEDDING TEXT COMPOSITION FOR PROPERTIES:
------------------------------------------
The embedding_text field is carefully constructed from the following property fields
to capture the semantic essence of each listing:

1. **description** (Primary): Full property description containing rich details about
   the property's features, condition, location benefits, and unique selling points.
   This is the most important field as it contains human-written narrative text.

2. **property_type**: Type of property (e.g., "Single Family Home", "Condo", "Townhouse")
   Provides categorical context that influences how other features are interpreted.

3. **bedrooms**: Number of bedrooms formatted as "X bedrooms"
   Key numeric feature that defines property capacity and family suitability.

4. **bathrooms**: Number of bathrooms formatted as "X bathrooms"  
   Important amenity that affects property value and livability.

5. **square_feet**: Total square footage formatted as "X sqft"
   Critical size metric that provides spatial context for the property.

FIELD CONCATENATION STRATEGY:
-----------------------------
Fields are concatenated using CONCAT_WS (Concatenate With Separator) with space delimiter:
- Order: description → property_type → bedrooms → bathrooms → square_feet
- Null/empty values are handled gracefully with COALESCE to prevent gaps
- Numeric fields are converted to descriptive text (e.g., "3 bedrooms" not just "3")

WHY THESE FIELDS WERE CHOSEN:
-----------------------------
- **Semantic Richness**: Description provides natural language context
- **Key Differentiators**: Bedrooms, bathrooms, and square feet are primary search criteria
- **Property Classification**: Property type helps disambiguate similar descriptions
- **Search Alignment**: These fields match what users typically search for

FIELDS INTENTIONALLY EXCLUDED FROM EMBEDDINGS:
----------------------------------------------
- **Price**: Excluded to prevent price bias in semantic similarity
- **Address/Location**: Handled separately via geo-coordinates for location-based search
- **Listing Date**: Temporal data that doesn't affect property semantics
- **Images/URLs**: Non-textual data not suitable for text embeddings
- **Market Trends**: Statistical data better suited for structured queries

EMBEDDING GENERATION PROCESS:
-----------------------------
1. SQL projection creates embedding_text using CONCAT_WS (lines 80-86)
2. Text extracted from DuckDB along with listing_ids (lines 90-95)
3. Texts sent to embedding provider API (line 97)
4. Resulting vectors stored as DOUBLE[] arrays with timestamps (lines 99-117)
5. Embeddings joined back to property data via listing_id (lines 120-153)

TOKENIZATION NOTE:
-----------------
No pre-tokenization or chunking is performed. The embedding provider's API handles:
- Text tokenization using model-specific tokenizers
- Truncation if text exceeds model's context window
- Conversion to dense vector representation
"""

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
    - Generate semantic embeddings for similarity search
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
            -- EMBEDDING TEXT GENERATION:
            -- Concatenate key property fields to create semantic representation
            -- Fields chosen for their descriptive value and search relevance
            -- Order: narrative description → categorical type → numeric features
            CONCAT_WS(' ',  -- Space-separated concatenation
                COALESCE(description, ''),  -- Primary: Full property description text
                COALESCE(property_details.property_type, ''),  -- Property classification
                CONCAT(COALESCE(property_details.bedrooms, 0), ' bedrooms'),  -- Bedroom count with label
                CONCAT(COALESCE(property_details.bathrooms, 0), ' bathrooms'),  -- Bathroom count with label
                CONCAT(COALESCE(property_details.square_feet, 0), ' sqft')  -- Size with unit
            ) as embedding_text
        """)
        
        # STEP 1: Extract text data from DuckDB for embedding generation
        # Get embedding text data directly from DuckDB without pandas conversion
        # This avoids memory overhead and maintains DuckDB's efficient data handling
        embedding_rows = transformed.project("listing_id, embedding_text").fetchall()
        
        # STEP 2: Prepare data for embedding API
        # Extract data into separate lists for batch processing
        listing_ids = [row[0] for row in embedding_rows]  # Property identifiers
        texts = [row[1] for row in embedding_rows]  # Concatenated text for each property
        
        # STEP 3: Generate embeddings via external provider
        # Generate embeddings using List[str] interface
        # Provider handles: tokenization → encoding → vector generation
        # No LlamaIndex or pre-chunking - direct API call with full texts
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