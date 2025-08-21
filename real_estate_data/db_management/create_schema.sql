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
-- NEW KNOWLEDGE GRAPH TABLES
-- ============================================================================

-- Enhanced neighborhoods table with graph metadata
CREATE TABLE IF NOT EXISTS neighborhoods_enhanced (
    neighborhood_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    county TEXT NOT NULL,
    state TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    
    -- Graph relationship fields
    district_id TEXT,
    city_id TEXT,
    county_id TEXT,
    state_id TEXT,
    
    -- Polygon boundaries for spatial matching (GeoJSON format)
    boundary_geojson TEXT,
    
    -- Wikipedia article associations
    primary_wiki_page_id INTEGER,
    wiki_confidence REAL,
    
    -- Metadata for graph traversal
    population INTEGER,
    established_year INTEGER,
    area_sq_miles REAL,
    
    -- Original neighborhood data
    description TEXT,
    median_home_price INTEGER,
    price_trend TEXT,
    amenities TEXT,  -- JSON array
    lifestyle_tags TEXT,  -- JSON array
    characteristics TEXT,  -- JSON object
    demographics TEXT,  -- JSON object
    
    -- Graph metadata (JSON)
    graph_metadata TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (primary_wiki_page_id) REFERENCES page_summaries(page_id)
);

-- Neighborhood-Wikipedia relationships table
CREATE TABLE IF NOT EXISTS neighborhood_wiki_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    neighborhood_id TEXT NOT NULL,
    wiki_page_id INTEGER NOT NULL,
    relationship_type TEXT NOT NULL,
    relationship_subtype TEXT,
    confidence_score REAL DEFAULT 0.5,
    distance_miles REAL,
    relevance_score REAL,
    
    -- Relationship metadata
    discovered_via TEXT, -- 'exact_name_match', 'fuzzy_name_match', 'proximity', 'category_analysis', 'content_analysis', 'dspy_reasoning'
    reasoning TEXT,
    verified BOOLEAN DEFAULT FALSE,
    verification_method TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (neighborhood_id) REFERENCES neighborhoods_enhanced(neighborhood_id),
    FOREIGN KEY (wiki_page_id) REFERENCES page_summaries(page_id),
    
    UNIQUE(neighborhood_id, wiki_page_id, relationship_type)
);

-- Geographic hierarchy table
CREATE TABLE IF NOT EXISTS geographic_hierarchy (
    id TEXT PRIMARY KEY, -- e.g., 'city_san_francisco', 'county_alameda'
    name TEXT NOT NULL,
    level TEXT NOT NULL CHECK(level IN ('neighborhood', 'district', 'city', 'county', 'state', 'region')),
    parent_id TEXT,
    
    -- Wikipedia associations
    primary_wiki_page_id INTEGER,
    wiki_confidence REAL,
    
    -- Geographic data
    latitude REAL,
    longitude REAL,
    boundary_geojson TEXT,
    
    -- Metadata
    population INTEGER,
    area_sq_miles REAL,
    timezone TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (parent_id) REFERENCES geographic_hierarchy(id),
    FOREIGN KEY (primary_wiki_page_id) REFERENCES page_summaries(page_id)
);

-- Properties table with neighborhood linkage
CREATE TABLE IF NOT EXISTS properties (
    listing_id TEXT PRIMARY KEY,
    neighborhood_id TEXT NOT NULL,
    
    -- Address information
    street TEXT,
    city TEXT,
    county TEXT,
    state TEXT,
    zip TEXT,
    latitude REAL,
    longitude REAL,
    
    -- Property details
    square_feet INTEGER,
    bedrooms INTEGER,
    bathrooms REAL,
    property_type TEXT,
    year_built INTEGER,
    lot_size REAL,
    stories INTEGER,
    garage_spaces INTEGER,
    
    -- Listing information
    listing_price INTEGER,
    price_per_sqft INTEGER,
    description TEXT,
    features TEXT,  -- JSON array
    listing_date DATE,
    days_on_market INTEGER,
    virtual_tour_url TEXT,
    images TEXT,  -- JSON array
    price_history TEXT,  -- JSON array
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (neighborhood_id) REFERENCES neighborhoods_enhanced(neighborhood_id)
);

-- Relationship cache table for DSPy responses
CREATE TABLE IF NOT EXISTS relationship_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL,  -- Hash of input parameters
    neighborhood_id TEXT,
    wiki_page_id INTEGER,
    response_data TEXT NOT NULL,  -- JSON response from DSPy
    confidence_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
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

