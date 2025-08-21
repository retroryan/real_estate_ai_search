-- Complete database schema for Real Estate Wikipedia Knowledge Graph
-- This script creates all tables if they don't exist, preserving existing data

-- ============================================================================
-- EXISTING WIKIPEDIA TABLES
-- ============================================================================

-- Locations table - hierarchical location data
CREATE TABLE IF NOT EXISTS locations (
    location_id INTEGER PRIMARY KEY AUTOINCREMENT,
    country TEXT NOT NULL DEFAULT 'United States',
    state TEXT NOT NULL,
    county TEXT NOT NULL,
    location TEXT,
    location_type TEXT,
    location_type_category TEXT,
    llm_suggested_type TEXT,
    confidence REAL DEFAULT 0.0,
    needs_review INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Articles table - Wikipedia articles
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pageid INTEGER NOT NULL,
    location_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    extract TEXT,
    categories TEXT,
    latitude REAL,
    longitude REAL,
    relevance_score REAL,
    depth INTEGER,
    crawled_at TIMESTAMP,
    html_file TEXT,
    file_hash TEXT,
    image_url TEXT,
    links_count INTEGER,
    infobox_data TEXT,
    FOREIGN KEY (location_id) REFERENCES locations (location_id)
);

-- Page summaries table - LLM-generated summaries
CREATE TABLE IF NOT EXISTS page_summaries (
    page_id INTEGER PRIMARY KEY,
    article_id INTEGER,
    title TEXT,
    short_summary TEXT NOT NULL,
    long_summary TEXT NOT NULL,
    key_topics TEXT,
    best_city TEXT,
    best_county TEXT,
    best_state TEXT,
    overall_confidence REAL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (page_id) REFERENCES articles(pageid)
);

-- Ingested data table - for search/embedding systems
CREATE TABLE IF NOT EXISTS ingested_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content_type TEXT NOT NULL CHECK(content_type IN ('wikipedia_doc', 'wikipedia_section', 'wikipedia_paragraph')),
    location_tier TEXT NOT NULL CHECK(location_tier IN ('city', 'county', 'state', 'none')),
    confidence_score REAL,
    best_city TEXT,
    best_county TEXT,
    best_state TEXT,
    chunk_size INTEGER,
    embedding_dims INTEGER DEFAULT 768,
    search_content_length INTEGER,
    ingestion_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    elasticsearch_doc_id TEXT,
    quality_tier TEXT CHECK(quality_tier IN ('excellent', 'good', 'limited')) DEFAULT 'good',
    search_priority INTEGER DEFAULT 1,
    FOREIGN KEY (page_id) REFERENCES page_summaries(page_id)
);

-- Flagged content table - for relevance filtering
CREATE TABLE IF NOT EXISTS flagged_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER UNIQUE,
    title TEXT NOT NULL,
    overall_score REAL,
    location_score REAL,
    re_score REAL,
    geo_score REAL,
    relevance_category TEXT,
    reasons_to_flag TEXT,
    reasons_to_keep TEXT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
);

-- Removed content table - for out-of-scope articles
CREATE TABLE IF NOT EXISTS removed_content (
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


-- ============================================================================
-- INDEXES FOR EXISTING TABLES
-- ============================================================================

CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_location 
    ON locations(country, state, county, location, location_type);

CREATE INDEX IF NOT EXISTS idx_locations_state ON locations(state);
CREATE INDEX IF NOT EXISTS idx_locations_type ON locations(location_type);
CREATE INDEX IF NOT EXISTS idx_locations_needs_review ON locations(needs_review);
CREATE INDEX IF NOT EXISTS idx_locations_confidence ON locations(confidence);

CREATE UNIQUE INDEX IF NOT EXISTS idx_page_summaries_article ON page_summaries(article_id);

CREATE INDEX IF NOT EXISTS idx_ingested_page_id ON ingested_data(page_id);
CREATE INDEX IF NOT EXISTS idx_ingested_location_tier ON ingested_data(location_tier);
CREATE INDEX IF NOT EXISTS idx_ingested_quality_tier ON ingested_data(quality_tier);
CREATE INDEX IF NOT EXISTS idx_ingested_timestamp ON ingested_data(ingestion_timestamp);
