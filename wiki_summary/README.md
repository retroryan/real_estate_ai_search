# Wikipedia Summarization Pipeline

A cutting-edge generative AI content classification and summarization system powered by **DSPy**, the Stanford framework for programming—not prompting—foundation models. This pipeline demonstrates advanced LLM orchestration techniques for intelligent content extraction, classification, and structured data generation.

## Brief Overview

The pipeline leverages multiple generative AI technologies to transform unstructured Wikipedia content into structured, queryable knowledge suitable for RAG and GraphRAG applications:

### 🤖 Generative AI Technologies

**Core AI Frameworks:**
- **DSPy (Declarative Self-improving Python)** - Stanford's framework for systematic LLM programming
  - `dspy.ChainOfThought` for multi-step reasoning and classification
  - `dspy.Predict` for direct structured predictions
  - `dspy.signatures` for type-safe prompt templates
  - Automatic prompt optimization and few-shot learning

**LLM Providers & Models:**
- **OpenRouter** - Gateway to 100+ language models
  - Default: `openrouter/openai/gpt-4o-mini` for cost-effective processing
  - Support for GPT-4, Claude, Llama, and other models
- **OpenAI API** - Direct access to GPT models
- **Google Gemini** - Advanced multimodal understanding
- **Ollama** - Local LLM deployment for privacy-sensitive applications

**AI Techniques & Algorithms:**
- **Chain-of-Thought (CoT) Reasoning** - Step-by-step logical analysis for location classification
- **Structured Data Extraction** - Converting unstructured text to typed Pydantic models
- **Confidence Scoring** - Probabilistic assessment of extraction quality
- **Content Classification Pipeline** - Multi-stage filtering and categorization
- **Semantic Caching** - Intelligent response caching based on content similarity
- **Relevance Filtering** - Domain-specific content evaluation using LLM reasoning

**Data Processing Capabilities:**
- **Dual Summary Generation** - Short (100 words) and long (500 words) contextual summaries
- **Location Intelligence** - Automatic extraction and validation of geographic entities
- **Topic Modeling** - Key topic identification and categorization
- **Knowledge Graph Preparation** - Structured data ready for Neo4j GraphRAG integration

## Quick Start

### Prerequisites
- Python 3.8+ (3.10+ recommended)
- 4GB RAM minimum  
- API key for OpenRouter/OpenAI
- Existing Wikipedia database at `data/wikipedia/wikipedia.db`

### Installation (Virtual Environment Required)

```bash
# Navigate to wiki_summary directory
cd wiki_summary

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp wiki_summary/.env.example wiki_summary/.env
# Edit wiki_summary/.env with your OpenRouter API key
```

### Basic Usage

**Run from wiki_summary directory with virtual environment:**

```bash
# Navigate to wiki_summary directory
cd /path/to/property_finder/wiki_summary

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate     # On Windows

# Run with no limit (processes all articles)
python main.py

# Process specific number of articles
python main.py --limit 5
python main.py --limit 10

# Process larger batches
python main.py --limit 50

# Force complete resummarization (clears cache and regenerates all)
python main.py --force-reprocess

# Force resummarization with limit
python main.py --force-reprocess --limit 100

# For full processing
python main.py --limit 600 --force-reprocess

# When done, deactivate
deactivate
```

**Alternative: Use the convenience script (auto-activates venv):**
```bash
cd /path/to/property_finder/wiki_summary
./run_wiki_summary.sh --limit 10
```

**Environment Configuration**: 
- The `.env` file must be located at `wiki_summary/.env`
- The module automatically loads `.env` from current directory
- **Required**: Set `OPENROUTER_API_KEY` in the `.env` file

### Database Validation Tool

The module includes a comprehensive database validation tool to check integrity and data quality:

```bash
# Run full database validation
python wiki_summary/validate_db.py

# Output validation results as JSON
python wiki_summary/validate_db.py --json

# Validate a different database
python wiki_summary/validate_db.py --db path/to/database.db
```

The validation tool checks:
- **Table existence**: Verifies all required tables exist
- **Referential integrity**: Checks foreign key relationships
- **Duplicate records**: Identifies duplicate entries
- **Location validity**: Finds mismatched or invalid locations
- **Data quality**: Checks for incomplete summaries and low confidence scores
- **Orphaned records**: Identifies unused locations and unprocessed articles
- **Index effectiveness**: Verifies proper database indexing

