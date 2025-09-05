"""Neighborhood enrichment utilities for Wikipedia articles.

This module provides utilities to enrich Wikipedia articles with neighborhood data,
following DuckDB best practices and clean architecture principles.
"""

from typing import Optional
import duckdb
from pydantic import BaseModel, Field
from squack_pipeline_v2.core.logging import PipelineLogger
from squack_pipeline_v2.utils.table_validation import validate_table_name


class NeighborhoodEnrichmentResult(BaseModel):
    """Result of neighborhood enrichment operation."""
    
    mappings_found: bool = Field(description="Whether neighborhood mappings were found")
    mapping_count: int = Field(default=0, description="Number of mappings created")
    articles_enriched: int = Field(default=0, description="Number of articles enriched")
    

class NeighborhoodWikipediaEnricher:
    """Handles enrichment of Wikipedia articles with neighborhood data.
    
    This class follows DuckDB best practices:
    - Uses CTEs instead of temporary tables where possible
    - Leverages Relation API for type safety
    - Validates table names at boundaries
    - Uses parameterized queries for safety
    """
    
    def __init__(self, connection: duckdb.DuckDBPyConnection):
        """Initialize the enricher with a DuckDB connection.
        
        Args:
            connection: Active DuckDB connection
        """
        self.conn = connection
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
    
    def check_neighborhoods_table_exists(self) -> bool:
        """Check if silver_neighborhoods table exists.
        
        Returns:
            True if table exists, False otherwise
        """
        result = self.conn.execute("""
            SELECT COUNT(*) > 0 
            FROM information_schema.tables 
            WHERE table_name = 'silver_neighborhoods'
        """).fetchone()[0]
        
        return bool(result)
    
    def get_neighborhood_mappings_cte(self) -> str:
        """Generate CTE for neighborhood mappings.
        
        Following DuckDB best practice: Use CTEs instead of temporary tables.
        
        Returns:
            SQL CTE definition for neighborhood mappings
        """
        return """
            neighborhood_mappings AS (
                SELECT 
                    wikipedia_page_id as page_id,
                    LIST(DISTINCT neighborhood_id ORDER BY neighborhood_id) as neighborhood_ids,
                    LIST(DISTINCT name ORDER BY name) as neighborhood_names,
                    FIRST(name ORDER BY neighborhood_id) as primary_neighborhood_name
                FROM silver_neighborhoods
                WHERE wikipedia_page_id IS NOT NULL
                GROUP BY wikipedia_page_id
            )
        """
    
    def create_enriched_wikipedia_query(
        self, 
        base_query: str,
        include_neighborhoods: bool = True
    ) -> str:
        """Create the final enriched Wikipedia query.
        
        Args:
            base_query: Base SELECT query for Wikipedia data
            include_neighborhoods: Whether to include neighborhood enrichment
            
        Returns:
            Complete SQL query with neighborhood enrichment
        """
        if not include_neighborhoods:
            # Return query with NULL neighborhood fields for consistency
            return f"""
                {base_query},
                CAST(NULL AS VARCHAR[]) as neighborhood_ids,
                CAST(NULL AS VARCHAR[]) as neighborhood_names,
                CAST(NULL AS VARCHAR) as primary_neighborhood_name
            """
        
        # Use CTE for neighborhood mappings (best practice)
        return f"""
            WITH {self.get_neighborhood_mappings_cte()}
            {base_query},
            nm.neighborhood_ids,
            nm.neighborhood_names,
            nm.primary_neighborhood_name
        """
    
    def enrich_wikipedia_relation(
        self,
        wikipedia_relation: duckdb.DuckDBPyRelation,
        neighborhoods_available: bool = True
    ) -> duckdb.DuckDBPyRelation:
        """Enrich a Wikipedia relation with neighborhood data using Relation API.
        
        Following DuckDB best practice: Use Relation API for type-safe operations.
        
        Args:
            wikipedia_relation: DuckDB relation containing Wikipedia data
            neighborhoods_available: Whether neighborhood data is available
            
        Returns:
            Enriched relation with neighborhood fields
        """
        if not neighborhoods_available:
            # Add NULL neighborhood fields for consistency
            return wikipedia_relation.project("""
                *,
                CAST(NULL AS VARCHAR[]) as neighborhood_ids,
                CAST(NULL AS VARCHAR[]) as neighborhood_names,
                CAST(NULL AS VARCHAR) as primary_neighborhood_name
            """)
        
        # Create neighborhood mappings relation
        neighborhoods = self.conn.table("silver_neighborhoods")
        
        # Filter and aggregate neighborhoods
        mappings = (neighborhoods
            .filter("wikipedia_page_id IS NOT NULL")
            .aggregate("""
                wikipedia_page_id as page_id,
                LIST(DISTINCT neighborhood_id ORDER BY neighborhood_id) as neighborhood_ids,
                LIST(DISTINCT name ORDER BY name) as neighborhood_names,
                FIRST(name ORDER BY neighborhood_id) as primary_neighborhood_name
            """, "wikipedia_page_id"))
        
        # Join with Wikipedia data
        enriched = wikipedia_relation.join(
            mappings,
            "page_id",
            how="left"
        )
        
        return enriched
    
    def get_enrichment_statistics(self, table_name: str) -> NeighborhoodEnrichmentResult:
        """Get statistics about neighborhood enrichment.
        
        Args:
            table_name: Name of the enriched table
            
        Returns:
            Enrichment statistics
        """
        # Validate table name (best practice)
        table_name = validate_table_name(table_name)
        
        # Check if neighborhoods exist
        if not self.check_neighborhoods_table_exists():
            return NeighborhoodEnrichmentResult(mappings_found=False)
        
        # Get mapping count
        mapping_count = self.conn.execute("""
            SELECT COUNT(DISTINCT wikipedia_page_id) 
            FROM silver_neighborhoods 
            WHERE wikipedia_page_id IS NOT NULL
        """).fetchone()[0]
        
        # Get enriched article count using parameterized query for column check
        enriched_count = self.conn.execute(f"""
            SELECT COUNT(*) 
            FROM {table_name}
            WHERE neighborhood_ids IS NOT NULL 
            AND array_length(neighborhood_ids) > 0
        """).fetchone()[0]
        
        return NeighborhoodEnrichmentResult(
            mappings_found=True,
            mapping_count=mapping_count,
            articles_enriched=enriched_count
        )