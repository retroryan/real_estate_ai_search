# Real Estate AI Search - Project Guide

## 🚨 CRITICAL: Development Requirements & Standards

### Complete Cut-Over Implementation Requirements

These requirements apply to ALL code changes and MUST be followed exactly. No exceptions.

#### Core Principles

1. **NO PERFORMANCE TESTING OR BENCHMARKING**
   - Do not add any performance comparison, performance testing, benchmarking, or query optimization
   - Focus on functionality, not performance metrics
   - No timing comparisons or speed tests

2. **FOLLOW REQUIREMENTS EXACTLY**
   - Implement only what is explicitly requested
   - Do not add features or functionality beyond the documented requirements
   - Always fix the core issue, not symptoms

3. **ATOMIC UPDATES ONLY**
   - All occurrences must be changed in a single, complete update
   - Change everything or change nothing
   - No partial updates allowed

4. **NO MIGRATION STRATEGIES**
   - No temporary compatibility periods
   - No rollback plans
   - No backwards compatibility layers
   - No wrapper functions for transitions

#### Implementation Standards

5. **CLEAN CODE PRACTICES**
   - Simple, direct replacements only
   - No code duplication to handle multiple patterns
   - No abstraction layers for compatibility
   - Use modules and maintain clean code structure

6. **NO LEGACY CODE PRESERVATION**
   - Do not comment out old code "just in case"
   - Do not create backup copies of old implementations
   - Remove old code completely when replacing

7. **NAMING CONVENTIONS**
   - Do not suffix class names with "Enhanced", "Improved", or version numbers
   - Update existing classes directly (e.g., update `PropertyIndex`, not create `ImprovedPropertyIndex`)
   - Never name components after phases or steps from proposal documents (no `test_phase_2_bronze_layer.py`)

#### Technical Requirements

8. **TYPE SYSTEM RULES**
   - ALWAYS use Pydantic for data models
   - Never use `hasattr()` for type checking
   - Never use `isinstance()` for type checking
   - No Union types - if you need a Union, re-evaluate the core design
   - No variable casting or type aliases

9. **DATA HANDLING**
   - Never generate mocks or sample data when actual results are missing
   - Investigate why data is missing and fix the root cause
   - Ask for clarification if data sources are unclear

10. **ERROR HANDLING**
   - If something doesn't work, fix the core issue
   - Do not hack around problems with mocks
   - Do not create workarounds - address the root cause

11. **COMMUNICATION**
    - If there are questions or uncertainties, ASK before proceeding
    - Document only what was explicitly requested
    - Provide clear feedback when requirements conflict with best practices

#### SOLID Principles (MANDATORY)

12. **SINGLE RESPONSIBILITY PRINCIPLE (SRP)**
    - Each class should have only ONE reason to change
    - Each module should do ONE thing well
    - Split large classes into smaller, focused components
    - If a class has "and" in its description, it needs to be split

13. **OPEN/CLOSED PRINCIPLE (OCP)**
    - Classes should be open for extension but closed for modification
    - Use dependency injection and interfaces
    - Add new functionality through new classes, not by modifying existing ones
    - Prefer composition over inheritance

14. **LISKOV SUBSTITUTION PRINCIPLE (LSP)**
    - Derived classes must be substitutable for their base classes
    - Subclasses should not weaken preconditions or strengthen postconditions
    - If you need to check the type of an object, you're violating LSP
    - All implementations of an interface must be interchangeable

15. **INTERFACE SEGREGATION PRINCIPLE (ISP)**
    - Clients should not be forced to depend on interfaces they don't use
    - Create small, focused interfaces rather than large, general ones
    - Better to have many specific interfaces than one general interface
    - If an implementation has empty methods, the interface is too broad

16. **DEPENDENCY INVERSION PRINCIPLE (DIP) - USE ONLY WHEN REQUESTED**
    - **IMPORTANT: This is a demo project - prefer simplicity over DIP**
    - Only implement DIP when explicitly requested or absolutely necessary
    - For most cases, direct dependencies are fine and preferred
    - Choose the simplest approach that works
    - If implementing DIP:
      - Depend on abstractions, not concretions
      - High-level modules should not depend on low-level modules
      - Both should depend on abstractions (interfaces/protocols)
      - Inject dependencies, don't create them internally

#### Testing Requirements

17. **INTEGRATION TESTS ARE PRIMARY**
    - Integration tests are MORE valuable than unit tests
    - Always write integration tests for new features
    - Test real interactions between components, not mocked behavior
    - Integration tests should cover the actual use cases

