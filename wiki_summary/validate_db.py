#!/usr/bin/env python3
"""
Standalone database validation tool for wiki_summary module.
Checks database integrity, invalid locations, and data quality issues.
"""

import sqlite3
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
from collections import defaultdict

class DatabaseValidator:
    """Comprehensive database validation for wiki_summary."""
    
    def __init__(self, db_path: str = "data/wikipedia/wikipedia.db"):
        """Initialize validator with database path."""
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            print(f"❌ Database not found: {self.db_path}")
            sys.exit(1)
        
        self.issues = defaultdict(list)
        self.stats = {}
        
    def run_all_validations(self) -> bool:
        """Run all validation checks and return overall status."""
        print("=" * 60)
        print("Wikipedia Database Validation Report")
        print("=" * 60)
        print(f"Database: {self.db_path}")
        print(f"Validation Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Run all validation checks
        self.check_table_existence()
        self.check_database_stats()
        self.check_referential_integrity()
        self.check_duplicate_records()
        self.check_location_validity()
        self.check_data_quality()
        self.check_orphaned_records()
        self.check_index_effectiveness()
        self.check_flagged_content_consistency()
        self.check_summary_completeness()
        
        # Generate report
        return self.generate_report()
    
    def check_table_existence(self):
        """Verify all required tables exist."""
        print("\n📋 Checking table existence...")
        required_tables = ['articles', 'locations', 'page_summaries', 'flagged_content']
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            existing_tables = {row[0] for row in cursor}
        
        for table in required_tables:
            if table not in existing_tables:
                self.issues['critical'].append(f"Missing required table: {table}")
            else:
                print(f"  ✓ Table '{table}' exists")
        
        # Check for unexpected tables
        unexpected = existing_tables - set(required_tables)
        if unexpected:
            print(f"  ℹ️  Additional tables found: {', '.join(unexpected)}")
    
    def check_database_stats(self):
        """Gather and display database statistics."""
        print("\n📊 Database Statistics:")
        
        with sqlite3.connect(self.db_path) as conn:
            # Count records in each table
            for table in ['articles', 'locations', 'page_summaries', 'flagged_content']:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                self.stats[f"{table}_count"] = count
                print(f"  • {table}: {count:,} records")
            
            # Check database size
            cursor = conn.execute("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()")
            size_bytes = cursor.fetchone()[0]
            size_mb = size_bytes / (1024 * 1024)
            print(f"  • Database size: {size_mb:.2f} MB")
            
            # Check coverage
            cursor = conn.execute("""
                SELECT 
                    COUNT(DISTINCT a.id) as articles_with_summaries
                FROM articles a
                JOIN page_summaries ps ON a.id = ps.article_id
            """)
            covered = cursor.fetchone()[0]
            coverage = (covered / self.stats['articles_count'] * 100) if self.stats['articles_count'] > 0 else 0
            print(f"  • Summary coverage: {covered}/{self.stats['articles_count']} ({coverage:.1f}%)")
    
    def check_referential_integrity(self):
        """Check foreign key relationships."""
        print("\n🔗 Checking referential integrity...")
        
        with sqlite3.connect(self.db_path) as conn:
            # Check articles -> locations
            cursor = conn.execute("""
                SELECT COUNT(*) FROM articles a
                LEFT JOIN locations l ON a.location_id = l.location_id
                WHERE a.location_id IS NOT NULL AND l.location_id IS NULL
            """)
            orphaned = cursor.fetchone()[0]
            if orphaned > 0:
                self.issues['integrity'].append(f"{orphaned} articles reference non-existent locations")
                print(f"  ❌ {orphaned} articles with invalid location_id")
            else:
                print(f"  ✓ All article location references valid")
            
            # Check page_summaries -> articles
            cursor = conn.execute("""
                SELECT COUNT(*) FROM page_summaries ps
                LEFT JOIN articles a ON ps.article_id = a.id
                WHERE a.id IS NULL
            """)
            orphaned = cursor.fetchone()[0]
            if orphaned > 0:
                self.issues['integrity'].append(f"{orphaned} summaries reference non-existent articles")
                print(f"  ❌ {orphaned} summaries with invalid article_id")
            else:
                print(f"  ✓ All summary article references valid")
            
            # Check flagged_content -> articles
            cursor = conn.execute("""
                SELECT COUNT(*) FROM flagged_content fc
                LEFT JOIN articles a ON fc.article_id = a.id
                WHERE a.id IS NULL
            """)
            orphaned = cursor.fetchone()[0]
            if orphaned > 0:
                self.issues['integrity'].append(f"{orphaned} flagged items reference non-existent articles")
                print(f"  ❌ {orphaned} flagged items with invalid article_id")
            else:
                print(f"  ✓ All flagged content article references valid")
    
    def check_duplicate_records(self):
        """Check for duplicate records that shouldn't exist."""
        print("\n🔍 Checking for duplicates...")
        
        with sqlite3.connect(self.db_path) as conn:
            # Check duplicate article_ids in page_summaries
            cursor = conn.execute("""
                SELECT article_id, COUNT(*) as cnt
                FROM page_summaries
                GROUP BY article_id
                HAVING COUNT(*) > 1
            """)
            duplicates = cursor.fetchall()
            if duplicates:
                for article_id, count in duplicates:
                    self.issues['duplicates'].append(f"article_id {article_id} has {count} summaries")
                print(f"  ❌ Found {len(duplicates)} duplicate article_ids in page_summaries")
            else:
                print(f"  ✓ No duplicate article_ids in page_summaries")
            
            # Check duplicate article_ids in flagged_content
            cursor = conn.execute("""
                SELECT article_id, COUNT(*) as cnt
                FROM flagged_content
                GROUP BY article_id
                HAVING COUNT(*) > 1
            """)
            duplicates = cursor.fetchall()
            if duplicates:
                for article_id, count in duplicates:
                    self.issues['duplicates'].append(f"article_id {article_id} has {count} flagged entries")
                print(f"  ❌ Found {len(duplicates)} duplicate article_ids in flagged_content")
            else:
                print(f"  ✓ No duplicate article_ids in flagged_content")
            
            # Check duplicate location paths
            cursor = conn.execute("""
                SELECT path, COUNT(*) as cnt
                FROM locations
                GROUP BY path
                HAVING COUNT(*) > 1
            """)
            duplicates = cursor.fetchall()
            if duplicates:
                for path, count in duplicates:
                    self.issues['duplicates'].append(f"location path '{path}' has {count} entries")
                print(f"  ❌ Found {len(duplicates)} duplicate location paths")
            else:
                print(f"  ✓ No duplicate location paths")
    
    def check_location_validity(self):
        """Check for invalid or suspicious location data."""
        print("\n📍 Checking location data quality...")
        
        with sqlite3.connect(self.db_path) as conn:
            # Check for empty locations
            cursor = conn.execute("""
                SELECT COUNT(*) FROM locations
                WHERE (state IS NULL OR state = '') 
                AND (location IS NULL OR location = '')
                AND (county IS NULL OR county = '')
            """)
            empty = cursor.fetchone()[0]
            if empty > 0:
                self.issues['locations'].append(f"{empty} locations with no state, location, or county")
                print(f"  ⚠️  {empty} locations with missing geographic data")
            
            # Check for mismatched state articles
            cursor = conn.execute("""
                SELECT a.title, l.state, l.location
                FROM articles a
                JOIN locations l ON a.location_id = l.location_id
                WHERE (
                    (a.title LIKE '%Utah%' AND l.state NOT IN ('Utah', 'UT')) OR
                    (a.title LIKE '%California%' AND l.state NOT IN ('California', 'CA')) OR
                    (a.title LIKE '%Illinois%' AND l.state NOT IN ('Illinois', 'IL')) OR
                    (a.title LIKE '%Colorado%' AND l.state NOT IN ('Colorado', 'CO'))
                )
                LIMIT 10
            """)
            mismatches = cursor.fetchall()
            if mismatches:
                print(f"  ⚠️  Found {len(mismatches)} potential location mismatches:")
                for title, state, city in mismatches[:5]:
                    print(f"     - '{title}' -> {city}, {state}")
                self.issues['locations'].extend([f"{title} in wrong state {state}" for title, state, _ in mismatches])
            else:
                print(f"  ✓ No obvious location mismatches detected")
            
            # Check for invalid state values
            valid_states = {
                'Utah', 'UT', 'California', 'CA', 'Illinois', 'IL', 
                'Colorado', 'CO', 'Ohio', 'OH', 'Kentucky', 'KY',
                'Nevada', 'NV', 'Arizona', 'AZ', 'Oregon', 'OR',
                'Washington', 'WA', 'Idaho', 'ID', 'Wyoming', 'WY'
            }
            cursor = conn.execute("""
                SELECT DISTINCT state, COUNT(*) as cnt
                FROM locations
                WHERE state NOT IN ({})
                GROUP BY state
            """.format(','.join('?' * len(valid_states))), tuple(valid_states))
            invalid_states = cursor.fetchall()
            if invalid_states:
                print(f"  ⚠️  Found {len(invalid_states)} unrecognized state values:")
                for state, count in invalid_states[:5]:
                    print(f"     - '{state}' ({count} locations)")
    
    def check_data_quality(self):
        """Check for data quality issues."""
        print("\n✨ Checking data quality...")
        
        with sqlite3.connect(self.db_path) as conn:
            # Check for articles with no content
            cursor = conn.execute("""
                SELECT COUNT(*) FROM articles
                WHERE (extract IS NULL OR extract = '')
                AND (html_file IS NULL OR html_file = '')
            """)
            empty = cursor.fetchone()[0]
            if empty > 0:
                self.issues['quality'].append(f"{empty} articles with no content")
                print(f"  ⚠️  {empty} articles with no extract or HTML")
            
            # Check for very short summaries
            cursor = conn.execute("""
                SELECT COUNT(*) FROM page_summaries
                WHERE LENGTH(short_summary) < 50
            """)
            short = cursor.fetchone()[0]
            if short > 0:
                self.issues['quality'].append(f"{short} summaries are suspiciously short")
                print(f"  ⚠️  {short} summaries with < 50 characters")
            
            # Check for missing key topics
            cursor = conn.execute("""
                SELECT COUNT(*) FROM page_summaries
                WHERE key_topics IS NULL OR key_topics = ''
            """)
            missing_topics = cursor.fetchone()[0]
            if missing_topics > 0:
                self.issues['quality'].append(f"{missing_topics} summaries missing key topics")
                print(f"  ⚠️  {missing_topics} summaries without key topics")
            
            # Check confidence scores
            cursor = conn.execute("""
                SELECT AVG(overall_confidence), MIN(overall_confidence), MAX(overall_confidence)
                FROM page_summaries
                WHERE overall_confidence IS NOT NULL
            """)
            avg_conf, min_conf, max_conf = cursor.fetchone()
            if avg_conf:
                print(f"  ℹ️  Confidence scores: avg={avg_conf:.2f}, min={min_conf:.2f}, max={max_conf:.2f}")
                if avg_conf < 0.5:
                    self.issues['quality'].append(f"Low average confidence score: {avg_conf:.2f}")
    
    def check_orphaned_records(self):
        """Check for orphaned records that should be cleaned up."""
        print("\n🗑️  Checking for orphaned records...")
        
        with sqlite3.connect(self.db_path) as conn:
            # Check for unused locations
            cursor = conn.execute("""
                SELECT COUNT(*) FROM locations l
                LEFT JOIN articles a ON l.location_id = a.location_id
                WHERE a.id IS NULL
            """)
            unused = cursor.fetchone()[0]
            if unused > 0:
                self.issues['cleanup'].append(f"{unused} unused locations")
                print(f"  ℹ️  {unused} locations not referenced by any article")
            
            # Check for articles without summaries or flagged content
            cursor = conn.execute("""
                SELECT COUNT(*) FROM articles a
                LEFT JOIN page_summaries ps ON a.id = ps.article_id
                LEFT JOIN flagged_content fc ON a.id = fc.article_id
                WHERE ps.article_id IS NULL AND fc.article_id IS NULL
            """)
            unprocessed = cursor.fetchone()[0]
            if unprocessed > 0:
                print(f"  ℹ️  {unprocessed} articles not yet processed")
    
    def check_index_effectiveness(self):
        """Check if proper indexes exist."""
        print("\n⚡ Checking index effectiveness...")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT name, tbl_name, sql 
                FROM sqlite_master 
                WHERE type = 'index' AND name NOT LIKE 'sqlite_%'
            """)
            indexes = cursor.fetchall()
            
            required_indexes = {
                'flagged_content': ['article_id'],
                'page_summaries': ['article_id'],
                'locations': ['path'],
                'articles': ['location_id']
            }
            
            index_map = defaultdict(list)
            for name, table, sql in indexes:
                if sql:  # Skip auto-indexes
                    index_map[table].append(name)
            
            for table, required_cols in required_indexes.items():
                if table in index_map:
                    print(f"  ✓ {table} has {len(index_map[table])} indexes")
                else:
                    self.issues['performance'].append(f"{table} missing indexes")
                    print(f"  ⚠️  {table} has no indexes")
    
    def check_flagged_content_consistency(self):
        """Check flagged content for consistency."""
        print("\n🚩 Checking flagged content consistency...")
        
        with sqlite3.connect(self.db_path) as conn:
            # Check category distribution
            cursor = conn.execute("""
                SELECT relevance_category, COUNT(*) as cnt
                FROM flagged_content
                GROUP BY relevance_category
            """)
            categories = cursor.fetchall()
            print("  Category distribution:")
            for category, count in categories:
                print(f"    • {category or 'NULL'}: {count}")
            
            # Check for invalid scores
            cursor = conn.execute("""
                SELECT COUNT(*) FROM flagged_content
                WHERE overall_score < 0 OR overall_score > 1
                OR location_score < 0 OR location_score > 1
                OR re_score < 0 OR re_score > 1
                OR geo_score < 0 OR geo_score > 1
            """)
            invalid = cursor.fetchone()[0]
            if invalid > 0:
                self.issues['consistency'].append(f"{invalid} flagged items with invalid scores")
                print(f"  ❌ {invalid} entries with scores outside [0,1] range")
            else:
                print(f"  ✓ All scores within valid range")
    
    def check_summary_completeness(self):
        """Check if summaries are complete and valid."""
        print("\n📝 Checking summary completeness...")
        
        with sqlite3.connect(self.db_path) as conn:
            # Check for summaries with missing fields
            cursor = conn.execute("""
                SELECT COUNT(*) FROM page_summaries
                WHERE short_summary IS NULL OR short_summary = ''
                OR long_summary IS NULL OR long_summary = ''
            """)
            incomplete = cursor.fetchone()[0]
            if incomplete > 0:
                self.issues['completeness'].append(f"{incomplete} incomplete summaries")
                print(f"  ⚠️  {incomplete} summaries missing required fields")
            
            # Check location extraction success rate
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN best_state IS NOT NULL THEN 1 ELSE 0 END) as with_state,
                    SUM(CASE WHEN best_city IS NOT NULL THEN 1 ELSE 0 END) as with_city
                FROM page_summaries
            """)
            total, with_state, with_city = cursor.fetchone()
            if total > 0:
                state_pct = (with_state / total * 100)
                city_pct = (with_city / total * 100)
                print(f"  ℹ️  Location extraction: {state_pct:.1f}% have state, {city_pct:.1f}% have city")
    
    def generate_report(self) -> bool:
        """Generate final validation report."""
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        
        total_issues = sum(len(issues) for issues in self.issues.values())
        
        if total_issues == 0:
            print("✅ Database validation PASSED - No issues found!")
            return True
        
        # Group issues by severity
        critical = self.issues.get('critical', [])
        high = self.issues.get('integrity', []) + self.issues.get('duplicates', [])
        medium = self.issues.get('locations', []) + self.issues.get('quality', [])
        low = self.issues.get('cleanup', []) + self.issues.get('performance', [])
        
        if critical:
            print(f"\n🔴 CRITICAL ISSUES ({len(critical)}):")
            for issue in critical[:5]:
                print(f"  • {issue}")
        
        if high:
            print(f"\n🟠 HIGH PRIORITY ({len(high)}):")
            for issue in high[:5]:
                print(f"  • {issue}")
        
        if medium:
            print(f"\n🟡 MEDIUM PRIORITY ({len(medium)}):")
            for issue in medium[:5]:
                print(f"  • {issue}")
        
        if low:
            print(f"\n🟢 LOW PRIORITY ({len(low)}):")
            for issue in low[:5]:
                print(f"  • {issue}")
        
        print(f"\n📊 Total issues found: {total_issues}")
        
        # Determine overall status
        if critical or len(high) > 5:
            print("❌ Database validation FAILED - Critical issues need attention")
            return False
        elif high:
            print("⚠️  Database validation PASSED WITH WARNINGS")
            return True
        else:
            print("✅ Database validation PASSED - Minor issues only")
            return True

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate wiki_summary database integrity")
    parser.add_argument('--db', default='data/wikipedia/wikipedia.db',
                       help='Path to database file (default: data/wikipedia/wikipedia.db)')
    parser.add_argument('--json', action='store_true',
                       help='Output results as JSON')
    
    args = parser.parse_args()
    
    validator = DatabaseValidator(args.db)
    
    if args.json:
        # JSON output for programmatic use
        with sqlite3.connect(validator.db_path) as conn:
            conn.row_factory = sqlite3.Row
            result = {
                'database': str(validator.db_path),
                'timestamp': datetime.now().isoformat(),
                'stats': {},
                'issues': {}
            }
            
            # Gather stats
            for table in ['articles', 'locations', 'page_summaries', 'flagged_content']:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                result['stats'][table] = cursor.fetchone()[0]
            
            # Run validation
            validator.run_all_validations()
            result['issues'] = dict(validator.issues)
            result['passed'] = len(validator.issues.get('critical', [])) == 0
            
            print(json.dumps(result, indent=2))
    else:
        # Human-readable output
        success = validator.run_all_validations()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()