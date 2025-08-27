"""
Example usage of WikipediaEnrichmentBuilder for Phase 4 integration.

This example demonstrates how to use the WikipediaEnrichmentBuilder to integrate
Wikipedia enrichment data into property and neighborhood documents for 
search pipeline indexing.
"""

from pyspark.sql import SparkSession
from data_pipeline.enrichment.wikipedia_integration import WikipediaEnrichmentBuilder

def example_usage():
    """
    Example of using WikipediaEnrichmentBuilder to enrich properties with Wikipedia data.
    """
    # Initialize Spark session
    spark = SparkSession.builder \
        .appName("WikipediaEnrichmentExample") \
        .getOrCreate()
    
    # Initialize the enrichment builder
    enricher = WikipediaEnrichmentBuilder(spark=spark)
    
    # Assume we have property and Wikipedia DataFrames
    # properties_df should have columns: listing_id, city, state, etc.
    # wikipedia_df should have columns: page_id, title, best_city, best_state, long_summary, key_topics, etc.
    
    # For demonstration, create sample data
    property_data = [
        ("prop_1", "San Francisco", "California", "123 Main St"),
        ("prop_2", "Berkeley", "California", "456 Oak Ave"),
        ("prop_3", "Oakland", "California", "789 Pine St"),
    ]
    
    wikipedia_data = [
        (123, "San Francisco", "San Francisco", "California", "San Francisco is a cultural hub...", "culture,tech,history"),
        (124, "Berkeley, California", "Berkeley", "California", "Berkeley is known for UC Berkeley...", "education,university,research"),
        (125, "Oakland, California", "Oakland", "California", "Oakland is a diverse port city...", "diversity,port,industry"),
    ]
    
    # Create DataFrames
    properties_df = spark.createDataFrame(
        property_data, 
        ["listing_id", "city", "state", "address"]
    )
    
    wikipedia_df = spark.createDataFrame(
        wikipedia_data,
        ["page_id", "title", "best_city", "best_state", "long_summary", "key_topics"]
    )
    
    # Enrich properties with Wikipedia data
    enriched_properties = enricher.enrich_properties(properties_df, wikipedia_df)
    
    # The enriched DataFrame will now contain:
    # - location_wikipedia_page_id
    # - location_wikipedia_title
    # - location_summary
    # - historical_significance
    # - location_key_topics
    # - cultural_features
    # - recreational_features
    # - transportation_features
    # - location_type
    # - location_confidence
    # - neighborhood_wikipedia_page_id
    # - neighborhood_wikipedia_title
    # - neighborhood_description
    # - neighborhood_history
    # - neighborhood_character
    # - notable_residents
    # - architectural_style
    # - establishment_year
    # - gentrification_index
    # - diversity_score
    # - cultural_richness
    # - historical_importance
    # - tourist_appeal
    # - local_amenities
    # - overall_desirability
    # - enriched_search_text
    
    # Show sample results
    enriched_properties.select(
        "listing_id", 
        "location_wikipedia_title",
        "location_summary",
        "cultural_richness",
        "overall_desirability"
    ).show(truncate=False)
    
    # Get enrichment statistics
    stats = enricher.get_enrichment_statistics(enriched_properties)
    print(f"Enrichment statistics: {stats}")
    
    # The enriched DataFrame can now be passed to search pipeline builders
    # which will create properly structured LocationContextModel and 
    # NeighborhoodContextModel objects for Elasticsearch indexing
    
    spark.stop()

def integration_with_search_pipeline():
    """
    Example of how the enriched data integrates with search pipeline builders.
    """
    from data_pipeline.search_pipeline.builders.property_builder import PropertyDocumentBuilder
    
    # After enrichment, the DataFrame contains all the fields needed by
    # the search pipeline builders to create structured documents
    
    # The PropertyDocumentBuilder will automatically:
    # 1. Extract enrichment fields from the DataFrame row
    # 2. Build LocationContextModel with landmarks, cultural_features, etc.
    # 3. Build NeighborhoodContextModel with history, character, etc.
    # 4. Create NearbyPOI objects from available data
    # 5. Calculate LocationScoresModel from quality scores
    # 6. Generate enriched_search_text combining all enrichment data
    
    # Example field mapping that builders expect:
    expected_fields = {
        "location_context": [
            "location_wikipedia_page_id",
            "location_wikipedia_title", 
            "location_summary",
            "historical_significance",
            "location_key_topics",
            "cultural_features",
            "recreational_features", 
            "transportation_features",
            "location_type",
            "location_confidence"
        ],
        "neighborhood_context": [
            "neighborhood_wikipedia_page_id",
            "neighborhood_wikipedia_title",
            "neighborhood_description",
            "neighborhood_history", 
            "neighborhood_character",
            "notable_residents",
            "architectural_style",
            "establishment_year",
            "gentrification_index",
            "diversity_score"
        ],
        "location_scores": [
            "cultural_richness",
            "historical_importance", 
            "tourist_appeal",
            "local_amenities",
            "overall_desirability"
        ]
    }
    
    print("Expected enrichment fields for search pipeline:")
    for category, fields in expected_fields.items():
        print(f"{category}:")
        for field in fields:
            print(f"  - {field}")

if __name__ == "__main__":
    example_usage()
    integration_with_search_pipeline()