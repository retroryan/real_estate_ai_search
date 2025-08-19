"""
Flexible location service for handling dynamic location types.
Supports any location type suggested by LLM without constraints.

USAGE:
- Use this service for flexible location type classification
- LocationClassification: Pydantic model for flexible location data
- FlexibleLocationService: Handles creating/updating locations with flexible types
- Supports dynamic types: ski_resort, mountain, beach, landmark, etc.
- Includes confidence scoring and type validation

For basic location mismatch detection and fixing, see location.py
"""

import sqlite3
import logging
from typing import Optional, Dict, List, Set
from collections import Counter
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from wiki_summary.exceptions import DatabaseException, ValidationException

logger = logging.getLogger(__name__)


# Known location types for reference (not enforced)
KNOWN_LOCATION_TYPES: Set[str] = {
    # Administrative
    'city', 'county', 'neighborhood', 'town', 'cdp', 'district', 'municipality',
    # Natural features
    'mountain', 'mountain_range', 'peak', 'canyon', 'valley', 'lake',
    'river', 'creek', 'beach', 'island', 'desert', 'forest', 'glacier',
    # Parks and recreation
    'national_park', 'state_park', 'county_park', 'city_park',
    'ski_resort', 'resort', 'resort_town', 'recreation_area',
    'trail', 'wilderness_area', 'golf_course', 'marina', 'campground',
    # Infrastructure
    'airport', 'station', 'landmark', 'building', 'bridge', 'dam', 'port',
    # Other
    'region', 'area', 'historic_site', 'monument', 'sanctuary', 'preserve'
}