18. **TEST COVERAGE PRIORITIES**
    - First priority: Integration tests that test actual workflows
    - Second priority: Integration tests for critical paths
    - Third priority: Unit tests for complex business logic only
    - Never write unit tests just for coverage metrics

19. **TEST IMPLEMENTATION RULES**
    - Tests must use real dependencies when possible (databases, APIs)
    - Only mock external services that are expensive or unreliable
    - Test the behavior, not the implementation
    - Each test should test one complete scenario end-to-end

## ⚠️ IMPORTANT: DuckDB Pipeline Guidelines

**When working on `squack_pipeline_v2/`, ALWAYS reference:**
- `squack_pipeline_v2/DUCK_DB_BEST_PRACTICES_V2.md` - Contains critical DuckDB patterns and anti-patterns
- Pay special attention to the "Quick Reference for LLMs" section at the top
- The pipeline currently has issues with TableIdentifier objects that need to be removed

## Quick Start Guide

### Prerequisites

1. **Python 3.10+** installed
2. **Elasticsearch** running locally (port 9200)
3. **Neo4j** (optional, for GraphRAG)
4. **API Keys** for embedding providers (Voyage, OpenAI, or Gemini)

### Initial Setup

```bash
# Clone and navigate to project
cd real_estate_ai_search

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Copy environment file
cp .env.example .env

# Edit .env and add your API keys:
VOYAGE_API_KEY=your-voyage-api-key-here
GOOGLE_API_KEY=your-gemini-api-key-here  # For Gemini embeddings
OPENAI_API_KEY=your-openai-key-here     # For OpenAI embeddings
```

## Running the Complete Pipeline

### Step 1: Start Elasticsearch

```bash
# Using Docker (recommended)
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0
```

### Step 2: Create Elasticsearch Indices

```bash
# Setup all indices with proper mappings
python -m real_estate_search.management setup-indices --clear

# Verify indices were created
curl -X GET "localhost:9200/_cat/indices?v"
```

### Step 3: Run Data Pipeline

The data pipeline processes property data, neighborhoods, and Wikipedia articles, generates embeddings, and indexes everything to Elasticsearch.

```bash
# Run full pipeline (properties, neighborhoods, Wikipedia)
python -m squack_pipeline

# Or run with specific options:
python -m squack_pipeline \
  --sample-size 100 \     # Process only 100 items per type
  --config squack_pipeline/config.yaml \
  --log-level INFO
```

### Step 4: Verify Data Loading

```bash
# Check Elasticsearch has data
python -m real_estate_search.management demo --list

# Run a test search
python -m real_estate_search.management demo 1
```

## Configuration Details

### API Key Loading Strategy

The project uses a hierarchical configuration approach:

1. **Environment Variables** (.env file in parent directory)
2. **YAML Configuration** (config.yaml files)
3. **Default Values** (in code)

#### Key Configuration Files

- `/real_estate_ai_search/.env` - Main environment variables (API keys)
- `/real_estate_search/config.yaml` - Elasticsearch and search settings
- `/squack_pipeline/config.yaml` - Pipeline and embedding settings

### Environment Variable Loading

The `real_estate_search` module specifically loads the `.env` file from the **parent directory**:

```python
# real_estate_search/config/config.py
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
```

This allows all modules to share a single `.env` file at the project root.

## Available Embedding Providers

### 1. Voyage AI (Recommended for Production)
```yaml
embedding:
  provider: voyage
  model_name: voyage-3
  dimension: 1024
```
Requires: `VOYAGE_API_KEY` in `.env`

### 2. OpenAI
```yaml
embedding:
  provider: openai
  model_name: text-embedding-3-small
  dimension: 1536
```
Requires: `OPENAI_API_KEY` in `.env`

### 3. Google Gemini
```yaml
embedding:
  provider: gemini
  model_name: models/embedding-001
  dimension: 768
```
Requires: `GOOGLE_API_KEY` in `.env`

### 4. Ollama (Local, No API Key Required)
```yaml
embedding:
  provider: ollama
  model_name: nomic-embed-text
  dimension: 768
```
Requires: Ollama server running locally

## Running Search Demos

### List All Available Demos
```bash
python -m real_estate_search.management demo --list
```

### Run Specific Demos

```bash
# Basic property search
python -m real_estate_search.management demo 1

# Geo-distance search
python -m real_estate_search.management demo 3

# Vector similarity search
python -m real_estate_search.management demo 7

# Wikipedia full-text search
python -m real_estate_search.management demo 10

# Multi-index hybrid search
python -m real_estate_search.management demo 11
```

## Testing and Validation

### Run Tests
```bash
# Run all tests
pytest

# Run specific test modules
pytest squack_pipeline/tests/
pytest real_estate_search/tests/

# Run integration tests
pytest squack_pipeline/integration_tests/
```

