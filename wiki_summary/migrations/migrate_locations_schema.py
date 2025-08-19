#!/usr/bin/env python3
"""
Migration script to update locations table for flexible location types.
Removes CHECK constraint and adds new columns for better classification.
"""

import sqlite3
import shutil
import sys
from datetime import datetime
from pathlib import Path

def backup_database(db_path: Path) -> Path:
    """Create timestamped backup of database."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = db_path.parent / f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"
    shutil.copy2(db_path, backup_path)
    print(f"✓ Created backup: {backup_path}")
    return backup_path

def check_current_schema(conn: sqlite3.Connection) -> bool:
    """Check if migration is needed."""
    cursor = conn.execute("""
        SELECT sql FROM sqlite_master 
        WHERE type='table' AND name='locations'
    """)
    result = cursor.fetchone()
    
    if not result:
        print("❌ locations table not found")
        return False
    
    schema = result[0]
    needs_migration = 'CHECK' in schema or 'location_type_category' not in schema
    return needs_migration

def migrate_schema(conn: sqlite3.Connection):
    """Perform the schema migration."""
    print("🔄 Starting schema migration...")
    
    # Start transaction
    conn.execute("BEGIN TRANSACTION")
    
    try:
        # Create new table without constraints
        conn.execute("""
            CREATE TABLE IF NOT EXISTS locations_new (
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
            )
        """)
        
        # Copy existing data
        conn.execute("""
            INSERT INTO locations_new (
                location_id, country, state, county, location, 
                location_type, created_at
            )
            SELECT 
                location_id, 
                COALESCE(country, 'United States'),
                state, 
                county, 
                location,
                location_type, 
                created_at
            FROM locations
        """)
        
        # Get count for verification
        old_count = conn.execute("SELECT COUNT(*) FROM locations").fetchone()[0]
        new_count = conn.execute("SELECT COUNT(*) FROM locations_new").fetchone()[0]
        
        if old_count != new_count:
            raise ValueError(f"Row count mismatch: {old_count} vs {new_count}")
        
        # Drop old table and rename new one
        conn.execute("DROP TABLE locations")
        conn.execute("ALTER TABLE locations_new RENAME TO locations")
        
        # Create indexes for performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_locations_state ON locations(state)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_locations_type ON locations(location_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_locations_needs_review ON locations(needs_review)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_locations_confidence ON locations(confidence)")
        
        # Commit transaction
        conn.execute("COMMIT")
        print(f"✓ Migration successful! Migrated {new_count} locations")
        
    except Exception as e:
        conn.execute("ROLLBACK")
        print(f"❌ Migration failed: {e}")
        raise

def verify_migration(conn: sqlite3.Connection):
    """Verify the migration was successful."""
    # Check new columns exist
    cursor = conn.execute("PRAGMA table_info(locations)")
    columns = {row[1] for row in cursor.fetchall()}
    
    required_columns = {
        'location_id', 'country', 'state', 'county', 'location',
        'location_type', 'location_type_category', 'llm_suggested_type',
        'confidence', 'needs_review', 'created_at', 'updated_at'
    }
    
    missing = required_columns - columns
    if missing:
        print(f"❌ Missing columns: {missing}")
        return False
    
    # Check no constraints
    cursor = conn.execute("SELECT sql FROM sqlite_master WHERE name='locations'")
    schema = cursor.fetchone()[0]
    if 'CHECK' in schema:
        print("❌ CHECK constraint still present")
        return False
    
    print("✓ Schema verification passed")
    return True

def main():
    """Run the migration."""
    # Determine database path
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])
    else:
        db_path = Path("data/wikipedia/wikipedia.db")
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return 1
    
    print(f"📂 Database: {db_path}")
    
    # Create backup
    backup_path = backup_database(db_path)
    
    try:
        with sqlite3.connect(db_path) as conn:
            # Check if migration needed
            if not check_current_schema(conn):
                print("✓ Schema already up to date")
                return 0
            
            # Perform migration
            migrate_schema(conn)
            
            # Verify success
            if verify_migration(conn):
                print("✅ Migration completed successfully!")
                return 0
            else:
                print("⚠️ Migration completed with warnings")
                return 1
                
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print(f"💾 Restore from backup if needed: {backup_path}")
        return 1

if __name__ == "__main__":
    sys.exit(main())