### Validating Summaries

After running the pipeline, validate that summaries are being created:

```sql
-- Check summary count
sqlite3 data/wikipedia/wikipedia.db "SELECT COUNT(*) FROM page_summaries;"

-- View recent summaries
sqlite3 data/wikipedia/wikipedia.db "SELECT title, SUBSTR(short_summary, 1, 100) || '...' as summary_preview, overall_confidence FROM page_summaries ORDER BY processed_at DESC LIMIT 5;"

-- Check flagged content analysis
sqlite3 data/wikipedia/wikipedia.db "SELECT relevance_category, COUNT(*) FROM flagged_content GROUP BY relevance_category;"

-- View highly relevant articles
sqlite3 data/wikipedia/wikipedia.db "SELECT title, overall_score, reasons_to_keep FROM flagged_content WHERE relevance_category = 'highly_relevant';"
```

## Force Reprocessing

The `--force-reprocess` flag allows you to completely regenerate all summaries:

```bash
# Force complete resummarization of entire database
python -m wiki_summary --force-reprocess
```

This will:
1. **Clear the cache directory** (`.cache/summaries/`) - removes all cached LLM responses
2. **Delete all existing summaries** from `page_summaries` table
3. **Delete all flagged content** from `flagged_content` table  
4. **Regenerate everything** using fresh LLM calls

Use cases:
- After updating the LLM prompt or model
- After fixing issues with the summarization logic
- To refresh summaries with latest LLM capabilities
- When relevance scoring methodology changes

**Note**: This will use significant API credits as it regenerates all summaries.

## Configuration

The pipeline uses Pydantic models for type-safe configuration with environment variable support:

```bash
# Required environment variables in .env
OPENROUTER_API_KEY=your_openrouter_api_key_here  # REQUIRED for OpenRouter models
LLM_MODEL=openrouter/openai/gpt-4o-mini          # Model to use

# Optional configuration
LLM_TEMPERATURE=0.3                              # Default: 0.3
LLM_MAX_TOKENS=2000                              # Default: 2000
DATABASE_PATH=data/wikipedia/wikipedia.db        # Default path
CACHE_ENABLED=true                               # Default: true
```

## Caching System

The pipeline includes a file-based caching system to reduce API costs during development:

### Cache Location
```
.cache/summaries/
```
Cache files are stored as JSON with filenames like `{page_id}_{content_hash}.json`

### How Caching Works

1. **Cache Key Generation**: Created from Wikipedia page ID + MD5 hash of content (first 12 chars)
   - Ensures cache invalidates if content changes
   - Example: `137018_86290dfca6a4.json`

2. **Cache Check**: Before calling the LLM, the system checks for cached results
   - If found, returns cached summary immediately
   - Logs "Using cached summary for page {page_id}"

3. **Cache Storage**: After LLM processing, results are saved to cache
   - Includes all summary data, location info, and confidence scores
   - Stored as formatted JSON for debugging

4. **Cache Control**:
   - Enabled by default (`CACHE_ENABLED=true` in .env)
   - Controlled via `use_cache` parameter in WikipediaExtractAgent
   - Can be disabled with `CACHE_ENABLED=false`

### What Gets Cached

The cached JSON includes:
- Short and long summaries
- Key topics list
- Location data (city, county, state)
- Confidence scores
- Processing metadata

### Managing the Cache

```bash
# View cache statistics
ls -la .cache/summaries/ | wc -l  # Count cached files
du -sh .cache/summaries/           # Total cache size

# Clear cache manually
rm -rf .cache/summaries/

# Force reprocessing (clears cache automatically)
python -m wiki_summary --force-reprocess

# Disable caching temporarily
CACHE_ENABLED=false python -m wiki_summary --limit 10
```

### Benefits

- **Cost Reduction**: Avoids redundant LLM API calls during development
- **Faster Iteration**: Re-runs use cached results for unchanged content
- **Debugging**: Cache files are human-readable JSON for inspection
- **Content-aware**: Cache invalidates automatically when article content changes

