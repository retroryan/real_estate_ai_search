"""Cross-entity enrichment processor for joining and enriching data across entities.

This processor handles cross-entity joins and enrichments, working with nested
structures preserved throughout the pipeline.

Tier: Cross-tier (typically Silver or Gold)
Entity: Multiple (Properties, Neighborhoods, Wikipedia)
Purpose: Entity relationship enrichment and aggregation
"""

import duckdb
from typing import Optional, Dict, Any

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.models.duckdb_models import TableIdentifier
from squack_pipeline.utils.logging import PipelineLogger


class CrossEntityEnrichmentProcessor:
    """Processor for cross-entity enrichment using SQL joins.
    
    Enriches entities by:
    - Joining properties with neighborhoods using neighborhood_id
    - Enriching properties with nearby Wikipedia articles using geo-proximity
    - Creating neighborhood-level aggregates from property data
    
    Preserves nested structures while adding enrichment fields.
    """
    
    def __init__(self, settings: PipelineSettings):
        """Initialize cross-entity enrichment processor."""
        self.settings = settings
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        self.connection: Optional[duckdb.DuckDBPyConnection] = None
    
    def set_connection(self, connection: duckdb.DuckDBPyConnection) -> None:
        """Set the DuckDB connection for the processor."""
        self.connection = connection
        self.logger.debug("DuckDB connection established for cross-entity enrichment")
    
    def enrich_properties_with_neighborhoods(
        self, 
        properties_table: str, 
        neighborhoods_table: str,
        output_table: str = "properties_enriched"
    ) -> str:
        """Enrich properties with neighborhood data using neighborhood_id join."""
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
        
        # Create validated table identifiers
        props = TableIdentifier(name=properties_table)
        hoods = TableIdentifier(name=neighborhoods_table)
        output = TableIdentifier(name=output_table)
        
        self.logger.info(f"Enriching properties with neighborhood data: {properties_table} + {neighborhoods_table}")
        
        # Drop existing output table if exists
        self.connection.execute(f"DROP TABLE IF EXISTS {output.qualified_name}")
        
        # Create enriched table with property-neighborhood join
        enrichment_query = f"""
        CREATE TABLE {output.qualified_name} AS
        SELECT 
            p.*,
            n.name as neighborhood_name,
            n.walkability_score as neighborhood_walkability,
            n.transit_score as neighborhood_transit,
            n.school_rating as neighborhood_school_rating,
            n.median_household_income as neighborhood_median_income,
            n.population as neighborhood_population,
            n.characteristics as neighborhood_characteristics,
            n.demographics as neighborhood_demographics
        FROM {props.qualified_name} p
        LEFT JOIN {hoods.qualified_name} n
        ON p.neighborhood_id = n.neighborhood_id
        """
        
        self.connection.execute(enrichment_query)
        
        # Log statistics
        total_count = self.connection.execute(f"SELECT COUNT(*) FROM {output.qualified_name}").fetchone()[0]
        matched_count = self.connection.execute(
            f"SELECT COUNT(*) FROM {output.qualified_name} WHERE neighborhood_name IS NOT NULL"
        ).fetchone()[0]
        
        match_rate = (matched_count / total_count * 100) if total_count > 0 else 0
        self.logger.success(
            f"Created enriched properties table with {total_count} records "
            f"({matched_count} matched to neighborhoods, {match_rate:.1f}%)"
        )
        
        return output_table
    
    def enrich_with_geographic_proximity(
        self,
        properties_table: str,
        wikipedia_table: str,
        output_table: str = "properties_wiki_enriched",
        max_distance_km: float = 5.0
    ) -> str:
        """Enrich properties with nearby Wikipedia articles based on geographic proximity."""
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
        
        # Create validated table identifiers
        props = TableIdentifier(name=properties_table)
        wiki = TableIdentifier(name=wikipedia_table)
        output = TableIdentifier(name=output_table)
        
        self.logger.info(f"Enriching properties with nearby Wikipedia articles (within {max_distance_km}km)")
        
        # Drop existing output table if exists
        self.connection.execute(f"DROP TABLE IF EXISTS {output.qualified_name}")
        
        # Create enriched table with geographic proximity join
        # Using simplified distance calculation (good enough for small distances)
        enrichment_query = f"""
        CREATE TABLE {output.qualified_name} AS
        WITH wiki_nearby AS (
            SELECT 
                p.listing_id,
                w.id as wiki_id,
                w.title as wiki_title,
                w.relevance_score as wiki_relevance,
                w.relevance_category as wiki_relevance_category,
                -- Simplified distance calculation (km) using nested coordinates
                SQRT(
                    POW((p.coordinates.latitude - w.latitude) * 111.0, 2) + 
                    POW((p.coordinates.longitude - w.longitude) * 111.0 * COS(RADIANS(p.coordinates.latitude)), 2)
                ) as distance_km
            FROM {props.qualified_name} p
            CROSS JOIN {wiki.qualified_name} w
            WHERE w.latitude IS NOT NULL 
            AND w.longitude IS NOT NULL
            AND p.coordinates.latitude IS NOT NULL
            AND p.coordinates.longitude IS NOT NULL
            AND ABS(p.coordinates.latitude - w.latitude) < 0.1  -- Pre-filter for performance
            AND ABS(p.coordinates.longitude - w.longitude) < 0.1
        )
        SELECT 
            p.*,
            wn.wiki_title as nearest_wiki_article,
            wn.wiki_relevance as nearest_wiki_relevance,
            wn.distance_km as nearest_wiki_distance_km
        FROM {props.qualified_name} p
        LEFT JOIN (
            SELECT DISTINCT ON (listing_id)
                listing_id,
                wiki_title,
                wiki_relevance,
                distance_km
            FROM wiki_nearby
            WHERE distance_km <= {max_distance_km}
            ORDER BY listing_id, wiki_relevance DESC, distance_km ASC
        ) wn ON p.listing_id = wn.listing_id
        """
        
        self.connection.execute(enrichment_query)
        
        # Log statistics
        total_count = self.connection.execute(f"SELECT COUNT(*) FROM {output.qualified_name}").fetchone()[0]
        matched_count = self.connection.execute(
            f"SELECT COUNT(*) FROM {output.qualified_name} WHERE nearest_wiki_article IS NOT NULL"
        ).fetchone()[0]
        
        match_rate = (matched_count / total_count * 100) if total_count > 0 else 0
        self.logger.success(
            f"Created wiki-enriched properties table with {total_count} records "
            f"({matched_count} matched to Wikipedia articles, {match_rate:.1f}%)"
        )
        
        return output_table
    
    def create_neighborhood_aggregates(
        self,
        properties_table: str,
        output_table: str = "neighborhood_stats"
    ) -> str:
        """Create neighborhood-level aggregates from property data."""
        if not self.connection:
            raise RuntimeError("No DuckDB connection available")
        
        # Create validated table identifiers
        props = TableIdentifier(name=properties_table)
        output = TableIdentifier(name=output_table)
        
        self.logger.info("Creating neighborhood aggregate statistics")
        
        # Drop existing output table if exists
        self.connection.execute(f"DROP TABLE IF EXISTS {output.qualified_name}")
        
        # Create aggregates table
        aggregates_query = f"""
        CREATE TABLE {output.qualified_name} AS
        SELECT 
            neighborhood_id,
            MAX(neighborhood_name) as neighborhood_name,
            COUNT(*) as property_count,
            AVG(listing_price) as avg_price,
            MEDIAN(listing_price) as median_price,
            MIN(listing_price) as min_price,
            MAX(listing_price) as max_price,
            AVG(price_per_sqft) as avg_price_per_sqft,
            AVG(property_details.bedrooms) as avg_bedrooms,
            AVG(property_details.bathrooms) as avg_bathrooms,
            AVG(property_details.square_feet) as avg_sqft,
            COUNT(DISTINCT property_details.property_type) as property_type_variety,
            MODE(property_details.property_type) as most_common_property_type
        FROM {props.qualified_name}
        WHERE neighborhood_id IS NOT NULL
        GROUP BY neighborhood_id
        ORDER BY property_count DESC
        """
        
        self.connection.execute(aggregates_query)
        
        # Log statistics
        count = self.connection.execute(f"SELECT COUNT(*) FROM {output.qualified_name}").fetchone()[0]
        self.logger.success(f"Created neighborhood statistics for {count} neighborhoods")
        
        return output_table
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get enrichment metrics."""
        if not self.connection:
            return {}
        
        metrics = {}
        
        # Check for enriched tables and get counts
        tables_to_check = [
            "properties_enriched",
            "properties_wiki_enriched", 
            "neighborhood_stats"
        ]
        
        for table in tables_to_check:
            try:
                count = self.connection.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
                metrics[f"{table}_count"] = count
            except:
                metrics[f"{table}_count"] = 0
        
        return metrics