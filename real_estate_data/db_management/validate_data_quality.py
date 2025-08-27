#!/usr/bin/env python3
"""
Validate data quality of Wikipedia relationships and neighborhood data.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataQualityValidator:
    """Validate Wikipedia relationships and neighborhood data quality."""
    
    def __init__(self, db_path: str = "data/wikipedia/wikipedia.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.issues = []
        
        # Known facts for validation
        self.facts = {
            "geographic": {
                "Oakley, Utah": {
                    "county": "Summit County",
                    "state": "Utah",
                    "nearby": ["Kamas", "Marion", "Peoa", "Coalville"],
                    "incorrect": ["Salt Lake City", "Provo", "Ogden"]
                },
                "Summit Park, Utah": {
                    "county": "Summit County", 
                    "state": "Utah",
                    "nearby": ["Park City", "Snyderville Basin", "Silver Summit"],
                    "incorrect": ["Oakley", "Coalville", "Kamas"]
                },
                "Heber City, Utah": {
                    "county": "Wasatch County",  # NOT Summit County
                    "state": "Utah",
                    "nearby": ["Midway", "Daniel", "Charleston"],
                    "incorrect": ["Park City", "Kamas", "Coalville"]
                },
                "Coalville, Utah": {
                    "county": "Summit County",
                    "state": "Utah",
                    "is_county_seat": True,
                    "nearby": ["Echo", "Hoytsville", "Wanship"],
                    "incorrect": ["Park City", "Heber City"]
                },
                "Kamas, Utah": {
                    "county": "Summit County",
                    "state": "Utah",
                    "nearby": ["Francis", "Woodland", "Oakley"],
                    "incorrect": ["Park City", "Coalville"]
                },
                "Canyons Village": {
                    "city": "Park City",
                    "county": "Summit County",
                    "state": "Utah",
                    "merged_with": "Park City Mountain Resort",
                    "year_merged": 2015
                }
            },
            "landmarks": {
                "Echo Reservoir": {
                    "nearest_city": "Coalville",
                    "county": "Summit County"
                },
                "Rockport Reservoir": {
                    "nearest_city": "Coalville",
                    "county": "Summit County"
                },
                "Deer Creek Reservoir": {
                    "nearest_city": "Heber City",
                    "county": "Wasatch County"
                },
                "Jordanelle Reservoir": {
                    "nearest_city": "Heber City",
                    "county": "Wasatch County"
                },
                "Mirror Lake": {
                    "nearest_city": "Kamas",
                    "highway": "Mirror Lake Highway (Utah State Route 150)"
                },
                "Uinta Mountains": {
                    "access_from": ["Kamas", "Francis"],
                    "not_near": ["Park City", "Coalville"]
                }
            },
            "incorrect_associations": {
                # These are commonly confused but incorrect
                "Santana Row": {
                    "not_in": ["San Francisco", "Oakland"],
                    "correct_city": "San Jose"
                },
                "Willow Glen": {
                    "not_in": ["San Francisco", "Park City"],
                    "correct_city": "San Jose"
                },
                "Weber River": {
                    "flows_through": ["Oakley", "Coalville", "Echo"],
                    "not_through": ["Park City", "Heber City"]
                }
            }
        }
    
    def validate_geographic_accuracy(self):
        """Validate geographic relationships are accurate."""
        cursor = self.conn.cursor()
        
        # Check county assignments
        cursor.execute("""
            SELECT n.neighborhood_id, n.name, n.city, n.county, n.state
            FROM neighborhoods_enhanced n
            WHERE n.neighborhood_id IN (
                'oak-oakley-008', 'sp-summit-park-006', 'heb-heber-010',
                'coal-downtown-007', 'kam-kamas-009', 'pc-canyons-005'
            )
        """)
        
        neighborhoods = cursor.fetchall()
        
        for nb in neighborhoods:
            # Special case: Heber Valley should be in Wasatch County
            if nb['name'] == 'Heber Valley' and nb['county'] != 'Wasatch':
                self.issues.append({
                    'type': 'INCORRECT_COUNTY',
                    'neighborhood': nb['name'],
                    'current': nb['county'],
                    'correct': 'Wasatch',
                    'severity': 'HIGH'
                })
            
            # All others in this set should be Summit County
            elif nb['name'] != 'Heber Valley' and nb['city'] not in ['San Jose'] and nb['county'] != 'Summit':
                self.issues.append({
                    'type': 'INCORRECT_COUNTY',
                    'neighborhood': nb['name'],
                    'current': nb['county'],
                    'correct': 'Summit',
                    'severity': 'HIGH'
                })
    
    def validate_wikipedia_associations(self):
        """Validate Wikipedia article associations are appropriate."""
        cursor = self.conn.cursor()
        
        # Check for suspicious associations
        cursor.execute("""
            SELECT n.name, n.city, ps.title, nwr.relationship_type, nwr.confidence_score
            FROM neighborhood_wiki_relationships nwr
            JOIN neighborhoods_enhanced n ON nwr.neighborhood_id = n.neighborhood_id
            JOIN page_summaries ps ON nwr.wiki_page_id = ps.page_id
            WHERE n.neighborhood_id IN (
                'oak-oakley-008', 'sp-summit-park-006', 'heb-heber-010',
                'coal-downtown-007', 'kam-kamas-009', 'pc-canyons-005'
            )
        """)
        
        associations = cursor.fetchall()
        
        for assoc in associations:
            # Check for geographic inconsistencies
            if 'Heber' in assoc['name'] and 'Summit County' in assoc['title']:
                self.issues.append({
                    'type': 'INCORRECT_ASSOCIATION',
                    'neighborhood': assoc['name'],
                    'article': assoc['title'],
                    'reason': 'Heber City is in Wasatch County, not Summit County',
                    'severity': 'MEDIUM'
                })
            
            # Check for duplicate associations (same article with different relationship types)
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM neighborhood_wiki_relationships nwr2
                JOIN neighborhoods_enhanced n2 ON nwr2.neighborhood_id = n2.neighborhood_id
                JOIN page_summaries ps2 ON nwr2.wiki_page_id = ps2.page_id
                WHERE n2.name = ? AND ps2.title = ?
            """, (assoc['name'], assoc['title']))
            
            result = cursor.fetchone()
            if result['count'] > 1:
                self.issues.append({
                    'type': 'DUPLICATE_ASSOCIATION',
                    'neighborhood': assoc['name'],
                    'article': assoc['title'],
                    'count': result['count'],
                    'severity': 'LOW'
                })
    
    def validate_synthetic_ids(self):
        """Check for synthetic vs real Wikipedia page IDs."""
        cursor = self.conn.cursor()
        
        # Wikipedia page IDs should be reasonable numbers
        cursor.execute("""
            SELECT DISTINCT ps.page_id, ps.title
            FROM page_summaries ps
            JOIN neighborhood_wiki_relationships nwr ON ps.page_id = nwr.wiki_page_id
            WHERE ps.page_id > 900000000 OR ps.page_id < 100
        """)
        
        suspicious_ids = cursor.fetchall()
        
        for page in suspicious_ids:
            self.issues.append({
                'type': 'SUSPICIOUS_PAGE_ID',
                'page_id': page['page_id'],
                'title': page['title'],
                'reason': 'Page ID seems synthetic or invalid',
                'severity': 'LOW'
            })
    
    def validate_json_consistency(self):
        """Validate JSON files match database content."""
        
        # Load JSON files
        pc_file = Path("real_estate_data/neighborhoods_pc.json")
        sf_file = Path("real_estate_data/neighborhoods_sf.json")
        
        json_neighborhoods = []
        if pc_file.exists():
            with open(pc_file) as f:
                json_neighborhoods.extend(json.load(f))
        if sf_file.exists():
            with open(sf_file) as f:
                json_neighborhoods.extend(json.load(f))
        
        cursor = self.conn.cursor()
        
        for nb in json_neighborhoods:
            nb_id = nb.get('neighborhood_id')
            if not nb_id:
                continue
            
            # Check if neighborhood exists in database
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM neighborhoods_enhanced
                WHERE neighborhood_id = ?
            """, (nb_id,))
            
            result = cursor.fetchone()
            if result['count'] == 0:
                self.issues.append({
                    'type': 'MISSING_IN_DATABASE',
                    'neighborhood_id': nb_id,
                    'name': nb.get('name'),
                    'severity': 'HIGH'
                })
            
            # Check Wikipedia data consistency
            if 'wikipedia_correlations' in nb:
                primary = nb['wikipedia_correlations'].get('primary_wiki_article')
                if primary and primary.get('page_id'):
                    cursor.execute("""
                        SELECT COUNT(*) as count
                        FROM page_summaries
                        WHERE page_id = ?
                    """, (primary['page_id'],))
                    
                    result = cursor.fetchone()
                    if result['count'] == 0:
                        self.issues.append({
                            'type': 'MISSING_WIKI_ARTICLE',
                            'neighborhood': nb.get('name'),
                            'page_id': primary['page_id'],
                            'title': primary.get('title'),
                            'severity': 'MEDIUM'
                        })
    
    def check_known_errors(self):
        """Check for known common errors."""
        cursor = self.conn.cursor()
        
        # Check if Orange Bubble Express and Red Pine Gondola are real Wikipedia articles
        # These are likely synthetic entries
        synthetic_articles = [
            'Orange Bubble Express',
            'Red Pine Gondola',
            'Colony at White Pine Canyon'
        ]
        
        for article_title in synthetic_articles:
            cursor.execute("""
                SELECT page_id FROM page_summaries WHERE title = ?
            """, (article_title,))
            
            result = cursor.fetchone()
            if result:
                self.issues.append({
                    'type': 'LIKELY_SYNTHETIC',
                    'title': article_title,
                    'page_id': result['page_id'],
                    'reason': 'This is likely not a real Wikipedia article',
                    'severity': 'MEDIUM'
                })
        
        # Check for real articles that should exist
        real_articles = {
            'Park City, Utah': 151252,
            'Summit County, Utah': 71074,
            'Wasatch County, Utah': 71078,
            'Deer Creek Reservoir': None,  # Should exist but ID unknown
            'Uinta Mountains': None,  # Should exist
            'Mirror Lake (Utah)': None  # Should exist
        }
        
        for title, expected_id in real_articles.items():
            cursor.execute("""
                SELECT page_id FROM page_summaries WHERE title = ?
            """, (title,))
            
            result = cursor.fetchone()
            if not result:
                self.issues.append({
                    'type': 'MISSING_REAL_ARTICLE',
                    'title': title,
                    'expected_id': expected_id,
                    'severity': 'HIGH'
                })
            elif expected_id and result['page_id'] != expected_id:
                self.issues.append({
                    'type': 'WRONG_PAGE_ID',
                    'title': title,
                    'current_id': result['page_id'],
                    'expected_id': expected_id,
                    'severity': 'MEDIUM'
                })
    
    def generate_report(self):
        """Generate a comprehensive data quality report."""
        
        print("\n" + "="*80)
        print("DATA QUALITY VALIDATION REPORT")
        print("="*80)
        
        # Run all validations
        print("\n⏳ Running validations...")
        self.validate_geographic_accuracy()
        self.validate_wikipedia_associations()
        self.validate_synthetic_ids()
        self.validate_json_consistency()
        self.check_known_errors()
        
        # Group issues by severity
        high_severity = [i for i in self.issues if i['severity'] == 'HIGH']
        medium_severity = [i for i in self.issues if i['severity'] == 'MEDIUM']
        low_severity = [i for i in self.issues if i['severity'] == 'LOW']
        
        print(f"\n📊 Summary:")
        print(f"  Total Issues Found: {len(self.issues)}")
        print(f"  High Severity: {len(high_severity)}")
        print(f"  Medium Severity: {len(medium_severity)}")
        print(f"  Low Severity: {len(low_severity)}")
        
        if high_severity:
            print("\n🔴 HIGH SEVERITY ISSUES:")
            for issue in high_severity:
                print(f"  [{issue['type']}]")
                for k, v in issue.items():
                    if k not in ['type', 'severity']:
                        print(f"    {k}: {v}")
        
        if medium_severity:
            print("\n🟡 MEDIUM SEVERITY ISSUES:")
            for issue in medium_severity[:10]:  # Limit to first 10
                print(f"  [{issue['type']}]")
                for k, v in issue.items():
                    if k not in ['type', 'severity']:
                        print(f"    {k}: {v}")
            if len(medium_severity) > 10:
                print(f"  ... and {len(medium_severity) - 10} more")
        
        if low_severity:
            print("\n🟢 LOW SEVERITY ISSUES:")
            print(f"  Found {len(low_severity)} low severity issues (mostly duplicates or synthetic IDs)")
        
        # Provide recommendations
        print("\n💡 RECOMMENDATIONS:")
        if any('INCORRECT_COUNTY' in i['type'] for i in self.issues):
            print("  • Fix county assignments for neighborhoods")
        if any('DUPLICATE' in i['type'] for i in self.issues):
            print("  • Remove duplicate Wikipedia associations")
        if any('SYNTHETIC' in i['type'] for i in self.issues):
            print("  • Consider removing or marking synthetic Wikipedia entries")
        if any('MISSING' in i['type'] for i in self.issues):
            print("  • Add missing Wikipedia articles or update references")
        
        return self.issues
    
    def close(self):
        """Close database connection."""
        self.conn.close()


def main():
    """Main execution function."""
    validator = DataQualityValidator()
    
    try:
        issues = validator.generate_report()
        
        # Save issues to file
        output_file = Path("real_estate_data/db_management/data_quality_issues.json")
        output_file.parent.mkdir(exist_ok=True, parents=True)
        
        with open(output_file, 'w') as f:
            json.dump(issues, f, indent=2)
        
        print(f"\n📁 Full report saved to: {output_file}")
        
    finally:
        validator.close()


if __name__ == "__main__":
    main()