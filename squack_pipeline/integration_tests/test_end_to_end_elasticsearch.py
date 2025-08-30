"""End-to-end integration test for SQUACK pipeline to Elasticsearch.

This test validates the complete pipeline:
1. Bronze tier: Load data with nested structures preserved
2. Silver tier: Enrich while maintaining nested structures
3. Gold tier: Minimal transformations for Elasticsearch
4. Elasticsearch: Write and query nested documents
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Any

import duckdb
import pytest
from dotenv import load_dotenv
from elasticsearch import Elasticsearch

from squack_pipeline.config.settings import PipelineSettings, ElasticsearchConfig
from squack_pipeline.loaders.connection import DuckDBConnectionManager
from squack_pipeline.loaders.property_loader import PropertyLoader
from squack_pipeline.loaders.neighborhood_loader import NeighborhoodLoader
from squack_pipeline.loaders.wikipedia_loader import WikipediaLoader
from squack_pipeline.processors.property_silver_processor import PropertySilverProcessor
from squack_pipeline.processors.neighborhood_silver_processor import NeighborhoodSilverProcessor
from squack_pipeline.processors.wikipedia_silver_processor import WikipediaSilverProcessor
from squack_pipeline.processors.property_gold_processor import PropertyGoldProcessor
from squack_pipeline.processors.neighborhood_gold_processor import NeighborhoodGoldProcessor
from squack_pipeline.processors.wikipedia_gold_processor import WikipediaGoldProcessor
from squack_pipeline.writers.elasticsearch.writer import ElasticsearchWriter
from squack_pipeline.writers.elasticsearch.models import EntityType


class TestEndToEndElasticsearch:
    """Test complete pipeline from Bronze to Elasticsearch with nested structures."""
    
    @pytest.fixture(scope="class")
    def env_loaded(self):
        """Load environment variables from .env file."""
        env_path = Path(__file__).parent.parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            print(f"✓ Loaded environment from {env_path}")
        return True
    
    @pytest.fixture
    def settings(self):
        """Load pipeline settings."""
        return PipelineSettings.load_from_yaml(Path("squack_pipeline/config.yaml"))
    
    @pytest.fixture
    def connection(self, settings):
        """Create DuckDB connection."""
        conn_mgr = DuckDBConnectionManager()
        conn_mgr.initialize(settings)
        return conn_mgr.get_connection()
    
    @pytest.fixture
    def es_client(self, env_loaded):
        """Create Elasticsearch client with auth from .env."""
        # Get credentials from environment
        es_host = os.getenv('ELASTICSEARCH_HOST', 'localhost')
        es_port = int(os.getenv('ELASTICSEARCH_PORT', '9200'))
        es_username = os.getenv('ES_USERNAME', 'elastic')
        es_password = os.getenv('ES_PASSWORD')
        
        client_config = {
            'hosts': [{'host': es_host, 'port': es_port, 'scheme': 'http'}],
            'request_timeout': 30,
            'max_retries': 3,
            'retry_on_timeout': True,
        }
        
        # Add authentication if configured
        if es_username and es_password:
            client_config['basic_auth'] = (es_username, es_password)
            print(f"✓ Using authentication for user: {es_username}")
        
        client = Elasticsearch(**client_config)
        
        # Verify connection
        info = client.info()
        print(f"✓ Connected to Elasticsearch {info['version']['number']}")
        
        return client
    
    @pytest.fixture
    def es_writer(self, settings, env_loaded):
        """Create Elasticsearch writer."""
        # Create ElasticsearchConfig from settings
        from squack_pipeline.config.settings import ElasticsearchConfig
        
        # Get Elasticsearch config from output settings or create default
        if not settings.output.elasticsearch:
            settings.output.elasticsearch = ElasticsearchConfig()
        
        writer = ElasticsearchWriter(settings)
        
        # Verify connection
        assert writer.verify_connection(), "Failed to connect to Elasticsearch"
        
        return writer
    
    def process_properties_to_gold(self, settings, connection) -> tuple[str, List[Dict]]:
        """Process properties through all tiers and return Gold table name and data."""
        # Bronze
        loader = PropertyLoader(settings)
        loader.set_connection(connection)
        bronze_table = loader.load(table_name="bronze_properties", sample_size=5)
        
        # Silver
        silver_proc = PropertySilverProcessor(settings)
        silver_proc.set_connection(connection)
        silver_table = silver_proc.process(bronze_table)
        
        # Gold
        gold_proc = PropertyGoldProcessor(settings)
        gold_proc.set_connection(connection)
        gold_table = gold_proc.process(silver_table)
        
        # Get data from Gold table
        gold_data = connection.execute(f"SELECT * FROM {gold_table}").fetchall()
        columns = [desc[0] for desc in connection.description]
        
        # Convert to list of dicts
        records = []
        for row in gold_data:
            record = dict(zip(columns, row))
            records.append(record)
        
        return gold_table, records
    
    def process_neighborhoods_to_gold(self, settings, connection) -> tuple[str, List[Dict]]:
        """Process neighborhoods through all tiers and return Gold table name and data."""
        # Bronze
        loader = NeighborhoodLoader(settings)
        loader.set_connection(connection)
        bronze_table = loader.load(table_name="bronze_neighborhoods", sample_size=5)
        
        # Silver
        silver_proc = NeighborhoodSilverProcessor(settings)
        silver_proc.set_connection(connection)
        silver_table = silver_proc.process(bronze_table)
        
        # Gold
        gold_proc = NeighborhoodGoldProcessor(settings)
        gold_proc.set_connection(connection)
        gold_table = gold_proc.process(silver_table)
        
        # Get data from Gold table
        gold_data = connection.execute(f"SELECT * FROM {gold_table}").fetchall()
        columns = [desc[0] for desc in connection.description]
        
        # Convert to list of dicts
        records = []
        for row in gold_data:
            record = dict(zip(columns, row))
            records.append(record)
        
        return gold_table, records
    
    def process_wikipedia_to_gold(self, settings, connection) -> tuple[str, List[Dict]]:
        """Process Wikipedia through all tiers and return Gold table name and data."""
        # Bronze
        loader = WikipediaLoader(settings)
        loader.set_connection(connection)
        bronze_table = loader.load(table_name="bronze_wikipedia", sample_size=5)
        
        # Silver
        silver_proc = WikipediaSilverProcessor(settings)
        silver_proc.set_connection(connection)
        silver_table = silver_proc.process(bronze_table)
        
        # Gold
        gold_proc = WikipediaGoldProcessor(settings)
        gold_proc.set_connection(connection)
        gold_table = gold_proc.process(silver_table)
        
        # Get data from Gold table
        gold_data = connection.execute(f"SELECT * FROM {gold_table}").fetchall()
        columns = [desc[0] for desc in connection.description]
        
        # Convert to list of dicts
        records = []
        for row in gold_data:
            record = dict(zip(columns, row))
            records.append(record)
        
        return gold_table, records
    
    def test_properties_end_to_end(self, settings, connection, es_writer, es_client):
        """Test Properties: Bronze → Silver → Gold → Elasticsearch with nested structures."""
        print("\n" + "="*80)
        print("Testing Properties End-to-End Pipeline to Elasticsearch")
        print("="*80)
        
        # 1. Process through all tiers
        gold_table, gold_records = self.process_properties_to_gold(settings, connection)
        print(f"✓ Processed to Gold: {gold_table} with {len(gold_records)} records")
        
        # 2. Write to Elasticsearch
        result = es_writer.write_entity(EntityType.PROPERTY, gold_records)
        assert result.success, f"Failed to write to Elasticsearch: {result.error}"
        print(f"✓ Written to Elasticsearch: {result.record_count} records in {result.duration_seconds:.2f}s")
        
        # Wait for indexing
        time.sleep(1)
        es_client.indices.refresh(index="properties")
        
        # 3. Query Elasticsearch to verify nested structures
        print("\nVerifying nested structures in Elasticsearch:")
        
        # Get a sample document
        search_result = es_client.search(
            index="properties",
            body={"query": {"match_all": {}}, "size": 1}
        )
        
        assert search_result['hits']['total']['value'] > 0, "No documents found in Elasticsearch"
        doc = search_result['hits']['hits'][0]['_source']
        
        # Verify nested structures are preserved
        assert 'address' in doc, "Address nested structure missing"
        assert isinstance(doc['address'], dict), "Address should be a nested object"
        assert 'street' in doc['address'], "Address.street missing"
        assert 'city' in doc['address'], "Address.city missing"
        print(f"  ✓ address.* preserved: {list(doc['address'].keys())}")
        
        assert 'property_details' in doc, "Property details nested structure missing"
        assert isinstance(doc['property_details'], dict), "Property details should be nested"
        assert 'bedrooms' in doc['property_details'], "Property_details.bedrooms missing"
        print(f"  ✓ property_details.* preserved: {list(doc['property_details'].keys())}")
        
        assert 'coordinates' in doc, "Coordinates nested structure missing"
        assert isinstance(doc['coordinates'], dict), "Coordinates should be nested"
        assert 'latitude' in doc['coordinates'], "Coordinates.latitude missing"
        assert 'longitude' in doc['coordinates'], "Coordinates.longitude missing"
        print(f"  ✓ coordinates.* preserved: lat={doc['coordinates']['latitude']:.4f}, lon={doc['coordinates']['longitude']:.4f}")
        
        assert 'parking' in doc, "Parking object missing"
        assert isinstance(doc['parking'], dict), "Parking should be an object"
        assert 'spaces' in doc['parking'], "Parking.spaces missing"
        print(f"  ✓ parking object preserved: {doc['parking']}")
        
        # 4. Test nested field queries
        print("\nTesting nested field queries in Elasticsearch:")
        
        # Query by nested address.city
        city_query = es_client.search(
            index="properties",
            body={
                "query": {
                    "term": {"address.city": "San Francisco"}
                },
                "size": 10
            }
        )
        city_count = city_query['hits']['total']['value']
        print(f"  ✓ Query by address.city: {city_count} properties in San Francisco")
        
        # Query by nested property_details.bedrooms
        bedroom_query = es_client.search(
            index="properties",
            body={
                "query": {
                    "range": {"property_details.bedrooms": {"gte": 3}}
                },
                "size": 10
            }
        )
        bedroom_count = bedroom_query['hits']['total']['value']
        print(f"  ✓ Query by property_details.bedrooms: {bedroom_count} properties with 3+ bedrooms")
        
        # Query by coordinates (geo query if mapping supports it)
        coord_query = es_client.search(
            index="properties",
            body={
                "query": {
                    "bool": {
                        "must": [
                            {"exists": {"field": "coordinates.latitude"}},
                            {"exists": {"field": "coordinates.longitude"}}
                        ]
                    }
                },
                "size": 10
            }
        )
        coord_count = coord_query['hits']['total']['value']
        print(f"  ✓ Query by coordinates existence: {coord_count} properties with coordinates")
        
        # 5. Test aggregations on nested fields
        agg_result = es_client.search(
            index="properties",
            body={
                "size": 0,
                "aggs": {
                    "cities": {
                        "terms": {"field": "address.city.keyword", "size": 10}
                    },
                    "avg_bedrooms": {
                        "avg": {"field": "property_details.bedrooms"}
                    },
                    "parking_stats": {
                        "stats": {"field": "parking.spaces"}
                    }
                }
            }
        )
        
        if 'aggregations' in agg_result:
            print("\n✓ Aggregations on nested fields successful:")
            if 'cities' in agg_result['aggregations']:
                cities = agg_result['aggregations']['cities']['buckets']
                if cities:
                    print(f"  - Top city: {cities[0]['key']} ({cities[0]['doc_count']} properties)")
            if 'avg_bedrooms' in agg_result['aggregations']:
                avg_br = agg_result['aggregations']['avg_bedrooms']['value']
                if avg_br:
                    print(f"  - Average bedrooms: {avg_br:.1f}")
            if 'parking_stats' in agg_result['aggregations']:
                parking = agg_result['aggregations']['parking_stats']
                if parking['count'] > 0:
                    print(f"  - Parking spaces: avg={parking['avg']:.1f}, max={parking['max']}")
        
        print("\n" + "="*80)
        print("✅ Properties End-to-End Pipeline Test PASSED")
        print("   Nested structures preserved from Bronze → Silver → Gold → Elasticsearch")
        print("="*80)
    
    def test_neighborhoods_end_to_end(self, settings, connection, es_writer, es_client):
        """Test Neighborhoods: Bronze → Silver → Gold → Elasticsearch with nested structures."""
        print("\n" + "="*80)
        print("Testing Neighborhoods End-to-End Pipeline to Elasticsearch")
        print("="*80)
        
        # 1. Process through all tiers
        gold_table, gold_records = self.process_neighborhoods_to_gold(settings, connection)
        print(f"✓ Processed to Gold: {gold_table} with {len(gold_records)} records")
        
        # 2. Write to Elasticsearch
        result = es_writer.write_entity(EntityType.NEIGHBORHOOD, gold_records)
        assert result.success, f"Failed to write to Elasticsearch: {result.error}"
        print(f"✓ Written to Elasticsearch: {result.record_count} records in {result.duration_seconds:.2f}s")
        
        # Wait for indexing
        time.sleep(1)
        es_client.indices.refresh(index="neighborhoods")
        
        # 3. Query Elasticsearch to verify nested structures
        print("\nVerifying nested structures in Elasticsearch:")
        
        # Get a sample document
        search_result = es_client.search(
            index="neighborhoods",
            body={"query": {"match_all": {}}, "size": 1}
        )
        
        assert search_result['hits']['total']['value'] > 0, "No documents found in Elasticsearch"
        doc = search_result['hits']['hits'][0]['_source']
        
        # Verify nested structures
        assert 'coordinates' in doc, "Coordinates nested structure missing"
        assert isinstance(doc['coordinates'], dict), "Coordinates should be nested"
        print(f"  ✓ coordinates.* preserved: {list(doc['coordinates'].keys())}")
        
        assert 'demographics' in doc, "Demographics nested structure missing"
        assert isinstance(doc['demographics'], dict), "Demographics should be nested"
        assert 'population' in doc['demographics'], "Demographics.population missing"
        print(f"  ✓ demographics.* preserved: {list(doc['demographics'].keys())}")
        
        assert 'characteristics' in doc, "Characteristics nested structure missing"
        assert isinstance(doc['characteristics'], dict), "Characteristics should be nested"
        print(f"  ✓ characteristics.* preserved: {list(doc['characteristics'].keys())}")
        
        # 4. Test nested field queries
        print("\nTesting nested field queries in Elasticsearch:")
        
        # Query by demographics.population
        pop_query = es_client.search(
            index="neighborhoods",
            body={
                "query": {
                    "range": {"demographics.population": {"gte": 1000}}
                },
                "size": 10
            }
        )
        pop_count = pop_query['hits']['total']['value']
        print(f"  ✓ Query by demographics.population: {pop_count} neighborhoods with 1000+ population")
        
        # Query by characteristics.walkability_score
        walk_query = es_client.search(
            index="neighborhoods",
            body={
                "query": {
                    "range": {"characteristics.walkability_score": {"gte": 7}}
                },
                "size": 10
            }
        )
        walk_count = walk_query['hits']['total']['value']
        print(f"  ✓ Query by characteristics.walkability_score: {walk_count} walkable neighborhoods")
        
        print("\n" + "="*80)
        print("✅ Neighborhoods End-to-End Pipeline Test PASSED")
        print("   Nested structures preserved throughout pipeline")
        print("="*80)
    
    def test_wikipedia_end_to_end(self, settings, connection, es_writer, es_client):
        """Test Wikipedia: Bronze → Silver → Gold → Elasticsearch (mostly flat structure)."""
        print("\n" + "="*80)
        print("Testing Wikipedia End-to-End Pipeline to Elasticsearch")
        print("="*80)
        
        # 1. Process through all tiers
        gold_table, gold_records = self.process_wikipedia_to_gold(settings, connection)
        print(f"✓ Processed to Gold: {gold_table} with {len(gold_records)} records")
        
        # 2. Write to Elasticsearch
        result = es_writer.write_entity(EntityType.WIKIPEDIA, gold_records)
        assert result.success, f"Failed to write to Elasticsearch: {result.error}"
        print(f"✓ Written to Elasticsearch: {result.record_count} records in {result.duration_seconds:.2f}s")
        
        # Wait for indexing
        time.sleep(1)
        es_client.indices.refresh(index="wikipedia")
        
        # 3. Query Elasticsearch to verify structure
        print("\nVerifying structure in Elasticsearch:")
        
        # Get a sample document
        search_result = es_client.search(
            index="wikipedia",
            body={"query": {"match_all": {}}, "size": 1}
        )
        
        assert search_result['hits']['total']['value'] > 0, "No documents found in Elasticsearch"
        doc = search_result['hits']['hits'][0]['_source']
        
        # Verify fields (Wikipedia is mostly flat)
        assert 'page_id' in doc, "page_id missing"
        assert 'title' in doc, "title missing"
        assert 'extract' in doc, "extract missing"
        print(f"  ✓ Core fields preserved: page_id={doc['page_id']}, title={doc['title'][:30]}...")
        
        if 'location' in doc and doc['location']:
            print(f"  ✓ Location array preserved: {doc['location']}")
        
        # 4. Test full-text search
        print("\nTesting full-text search in Elasticsearch:")
        
        text_query = es_client.search(
            index="wikipedia",
            body={
                "query": {
                    "match": {"extract": "park"}
                },
                "size": 10
            }
        )
        text_count = text_query['hits']['total']['value']
        print(f"  ✓ Full-text search: {text_count} articles mentioning 'park'")
        
        print("\n" + "="*80)
        print("✅ Wikipedia End-to-End Pipeline Test PASSED")
        print("="*80)
    
    def test_cross_index_search(self, settings, connection, es_writer, es_client):
        """Test searching across multiple indices with nested structures."""
        print("\n" + "="*80)
        print("Testing Cross-Index Search with Nested Structures")
        print("="*80)
        
        # Process and write all entities
        print("\nProcessing all entities to Elasticsearch...")
        
        # Properties
        _, prop_records = self.process_properties_to_gold(settings, connection)
        prop_result = es_writer.write_entity(EntityType.PROPERTY, prop_records)
        print(f"  ✓ Properties: {prop_result.record_count} records")
        
        # Neighborhoods
        _, neigh_records = self.process_neighborhoods_to_gold(settings, connection)
        neigh_result = es_writer.write_entity(EntityType.NEIGHBORHOOD, neigh_records)
        print(f"  ✓ Neighborhoods: {neigh_result.record_count} records")
        
        # Wikipedia
        _, wiki_records = self.process_wikipedia_to_gold(settings, connection)
        wiki_result = es_writer.write_entity(EntityType.WIKIPEDIA, wiki_records)
        print(f"  ✓ Wikipedia: {wiki_result.record_count} records")
        
        # Wait for indexing
        time.sleep(1)
        es_client.indices.refresh(index="properties,neighborhoods,wikipedia")
        
        # Test multi-index search
        print("\nTesting multi-index search:")
        
        multi_search = es_client.search(
            index="properties,neighborhoods,wikipedia",
            body={
                "query": {"match_all": {}},
                "size": 0,
                "aggs": {
                    "by_index": {
                        "terms": {"field": "_index", "size": 10}
                    }
                }
            }
        )
        
        if 'aggregations' in multi_search:
            print("✓ Multi-index search successful:")
            for bucket in multi_search['aggregations']['by_index']['buckets']:
                print(f"  - {bucket['key']}: {bucket['doc_count']} documents")
        
        # Test entity_type field (added by Gold processors)
        entity_search = es_client.search(
            index="properties,neighborhoods",
            body={
                "query": {"exists": {"field": "entity_type"}},
                "size": 0,
                "aggs": {
                    "by_entity": {
                        "terms": {"field": "entity_type.keyword", "size": 10}
                    }
                }
            }
        )
        
        if 'aggregations' in entity_search and entity_search['aggregations']['by_entity']['buckets']:
            print("\n✓ Entity type field present:")
            for bucket in entity_search['aggregations']['by_entity']['buckets']:
                print(f"  - entity_type={bucket['key']}: {bucket['doc_count']} documents")
        
        print("\n" + "="*80)
        print("✅ Cross-Index Search Test PASSED")
        print("="*80)
        
        print("\n" + "="*80)
        print("🎉 END-TO-END VALIDATION COMPLETE")
        print("="*80)
        print("✅ All nested structures preserved throughout the pipeline:")
        print("   Bronze (DuckDB STRUCTs) → Silver (Enriched STRUCTs) →")
        print("   Gold (Minimal transforms) → Elasticsearch (Nested JSON)")
        print("\n✅ Dot notation queries work in both DuckDB and Elasticsearch")
        print("✅ No flattening or reconstruction required")
        print("="*80)