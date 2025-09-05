"""Gold layer enrichment utilities for neighborhood-based enhancements.

This module provides utilities for enriching Gold layer views with neighborhood-based
business logic, following DuckDB best practices and clean architecture principles.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class NeighborhoodSearchFacets(BaseModel):
    """Configuration for neighborhood-based search facets."""
    
    has_neighborhood: str = Field(
        default="has_neighborhood",
        description="Facet for articles with neighborhood associations"
    )
    no_neighborhood: str = Field(
        default="no_neighborhood", 
        description="Facet for articles without neighborhood associations"
    )
    multi_neighborhood: str = Field(
        default="multi_neighborhood",
        description="Facet for articles with multiple neighborhoods"
    )


class NeighborhoodQualityBoost(BaseModel):
    """Configuration for quality score boosting based on neighborhood presence."""
    
    has_neighborhood_boost: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Quality score boost for articles with neighborhood"
    )
    multi_neighborhood_boost: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Additional boost for multiple neighborhoods"
    )
    weight_in_ranking: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Weight of neighborhood presence in search ranking"
    )


class GoldNeighborhoodEnricher:
    """Handles neighborhood-based enrichments for Gold layer views.
    
    This class provides SQL fragments and expressions for enriching
    Gold layer views with neighborhood-based business logic.
    """
    
    def __init__(
        self,
        facets_config: Optional[NeighborhoodSearchFacets] = None,
        quality_config: Optional[NeighborhoodQualityBoost] = None
    ):
        """Initialize the Gold layer enricher.
        
        Args:
            facets_config: Configuration for search facets
            quality_config: Configuration for quality scoring
        """
        self.facets = facets_config or NeighborhoodSearchFacets()
        self.quality = quality_config or NeighborhoodQualityBoost()
    
    def get_neighborhood_facet_sql(self) -> str:
        """Generate SQL expression for neighborhood-based search facets.
        
        Returns:
            SQL CASE expression for neighborhood facets
        """
        return f"""
            CASE 
                WHEN neighborhood_names IS NOT NULL AND array_length(neighborhood_names) > 1 
                    THEN '{self.facets.multi_neighborhood}'
                WHEN neighborhood_names IS NOT NULL AND array_length(neighborhood_names) = 1 
                    THEN '{self.facets.has_neighborhood}'
                ELSE '{self.facets.no_neighborhood}'
            END
        """
    
    def get_neighborhood_quality_boost_sql(self) -> str:
        """Generate SQL expression for neighborhood-based quality boost.
        
        Returns:
            SQL expression for quality score boost
        """
        base_boost = self.quality.has_neighborhood_boost
        multi_boost = self.quality.multi_neighborhood_boost
        
        return f"""
            CASE 
                WHEN neighborhood_names IS NOT NULL AND array_length(neighborhood_names) > 1 
                    THEN {base_boost + multi_boost}
                WHEN neighborhood_names IS NOT NULL AND array_length(neighborhood_names) >= 1 
                    THEN {base_boost}
                ELSE 0.0
            END
        """
    
    def get_enhanced_quality_score_sql(self, base_score_expr: str) -> str:
        """Generate SQL for enhanced quality score including neighborhood boost.
        
        Args:
            base_score_expr: SQL expression for base quality score
            
        Returns:
            SQL expression for enhanced quality score
        """
        boost_sql = self.get_neighborhood_quality_boost_sql()
        
        return f"""
            CAST((
                {base_score_expr} + {boost_sql}
            ) AS FLOAT)
        """
    
    def get_neighborhood_ranking_component_sql(self) -> str:
        """Generate SQL for neighborhood component in search ranking.
        
        Returns:
            SQL expression for neighborhood ranking component
        """
        weight = self.quality.weight_in_ranking
        
        return f"""
            (CASE 
                WHEN neighborhood_names IS NOT NULL AND array_length(neighborhood_names) > 0
                    THEN {weight}
                ELSE 0.0
            END)
        """
    
    def get_neighborhood_metadata_sql(self) -> str:
        """Generate SQL for neighborhood metadata fields.
        
        Returns:
            SQL expressions for neighborhood metadata
        """
        return """
            -- Neighborhood count for analytics
            CASE 
                WHEN neighborhood_names IS NOT NULL 
                    THEN array_length(neighborhood_names)
                ELSE 0
            END as neighborhood_count,
            
            -- Neighborhood association flag
            CASE 
                WHEN neighborhood_names IS NOT NULL AND array_length(neighborhood_names) > 0
                    THEN true
                ELSE false
            END as has_neighborhood_association
        """
    
    def get_enriched_search_facets_sql(self, existing_facets: List[str]) -> str:
        """Generate SQL for search facets including neighborhood facets.
        
        Args:
            existing_facets: List of existing facet SQL expressions
            
        Returns:
            SQL array expression with all facets
        """
        # Add neighborhood facet to existing facets
        all_facets = existing_facets + [self.get_neighborhood_facet_sql()]
        
        # Format as SQL array
        facets_sql = ",\n                    ".join(all_facets)
        
        return f"""
                ARRAY[
                    {facets_sql}
                ]"""
    
    def get_neighborhood_fields_projection(self) -> str:
        """Get SQL projection for neighborhood fields from Silver layer.
        
        Returns:
            SQL expressions for selecting neighborhood fields
        """
        return """
                -- Neighborhood fields from Silver layer
                neighborhood_ids,
                neighborhood_names,
                primary_neighborhood_name,"""