class LocationClassification(BaseModel):
    """Flexible location classification without type constraints."""
    
    # Core fields
    location_name: str = Field(description="Primary name of the location")
    location_type: str = Field(description="Type of location (any value accepted)")
    state: str = Field(description="State name (full name)")
    county: str = Field(description="County name")
    country: str = Field(default="United States")
    
    # Classification metadata
    location_type_category: Optional[str] = Field(
        default=None,
        description="Broader category: administrative, natural_feature, recreation, infrastructure, other"
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Relevance flags
    is_utah_california: bool = Field(default=False)
    should_flag: bool = Field(default=False)
    reasoning: Optional[str] = Field(default=None)
    
    # Auto-computed fields
    is_known_type: bool = Field(default=False)
    needs_review: bool = Field(default=False)
    
    @field_validator('location_type')
    @classmethod
    def normalize_location_type(cls, v: str) -> str:
        """Normalize location type to lowercase with underscores."""
        if v:
            return v.lower().replace(' ', '_').replace('-', '_')
        return v
    
    @field_validator('state')
    @classmethod
    def normalize_state(cls, v: str) -> str:
        """Ensure state is full name, not abbreviation."""
        state_map = {
            'ut': 'Utah', 'ca': 'California', 'calif': 'California',
            'ny': 'New York', 'tx': 'Texas', 'co': 'Colorado'
        }
        lower_v = v.lower() if v else ''
        return state_map.get(lower_v, v)
    
    def model_post_init(self, __context):
        """Auto-compute derived fields after initialization."""
        # Check if type is known
        self.is_known_type = self.location_type in KNOWN_LOCATION_TYPES
        
        # Flag for review if low confidence or unknown type
        self.needs_review = (
            self.confidence < 0.6 or 
            not self.is_known_type or
            self.state == 'unknown'
        )
        
        # Auto-categorize if not provided
        if not self.location_type_category:
            self.location_type_category = self._infer_category()
    
    def _infer_category(self) -> str:
        """Infer category from location type."""
        type_lower = self.location_type.lower()
        
        if any(t in type_lower for t in ['city', 'county', 'town', 'neighborhood', 'district']):
            return 'administrative'
        elif any(t in type_lower for t in ['mountain', 'lake', 'river', 'canyon', 'valley', 'peak']):
            return 'natural_feature'
        elif any(t in type_lower for t in ['park', 'resort', 'recreation', 'trail', 'golf']):
            return 'recreation'
        elif any(t in type_lower for t in ['airport', 'station', 'bridge', 'building']):
            return 'infrastructure'
        else:
            return 'other'


class FlexibleLocationService:
    """Service for managing flexible location types in database."""
    
    def __init__(self, db_path: str):
        """Initialize service with database path."""
        self.db_path = Path(db_path)
        self.new_types_log: List[Dict] = []
        self.type_counts = Counter()
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
        
        logger.info(f"Initialized FlexibleLocationService with {db_path}")
    
    def process_classification(self, classification: LocationClassification, article_id: int) -> int:
        """Process a location classification and update database.
        
        Args:
            classification: Location classification from LLM
            article_id: ID of the article being classified
            
        Returns:
            location_id of the processed location
        """
        # Track new types
        if not classification.is_known_type:
            self._log_new_type(classification)
        
        # Update type count
        self.type_counts[classification.location_type] += 1
        
        with sqlite3.connect(self.db_path) as conn:
            # Check if location exists
            location_id = self._find_existing_location(conn, classification)
            
            if location_id:
                # Update existing location
                self._update_location(conn, location_id, classification)
            else:
                # Create new location
                location_id = self._create_location(conn, classification)
            
            # Update article's location_id
            self._update_article_location(conn, article_id, location_id)
            
            conn.commit()
            
        logger.info(f"Processed {classification.location_name} ({classification.location_type}) -> location_id={location_id}")
        return location_id
    
    def _find_existing_location(self, conn: sqlite3.Connection, classification: LocationClassification) -> Optional[int]:
        """Find existing location matching classification."""
        cursor = conn.execute("""
            SELECT location_id FROM locations
            WHERE location = ? AND state = ? AND county = ?
        """, (classification.location_name, classification.state, classification.county))
        
        result = cursor.fetchone()
        return result[0] if result else None
    
    def _update_location(self, conn: sqlite3.Connection, location_id: int, classification: LocationClassification):
        """Update existing location with new classification data."""
        conn.execute("""
            UPDATE locations SET
                location_type = ?,
                location_type_category = ?,
                llm_suggested_type = ?,
                confidence = ?,
                needs_review = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE location_id = ?
        """, (
            classification.location_type,
            classification.location_type_category,
            classification.location_type,  # Store original suggestion
            classification.confidence,
            int(classification.needs_review),
            location_id
        ))
    
    def _create_location(self, conn: sqlite3.Connection, classification: LocationClassification) -> int:
        """Create new location record."""
        cursor = conn.execute("""
            INSERT INTO locations (
                country, state, county, location, 
                location_type, location_type_category,
                llm_suggested_type, confidence, needs_review
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            classification.country,
            classification.state,
            classification.county,
            classification.location_name,
            classification.location_type,
            classification.location_type_category,
            classification.location_type,  # Store original
            classification.confidence,
            int(classification.needs_review)
        ))
        return cursor.lastrowid
    
    def _update_article_location(self, conn: sqlite3.Connection, article_id: int, location_id: int):
        """Update article's location_id."""
        conn.execute("""
            UPDATE articles SET location_id = ?
            WHERE id = ?
        """, (location_id, article_id))
    
    def _log_new_type(self, classification: LocationClassification):
        """Log discovery of new location type."""
        self.new_types_log.append({
            'type': classification.location_type,
            'example': classification.location_name,
            'state': classification.state,
            'confidence': classification.confidence,
            'reasoning': classification.reasoning,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"New location type discovered: '{classification.location_type}' (example: {classification.location_name})")
    
    def generate_report(self) -> Dict:
        """Generate report on location classifications."""
        # Get database statistics
        with sqlite3.connect(self.db_path) as conn:
            stats = self._get_database_stats(conn)
        
        # Analyze new types
        new_type_summary = self._analyze_new_types()
        
        report = {
            'database_stats': stats,
            'type_distribution': dict(self.type_counts.most_common(20)),
            'new_types': new_type_summary,
            'recommendations': self._generate_recommendations(),
            'timestamp': datetime.now().isoformat()
        }
        
        return report
    
    def _get_database_stats(self, conn: sqlite3.Connection) -> Dict:
        """Get statistics from database."""
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT location_type) as unique_types,
                AVG(confidence) as avg_confidence,
                SUM(needs_review) as needs_review_count,
                COUNT(DISTINCT state) as unique_states
            FROM locations
        """)
        
        row = cursor.fetchone()
        return {
            'total_locations': row[0],
            'unique_types': row[1],
            'avg_confidence': round(row[2], 2) if row[2] else 0,
            'needs_review': row[3],
            'unique_states': row[4]
        }
    
    def _analyze_new_types(self) -> Dict:
        """Analyze discovered new types."""
        if not self.new_types_log:
            return {'count': 0, 'types': []}
        
        type_examples = {}
        for entry in self.new_types_log:
            t = entry['type']
            if t not in type_examples:
                type_examples[t] = []
            type_examples[t].append(entry['example'])
        
        return {
            'count': len(type_examples),
            'types': [
                {'type': t, 'examples': examples[:3], 'count': len(examples)}
                for t, examples in type_examples.items()
            ]
        }
    
    def _generate_recommendations(self) -> List[Dict]:
        """Generate recommendations for new types."""
        recommendations = []
        
        for type_name, count in self.type_counts.items():
            if type_name not in KNOWN_LOCATION_TYPES and count >= 3:
                recommendations.append({
                    'action': 'add_to_known_types',
                    'type': type_name,
                    'occurrences': count,
                    'reason': f"Seen {count} times, consider adding to KNOWN_LOCATION_TYPES"
                })
        
        # Check for types needing review
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT location_type, COUNT(*) as cnt
                FROM locations
                WHERE needs_review = 1
                GROUP BY location_type
                ORDER BY cnt DESC
                LIMIT 5
            """)
            
            for row in cursor:
                recommendations.append({
                    'action': 'review_type',
                    'type': row[0],
                    'count': row[1],
                    'reason': 'Multiple locations of this type flagged for review'
                })
        
        return recommendations