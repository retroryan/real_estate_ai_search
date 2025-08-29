# Real Estate AI Search - GitHub Copilot Instructions

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Bootstrap and Environment Setup
- **Prerequisites**: Python 3.10+ required (repository uses Python 3.12+ features)
- **Quick validation (no dependencies)**: 
  ```bash
  # Test immediately without any installations
  python real_estate_data/validate_property_data.py
  python -c "import json; print(f'Properties: {len(json.load(open(\"real_estate_data/properties_sf.json\")))}')"
  ```
- **Create virtual environment**: 
  ```bash
  python -m venv venv
  source venv/bin/activate  # On Windows: venv\Scripts\activate
  ```
- **Environment configuration**: 
  ```bash
  cp .env.example .env
  # Edit .env and add your API keys:
  # VOYAGE_API_KEY=your-voyage-api-key-here
  # GOOGLE_API_KEY=your-gemini-api-key-here
  # OPENAI_API_KEY=your-openai-key-here
  # NEO4J_URI=bolt://localhost:7687
  # NEO4J_USERNAME=neo4j
  # NEO4J_PASSWORD=password
  ```

### Dependencies Installation
- **NEVER CANCEL**: Dependency installation takes 15-25 minutes with complex AI framework dependencies. Set timeout to 30+ minutes.
- **Primary method**: `pip install -e .` -- installs as editable package using pyproject.toml
- **Fallback method**: `pip install -r requirements.txt` -- if pyproject.toml installation fails due to missing dependencies
- **Known issue**: Some dependencies (property_finder_models, api_client) may not be available in all environments
- **Development dependencies**: `pip install -e .[dev]` -- includes pytest, black, ruff, mypy

### Build and Test
- **Run all tests**: `pytest` -- takes 10-15 minutes. NEVER CANCEL. Set timeout to 20+ minutes.
- **Run specific module tests**: 
  ```bash
  pytest data_pipeline/tests/          # Data pipeline unit tests
  pytest data_pipeline/integration_tests/  # Integration tests - takes 5-10 minutes
  pytest real_estate_search/tests/    # Elasticsearch search tests
  pytest graph_real_estate/tests/     # Neo4j GraphRAG tests
  ```
- **Run integration validation**: `pytest data_pipeline/integration_tests/test_parquet_validation.py`

### Core Application Setup
- **Elasticsearch setup** (required for search functionality):
  ```bash
  # Start Elasticsearch with Docker
  docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 \
    -e "discovery.type=single-node" -e "xpack.security.enabled=false" \
    docker.elastic.co/elasticsearch/elasticsearch:8.11.0
  
  # Create indices with proper mappings
  python -m real_estate_search.management setup-indices --clear
  ```
- **Neo4j setup** (optional, for GraphRAG):
  ```bash
  cd graph_real_estate
  docker-compose up -d
  ```

### Data Pipeline Execution
- **NEVER CANCEL**: Full pipeline takes 30-60 minutes depending on dataset size. Set timeout to 90+ minutes.
- **Full pipeline**: `python -m data_pipeline` -- processes all data types (properties, neighborhoods, Wikipedia)
- **Development mode**: `python -m data_pipeline --sample-size 10` -- for testing, takes 5-10 minutes
- **Specific data types**: 
  ```bash
  python -m data_pipeline --data-type properties
  python -m data_pipeline --data-type wikipedia
  ```

## Validation

### Manual Validation Scenarios
- **ALWAYS validate data integrity first** by running the built-in validation script:
  ```bash
  python real_estate_data/validate_property_data.py  # Should show "ALL VALIDATIONS PASSED!"
  ```
- **Always validate search functionality after making changes** by running complete search demos:
  ```bash
  # List all available demos
  python -m real_estate_search.management demo --list
  
  # Test basic property search (validates core functionality)
  python -m real_estate_search.management demo 1
  
  # Test vector similarity search (validates embedding pipeline)
  python -m real_estate_search.management demo 7
  
  # Test Wikipedia full-text search (validates content indexing)
  python -m real_estate_search.management demo 10
  
  # Test rich property listing (validates complete integration)
  python -m real_estate_search.management demo 15
  ```
- **Verify Elasticsearch data**: 
  ```bash
  curl -X GET "localhost:9200/_cluster/health?pretty"  # Should show green status
  curl -X GET "localhost:9200/properties/_count?pretty"  # Should show document count > 0
  ```
- **Test data pipeline outputs**: Check that Parquet files are created in `data/parquet/` directory
- **Validate embedding generation**: `python -m common_embeddings.main evaluate`
- **Test without dependencies**: Use data validation for quick testing without installing AI dependencies

### Pre-commit Validation
- **Data validation (no dependencies required)**: `python real_estate_data/validate_property_data.py` -- must show "ALL VALIDATIONS PASSED!"
- **Always run linting before committing**: `ruff check .` and `black --check .`
- **Type checking**: `mypy data_pipeline/` -- optional but recommended
- **Integration smoke test**: `python -m real_estate_search.management demo 1` -- must complete successfully

## Common Tasks