### Validate Pipeline Output
```bash
# Validate Parquet files
python -m pytest squack_pipeline/integration_tests/test_parquet_validation.py

# Check Elasticsearch data
python squack_pipeline/scripts/verify_elasticsearch.py

# Validate embeddings
python -m common_embeddings.main evaluate
```

## Common Commands

### Pipeline Commands
```bash
# Full pipeline
python -m squack_pipeline

# Test mode (small sample)
python -m squack_pipeline --test-mode

# Specific data type only
python -m squack_pipeline --data-type properties
python -m squack_pipeline --data-type wikipedia

# Validate without running
python -m squack_pipeline --validate-only
```

### Elasticsearch Management
```bash
# Setup indices
python -m real_estate_search.management setup-indices --clear

# Check index health
curl -X GET "localhost:9200/_cluster/health?pretty"

# Count documents
curl -X GET "localhost:9200/properties/_count?pretty"

# Delete all indices (WARNING: destroys data)
curl -X DELETE "localhost:9200/properties,neighborhoods,wiki_*"
```

### Debugging Commands
```bash
# Check API key is loaded
python -c "import os; print('VOYAGE_API_KEY set:', bool(os.getenv('VOYAGE_API_KEY')))"

# Test Elasticsearch connection
curl -X GET "localhost:9200/_cluster/health?pretty"
# If authentication is required, use ES_PASSWORD from .env:
# curl -u elastic:$ES_PASSWORD -X GET "localhost:9200/_cluster/health?pretty"

# View sample data
python -c "import json; print(json.dumps(json.load(open('real_estate_data/properties_sf.json'))[0], indent=2))"
```

## Troubleshooting

### Issue: "API key not found"
**Solution**: Ensure `.env` file exists in the project root with:
```
VOYAGE_API_KEY=your-actual-api-key
```

### Issue: "Connection refused to Elasticsearch"
**Solution**: Start Elasticsearch:
```bash
docker start elasticsearch  # If using Docker
# OR
brew services start elasticsearch  # On macOS with Homebrew
```

### Issue: "Index not found"
**Solution**: Create indices first:
```bash
python -m real_estate_search.management setup-indices --clear
```

### Issue: "No documents in index"
**Solution**: Run the data pipeline:
```bash
python -m squack_pipeline
```

### Issue: Pipeline hangs on embeddings
**Solution**: Use smaller batch size or sample size:
```bash
python -m squack_pipeline --sample-size 10 --config squack_pipeline/config.yaml
```

## Project Structure Overview

```
real_estate_ai_search/
├── .env                           # API keys (create from .env.example)
├── squack_pipeline/               # Spark pipeline for data processing
│   ├── config.yaml               # Pipeline configuration
│   └── __main__.py               # Entry point
├── real_estate_search/            # Elasticsearch RAG implementation
│   ├── config.yaml               # Search configuration
│   ├── management/               # CLI commands
│   └── demo_queries/             # Example searches
├── graph_real_estate/            # Neo4j GraphRAG implementation
├── common_embeddings/            # Embedding evaluation tools
└── real_estate_data/             # Source data files
```

## Advanced Features

### Custom Embedding Configuration

Edit `squack_pipeline/config.yaml`:
```yaml
embedding:
  provider: voyage
  model_name: voyage-3
  batch_size: 10
  dimension: 1024
```

### Multi-Index Search

The system supports searching across multiple indices:
- Properties
- Neighborhoods
- Wikipedia chunks
- Wikipedia summaries

### Hybrid Search Capabilities

Combines:
- **Vector Search**: Semantic similarity using embeddings
- **Full-Text Search**: BM25 relevance scoring
- **Geo Search**: Distance-based ranking
- **Faceted Search**: Filter by property type, price range, etc.

## Performance Tips

1. **Use batch processing**: Process data in batches for better performance
2. **Adjust thread count**: Modify `parallel_threads` in config
3. **Enable caching**: Use Elasticsearch query cache
4. **Optimize embeddings**: Use appropriate batch sizes for your provider
5. **Monitor resources**: Check CPU/memory usage during pipeline runs

## Next Steps

1. **Explore demos**: Run all demos to understand capabilities
2. **Customize searches**: Modify demo queries for your use case
3. **Add data**: Extend with your own property/location data
4. **Tune embeddings**: Compare different embedding models
5. **Deploy API**: Use FastAPI endpoints for production

## Support

For issues or questions:
1. Check this guide first
2. Review module-specific READMEs
3. Check integration test files for examples
4. Review error logs with `--log-level DEBUG`