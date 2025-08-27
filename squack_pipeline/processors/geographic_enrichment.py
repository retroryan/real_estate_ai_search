"""Geographic enrichment processor for location-based features."""

from typing import Dict, Any

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.processors.base import TransformationProcessor
from squack_pipeline.utils.logging import log_execution_time


class GeographicEnrichmentProcessor(TransformationProcessor):
    """Processor for geographic data enrichment and spatial analysis."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize geographic enrichment processor."""
        super().__init__(settings)
        self.metrics = {
            "records_processed": 0,
            "coordinates_enriched": 0,
            "distances_calculated": 0,
            "geographic_completeness": 0.0
        }
        
        # Bay Area reference points (major city centers)
        self.reference_points = {
            'sf_downtown': {'lat': 37.7749, 'lon': -122.4194, 'name': 'San Francisco Downtown'},
            'oakland_downtown': {'lat': 37.8044, 'lon': -122.2712, 'name': 'Oakland Downtown'},
            'palo_alto_center': {'lat': 37.4419, 'lon': -122.1430, 'name': 'Palo Alto Center'},
            'san_jose_downtown': {'lat': 37.3382, 'lon': -121.8863, 'name': 'San Jose Downtown'}
        }
    
    def process(self, input_table: str) -> str:
        """Override process to create properly named enriched table."""
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
        
        # Generate output table name with proper prefix
        import time
        timestamp = int(time.time())
        output_table = f"property_enriched_{timestamp}"
        
        # Get transformation query
        transformation_query = self.get_transformation_query(input_table)
        
        # Create output table from transformation
        self.create_table_from_query(output_table, transformation_query)
        
        # Update metrics
        input_count = self.count_records(input_table)
        output_count = self.count_records(output_table)
        
        self.logger.info(
            f"Transformed {input_count} records to {output_count} records "
            f"in {output_table}"
        )
        
        return output_table
    
    @log_execution_time
    def get_transformation_query(self, input_table: str) -> str:
        """Get SQL transformation query for geographic enrichment."""
        # Build distance calculations for each reference point
        distance_calculations = []
        for key, point in self.reference_points.items():
            calc = f"""
            CASE 
                WHEN t.latitude IS NOT NULL AND t.longitude IS NOT NULL
                THEN ROUND(
                    111.045 * DEGREES(ACOS(
                        LEAST(1.0, 
                            COS(RADIANS(t.latitude)) * 
                            COS(RADIANS({point['lat']})) * 
                            COS(RADIANS(t.longitude) - RADIANS({point['lon']})) +
                            SIN(RADIANS(t.latitude)) * 
                            SIN(RADIANS({point['lat']}))
                        )
                    )), 2
                )
                ELSE NULL 
            END as distance_to_{key}_km"""
            distance_calculations.append(calc)
        
        distance_fields = ",\n            ".join(distance_calculations)
        
        return f"""
        SELECT 
            -- Original data
            t.*,
            
            -- GEOGRAPHIC ENRICHMENT: Distance Calculations
            {distance_fields},
            
            -- Closest major city
            CASE 
                WHEN t.latitude IS NOT NULL AND t.longitude IS NOT NULL THEN
                    (SELECT city_name FROM (
                        SELECT 'San Francisco' as city_name, 
                               111.045 * DEGREES(ACOS(
                                   LEAST(1.0, 
                                       COS(RADIANS(t.latitude)) * COS(RADIANS(37.7749)) * 
                                       COS(RADIANS(t.longitude) - RADIANS(-122.4194)) +
                                       SIN(RADIANS(t.latitude)) * SIN(RADIANS(37.7749))
                                   )
                               )) as distance
                        UNION ALL
                        SELECT 'Oakland' as city_name,
                               111.045 * DEGREES(ACOS(
                                   LEAST(1.0, 
                                       COS(RADIANS(t.latitude)) * COS(RADIANS(37.8044)) * 
                                       COS(RADIANS(t.longitude) - RADIANS(-122.2712)) +
                                       SIN(RADIANS(t.latitude)) * SIN(RADIANS(37.8044))
                                   )
                               )) as distance
                        UNION ALL
                        SELECT 'Palo Alto' as city_name,
                               111.045 * DEGREES(ACOS(
                                   LEAST(1.0, 
                                       COS(RADIANS(t.latitude)) * COS(RADIANS(37.4419)) * 
                                       COS(RADIANS(t.longitude) - RADIANS(-122.1430)) +
                                       SIN(RADIANS(t.latitude)) * SIN(RADIANS(37.4419))
                                   )
                               )) as distance
                        UNION ALL
                        SELECT 'San Jose' as city_name,
                               111.045 * DEGREES(ACOS(
                                   LEAST(1.0, 
                                       COS(RADIANS(t.latitude)) * COS(RADIANS(37.3382)) * 
                                       COS(RADIANS(t.longitude) - RADIANS(-121.8863)) +
                                       SIN(RADIANS(t.latitude)) * SIN(RADIANS(37.3382))
                                   )
                               )) as distance
                    ) ORDER BY distance LIMIT 1)
                ELSE 'unknown'
            END as closest_major_city,
            
            -- Geographic region classification
            CASE 
                WHEN t.latitude IS NOT NULL AND t.longitude IS NOT NULL THEN
                    CASE 
                        -- San Francisco proper
                        WHEN t.latitude BETWEEN 37.70 AND 37.80 
                         AND t.longitude BETWEEN -122.52 AND -122.37
                        THEN 'san_francisco'
                        
                        -- East Bay (Oakland area)
                        WHEN t.latitude BETWEEN 37.70 AND 37.85 
                         AND t.longitude BETWEEN -122.35 AND -122.15
                        THEN 'east_bay'
                        
                        -- Peninsula (Palo Alto, Mountain View area)
                        WHEN t.latitude BETWEEN 37.35 AND 37.50 
                         AND t.longitude BETWEEN -122.20 AND -122.05
                        THEN 'peninsula'
                        
                        -- South Bay (San Jose area)
                        WHEN t.latitude BETWEEN 37.25 AND 37.45 
                         AND t.longitude BETWEEN -121.95 AND -121.75
                        THEN 'south_bay'
                        
                        -- North Bay
                        WHEN t.latitude BETWEEN 37.85 AND 38.35 
                         AND t.longitude BETWEEN -122.70 AND -122.30
                        THEN 'north_bay'
                        
                        ELSE 'other_bay_area'
                    END
                ELSE 'unknown_region'
            END as geographic_region,
            
            -- Coordinate precision assessment
            CASE 
                WHEN t.latitude IS NOT NULL AND t.longitude IS NOT NULL
                THEN
                    CASE 
                        WHEN t.latitude::VARCHAR LIKE '%._____%' 
                         AND t.longitude::VARCHAR LIKE '%._____%'
                        THEN 'high_precision'
                        WHEN t.latitude::VARCHAR LIKE '%.____%' 
                         AND t.longitude::VARCHAR LIKE '%.____%'
                        THEN 'medium_precision'
                        ELSE 'low_precision'
                    END
                ELSE 'no_coordinates'
            END as coordinate_precision,
            
            -- Distance to nearest major center (minimum of all distances)
            CASE 
                WHEN t.latitude IS NOT NULL AND t.longitude IS NOT NULL
                THEN LEAST(
                    111.045 * DEGREES(ACOS(LEAST(1.0, COS(RADIANS(t.latitude)) * COS(RADIANS(37.7749)) * COS(RADIANS(t.longitude) - RADIANS(-122.4194)) + SIN(RADIANS(t.latitude)) * SIN(RADIANS(37.7749))))),
                    111.045 * DEGREES(ACOS(LEAST(1.0, COS(RADIANS(t.latitude)) * COS(RADIANS(37.8044)) * COS(RADIANS(t.longitude) - RADIANS(-122.2712)) + SIN(RADIANS(t.latitude)) * SIN(RADIANS(37.8044))))),
                    111.045 * DEGREES(ACOS(LEAST(1.0, COS(RADIANS(t.latitude)) * COS(RADIANS(37.4419)) * COS(RADIANS(t.longitude) - RADIANS(-122.1430)) + SIN(RADIANS(t.latitude)) * SIN(RADIANS(37.4419))))),
                    111.045 * DEGREES(ACOS(LEAST(1.0, COS(RADIANS(t.latitude)) * COS(RADIANS(37.3382)) * COS(RADIANS(t.longitude) - RADIANS(-121.8863)) + SIN(RADIANS(t.latitude)) * SIN(RADIANS(37.3382)))))
                )
                ELSE NULL
            END as distance_to_nearest_center_km,
            
            -- Urban accessibility score (closer to centers = higher score)
            CASE 
                WHEN t.latitude IS NOT NULL AND t.longitude IS NOT NULL
                THEN 
                    GREATEST(0, LEAST(100, 
                        100 - (LEAST(
                            111.045 * DEGREES(ACOS(LEAST(1.0, COS(RADIANS(t.latitude)) * COS(RADIANS(37.7749)) * COS(RADIANS(t.longitude) - RADIANS(-122.4194)) + SIN(RADIANS(t.latitude)) * SIN(RADIANS(37.7749))))),
                            111.045 * DEGREES(ACOS(LEAST(1.0, COS(RADIANS(t.latitude)) * COS(RADIANS(37.8044)) * COS(RADIANS(t.longitude) - RADIANS(-122.2712)) + SIN(RADIANS(t.latitude)) * SIN(RADIANS(37.8044))))),
                            111.045 * DEGREES(ACOS(LEAST(1.0, COS(RADIANS(t.latitude)) * COS(RADIANS(37.4419)) * COS(RADIANS(t.longitude) - RADIANS(-122.1430)) + SIN(RADIANS(t.latitude)) * SIN(RADIANS(37.4419))))),
                            111.045 * DEGREES(ACOS(LEAST(1.0, COS(RADIANS(t.latitude)) * COS(RADIANS(37.3382)) * COS(RADIANS(t.longitude) - RADIANS(-121.8863)) + SIN(RADIANS(t.latitude)) * SIN(RADIANS(37.3382)))))
                        ) * 2)
                    ))::INTEGER
                ELSE 0
            END as urban_accessibility_score,
            
            -- Geographic enrichment metadata
            CURRENT_TIMESTAMP as geo_enriched_at,
            'geographic_enrichment_v1.0' as geo_processing_version
            
        FROM {input_table} t
        """
    
    def validate_input(self, table_name: str) -> bool:
        """Validate input data for geographic enrichment."""
        if not self.connection:
            return False
        
        try:
            # Check table exists and has data
            count = self.count_records(table_name)
            if count == 0:
                self.logger.error(f"Input table {table_name} is empty")
                return False
            
            # Check for latitude and longitude columns
            schema = self.get_table_schema(table_name)
            if 'latitude' not in schema or 'longitude' not in schema:
                self.logger.warning("Missing latitude or longitude columns for geographic enrichment")
                # Not a hard failure - we can still process other fields
                return True
            
            # Check how many records have valid coordinates
            valid_coords_query = f"""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN t.latitude IS NOT NULL AND t.longitude IS NOT NULL THEN 1 END) as with_coords
            FROM {table_name} t
            """
            
            result = self.execute_sql(valid_coords_query).fetchone()
            if result:
                total, with_coords = result
                coord_rate = with_coords / total if total > 0 else 0
                self.logger.info(f"Records with valid coordinates: {with_coords}/{total} ({coord_rate:.1%})")
                
                if coord_rate < 0.5:
                    self.logger.warning("Less than 50% of records have valid coordinates")
            
            self.logger.success(f"Geographic input validation passed for {table_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Geographic input validation failed: {e}")
            return False
    
    def validate_output(self, table_name: str) -> bool:
        """Validate geographic enrichment output."""
        if not self.connection:
            return False
        
        try:
            total_records = self.count_records(table_name)
            if total_records == 0:
                self.logger.error("No records in geographic output")
                return False
            
            # Check enrichment completeness
            enrichment_query = f"""
            SELECT 
                COUNT(*) as total_records,
                COUNT(distance_to_sf_downtown_km) as has_sf_distance,
                COUNT(closest_major_city) as has_closest_city,
                COUNT(geographic_region) as has_region,
                COUNT(CASE WHEN geographic_region != 'unknown_region' THEN 1 END) as valid_regions,
                AVG(urban_accessibility_score) as avg_accessibility
            FROM {table_name}
            """
            
            result = self.execute_sql(enrichment_query).fetchone()
            if result:
                (total, has_sf_dist, has_closest, has_region, 
                 valid_regions, avg_access) = result
                
                # Calculate enrichment metrics
                geo_completeness = valid_regions / total if total > 0 else 0
                self.metrics.update({
                    "records_processed": total,
                    "coordinates_enriched": has_sf_dist or 0,
                    "distances_calculated": (has_sf_dist or 0) * 4,  # 4 distance calculations per record
                    "geographic_completeness": geo_completeness
                })
                
                # Log enrichment metrics
                self.logger.info(f"Geographic completeness: {geo_completeness:.2%}")
                self.logger.info(f"Records with distance calculations: {has_sf_dist}/{total}")
                self.logger.info(f"Records with valid regions: {valid_regions}/{total}")
                self.logger.info(f"Average urban accessibility score: {avg_access:.1f}")
                
            self.logger.success(f"Geographic output validation passed for {table_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Geographic output validation failed: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get geographic enrichment metrics."""
        return self.metrics.copy()