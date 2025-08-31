"""Wikipedia Silver layer transformation - standardization only."""

from squack_pipeline_v2.silver.base import SilverTransformer
from squack_pipeline_v2.core.logging import log_stage
from squack_pipeline_v2.utils import StateStandardizer


class WikipediaSilverTransformer(SilverTransformer):
    """Transformer for Wikipedia data into Silver layer.
    
    Silver layer principles:
    - Standardize field names (pageid → page_id)
    - Validate data quality
    - Clean text fields
    - NO business logic or enrichment (that's Gold layer)
    """
    
    def _get_entity_type(self) -> str:
        """Return entity type."""
        return "wikipedia"
    
    def _apply_transformations(self, input_table: str, output_table: str) -> None:
        """Apply Wikipedia standardization transformations.
        
        Silver layer focuses on:
        - Field name standardization (pageid → page_id, best_state → state)
        - Value standardization (state full names → abbreviations)
        - Coordinate validation
        - Text cleaning
        - Keep data structure simple
        
        Args:
            input_table: Bronze input table
            output_table: Silver output table
        """
        # Get state transformation SQL
        state_case_sql = StateStandardizer.get_sql_case_statement('best_state', 'state')
        
        query = f"""
        CREATE TABLE {output_table} AS
        SELECT
            -- Standardize identifiers
            id,
            pageid as page_id,
            location_id,
            
            -- Text fields (cleaned)
            TRIM(title) as title,
            url,
            TRIM(extract) as extract,
            categories,
            
            -- Coordinates (validated)
            latitude,
            longitude,
            
            -- Location data standardized from Bronze layer
            best_city as city,
            best_county as county,
            -- Transform state full names to abbreviations
            {state_case_sql},
            
            -- Metrics and metadata
            relevance_score,
            depth,
            crawled_at,
            html_file,
            file_hash,
            image_url,
            links_count,
            infobox_data
            
        FROM {input_table}
        WHERE pageid IS NOT NULL
            AND (latitude IS NULL OR (latitude BETWEEN -90 AND 90))
            AND (longitude IS NULL OR (longitude BETWEEN -180 AND 180))
        """
        
        self.connection_manager.execute(query)