### Repository Structure (Reference)
```
real_estate_ai_search/
├── .env                           # API keys configuration
├── data_pipeline/                 # Spark-based ETL pipeline (main processing engine)
│   ├── __main__.py               # Entry point: python -m data_pipeline
│   ├── config.yaml               # Pipeline configuration
│   ├── integration_tests/        # 30-60 minute integration tests
│   └── tests/                    # Unit tests
├── real_estate_search/            # Elasticsearch RAG implementation
│   ├── management/               # CLI: python -m real_estate_search.management
│   ├── demo_queries/             # 15 pre-built search demos
│   └── config.yaml               # Search configuration
├── graph_real_estate/            # Neo4j GraphRAG implementation
│   ├── search_properties.py     # Main search interface
│   └── docker-compose.yml        # Neo4j container setup
├── common_embeddings/            # Embedding evaluation and comparison
├── squack_pipeline/              # DuckDB alternative pipeline (WIP)
├── wiki_summary/                 # DSPy-powered Wikipedia summarization
├── wiki_crawl/                   # Wikipedia content crawler
└── real_estate_data/             # Source data files (JSON)
    ├── properties_sf.json        # San Francisco properties (~550 listings)
    ├── properties_pc.json        # Park City properties
    ├── neighborhoods_sf.json     # Neighborhood data
    └── neighborhoods_pc.json
```

### Key Entry Points
- **Main data pipeline**: `python -m data_pipeline`
- **Search management**: `python -m real_estate_search.management [command]`
- **Demo runner script**: `./elastic_demos.sh [demo_number]`
- **GraphRAG search**: `python graph_real_estate/search_properties.py "search query"`
- **Wikipedia summarization**: `python wiki_summary/summarize_main.py --limit 50`

### Frequently Used Commands
```bash
# Check API key configuration
python -c "import os; print('VOYAGE_API_KEY set:', bool(os.getenv('VOYAGE_API_KEY')))"

# Verify Elasticsearch connection
curl -X GET "localhost:9200/_cluster/health?pretty"

# View sample property data
python -c "import json; print(json.dumps(json.load(open('real_estate_data/properties_sf.json'))[0], indent=2))"

# Debug pipeline configuration
python -c "from data_pipeline.config.loader import load_configuration; print(load_configuration())"

# Check embedding generation
python -m common_embeddings.main evaluate

# Quick data validation (no dependencies required)
python real_estate_data/validate_property_data.py
```

### Build Time Expectations
- **Dependency installation**: 15-25 minutes
- **Full test suite**: 10-15 minutes
- **Data pipeline (full)**: 30-60 minutes
- **Data pipeline (sample)**: 5-10 minutes  
- **Integration tests**: 30-60 minutes
- **Demo queries**: 1-2 seconds each
- **Elasticsearch index creation**: 2-5 minutes

## Critical Warnings

### NEVER CANCEL Operations
- **pip install operations**: Can take 25+ minutes due to complex dependencies
- **pytest execution**: Takes 15+ minutes, includes integration tests
- **python -m data_pipeline**: Takes 60+ minutes for full execution
- **Integration tests**: Can run 60+ minutes, include embedding generation
- **Docker image pulls**: Elasticsearch/Neo4j images are large (5-10 minutes)

### Common Issues and Solutions
- **"property_finder_models not found"**: Expected in some environments. Use these fallback commands:
  ```bash
  # Install core dependencies only
  pip install python-dotenv pyyaml pytest
  
  # Test basic functionality without AI dependencies
  python real_estate_data/validate_property_data.py
  ```
- **"Elasticsearch connection refused"**: Start Elasticsearch: `docker start elasticsearch`
- **"No module named 'real_estate_search'"**: Run `pip install -e .` from repository root
- **"API key not found"**: Ensure `.env` file exists with required keys
- **Pipeline hangs on embeddings**: Use `--sample-size 10` for testing
- **Tests fail with timeout**: Increase pytest timeout or run specific test modules
- **Network timeouts during installation**: Some environments may have restricted internet access. Focus on validation scripts that don't require complex dependencies.

### Development vs Production
- **Development**: Always use `--sample-size` parameter to limit data processing
- **Production**: Remove sample size limitations, expect longer execution times
- **Testing**: Use integration tests to validate complete workflows
- **Debugging**: Enable debug logging with `--log-level DEBUG`

## Module-Specific Notes

### data_pipeline/
- **Primary responsibility**: ETL processing with Spark, embedding generation
- **Test command**: `pytest data_pipeline/tests/` (unit) and `pytest data_pipeline/integration_tests/` (integration)
- **Configuration**: `data_pipeline/config.yaml`
- **Entry point**: `python -m data_pipeline`

### real_estate_search/
- **Primary responsibility**: Elasticsearch-based RAG search
- **Test command**: `pytest real_estate_search/tests/`
- **Demo system**: 15 pre-built demos accessible via `python -m real_estate_search.management demo [1-15]`
- **Management CLI**: Full index management via `python -m real_estate_search.management`

### graph_real_estate/
- **Primary responsibility**: Neo4j GraphRAG implementation
- **Setup required**: Docker Compose for Neo4j
- **Test command**: `pytest graph_real_estate/tests/`
- **Search interface**: `python graph_real_estate/search_properties.py "query"`

### common_embeddings/
- **Primary responsibility**: Embedding model evaluation and comparison
- **Test command**: `python -m common_embeddings.main evaluate`
- **Supports**: Voyage AI, OpenAI, Gemini, Ollama embedding providers