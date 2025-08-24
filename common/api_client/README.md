# Common Ingest API Client

A comprehensive Python client library for interacting with the Common Ingest API. This client provides type-safe access to all API endpoints with automatic pagination, error handling, and logging.

## Features

- 🏠 **Property & Neighborhood Data** - Access enriched property listings and neighborhood information
- 📚 **Wikipedia Integration** - Retrieve Wikipedia articles and summaries with location filtering
- 📊 **Statistics & Analytics** - Get comprehensive statistics about data coverage and quality
- 🔍 **Smart Filtering** - Filter by city, state, confidence scores, and more
- 📄 **Automatic Pagination** - Seamlessly iterate through large datasets
- ⚡ **Type Safety** - Full Pydantic model validation
- 🔧 **Flexible Configuration** - Multiple configuration options (YAML, env vars, dict)
- 📝 **Comprehensive Logging** - Structured logging for debugging and monitoring

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from common.api_client import APIClientFactory

# Create factory for local development
factory = APIClientFactory.for_local_development(port=8000)

# Check API health
if factory.check_health():
    print("API is healthy")

# Get properties
properties = factory.property_client.get_properties(
    city="San Francisco",
    page_size=10
)

# Get Wikipedia articles
articles = factory.wikipedia_client.get_articles(
    state="California",
    relevance_min=0.7
)

# Get statistics
stats = factory.stats_client.get_summary_stats()
print(f"Total properties: {stats.total_properties}")
```

## Client Factory

The `APIClientFactory` is the recommended way to create and manage API clients:

### Configuration Methods

```python
# Method 1: Local development
factory = APIClientFactory.for_local_development(port=8000)

# Method 2: From YAML configuration
factory = APIClientFactory.from_yaml("config/api_config.yaml")

# Method 3: From environment variables
factory = APIClientFactory.from_env(env_prefix="API")

# Method 4: Production configuration
factory = APIClientFactory.for_production(
    api_url="https://api.example.com",
    api_key="your-api-key",
    timeout=60
)

# Method 5: Direct configuration
factory = APIClientFactory(
    base_url="http://localhost:8000",
    logger=custom_logger
)
```

## Available Clients

### Property Client

Access property and neighborhood data:

```python
# Get properties with filtering
properties = factory.property_client.get_properties(
    city="Park City",
    include_embeddings=True,
    collection_name="embeddings_nomic",
    page=1,
    page_size=50
)

# Get single property
property = factory.property_client.get_property_by_id("prop-oak-125")

# Get all properties with pagination
for batch in factory.property_client.get_all_properties(page_size=100):
    for property in batch:
        print(f"{property.listing_id}: ${property.price}")

# Get neighborhoods
neighborhoods = factory.property_client.get_neighborhoods(
    city="San Francisco",
    page_size=20
)
```

### Wikipedia Client

Access Wikipedia articles and summaries:

```python
# Get articles with filtering
articles = factory.wikipedia_client.get_articles(
    city="San Francisco",
    state="California",
    relevance_min=0.5,
    sort_by="relevance",  # Options: relevance, title, page_id
    page_size=25
)

# Get article by ID
article = factory.wikipedia_client.get_article_by_id(
    page_id=12345,
    include_embeddings=True
)

# Get summaries with confidence filtering
summaries = factory.wikipedia_client.get_summaries(
    confidence_min=0.8,
    include_key_topics=True,
    page_size=30
)

# Iterate through all summaries
for batch in factory.wikipedia_client.get_all_summaries():
    for summary in batch:
        print(f"{summary.article_title}: {summary.overall_confidence}")
```

### Statistics Client

Access comprehensive statistics and metrics:

```python
# Get summary statistics
summary = factory.stats_client.get_summary_stats()
print(f"Total properties: {summary.total_properties}")
print(f"Unique cities: {summary.unique_cities}")

# Get detailed property statistics
property_stats = factory.stats_client.get_property_stats()
print(f"Properties by type: {property_stats.by_type}")
print(f"Average price: ${property_stats.price_stats['avg']}")

# Get neighborhood statistics
neighborhood_stats = factory.stats_client.get_neighborhood_stats()

# Get Wikipedia statistics
wiki_stats = factory.stats_client.get_wikipedia_stats()