-- ============================================================================
-- INDEXES FOR NEW KNOWLEDGE GRAPH TABLES
-- ============================================================================

-- Neighborhood indexes
CREATE INDEX IF NOT EXISTS idx_neighborhoods_city ON neighborhoods_enhanced(city);
CREATE INDEX IF NOT EXISTS idx_neighborhoods_county ON neighborhoods_enhanced(county);
CREATE INDEX IF NOT EXISTS idx_neighborhoods_state ON neighborhoods_enhanced(state);
CREATE INDEX IF NOT EXISTS idx_neighborhoods_wiki ON neighborhoods_enhanced(primary_wiki_page_id);

-- Relationship indexes for efficient graph traversal
CREATE INDEX IF NOT EXISTS idx_nwr_neighborhood ON neighborhood_wiki_relationships(neighborhood_id);
CREATE INDEX IF NOT EXISTS idx_nwr_wiki_page ON neighborhood_wiki_relationships(wiki_page_id);
CREATE INDEX IF NOT EXISTS idx_nwr_type ON neighborhood_wiki_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_nwr_confidence ON neighborhood_wiki_relationships(confidence_score);
CREATE INDEX IF NOT EXISTS idx_nwr_distance ON neighborhood_wiki_relationships(distance_miles);

-- Geographic hierarchy indexes
CREATE INDEX IF NOT EXISTS idx_geo_level ON geographic_hierarchy(level);
CREATE INDEX IF NOT EXISTS idx_geo_parent ON geographic_hierarchy(parent_id);
CREATE INDEX IF NOT EXISTS idx_geo_wiki ON geographic_hierarchy(primary_wiki_page_id);

-- Property indexes
CREATE INDEX IF NOT EXISTS idx_properties_neighborhood ON properties(neighborhood_id);
CREATE INDEX IF NOT EXISTS idx_properties_city ON properties(city);
CREATE INDEX IF NOT EXISTS idx_properties_price ON properties(listing_price);

-- Cache indexes
CREATE INDEX IF NOT EXISTS idx_cache_key ON relationship_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON relationship_cache(expires_at);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View for neighborhood with all Wikipedia relationships
CREATE VIEW IF NOT EXISTS v_neighborhood_wikipedia AS
SELECT 
    n.neighborhood_id,
    n.name as neighborhood_name,
    n.city,
    n.county,
    n.state,
    nwr.wiki_page_id,
    ps.title as wiki_title,
    nwr.relationship_type,
    nwr.confidence_score,
    nwr.distance_miles,
    nwr.reasoning
FROM neighborhoods_enhanced n
LEFT JOIN neighborhood_wiki_relationships nwr ON n.neighborhood_id = nwr.neighborhood_id
LEFT JOIN page_summaries ps ON nwr.wiki_page_id = ps.page_id
ORDER BY n.neighborhood_id, nwr.confidence_score DESC;

-- View for properties with full neighborhood and Wikipedia context
CREATE VIEW IF NOT EXISTS v_properties_enriched AS
SELECT 
    p.*,
    n.name as neighborhood_name,
    n.description as neighborhood_description,
    n.median_home_price as neighborhood_median_price,
    n.graph_metadata,
    ps.title as primary_wiki_title,
    ps.short_summary as primary_wiki_summary
FROM properties p
LEFT JOIN neighborhoods_enhanced n ON p.neighborhood_id = n.neighborhood_id
LEFT JOIN page_summaries ps ON n.primary_wiki_page_id = ps.page_id;

-- View for geographic hierarchy with Wikipedia
CREATE VIEW IF NOT EXISTS v_geographic_hierarchy AS
SELECT 
    g.id,
    g.name,
    g.level,
    g.parent_id,
    p.name as parent_name,
    ps.title as wiki_title,
    ps.short_summary as wiki_summary,
    g.population,
    g.area_sq_miles
FROM geographic_hierarchy g
LEFT JOIN geographic_hierarchy p ON g.parent_id = p.id
LEFT JOIN page_summaries ps ON g.primary_wiki_page_id = ps.page_id
ORDER BY 
    CASE g.level
        WHEN 'state' THEN 1
        WHEN 'county' THEN 2
        WHEN 'city' THEN 3
        WHEN 'district' THEN 4
        WHEN 'neighborhood' THEN 5
        ELSE 6
    END,
    g.name;