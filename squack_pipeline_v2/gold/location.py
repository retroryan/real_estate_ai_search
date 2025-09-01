"""Location Gold layer enrichment using DuckDB views.

Creates canonical geographic entities for graph building.
"""

from squack_pipeline_v2.gold.base import GoldEnricher
from squack_pipeline_v2.core.logging import log_stage


class LocationGoldEnricher(GoldEnricher):
    """Enricher for location data into Gold layer.
    
    Gold layer principles:
    - Create canonical geographic entities
    - Build complete hierarchy relationships
    - Prepare data for graph node/relationship creation
    - Enable full geographic traversal
    """
    
    def _get_entity_type(self) -> str:
        """Return entity type."""
        return "location"

    @log_stage("Gold: Location Enrichment")
    def _create_enriched_view(self, input_table: str, output_table: str) -> None:
        """Create enriched location view for graph building.
        
        Following DuckDB best practices:
        - Use views for Gold layer (not tables)
        - Single CREATE VIEW operation
        - Prepare data for downstream graph building
        
        Args:
            input_table: Silver input table
            output_table: Gold output view
        """
        conn = self.connection_manager.get_connection()
        
        # Create enriched view with all hierarchy data
        query = f"""
        CREATE VIEW {output_table} AS
        SELECT
            -- Original fields
            neighborhood_standardized as neighborhood,
            city_standardized as city,
            county_standardized as county,
            state_standardized as state,
            zip_code,
            zip_code_status,
            
            -- Hierarchical IDs for graph building
            neighborhood_id,
            city_id,
            county_id,
            state_id,
            
            -- Location type for filtering
            location_type,
            
            -- Full hierarchy path for debugging
            hierarchy_path,
            
            -- Computed fields for graph relationships
            CASE 
                WHEN neighborhood_id IS NOT NULL THEN 'neighborhood:' || neighborhood_id
                WHEN city_id IS NOT NULL THEN 'city:' || city_id
                WHEN county_id IS NOT NULL THEN 'county:' || county_id
                WHEN state_id IS NOT NULL THEN 'state:' || state_id
                ELSE NULL
            END as graph_node_id,
            
            -- Parent relationships for hierarchy
            CASE
                WHEN location_type = 'neighborhood' THEN city_id
                WHEN location_type = 'city' THEN county_id
                WHEN location_type = 'county' THEN state_id
                ELSE NULL
            END as parent_location_id
            
        FROM {input_table}
        """
        
        conn.execute(query)
        
        self.enrichments_applied.append("hierarchical_ids")
        self.enrichments_applied.append("graph_node_ids")
        self.enrichments_applied.append("parent_relationships")
        
        self.logger.info(f"Location gold enrichment complete: {output_table}")