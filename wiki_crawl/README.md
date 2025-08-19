# Wikipedia Data Acquisition Module

## Overview

A self-contained Python module for crawling Wikipedia articles related to geographic locations. Features BFS crawling with relevance scoring, proper CC BY-SA 3.0 attribution, and multiple output formats.

## Quick Start

### Installation
```bash
# Install module-specific dependencies
cd wiki_crawl
pip install -r requirements.txt
```

### Basic Commands
```bash
# Crawl a location
python -m wiki_crawl.main crawl "Park City" "Utah" --depth 2 --max-articles 20

# Generate attribution files
python -m wiki_crawl.main attribution

# Analyze crawled data
python -m wiki_crawl.main analyze data/wikipedia/wikipedia.db
```

## Module Structure

```
wiki_crawl/
├── models.py               # Pydantic data models
├── wikipedia_api.py        # Wikipedia API client
├── relevance.py           # Relevance scoring logic
├── database.py            # SQLite database operations
├── crawler.py             # Main crawler orchestrator
├── generate_attribution.py # CC BY-SA 3.0 attribution generator
├── wikipedia_location_crawler.py  # Legacy compatibility layer
├── main.py                # CLI entry point
└── requirements.txt       # Module dependencies
```

## Architecture

### Core Components

1. **Models** (`models.py`)
   - `WikipediaPage`: Article data with metadata
   - `CrawlerConfig`: Configuration settings
   - `CrawlStatistics`: Crawl metrics
   - `CrawlMetadata`: Crawl metadata

2. **Crawler** (`crawler.py`)
   - BFS algorithm with depth control
   - Queue management for efficient crawling
   - Automatic deduplication

3. **Relevance Scoring** (`relevance.py`)
   - Location-based keyword matching
   - Category analysis
   - Geographic coordinate bonus
   - Score range: 0-100+

4. **Database** (`database.py`)
   - SQLite storage with proper schema
   - INSERT OR REPLACE for updates
   - Efficient batch operations

5. **Wikipedia API** (`wikipedia_api.py`)
   - Rate limiting with proper headers
   - HTML download with caching
   - Coordinate extraction

## Data Storage

### Database Location
- **Path**: `data/wikipedia/wikipedia.db`
- **HTML Pages**: `data/wikipedia/pages/`

### Database Schema
```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY,
    page_id INTEGER UNIQUE,
    title TEXT NOT NULL,
    url TEXT,
    full_text TEXT,
    depth INTEGER,
    relevance_score REAL,
    latitude REAL,
    longitude REAL,
    categories TEXT,  -- JSON array
    html_file TEXT,
    crawled_at TIMESTAMP
);
```

## Commands

### 1. Crawl Command
```bash
python -m wiki_crawl.main crawl <city> <state> [options]

Options:
  --depth N            Maximum crawl depth (default: 2)
  --max-articles N     Max articles per depth level (default: 20)
  --no-download        Skip HTML downloads
```

Example:
```bash
python -m wiki_crawl.main crawl "Park City" "Utah" --depth 3 --max-articles 30
```

### 2. Attribution Command
```bash
python -m wiki_crawl.main attribution [--data-dir PATH]
```

Generates three files:
- `WIKIPEDIA_ATTRIBUTION.json` - Machine-readable
- `WIKIPEDIA_ATTRIBUTION.md` - Markdown format
- `WIKIPEDIA_ATTRIBUTION.html` - Web viewable

### 3. Analyze Command
```bash
python -m wiki_crawl.main analyze <database_path>
```

Shows:
- Top relevant articles
- Places with coordinates
- Category distribution
- Crawl statistics

## Relevance Scoring Algorithm

### Scoring Components

1. **Must-Have Keywords** (10 points each)
   - City name in text
   - State name in text
   - +5 bonus for title matches

2. **Bonus Keywords** (2 points each)
   - Geographic: county, park, monument, river, mountain
   - Urban: downtown, district, neighborhood
   - Tourism: tourist, attraction, historic, museum
   - +3 bonus for title matches

3. **Categories** (5 points each)
   - Categories containing city/state names
   - Geographic categories

4. **Coordinates** (3 points)
   - Articles with lat/lon coordinates

### Example Scores
- Direct city page: 50-70 points
- Related landmarks: 30-50 points
- Nearby locations: 20-30 points
- Peripheral articles: <20 points

## Performance

