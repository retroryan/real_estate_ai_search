# Graph Manager - Neo4j Database Management Tool

## Overview

The `graph_manager.sh` script provides a comprehensive interface for managing the Neo4j graph database in the Real Estate AI Search system. It handles database initialization, data loading from the SQUACK pipeline, relationship building, and monitoring.

## Features

- 🗄️ **Database Management**: Clear, initialize, and rebuild the graph database
- 📊 **Data Loading**: Integrate with SQUACK pipeline v2 for Neo4j data ingestion
- 🔗 **Relationship Building**: Create graph relationships after data loading
- 📈 **Statistics & Health**: Monitor database health and view detailed statistics
- 🔍 **Query Testing**: Run sample queries to verify data integrity
- 🎯 **Demo Execution**: Run pre-built demonstration queries

## Prerequisites

1. **Neo4j Database** running on `localhost:7687`
2. **Python Virtual Environment** at `.venv` with required packages:
   - neo4j
   - python-dotenv
   - pydantic
   - pyyaml
3. **Environment Variables** in `.env`:
   ```bash
   NEO4J_PASSWORD=your_password
   VOYAGE_API_KEY=your_api_key  # For embeddings
   ```

## Installation

```bash
# Make the script executable
chmod +x graph_manager.sh

# Install required Python packages
source .venv/bin/activate
pip install neo4j python-dotenv pydantic pyyaml
```

## Usage

### Command Line Mode

```bash
# Show help
./graph_manager.sh help

# Clear all data from Neo4j
./graph_manager.sh clear

# Initialize database schema (constraints and indexes)
./graph_manager.sh init

# Load data from SQUACK pipeline (with sample size)
./graph_manager.sh load 10

# Build graph relationships
./graph_manager.sh build

# Full rebuild (clear + init + load + build)
./graph_manager.sh rebuild 50

# Run sample query
./graph_manager.sh query

# Show database statistics
./graph_manager.sh stats

# Run demonstration (1-7)
./graph_manager.sh demo 1

# Quick setup (init + load 10 samples + build)
./graph_manager.sh quick
```

### Interactive Mode

Run without arguments for an interactive menu:

```bash
./graph_manager.sh
```

This displays:
```
╔════════════════════════════════════════════════════════════╗
║           Neo4j Graph Database Manager                     ║
╚════════════════════════════════════════════════════════════╝

1) Clear Database         - Remove all data from Neo4j
2) Initialize Schema      - Create constraints and indexes
3) Load Data             - Run SQUACK pipeline to load data
4) Build Relationships   - Create graph relationships
5) Rebuild Full         - Clear and rebuild everything
6) Run Sample Query     - Execute a sample query
7) Show Statistics      - Display database health and stats
8) Run Demo            - Run demonstration queries
9) Quick Setup         - Initialize + Load (10 samples) + Build
0) Exit
```

## Workflow Examples

### Complete Setup from Scratch

```bash
# 1. Clear any existing data
./graph_manager.sh clear

# 2. Initialize schema
./graph_manager.sh init

# 3. Load data from SQUACK pipeline
./graph_manager.sh load 20

# 4. Build relationships
./graph_manager.sh build

# 5. Verify the setup
./graph_manager.sh stats
./graph_manager.sh query
```

### Quick Setup for Testing

```bash
# One command to setup with 10 samples
./graph_manager.sh quick
```

### Full Rebuild with Custom Sample Size

```bash
# Rebuild everything with 100 samples
./graph_manager.sh rebuild 100
```

## Database Statistics Output

The `stats` command provides comprehensive database information:

```
📊 Node Statistics:
  Property                    420 nodes
  Neighborhood                 21 nodes
  WikipediaArticle            464 nodes
  Feature                     437 nodes
  PropertyType                  7 nodes
  PriceRange                    9 nodes
  City                          1 nodes
  State                         5 nodes
  ZipCode                      22 nodes
  TOTAL                     1,386 nodes

🔗 Relationship Statistics:
  LOCATED_IN                    2 relationships
  HAS_FEATURE                  13 relationships
  IN_CITY                       2 relationships
  IN_STATE                      1 relationships
  IN_ZIP_CODE                   2 relationships
  TYPE_OF                       2 relationships
  IN_PRICE_RANGE                2 relationships
  TOTAL                        24 relationships

🔐 Constraints: 18 active
🔍 Indexes: 59 active

✅ Health Status:
  Database:     HEALTHY
  Connectivity: OK
  Data Present: YES (1,386 nodes)
```

## Data Flow

1. **SQUACK Pipeline v2** → Processes raw data through Bronze/Silver/Gold layers
2. **Neo4j Writer** → Writes graph nodes and relationships to Neo4j
3. **Graph Real Estate** → Builds additional relationships and indexes
4. **Query/Demo** → Verify and demonstrate the graph capabilities

## Integration with SQUACK Pipeline

The script integrates with SQUACK pipeline v2 through the `neo4j.config.yaml` configuration:

```yaml
output:
  neo4j:
    enabled: true
    uri: bolt://localhost:7687
    username: neo4j
    database: neo4j
```

When you run `./graph_manager.sh load 10`, it executes:
```bash
python -m squack_pipeline_v2 \
    --config squack_pipeline_v2/neo4j.config.yaml \
    --sample-size 10
```

## Troubleshooting

### Neo4j Connection Issues
```bash
# Check if Neo4j is running
docker ps | grep neo4j

# Start Neo4j if needed
docker-compose up -d neo4j
```

### Virtual Environment Issues
```bash
# Ensure virtual environment exists
python -m venv .venv

# Activate and install dependencies
source .venv/bin/activate
pip install -r requirements.txt
```

### Data Not Loading
```bash
# Check SQUACK pipeline logs
./graph_manager.sh load 2  # Start with small sample

# Verify environment variables
cat .env | grep NEO4J_PASSWORD
cat .env | grep VOYAGE_API_KEY
```

## Performance Considerations

- **Small samples (1-10)**: Quick testing and development
- **Medium samples (10-50)**: Integration testing
- **Large samples (50-500)**: Performance testing
- **Full dataset**: Production deployment

## Color Coding

The script uses colors for different message types:
- 🟢 Green: Success messages
- 🔴 Red: Error messages
- 🟡 Yellow: Warning messages
- 🔵 Blue: Information messages
- 🟣 Cyan: Headers and sections

## Related Documentation

- [GRAPH_FTW.md](GRAPH_FTW.md) - Neo4j integration proposal and implementation
- [GRAPH_IN_DEPTH.md](GRAPH_IN_DEPTH.md) - Detailed graph pipeline documentation
- [CLAUDE.md](CLAUDE.md) - Overall project guide

## Future Enhancements

- [ ] Add backup/restore functionality
- [ ] Support for remote Neo4j instances
- [ ] Batch processing for large datasets
- [ ] Performance metrics and timing
- [ ] Export/import graph snapshots
- [ ] Automated testing suite integration