## New Database-Centric Design

### Database Schema

The pipeline uses SQLite database with enhanced tables:

#### `locations` Table (Updated)
Flexible location storage without type constraints:
```sql
CREATE TABLE locations (
    location_id INTEGER PRIMARY KEY AUTOINCREMENT,
    country TEXT NOT NULL DEFAULT 'United States',
    state TEXT NOT NULL,
    county TEXT NOT NULL,
    location TEXT,
    location_type TEXT,  -- No constraints - accepts any type
    location_type_category TEXT,  -- Broader category
    llm_suggested_type TEXT,  -- Original LLM suggestion
    confidence REAL DEFAULT 0.0,
    needs_review INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `page_summaries` Table
Stores processed article summaries with dual summary lengths:
```sql
CREATE TABLE page_summaries (
    page_id INTEGER PRIMARY KEY,
    article_id INTEGER,
    title TEXT,
    short_summary TEXT NOT NULL,  -- ~100 words
    long_summary TEXT NOT NULL,   -- ~500 words
    key_topics TEXT,
    best_city TEXT,
    best_state TEXT,
    overall_confidence REAL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `flagged_content` Table
Correctly tracks articles to flag (non-Utah/California):
```sql
CREATE TABLE flagged_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER,
    title TEXT NOT NULL,
    overall_score REAL,
    location_score REAL,
    re_score REAL,
    geo_score REAL,
    relevance_category TEXT,  -- 'highly_relevant', 'marginal_relevance', 'flagged_for_removal'
    reasons_to_flag TEXT,  -- e.g., "Not Utah/California location: Colorado"
    reasons_to_keep TEXT,  -- e.g., "Utah/California location: Park City"
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `removed_content` Table
Tracks articles removed as out-of-scope:
```sql
CREATE TABLE removed_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id INTEGER,
    title TEXT NOT NULL,
    html_file TEXT,
    detected_state TEXT,
    detected_city TEXT,
    detected_county TEXT,
    removed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reason TEXT DEFAULT 'Outside Utah/California scope'
);
```

### Automatic Content Filtering (Fixed)

The pipeline now correctly filters articles:
- **KEEPS Utah/California articles**: All articles primarily about Utah or California locations
- **FLAGS non-Utah/California articles**: Articles about other states marked for removal
- **Flexible location types**: Accepts any type (ski_resort, state_park, botanical_garden, etc.)
- **Confidence-based review**: Low-confidence classifications flagged for manual review

Flagging logic:
1. Articles classified by location using DSPy Chain-of-Thought
2. Non-Utah/California articles flagged with reason
3. Utah/California articles scored by real estate relevance
4. All evaluations stored in `flagged_content` table

### Core Components (Enhanced)

1. **WikipediaSummarizationPipeline**: Main orchestrator with database integration
2. **WikipediaExtractAgent**: DSPy-based extraction with Chain-of-Thought reasoning
3. **LocationClassificationCoT**: Flexible location type classification module
4. **FlexibleLocationService**: Handles any location type without constraints
5. **IntegratedLocationEvaluator**: Combines classification, database updates, and flagging
6. **RealEstateRelevanceFilter**: Fixed filtering logic (flags non-Utah/California)
7. **PipelineConfig**: Type-safe configuration with Pydantic models

### Processing Flow (Updated)

1. **Article Retrieval**: Query ALL articles from `data/wikipedia/wikipedia.db`
2. **Location Classification**: Use DSPy to classify location type and state
3. **Flagging Logic**: Flag non-Utah/California articles, keep Utah/California
4. **Relevance Scoring**: Score Utah/California articles by real estate relevance
5. **DSPy Processing**: Generate summaries for relevant articles using Chain-of-Thought
6. **Database Storage**: Persist summaries in `page_summaries` table
7. **Analysis Reporting**: Query database for comprehensive statistics

## Output & Analysis

### Generated Data
- **Dual summaries**: Short (~100 words) and long (~500 words) summaries with confidence scores
- **Key topics**: 3-5 relevant topics per article
- **Location extraction**: City, county, state with validation
- **Relevance scoring**: Multi-dimensional analysis (location, real estate, geography)

### Database Benefits
- **Persistent storage**: Data survives between runs
- **SQL queryable**: Complex analysis and filtering capabilities  
- **Integrated**: Uses existing Wikipedia database infrastructure
- **Scalable**: Handles large article volumes efficiently
- **Traceable**: Full audit trail with timestamps

## Quality Metrics

- **Processing Success Rate**: 20-80% depending on content relevance
- **Confidence Scores**: 0.70-0.95 for relevant articles  
- **Relevance Filtering**: Automatically flags non-real estate content
- **Geographic Focus**: Utah/California with broader regional context

## Demo Ready

This implementation is optimized for demonstrations with:
- Clear logging and progress indicators
- Comprehensive error handling with visible warnings
- Type-safe configuration and data models
- Automated quality control reports
- Professional command-line interface

## Example Queries & Validation

### Common Analysis Queries

```sql
-- Summary statistics
SELECT 
    COUNT(*) as total_summaries,
    AVG(overall_confidence) as avg_confidence,
    MIN(overall_confidence) as min_confidence,
    MAX(overall_confidence) as max_confidence