# Get coverage statistics
coverage = factory.stats_client.get_coverage_stats()
for city_info in coverage.top_cities_by_data[:5]:
    print(f"{city_info['city']}: {city_info['total_data_points']} data points")

# Get enrichment statistics
enrichment = factory.stats_client.get_enrichment_stats()

# Get all statistics at once
all_stats = factory.stats_client.get_all_stats()
```

### System Client

Access system health and information:

```python
# Check health status
health = factory.system_client.get_health()
print(f"Status: {health.status}")  # healthy, degraded, or unhealthy
print(f"Components: {health.components}")

# Check readiness (simplified health check)
is_ready = factory.system_client.check_readiness()

# Get root API information
info = factory.system_client.get_root_info()
print(f"API Version: {info.version}")

# Check specific component health
component_health = factory.system_client.get_component_health("wikipedia_database")
print(f"Wikipedia DB status: {component_health['status']}")
```

## Pagination

All list endpoints support pagination with automatic iteration:

```python
# Manual pagination
page = 1
while True:
    properties = factory.property_client.get_properties(
        page=page,
        page_size=50
    )
    if not properties:
        break
    # Process properties
    page += 1

# Automatic pagination (recommended)
for batch in factory.property_client.get_all_properties(page_size=50):
    for property in batch:
        # Process each property
        pass
```

## Error Handling

The client includes comprehensive error handling:

```python
from common.api_client import NotFoundError, APIError

try:
    property = factory.property_client.get_property_by_id("invalid-id")
except NotFoundError as e:
    print(f"Property not found: {e}")
except APIError as e:
    print(f"API error: {e}")
```

## Configuration File Example

Create a YAML configuration file:

```yaml
# config/api_config.yaml
api:
  base_url: http://localhost:8000
  timeout: 30
  default_headers:
    X-API-Key: your-api-key

property_api:
  base_url: http://localhost:8000/api/v1
  timeout: 60

wikipedia_api:
  base_url: http://localhost:8000/api/v1/wikipedia
  timeout: 45
```

Load configuration:

```python
factory = APIClientFactory.from_yaml("config/api_config.yaml", section="api")
```

## Environment Variables

Configure via environment variables:

```bash
export API_BASE_URL=http://localhost:8000
export API_TIMEOUT=30
export API_KEY=your-api-key
```

```python
factory = APIClientFactory.from_env(env_prefix="API")
```

## Logging

The client includes structured logging:

```python
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("api_client")

# Create factory with custom logger
factory = APIClientFactory(
    base_url="http://localhost:8000",
    logger=logger
)
```

## Integration Testing

Run integration tests:

```bash
# Run all integration tests
pytest common/api_client/integration_tests/

# Run specific test file
pytest common/api_client/integration_tests/test_property_client_integration.py

# Run with coverage
pytest common/api_client/integration_tests/ --cov=common.api_client
```

## Examples

See the `examples/` directory for complete usage examples:

```bash
# Run the usage example
python common/api_client/examples/usage_example.py
```

## API Endpoints

The client covers all Common Ingest API endpoints:

### Property Endpoints
- `GET /api/v1/properties` - List properties with filtering
- `GET /api/v1/properties/{id}` - Get single property
- `GET /api/v1/neighborhoods` - List neighborhoods
- `GET /api/v1/neighborhoods/{id}` - Get single neighborhood

### Wikipedia Endpoints
- `GET /api/v1/wikipedia/articles` - List articles
- `GET /api/v1/wikipedia/articles/{id}` - Get single article
- `GET /api/v1/wikipedia/summaries` - List summaries
- `GET /api/v1/wikipedia/summaries/{id}` - Get single summary

### Statistics Endpoints
- `GET /api/v1/stats/summary` - Overall summary
- `GET /api/v1/stats/properties` - Property statistics
- `GET /api/v1/stats/neighborhoods` - Neighborhood statistics
- `GET /api/v1/stats/wikipedia` - Wikipedia statistics
- `GET /api/v1/stats/coverage` - Coverage statistics
- `GET /api/v1/stats/enrichment` - Enrichment statistics

### System Endpoints
- `GET /` - Root API information
- `GET /api/v1/health` - Health check with component status

## License

MIT