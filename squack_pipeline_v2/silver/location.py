"""Location Silver layer transformation using DuckDB Relation API."""

from squack_pipeline_v2.silver.base import SilverTransformer
from squack_pipeline_v2.core.logging import log_stage


class LocationSilverTransformer(SilverTransformer):
    """Transformer for location data into Silver layer using Relation API.
    
    Silver layer principles:
    - Standardize state names (CA → California, UT → Utah)
    - Clean and normalize city names
    - Remove "County" suffix from county names
    - Create hierarchical IDs for linking
    - Validate ZIP codes and flag placeholders
    """
    
    def _get_entity_type(self) -> str:
        """Return entity type."""
        return "location"

    @log_stage("Silver: Location Transformation")
    def _apply_transformations(self, input_table: str, output_table: str) -> None:
        """Apply location transformations using DuckDB Relation API.
        
        Following DuckDB best practices:
        - Use Relation API throughout
        - Single CREATE TABLE operation
        - All standardizations in one pass
        
        Args:
            input_table: Bronze input table
            output_table: Silver output table
        """
        conn = self.connection_manager.get_connection()
        
        # Use Relation API to create base transformation
        bronze = conn.table(input_table)
        
        # Apply all transformations in a single projection using Relation API
        transformed = bronze.project("""
            -- Standardize state names
            CASE 
                WHEN state = 'CA' THEN 'California'
                WHEN state = 'UT' THEN 'Utah'
                WHEN state IN ('California', 'Utah') THEN state
                ELSE COALESCE(state, 'Unknown')
            END as state_standardized,
            
            -- Original state for reference
            state as state_original,
            
            -- Standardize county names (remove 'County' suffix)
            CASE 
                WHEN county IS NOT NULL THEN 
                    TRIM(REGEXP_REPLACE(county, '\\s+County$', '', 'i'))
                ELSE NULL
            END as county_standardized,
            
            -- Clean city names (trim only - DuckDB doesn't have INITCAP)
            CASE 
                WHEN city IS NOT NULL THEN 
                    TRIM(city)
                ELSE NULL
            END as city_standardized,
            
            -- Clean neighborhood names
            CASE 
                WHEN neighborhood IS NOT NULL THEN 
                    TRIM(neighborhood)
                ELSE NULL
            END as neighborhood_standardized,
            
            -- Validate and flag ZIP codes
            zip_code,
            CASE 
                WHEN zip_code IS NULL THEN 'missing'
                WHEN LENGTH(zip_code) != 5 THEN 'invalid'
                WHEN zip_code = '90001' THEN 'placeholder'
                WHEN REGEXP_MATCHES(zip_code, '^[0-9]{5}$') THEN 'valid'
                ELSE 'invalid'
            END as zip_code_status,
            
            -- Create hierarchical location IDs for linking
            CASE 
                WHEN neighborhood IS NOT NULL AND city IS NOT NULL THEN 
                    LOWER(CONCAT(
                        REGEXP_REPLACE(neighborhood, '[^a-zA-Z0-9]', '', 'g'),
                        '_',
                        REGEXP_REPLACE(city, '[^a-zA-Z0-9]', '', 'g')
                    ))
                ELSE NULL
            END as neighborhood_id,
            
            LOWER(CONCAT(
                REGEXP_REPLACE(COALESCE(city, ''), '[^a-zA-Z0-9]', '', 'g'),
                '_',
                CASE 
                    WHEN state = 'CA' THEN 'california'
                    WHEN state = 'UT' THEN 'utah'
                    WHEN state = 'California' THEN 'california'
                    WHEN state = 'Utah' THEN 'utah'
                    ELSE LOWER(REGEXP_REPLACE(COALESCE(state, ''), '[^a-zA-Z0-9]', '', 'g'))
                END
            )) as city_id,
            
            LOWER(CONCAT(
                REGEXP_REPLACE(
                    COALESCE(REGEXP_REPLACE(county, '\\s+County$', '', 'i'), ''),
                    '[^a-zA-Z0-9]', '', 'g'
                ),
                '_',
                CASE 
                    WHEN state = 'CA' THEN 'california'
                    WHEN state = 'UT' THEN 'utah'
                    WHEN state = 'California' THEN 'california'
                    WHEN state = 'Utah' THEN 'utah'
                    ELSE LOWER(REGEXP_REPLACE(COALESCE(state, ''), '[^a-zA-Z0-9]', '', 'g'))
                END
            )) as county_id,
            
            CASE 
                WHEN state = 'CA' THEN 'state_california'
                WHEN state = 'UT' THEN 'state_utah'
                WHEN state = 'California' THEN 'state_california'
                WHEN state = 'Utah' THEN 'state_utah'
                ELSE CONCAT('state_', LOWER(REGEXP_REPLACE(COALESCE(state, 'unknown'), '[^a-zA-Z0-9]', '', 'g')))
            END as state_id,
            
            -- Determine location type based on available fields
            CASE 
                WHEN neighborhood IS NOT NULL THEN 'neighborhood'
                WHEN city IS NOT NULL AND neighborhood IS NULL THEN 'city'
                WHEN county IS NOT NULL AND city IS NULL THEN 'county'
                WHEN state IS NOT NULL AND county IS NULL THEN 'state'
                ELSE 'unknown'
            END as location_type,
            
            -- Create full hierarchy path for debugging/analysis
            CONCAT_WS(' > ',
                neighborhood,
                city,
                county,
                state
            ) as hierarchy_path
        """)
        
        # Create the table in a single operation
        transformed.create(output_table)
        
        self.logger.info(f"Location silver transformation complete: {output_table}")