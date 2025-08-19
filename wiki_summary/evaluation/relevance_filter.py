"""
Relevance filter for Wikipedia articles to focus on real estate relevant content.
Flags articles that are not relevant to neighborhoods in Utah and California.
"""

import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
import re
from typing import TYPE_CHECKING

# Import shared models
from wiki_summary.models.relevance import RelevanceScore

if TYPE_CHECKING:
    from wiki_summary.services.flexible_location import LocationClassification

logger = logging.getLogger(__name__)


class EnhancedLocationData(BaseModel):
    """Enhanced location data combining database and LLM-extracted information."""
    article_id: int = Field(description="Database article ID")
    city: Optional[str] = Field(None, description="City name (LLM or database)")
    county: Optional[str] = Field(None, description="County name (LLM extracted)")
    state: Optional[str] = Field(None, description="State name (LLM or database)")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="LLM extraction confidence")
    
    class Config:
        validate_assignment = True


class RealEstateRelevanceFilter:
    """
    Filter Wikipedia articles for real estate relevance.
    Focus on Utah (Park City area) and California (San Francisco area).
    """
    
    def __init__(self, neighborhoods_file: Optional[str] = None):
        """
        Initialize filter with neighborhood data.
        
        Args:
            neighborhoods_file: Path to neighborhoods JSON file
        """
        # Load neighborhood data
        self.neighborhoods = self._load_neighborhoods()
        
        # Define relevant geographic areas
        self.relevant_states = {"utah", "ut", "california", "ca", "calif"}
        self.relevant_counties_ut = {
            "summit", "wasatch", "salt lake", "utah county", "davis", "weber"
        }
        self.relevant_counties_ca = {
            "san francisco", "san mateo", "marin", "alameda", "contra costa",
            "santa clara", "sonoma", "napa"
        }
        
        # Consolidated keyword sets for topic evaluation
        self.RE_KEYWORDS = {
            # Real estate core terms
            'real estate', 'housing', 'property', 'development', 'residential',
            'neighborhood', 'community', 'homes', 'architecture', 'zoning',
            'district', 'construction', 'buildings'
        }
        
        self.AMENITY_KEYWORDS = {
            # Location amenities and features
            'tourism', 'recreation', 'shopping', 'dining', 'schools',
            'parks', 'transit', 'downtown', 'historic', 'cultural', 
            'ski', 'resort', 'transportation', 'highways', 'airports',
            'hospitals', 'healthcare', 'universities', 'colleges'
        }
        
        self.NEGATIVE_KEYWORDS = {
            # Non-real estate topics to flag
            'military', 'battle', 'war', 'conflict', 'biography',
            'sports team', 'athlete', 'album', 'song', 'movie', 
            'television', 'quantum physics', 'molecular biology'
        }
        
        # Broader geographic context that's acceptable
        self.acceptable_broader_context = {
            "rocky mountains", "sierra nevada", "pacific coast",
            "wasatch range", "uintah", "san francisco bay", "bay area",
            "silicon valley", "wine country", "tahoe", "great salt lake"
        }
        
        logger.info("Initialized RealEstateRelevanceFilter")
    
    def _load_neighborhoods(self) -> dict:
        """Load neighborhood data from JSON files."""
        neighborhoods = {}
        
        # Load Park City neighborhoods
        pc_file = Path("real_estate_data/neighborhoods_pc.json")
        if pc_file.exists():
            with open(pc_file) as f:
                pc_data = json.load(f)
                for n in pc_data:
                    neighborhoods[n['name'].lower()] = {
                        'city': n['city'],
                        'state': n['state'],
                        'tags': n.get('lifestyle_tags', [])
                    }
        
        # Load San Francisco neighborhoods  
        sf_file = Path("real_estate_data/neighborhoods_sf.json")
        if sf_file.exists():
            with open(sf_file) as f:
                sf_data = json.load(f)
                for n in sf_data:
                    neighborhoods[n['name'].lower()] = {
                        'city': n['city'],
                        'state': n['state'],
                        'tags': n.get('lifestyle_tags', [])
                    }
        
        return neighborhoods
    
    def evaluate_article_with_llm_data(self, title: str, summary: str, 
                                      location_data: EnhancedLocationData,
                                      key_topics: list[str]) -> RelevanceScore:
        """
        Evaluate article relevance using ONLY LLM-generated data.
        No keyword matching - trust the LLM's understanding.
        
        SCORING METHODOLOGY:
        The relevance score is computed from three components:
        
        1. Location Relevance (40% weight):
           - 1.0 if state is Utah or California
           - 0.0 if different state
           - 0.3 if state unknown
        
        2. Real Estate Relevance (50% weight):
           - Based on LLM-identified topics
           - RE topics (housing, property, etc): +0.2 per topic
           - Amenity topics (parks, schools, etc): +0.1 per topic
           - Negative topics (military, sports, etc): -0.3 per topic
        
        3. Geographic Scope (10% weight):
           - 1.0 for target counties (Summit, San Francisco, etc)
           - Bonus for target cities (Park City, SF, etc)
        
        4. Confidence Adjustment:
           - +0.1 for high LLM confidence (>0.8)
           - -0.2 for low LLM confidence (<0.5)
        
        Final score >= 0.5 means article is relevant.
        
        Args:
            title: Article title
            summary: LLM-generated summary content
            location_data: Enhanced location data from LLM
            key_topics: LLM-identified key topics
            
        Returns:
            RelevanceScore with LLM-based evaluation
        """
        score = RelevanceScore(
            article_id=location_data.article_id,
            title=title
        )
        
        # Step 1: Evaluate location (is it in Utah/California?)
        self._evaluate_llm_location(score, location_data)
        
        # Step 2: Evaluate topics (is it about RE/neighborhoods?)
        self._evaluate_topics(score, key_topics, enhance_mode=False)
        
        # Step 3: Apply confidence adjustment
        if location_data.confidence > 0.8:
            score.reasons_to_keep.append(f"High LLM confidence: {location_data.confidence:.2f}")
            confidence_boost = 0.1
        elif location_data.confidence < 0.5:
            score.reasons_to_flag.append(f"Low LLM confidence: {location_data.confidence:.2f}")
            confidence_boost = -0.2
        else:
            confidence_boost = 0.0
        
        # Step 4: Calculate weighted final score
        # Weights: location=40%, RE relevance=50%, geographic=10%
        score.overall_score = min(1.0, max(0.0, 
            0.4 * score.location_relevance +      # Is it in target states?
            0.5 * score.real_estate_relevance +   # Is it RE-related?
            0.1 * score.geographic_scope +        # Is it in target counties/cities?
            confidence_boost                      # LLM confidence adjustment
        ))
        
        # Article is relevant if score >= 0.5
        score.is_relevant = score.overall_score >= 0.5
        
        return score
    
    def _evaluate_llm_location(self, score: RelevanceScore, location_data: EnhancedLocationData):
        """Evaluate location relevance based on LLM extraction."""
        # Check if location is in our target areas
        if location_data.state:
            state_lower = location_data.state.lower()
            if any(s in state_lower for s in ['utah', 'ut', 'california', 'ca', 'calif']):
                score.location_relevance = 1.0
                score.reasons_to_keep.append(f"Target state: {location_data.state}")
            else:
                score.location_relevance = 0.0
                score.reasons_to_flag.append(f"Non-target state: {location_data.state}")
        else:
            score.location_relevance = 0.3  # Unknown state
            score.reasons_to_flag.append("State not identified by LLM")
        
        # Bonus for specific counties/cities
        if location_data.county:
            county_lower = location_data.county.lower()
            if any(c in county_lower for c in ['summit', 'wasatch', 'san francisco', 'san mateo']):
                score.geographic_scope = 1.0
                score.reasons_to_keep.append(f"Target county: {location_data.county}")
            else:
                score.geographic_scope = 0.5
        
        if location_data.city:
            city_lower = location_data.city.lower()
            if any(c in city_lower for c in ['park city', 'san francisco', 'palo alto']):
                score.geographic_scope = min(1.0, score.geographic_scope + 0.3)
                score.reasons_to_keep.append(f"Target city: {location_data.city}")
    
    def evaluate_with_location_classification(self, classification: 'LocationClassification') -> RelevanceScore:
        """Evaluate article relevance using flexible location classification.
        
        This method properly flags non-Utah/California articles while keeping
        Utah/California articles based on their real estate relevance.
        
        Args:
            classification: LocationClassification from the flexible location service
            
        Returns:
            RelevanceScore with proper flagging logic
        """
        # Create score object
        score = RelevanceScore(
            article_id=getattr(classification, 'article_id', 0),
            title=classification.location_name
        )
        
        # Primary logic: Flag articles NOT in Utah/California
        if classification.should_flag:
            # Article is NOT Utah/California - flag it
            score.overall_score = 0.2
            score.location_relevance = 0.0
            score.real_estate_relevance = 0.0
            score.geographic_scope = 0.0
            score.reasons_to_flag.append(f"Not Utah/California location: {classification.state}")
            score.is_relevant = False
            
        elif classification.is_utah_california:
            # Article IS Utah/California - evaluate its relevance
            score.location_relevance = 1.0
            score.reasons_to_keep.append(f"Utah/California location: {classification.location_name}")
            
            # Score based on location type for real estate relevance
            location_type = classification.location_type.lower()
            
            # High RE relevance types
            if any(t in location_type for t in ['city', 'neighborhood', 'town', 'resort', 'community']):
                score.real_estate_relevance = 0.8
                score.reasons_to_keep.append(f"High RE relevance: {classification.location_type}")
                
            # Medium RE relevance types  
            elif any(t in location_type for t in ['county', 'valley', 'district', 'cdp']):
                score.real_estate_relevance = 0.6
                score.reasons_to_keep.append(f"Medium RE relevance: {classification.location_type}")
                
            # Lower but still relevant types
            elif any(t in location_type for t in ['park', 'lake', 'recreation', 'trail', 'beach']):
                score.real_estate_relevance = 0.5
                score.reasons_to_keep.append(f"Recreation/amenity relevance: {classification.location_type}")
                
            # Other types
            else:
                score.real_estate_relevance = 0.3
                score.reasons_to_keep.append(f"General location: {classification.location_type}")
            
            # Geographic scope based on confidence
            score.geographic_scope = classification.confidence
            
            # Calculate overall score
            score.overall_score = (
                0.4 * score.location_relevance +
                0.4 * score.real_estate_relevance +
                0.2 * score.geographic_scope
            )
            
            # Mark as relevant if score is good
            score.is_relevant = score.overall_score >= 0.5
            
        else:
            # Ambiguous/unknown location - flag for review
            score.overall_score = 0.4
            score.location_relevance = 0.3
            score.real_estate_relevance = 0.3
            score.geographic_scope = 0.3
            score.reasons_to_flag.append("Location unclear or ambiguous")
            score.reasons_to_flag.append(f"Low confidence: {classification.confidence:.2f}")
            score.is_relevant = False
        
        return score
    
    def _evaluate_topics(self, score: RelevanceScore, topics: list[str], enhance_mode: bool = False):
        """Consolidated topic evaluation method.
        
        Args:
            score: RelevanceScore to modify
            topics: List of topic strings
            enhance_mode: If True, enhances existing scores. If False, sets base scores.
        """
        if not topics:
            if not enhance_mode:
                score.real_estate_relevance = 0.3
                score.reasons_to_flag.append("No key topics identified")
            return
        
        topics_lower = [t.lower() for t in topics]
        
        # Count matches using consolidated keyword sets
        re_matches = sum(1 for t in topics_lower if any(k in t for k in self.RE_KEYWORDS))
        amenity_matches = sum(1 for t in topics_lower if any(k in t for k in self.AMENITY_KEYWORDS))
        negative_matches = sum(1 for t in topics_lower if any(k in t for k in self.NEGATIVE_KEYWORDS))
        
        # Calculate scores based on mode
        if enhance_mode:
            # Enhancement mode: adjust existing scores
            if re_matches > 0:
                score.real_estate_relevance = min(1.0, score.real_estate_relevance + 0.2 * re_matches)
                score.reasons_to_keep.append(f"RE-relevant topics: {re_matches}")
            
            if amenity_matches > 0:
                score.geographic_scope = min(1.0, score.geographic_scope + 0.1 * amenity_matches)
                score.reasons_to_keep.append(f"Location topics: {amenity_matches}")
            
            if negative_matches > 0:
                score.real_estate_relevance *= (1 - 0.2 * negative_matches)
                score.reasons_to_flag.append(f"Non-RE topics: {negative_matches}")
                
        else:
            # Base mode: set initial scores
            if re_matches > 0:
                score.real_estate_relevance = min(1.0, 0.3 + 0.2 * re_matches)
                matching_topics = [t for t in topics if any(k in t.lower() for k in self.RE_KEYWORDS)][:2]
                score.reasons_to_keep.append(f"RE topics: {re_matches} ({', '.join(matching_topics)})")
            
            if amenity_matches > 0:
                score.real_estate_relevance = min(1.0, score.real_estate_relevance + 0.1 * amenity_matches)
                score.reasons_to_keep.append(f"Amenity topics: {amenity_matches}")
            
            if negative_matches > 0:
                score.real_estate_relevance = max(0.0, score.real_estate_relevance - 0.3 * negative_matches)
                score.reasons_to_flag.append(f"Non-RE topics: {negative_matches}")
            
            # Default if no matches in base mode
            if re_matches == 0 and amenity_matches == 0:
                score.real_estate_relevance = 0.2
                score.reasons_to_flag.append("No RE-relevant topics found")
    
    def _enhance_scoring_with_topics(self, score: RelevanceScore, topics: list[str]):
        """Enhance relevance scoring based on LLM-identified topics."""
        # Use the consolidated topic evaluation in enhancement mode
        self._evaluate_topics(score, topics, enhance_mode=True)
    
    def evaluate_article(self, title: str, content: str, 
                        location_data: Optional[dict] = None) -> RelevanceScore:
        """
        Evaluate article relevance for real estate purposes.
        
        Args:
            title: Article title
            content: Article content (first 2000 chars is enough)
            location_data: Optional location metadata
            
        Returns:
            RelevanceScore with detailed evaluation
        """
        score = RelevanceScore(
            article_id=location_data.get('article_id', 0) if location_data else 0,
            title=title
        )
        
        # Lowercase for comparison
        title_lower = title.lower()
        content_lower = content.lower() if content else ""
        
        # 1. Evaluate location relevance
        self._evaluate_location(title_lower, content_lower, location_data, score)
        
        # 2. Evaluate real estate relevance
        self._evaluate_real_estate_relevance(title_lower, content_lower, score)
        
        # 3. Evaluate geographic scope
        self._evaluate_geographic_scope(title_lower, content_lower, location_data, score)
        
        # Calculate overall score
        score.calculate_overall()
        
        return score
    
    def _evaluate_location(self, title: str, content: str, 
                          location_data: Optional[dict], score: RelevanceScore):
        """Evaluate location relevance."""
        points = 0.0
        
        # Check if in relevant states
        if location_data:
            state = location_data.get('state', '').lower()
            if state in self.relevant_states:
                points += 0.5
                score.reasons_to_keep.append(f"Located in {state.upper()}")
            elif state and state not in ['', 'unknown']:
                score.reasons_to_flag.append(f"CRITICAL: Wrong state - {state}")
                score.location_relevance = 0
                return
        
        # Check for neighborhood mentions
        for neighborhood in self.neighborhoods:
            if neighborhood in title or neighborhood in content[:1000]:
                points += 0.3
                score.reasons_to_keep.append(f"Mentions neighborhood: {neighborhood}")
        
        # Check for relevant city/county mentions
        ut_counties = sum(1 for c in self.relevant_counties_ut if c in content)
        ca_counties = sum(1 for c in self.relevant_counties_ca if c in content)
        
        if ut_counties > 0:
            points += 0.2
            score.reasons_to_keep.append("Mentions Utah counties")
        if ca_counties > 0:
            points += 0.2
            score.reasons_to_keep.append("Mentions California counties")
        
        # Specific location checks
        if "park city" in title or "park city" in content[:500]:
            points += 0.3
            score.reasons_to_keep.append("Park City content")
        if "san francisco" in title or "san francisco" in content[:500]:
            points += 0.3
            score.reasons_to_keep.append("San Francisco content")
        
        score.location_relevance = min(1.0, points)
    
    def _evaluate_real_estate_relevance(self, title: str, content: str, 
                                       score: RelevanceScore):
        """Evaluate real estate and lifestyle relevance."""
        points = 0.0
        
        # Count positive keywords using consolidated sets
        positive_matches = sum(1 for kw in self.RE_KEYWORDS 
                              if kw in content)
        positive_matches += sum(1 for kw in self.AMENITY_KEYWORDS 
                               if kw in content)
        if positive_matches > 5:
            points += 0.6
            score.reasons_to_keep.append(f"High RE keyword density ({positive_matches} matches)")
        elif positive_matches > 2:
            points += 0.4
            score.reasons_to_keep.append(f"Moderate RE keywords ({positive_matches} matches)")
        elif positive_matches > 0:
            points += 0.2
        
        # Check for negative keywords using consolidated set
        negative_matches = sum(1 for kw in self.NEGATIVE_KEYWORDS 
                              if kw in content)
        if negative_matches > 3:
            points -= 0.4
            score.reasons_to_flag.append(f"Non-RE content detected ({negative_matches} matches)")
        elif negative_matches > 1:
            points -= 0.2
        
        # Special categories that are always relevant
        if any(cat in title for cat in ["school", "park", "recreation", "shopping",
                                        "transit", "development", "historic district"]):
            points += 0.3
            score.reasons_to_keep.append("RE-relevant category")
        
        # Special categories to flag
        if any(cat in title for cat in ["election", "political party", "military",
                                        "war", "battle", "federal"]):
            points -= 0.5
            score.reasons_to_flag.append("Non-RE category")
        
        score.real_estate_relevance = max(0.0, min(1.0, points))
    
    def _evaluate_geographic_scope(self, title: str, content: str,
                                  location_data: Optional[dict], score: RelevanceScore):
        """Evaluate if geographic scope is appropriate."""
        points = 1.0  # Start with assumption it's ok
        
        # Check for acceptable broader context
        for context in self.acceptable_broader_context:
            if context in content:
                score.reasons_to_keep.append(f"Relevant regional context: {context}")
                points = 1.0
                score.geographic_scope = points
                return
        
        # Check for out-of-scope geography
        out_of_scope = [
            "new york", "texas", "florida", "washington dc", "chicago",
            "boston", "atlanta", "denver", "portland", "seattle"
        ]
        
        for place in out_of_scope:
            if place in title:
                points = 0.0
                score.reasons_to_flag.append(f"CRITICAL: Out of geographic scope - {place}")
                break
            elif place in content[:500]:  # Less critical if just mentioned
                points -= 0.3
                score.reasons_to_flag.append(f"Mentions out-of-scope location: {place}")
        
        # National/International scope
        if any(term in title for term in ["united states", "national", "federal",
                                          "international", "global"]):
            if not any(term in title for term in ["national register", "national park"]):
                points -= 0.5
                score.reasons_to_flag.append("Too broad geographic scope")
        
        score.geographic_scope = max(0.0, points)
    
    def create_flagged_content_report(self, evaluations: list[RelevanceScore],
                                     db_path: str):
        """
        Create a report of flagged content in the database.
        
        Args:
            evaluations: List of RelevanceScore evaluations
            db_path: Path to the database
        """
        import sqlite3
        
        logger.info(f"Creating flagged content report with {len(evaluations)} evaluations")
        logger.info(f"Database path: {db_path}")
        
        with sqlite3.connect(db_path) as conn:
            # Create flagged_content table if it doesn't exist
            conn.execute("""
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
                    FOREIGN KEY (article_id) REFERENCES articles(id)
                )
            """)
            
            # Insert ONLY articles that should be flagged (non-Utah/California or low relevance)
            flagged_count = 0
            for eval in evaluations:
                # Only insert articles that should actually be flagged
                should_flag = False
                category = None
                
                # Flag if it's outside Utah/California (location_relevance = 0.0)
                if eval.location_relevance <= 0.0:
                    should_flag = True
                    category = "non_target_location"
                # Flag if it has critical issues (like wrong state explicitly mentioned)
                elif any("CRITICAL" in r for r in eval.reasons_to_flag):
                    should_flag = True
                    category = "critical_issues"
                # Flag if overall score is very low despite being in Utah/California
                elif eval.overall_score < 0.3 and eval.location_relevance > 0.0:
                    should_flag = True
                    category = "low_relevance"
                
                # Only insert if it should be flagged
                if should_flag:
                    conn.execute("""
                        INSERT OR REPLACE INTO flagged_content 
                        (article_id, title, overall_score, location_score, re_score, geo_score,
                         relevance_category, reasons_to_flag, reasons_to_keep)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        eval.article_id,
                        eval.title,
                        round(eval.overall_score, 2),
                        round(eval.location_relevance, 2),
                        round(eval.real_estate_relevance, 2),
                        round(eval.geographic_scope, 2),
                        category,
                        ', '.join(eval.reasons_to_flag) if eval.reasons_to_flag else None,
                        ', '.join(eval.reasons_to_keep) if eval.reasons_to_keep else None
                    ))
                    flagged_count += 1
            
            logger.info(f"Flagged {flagged_count} out of {len(evaluations)} articles for potential removal")
            
            conn.commit()
            logger.info(f"Committed {flagged_count} flagged records to flagged_content")
        
        # Generate summary statistics
        stats = self._get_flagged_content_stats(db_path)
        logger.info(f"Stats retrieved: {stats}")
        
        logger.info(f"Created flagged content report in database")
        
        # Print summary
        print(f"\n=== Relevance Filtering Report ===")
        print(f"Total articles evaluated: {stats['total']}")
        print(f"Highly relevant: {stats['highly_relevant']}")
        print(f"Marginal relevance: {stats['marginal_relevance']}")
        print(f"Flagged for removal: {stats['flagged_for_removal']}")
        
        if stats['flagged_for_removal'] > 0:
            flagged_articles = self._get_flagged_articles(db_path)
            print("\nArticles to remove:")
            for article in flagged_articles[:5]:
                print(f"  - {article['title']} (score: {article['overall_score']})")
                if article['reasons_to_flag']:
                    for reason in article['reasons_to_flag'].split(', ')[:2]:
                        print(f"    → {reason}")
        
        return stats
    
    def _get_flagged_content_stats(self, db_path: str) -> dict:
        """Get statistics from flagged content table."""
        import sqlite3
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN relevance_category = 'highly_relevant' THEN 1 ELSE 0 END) as highly_relevant,
                    SUM(CASE WHEN relevance_category = 'marginal_relevance' THEN 1 ELSE 0 END) as marginal_relevance,
                    SUM(CASE WHEN relevance_category = 'flagged_for_removal' THEN 1 ELSE 0 END) as flagged_for_removal
                FROM flagged_content
            """)
            
            row = cursor.fetchone()
            return {
                'total': row[0],
                'highly_relevant': row[1],
                'marginal_relevance': row[2], 
                'flagged_for_removal': row[3]
            }
    
    def _get_flagged_articles(self, db_path: str) -> list:
        """Get articles flagged for removal."""
        import sqlite3
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("""
                SELECT title, overall_score, reasons_to_flag
                FROM flagged_content
                WHERE relevance_category = 'flagged_for_removal'
                ORDER BY overall_score ASC
            """)
            
            return [{'title': row[0], 'overall_score': row[1], 'reasons_to_flag': row[2]}
                   for row in cursor.fetchall()]

