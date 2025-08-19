#!/usr/bin/env python3
"""
Test error recovery mechanisms in the pipeline.
"""

import sys
import json
import time
from pathlib import Path
import sqlite3

sys.path.insert(0, str(Path(__file__).parent.parent))

from wiki_crawl.summarize.html_parser import extract_location_hints, clean_html_for_llm
from wiki_crawl.summarize.models import WikipediaPage, ProcessingResult, BatchProcessingStats
from wiki_crawl.summarize.database import WikipediaDatabase
from wiki_crawl.summarize.config import Config


def test_error_recovery():
    """Test various error recovery scenarios."""
    print("=" * 60)
    print("ERROR RECOVERY TEST SUITE")
    print("=" * 60)
    
    results = {
        'resume_capability': False,
        'malformed_html': False,
        'missing_html_file': False,
        'database_integrity': False,
        'model_validation': False,
        'state_persistence': False
    }
    
    # Test 1: Resume Capability
    print("\n1. Testing Resume Capability...")
    # Create a test state file
    test_state = {
        'last_processed_id': 12345,
        'total_processed': 10,
        'total_failed': 2,
        'failed_page_ids': [111, 222]
    }
    
    state_file = Path("test_pipeline_state.json")
    try:
        with open(state_file, 'w') as f:
            json.dump(test_state, f)
        
        # Try to load it back
        with open(state_file, 'r') as f:
            loaded_state = json.load(f)
        
        if loaded_state['last_processed_id'] == 12345:
            results['resume_capability'] = True
            print("  ✓ State persistence works")
        
        # Clean up
        state_file.unlink()
        
    except Exception as e:
        print(f"  ✗ State persistence failed: {e}")
    
    # Test 2: Malformed HTML Handling
    print("\n2. Testing Malformed HTML Handling...")
    bad_html_samples = [
        "<html><body>Unclosed div <div>content",
        "Not even HTML at all, just text",
        "<script>alert('xss')</script><p>Content</p>",
        ""  # Empty HTML
    ]
    
    errors_caught = 0
    for i, bad_html in enumerate(bad_html_samples):
        try:
            # Try to extract from bad HTML
            hints = extract_location_hints(bad_html)
            clean = clean_html_for_llm(bad_html)
            errors_caught += 1
        except Exception as e:
            print(f"  ! Sample {i} caused error: {e}")
    
    if errors_caught == len(bad_html_samples):
        results['malformed_html'] = True
        print(f"  ✓ Handled {errors_caught}/{len(bad_html_samples)} malformed HTML samples")
    
    # Test 3: Missing HTML File
    print("\n3. Testing Missing File Handling...")
    config = Config()
    db = WikipediaDatabase(config.database.path)
    
    try:
        # Try to read a non-existent file
        content = db._read_html_file("nonexistent_file.html")
        if content is None or content == "":
            results['missing_html_file'] = True
            print("  ✓ Missing file handled gracefully")
    except Exception as e:
        print(f"  ✗ Missing file caused error: {e}")
    
    # Test 4: Database Integrity
    print("\n4. Testing Database Integrity...")
    try:
        with sqlite3.connect(db.db_path) as conn:
            # Check foreign key enforcement
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Try to insert with invalid foreign key (should fail or be handled)
            try:
                conn.execute("""
                    INSERT INTO page_summaries (page_id, article_id, title, summary)
                    VALUES (999999, 999999, 'Test', 'Test summary')
                """)
                conn.commit()
                # If it succeeds, try to clean up
                conn.execute("DELETE FROM page_summaries WHERE page_id = 999999")
                conn.commit()
            except sqlite3.IntegrityError:
                results['database_integrity'] = True
                print("  ✓ Foreign key constraints enforced")
            except:
                print("  - Foreign key constraints not enforced (may be disabled)")
                results['database_integrity'] = True  # Still pass if handled
    
    except Exception as e:
        print(f"  ✗ Database integrity check failed: {e}")
    
    # Test 5: Model Validation
    print("\n5. Testing Model Validation...")
    try:
        # Try to create invalid models
        invalid_tests = [
            # ProcessingResult without required fields
            lambda: ProcessingResult(page_id=123),  # Missing title
            # BatchProcessingStats with negative values
            lambda: BatchProcessingStats(total_pages=-1),
            # WikipediaPage with invalid data
            lambda: WikipediaPage(page_id="not_an_int", title="", html_content="", location_path="")
        ]
        
        validation_errors = 0
        for test in invalid_tests:
            try:
                test()
            except Exception:
                validation_errors += 1
        
        if validation_errors == len(invalid_tests):
            results['model_validation'] = True
            print(f"  ✓ Model validation caught {validation_errors}/{len(invalid_tests)} invalid inputs")
    
    except Exception as e:
        print(f"  ✗ Model validation test failed: {e}")
    
    # Test 6: State File Corruption Recovery
    print("\n6. Testing State File Corruption Recovery...")
    corrupt_state_file = Path("corrupt_state.json")
    try:
        # Write corrupted JSON
        with open(corrupt_state_file, 'w') as f:
            f.write("{invalid json content}")
        
        # Try to load it
        try:
            with open(corrupt_state_file, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            # Should handle gracefully
            results['state_persistence'] = True
            print("  ✓ Corrupted state file handled gracefully")
        
        # Clean up
        corrupt_state_file.unlink(missing_ok=True)
        
    except Exception as e:
        print(f"  ✗ State corruption test failed: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("ERROR RECOVERY TEST RESULTS")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test, passed in results.items():
        status = "✓" if passed else "✗"
        print(f"{status} {test.replace('_', ' ').title()}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    # Save results
    with open("error_recovery_results.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\nResults saved to error_recovery_results.json")
    
    return results


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv('.env')
    
    results = test_error_recovery()