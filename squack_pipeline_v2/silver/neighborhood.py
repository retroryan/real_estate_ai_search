"""Neighborhood Silver layer transformation - flatten for Elasticsearch structure."""

from squack_pipeline_v2.silver.base import SilverTransformer
from squack_pipeline_v2.core.logging import log_stage


class NeighborhoodSilverTransformer(SilverTransformer):
    """Transformer for neighborhood data into Silver layer.
    
    CORRECTED to match actual Elasticsearch template structure:
    - Flatten key fields to top level (population, median_income, walkability_score, etc.)
    - Create location as geo_point at top level
    - Keep demographics as nested object (ES template expects this)
    - Keep wikipedia_correlations nested structure
    """
    
    def _get_entity_type(self) -> str:
        """Return entity type."""
        return "neighborhood"
    
    def _apply_transformations(self, input_table: str, output_table: str) -> None:
        """Apply neighborhood flattening to match Elasticsearch template.
        
        Args:
            input_table: Bronze input table
            output_table: Silver output table
        """
        query = f"""
        CREATE TABLE {output_table} AS
        SELECT 
            -- Core identifiers
            neighborhood_id,
            name,
            city,
            state,
            
            -- Create location as top-level geo_point (ES template expects this)
            CASE 
                WHEN coordinates.longitude IS NOT NULL AND coordinates.latitude IS NOT NULL
                THEN LIST_VALUE(coordinates.longitude, coordinates.latitude)
                ELSE NULL
            END as location,
            
            -- Flatten key metrics to top level (as ES template expects)
            demographics.population as population,
            demographics.median_household_income as median_income,
            characteristics.walkability_score as walkability_score,
            characteristics.school_rating as school_rating,
            
            -- Keep demographics as nested object (ES template has this structure)
            demographics,
            
            -- Text fields
            description,
            amenities,
            
            -- Keep wikipedia_correlations nested (ES template expects this exact structure)
            wikipedia_correlations
            
        FROM {input_table}
        WHERE neighborhood_id IS NOT NULL
        AND name IS NOT NULL
        """
        
        self.connection_manager.execute(query)