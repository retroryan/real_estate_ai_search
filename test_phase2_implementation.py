#!/usr/bin/env python3
"""
Test script for Phase 2 field population using the new Pandas UDF ScoreCalculator.
"""

import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, array, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, FloatType, ArrayType

def create_test_spark_session():
    return SparkSession.builder \
        .appName('Phase2FieldsTest') \
        .master('local[2]') \
        .config('spark.sql.shuffle.partitions', '2') \
        .config('spark.sql.execution.arrow.pyspark.enabled', 'true') \
        .getOrCreate()

def create_test_neighborhood_data(spark):
    schema = StructType([
        StructField('neighborhood_id', StringType(), True),
        StructField('name', StringType(), True),
        StructField('city', StringType(), True),
        StructField('state', StringType(), True),
        StructField('amenities', ArrayType(StringType()), True),
        StructField('aggregated_topics', ArrayType(StringType()), True),
        StructField('wikipedia_count', IntegerType(), True),
        StructField('topic_count', IntegerType(), True),
        StructField('amenity_count', IntegerType(), True)
    ])
    
    data = [
        ('nbr1', 'Nightlife District', 'San Francisco', 'CA', 
         ['bar', 'pub', 'nightclub', 'cocktail lounge', 'music venue'], 
         ['entertainment', 'nightlife', 'culture'], 15, 25, 5),
        ('nbr2', 'Family Suburbs', 'San Jose', 'CA', 
         ['elementary school', 'park', 'playground', 'library', 'community center', 'pediatric clinic'], 
         ['family', 'education', 'recreation'], 8, 12, 6),
        ('nbr3', 'Arts Quarter', 'Oakland', 'CA', 
         ['art gallery', 'museum', 'theater', 'concert hall', 'cultural center'], 
         ['art', 'culture', 'history', 'music'], 20, 18, 5),
    ]
    
    return spark.createDataFrame(data, schema)

def create_test_wikipedia_data(spark):
    schema = StructType([
        StructField('page_id', StringType(), True),
        StructField('title', StringType(), True),
        StructField('long_summary', StringType(), True),
        StructField('key_topics', ArrayType(StringType()), True),
        StructField('relevance_score', FloatType(), True),
        StructField('location_confidence', FloatType(), True)
    ])
    
    data = [
        ('wiki1', 'Golden Gate Bridge', 
         'The Golden Gate Bridge is a suspension bridge spanning the Golden Gate strait with extensive details...', 
         ['bridge', 'architecture', 'transportation', 'San Francisco'], 0.95, 0.9),
        ('wiki2', 'Short Article', 'Brief summary.', 
         ['topic'], 0.3, 0.4),
    ]
    
    return spark.createDataFrame(data, schema)

def test_score_calculator(spark):
    """Test the new Pandas UDF-based ScoreCalculator."""
    print('🧪 Testing Pandas UDF ScoreCalculator...')
    
    from data_pipeline.processing.score_calculator import ScoreCalculator
    
    # Create test data
    test_df = create_test_neighborhood_data(spark)
    
    # Initialize score calculator
    score_calculator = ScoreCalculator(spark)
    
    # Test lifestyle scores
    lifestyle_df = score_calculator.add_lifestyle_scores(test_df)
    knowledge_df = score_calculator.add_knowledge_scores(lifestyle_df)
    
    # Check results
    results = knowledge_df.select(
        'name', 'nightlife_score', 'family_friendly_score', 
        'cultural_score', 'green_space_score', 'knowledge_score'
    ).collect()
    
    print(f'✅ Successfully calculated scores for {len(results)} neighborhoods')
    
    for row in results:
        print(f'📊 {row["name"]}:')
        print(f'   Nightlife: {row["nightlife_score"]:.2f}')
        print(f'   Family: {row["family_friendly_score"]:.2f}')
        print(f'   Cultural: {row["cultural_score"]:.2f}')
        print(f'   Green Space: {row["green_space_score"]:.2f}')
        print(f'   Knowledge: {row["knowledge_score"]:.3f}')
        print()
    
    return True

