"""Database operations for Wikipedia crawler."""

import sqlite3
import json
from pathlib import Path
from typing import Dict, Optional
import logging

from .models import WikipediaPage, CrawlerConfig

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manage SQLite database operations."""
    
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.db_path = config.data_dir / "wikipedia" / "wikipedia.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create tables using the existing schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS locations (
                location_id INTEGER PRIMARY KEY AUTOINCREMENT,
                country TEXT NOT NULL,
                state TEXT NOT NULL,
                county TEXT NOT NULL,
                location TEXT,
                location_type TEXT CHECK(location_type IN ('county', 'city', 'neighborhood', 'national_park', 'mountain', 'canyon', 'valley', 'district')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
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
                FOREIGN KEY (location_id) REFERENCES locations (location_id),
                UNIQUE(pageid, location_id)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_location ON articles(location_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_pageid ON articles(pageid)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_title ON articles(title)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_file_hash ON articles(file_hash)')
        
        conn.commit()
        conn.close()
    
    def get_or_create_location_id(self) -> int:
        """Get or create location record and return its ID."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        location_type = 'city' if self.config.city else 'county'
        
        # First, try to find existing location
        cursor.execute('''
            SELECT location_id FROM locations 
            WHERE country = ? AND state = ? AND location = ? AND location_type = ?
        ''', ('USA', self.config.state, self.config.city, location_type))
        result = cursor.fetchone()
        
        if result:
            location_id = result[0]
        else:
            # If not found, create it
            cursor.execute('''
                INSERT INTO locations (country, state, county, location, location_type)
                VALUES (?, ?, ?, ?, ?)
            ''', ('USA', self.config.state, 'Unknown', self.config.city, location_type))
            location_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return location_id
    
    def save_articles(self, articles: Dict[str, WikipediaPage]):
        """Save articles to database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        location_id = self.get_or_create_location_id()
        
        for title, page in articles.items():
            # Prepare categories as JSON string
            categories_json = json.dumps(page.categories) if page.categories else None
            
            cursor.execute('''
                INSERT OR REPLACE INTO articles 
                (pageid, location_id, title, url, extract, categories,
                 latitude, longitude, relevance_score, depth, crawled_at,
                 html_file, file_hash, image_url, links_count, infobox_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                page.pageid, location_id, page.title, page.url, page.extract,
                categories_json,
                page.coordinates.lat if page.coordinates else None,
                page.coordinates.lon if page.coordinates else None,
                page.relevance_score, page.depth,
                page.crawled_at.isoformat(),
                page.local_filename, page.file_hash, page.image_url,
                len(page.links), None
            ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Saved {len(articles)} articles to {self.db_path}")