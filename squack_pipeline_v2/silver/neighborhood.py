"""Neighborhood Silver layer transformation using DuckDB Relation API."""

from squack_pipeline_v2.silver.base import SilverTransformer
from squack_pipeline_v2.core.logging import log_stage


class NeighborhoodSilverTransformer(SilverTransformer):
    """Transformer for neighborhood data into Silver layer using Relation API.
    
    Silver layer principles:
    - Flatten key metrics for analysis
    - Standardize location data
    - Clean and validate fields
    - Prepare for downstream consumption
    """
    
    def _get_entity_type(self) -> str:
        """Return entity type."""
        return "neighborhood"
    
    @log_stage("Silver: Neighborhood Transformation")
    def _apply_transformations(self, input_table: str, output_table: str) -> None:
        """Apply neighborhood transformations using DuckDB Relation API.
        
        Uses the Relation API for:
        - Lazy evaluation
        - Query optimization
        - Clean transformation chains
        
        Args:
            input_table: Bronze input table
            output_table: Silver output table
        """
        # Get connection for Relation API
        conn = self.connection_manager.get_connection()
        
        # Apply transformations using SQL within relation
        silver_relation = conn.sql(f"""
            SELECT 
                -- Core identifiers
                neighborhood_id,
                name,
                city,
                state,
                
                -- Create location as geo_point
                CASE 
                    WHEN coordinates.longitude IS NOT NULL AND coordinates.latitude IS NOT NULL
                    THEN LIST_VALUE(coordinates.longitude, coordinates.latitude)
                    ELSE NULL
                END as location,
                
                -- Flatten key metrics to top level
                demographics.population as population,
                demographics.median_household_income as median_income,
                characteristics.walkability_score as walkability_score,
                characteristics.school_rating as school_rating,
                
                -- Keep demographics as nested object
                demographics,
                
                -- Text fields
                description,
                amenities,
                
                -- Keep correlations nested
                wikipedia_correlations
                
            FROM {input_table}
            WHERE neighborhood_id IS NOT NULL
            AND name IS NOT NULL
        """)
        
        # Create the output table
        silver_relation.create(output_table)
        
        self.logger.info(f"Transformed neighborhoods from {input_table} to {output_table}")