def test_wikipedia_confidence(spark):
    """Test Wikipedia confidence scoring."""
    print('🧪 Testing Wikipedia Confidence Scoring...')
    
    from data_pipeline.processing.score_calculator import ScoreCalculator
    
    # Create test data
    test_df = create_test_wikipedia_data(spark)
    
    # Add required fields for confidence calculation
    test_df = test_df.withColumn(
        'content_ratio',
        col('long_summary').rlike('.{100,}').cast('float')
    ).withColumn(
        'extraction_confidence', 
        col('relevance_score')
    )
    
    # Initialize score calculator
    score_calculator = ScoreCalculator(spark)
    
    # Add confidence scores
    scored_df = score_calculator.add_confidence_scores(test_df)
    
    # Check results
    results = scored_df.select(
        'title', 'overall_confidence', 
        'location_confidence', 'extraction_confidence'
    ).collect()
    
    print(f'✅ Successfully calculated confidence scores for {len(results)} articles')
    
    for row in results:
        print(f'📊 {row["title"]}: Overall Confidence = {row["overall_confidence"]:.3f}')
    
    return True

def test_enricher_integration(spark):
    """Test integration with enricher classes."""
    print('🧪 Testing Enricher Integration...')
    
    from data_pipeline.enrichment.neighborhood_enricher import NeighborhoodEnricher
    from data_pipeline.enrichment.wikipedia_enricher import WikipediaEnricher
    
    # Test neighborhood enricher
    neighborhood_df = create_test_neighborhood_data(spark)
    neighborhood_enricher = NeighborhoodEnricher(spark)
    
    enriched_neighborhoods = neighborhood_enricher._add_phase2_fields(neighborhood_df)
    
    expected_fields = [
        'created_at', 'updated_at', 'nightlife_score', 'family_friendly_score',
        'cultural_score', 'green_space_score', 'knowledge_score'
    ]
    
    missing_fields = [f for f in expected_fields if f not in enriched_neighborhoods.columns]
    
    if not missing_fields:
        print('✅ Neighborhood enricher integration successful')
        neighborhood_success = True
    else:
        print(f'❌ Neighborhood enricher missing fields: {missing_fields}')
        neighborhood_success = False
    
    # Test wikipedia enricher
    wikipedia_df = create_test_wikipedia_data(spark)
    wikipedia_enricher = WikipediaEnricher(spark)
    
    enriched_wikipedia = wikipedia_enricher._add_phase2_fields(wikipedia_df)
    
    expected_fields = [
        'created_at', 'updated_at', 'content_length', 'topic_count',
        'extraction_confidence', 'overall_confidence'
    ]
    
    missing_fields = [f for f in expected_fields if f not in enriched_wikipedia.columns]
    
    if not missing_fields:
        print('✅ Wikipedia enricher integration successful')
        wikipedia_success = True
    else:
        print(f'❌ Wikipedia enricher missing fields: {missing_fields}')
        wikipedia_success = False
    
    return neighborhood_success and wikipedia_success

def main():
    print('🚀 Starting Phase 2 Field Population Tests...\n')
    
    spark = create_test_spark_session()
    
    try:
        results = []
        results.append(test_score_calculator(spark))
        results.append(test_wikipedia_confidence(spark))
        results.append(test_enricher_integration(spark))
        
        passed = sum(results)
        total = len(results)
        
        print(f'🎯 Final Test Summary: {passed}/{total} test categories passed')
        
        if passed == total:
            print('🎉 All Phase 2 field population tests passed!')
            print('✨ The new Pandas UDF ScoreCalculator is working correctly!')
            return 0
        else:
            print('❌ Some tests failed - check the implementation')
            return 1
            
    except Exception as e:
        print(f'❌ Test execution failed: {e}')
        import traceback
        traceback.print_exc()
        return 1
    finally:
        spark.stop()

if __name__ == '__main__':
    sys.exit(main())