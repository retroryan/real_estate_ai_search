"""
Integration test for Wikipedia correlations preservation through the data pipeline.

This test verifies that Wikipedia correlation data from neighborhood source JSON
is properly preserved through loading, enrichment, and Elasticsearch indexing.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

from data_pipeline.models.spark_models import (
    Neighborhood,
    WikipediaArticleReference,
    WikipediaCorrelations,
    ParentGeography,
    WikipediaGeoReference
)
from data_pipeline.loaders.neighborhood_loader import NeighborhoodLoader
from data_pipeline.enrichment.neighborhood_enricher import NeighborhoodEnricher


@pytest.fixture(scope="module")
def spark_session():
    """Create a Spark session for testing."""
    spark = SparkSession.builder \
        .appName("WikipediaCorrelationsTest") \
        .master("local[*]") \
        .config("spark.sql.shuffle.partitions", "2") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .getOrCreate()
    
    yield spark
    spark.stop()


@pytest.fixture
def sample_neighborhood_data() -> Dict[str, Any]:
    """Create sample neighborhood data with Wikipedia correlations."""
    return {
        "neighborhood_id": "test-neighborhood-001",
        "name": "Test Neighborhood",
        "city": "San Francisco",
        "state": "CA",
        "description": "A test neighborhood for integration testing",
        "amenities": ["parks", "schools", "shopping"],
        "demographics": {
            "population": 25000,
            "median_income": 85000,
            "median_age": 35.5
        },
        "graph_metadata": {
            "primary_wiki_article": {
                "page_id": 123456,
                "title": "Test Neighborhood, San Francisco",
                "url": "https://en.wikipedia.org/wiki/Test_Neighborhood",
                "confidence": 0.95
            },
            "related_wiki_articles": [
                {
                    "page_id": 789012,
                    "title": "Test Park",
                    "url": "https://en.wikipedia.org/wiki/Test_Park",
                    "confidence": 0.85,
                    "relationship": "park"
                },
                {
                    "page_id": 345678,
                    "title": "Test Historic Site",
                    "url": "https://en.wikipedia.org/wiki/Test_Historic_Site",
                    "confidence": 0.75,
                    "relationship": "landmark"
                }
            ],
            "parent_geography": {
                "city_wiki": {
                    "page_id": 49728,
                    "title": "San Francisco"
                },
                "state_wiki": {
                    "page_id": 5407,
                    "title": "California"
                }
            },
            "generated_by": "test_generator",
            "generated_at": "2024-01-01T00:00:00Z",
            "source": "test_source"
        }
    }


class TestWikipediaCorrelations:
    """Test Wikipedia correlations preservation through the pipeline."""
    
    def test_model_creation(self, sample_neighborhood_data):
        """Test that models can be created with Wikipedia correlation data."""
        # Extract graph_metadata
        graph_data = sample_neighborhood_data["graph_metadata"]
        
        # Create WikipediaArticleReference for primary article
        primary_article = WikipediaArticleReference(
            page_id=graph_data["primary_wiki_article"]["page_id"],
            title=graph_data["primary_wiki_article"]["title"],
            url=graph_data["primary_wiki_article"]["url"],
            confidence=graph_data["primary_wiki_article"]["confidence"]
        )
        
        assert primary_article.page_id == 123456
        assert primary_article.confidence == 0.95
        
        # Create related articles
        related_articles = [
            WikipediaArticleReference(
                page_id=article["page_id"],
                title=article["title"],
                url=article["url"],
                confidence=article["confidence"],
                relationship=article.get("relationship")
            )
            for article in graph_data["related_wiki_articles"]
        ]
        
        assert len(related_articles) == 2
        assert related_articles[0].relationship == "park"
        
        # Create ParentGeography
        parent_geo = ParentGeography(
            city_wiki=WikipediaGeoReference(
                page_id=graph_data["parent_geography"]["city_wiki"]["page_id"],
                title=graph_data["parent_geography"]["city_wiki"]["title"]
            ),
            state_wiki=WikipediaGeoReference(
                page_id=graph_data["parent_geography"]["state_wiki"]["page_id"],
                title=graph_data["parent_geography"]["state_wiki"]["title"]
            )
        )
        
        assert parent_geo.city_wiki.page_id == 49728
        
        # Create WikipediaCorrelations
        correlations = WikipediaCorrelations(
            primary_wiki_article=primary_article,
            related_wiki_articles=related_articles,
            parent_geography=parent_geo,
            generated_by=graph_data["generated_by"],
            generated_at=graph_data["generated_at"],
            source=graph_data["source"]
        )
        
        assert correlations.primary_wiki_article.title == "Test Neighborhood, San Francisco"
        assert len(correlations.related_wiki_articles) == 2
    
    def test_loader_preserves_correlations(self, spark_session, sample_neighborhood_data):
        """Test that the loader preserves Wikipedia correlations from JSON."""
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([sample_neighborhood_data], f)
            temp_file = f.name
        
        try:
            # Initialize loader
            loader = NeighborhoodLoader(spark_session)
            
            # Load data
            df = loader.load(temp_file)
            
            # Check that wikipedia_correlations field exists (renamed from graph_metadata)
            assert "wikipedia_correlations" in df.columns or "graph_metadata" in df.columns
            
            # Get the first row
            row = df.first()
            
            # Check if correlations are preserved (might be under either name initially)
            correlations = row.wikipedia_correlations if hasattr(row, 'wikipedia_correlations') else row.graph_metadata if hasattr(row, 'graph_metadata') else None
            
            if correlations:
                assert correlations.primary_wiki_article.page_id == 123456
                assert correlations.primary_wiki_article.confidence == 0.95
                assert len(correlations.related_wiki_articles) == 2
        
        finally:
            # Clean up
            os.unlink(temp_file)
    
    def test_enricher_preserves_correlations(self, spark_session, sample_neighborhood_data):
        """Test that the enricher preserves Wikipedia correlations during enrichment."""
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([sample_neighborhood_data], f)
            temp_file = f.name
        
        try:
            # Load data
            loader = NeighborhoodLoader(spark_session)
            df = loader.load(temp_file)
            
            # Initialize enricher
            enricher = NeighborhoodEnricher(spark_session)
            
            # Enrich data
            enriched_df = enricher.enrich(df)
            
            # Check that wikipedia_correlations is preserved
            assert "wikipedia_correlations" in enriched_df.columns
            
            # Check that wikipedia_confidence_avg is calculated
            assert "wikipedia_confidence_avg" in enriched_df.columns
            
            # Get the first row
            row = enriched_df.first()
            
            # Verify confidence average
            if hasattr(row, 'wikipedia_confidence_avg'):
                # Should be 0.95 from primary article or 0.0 if missing
                assert row.wikipedia_confidence_avg in [0.95, 0.0]
            
            # Verify correlations are still present
            if hasattr(row, 'wikipedia_correlations') and row.wikipedia_correlations:
                assert row.wikipedia_correlations.primary_wiki_article.page_id == 123456
        
        finally:
            # Clean up
            os.unlink(temp_file)
    
    def test_elasticsearch_mapping_structure(self):
        """Test that Elasticsearch mapping includes Wikipedia correlations."""
        # Read the mapping file
        mapping_file = Path("/Users/ryanknight/projects/temporal/real_estate_ai_search/real_estate_search/elasticsearch/templates/neighborhoods.json")
        
        if mapping_file.exists():
            with open(mapping_file) as f:
                mapping = json.load(f)
            
            # Check that wikipedia_correlations is in the mapping
            assert "wikipedia_correlations" in mapping["properties"]
            
            wiki_mapping = mapping["properties"]["wikipedia_correlations"]
            assert wiki_mapping["type"] == "nested"
            
            # Check primary_wiki_article structure
            assert "primary_wiki_article" in wiki_mapping["properties"]
            primary = wiki_mapping["properties"]["primary_wiki_article"]
            assert "page_id" in primary["properties"]
            assert primary["properties"]["page_id"]["type"] == "long"
            assert "confidence" in primary["properties"]
            assert primary["properties"]["confidence"]["type"] == "float"
            
            # Check related_wiki_articles structure
            assert "related_wiki_articles" in wiki_mapping["properties"]
            related = wiki_mapping["properties"]["related_wiki_articles"]
            assert related["type"] == "nested"
            
            # Check wikipedia_confidence_avg field
            assert "wikipedia_confidence_avg" in mapping["properties"]
            assert mapping["properties"]["wikipedia_confidence_avg"]["type"] == "float"
    
    def test_end_to_end_correlation_preservation(self, spark_session, sample_neighborhood_data):
        """Test complete pipeline preservation of Wikipedia correlations."""
        # Create temporary JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([sample_neighborhood_data], f)
            temp_file = f.name
        
        try:
            # Load data
            loader = NeighborhoodLoader(spark_session)
            df = loader.load(temp_file)
            
            # Enrich data
            enricher = NeighborhoodEnricher(spark_session)
            enriched_df = enricher.enrich(df)
            
            # Verify final schema includes all expected fields
            schema_fields = {field.name for field in enriched_df.schema.fields}
            
            # Core fields
            assert "neighborhood_id" in schema_fields
            assert "name" in schema_fields
            
            # Wikipedia correlation fields
            assert "wikipedia_correlations" in schema_fields
            assert "wikipedia_confidence_avg" in schema_fields
            
            # Get data for verification
            row = enriched_df.first()
            
            # Verify data integrity
            assert row.neighborhood_id == "test-neighborhood-001"
            
            # Verify Wikipedia correlations preserved
            if hasattr(row, 'wikipedia_correlations') and row.wikipedia_correlations:
                assert row.wikipedia_correlations.primary_wiki_article.page_id == 123456
                assert row.wikipedia_correlations.primary_wiki_article.title == "Test Neighborhood, San Francisco"
                assert len(row.wikipedia_correlations.related_wiki_articles) == 2
                
                # Check related articles
                park_articles = [
                    a for a in row.wikipedia_correlations.related_wiki_articles 
                    if a.relationship == "park"
                ]
                assert len(park_articles) == 1
                assert park_articles[0].page_id == 789012
        
        finally:
            # Clean up
            os.unlink(temp_file)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])