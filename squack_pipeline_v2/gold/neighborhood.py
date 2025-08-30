"""Neighborhood Gold layer enrichment - matches Elasticsearch template exactly."""

from squack_pipeline_v2.gold.base import GoldEnricher
from squack_pipeline_v2.core.logging import log_stage


class NeighborhoodGoldEnricher(GoldEnricher):
    """Enricher for neighborhood data into Gold layer.
    
    CORRECTED to match actual Elasticsearch template:
    - Pass through flattened fields from Silver
    - Data already matches ES structure
    - Minimal transformation needed
    """
    
    def _get_entity_type(self) -> str:
        """Return entity type."""
        return "neighborhood"
    
    def _apply_enrichments(self, input_table: str, output_table: str) -> None:
        """Apply minimal Gold enrichments - data already matches ES structure.
        
        Args:
            input_table: Silver neighborhoods table
            output_table: Gold neighborhoods table
        """
        query = f"""
        CREATE TABLE {output_table} AS
        SELECT 
            -- Pass through all fields from Silver (already in correct ES structure)
            neighborhood_id,
            name,
            city,
            state,
            
            -- Location already as geo_point array
            location,
            
            -- Extract center coordinates for ES writer compatibility
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
            
            -- Flattened metrics (already at top level from Silver)
            COALESCE(population, 0) as population,
            COALESCE(median_income, 0) as median_income,
            
            -- Add derived price field for ES compatibility
            COALESCE(median_income, 0) * 4 as median_home_price,
            
            -- Scores with defaults
            COALESCE(walkability_score, 0.0) as walkability_score,
            COALESCE(school_rating, 0.0) as school_score,  -- Rename for ES compatibility
            
            -- Calculate overall livability score
            (COALESCE(walkability_score, 0.0) + COALESCE(school_rating, 0.0) * 10) / 2 as overall_livability_score,
            
            -- Nested objects (preserved from Bronze via Silver)
            COALESCE(demographics, struct_pack()) as demographics,
            wikipedia_correlations,
            
            -- Text and arrays
            COALESCE(description, '') as description,
            COALESCE(amenities, LIST_VALUE()) as amenities,
            
            -- Create embedding text by combining key fields
            COALESCE(CAST(name AS VARCHAR), '') || ' | ' ||
            COALESCE(CAST(description AS VARCHAR), '') || ' | ' ||
            COALESCE(CAST(amenities AS VARCHAR), '') as embedding_text,
            
            -- Add Gold metadata
            CURRENT_TIMESTAMP as gold_processed_at,
            'neighborhood_gold_v2_corrected' as processing_version
            
        FROM {input_table}
        WHERE neighborhood_id IS NOT NULL
        """
        
        self.connection_manager.execute(query)
        self.enrichments_applied.append("es_structure_compliance")
        self.enrichments_applied.append("embedding_text")