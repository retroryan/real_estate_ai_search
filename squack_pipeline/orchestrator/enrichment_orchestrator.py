"""Cross-entity enrichment orchestrator for post-Gold processing."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import duckdb

from squack_pipeline.models import EntityType, MedallionTier
from squack_pipeline.models.pipeline_models import ProcessedTable
from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.loaders.connection import DuckDBConnectionManager
from squack_pipeline.utils.logging import PipelineLogger


class EnrichmentResult(BaseModel):
    """Result of a cross-entity enrichment operation."""
    
    source_entity: EntityType = Field(
        ...,
        description="Primary entity that was enriched"
    )
    
    enrichment_entity: EntityType = Field(
        ...,
        description="Entity used for enrichment"
    )
    
    enriched_table: str = Field(
        ...,
        description="Name of the enriched table created"
    )
    
    records_enriched: int = Field(
        default=0,
        ge=0,
        description="Number of records successfully enriched"
    )
    
    records_failed: int = Field(
        default=0,
        ge=0,
        description="Number of records that failed enrichment"
    )
    
    enrichment_fields: List[str] = Field(
        default_factory=list,
        description="Fields added during enrichment"
    )


class EnrichmentOrchestrator:
    """Orchestrator for cross-entity enrichment after Gold tier processing.
    
    This orchestrator handles enrichment operations that require data from
    multiple entity types, such as:
    - Enriching properties with neighborhood demographics
    - Adding Wikipedia context to properties and neighborhoods
    - Computing cross-entity relationships and metrics
    """
    
    def __init__(
        self,
        settings: PipelineSettings,
        connection_manager: DuckDBConnectionManager
    ):
        """Initialize the enrichment orchestrator.
        
        Args:
            settings: Pipeline settings
            connection_manager: DuckDB connection manager
        """
        self.settings = settings
        self.connection_manager = connection_manager
        self.connection = connection_manager.get_connection()
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        self.results: List[EnrichmentResult] = []
    
    def enrich_all(
        self,
        gold_tables: Dict[EntityType, ProcessedTable]
    ) -> List[EnrichmentResult]:
        """Run all applicable cross-entity enrichments.
        
        Args:
            gold_tables: Dictionary of Gold tier tables by entity type
            
        Returns:
            List of enrichment results
        """
        self.results = []
        
        # Property-Neighborhood enrichment
        if (EntityType.PROPERTY in gold_tables and 
            EntityType.NEIGHBORHOOD in gold_tables):
            result = self.enrich_properties_with_neighborhoods(
                gold_tables[EntityType.PROPERTY],
                gold_tables[EntityType.NEIGHBORHOOD]
            )
            if result:
                self.results.append(result)
        
        # Property-Wikipedia enrichment
        if (EntityType.PROPERTY in gold_tables and 
            EntityType.WIKIPEDIA in gold_tables):
            result = self.enrich_properties_with_wikipedia(
                gold_tables[EntityType.PROPERTY],
                gold_tables[EntityType.WIKIPEDIA]
            )
            if result:
                self.results.append(result)
        
        # Neighborhood-Wikipedia enrichment
        if (EntityType.NEIGHBORHOOD in gold_tables and 
            EntityType.WIKIPEDIA in gold_tables):
            result = self.enrich_neighborhoods_with_wikipedia(
                gold_tables[EntityType.NEIGHBORHOOD],
                gold_tables[EntityType.WIKIPEDIA]
            )
            if result:
                self.results.append(result)
        
        # Log summary
        self._log_enrichment_summary()
        
        return self.results
    
    def enrich_properties_with_neighborhoods(
        self,
        property_table: ProcessedTable,
        neighborhood_table: ProcessedTable
    ) -> Optional[EnrichmentResult]:
        """Enrich properties with neighborhood demographic data.
        
        Args:
            property_table: Gold tier property table
            neighborhood_table: Gold tier neighborhood table
            
        Returns:
            EnrichmentResult or None if enrichment fails
        """
        try:
            self.logger.info(
                f"Enriching properties from {property_table.table_name} "
                f"with neighborhoods from {neighborhood_table.table_name}"
            )
            
            enriched_table = f"enriched_properties_neighborhoods_{property_table.timestamp}"
            
            # Create enriched table with neighborhood data
            query = f"""
            CREATE OR REPLACE TABLE {enriched_table} AS
            SELECT 
                p.*,
                n.name as neighborhood_name,
                n.description as neighborhood_description,
                n.demographics as neighborhood_demographics,
                n.statistics as neighborhood_statistics,
                n.amenities as neighborhood_amenities,
                n.schools as neighborhood_schools,
                n.walkability_score as neighborhood_walkability_score,
                n.crime_rate as neighborhood_crime_rate,
                n.avg_home_value as neighborhood_avg_home_value,
                n.avg_rent as neighborhood_avg_rent
            FROM {property_table.table_name} p
            LEFT JOIN {neighborhood_table.table_name} n
                ON p.neighborhood_id = n.neighborhood_id
            """
            
            self.connection.execute(query)
            
            # Count enriched records
            count_query = f"""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN neighborhood_name IS NOT NULL THEN 1 END) as enriched
            FROM {enriched_table}
            """
            result = self.connection.execute(count_query).fetchone()
            total_records = result[0]
            enriched_records = result[1]
            failed_records = total_records - enriched_records
            
            self.logger.info(
                f"Property-Neighborhood enrichment complete: "
                f"{enriched_records}/{total_records} records enriched"
            )
            
            return EnrichmentResult(
                source_entity=EntityType.PROPERTY,
                enrichment_entity=EntityType.NEIGHBORHOOD,
                enriched_table=enriched_table,
                records_enriched=enriched_records,
                records_failed=failed_records,
                enrichment_fields=[
                    "neighborhood_name", "neighborhood_description",
                    "neighborhood_demographics", "neighborhood_statistics",
                    "neighborhood_amenities", "neighborhood_schools",
                    "neighborhood_walkability_score", "neighborhood_crime_rate",
                    "neighborhood_avg_home_value", "neighborhood_avg_rent"
                ]
            )
            
        except Exception as e:
            self.logger.error(f"Failed to enrich properties with neighborhoods: {e}")
            return None
    
    def enrich_properties_with_wikipedia(
        self,
        property_table: ProcessedTable,
        wikipedia_table: ProcessedTable
    ) -> Optional[EnrichmentResult]:
        """Enrich properties with relevant Wikipedia articles.
        
        Args:
            property_table: Gold tier property table
            wikipedia_table: Gold tier Wikipedia table
            
        Returns:
            EnrichmentResult or None if enrichment fails
        """
        try:
            self.logger.info(
                f"Enriching properties from {property_table.table_name} "
                f"with Wikipedia from {wikipedia_table.table_name}"
            )
            
            enriched_table = f"enriched_properties_wikipedia_{property_table.timestamp}"
            
            # Create enriched table with Wikipedia context
            # Match based on city/location relevance
            query = f"""
            CREATE OR REPLACE TABLE {enriched_table} AS
            WITH ranked_wiki AS (
                SELECT 
                    w.*,
                    p.listing_id,
                    ROW_NUMBER() OVER (
                        PARTITION BY p.listing_id 
                        ORDER BY w.relevance_score DESC
                    ) as rank
                FROM {property_table.table_name} p
                LEFT JOIN {wikipedia_table.table_name} w
                    ON w.city_relevance = p.address.city
                    OR w.location_context ILIKE '%' || p.address.city || '%'
            )
            SELECT 
                p.*,
                ARRAY_AGG(
                    STRUCT(
                        rw.page_id as wiki_page_id,
                        rw.title as wiki_title,
                        rw.summary as wiki_summary,
                        rw.relevance_score as wiki_relevance
                    ) ORDER BY rw.rank
                ) FILTER (WHERE rw.page_id IS NOT NULL AND rw.rank <= 3) 
                    as wikipedia_context
            FROM {property_table.table_name} p
            LEFT JOIN ranked_wiki rw ON p.listing_id = rw.listing_id
            GROUP BY p.*
            """
            
            self.connection.execute(query)
            
            # Count enriched records
            count_query = f"""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN wikipedia_context IS NOT NULL THEN 1 END) as enriched
            FROM {enriched_table}
            """
            result = self.connection.execute(count_query).fetchone()
            total_records = result[0]
            enriched_records = result[1]
            failed_records = total_records - enriched_records
            
            self.logger.info(
                f"Property-Wikipedia enrichment complete: "
                f"{enriched_records}/{total_records} records enriched"
            )
            
            return EnrichmentResult(
                source_entity=EntityType.PROPERTY,
                enrichment_entity=EntityType.WIKIPEDIA,
                enriched_table=enriched_table,
                records_enriched=enriched_records,
                records_failed=failed_records,
                enrichment_fields=["wikipedia_context"]
            )
            
        except Exception as e:
            self.logger.error(f"Failed to enrich properties with Wikipedia: {e}")
            return None
    
    def enrich_neighborhoods_with_wikipedia(
        self,
        neighborhood_table: ProcessedTable,
        wikipedia_table: ProcessedTable
    ) -> Optional[EnrichmentResult]:
        """Enrich neighborhoods with relevant Wikipedia articles.
        
        Args:
            neighborhood_table: Gold tier neighborhood table
            wikipedia_table: Gold tier Wikipedia table
            
        Returns:
            EnrichmentResult or None if enrichment fails
        """
        try:
            self.logger.info(
                f"Enriching neighborhoods from {neighborhood_table.table_name} "
                f"with Wikipedia from {wikipedia_table.table_name}"
            )
            
            enriched_table = f"enriched_neighborhoods_wikipedia_{neighborhood_table.timestamp}"
            
            # Create enriched table with Wikipedia context
            query = f"""
            CREATE OR REPLACE TABLE {enriched_table} AS
            WITH ranked_wiki AS (
                SELECT 
                    w.*,
                    n.neighborhood_id,
                    ROW_NUMBER() OVER (
                        PARTITION BY n.neighborhood_id 
                        ORDER BY w.relevance_score DESC
                    ) as rank
                FROM {neighborhood_table.table_name} n
                LEFT JOIN {wikipedia_table.table_name} w
                    ON w.city_relevance = n.city
                    OR w.location_context ILIKE '%' || n.name || '%'
                    OR w.title ILIKE '%' || n.name || '%'
            )
            SELECT 
                n.*,
                ARRAY_AGG(
                    STRUCT(
                        rw.page_id as wiki_page_id,
                        rw.title as wiki_title,
                        rw.summary as wiki_summary,
                        rw.categories as wiki_categories,
                        rw.relevance_score as wiki_relevance
                    ) ORDER BY rw.rank
                ) FILTER (WHERE rw.page_id IS NOT NULL AND rw.rank <= 5) 
                    as wikipedia_articles
            FROM {neighborhood_table.table_name} n
            LEFT JOIN ranked_wiki rw ON n.neighborhood_id = rw.neighborhood_id
            GROUP BY n.*
            """
            
            self.connection.execute(query)
            
            # Count enriched records
            count_query = f"""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN wikipedia_articles IS NOT NULL THEN 1 END) as enriched
            FROM {enriched_table}
            """
            result = self.connection.execute(count_query).fetchone()
            total_records = result[0]
            enriched_records = result[1]
            failed_records = total_records - enriched_records
            
            self.logger.info(
                f"Neighborhood-Wikipedia enrichment complete: "
                f"{enriched_records}/{total_records} records enriched"
            )
            
            return EnrichmentResult(
                source_entity=EntityType.NEIGHBORHOOD,
                enrichment_entity=EntityType.WIKIPEDIA,
                enriched_table=enriched_table,
                records_enriched=enriched_records,
                records_failed=failed_records,
                enrichment_fields=["wikipedia_articles"]
            )
            
        except Exception as e:
            self.logger.error(f"Failed to enrich neighborhoods with Wikipedia: {e}")
            return None
    
    def _log_enrichment_summary(self) -> None:
        """Log a summary of all enrichment operations."""
        if not self.results:
            self.logger.info("No enrichment operations were performed")
            return
        
        self.logger.info("=" * 60)
        self.logger.info("Cross-Entity Enrichment Summary:")
        self.logger.info("=" * 60)
        
        for result in self.results:
            success_rate = (
                result.records_enriched / (result.records_enriched + result.records_failed) * 100
                if (result.records_enriched + result.records_failed) > 0
                else 0
            )
            
            self.logger.info(
                f"  {result.source_entity.value} + {result.enrichment_entity.value}:"
            )
            self.logger.info(f"    Table: {result.enriched_table}")
            self.logger.info(f"    Success Rate: {success_rate:.1f}%")
            self.logger.info(
                f"    Records: {result.records_enriched} enriched, "
                f"{result.records_failed} failed"
            )
            self.logger.info(
                f"    Fields Added: {', '.join(result.enrichment_fields[:3])}"
                f"{' ...' if len(result.enrichment_fields) > 3 else ''}"
            )
        
        self.logger.info("=" * 60)