### Typical Performance
- **Articles/minute**: ~20 with depth=2
- **API delay**: 0.5 seconds (respects Wikipedia rate limits)
- **Memory usage**: ~100MB for 100 articles
- **Storage**: ~50KB per article (with HTML)

### Rate Limiting
- Proper User-Agent header for Wikipedia compliance
- 0.5 second delay between requests
- Automatic retry with exponential backoff

## Example Workflows

### Complete Location Analysis
```bash
# 1. Crawl the location
python -m wiki_crawl.main crawl "Moab" "Utah" --depth 2

# 2. Generate attribution
python -m wiki_crawl.main attribution

# 3. Analyze results
python -m wiki_crawl.main analyze data/wikipedia/wikipedia.db
```

### Testing Different Depths
```bash
# Quick test (depth 1)
python -m wiki_crawl.main crawl "Park City" "Utah" --depth 1 --max-articles 10

# Medium crawl (depth 2)
python -m wiki_crawl.main crawl "Park City" "Utah" --depth 2 --max-articles 20

# Deep crawl (depth 3)
python -m wiki_crawl.main crawl "Park City" "Utah" --depth 3 --max-articles 50
```

## Integration with Parent Project

While self-contained, this module integrates with the property_finder project:

1. **Shared Database**: Uses `data/wikipedia/wikipedia.db`
2. **Import Support**: Can be imported as `from wiki_crawl import WikipediaLocationCrawler`
3. **Data Pipeline**: Feeds into wiki_summary and wiki_embed modules

## Error Handling

- **Network errors**: Logged and skipped
- **API errors**: Exponential backoff retry
- **Database errors**: Transaction rollback
- **File system errors**: Logged with counts

## Dependencies

Core requirements (in `requirements.txt`):
- `requests>=2.31.0` - HTTP client
- `pydantic>=2.0.0` - Data validation
- `beautifulsoup4>=4.12.0` - HTML parsing
- `lxml>=4.9.0` - XML processing
- `python-dotenv>=1.0.0` - Environment variables
- `tqdm>=4.65.0` - Progress bars

## License & Attribution

This module generates CC BY-SA 3.0 compliant attribution for all Wikipedia content. Always run the attribution command after crawling to ensure compliance.

## Future Enhancements

### Performance Improvements

1. **Asynchronous Crawling**
   - Convert to async/await with aiohttp for non-blocking I/O
   - Enable concurrent API calls with semaphore-based rate limiting
   - Implement connection pooling for better resource utilization
   - Could achieve 10-50x faster crawling speeds

2. **Distributed Architecture**
   - Scale horizontally across multiple machines
   - Use message queues (RabbitMQ/Kafka) for URL distribution
   - Implement centralized state management with Redis
   - Add fault tolerance with automatic task redistribution

### Intelligent Crawling

3. **Smart URL Management**
   - Bloom filters for efficient duplicate detection
   - Priority queue based on relevance predictions
   - Content fingerprinting to avoid duplicate storage
   - Adaptive crawl depth based on content relevance
   - Crawl state persistence for resumable operations

4. **Machine Learning Integration**
   - Train classifiers to predict page relevance before downloading
   - Named entity recognition for better location extraction
   - Topic modeling to identify content clusters
   - Learning to rank for optimal crawl ordering
   - Automatic keyword expansion from crawled content

### Data Processing

5. **Advanced Storage**
   - Time-based table partitioning for efficient queries
   - Full-text search indexes on content
   - Materialized views for common query patterns
   - Redis caching for frequently accessed pages
   - Cloud storage integration (S3) for HTML files

6. **Content Analysis**
   - Natural language processing for entity extraction
   - Sentiment analysis for content characterization
   - Image analysis for visual content understanding
   - Knowledge graph construction from extracted facts
   - Automatic summarization of long articles

### Operations & Monitoring

7. **Observability Stack**
   - Prometheus metrics for crawl performance
   - Grafana dashboards for real-time visualization
   - Distributed tracing with OpenTelemetry
   - Centralized logging with ELK stack
   - Alerting for failures or anomalies

8. **API & Interfaces**
   - RESTful API for crawl management
   - WebSocket support for real-time progress
   - Web dashboard for monitoring
   - GraphQL API for flexible queries
   - Webhook notifications for crawl events

These enhancements would transform the crawler into a production-ready, scalable system capable of handling large-scale Wikipedia data acquisition with improved performance, intelligence, and reliability.