FROM page_summaries;

-- Recent processing activity
SELECT 
    DATE(processed_at) as date,
    COUNT(*) as summaries_created
FROM page_summaries 
GROUP BY DATE(processed_at) 
ORDER BY date DESC;

-- Relevance breakdown
SELECT 
    relevance_category,
    COUNT(*) as count,
    ROUND(AVG(overall_score), 2) as avg_score
FROM flagged_content 
GROUP BY relevance_category;

-- Articles with issues
SELECT title, reasons_to_flag 
FROM flagged_content 
WHERE reasons_to_flag IS NOT NULL 
ORDER BY overall_score ASC;
```

### Integration with Existing Data

The pipeline integrates with the existing Wikipedia crawl database:
```sql
-- Join summaries with original articles
SELECT 
    a.title,
    a.url,
    ps.summary,
    ps.overall_confidence,
    fc.relevance_category
FROM articles a
LEFT JOIN page_summaries ps ON a.pageid = ps.page_id
LEFT JOIN flagged_content fc ON a.id = fc.article_id
WHERE ps.summary IS NOT NULL;
```

## File Structure

```
wiki_summary/
├── main.py                          # Main pipeline orchestrator
├── config.py                        # Pydantic configuration models
├── validate_db.py                   # Database validation tool
├── requirements.txt                 # Python dependencies
├── .env                            # Configuration (API keys, settings)
├── models/                         # Data models
│   └── location.py                 # Location-related Pydantic models
├── services/                       # Service layer (ENHANCED)
│   ├── location.py                 # Location management service
│   ├── flagged_content.py          # Flagged content persistence
│   ├── flexible_location.py        # NEW: Flexible location type handling
│   └── integrated_location_evaluator.py # NEW: Integrated classification & flagging
├── evaluation/                     # Evaluation and filtering (FIXED)
│   ├── relevance_filter.py         # Fixed flagging logic (non-UT/CA flagged)
│   └── metrics.py                  # Evaluation metrics
├── summarize/                      # Summarization components (ENHANCED)
│   ├── extract_agent.py            # DSPy extraction agent with classifier
│   ├── location_classifier.py      # NEW: DSPy location classification module
│   ├── models.py                   # Summary data models  
│   ├── signatures.py               # Enhanced DSPy signatures with flexible types
│   ├── cache.py                    # Response caching system
│   └── html_parser.py              # HTML location extraction
└── shared/                         # Shared utilities
    └── llm_utils.py                # LLM configuration utilities
```

## Recent Improvements (2025-08-19)

### Flexible Location Classification
- **No type constraints**: Accepts any location type (ski_resort, botanical_garden, etc.)
- **DSPy Chain-of-Thought**: Enhanced accuracy in classification
- **New type discovery**: Tracks and reports newly discovered location types
- **Confidence scoring**: Flags low-confidence classifications for review

### Fixed Flagging Logic
- **Corrected inversion**: Now properly flags non-Utah/California articles
- **Integrated evaluation**: Combines classification with relevance scoring
- **Test verified**: 100% accuracy on test cases
- **Clear reasoning**: Provides explanations for flagging decisions

### Enhanced Database Schema
- **Flexible locations table**: No CHECK constraints on location_type
- **Metadata tracking**: Added confidence, needs_review, and category fields
- **Migration support**: Safe schema migration with automatic backup
- **Performance indexes**: Optimized for querying by state and type

### New Services
- **FlexibleLocationService**: Handles any location type gracefully
- **IntegratedLocationEvaluator**: One-stop service for classification and flagging
- **LocationClassificationCoT**: DSPy module for location classification

### Database Integrity
- Comprehensive validation tool (`validate_db.py`)
- Automatic cleanup of orphaned records
- Referential integrity enforcement
- Idempotent operations for safe reruns

## Troubleshooting

### Common Issues and Solutions

#### Articles Not Being Flagged Correctly
```bash
# Check how an article was classified
sqlite3 data/wikipedia/wikipedia.db "SELECT * FROM flagged_content WHERE title LIKE '%YourArticle%';"

# View removed articles
sqlite3 data/wikipedia/wikipedia.db "SELECT title, detected_state, reason FROM removed_content ORDER BY removed_at DESC LIMIT 10;"
```

#### Summaries Not Being Saved
```bash
# Validate database integrity
python wiki_summary/validate_db.py

# Check for orphaned summaries
sqlite3 data/wikipedia/wikipedia.db "SELECT COUNT(*) FROM page_summaries WHERE article_id NOT IN (SELECT id FROM articles);"
```

#### Location Mismatches
```bash
# Find articles with location issues
sqlite3 data/wikipedia/wikipedia.db "SELECT a.title, l.state FROM articles a JOIN locations l ON a.location_id = l.location_id WHERE a.title LIKE '%Illinois%' AND l.state = 'Utah';"

# Check removed content for location issues
sqlite3 data/wikipedia/wikipedia.db "SELECT title, detected_state FROM removed_content WHERE detected_state NOT IN ('Utah', 'California', '');"
```

#### API Rate Limits
- Add delays between batches: Process smaller limits with breaks
- Check API usage on OpenRouter dashboard
- Consider using cached responses during development

#### Memory Issues
- Process smaller batches: `--limit 10` instead of `--limit 100`
- Clear cache periodically: `rm -rf .cache/summaries/`
- Monitor memory usage during processing

## Virtual Environment Setup Guide

### Why Use a Virtual Environment?

The wiki_summary module requires specific versions of pydantic and pydantic-settings that may conflict with other projects. Using a virtual environment ensures clean, isolated dependencies.

### Complete Setup Instructions

#### 1. Initial Setup (One Time)

```bash
# Navigate to the wiki_summary directory
cd /path/to/property_finder/wiki_summary

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate     # On Windows

# Upgrade pip (recommended)
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Create .env file from template
cp .env.example .env
# Edit .env and add your API keys
```

#### 2. Running the Module

**ALWAYS activate the virtual environment before running:**

```bash
# Navigate to wiki_summary directory
cd /path/to/property_finder/wiki_summary

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate     # On Windows

# Run the module (from wiki_summary directory)
python main.py --limit 10

# For full processing with force reprocess
python main.py --limit 600 --force-reprocess
```

#### 3. Deactivating Virtual Environment

```bash
# When done, deactivate the virtual environment
deactivate
```

#### If You Encounter Version Conflicts

```bash
# Clean reinstall
deactivate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Common Virtual Environment Issues

#### "Module not found" Errors
- Ensure virtual environment is activated (you should see `(venv)` in prompt)
- Verify you're in the wiki_summary directory
- Check installation: `pip list | grep pydantic`

#### Wrong Python Version
```bash
# Check Python version
python --version

# If needed, specify Python version when creating venv
python3.10 -m venv venv
```

#### Permission Errors
```bash
# If you get permission errors, use --user flag
pip install --user -r requirements.txt
```

### Automation Script

Create a run script for convenience:

```bash
# Create run_wiki_summary.sh in wiki_summary/
cat > run_wiki_summary.sh << 'EOF'
#!/bin/bash
source venv/bin/activate
python main.py "$@"
deactivate
EOF

chmod +x run_wiki_summary.sh

# Use it
./run_wiki_summary.sh --limit 10
```